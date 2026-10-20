"""Scalar safety filters with exact projection and independently checked residuals.

Published conditions are specialized to a wall double integrator. These are not
reproductions of the papers' full experiments. See docs/methods.md.
"""

from dataclasses import dataclass, field
from fractions import Fraction

from .numbers import positive, q, sqrt_upper

METHODS = ("nominal", "continuous_cbf", "endpoint", "breeden", "breeden_reachable",
           "breeden_second_order", "zocbf", "exact_hold")


@dataclass(frozen=True)
class Decision:
    status: str
    action: Fraction | None = None
    residual: Fraction | None = None
    reason: str = ""
    details: dict = field(default_factory=dict)


def inequality_residual(coefficient, action, rhs):
    """Positive means violation of coefficient * action >= rhs."""
    return q(rhs)-q(coefficient)*q(action)


def decide(method, state, nominal, duration, a_max, tau="0.3", gain=2, gamma=1):
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}")
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    tau, gain = positive(tau, "tau"), positive(gain, "CBF gain")
    gamma = positive(gamma, "gamma")
    if gamma > 1:
        raise ValueError("gamma must be in (0,1]")
    nominal = max(-a_max, min(a_max, q(nominal)))
    if state.d < 0:
        return Decision("outside_domain", reason="Initial geometric constraint is violated")
    if method == "nominal":
        return Decision("feasible", nominal, details={"guarantee": "none"})
    if method == "exact_hold":
        if state.viability_margin(a_max) < 0:
            return Decision("infeasible", reason="Outside the ideal wall viability kernel")

        def admissible(u):
            return (state.minimum(u, duration)[0] >= 0
                    and state.at(u, duration).viability_margin(a_max) >= 0)

        if not admissible(-a_max):
            raise ArithmeticError("Braking reference violated its analytical invariant")
        lower, upper = -a_max, nominal
        if admissible(nominal):
            return Decision("feasible", nominal, details={"guarantee": "hold safety and terminal viability"})
        for _ in range(64):
            middle = (lower+upper)/2
            if admissible(middle):
                lower = middle
            else:
                upper = middle
        return Decision("feasible", lower, details={
            "guarantee": "hold safety and terminal viability",
            "projection_error_bound_exact": str(upper-lower)})

    details = {}
    if method in ("continuous_cbf", "breeden", "breeden_reachable", "breeden_second_order"):
        barrier = state.d-tau*state.v
        if barrier < 0:
            return Decision("outside_domain", reason="d-tau*v < 0: outside this CBF's initial set",
                            details={"barrier_exact": str(barrier)})
        margin = Fraction(0)
        if method == "breeden":
            velocity_bound = abs(state.v)+a_max*duration
            delta = sqrt_upper(velocity_bound**2+a_max**2)
            lipschitz = 1+gain*sqrt_upper(1+tau**2)
            margin = lipschitz*duration*delta
            details = {"source": "Breeden et al. 2021, Theorem 1, Eq. (11)",
                       "reachable_speed_bound_exact": str(velocity_bound),
                       "lipschitz_sum_upper_exact": str(lipschitz),
                       "flow_norm_upper_exact": str(delta), "margin_exact": str(margin)}
        elif method == "breeden_reachable":
            # Breeden v1 Eq. (14): the reachable-error functional has a positive
            # input kernel. Constant +a maximizes it at each time; its time
            # polynomial is convex, so its supremum is at 0 or T (closure).
            linear = gain*state.v+a_max*(1+gain*tau)
            quadratic = gain*a_max/2
            endpoint = linear*duration+quadratic*duration**2
            margin = max(Fraction(0), endpoint)
            details = {"source": "Breeden et al. 2103.03677v1, Theorem 2, Eq. (14)",
                       "margin_exact": str(margin),
                       "reachable_error_polynomial_exact": ["0", str(linear), str(quadratic)],
                       "supremum_time_exact": str(duration if endpoint > 0 else Fraction(0)),
                       "supremum_control_exact": str(a_max),
                       "reachability_scope": "all measurable admissible acceleration histories, closed-horizon supremum"}
        elif method == "breeden_second_order":
            # Paper H=-d+tau*v has H_ddot=u under a hold, so eta=a exactly.
            # This published condition fixes its effective gain to gamma/T.
            margin = a_max*duration/2
            details = {"source": "Breeden et al. 2103.03677v1, Theorem 3, Eqs. (18)-(19)",
                       "second_derivative_upper_exact": str(a_max), "margin_exact": str(margin),
                       "effective_gain_exact": str(gamma/duration)}
        effective_gain = gamma/duration if method == "breeden_second_order" else gain
        bound = (effective_gain*barrier-state.v-margin)/tau
    else:
        margin = Fraction(0)
        if method == "zocbf":
            velocity_bound = abs(state.v)+a_max*duration
            # h=d has gradient norm 1. This bounds the flow on the entire
            # local reachable tube, including any potential unsafe portion.
            margin = duration*sqrt_upper(velocity_bound**2+a_max**2)
            details = {"source": "Tan et al. 2411.17079v2, Eq. (4), Lemma 1",
                       "delta_exact": str(margin),
                       "reachable_speed_bound_exact": str(velocity_bound)}
        bound = 2*(gamma*state.d-state.v*duration-margin)/duration**2
    details["upper_action_bound_exact"] = str(bound)
    if bound < -a_max:
        return Decision("infeasible", reason="Safety condition and actuator limits do not intersect",
                        details=details)
    action = min(nominal, bound)
    residual = inequality_residual(-1, action, -bound)
    if residual > 0 or abs(action) > a_max:
        raise ArithmeticError("Returned action violated its exact scalar constraints")
    return Decision("feasible", action, residual, details=details)
