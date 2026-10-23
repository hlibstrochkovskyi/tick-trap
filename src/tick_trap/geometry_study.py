"""Matched one-hold geometric predicates, with auxiliary preservation kept separate.

This offline study reuses a recorded candidate cohort, not its cached decisions
or runtimes. Tube methods are elementary sufficient conditions, not SSCBF/MPC.
"""

from collections import Counter
import json
from random import Random
from statistics import median
from time import perf_counter_ns

from .algebraic_reference import exact_sign_reference
from .barrier_paths import auxiliary_polynomial
from .certification_study import _integer, distribution, paired_comparisons
from .dynamics import Circle, PlanarState
from .numbers import positive, vector2
from .planar_control import candidate_actions, hocbf_constraints, segment_minimum
from .polynomial import certify_minimum, certify_sign
from .segment_audit import ASSUMPTIONS, _exact, chord_tube_certificate
from .timing_evidence import verify_timing_evidence

METHODS = ("command_tube", "box_tube", "minimum", "sign", "sturm")
PARAMETER_FREE = ("command_tube", "box_tube", "sturm")
SCOPE = ("Offline fixed-control geometric h>=0 comparison on an inherited cohort; "
         "psi preservation and diagnostic endpoint/chord checks remain separate. "
         "Includes evidence construction, excludes cohort/reference work; no controller, "
         "SSCBF reproduction, equal primitive-work, hard deadline or novelty claim")


def _same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _decision(statuses):
    statuses = tuple(statuses)
    return "rejected" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "accepted"


def _settings(spec):
    if not isinstance(spec, dict) or set(spec)-{"strategies", "tolerances", "budgets", "repeats", "seed"}:
        raise ValueError("Unknown geometry study setting")
    methods = spec.get("strategies", list(METHODS))
    widths, budgets = spec.get("tolerances", ["1e-12"]), spec.get("budgets", [0, 8, 64])
    if not all(isinstance(v, list) and v for v in (methods, widths, budgets)):
        raise ValueError("Require nonempty method and numerical settings")
    widths = [positive(_exact(t), "tolerance") for t in widths]
    budgets = [_integer(b, "budget") for b in budgets]
    if (any(not isinstance(m, str) or m not in METHODS for m in methods)
            or any(len(v) != len(set(v)) for v in (methods, widths, budgets))):
        raise ValueError("Invalid or duplicate geometry setting")
    repeats, seed = _integer(spec.get("repeats", 5), "repeats", 1), _integer(spec.get("seed", 20261023), "seed")
    settings = ([(m, None, None) for m in methods if m in PARAMETER_FREE] +
                [(m, t, b) for t in widths for b in budgets for m in methods if m not in PARAMETER_FREE])
    return methods, widths, budgets, repeats, seed, settings


def _reference(source_spec, source_study):
    cases, saved = source_spec["cases"], source_study["reference"]
    if not cases or len(cases) != len(saved):
        raise ValueError("Source case coverage differs")
    references, names = [], set()
    allowed = {"name", "p", "v", "nominal", "obstacles", "duration", "a_max", "lambda1", "lambda2",
               "gamma", "grid_points", "command_quantum", "tolerance", "max_subdivisions"}
    for case, old in zip(cases, saved):
        config = source_spec.get("base", {}) | case
        if set(config)-allowed or config["name"] in names or config["name"] != old["name"]:
            raise ValueError("Unsupported or inconsistent source case")
        names.add(config["name"])
        state = PlanarState(config["p"], config["v"])
        obstacles = tuple(Circle(**o) for o in config["obstacles"])
        if not obstacles:
            raise ValueError("Geometry comparison requires static circular obstacles")
        duration, a_max = positive(config["duration"]), positive(config["a_max"])
        gain = positive(config.get("lambda1", 2))
        _, domains = hocbf_constraints(state, obstacles, gain, config.get("lambda2", 2))
        applicable = all(d["in_domain"] for d in domains)
        if not all(_exact(d["h_exact"]) >= 0 for d in domains) or applicable != old["hocbf_applicable"]:
            raise ValueError("Source initial-domain labels do not regenerate")
        actions = candidate_actions(config["nominal"], state, duration, a_max,
                                    config.get("grid_points", 5), config.get("command_quantum", "1e-6"))
        if (len(actions) != _integer(old["candidate_count"], "candidate count")
                or [list(map(str, a)) for a in actions] != [c["action_exact"] for c in old["candidates"]]):
            raise ValueError("Source candidate coverage or ordering differs")
        candidates = []
        if applicable:
            for action, previous in zip(actions, old["candidates"]):
                evidence, chords = [], []
                sampled = True
                for obstacle in obstacles:
                    h = obstacle.polynomial(state, action)
                    evidence.append({"h": exact_sign_reference(h, duration),
                                     "psi": exact_sign_reference(auxiliary_polynomial(h, gain), duration)})
                    chords.append(str(segment_minimum(state, action, obstacle, duration)))
                    sampled &= h[0] >= 0 and sum(c*duration**i for i, c in enumerate(h)) >= 0
                geometry = "safe" if all(e["h"]["status"] == "safe" for e in evidence) else "unsafe"
                auxiliary = "safe" if all(e["psi"]["status"] == "safe" for e in evidence) else "unsafe"
                joint = "safe" if geometry == auxiliary == "safe" else "unsafe"
                if (not _same(evidence, previous["independent_evidence"])
                        or any(previous[field] != value for field, value in
                               (("independent_geometric_status", geometry), ("independent_auxiliary_status", auxiliary),
                                ("independent_high_order_status", joint)))):
                    raise ValueError("Source polynomial sign evidence does not regenerate")
                candidates.append({"action_exact": list(map(str, action)), "independent_evidence": evidence,
                                   "geometric_status": geometry, "auxiliary_status": auxiliary, "joint_status": joint,
                                   "sampled_status": "safe" if sampled else "unsafe",
                                   "chord_status": "safe" if all(_exact(m) >= 0 for m in chords) else "unsafe",
                                   "chord_minima_exact": chords})
        references.append({"name": config["name"], "input": config, "initial_domains": domains,
                           "hocbf_applicable": applicable, "candidate_count": len(actions), "candidates": candidates})
    if sum(r["hocbf_applicable"] for r in references) != source_study["applicable_cases"]:
        raise ValueError("Source applicable-case coverage differs")
    return references


def evaluate_geometry(method, state, action, obstacles, duration, a_max, tolerance=None, budget=None):
    """Measured predicate only; receives no saved reference or cached answers.

    A bounded method shares its split allowance over all obstacles in order.
    Every obstacle is checked even after an unsafe witness. Free methods have
    no comparable split allowance or proven execution-time bound.
    """
    if method not in METHODS:
        raise ValueError("Unknown geometric predicate")
    duration, a_max = positive(_exact(duration)), positive(_exact(a_max))
    action = vector2(tuple(_exact(x) for x in action))
    if max(abs(x) for x in action) > a_max:
        raise ValueError("Action lies outside the recorded actuator box")
    proofs, used = [], 0
    for obstacle in obstacles:
        if method in ("command_tube", "box_tube"):
            evidence = chord_tube_certificate(state, action, obstacle, duration, a_max,
                                              "command" if method == "command_tube" else "actuator_box")
            proof = {"property": "h", "status": evidence["status"], "goal": "tube_sufficiency", "evidence": evidence}
        else:
            h = obstacle.polynomial(state, action)
            if method == "sturm":
                evidence = exact_sign_reference(h, duration)
                proof = {"property": "h", "status": evidence["status"], "goal": "exact_sign", "evidence": evidence}
            else:
                certifier = certify_minimum if method == "minimum" else certify_sign
                c = certifier(h, duration, tolerance, budget-used)
                used += c.subdivisions
                proof = {"property": "h", "status": c.status, "goal": c.goal,
                         "lower_exact": str(c.lower), "upper_exact": str(c.upper),
                         "witness_time_exact": str(c.witness_time), "subdivisions": c.subdivisions,
                         "precision_reached": c.precision_reached, "budget_exhausted": c.budget_exhausted,
                         "stopping_reason": c.stopping_reason}
        proofs.append(proof)
    return {"status": _decision(p["status"] for p in proofs), "subdivisions": used, "proofs": proofs}


def _assemble(reference, rows, settings):
    methods, widths, budgets, repeats, seed, schedule = settings
    controls = [c for r in reference for c in r["candidates"]]
    diagnostics = {}
    for key in ("sampled_status", "chord_status"):
        transitions = Counter((c[key], c["geometric_status"]) for c in controls)
        diagnostics[key] = [{"diagnostic": a, "geometry": b, "controls": n} for (a, b), n in sorted(transitions.items())]
    groups = []
    for method, width, budget in schedule:
        selected = [r for r in rows if (r["strategy"], r["tolerance_exact"], r["budget"]) ==
                    (method, str(width) if width is not None else None, budget)]
        if not selected:
            continue
        group = {"strategy": method, "tolerance_exact": str(width) if width is not None else None,
                 "budget": budget, "queries": len(selected),
                 "total_subdivisions": sum(r["result"]["subdivisions"] for r in selected),
                 "obstacle_checks": sum(len(r["result"]["proofs"]) for r in selected),
                 "median_per_control_ns": median(r["predicate_ns_median"] for r in selected),
                 "per_control_median_ns_distribution": distribution([r["predicate_ns_median"] for r in selected]),
                 "all_repeat_ns_distribution": distribution([t for r in selected for t in r["all_predicate_ns"]]),
                 "accepted_auxiliary_unsafe_controls": sum(r["result"]["status"] == "accepted" and r["auxiliary_reference_status"] == "unsafe" for r in selected),
                 "accepted_joint_safe_controls": sum(r["result"]["status"] == "accepted" and r["joint_reference_status"] == "safe" for r in selected)}
        for decision in ("accepted", "rejected", "unknown"):
            group[decision] = sum(r["result"]["status"] == decision for r in selected)
            for truth in ("safe", "unsafe"):
                group[f"{decision}_{truth}_controls"] = sum(r["result"]["status"] == decision and r["independent_reference_status"] == truth for r in selected)
        groups.append(group)
    return {"seed": seed, "repeats": repeats, "strategies": methods, "budget_scope": "per_control",
            "cases": len(reference), "applicable_cases": sum(r["hocbf_applicable"] for r in reference),
            "controls": len(controls), "reference": reference, "measurements": rows, "groups": groups,
            "geometric_truth_counts": dict(Counter(c["geometric_status"] for c in controls)),
            "joint_truth_counts": dict(Counter(c["joint_status"] for c in controls)), "diagnostics": diagnostics,
            "paired_comparisons": paired_comparisons(rows, methods, widths, budgets, PARAMETER_FREE),
            "assumptions": ASSUMPTIONS | {"cohort": "Original HOCBF-domain cohort retained for matching; not a required initial-domain restriction of every geometric predicate"},
            "scope": SCOPE}


def _identity(reference):
    for case_index, case in enumerate(reference):
        config = case["input"]
        state, obstacles = PlanarState(config["p"], config["v"]), tuple(Circle(**o) for o in config["obstacles"])
        for candidate_index, candidate in enumerate(case["candidates"]):
            identity = {"case_index": case_index, "candidate_index": candidate_index, "case": case["name"],
                        "action_exact": candidate["action_exact"], "independent_reference_status": candidate["geometric_status"],
                        "auxiliary_reference_status": candidate["auxiliary_status"], "joint_reference_status": candidate["joint_status"]}
            arguments = (state, vector2(candidate["action_exact"]), obstacles, positive(config["duration"]), positive(config["a_max"]))
            yield identity, arguments


def geometry_study(source_spec, source_study, spec):
    settings = _settings(spec)
    reference = _reference(source_spec, source_study)
    rng, rows = Random(settings[4]), []
    for identity, arguments in _identity(reference):
        samples, positions, answers = ([[] for _ in settings[-1]], [[] for _ in settings[-1]], [None]*len(settings[-1]))
        for _ in range(settings[3]):
            order = list(range(len(settings[-1])))
            rng.shuffle(order)
            for position, index in enumerate(order):
                method, tolerance, budget = settings[-1][index]
                start = perf_counter_ns()
                result = evaluate_geometry(method, *arguments, tolerance, budget)
                samples[index].append(perf_counter_ns()-start)
                positions[index].append(position)
                if answers[index] is not None and not _same(result, answers[index]):
                    raise ArithmeticError("Repeated exact geometric predicate changed its evidence")
                answers[index] = result
        for index, (method, tolerance, budget) in enumerate(settings[-1]):
            result = answers[index]
            if ((result["status"] == "accepted" and identity["independent_reference_status"] != "safe") or
                    (result["status"] == "rejected" and identity["independent_reference_status"] != "unsafe")):
                raise ArithmeticError("Geometric predicate contradicts complete path sign")
            rows.append(identity | {"strategy": method, "tolerance_exact": str(tolerance) if tolerance is not None else None,
                        "budget": budget, "result": result, "all_predicate_ns": samples[index],
                        "predicate_ns_median": median(samples[index]), "sample_positions": positions[index]})
    return _assemble(reference, rows, settings)


def verify_geometry_study(source_spec, source_study, spec, saved):
    """Replay all science and check raw timing layout/statistics, not the clock."""
    settings, reference = _settings(spec), _reference(source_spec, source_study)
    if not _same(saved["reference"], reference):
        raise ValueError("Physical cohort, domain or complete reference evidence changed")
    timing_spec = {"strategies": settings[0], "tolerances": list(map(str, settings[1])), "budgets": settings[2],
                   "repeats": settings[3], "seed": settings[4]}
    timing = verify_timing_evidence(timing_spec, saved, parameter_free=PARAMETER_FREE,
                                    proof_count_field="obstacle_checks")
    rows, index = [], 0
    for identity, arguments in _identity(reference):
        for method, tolerance, budget in settings[-1]:
            old = saved["measurements"][index]
            expected = identity | {"strategy": method, "tolerance_exact": str(tolerance) if tolerance is not None else None,
                                   "budget": budget, "result": evaluate_geometry(method, *arguments, tolerance, budget)}
            row = expected | {key: old[key] for key in ("all_predicate_ns", "predicate_ns_median", "sample_positions")}
            if not _same(row, old):
                raise ValueError("Geometric decision or full exact proof does not regenerate")
            rows.append(row)
            index += 1
    if not _same(_assemble(reference, rows, settings), saved):
        raise ValueError("Geometry study scope, counts, diagnostics or statistics changed")
    return {"status": "verified", "controls": saved["controls"], "predicate_results": index,
            "timing": timing, "scope": "Full exact cohort/predicate replay and empirical paired-layout verification; no clock authentication or controller substitution"}
