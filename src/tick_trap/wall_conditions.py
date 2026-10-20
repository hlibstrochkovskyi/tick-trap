"""Matched held-control and rollout comparison of published wall conditions."""

from fractions import Fraction
from itertools import product
import json

from .algebraic_reference import exact_sign_reference
from .controllers import decide
from .dynamics import WallState
from .experiments import RunConfig, run
from .numbers import positive, q

WALL_CONDITIONS = ("continuous_cbf", "breeden", "breeden_reachable", "breeden_second_order")


def wall_condition_study(spec):
    """Compare the same initial b-set and candidates, with explicit gain policies.

    All runs use the ideal exact model, zero observation error and zero delay.
    Published conditions preserve b=d-tau*v; the continuous-CBF emulation is a
    diagnostic and is allowed to fail that held-path test. Infeasibility stops.
    """
    if not isinstance(spec, dict) or set(spec)-{"base", "cases", "durations", "gain_policies", "grid_points", "methods"}:
        raise ValueError("Unknown wall condition study field")
    base, cases = spec.get("base", {}), spec.get("cases", [])
    allowed = {"a_max", "tau", "gamma", "cbf_gain", "nominal", "horizon", "seed"}
    if not isinstance(base, dict) or set(base)-allowed or not isinstance(cases, list) or not cases:
        raise ValueError("Invalid wall study base or cases")
    defaults = dict(a_max="10", tau="0.3", gamma="1", cbf_gain="2", nominal="0", horizon="2", seed=20261020)
    base = defaults | base
    a, tau, gamma, fixed_gain = (positive(base[k], k) for k in ("a_max", "tau", "gamma", "cbf_gain"))
    if gamma > 1:
        raise ValueError("gamma must be in (0,1]")
    nominal = max(-a, min(a, q(base["nominal"])))
    points = spec.get("grid_points", 21)
    if isinstance(points, bool) or not isinstance(points, int) or points < 2:
        raise ValueError("grid_points must be an integer >= 2")
    durations = [positive(t, "duration") for t in spec.get("durations", ["0.1"])]
    policies, methods = spec.get("gain_policies", ["fixed", "matched"]), spec.get("methods", list(WALL_CONDITIONS))
    if not durations or len(set(durations)) != len(durations):
        raise ValueError("durations must be nonempty and unique")
    for values, supported, name in ((policies, ("fixed", "matched"), "gain_policies"), (methods, WALL_CONDITIONS, "methods")):
        if (not isinstance(values, list) or not values or any(not isinstance(v, str) or v not in supported for v in values)
                or len(set(values)) != len(values)):
            raise ValueError("Invalid "+name)
    names = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"name", "d", "v"} or not isinstance(case["name"], str) or not case["name"]:
            raise ValueError("Each case requires a name, d and v")
        if q(case["d"]) < 0 or case["name"] in names:
            raise ValueError("Cases must be geometrically safe and have distinct names")
        names.append(case["name"])
    controls = sorted({-a+2*a*Fraction(i, points-1) for i in range(points)} | {nominal})
    # Validate the entire rollout grid before any experiment is executed.
    configurations = []
    for case, duration, policy, method in product(cases, durations, policies, methods):
        gain = fixed_gain if policy == "fixed" else gamma/duration
        config = RunConfig(**(base | {"method": method, "d": str(q(case["d"])), "v": str(q(case["v"])),
                                     "duration": str(duration), "cbf_gain": str(gain)}))
        configurations.append((case["name"], policy, config))
    comparisons = []
    for case, duration, policy in product(cases, durations, policies):
        state = WallState(case["d"], case["v"])
        b0 = state.d-tau*state.v
        gain = fixed_gain if policy == "fixed" else gamma/duration
        selected, intervals = {}, {}
        for method in methods:
            decision = decide(method, state, nominal, duration, a, tau, gain, gamma)
            selected[method] = {"status": decision.status, "action_exact": str(decision.action) if decision.action is not None else None,
                                "residual_exact": str(decision.residual) if decision.residual is not None else None,
                                "effective_gain_exact": str(gamma/duration if method == "breeden_second_order" else gain),
                                "details": decision.details}
            if decision.status != "feasible":
                intervals[method] = None
            else:
                upper = min(a, q(decision.details["upper_action_bound_exact"]))
                intervals[method] = {"lower_exact": str(-a), "upper_exact": str(upper), "width_exact": str(upper+a)}
        rows = []
        for u in controls:
            geometric = (state.d, -state.v, -u/2)
            barrier = (b0, -state.v-tau*u, -u/2)
            h_min, h_time = state.minimum(u, duration)
            b_min, b_time = WallState(b0, state.v+tau*u).minimum(u, duration)
            independent = {"d": exact_sign_reference(geometric, duration), "b": exact_sign_reference(barrier, duration)}
            if (independent["d"]["status"] == "safe") != (h_min >= 0) or (independent["b"]["status"] == "safe") != (b_min >= 0):
                raise ArithmeticError("Independent quadratic sign reference disagrees with analytical minima")
            joint_safe = h_min >= 0 and b_min >= 0
            admissions = {m: None if b0 < 0 else intervals[m] is not None and u <= q(intervals[m]["upper_exact"]) for m in methods}
            if any(admissions[m] and not joint_safe for m in methods if m != "continuous_cbf"):
                raise ArithmeticError("Published condition admitted a held path violating its required set")
            rows.append({"action_exact": str(u), "geometric_polynomial_exact": [str(c) for c in geometric],
                         "barrier_polynomial_exact": [str(c) for c in barrier],
                         "geometric_minimum_exact": str(h_min), "geometric_witness_time_exact": str(h_time),
                         "barrier_minimum_exact": str(b_min), "barrier_witness_time_exact": str(b_time),
                         "joint_safe": joint_safe, "independent_reference": independent, "admissions": admissions})
        counts = {}
        for method in methods:
            counts[method] = {"applicable": sum(r["admissions"][method] is not None for r in rows),
                              "accepted_safe": sum(r["admissions"][method] is True and r["joint_safe"] for r in rows),
                              "accepted_unsafe": sum(r["admissions"][method] is True and not r["joint_safe"] for r in rows),
                              "safe_excluded": sum(r["admissions"][method] is False and r["joint_safe"] for r in rows),
                              "unsafe_rejected": sum(r["admissions"][method] is False and not r["joint_safe"] for r in rows)}
        comparisons.append({"name": case["name"], "state_exact": {"d": str(state.d), "v": str(state.v)},
                            "duration_exact": str(duration), "gain_policy": policy, "comparison_gain_exact": str(gain),
                            "initial_barrier_exact": str(b0), "initial_viable": state.viability_margin(a) >= 0,
                            "in_domain": b0 >= 0, "selected": selected, "control_intervals": intervals, "counts": counts, "controls": rows})
    runs = []
    for name, policy, config in configurations:
        result = run(config)
        b0 = q(config.d)-tau*q(config.v)
        minima = []
        for record in result["records"]:
            if "action_exact" not in record:
                continue
            state = WallState(record["state"]["d_exact"], record["state"]["v_exact"])
            u = q(record["action_exact"])
            value, time = WallState(state.d-tau*state.v, state.v+tau*u).minimum(u, config.duration)
            record.update(barrier_minimum_exact=str(value), barrier_witness_time_exact=str(time), barrier_safe=value >= 0)
            minima.append(value)
            if config.method != "continuous_cbf" and value < 0:
                raise ArithmeticError("Published wall rollout violated its barrier during a feasible hold")
        result.update(study_case=name, gain_policy=policy,
                      effective_gain_exact=str(gamma/q(config.duration) if config.method == "breeden_second_order" else q(config.cbf_gain)),
                      barrier_safe_on_executed_holds=b0 >= 0 and all(x >= 0 for x in minima),
                      completed_barrier_horizon=result["completed_safe_horizon"] and b0 >= 0 and all(x >= 0 for x in minima),
                      minimum_barrier_exact=str(min([b0, *minima])))
        runs.append(result)
    groups = []
    for duration, policy, method in product(durations, policies, methods):
        matched = [c for c in comparisons if (c["duration_exact"], c["gain_policy"]) == (str(duration), policy)]
        trajectories = [r for r in runs if (r["config"]["duration"], r["gain_policy"], r["config"]["method"]) == (str(duration), policy, method)]
        groups.append({"duration_exact": str(duration), "gain_policy": policy, "method": method,
                       "states": len(matched), "applicable_controls": sum(c["counts"][method]["applicable"] for c in matched),
                       **{k: sum(c["counts"][method][k] for c in matched) for k in ("accepted_safe", "accepted_unsafe", "safe_excluded", "unsafe_rejected")},
                       "rollouts": len(trajectories), "completed_barrier_horizons": sum(r["completed_barrier_horizon"] for r in trajectories),
                       "completed_geometric_horizons": sum(r["completed_safe_horizon"] for r in trajectories),
                       "infeasible_stops": sum(r["termination"] == "infeasible" for r in trajectories),
                       "outside_domain_stops": sum(r["termination"] == "outside_domain" for r in trajectories),
                       "collisions": sum(r["collision_observed"] for r in trajectories)})
    return {"methods": methods, "single_hold_cases": comparisons, "groups": groups, "runs": runs,
            "scope": "Restricted wall specializations of Breeden 2103.03677v1 Theorems 1–3; exact model, observations and held actuation. Fixed and gamma/T-matched gains are separate. Geometric safety, barrier preservation and viability are distinct; no global feasibility or full paper reproduction claim."}


def verify_wall_condition_study(spec, study, runs):
    """Regenerate all scientific fields; exclude empirical timing observations.

    This is a consistency replay using the same controllers and exact model,
    including the independent algebraic signs for the fixed-control reference.
    It is not an independent implementation of the complete experiment.
    """
    timing_fields = {"solve_ns", "solve_ns_total", "certification_ns", "certification_ns_total",
                     "deadline_missed", "deadline_misses"}
    def scientific(value):
        if isinstance(value, dict):
            return {k: scientific(v) for k, v in value.items() if k not in timing_fields}
        if isinstance(value, list):
            return [scientific(v) for v in value]
        return value
    expected = wall_condition_study(spec)
    expected_runs = expected.pop("runs")
    encode = lambda value: json.dumps(scientific(value), sort_keys=True, allow_nan=False)
    if encode(study) != encode(expected) or encode(runs) != encode(expected_runs):
        raise ValueError("Wall study scientific evidence disagrees with exact regeneration")
    return {"status": "verified", "single_hold_cases": len(study["single_hold_cases"]),
            "fixed_control_checks": sum(len(c["controls"]) for c in study["single_hold_cases"]),
            "runs": len(runs), "executed_holds": sum(r["executed_steps"] for r in runs),
            "excluded_fields": sorted(timing_fields),
            "scope": "Exact scientific-record regeneration using the declared model and controllers; independent algebraic signs cross-check fixed-control minima. Timing and deadline observations, physical-model validity and original paper experiments are not verified."}
