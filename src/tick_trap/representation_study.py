"""Matched polynomial/control diagnostics for representation-dependent widths."""

from collections import Counter
from itertools import product
import json

from .algebraic_reference import exact_sign_reference
from .representation_audit import METHODS, TIME_BASES, _exact, representation_certificate, transformed_polynomial


def _same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Require nonnegative integer indices and budgets")
    return value


def _decision(statuses):
    statuses = tuple(statuses)
    return "rejected" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "accepted"


def representation_study(catalog, settings):
    if not isinstance(settings, dict) or set(settings)-{"scales", "tolerances", "budgets", "time_bases", "methods"}:
        raise ValueError("Unknown representation study setting")
    scales, tolerances = settings.get("scales", ["1e-6", "1", "1e6"]), settings.get("tolerances", ["1e-12"])
    budgets, bases = settings.get("budgets", [0, 8, 64]), settings.get("time_bases", list(TIME_BASES))
    methods = settings.get("methods", list(METHODS))
    if not all(isinstance(v, list) and v for v in (scales, tolerances, budgets, bases, methods)):
        raise ValueError("Study settings must be nonempty lists")
    scales, tolerances = [_exact(s) for s in scales], [_exact(t) for t in tolerances]
    budgets = [_integer(b) for b in budgets]
    if (any(v <= 0 for v in [*scales, *tolerances])
            or any(not isinstance(b, str) or b not in TIME_BASES for b in bases)
            or any(not isinstance(m, str) or m not in METHODS for m in methods)
            or any(len(set(v)) != len(v) for v in (scales, tolerances, budgets, bases, methods))):
        raise ValueError("Invalid or duplicated representation settings")
    queries = catalog["queries"]
    if not isinstance(queries, list) or not queries or _integer(catalog["unique_queries"]) != len(queries):
        raise ValueError("Invalid source query coverage")
    # A location uniquely names one obstacle/property use; deduplication of equal
    # polynomials must retain every such use without duplicating a control.
    controls, locations, case_names, uses = {}, set(), {}, 0
    for index, query in enumerate(queries):
        if _integer(query["query_index"]) != index or not query["uses"]:
            raise ValueError("Noncanonical query index or missing property uses")
        for use in query["uses"]:
            case, candidate, obstacle = (_integer(use[k]) for k in ("case_index", "candidate_index", "obstacle_index"))
            name, property_name = use["case"], use["property"]
            action = tuple(_exact(c) for c in use["action_exact"])
            location = (case, candidate, obstacle, property_name)
            if (not isinstance(name, str) or not name or property_name not in ("h", "psi") or len(action) != 2
                    or location in locations or case_names.get(case, name) != name):
                raise ValueError("Invalid or duplicated source property use")
            case_names[case] = name
            locations.add(location)
            control = controls.setdefault((case, candidate), {"case": name, "case_index": case,
                        "candidate_index": candidate, "action_exact": [str(c) for c in action], "queries": []})
            if tuple(_exact(c) for c in control["action_exact"]) != action:
                raise ValueError("Property uses disagree on the physical action")
            control["queries"].append(index)
            uses += 1
    for case, candidate, obstacle, prop in locations:
        if (case, candidate, obstacle, "psi" if prop == "h" else "h") not in locations:
            raise ValueError("A control is missing its geometric or auxiliary property")
    if (_integer(catalog["controls"]) != len(controls) or _integer(catalog["property_uses"]) != uses
            or _integer(catalog["applicable_cases"]) != len(case_names)
            or any(i >= _integer(catalog["cases"]) for i in case_names)):
        raise ValueError("Source control/property coverage counts disagree")
    controls = [controls[k] for k in sorted(controls)]
    records, baseline_results, by_setting, unique_calls = [], {}, {}, 0
    for index, query in enumerate(queries):
        polynomial, duration = tuple(_exact(c) for c in query["polynomial_exact"]), _exact(query["duration_exact"])
        original_sign = exact_sign_reference(polynomial, duration)
        if not _same(original_sign, query["complete_sign_reference"]):
            raise ValueError("Complete source sign evidence does not regenerate")
        cache = {}

        def get(method, tolerance, budget, scale, basis):
            nonlocal unique_calls
            # Unit and physical coordinates coincide for a unit physical hold.
            basis = "physical" if duration == 1 else basis
            key = (method, tolerance, budget, scale, basis)
            if key not in cache:
                cache[key] = representation_certificate(method, polynomial, duration, tolerance, budget, scale, basis)
                unique_calls += 1
            return cache[key]

        def pack(result):
            return {k: v for k, v in result.items() if k not in
                    ("polynomial_exact", "duration_exact", "time_factor_exact", "value_scale_exact")}

        baselines = []
        for method, tolerance, budget in product(methods, tolerances, budgets):
            base = get(method, tolerance, budget, _exact(1), "physical")
            key = (method, str(tolerance), budget)
            baseline_results.setdefault(key, {})[index] = base
            baselines.append({"method": method, "base_tolerance_exact": str(tolerance), "budget": budget, **pack(base)})
        representations = []
        for scale, basis in product(scales, bases):
            p, end, time_factor, _ = transformed_polynomial(polynomial, duration, scale, basis)
            sign = exact_sign_reference(p, end)
            if sign["status"] != original_sign["status"]:
                raise ArithmeticError("Positive representation changed the complete sign")
            evaluations = []
            for method, tolerance, budget in product(methods, tolerances, budgets):
                baseline = baseline_results[(method, str(tolerance), budget)][index]
                policies = {}
                for policy, width in (("fixed_absolute", tolerance), ("equivalent_width", scale*tolerance)):
                    result = get(method, width, budget, scale, basis)
                    same = _same(result["original_coordinates"], baseline["original_coordinates"])
                    if policy == "equivalent_width" and not same:
                        raise ArithmeticError("Equivalent width failed exact representation covariance")
                    physical = get(method, width, budget, scale, "physical")
                    if not _same(result["original_coordinates"], physical["original_coordinates"]):
                        raise ArithmeticError("Pure time substitution changed the converted certificate")
                    status = result["certificate"]["status"]
                    if status != "unknown" and status != original_sign["status"]:
                        raise ArithmeticError("A represented certificate contradicts exact sign truth")
                    base_bounds, converted = baseline["original_coordinates"], result["original_coordinates"]
                    if max(_exact(base_bounds["lower_exact"]), _exact(converted["lower_exact"])) > min(
                            _exact(base_bounds["upper_exact"]), _exact(converted["upper_exact"])):
                        raise ArithmeticError("Converted minimum enclosures are disjoint")
                    packed = pack(result) | {"matches_baseline": same, "time_substitution_matches": True}
                    policies[policy] = packed
                    key = (method, str(tolerance), budget, str(scale), basis, policy)
                    by_setting.setdefault(key, {})[index] = packed
                evaluations.append({"method": method, "base_tolerance_exact": str(tolerance),
                                    "budget": budget, "policies": policies})
            representations.append({"scale_exact": str(scale), "time_basis": basis,
                                    "polynomial_exact": [str(c) for c in p], "duration_exact": str(end),
                                    "time_factor_exact": str(time_factor), "complete_sign_reference": sign,
                                    "evaluations": evaluations})
        records.append({"query_index": index, "polynomial_exact": [str(c) for c in polynomial],
                        "duration_exact": str(duration), "uses": query["uses"], "complete_sign_reference": original_sign,
                        "baselines": baselines, "representations": representations})
    for control in controls:
        control["reference_status"] = "unsafe" if any(records[i]["complete_sign_reference"]["status"] == "unsafe"
                                                       for i in control["queries"]) else "safe"
    groups = []
    for key, results in by_setting.items():
        method, tolerance, budget, scale, basis, policy = key
        baseline = baseline_results[(method, tolerance, budget)]
        transitions = Counter((baseline[i]["certificate"]["status"], r["certificate"]["status"]) for i, r in results.items())
        control_transitions, accepted_safe, rejected_unsafe, unknown_safe, unknown_unsafe = Counter(), 0, 0, 0, 0
        for control in controls:
            old = _decision(baseline[i]["certificate"]["status"] for i in control["queries"])
            decision = _decision(results[i]["certificate"]["status"] for i in control["queries"])
            truth = control["reference_status"]
            if (decision == "accepted" and truth == "unsafe") or (decision == "rejected" and truth == "safe"):
                raise ArithmeticError("Joint classification contradicts the required h-and-psi property")
            control_transitions[(old, decision)] += 1
            accepted_safe += decision == "accepted" and truth == "safe"
            rejected_unsafe += decision == "rejected" and truth == "unsafe"
            unknown_safe += decision == "unknown" and truth == "safe"
            unknown_unsafe += decision == "unknown" and truth == "unsafe"
        groups.append({"method": method, "base_tolerance_exact": tolerance, "budget": budget,
                       "scale_exact": scale, "time_basis": basis, "tolerance_policy": policy,
                       "polynomials": len(results), "controls": len(controls),
                       "safe": sum(r["certificate"]["status"] == "safe" for r in results.values()),
                       "unsafe": sum(r["certificate"]["status"] == "unsafe" for r in results.values()),
                       "unknown": sum(r["certificate"]["status"] == "unknown" for r in results.values()),
                       "precision_reached": sum(r["certificate"]["precision_reached"] for r in results.values()),
                       "same_converted_certificate": sum(r["matches_baseline"] for r in results.values()),
                       "total_subdivisions": sum(r["certificate"]["subdivisions"] for r in results.values()),
                       "root_count_calls": sum(r["certificate"].get("root_count_calls", 0) for r in results.values()),
                       "accepted_safe_controls": accepted_safe, "rejected_unsafe_controls": rejected_unsafe,
                       "unknown_safe_controls": unknown_safe, "unknown_unsafe_controls": unknown_unsafe,
                       "polynomial_transitions": [{"baseline": a, "represented": b, "queries": n} for (a, b), n in sorted(transitions.items())],
                       "control_transitions": [{"baseline": a, "represented": b, "controls": n} for (a, b), n in sorted(control_transitions.items())]})
    return {"source_queries": len(records), "property_uses": uses, "controls": controls,
            "joint_truth_counts": dict(Counter(c["reference_status"] for c in controls)),
            "unique_backend_evaluations": unique_calls, "groups": groups, "queries": records,
            "scope": "Offline exact-rational representation audit of fixed h-and-psi polynomial queries; individual per-polynomial split allowances, no action search, controller changes, timing measurement, equal primitive-work guarantee or novelty claim"}


def verify_representation_study(catalog, settings, stored):
    expected = representation_study(catalog, settings)
    if not _same(stored, expected):
        raise ValueError("Representation evidence does not match exact regeneration")
    return {"status": "verified", "source_queries": expected["source_queries"],
            "controls": len(expected["controls"]), "property_uses": expected["property_uses"],
            "groups": len(expected["groups"]),
            "certificate_evaluations": sum(g["polynomials"] for g in expected["groups"]),
            "scope": "Deterministic regeneration of represented inputs, raw/converted bounds, tolerance policies, work counts and joint classifications; no online status is changed"}
