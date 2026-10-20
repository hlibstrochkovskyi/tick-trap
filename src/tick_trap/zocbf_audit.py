"""Offline ZOCBF buffer, prediction-error and input-pairing diagnostics.

The constraint is a declared affine proxy h(d,v,u)=d-tau*v-sigma*u, not a
rollover model or a new controller. Global ZOCBF existence is not asserted.
"""

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
    norm = sqrt_upper(1+tau*tau)*sqrt_upper(speed_bound**2+a*a)*duration
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
            residual = predicted-(1-gamma)*start-delta-margin
            passed = residual >= 0
            lower_valid = final >= predicted-margin
            sufficient = start >= 0 and bound_valid and lower_valid and passed
            if sufficient and minimum < 0:
                raise ArithmeticError("Valid one-hold implication admitted an unsafe proxy path")
            if name == "reset_start_input" and bound_valid and passed and minimum < 0:
                raise ArithmeticError("Reset-start condition contradicts its separate valid hold-bound argument")
            variants.append({"variant": name, "start_value_exact": str(start), "predicted_end_value_exact": str(predicted),
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
            "reachable_speed_bound_exact": str(speed_bound), "oracle_backward_drop_exact": str(backward),
            "euler_endpoint_error_bound_exact": str(prediction_error), "assessments": assessments,
            "scope": "Exact local held-input proxy diagnostics; no global ZOCBF, recursive feasibility, rollover model or new controller certified"}
