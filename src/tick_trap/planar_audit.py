"""Compare admitted controls at the same states, independently of rollouts."""

from time import perf_counter_ns

from .dynamics import Circle, PlanarState
from .numbers import positive, q, vector2
from .planar_control import candidate_actions, hocbf_constraints, segment_minimum, zocbf_buffer
from .planar_experiments import braking_continuation
from .polynomial import certify_minimum
from .qp import dot

PREDICATES = ("hocbf", "endpoint", "segment", "zocbf")


def audit_case(name, p, v, nominal, obstacles, duration, a_max, lambda1=2, lambda2=2,
               gamma=1, grid_points=5, command_quantum="1e-6", tolerance="1e-12", max_subdivisions=4096):
    state, nominal = PlanarState(p, v), vector2(nominal)
    obstacles = tuple(o if isinstance(o, Circle) else Circle(**o) for o in obstacles)
    duration, a_max, gamma = positive(duration, "duration"), positive(a_max, "a_max"), positive(gamma, "gamma")
    if gamma > 1:
        raise ValueError("gamma must be in (0,1]")
    constraints, domains = hocbf_constraints(state, obstacles, lambda1, lambda2)
    if not all(q(domain["h_exact"]) >= 0 for domain in domains):
        raise ValueError("Candidate audit requires geometrically safe initial states")
    hocbf_applicable = all(domain["in_domain"] for domain in domains)
    start = perf_counter_ns()
    buffers = [zocbf_buffer(state, o, duration, a_max) for o in obstacles]
    buffer_ns = perf_counter_ns()-start
    candidates = candidate_actions(nominal, state, duration, a_max, grid_points, command_quantum)
    rows = []
    for action in candidates:
        row = {"action_exact": [str(x) for x in action],
               "intervention_squared_exact": str(sum((a-n)**2 for a, n in zip(action, nominal))),
               "predicates": {}, "predicate_ns": {}}
        start = perf_counter_ns()
        row["predicates"]["hocbf"] = all(c.residual(action) <= 0 for c in constraints) if hocbf_applicable else None
        row["hocbf_residuals_exact"] = [str(c.residual(action)) for c in constraints]
        row["predicate_ns"]["hocbf"] = perf_counter_ns()-start
        start = perf_counter_ns()
        end = state.at(action, duration)
        end_margins = []
        for obstacle in obstacles:
            initial_r = tuple(p-c for p, c in zip(state.p, obstacle.center))
            end_r = tuple(p-c for p, c in zip(end.p, obstacle.center))
            h0 = dot(initial_r, initial_r)-obstacle.radius**2
            h1 = dot(end_r, end_r)-obstacle.radius**2
            end_margins.append(h1-(1-gamma)*h0)
        row["predicates"]["endpoint"] = all(m >= 0 for m in end_margins)
        row["endpoint_margins_exact"] = [str(m) for m in end_margins]
        row["predicate_ns"]["endpoint"] = perf_counter_ns()-start
        start = perf_counter_ns()
        segment = [segment_minimum(state, action, o, duration) for o in obstacles]
        row["predicates"]["segment"] = all(m >= 0 for m in segment)
        row["segment_minima_exact"] = [str(m) for m in segment]
        row["predicate_ns"]["segment"] = perf_counter_ns()-start
        start = perf_counter_ns()
        zocbf = [m-b for m, b in zip(end_margins, buffers)]
        row["predicates"]["zocbf"] = all(m >= 0 for m in zocbf)
        row["zocbf_margins_exact"] = [str(m) for m in zocbf]
        row["predicate_ns"]["zocbf"] = perf_counter_ns()-start
        start = perf_counter_ns()
        certificates = [certify_minimum(o.polynomial(state, action), duration, tolerance, max_subdivisions)
                        for o in obstacles]
        row["certification_ns"] = perf_counter_ns()-start
        statuses = [c.status for c in certificates]
        row["trajectory_status"] = "unsafe" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "safe"
        row["certificates"] = [{"status": c.status, "lower_exact": str(c.lower), "upper_exact": str(c.upper),
                                "witness_time_exact": str(c.witness_time), "subdivisions": c.subdivisions}
                               for c in certificates]
        rows.append(row)
    counts = {}
    for method in PREDICATES:
        counts[method] = {
            "applicable": sum(r["predicates"][method] is not None for r in rows),
            "accepted": sum(r["predicates"][method] is True for r in rows),
            "safe_admitted": sum(r["predicates"][method] is True and r["trajectory_status"] == "safe" for r in rows),
            "unsafe_admitted": sum(r["predicates"][method] is True and r["trajectory_status"] == "unsafe" for r in rows),
            "safe_excluded": sum(r["predicates"][method] is False and r["trajectory_status"] == "safe" for r in rows),
            "accepted_truth_unknown": sum(r["predicates"][method] is True and r["trajectory_status"] == "unknown" for r in rows),
        }
    return {"name": name, "candidate_count": len(candidates), "hocbf_applicable": hocbf_applicable,
            "initial_braking": braking_continuation(state, obstacles, duration, a_max, tolerance, max_subdivisions, command_quantum),
            "truth_counts": {status: sum(r["trajectory_status"] == status for r in rows) for status in ("safe", "unsafe", "unknown")},
            "zocbf_buffers_exact": [str(b) for b in buffers], "buffer_construction_ns": buffer_ns,
            "counts": counts, "candidates": rows,
            "scope": "Finite matched controls and one-interval safety; no global feasibility or viability-kernel claim"}


def audit_cases(spec):
    if not isinstance(spec, dict) or set(spec)-{"base", "cases"}:
        raise ValueError("Candidate audit accepts only base and cases")
    base, cases = spec.get("base", {}), spec.get("cases", [])
    if not isinstance(base, dict) or not isinstance(cases, list) or not cases:
        raise ValueError("Audit base must be an object and cases a nonempty list")
    if not all(isinstance(case, dict) for case in cases):
        raise ValueError("Each audit case must be an object")
    return [audit_case(**(base | case)) for case in cases]
