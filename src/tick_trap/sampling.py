"""A rational specialization of Liu et al. 2511.11897v1, Eqs. (15)/(22).

Only static circles, exact double-integrator holds, and linear class-K gains.
The candidate-specific derivative bound is computed from the actual polynomial;
the paper's quadrature approximation and slack-penalized QP are not reproduced.
"""

from fractions import Fraction

from .numbers import nonnegative, positive, vector2
from .polynomial import evaluate


def exp_negative_upper(value, tolerance="1e-18"):
    """Return exp(-value) <= result <= exp(-value)+tolerance, rationally.

    Positive Taylor terms enclose exp(value) using a geometric tail. Reciprocal
    endpoints reverse the enclosure. Large arguments use exp(1)>2, avoiding
    enormous intermediate powers. No floating-point transcendental is trusted.
    """
    value, tolerance = nonnegative(value), positive(tolerance, "tolerance")
    if value == 0:
        return Fraction(1)
    cutoff, power = 0, 1
    while Fraction(1, power) > tolerance:
        cutoff, power = cutoff+1, power*2
    if value >= cutoff:
        return Fraction(1, power)
    total, term, degree = Fraction(1), Fraction(1), 0
    while True:
        next_term = term*value/(degree+1)
        ratio = value/(degree+2)
        if ratio < 1:
            tail = next_term/(1-ratio)
            upper, lower = 1/total, 1/(total+tail)
            if upper-lower <= tolerance:
                return upper
        total += next_term
        term, degree = next_term, degree+1


def quadratic_absolute_bound(coefficients, duration):
    """Exact max |q(t)| for a quadratic, including endpoints and its vertex."""
    duration = positive(duration, "duration")
    coefficients = tuple(Fraction(c) for c in coefficients)
    if len(coefficients) != 3:
        raise ValueError("Expected three quadratic coefficients")
    points = [Fraction(0), duration]
    if coefficients[2]:
        vertex = -coefficients[1]/(2*coefficients[2])
        if 0 < vertex < duration:
            points.append(vertex)
    witness = max(points, key=lambda t: abs(evaluate(coefficients, t)))
    return abs(evaluate(coefficients, witness)), witness


def sacbf_assessment(state, action, obstacle, duration, lambda1=2, lambda2=2, relaxed=False):
    """Assess one candidate against the unrelaxed or omega=0 SACBF condition.

    Relaxed acceptance is the existence envelope over nonnegative slack, not the
    optimizer's preferred slack. Both preserve h and psi=h_dot+lambda1*h on this
    hold when h(0),psi(0)>=0. No future input or recursive feasibility is assumed.
    """
    duration = positive(duration, "duration")
    lambda1, lambda2 = positive(lambda1, "lambda1"), positive(lambda2, "lambda2")
    action = vector2(action)
    h = obstacle.polynomial(state, action)
    psi = tuple(lambda1*h[i]+((i+1)*h[i+1] if i+1 < len(h) else 0) for i in range(len(h)))
    second = (2*psi[2], 6*psi[3], 12*psi[4])
    bound, witness = quadratic_absolute_bound(second, duration)
    decay = Fraction(0) if relaxed else exp_negative_upper(lambda2*duration)
    target = decay*psi[0]
    margin = psi[0]+duration*psi[1]-bound*duration**2/2-target
    domain = h[0] >= 0 and psi[0] >= 0
    return {"accepted": domain and margin >= 0, "in_domain": domain,
            "h_exact": str(h[0]), "psi_exact": str(psi[0]), "psi_dot_exact": str(psi[1]),
            "margin_exact": str(margin), "target_exact": str(target),
            "decay_upper_exact": str(decay), "relaxation": "omega=0" if relaxed else "omega=1",
            "second_derivative_exact": [str(c) for c in second],
            "second_derivative_bound_exact": str(bound), "bound_witness_time_exact": str(witness)}
