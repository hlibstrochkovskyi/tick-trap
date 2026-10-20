"""Offline audit of endpoint approximation, sampled checks and set distance.

No controller is synthesized and no practical-safety family is certified. Exact
one-hold observations are kept separate from Taylor et al.'s family hypotheses.
"""

from .algebraic_reference import exact_sign_reference
import json
from .dynamics import WallState
from .numbers import nonnegative, positive, q

MAPS = ("euler", "midpoint")


def approximate_wall_step(state, action, duration, method):
    """One explicit Euler or explicit midpoint step of d_dot=-v, v_dot=u."""
    action, duration = q(action), positive(duration, "duration")
    if method == "euler":
        return WallState(state.d-duration*state.v, state.v+duration*action)
    if method == "midpoint":
        stage = WallState(state.d-duration*state.v/2, state.v+duration*action/2)
        return WallState(state.d-duration*stage.v, state.v+duration*action)
    raise ValueError("Unknown approximation method")


def barrier_distance_squared(state, tau, position_scale=1, velocity_scale=1):
    """Distance to C_b={d-tau*v>=0} in normalized (d/L,v/V) coordinates.

    Return the exact squared norm distance and a closest *physical* state. A
    radius in this metric is dimensionless, not a physical clearance tolerance.
    """
    tau, length, speed = positive(tau, "tau"), positive(position_scale, "position_scale"), positive(velocity_scale, "velocity_scale")
    b = state.d-tau*state.v
    if b >= 0:
        return q(0), state
    norm_squared = length**2+(tau*speed)**2
    projected = WallState(state.d-b*length**2/norm_squared, state.v+b*tau*speed**2/norm_squared)
    return b*b/norm_squared, projected


def _state(state):
    return {"d_exact": str(state.d), "v_exact": str(state.v)}


def audit_wall_approximation(state, action, duration, a_max=10, tau="0.3", gain=2,
                             position_scale=1, velocity_scale=1, radii=(0, "0.01", "0.1")):
    """Compare two approximate maps to one actual held trajectory, exactly.

    The pointwise decrement b(Fa)-(1-T*k)b0>=0 and T*k<=1 are necessary
    ingredients, not proof of a family of SD-BFs or practical safety. All output
    distances concern C_b alone, with the stated state normalization.
    """
    action, duration = q(action), positive(duration, "duration")
    a, tau, gain = positive(a_max, "a_max"), positive(tau, "tau"), positive(gain, "gain")
    length, speed = positive(position_scale, "position_scale"), positive(velocity_scale, "velocity_scale")
    radii = [nonnegative(r, "radius") for r in radii]
    if not radii or len(set(radii)) != len(radii) or abs(action) > a:
        raise ValueError("Require distinct nonnegative radii and an actuator-admissible action")
    actual = state.at(action, duration)
    b0, b1 = state.d-tau*state.v, actual.d-tau*actual.v
    geometric = (state.d, -state.v, -action/2)
    barrier = (b0, -state.v-tau*action, -action/2)
    d_min, d_time = state.minimum(action, duration)
    b_min, b_time = WallState(b0, state.v+tau*action).minimum(action, duration)
    references = {"d": exact_sign_reference(geometric, duration), "b": exact_sign_reference(barrier, duration)}
    if ((references["d"]["status"] == "safe") != (d_min >= 0) or
            (references["b"]["status"] == "safe") != (b_min >= 0)):
        raise ArithmeticError("Independent sign reference contradicts an exact quadratic minimum")
    normal_squared = length**2+(tau*speed)**2
    initial_distance, initial_projection = barrier_distance_squared(state, tau, length, speed)
    final_distance, final_projection = barrier_distance_squared(actual, tau, length, speed)
    worst = max(-b_min, 0)**2/normal_squared
    model_results = []
    for method in MAPS:
        approximate = approximate_wall_step(state, action, duration, method)
        b_approx = approximate.d-tau*approximate.v
        error = ((actual.d-approximate.d)/length, (actual.v-approximate.v)/speed)
        error_squared = sum(e*e for e in error)
        tight_bound = a*duration**2/(2*length) if method == "euler" else q(0)
        # rho must be class K_infinity. Exact midpoint error is zero, but rho=0
        # is not strictly increasing; rho(T)=T is a valid conservative witness.
        rho = a*duration/(2*length) if method == "euler" else duration
        residual = b_approx-(1-duration*gain)*b0
        barrier_error_bound = a*duration**2/2 if method == "euler" else q(0)
        if (error_squared > tight_bound**2 or error_squared > (duration*rho)**2
                or abs(b1-b_approx) > barrier_error_bound):
            raise ArithmeticError("Exact map discrepancy exceeded its analytical consistency bound")
        model_results.append({"method": method, "approximate_end_state": _state(approximate),
                              "approximate_end_barrier_exact": str(b_approx),
                              "position_input_coefficient_exact": str(q(0) if method == "euler" else -duration**2/2),
                              "barrier_input_coefficient_exact": str(-tau*duration if method == "euler" else -tau*duration-duration**2/2),
                              "normalized_error_vector_exact": [str(e) for e in error],
                              "normalized_error_squared_exact": str(error_squared),
                              "tight_uniform_error_upper_exact": str(tight_bound),
                              "rho_at_duration_exact": str(rho),
                              "rho_formula": "a*T/(2*L)" if method == "euler" else "T",
                              "barrier_map_error_exact": str(b1-b_approx),
                              "uniform_barrier_error_upper_exact": str(barrier_error_bound),
                              "approximate_decrement_residual_exact": str(residual),
                              "approximate_decrement_satisfied": residual >= 0,
                              "step_restriction_satisfied": duration*gain <= 1,
                              "pointwise_ingredients_satisfied": b0 >= 0 and duration*gain <= 1 and residual >= 0,
                              "approximate_sampled_barrier_safe": b0 >= 0 and b_approx >= 0})
    return {"state": _state(state), "action_exact": str(action), "duration_exact": str(duration),
            "a_max_exact": str(a), "tau_exact": str(tau), "gain_exact": str(gain),
            "initial_geometric_safe": state.d >= 0, "initial_barrier_safe": b0 >= 0,
            "initial_viable": state.viability_margin(a) >= 0,
            "actual_end_state": _state(actual), "initial_barrier_exact": str(b0), "actual_end_barrier_exact": str(b1),
            "exact_sampled_geometric_safe": state.d >= 0 and actual.d >= 0,
            "exact_sampled_barrier_safe": b0 >= 0 and b1 >= 0,
            "geometric_path_status": "safe" if d_min >= 0 else "unsafe",
            "barrier_path_status": "safe" if b_min >= 0 else "unsafe",
            "geometric_polynomial_exact": [str(c) for c in geometric], "barrier_polynomial_exact": [str(c) for c in barrier],
            "geometric_minimum_exact": str(d_min), "geometric_witness_time_exact": str(d_time),
            "barrier_minimum_exact": str(b_min), "barrier_witness_time_exact": str(b_time),
            "independent_sign_references": references,
            "metric": {"coordinates": "(d/L,v/V)", "position_scale_exact": str(length), "velocity_scale_exact": str(speed),
                       "barrier_normal_squared_exact": str(normal_squared), "target_set": "C_b={d-tau*v>=0}",
                       "initial_distance_squared_exact": str(initial_distance), "end_distance_squared_exact": str(final_distance),
                       "initial_closest_state": _state(initial_projection), "end_closest_state": _state(final_projection),
                       "maximum_path_distance_squared_exact": str(worst)},
            "dilations": [{"radius_exact": str(r), "sampled_within_dilation": max(initial_distance, final_distance) <= r*r,
                           "path_within_dilation": worst <= r*r} for r in radii],
            "maps": model_results, "practical_safety_family_certificate": "not_established",
            "scope": "Exact one-hold diagnostics; set-distance allowances do not change exact-set statuses or certify an invariant controller family"}


def approximation_study(spec):
    """Evaluate matched physical holds under explicit state-distance metrics."""
    if not isinstance(spec, dict) or set(spec)-{"base", "cases", "durations", "normalizations", "radii"}:
        raise ValueError("Unknown approximation study field")
    base, cases = spec.get("base", {}), spec.get("cases", [])
    if not isinstance(base, dict) or set(base)-{"a_max", "tau", "gain"} or not isinstance(cases, list) or not cases:
        raise ValueError("Invalid approximation study base or cases")
    base = {"a_max": 10, "tau": "0.3", "gain": 2} | base
    periods = spec.get("durations", ["0.1"])
    radii = spec.get("radii", [0, "0.01", "0.1"])
    normalizations = spec.get("normalizations", [{"name": "unit", "position_scale": 1, "velocity_scale": 1}])
    if not isinstance(periods, list) or not periods or not isinstance(radii, list) or not radii:
        raise ValueError("durations and radii must be nonempty lists")
    periods, radii = [positive(t, "duration") for t in periods], [nonnegative(r, "radius") for r in radii]
    if len(set(periods)) != len(periods) or len(set(radii)) != len(radii):
        raise ValueError("Duplicate durations or radii")
    if not isinstance(normalizations, list) or not normalizations:
        raise ValueError("normalizations must be a nonempty list")
    labels = []
    for metric in normalizations:
        if (not isinstance(metric, dict) or set(metric) != {"name", "position_scale", "velocity_scale"}
                or not isinstance(metric["name"], str) or not metric["name"] or metric["name"] in labels):
            raise ValueError("Each normalization needs a distinct name and positive scales")
        positive(metric["position_scale"], "position_scale")
        positive(metric["velocity_scale"], "velocity_scale")
        labels.append(metric["name"])
    names, records = [], []
    for case_index, case in enumerate(cases):
        if (not isinstance(case, dict) or set(case)-{"name", "d", "v", "u", "a_max", "tau", "gain"}
                or not {"name", "d", "v", "u"} <= set(case) or not isinstance(case["name"], str)
                or not case["name"] or case["name"] in names):
            raise ValueError("Each case needs a distinct name, d, v and u")
        names.append(case["name"])
        config = base | {k: v for k, v in case.items() if k in base}
        state = WallState(case["d"], case["v"])
        for duration in periods:
            for metric in normalizations:
                result = audit_wall_approximation(state, case["u"], duration, **config,
                                                  position_scale=metric["position_scale"], velocity_scale=metric["velocity_scale"], radii=radii)
                records.append({"case_index": case_index, "case": case["name"], "normalization": metric["name"], **result})
    groups, dilation_groups = [], []
    for label in labels:
        physical = [r for r in records if r["normalization"] == label]
        for method in MAPS:
            matched = [(r, next(m for m in r["maps"] if m["method"] == method)) for r in physical]
            groups.append({"normalization": label, "method": method, "holds": len(matched),
                           "nonzero_map_errors": sum(q(m["normalized_error_squared_exact"]) > 0 for r, m in matched),
                           "pointwise_ingredients_satisfied": sum(m["pointwise_ingredients_satisfied"] for r, m in matched),
                           "step_restriction_violations": sum(not m["step_restriction_satisfied"] for r, m in matched),
                           "pointwise_pass_but_exact_sample_outside_b": sum(m["pointwise_ingredients_satisfied"] and not r["exact_sampled_barrier_safe"] for r, m in matched),
                           "pointwise_pass_and_exact_samples_safe_but_path_outside_b": sum(m["pointwise_ingredients_satisfied"] and r["exact_sampled_barrier_safe"] and r["barrier_path_status"] == "unsafe" for r, m in matched),
                           "pointwise_pass_and_exact_samples_safe_but_geometric_collision": sum(m["pointwise_ingredients_satisfied"] and r["exact_sampled_barrier_safe"] and r["exact_sampled_geometric_safe"] and r["geometric_path_status"] == "unsafe" for r, m in matched),
                           "established_practical_safety_families": 0})
        for radius in radii:
            selected = [(r, next(d for d in r["dilations"] if q(d["radius_exact"]) == radius)) for r in physical]
            dilation_groups.append({"normalization": label, "radius_exact": str(radius), "holds": len(selected),
                                    "sampled_within_dilation": sum(d["sampled_within_dilation"] for r, d in selected),
                                    "path_within_dilation": sum(d["path_within_dilation"] for r, d in selected),
                                    "within_dilation_despite_exact_barrier_violation": sum(d["path_within_dilation"] and r["barrier_path_status"] == "unsafe" for r, d in selected)})
    return {"records": records, "groups": groups, "dilation_groups": dilation_groups,
            "scope": "Offline held-input map and property audit inspired by Taylor 2203.11470v2; no Taylor controller or practically invariant set family is implemented or certified"}


def verify_approximation_study(spec, stored):
    """Regenerate every deterministic field, including references and metrics."""
    expected = approximation_study(spec)
    encode = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
    if encode(stored) != encode(expected):
        raise ValueError("Approximation audit does not match exact regeneration")
    return {"status": "verified", "held_metric_cases": len(expected["records"]),
            "map_comparisons": sum(len(r["maps"]) for r in expected["records"]),
            "distance_classifications": sum(len(r["dilations"]) for r in expected["records"]),
            "scope": "Deterministic arithmetic and saved-record consistency with independent polynomial sign references; no controller-family or physical-safety theorem verified"}
