"""Scalar safety filters with exact projection and independently checked residuals.

Published conditions are specialized to a wall double integrator. These are not
reproductions of the papers' full experiments. See docs/methods.md.
"""

from dataclasses import dataclass, field
from fractions import Fraction

from .numbers import positive, q, sqrt_upper

METHODS = ("nominal", "continuous_cbf", "endpoint", "breeden", "zocbf", "exact_hold")


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
    if method in ("continuous_cbf", "breeden"):
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
        bound = (gain*barrier-state.v-margin)/tau
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
