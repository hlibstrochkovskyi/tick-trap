"""Offline checks of positive barrier scaling and exact time reparameterization."""

from fractions import Fraction as F

from .algebraic_minimum import enclose_algebraic_minimum
from .algebraic_reference import _trim
from .polynomial import certify_minimum, certify_sign

METHODS = ("bernstein_minimum", "bernstein_sign", "stationary_minimum")
TIME_BASES = ("physical", "unit_interval")


def _exact(value):
    if isinstance(value, (bool, float)):
        raise ValueError("Representation audit requires exact rational inputs")
    return F(value)


def transformed_polynomial(coefficients, duration, scale=1, time_basis="physical"):
    values = list(coefficients)
    if not values:
        raise ValueError("Require a nonempty polynomial")
    polynomial = _trim(tuple(_exact(c) for c in values))
    duration, scale = _exact(duration), _exact(scale)
    if len(polynomial) > 5 or duration <= 0 or scale <= 0 or time_basis not in TIME_BASES:
        raise ValueError("Require degree <=4, positive duration/scale and a supported time basis")
    time_factor = duration if time_basis == "unit_interval" else F(1)
    transformed = tuple(scale*c*time_factor**i for i, c in enumerate(polynomial))
    return transformed, duration/time_factor, time_factor, scale


def representation_certificate(method, coefficients, duration, tolerance, budget, scale=1, time_basis="physical"):
    """Evaluate a representation at the supplied *represented-value* tolerance.

    Return exact raw and original-value/time bounds. The caller must state whether
    tolerance is held fixed or scaled; no backend, controller or default changes.
    """
    if method not in METHODS:
        raise ValueError("Unsupported representation-audit method")
    tolerance = _exact(tolerance)
    if tolerance <= 0 or isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("Require positive tolerance and a nonnegative integer budget")
    polynomial, end, time_factor, scale = transformed_polynomial(coefficients, duration, scale, time_basis)
    if method == "stationary_minimum":
        result = enclose_algebraic_minimum(polynomial, end, tolerance, budget)
        certificate = {key: result[key] for key in
                       ("goal", "status", "lower_exact", "upper_exact", "witness_time_exact", "subdivisions",
                        "precision_reached", "budget_exhausted", "stopping_reason", "root_count_calls", "stationary_roots_open")}
        # Keep final root boxes/points, but not duplicate every intermediate Sturm
        # chain in a representation sweep. Exact regeneration can rebuild them.
        certificate["stationary_boxes"] = [{k: v for k, v in b.items() if k != "root_count_proof"}
                                             for b in result["stationary_boxes"]]
        certificate["exact_stationary_points"] = result["exact_stationary_points"]
    else:
        function = certify_sign if method == "bernstein_sign" else certify_minimum
        result = function(polynomial, end, tolerance, budget)
        certificate = {"goal": result.goal, "status": result.status, "lower_exact": str(result.lower),
                       "upper_exact": str(result.upper), "witness_time_exact": str(result.witness_time),
                       "subdivisions": result.subdivisions, "precision_reached": result.precision_reached,
                       "budget_exhausted": result.budget_exhausted, "stopping_reason": result.stopping_reason}
    normalized = {k: v for k, v in certificate.items() if k not in
                  ("lower_exact", "upper_exact", "witness_time_exact", "stationary_boxes", "exact_stationary_points")}
    normalized.update(lower_exact=str(F(certificate["lower_exact"])/scale),
                      upper_exact=str(F(certificate["upper_exact"])/scale),
                      witness_time_exact=str(F(certificate["witness_time_exact"])*time_factor))
    return {"polynomial_exact": [str(c) for c in polynomial], "duration_exact": str(end),
            "time_factor_exact": str(time_factor), "value_scale_exact": str(scale),
            "tolerance_exact": str(tolerance), "original_value_tolerance_exact": str(tolerance/scale),
            "input_max_numerator_bits": max(abs(c.numerator).bit_length() for c in (*polynomial, end, tolerance)),
            "input_max_denominator_bits": max(c.denominator.bit_length() for c in (*polynomial, end, tolerance)),
            "certificate": certificate, "original_coordinates": normalized}
