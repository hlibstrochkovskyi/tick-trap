"""Offline ZOCBF buffer, prediction-error and input-pairing diagnostics.

The constraint is a declared affine proxy h(d,v,u)=d-tau*v-sigma*u, not a
rollover model or a new controller. Global ZOCBF existence is not asserted.
"""

import json

from .algebraic_reference import exact_sign_reference
from .approximation_audit import approximate_wall_step
from .dynamics import WallState
from .numbers import nonnegative, positive, q, sqrt_upper

BUFFER_POLICIES = ("norm_tube", "projected_tube", "candidate_derivative", "oracle_absolute", "oracle_backward_drop", "endpoint_only")
VARIANTS = ("exact_previous", "euler_unadjusted", "euler_tightened", "midpoint_previous", "reset_start_input", "stale_end_input")


def constraint_value(state, action, tau=0, sigma=0):
    return state.d-nonnegative(tau, "tau")*state.v-nonnegative(sigma, "sigma")*q(action)


def audit_zocbf_hold(state, previous_action, action, duration, a_max=10, tau=0, sigma=0, gamma="0.5"):
    """Reconstruct Eq. (4), local hold bounds and Eq. (20) for an affine proxy.

    Every value is exact rational, including outward square-root enclosures.
    Buffer alternatives are offline references, not full paper implementations.
    The constant input can jump at time zero; left and right values stay separate.
    """
    previous_action, action = q(previous_action), q(action)
    duration, a = positive(duration, "duration"), positive(a_max, "a_max")
    tau, sigma, gamma = nonnegative(tau, "tau"), nonnegative(sigma, "sigma"), positive(gamma, "gamma")
    if gamma > 1 or max(abs(previous_action), abs(action)) > a:
        raise ValueError("Require gamma in (0,1] and both commands in the actuator interval")
    left = constraint_value(state, previous_action, tau, sigma)
    right = constraint_value(state, action, tau, sigma)
    end = state.at(action, duration)
    final = constraint_value(end, action, tau, sigma)
    stale_final = constraint_value(end, previous_action, tau, sigma)
    polynomial = (right, -state.v-tau*action, -action/2)
    minimum, minimum_time = WallState(right, state.v+tau*action).minimum(action, duration)
    neg_maximum, maximum_time = WallState(-right, -state.v-tau*action).minimum(-action, duration)
    maximum = -neg_maximum
    independent = exact_sign_reference(polynomial, duration)
    if (independent["status"] == "safe") != (minimum >= 0):
        raise ArithmeticError("Independent sign reference disagrees with the exact held proxy minimum")
    d_min, d_time = state.minimum(action, duration)
    speed_bound = abs(state.v)+a*duration
    root_scale = 10**12
    gradient_bound = sqrt_upper(1+tau*tau, root_scale)
    flow_bound = sqrt_upper(speed_bound**2+a*a, root_scale)
    norm = gradient_bound*flow_bound*duration
    projected = (speed_bound+tau*a)*duration
    candidate = max(abs(state.v+tau*action), abs(state.v+(tau+duration)*action))*duration
    backward = final-minimum
    absolute = max(backward, maximum-final)
    if not 0 <= backward <= absolute <= candidate <= projected <= norm:
        raise ArithmeticError("Analytical buffer hierarchy was violated")
    buffers = dict(zip(BUFFER_POLICIES, (norm, projected, candidate, absolute, backward, q(0))))
    euler_end = approximate_wall_step(state, action, duration, "euler")
    midpoint_end = approximate_wall_step(state, action, duration, "midpoint")
    euler_value = constraint_value(euler_end, action, tau, sigma)
    midpoint_value = constraint_value(midpoint_end, action, tau, sigma)
    prediction_error = abs(action)*duration**2/2
    if abs(euler_value-final) != prediction_error or midpoint_value != final:
        raise ArithmeticError("Proxy endpoint prediction error does not match the exact affine model")
    assessments = []
    for policy, delta in buffers.items():
        bound_valid = delta >= backward
        endpoints = {"exact_previous": (left, final, q(0)),
                     "euler_unadjusted": (left, euler_value, q(0)),
                     "euler_tightened": (left, euler_value, prediction_error),
                     "midpoint_previous": (left, midpoint_value, q(0)),
                     "reset_start_input": (right, final, q(0)),
                     "stale_end_input": (left, stale_final, q(0))}
        variants = []
        for name, (start, predicted, margin) in endpoints.items():
            target = (1-gamma)*start
            residual = predicted-target-delta-margin
            passed = residual >= 0
            lower_valid = final >= predicted-margin
            sufficient = target >= 0 and bound_valid and lower_valid and passed
            if sufficient and minimum < 0:
                raise ArithmeticError("Valid one-hold implication admitted an unsafe proxy path")
            if name == "reset_start_input" and bound_valid and passed and minimum < 0:
                raise ArithmeticError("Reset-start condition contradicts its separate valid hold-bound argument")
            variants.append({"variant": name, "start_value_exact": str(start), "predicted_end_value_exact": str(predicted),
                             "endpoint_target_exact": str(target), "endpoint_target_nonnegative": target >= 0,
                             "prediction_margin_exact": str(margin), "residual_exact": str(residual),
                             "condition_passed": passed, "endpoint_lower_bound_valid": lower_valid,
                             "one_hold_implication_ingredients": sufficient,
                             "matches_paper_input_pairing": name not in ("reset_start_input", "stale_end_input")})
        assessments.append({"buffer_policy": policy, "delta_exact": str(delta),
                            "backward_difference_bound_valid": bound_valid,
                            "positive_delta": delta > 0, "variants": variants})
    return {"state_exact": {"d": str(state.d), "v": str(state.v)},
            "previous_action_exact": str(previous_action), "action_exact": str(action), "duration_exact": str(duration),
            "a_max_exact": str(a), "tau_exact": str(tau), "sigma_exact": str(sigma), "gamma_exact": str(gamma),
            "left_barrier_exact": str(left), "right_barrier_exact": str(right),
            "endpoint_input_convention": "current held input; left limit before the next update",
            "input_jump_exact": str(right-left), "actual_end_barrier_exact": str(final),
            "stale_input_end_barrier_exact": str(stale_final),
            "left_pair_safe": left >= 0, "right_pair_safe": right >= 0,
            "actual_sampled_constraint_safe": right >= 0 and final >= 0,
            "constraint_path_status": "safe" if minimum >= 0 else "unsafe",
            "constraint_polynomial_exact": [str(c) for c in polynomial],
            "constraint_minimum_exact": str(minimum), "minimum_time_exact": str(minimum_time),
            "constraint_maximum_exact": str(maximum), "maximum_time_exact": str(maximum_time),
            "independent_sign_reference": independent, "geometric_minimum_exact": str(d_min),
            "geometric_minimum_time_exact": str(d_time), "geometric_path_status": "safe" if d_min >= 0 else "unsafe",
            "initial_viable": state.viability_margin(a) >= 0,
            "gradient_norm_upper_exact": str(gradient_bound), "flow_norm_upper_exact": str(flow_bound),
            "square_root_enclosure_scale": root_scale,
            "reachable_speed_bound_exact": str(speed_bound), "oracle_backward_drop_exact": str(backward),
            "euler_endpoint_error_bound_exact": str(prediction_error), "assessments": assessments,
            "scope": "Exact local held-input proxy diagnostics; no global ZOCBF, recursive feasibility, rollover model or new controller certified"}


def zocbf_contract_study(spec):
    """Evaluate every buffer/prediction variant on the same prescribed holds."""
    if not isinstance(spec, dict) or set(spec)-{"base", "cases", "durations"}:
        raise ValueError("Unknown ZOCBF contract study field")
    base, cases, periods = spec.get("base", {}), spec.get("cases", []), spec.get("durations", ["0.1"])
    allowed = {"a_max", "tau", "sigma", "gamma"}
    if not isinstance(base, dict) or set(base)-allowed or not isinstance(cases, list) or not cases:
        raise ValueError("Invalid ZOCBF base or cases")
    base = {"a_max": 1, "tau": 0, "sigma": 0, "gamma": "0.5"} | base
    if not isinstance(periods, list) or not periods:
        raise ValueError("durations must be a nonempty list")
    periods = [positive(t, "duration") for t in periods]
    if len(set(periods)) != len(periods):
        raise ValueError("Duplicate durations")
    records, names = [], []
    for index, case in enumerate(cases):
        required = {"name", "d", "v", "previous_action", "action"}
        if (not isinstance(case, dict) or not required <= set(case) or set(case)-required-allowed
                or not isinstance(case["name"], str) or not case["name"] or case["name"] in names):
            raise ValueError("Each case requires a distinct name, state and both input values")
        names.append(case["name"])
        config = base | {k: v for k, v in case.items() if k in allowed}
        for duration in periods:
            record = audit_zocbf_hold(WallState(case["d"], case["v"]), case["previous_action"], case["action"], duration, **config)
            records.append({"case_index": index, "case": case["name"], **record})
    groups = []
    for policy in BUFFER_POLICIES:
        for variant in VARIANTS:
            matched = []
            for row in records:
                buffer = next(b for b in row["assessments"] if b["buffer_policy"] == policy)
                check = next(v for v in buffer["variants"] if v["variant"] == variant)
                matched.append((row, buffer, check))
            groups.append({"buffer_policy": policy, "variant": variant, "holds": len(matched),
                           "safe_left_pairs": sum(r["left_pair_safe"] for r, b, v in matched),
                           "raw_condition_passes": sum(v["condition_passed"] for r, b, v in matched),
                           "passes_with_safe_left": sum(r["left_pair_safe"] and v["condition_passed"] for r, b, v in matched),
                           "passes_with_safe_left_and_unsafe_proxy": sum(r["left_pair_safe"] and v["condition_passed"] and r["constraint_path_status"] == "unsafe" for r, b, v in matched),
                           "passes_with_safe_left_and_unsafe_jump": sum(r["left_pair_safe"] and v["condition_passed"] and not r["right_pair_safe"] for r, b, v in matched),
                           "safe_holds_rejected_with_safe_left": sum(r["left_pair_safe"] and not v["condition_passed"] and r["constraint_path_status"] == "safe" for r, b, v in matched),
                           "valid_local_implication_ingredients": sum(v["one_hold_implication_ingredients"] for r, b, v in matched),
                           "invalid_backward_bounds": sum(not b["backward_difference_bound_valid"] for r, b, v in matched),
                           "zero_deltas": sum(not b["positive_delta"] for r, b, v in matched),
                           "invalid_endpoint_lower_bounds": sum(not v["endpoint_lower_bound_valid"] for r, b, v in matched),
                           "disagreements_with_exact_history_condition": sum(v["condition_passed"] != b["variants"][0]["condition_passed"] for r, b, v in matched)})
    return {"records": records, "groups": groups,
            "scope": "Local affine state-input proxy and numerical-condition audit of Tan 2411.17079v2; alternative bounds and diagnostic input pairings are not new controllers or full paper replications"}


def verify_zocbf_contract_study(spec, stored):
    expected = zocbf_contract_study(spec)
    encode = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
    if encode(stored) != encode(expected):
        raise ValueError("ZOCBF contract evidence does not match exact regeneration")
    return {"status": "verified", "holds": len(expected["records"]),
            "buffer_assessments": sum(len(r["assessments"]) for r in expected["records"]),
            "condition_assessments": sum(len(b["variants"]) for r in expected["records"] for b in r["assessments"]),
            "scope": "Deterministic local-condition regeneration with independent proxy sign references; no global ZOCBF existence or physical rollover guarantee verified"}
