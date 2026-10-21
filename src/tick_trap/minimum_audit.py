"""Offline cross-check of archived planar minimum enclosures, without timing."""

import json

from .algebraic_minimum import enclose_algebraic_minimum
from .algebraic_reference import exact_sign_reference
from .allocation_audit import allocation_audit
from .barrier_paths import auxiliary_polynomial
from .certification_study import _integer
from .dynamics import Circle, PlanarState
from .numbers import positive, q, vector2
from .polynomial import certify_minimum


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _bernstein(cert):
    return {"status": cert.status, "lower_exact": str(cert.lower), "upper_exact": str(cert.upper),
            "witness_time_exact": str(cert.witness_time), "subdivisions": cert.subdivisions}


def _overlap(left, right):
    lower = max(q(left["lower_exact"]), q(right["lower_exact"]))
    upper = min(q(left["upper_exact"]), q(right["upper_exact"]))
    if lower > upper:
        raise ArithmeticError("Independent and Bernstein minimum enclosures are disjoint")
    return {"lower_exact": str(lower), "upper_exact": str(upper)}


def minimum_reference_audit(spec, study, settings):
    """Rebuild source commands and audit original and matched minimum bounds.

    The source predicate results are replayed separately first. Original saved
    high-precision Bernstein enclosures, which the allocation replay does not
    check, are reconstructed here too. No historical timing is used or changed.
    Repeated polynomials at the same period/reference settings share a query,
    with all physical/property uses retained.
    """
    if not isinstance(settings, dict) or set(settings)-{"tolerances", "budgets"}:
        raise ValueError("Unknown minimum audit field")
    tolerances, budgets = settings.get("tolerances", ["1e-12"]), settings.get("budgets", [0, 8, 64])
    if not all(isinstance(v, list) and v for v in (tolerances, budgets)):
        raise ValueError("Require nonempty tolerances and budgets")
    tolerances = [positive(t, "tolerance") for t in tolerances]
    budgets = [_integer(b, "budget") for b in budgets]
    if len(set(tolerances)) != len(tolerances) or len(set(budgets)) != len(budgets):
        raise ValueError("Duplicate numerical settings")
    replay = allocation_audit(spec, study)
    queries, indexed, uses, controls = [], {}, 0, 0
    for case_index, case in enumerate(spec["cases"]):
        config = spec.get("base", {}) | case
        saved = study["reference"][case_index]
        if not saved["hocbf_applicable"]:
            continue
        state = PlanarState(config["p"], config["v"])
        obstacles = [o if isinstance(o, Circle) else Circle(**o) for o in config["obstacles"]]
        duration = positive(config["duration"])
        gain = positive(config.get("lambda1", 2))
        reference_tolerance = positive(config.get("tolerance", "1e-12"))
        reference_budget = _integer(config.get("max_subdivisions", 4096), "reference budget")
        for candidate_index, candidate in enumerate(saved["candidates"]):
            controls += 1
            action = vector2(candidate["action_exact"])
            for obstacle_index, obstacle in enumerate(obstacles):
                h = obstacle.polynomial(state, action)
                for name, polynomial, field in (("h", h, "certificates"),
                                                 ("psi", auxiliary_polynomial(h, gain), "auxiliary_certificates")):
                    old = candidate[field][obstacle_index]
                    key = (polynomial, duration, reference_tolerance, reference_budget)
                    if key not in indexed:
                        rebuilt = _bernstein(certify_minimum(polynomial, duration, reference_tolerance, reference_budget))
                        sign = exact_sign_reference(polynomial, duration)
                        query = {"query_index": len(queries), "polynomial_exact": [str(c) for c in polynomial],
                                 "duration_exact": str(duration), "reference_tolerance_exact": str(reference_tolerance),
                                 "reference_budget": reference_budget, "archived_bernstein": rebuilt,
                                 "complete_sign_reference": sign, "uses": [], "assessments": []}
                        for tolerance in tolerances:
                            for budget in budgets:
                                independent = enclose_algebraic_minimum(polynomial, duration, tolerance, budget)
                                bernstein = certify_minimum(polynomial, duration, tolerance, budget)
                                matched = _bernstein(bernstein) | {"precision_reached": bernstein.precision_reached,
                                                                  "budget_exhausted": bernstein.budget_exhausted}
                                for result in (independent, matched):
                                    if result["status"] != "unknown" and result["status"] != sign["status"]:
                                        raise ArithmeticError("Minimum sign contradicts the complete algebraic sign reference")
                                query["assessments"].append({"tolerance_exact": str(tolerance), "budget": budget,
                                                             "stationary": independent, "matched_bernstein": matched,
                                                             "matched_intersection": _overlap(independent, matched),
                                                             "archived_intersection": _overlap(independent, rebuilt)})
                        indexed[key] = len(queries)
                        queries.append(query)
                    query = queries[indexed[key]]
                    if not _same(old, query["archived_bernstein"]):
                        raise ValueError("Archived Bernstein minimum does not match exact reconstruction")
                    query["uses"].append({"case": config["name"], "case_index": case_index,
                                          "candidate_index": candidate_index, "obstacle_index": obstacle_index,
                                          "property": name, "action_exact": [str(c) for c in action]})
                    uses += 1
    groups = []
    for tolerance in tolerances:
        for budget in budgets:
            rows = [(query, a) for query in queries for a in query["assessments"]
                    if (a["tolerance_exact"], a["budget"]) == (str(tolerance), budget)]
            group = {"tolerance_exact": str(tolerance), "budget": budget, "unique_queries": len(rows),
                     "overlapping_matched_enclosures": len(rows), "overlapping_archived_enclosures": len(rows)}
            for label, field in (("stationary", "stationary"), ("bernstein", "matched_bernstein")):
                group[label] = {"safe": sum(a[field]["status"] == "safe" for query, a in rows),
                                "unsafe": sum(a[field]["status"] == "unsafe" for query, a in rows),
                                "unknown": sum(a[field]["status"] == "unknown" for query, a in rows),
                                "precision_reached": sum(a[field]["precision_reached"] for query, a in rows),
                                "budget_exhausted": sum(a[field]["budget_exhausted"] for query, a in rows),
                                "subdivisions": sum(a[field]["subdivisions"] for query, a in rows)}
            group["stationary"]["root_count_calls"] = sum(a["stationary"]["root_count_calls"] for query, a in rows)
            groups.append(group)
    return {"cases": len(spec["cases"]), "applicable_cases": study["applicable_cases"],
            "controls": controls, "property_uses": uses, "unique_queries": len(queries),
            "source_predicate_replay": {k: replay[k] for k in ("status", "property_configurations", "replayed_queries")},
            "groups": groups, "queries": queries,
            "scope": "Deterministic offline independent minimum-enclosure cross-check on exact archived planar h and psi polynomials. Complete signs, minimum widths, split counts and execution decisions remain separate; no timing or equal primitive-work claim"}


def verify_minimum_reference_audit(spec, study, settings, stored):
    expected = minimum_reference_audit(spec, study, settings)
    if not _same(stored, expected):
        raise ValueError("Minimum audit does not match exact regeneration")
    return {"status": "verified", "controls": expected["controls"], "property_uses": expected["property_uses"],
            "unique_queries": expected["unique_queries"],
            "enclosure_comparisons": sum(len(q["assessments"]) for q in expected["queries"]),
            "scope": "Deterministic replay of independent and Bernstein bounds, original saved minima and exact source predicates; not a formal program proof or online certificate substitution"}
