"""Paired property-evaluation costs at fixed states and fixed candidate controls."""

from random import Random
from statistics import median
from time import perf_counter_ns

from .barrier_paths import certify_auxiliary_path
from .dynamics import Circle, PlanarState
from .numbers import positive, vector2
from .planar_audit import audit_cases
from .polynomial import certify_minimum, certify_sign
from .sampling import sacbf_assessment

STRATEGIES = ("sacbf_relaxed", "minimum", "sign", "auxiliary_sign")


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _evaluate(strategy, state, action, obstacles, duration, lambda1, lambda2, tolerance, budget):
    if strategy == "sacbf_relaxed":
        assessments = [sacbf_assessment(state, action, o, duration, lambda1, lambda2, True) for o in obstacles]
        return {"status": "accepted" if all(a["accepted"] for a in assessments) else "rejected",
                "subdivisions": 0, "assessments": assessments}
    certifier = certify_sign if strategy == "sign" else certify_minimum
    proofs, implications = [], []
    for obstacle in obstacles:
        h = obstacle.polynomial(state, action)
        if strategy == "auxiliary_sign":
            cert, implication = certify_auxiliary_path(h, lambda1, duration, tolerance, budget)
            implications.append(implication)
            computed = [("psi", cert)]
        else:
            psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
            computed = [(name, certifier(polynomial, duration, tolerance, budget))
                        for name, polynomial in (("h", h), ("psi", psi))]
        for property_name, cert in computed:
            proofs.append({"property": property_name, "status": cert.status, "goal": cert.goal,
                           "lower_exact": str(cert.lower), "upper_exact": str(cert.upper),
                           "witness_time_exact": str(cert.witness_time), "subdivisions": cert.subdivisions,
                           "precision_reached": cert.precision_reached, "budget_exhausted": cert.budget_exhausted,
                           "stopping_reason": cert.stopping_reason})
    statuses = [p["status"] for p in proofs]
    result = {"status": "rejected" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "accepted",
              "subdivisions": sum(p["subdivisions"] for p in proofs), "proofs": proofs}
    if strategy == "auxiliary_sign":
        result["geometric_implications"] = implications
    return result


def certification_study(spec):
    """Time identical property queries; reference work is offline and separate.

    Every strategy targets both path properties at every obstacle; auxiliary_sign
    derives the geometric property rather than querying its polynomial sign.
    Repeated measurements are interleaved in a seeded shuffled order per control.
    Costs include polynomial/condition construction and exact evidence assembly,
    but exclude candidate generation, control selection and offline reference work.
    """
    if not isinstance(spec, dict) or set(spec)-{"base", "cases", "tolerances", "budgets", "repeats", "seed", "strategies"}:
        raise ValueError("Unknown certification study field")
    strategies = spec.get("strategies", list(STRATEGIES[:3]))
    if (not isinstance(strategies, list) or not strategies or
            any(not isinstance(s, str) or s not in STRATEGIES for s in strategies) or len(set(strategies)) != len(strategies)):
        raise ValueError("strategies must be a nonempty list of distinct supported names")
    repeats = _integer(spec.get("repeats", 5), "repeats", 1)
    seed = _integer(spec.get("seed", 20261019), "seed")
    tolerances, budgets = spec.get("tolerances", ["1e-10"]), spec.get("budgets", [256])
    if not all(isinstance(values, list) and values for values in (tolerances, budgets)):
        raise ValueError("tolerances and budgets must be nonempty lists")
    tolerances = [positive(t, "tolerance") for t in tolerances]
    budgets = [_integer(b, "budget") for b in budgets]
    if len(set(tolerances)) != len(tolerances) or len(set(budgets)) != len(budgets):
        raise ValueError("Duplicate tolerances or budgets would duplicate matched queries")
    reference = audit_cases({"base": spec.get("base", {}), "cases": spec.get("cases", [])})
    settings = ([(s, None, None) for s in strategies if s == "sacbf_relaxed"] +
                [(s, t, b) for t in tolerances for b in budgets for s in strategies if s != "sacbf_relaxed"])
    rng, rows = Random(seed), []
    for case_index, (case, evidence) in enumerate(zip(spec["cases"], reference)):
        config = spec.get("base", {}) | case
        if not evidence["hocbf_applicable"]:
            continue
        state = PlanarState(config["p"], config["v"])
        obstacles = tuple(o if isinstance(o, Circle) else Circle(**o) for o in config["obstacles"])
        duration = positive(config["duration"], "duration")
        lambda1, lambda2 = positive(config.get("lambda1", 2)), positive(config.get("lambda2", 2))
        for candidate_index, candidate in enumerate(evidence["candidates"]):
            action = vector2(candidate["action_exact"])
            measurements = [[] for _ in settings]
            positions = [[] for _ in settings]
            results = [None for _ in settings]
            for _ in range(repeats):
                order = list(range(len(settings)))
                rng.shuffle(order)
                for position, setting_index in enumerate(order):
                    strategy, tolerance, budget = settings[setting_index]
                    start = perf_counter_ns()
                    result = _evaluate(strategy, state, action, obstacles, duration, lambda1, lambda2, tolerance, budget)
                    elapsed = perf_counter_ns()-start
                    measurements[setting_index].append(elapsed)
                    positions[setting_index].append(position)
                    if results[setting_index] is not None and results[setting_index] != result:
                        raise ArithmeticError("Repeated exact property evaluation changed its result")
                    results[setting_index] = result
            for i, (strategy, tolerance, budget) in enumerate(settings):
                result = results[i]
                if result["status"] == "accepted" and candidate["high_order_path_status"] == "unsafe":
                    raise ArithmeticError("A safety predicate admitted a reference-certified unsafe path")
                if strategy != "sacbf_relaxed" and result["status"] == "rejected" and candidate["high_order_path_status"] == "safe":
                    raise ArithmeticError("A negative witness contradicts a reference-certified safe path")
                rows.append({"case": evidence["name"], "case_index": case_index, "candidate_index": candidate_index,
                             "action_exact": candidate["action_exact"], "reference_status": candidate["high_order_path_status"],
                             "strategy": strategy, "tolerance_exact": str(tolerance) if tolerance is not None else None,
                             "budget": budget, "result": result, "predicate_ns_median": median(measurements[i]),
                             "all_predicate_ns": measurements[i], "sample_positions": positions[i]})
            by_setting = dict(zip(settings, results))
            if "minimum" in strategies and "sign" in strategies:
                for tolerance in tolerances:
                    for budget in budgets:
                        minimum, sign = (by_setting[(s, tolerance, budget)] for s in ("minimum", "sign"))
                        if minimum["status"] != sign["status"] or sign["subdivisions"] > minimum["subdivisions"]:
                            raise ArithmeticError("Matched sign/minimum proof-prefix consistency failed")
    groups = []
    for strategy, tolerance, budget in settings:
        group = [r for r in rows if (r["strategy"], r["tolerance_exact"], r["budget"]) ==
                 (strategy, str(tolerance) if tolerance is not None else None, budget)]
        if not group:
            continue
        groups.append({"strategy": strategy, "tolerance_exact": str(tolerance) if tolerance is not None else None,
                       "budget": budget, "queries": len(group),
                       "accepted": sum(r["result"]["status"] == "accepted" for r in group),
                       "rejected": sum(r["result"]["status"] == "rejected" for r in group),
                       "unknown": sum(r["result"]["status"] == "unknown" for r in group),
                       "reference_safe_excluded": sum(r["reference_status"] == "safe" and r["result"]["status"] == "rejected" for r in group),
                       "reference_safe_unresolved": sum(r["reference_status"] == "safe" and r["result"]["status"] == "unknown" for r in group),
                       "accepted_reference_unknown": sum(r["reference_status"] == "unknown" and r["result"]["status"] == "accepted" for r in group),
                       "polynomial_checks": sum(len(r["result"].get("proofs", [])) for r in group),
                       "geometric_implications_proved": sum(p["status"] == "safe" for r in group
                                                            for p in r["result"].get("geometric_implications", [])),
                       "total_subdivisions": sum(r["result"]["subdivisions"] for r in group),
                       "median_per_control_ns": median(r["predicate_ns_median"] for r in group)})
    comparisons = []
    if "sign" in strategies and "auxiliary_sign" in strategies:
        for tolerance in tolerances:
            for budget in budgets:
                paired = {}
                for row in rows:
                    if row["tolerance_exact"] == str(tolerance) and row["budget"] == budget and row["strategy"] in ("sign", "auxiliary_sign"):
                        paired.setdefault((row["case_index"], row["candidate_index"]), {})[row["strategy"]] = row["result"]["status"]
                transitions = {}
                for decisions in paired.values():
                    transition = (decisions["sign"], decisions["auxiliary_sign"])
                    transitions[transition] = transitions.get(transition, 0)+1
                comparisons.append({"tolerance_exact": str(tolerance), "budget": budget, "controls": len(paired),
                                    "transitions": [{"dual_sign": a, "auxiliary_sign": b, "controls": count}
                                                    for (a, b), count in sorted(transitions.items())]})
    return {"seed": seed, "repeats": repeats, "cases": len(reference), "strategies": strategies,
            "applicable_cases": sum(c["hocbf_applicable"] for c in reference),
            "reference": reference, "groups": groups, "measurements": rows, "decision_comparisons": comparisons,
            "scope": "Fixed-state/control h and psi evaluation plus evidence assembly; excludes search, selection and offline reference costs"}
