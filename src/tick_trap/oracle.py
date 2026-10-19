"""Safety evaluation: wall clearance in m; circle barrier in m²."""

from math import sqrt
from time import perf_counter_ns

from .numbers import positive, q
from .polynomial import certify_minimum, evaluate, stationary_estimate


def wall_interval(state, u, duration):
    start = perf_counter_ns()
    minimum, time = state.minimum(u, duration)
    end = state.at(u, duration)
    return {"sampled_safe": state.d >= 0 and end.d >= 0,
            "continuous_status": "safe" if minimum >= 0 else "unsafe",
            "minimum_clearance": float(minimum), "minimum_clearance_exact": str(minimum),
            "witness_time": float(time), "witness_time_exact": str(time),
            "certification_ns": perf_counter_ns()-start}


def circle_interval(state, u, circle, duration, tolerance="1e-10", max_subdivisions=4096):
    duration = positive(duration, "duration")
    polynomial = circle.polynomial(state, u)
    start = perf_counter_ns()
    estimate = stationary_estimate(polynomial, duration)
    estimate_ns = perf_counter_ns()-start
    start = perf_counter_ns()
    cert = certify_minimum(polynomial, duration, tolerance, max_subdivisions)
    cert_ns = perf_counter_ns()-start
    return {"sampled_safe": polynomial[0] >= 0 and evaluate(polynomial, duration) >= 0,
            "continuous_status": cert.status,
            "barrier_units": "m^2", "polynomial_exact": [str(c) for c in polynomial],
            **estimate, "clearance_estimate": sqrt(max(0, estimate["minimum_estimate"]+float(circle.radius**2)))-float(circle.radius),
            "minimum_lower_exact": str(cert.lower), "minimum_upper_exact": str(cert.upper),
            "witness_time_exact": str(cert.witness_time),
            "precision_reached": cert.precision_reached, "budget_exhausted": cert.budget_exhausted,
            "subdivisions": cert.subdivisions, "estimation_ns": estimate_ns,
            "certification_ns": cert_ns}
