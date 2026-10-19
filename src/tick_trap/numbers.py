"""Exact input interpretation. Floats mean their actual binary rational value."""

from fractions import Fraction
from math import isfinite, isqrt


def q(value) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a physical quantity")
    try:
        result = Fraction(value)
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"Expected a finite rational quantity, got {value!r}") from exc
    return result


def positive(value, name="value") -> Fraction:
    result = q(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def nonnegative(value, name="value") -> Fraction:
    result = q(value)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def vector2(value):
    if len(value) != 2:
        raise ValueError("Expected a two-dimensional vector")
    return tuple(q(x) for x in value)


def sqrt_upper(value, scale=10**12) -> Fraction:
    """A rational upper enclosure of sqrt(value), using integer arithmetic."""
    value = nonnegative(value)
    n = value.numerator * scale**2
    root = isqrt(n // value.denominator)
    if root**2 * value.denominator < n:
        root += 1
    return Fraction(root, scale)


def finite_float(value):
    result = float(value)
    if not isfinite(result):
        raise ValueError("Quantity cannot be represented as a finite float")
    return result
