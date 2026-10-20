"""Replay fixed-control certification evidence and explain shared-work limits.

This is offline instrumentation of the existing predicates, not a controller or
an independent implementation of Bernstein certification. Full-budget queries
are explicitly counterfactual; they never authorize an unknown recorded action.
"""

from collections import Counter
import json

from .algebraic_reference import exact_sign_reference
from .barrier_paths import auxiliary_polynomial
from .certification_study import STRATEGIES
from .dynamics import Circle, PlanarState
from .numbers import positive, q, vector2
from .planar_control import candidate_actions, hocbf_constraints
from .polynomial import certify_minimum, certify_sign
from .sampling import sacbf_assessment


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, name, minimum=0):
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum, f"Invalid {name}")
    return value


def _same(left, right):
    # Python equality alone treats True == 1 and 1.0 == 1. Evidence must preserve
    # JSON types as well as values, especially work counts and stopping flags.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _proof(cert, property_name):
    return {"property": property_name, "status": cert.status, "goal": cert.goal,
            "lower_exact": str(cert.lower), "upper_exact": str(cert.upper),
            "witness_time_exact": str(cert.witness_time), "subdivisions": cert.subdivisions,
            "precision_reached": cert.precision_reached, "budget_exhausted": cert.budget_exhausted,
            "stopping_reason": cert.stopping_reason}


def _decision(statuses):
    return "rejected" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "accepted"


def allocation_audit(spec, study):
    """Check every timed predicate result and reconstruct its work allocation.

    Rebuild candidate sets, domains, exact polynomials and independent sign truth.
    Replay at the *assigned* budget, rather than trusting a recorded count. Also
    evaluate each queried polynomial at the full per-polynomial limit to identify
    losses caused by prior work allocation. For minimum queries the sign-prefix
    count measures work beyond a sign decision, still required by a width goal.

    Timing samples, old audit predicates, stopping plans and group statistics in
    the input are not verified here. They are not used to establish these results.
    """
    _require(isinstance(spec, dict) and isinstance(study, dict), "Expected configuration and study objects")
    strategies = spec.get("strategies", list(STRATEGIES[:3]))
    _require(isinstance(strategies, list) and strategies and all(isinstance(s, str) and s in STRATEGIES for s in strategies)
             and len(set(strategies)) == len(strategies), "Invalid strategies")
    scope = spec.get("budget_scope", "per_polynomial")
    _require(scope in ("per_polynomial", "per_control") and study["budget_scope"] == scope, "Budget scope mismatch")
    tolerances = [positive(t, "tolerance") for t in spec.get("tolerances", ["1e-10"])]
    budgets = [_integer(b, "budget") for b in spec.get("budgets", [256])]
    _require(tolerances and budgets and len(set(tolerances)) == len(tolerances) and len(set(budgets)) == len(budgets),
             "Invalid or duplicate numerical settings")
    settings = ([(s, None, None) for s in strategies if s == "sacbf_relaxed"] +
                [(s, str(t), b) for t in tolerances for b in budgets for s in strategies if s != "sacbf_relaxed"])
    _require(study["strategies"] == strategies and _integer(study["seed"], "study seed") == _integer(spec.get("seed", 20261019), "seed")
             and _integer(study["repeats"], "study repeats", 1) == _integer(spec.get("repeats", 5), "repeats", 1), "Study configuration mismatch")
    base, cases = spec.get("base", {}), spec.get("cases", [])
    _require(isinstance(base, dict) and isinstance(cases, list) and cases and
             len(study["reference"]) == len(cases) and _integer(study["cases"], "study cases") == len(cases), "Case coverage mismatch")
    indexed = {}
    for row in study["measurements"]:
        key = (row["case_index"], row["candidate_index"], row["strategy"], row["tolerance_exact"], row["budget"])
        _integer(key[0], "case index")
        _integer(key[1], "candidate index")
        if key[4] is not None:
            _integer(key[4], "row budget")
        _require(key not in indexed, "Duplicate property measurement")
        indexed[key] = row
    cache, sign_cache, rows, applicable, expected = {}, {}, [], 0, set()

    def certify(polynomial, duration, tolerance, budget, goal):
        key = (polynomial, duration, tolerance, budget, goal)
        if key not in cache:
            function = certify_sign if goal == "sign" else certify_minimum
            cache[key] = function(polynomial, duration, tolerance, budget)
        return cache[key]

    def truth(polynomial, duration):
        key = (polynomial, duration)
        if key not in sign_cache:
            sign_cache[key] = exact_sign_reference(polynomial, duration)
        return sign_cache[key]

    for case_index, case in enumerate(cases):
        config, reference = base | case, study["reference"][case_index]
        state, nominal = PlanarState(config["p"], config["v"]), vector2(config["nominal"])
        obstacles = tuple(Circle(**o) if isinstance(o, dict) else o for o in config["obstacles"])
        duration, a_max = positive(config["duration"]), positive(config["a_max"])
        lambda1, lambda2 = positive(config.get("lambda1", 2)), positive(config.get("lambda2", 2))
        _, domains = hocbf_constraints(state, obstacles, lambda1, lambda2)
        _require(all(q(d["h_exact"]) >= 0 for d in domains), "Initially unsafe audit state")
        in_domain = all(d["in_domain"] for d in domains)
        candidates = candidate_actions(nominal, state, duration, a_max, config.get("grid_points", 5),
                                       config.get("command_quantum", "1e-6"))
        _require(reference["name"] == config["name"] and reference["hocbf_applicable"] == in_domain
                 and reference["candidate_count"] == len(candidates)
                 and len(reference["candidates"]) == len(candidates), "Candidate set or domain mismatch")
        for candidate_index, action in enumerate(candidates):
            saved_candidate = reference["candidates"][candidate_index]
            _require(vector2(saved_candidate["action_exact"]) == action, "Candidate order or action mismatch")
            if not in_domain:
                continue
            geometric = [o.polynomial(state, action) for o in obstacles]
            paths = [(h, auxiliary_polynomial(h, lambda1)) for h in geometric]
            independent = [{"h": truth(h, duration), "psi": truth(psi, duration)} for h, psi in paths]
            h_truth = "unsafe" if any(p["h"]["status"] == "unsafe" for p in independent) else "safe"
            psi_truth = "unsafe" if any(p["psi"]["status"] == "unsafe" for p in independent) else "safe"
            joint_truth = "unsafe" if "unsafe" in (h_truth, psi_truth) else "safe"
            _require(_same(saved_candidate["independent_evidence"], independent) and
                     saved_candidate["independent_high_order_status"] == joint_truth and
                     saved_candidate["independent_geometric_status"] == h_truth and
                     saved_candidate["independent_auxiliary_status"] == psi_truth, "Independent reference mismatch")
            for strategy, tolerance_text, budget in settings:
                key = (case_index, candidate_index, strategy, tolerance_text, budget)
                expected.add(key)
                _require(key in indexed, "Missing property measurement")
                saved = indexed[key]
                _require(saved["case"] == config["name"] and vector2(saved["action_exact"]) == action
                         and saved["independent_reference_status"] == joint_truth
                         and saved["geometric_reference_status"] == h_truth
                         and saved["auxiliary_reference_status"] == psi_truth, "Measurement action or truth mismatch")
                trace, proofs, implications, used = [], [], [], 0
                if strategy == "sacbf_relaxed":
                    assessments = [sacbf_assessment(state, action, o, duration, lambda1, lambda2, True) for o in obstacles]
                    result = {"status": "accepted" if all(a["accepted"] for a in assessments) else "rejected",
                              "subdivisions": 0, "assessments": assessments}
                    counterfactual = result["status"]
                else:
                    tolerance = positive(tolerance_text)
                    goal = "minimum" if strategy == "minimum" else "sign"
                    full_statuses, earlier_post_sign = [], 0
                    for obstacle_index, (h, psi) in enumerate(paths):
                        for property_name, polynomial in (("psi", psi),) if strategy == "auxiliary_sign" else (("h", h), ("psi", psi)):
                            allowance = budget if scope == "per_polynomial" else budget-used
                            cert = certify(polynomial, duration, tolerance, allowance, goal)
                            full = certify(polynomial, duration, tolerance, budget, goal)
                            sign = certify(polynomial, duration, tolerance, allowance, "sign")
                            _require(cert.status == sign.status and cert.subdivisions >= sign.subdivisions,
                                     "Single-polynomial proof-prefix inconsistency")
                            spent_after_sign = cert.subdivisions-sign.subdivisions
                            used += cert.subdivisions
                            trace.append({"obstacle_index": obstacle_index, "property": property_name,
                                          "polynomial_exact": [str(c) for c in polynomial],
                                          "assigned_budget": allowance, "prior_subdivisions": used-cert.subdivisions,
                                          "remaining_budget": budget-used if scope == "per_control" else None,
                                          "certificate": _proof(cert, property_name),
                                          "full_per_polynomial_certificate": _proof(full, property_name),
                                          "sign_goal_subdivisions": sign.subdivisions,
                                          "subdivisions_after_sign_decision": spent_after_sign,
                                          "prior_subdivisions_after_sign_decisions": earlier_post_sign,
                                          "allocation_limited_unknown": cert.status == "unknown" and full.status != "unknown"})
                            earlier_post_sign += spent_after_sign
                            proofs.append(_proof(cert, property_name))
                            full_statuses.append(full.status)
                            if strategy == "auxiliary_sign":
                                implications.append({"rule": "linear_comparison", "initial_h_exact": str(h[0]),
                                                     "lambda1_exact": str(lambda1), "duration_exact": str(duration),
                                                     "status": "safe" if cert.status == "safe" else "not_certified"})
                    result = {"status": _decision([p["status"] for p in proofs]), "subdivisions": used, "proofs": proofs}
                    if strategy == "auxiliary_sign":
                        result["geometric_implications"] = implications
                    counterfactual = _decision(full_statuses)
                _require(_same(saved["result"], result), "Saved result disagrees with assigned-budget replay")
                _require(not (result["status"] == "accepted" and joint_truth == "unsafe"), "Accepted path violates independent truth")
                _require(not (strategy != "sacbf_relaxed" and result["status"] == "rejected" and joint_truth == "safe"),
                         "Negative witness contradicts independent truth")
                rows.append({"case_index": case_index, "candidate_index": candidate_index, "case": config["name"],
                             "action_exact": [str(a) for a in action], "strategy": strategy,
                             "tolerance_exact": tolerance_text, "budget": budget, "status": result["status"],
                             "independent_joint_status": joint_truth, "full_per_polynomial_status": counterfactual,
                             "allocation_limited_control": result["status"] == "unknown" and counterfactual != "unknown",
                             "trace": trace})
        applicable += in_domain
    _require(expected == set(indexed), "Unexpected property measurement or excluded-domain row")
    _require(_integer(study["applicable_cases"], "applicable cases") == applicable, "Applicable-case count mismatch")
    groups = []
    for strategy, tolerance, budget in settings:
        group = [r for r in rows if (r["strategy"], r["tolerance_exact"], r["budget"]) == (strategy, tolerance, budget)]
        if not group:
            continue
        transitions = Counter((r["full_per_polynomial_status"], r["status"]) for r in group)
        groups.append({"strategy": strategy, "tolerance_exact": tolerance, "budget": budget, "controls": len(group),
                       "accepted": sum(r["status"] == "accepted" for r in group),
                       "rejected": sum(r["status"] == "rejected" for r in group),
                       "unknown": sum(r["status"] == "unknown" for r in group),
                       "allocation_limited_controls": sum(r["allocation_limited_control"] for r in group),
                       "unknown_at_full_per_polynomial_limits": sum(r["status"] == "unknown" and r["full_per_polynomial_status"] == "unknown" for r in group),
                       "allocation_limited_unknown_queries": sum(t["allocation_limited_unknown"] for r in group for t in r["trace"]),
                       "total_subdivisions": sum(t["certificate"]["subdivisions"] for r in group for t in r["trace"]),
                       "subdivisions_after_sign_decisions": sum(t["subdivisions_after_sign_decision"] for r in group for t in r["trace"]),
                       "full_to_allocated_transitions": [{"full_per_polynomial": a, "allocated": b, "controls": n}
                                                          for (a, b), n in sorted(transitions.items())]})
    return {"status": "verified", "budget_scope": scope, "property_configurations": len(rows),
            "replayed_queries": sum(len(r["trace"]) for r in rows), "unique_bernstein_replays": len(cache),
            "unique_independent_sign_references": len(sign_cache), "groups": groups, "measurements": rows,
            "scope": "Offline assigned-budget replay and counterfactual allocation diagnosis; no recorded decision is changed. Uses the existing Bernstein engine, with independent algebraic sign cross-checks. Input timing samples and historical audit predicates are outside verification scope."}
