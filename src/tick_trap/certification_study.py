"""Paired property-evaluation costs at fixed states and fixed candidate controls."""

from random import Random
from itertools import combinations
from statistics import median
from time import perf_counter_ns

from .barrier_paths import certify_auxiliary_path
from .algebraic_reference import exact_sign_reference
from .dynamics import Circle, PlanarState
from .numbers import positive, vector2
from .planar_audit import audit_cases
from .polynomial import certify_minimum, certify_sign
from .sampling import sacbf_assessment

STRATEGIES = ("sacbf_relaxed", "minimum", "sign", "auxiliary_sign", "sturm")
PARAMETER_FREE = ("sacbf_relaxed", "sturm")


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _evaluate(strategy, state, action, obstacles, duration, lambda1, lambda2, tolerance, budget,
              budget_scope="per_polynomial"):
    if strategy not in STRATEGIES:
        raise ValueError("Unsupported property-evaluation strategy")
    if strategy == "sacbf_relaxed":
        assessments = [sacbf_assessment(state, action, o, duration, lambda1, lambda2, True) for o in obstacles]
        return {"status": "accepted" if all(a["accepted"] for a in assessments) else "rejected",
                "subdivisions": 0, "assessments": assessments}
    if strategy == "sturm":
        proofs = []
        for obstacle in obstacles:
            h = obstacle.polynomial(state, action)
            psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
            for name, polynomial in (("h", h), ("psi", psi)):
                evidence = exact_sign_reference(polynomial, duration)
                proofs.append({"property": name, "status": evidence["status"], "goal": "exact_sign",
                               "evidence": evidence})
        return {"status": "rejected" if any(p["status"] == "unsafe" for p in proofs) else "accepted",
                "subdivisions": 0, "proofs": proofs,
                "work_scope": "Exact rational algebra; no subdivision budget or hard runtime bound"}
    certifier = certify_sign if strategy == "sign" else certify_minimum
    proofs, implications, used = [], [], 0
    def available():
        return budget if budget_scope == "per_polynomial" else budget-used
    for obstacle in obstacles:
        h = obstacle.polynomial(state, action)
        if strategy == "auxiliary_sign":
            cert, implication = certify_auxiliary_path(h, lambda1, duration, tolerance, available())
            implications.append(implication)
            computed = [("psi", cert)]
        else:
            psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
            computed = []
            for name, polynomial in (("h", h), ("psi", psi)):
                cert = certifier(polynomial, duration, tolerance, available())
                computed.append((name, cert))
                used += cert.subdivisions
        if strategy == "auxiliary_sign":
            used += cert.subdivisions
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


def distribution(values):
    """Descriptive linear-interpolated empirical quantiles; no confidence claim."""
    values = sorted(values)
    if not values:
        return {"count": 0}
    def quantile(probability):
        index = (len(values)-1)*probability
        lower = int(index)
        return values[lower]+(values[min(lower+1, len(values)-1)]-values[lower])*(index-lower)
    return {"count": len(values), "min": values[0], "p10": quantile(.1), "p25": quantile(.25),
            "median": median(values), "p75": quantile(.75), "p90": quantile(.9),
            "p95": quantile(.95), "max": values[-1]}


def paired_comparisons(rows, strategies, tolerances, budgets):
    comparisons = []
    for tolerance in tolerances:
        for budget in budgets:
            matched = {}
            for row in rows:
                if row["strategy"] in PARAMETER_FREE or (row["tolerance_exact"], row["budget"]) == (str(tolerance), budget):
                    matched.setdefault((row["case_index"], row["candidate_index"]), {})[row["strategy"]] = row
            for baseline, candidate in combinations(strategies, 2):
                transitions, ratios, differences, repeated_ratios = {}, [], [], []
                case_ratios = {}
                for pair in matched.values():
                    a, b = pair[baseline], pair[candidate]
                    transition = (a["result"]["status"], b["result"]["status"])
                    transitions[transition] = transitions.get(transition, 0)+1
                    ratio = a["predicate_ns_median"]/b["predicate_ns_median"]
                    ratios.append(ratio)
                    differences.append(a["predicate_ns_median"]-b["predicate_ns_median"])
                    case_ratios.setdefault(a["case"], []).append(ratio)
                    repeated_ratios.extend(x/y for x, y in zip(a["all_predicate_ns"], b["all_predicate_ns"]))
                if ratios:
                    comparisons.append({"baseline": baseline, "candidate": candidate, "tolerance_exact": str(tolerance),
                                        "budget": budget, "controls": len(ratios),
                                        "transitions": [{"baseline": a, "candidate": b, "controls": n}
                                                        for (a, b), n in sorted(transitions.items())],
                                        "paired_median_time_ratio": distribution(ratios),
                                        "paired_median_difference_ns": distribution(differences),
                                        "paired_repeat_time_ratio": distribution(repeated_ratios),
                                        "per_case_paired_median_ratio": {name: distribution(v) for name, v in case_ratios.items()}})
    return comparisons


def certification_study(spec):
    """Time identical property queries; reference work is offline and separate.

    Every strategy targets both path properties at every obstacle; auxiliary_sign
    derives the geometric property rather than querying its polynomial sign.
    Repeated measurements are interleaved in a seeded shuffled order per control.
    The optional sturm comparator reruns the independent algebraic reference
    inside the measured region; it does not read cached offline answers or
    replace any online unknown. Its finite-degree algebra has no subdivision
    allowance, so its zero split count is not an equal-work comparison.
    Costs include polynomial/condition construction and exact evidence assembly,
    but exclude candidate generation, control selection and offline reference work.
    """
    if not isinstance(spec, dict) or set(spec)-{"base", "cases", "tolerances", "budgets", "repeats", "seed", "strategies", "budget_scope"}:
        raise ValueError("Unknown certification study field")
    strategies = spec.get("strategies", list(STRATEGIES[:3]))
    if (not isinstance(strategies, list) or not strategies or
            any(not isinstance(s, str) or s not in STRATEGIES for s in strategies) or len(set(strategies)) != len(strategies)):
        raise ValueError("strategies must be a nonempty list of distinct supported names")
    repeats = _integer(spec.get("repeats", 5), "repeats", 1)
    budget_scope = spec.get("budget_scope", "per_polynomial")
    if budget_scope not in ("per_polynomial", "per_control"):
        raise ValueError("budget_scope must be per_polynomial or per_control")
    seed = _integer(spec.get("seed", 20261019), "seed")
    tolerances, budgets = spec.get("tolerances", ["1e-10"]), spec.get("budgets", [256])
    if not all(isinstance(values, list) and values for values in (tolerances, budgets)):
        raise ValueError("tolerances and budgets must be nonempty lists")
    tolerances = [positive(t, "tolerance") for t in tolerances]
    budgets = [_integer(b, "budget") for b in budgets]
    if len(set(tolerances)) != len(tolerances) or len(set(budgets)) != len(budgets):
        raise ValueError("Duplicate tolerances or budgets would duplicate matched queries")
    reference = audit_cases({"base": spec.get("base", {}), "cases": spec.get("cases", [])})
    settings = ([(s, None, None) for s in strategies if s in PARAMETER_FREE] +
                [(s, t, b) for t in tolerances for b in budgets for s in strategies if s not in PARAMETER_FREE])
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
            start = perf_counter_ns()
            independent = []
            for obstacle in obstacles:
                h = obstacle.polynomial(state, action)
                psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
                independent.append({"h": exact_sign_reference(h, duration), "psi": exact_sign_reference(psi, duration)})
            independent_ns = perf_counter_ns()-start
            geometric_truth = "unsafe" if any(p["h"]["status"] == "unsafe" for p in independent) else "safe"
            auxiliary_truth = "unsafe" if any(p["psi"]["status"] == "unsafe" for p in independent) else "safe"
            truth = "unsafe" if "unsafe" in (geometric_truth, auxiliary_truth) else "safe"
            for field, actual in (("trajectory_status", geometric_truth), ("auxiliary_status", auxiliary_truth),
                                  ("high_order_path_status", truth)):
                if candidate[field] != "unknown" and candidate[field] != actual:
                    raise ArithmeticError("Independent algebraic reference contradicts a resolved Bernstein sign")
            candidate.update({"independent_evidence": independent, "independent_reference_ns": independent_ns,
                              "independent_high_order_status": truth, "independent_geometric_status": geometric_truth,
                              "independent_auxiliary_status": auxiliary_truth})
            measurements = [[] for _ in settings]
            positions = [[] for _ in settings]
            results = [None for _ in settings]
            for _ in range(repeats):
                order = list(range(len(settings)))
                rng.shuffle(order)
                for position, setting_index in enumerate(order):
                    strategy, tolerance, budget = settings[setting_index]
                    start = perf_counter_ns()
                    result = _evaluate(strategy, state, action, obstacles, duration, lambda1, lambda2, tolerance, budget, budget_scope)
                    elapsed = perf_counter_ns()-start
                    measurements[setting_index].append(elapsed)
                    positions[setting_index].append(position)
                    if results[setting_index] is not None and results[setting_index] != result:
                        raise ArithmeticError("Repeated exact property evaluation changed its result")
                    results[setting_index] = result
            for i, (strategy, tolerance, budget) in enumerate(settings):
                result = results[i]
                if result["status"] == "accepted" and truth == "unsafe":
                    raise ArithmeticError("A safety predicate admitted a reference-certified unsafe path")
                if strategy != "sacbf_relaxed" and result["status"] == "rejected" and truth == "safe":
                    raise ArithmeticError("A negative witness contradicts a reference-certified safe path")
                rows.append({"case": evidence["name"], "case_index": case_index, "candidate_index": candidate_index,
                             "action_exact": candidate["action_exact"], "reference_status": candidate["high_order_path_status"],
                             "independent_reference_status": truth, "geometric_reference_status": geometric_truth,
                             "auxiliary_reference_status": auxiliary_truth,
                             "strategy": strategy, "tolerance_exact": str(tolerance) if tolerance is not None else None,
                             "budget": budget, "result": result, "predicate_ns_median": median(measurements[i]),
                             "all_predicate_ns": measurements[i], "sample_positions": positions[i]})
            by_setting = dict(zip(settings, results))
            if budget_scope == "per_polynomial" and "minimum" in strategies and "sign" in strategies:
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
                       "accepted_safe_controls": sum(r["independent_reference_status"] == "safe" and r["result"]["status"] == "accepted" for r in group),
                       "accepted_unsafe_controls": sum(r["independent_reference_status"] == "unsafe" and r["result"]["status"] == "accepted" for r in group),
                       "rejected_unsafe_controls": sum(r["independent_reference_status"] == "unsafe" and r["result"]["status"] == "rejected" for r in group),
                       "rejected_safe_controls": sum(r["independent_reference_status"] == "safe" and r["result"]["status"] == "rejected" for r in group),
                       "unknown_safe_controls": sum(r["independent_reference_status"] == "safe" and r["result"]["status"] == "unknown" for r in group),
                       "unknown_unsafe_controls": sum(r["independent_reference_status"] == "unsafe" and r["result"]["status"] == "unknown" for r in group),
                       "geometrically_unsafe_rejected": sum(r["geometric_reference_status"] == "unsafe" and r["result"]["status"] == "rejected" for r in group),
                       "reference_safe_excluded": sum(r["reference_status"] == "safe" and r["result"]["status"] == "rejected" for r in group),
                       "reference_safe_unresolved": sum(r["reference_status"] == "safe" and r["result"]["status"] == "unknown" for r in group),
                       "accepted_reference_unknown": sum(r["reference_status"] == "unknown" and r["result"]["status"] == "accepted" for r in group),
                       "polynomial_checks": sum(len(r["result"].get("proofs", [])) for r in group),
                       "geometric_implications_proved": sum(p["status"] == "safe" for r in group
                                                            for p in r["result"].get("geometric_implications", [])),
                       "total_subdivisions": sum(r["result"]["subdivisions"] for r in group),
                       "median_per_control_ns": median(r["predicate_ns_median"] for r in group),
                       "per_control_median_ns_distribution": distribution([r["predicate_ns_median"] for r in group]),
                       "all_repeat_ns_distribution": distribution([t for r in group for t in r["all_predicate_ns"]])})
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
    return {"seed": seed, "repeats": repeats, "cases": len(reference), "strategies": strategies, "budget_scope": budget_scope,
            "applicable_cases": sum(c["hocbf_applicable"] for c in reference),
            "reference": reference, "groups": groups, "measurements": rows, "decision_comparisons": comparisons,
            "paired_comparisons": paired_comparisons(rows, strategies, tolerances, budgets),
            "reference_scope": "Independent exact square-free/Sturm signs of h AND psi; original bounded Bernstein answers retained separately",
            "scope": "Fixed-state/control h and psi evaluation plus evidence assembly; excludes search, selection and offline reference costs"}
