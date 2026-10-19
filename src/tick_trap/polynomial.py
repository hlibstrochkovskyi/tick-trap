"""Polynomial estimates and validated rational Bernstein minimum enclosures."""

from dataclasses import dataclass
from fractions import Fraction
from heapq import heappop, heappush
from math import comb

from .numbers import finite_float, nonnegative, positive, q


def evaluate(coefficients, t):
    result = 0
    for c in reversed(coefficients):
        result = result*t + c
    return result


def _trim(coefficients):
    coefficients = list(coefficients)
    if not coefficients:
        raise ValueError("Polynomial must have at least one coefficient")
    while len(coefficients) > 1 and coefficients[-1] == 0:
        coefficients.pop()
    return coefficients


def stationary_estimate(coefficients, duration):
    """Numerical derivative-root isolation. An estimate, never a certificate.

    Normalize time to [0,1], recursively split at derivative roots, then bisect
    monotone pieces. Repeated roots are included using a floating tolerance.
    """
    duration = positive(duration, "duration")
    exact = _trim([q(c) * duration**i for i, c in enumerate(coefficients)])
    scale = max(abs(c) for c in exact) or 1
    coefficients = [finite_float(c/scale) for c in exact]

    def roots(c):
        c = _trim(c)
        if len(c) == 1:
            return []
        if len(c) == 2:
            r = -c[0]/c[1]
            return [r] if 0 <= r <= 1 else []
        critical = roots([i*c[i] for i in range(1, len(c))])
        points = sorted(set([0., *critical, 1.]))
        found = [t for t in points if abs(evaluate(c, t)) < 1e-13]
        for left, right in zip(points, points[1:]):
            fl, fr = evaluate(c, left), evaluate(c, right)
            if fl*fr < 0:
                for _ in range(64):
                    middle = (left+right)/2
                    fm = evaluate(c, middle)
                    if fl*fm <= 0:
                        right = middle
                    else:
                        left, fl = middle, fm
                found.append((left+right)/2)
        return sorted(set(found))

    critical = roots([i*coefficients[i] for i in range(1, len(coefficients))]) if len(coefficients) > 1 else []
    t = min([0., 1., *critical], key=lambda x: evaluate(coefficients, x))
    return {"minimum_estimate": finite_float(evaluate(coefficients, t)*scale),
            "time_estimate": t*finite_float(duration),
            "critical_times_estimate": [x*finite_float(duration) for x in critical]}


def _bernstein(coefficients, duration):
    coefficients = _trim([q(c) for c in coefficients])
    degree = len(coefficients)-1
    power = [c*duration**i for i, c in enumerate(coefficients)]
    return tuple(sum(power[j]*Fraction(comb(k, j), comb(degree, j))
                     for j in range(k+1)) for k in range(degree+1))


def _split(b):
    left, right = [b[0]], [b[-1]]
    while len(b) > 1:
        b = tuple((x+y)/2 for x, y in zip(b, b[1:]))
        left.append(b[0])
        right.append(b[-1])
    return tuple(left), tuple(reversed(right))


@dataclass(frozen=True)
class Certificate:
    status: str
    lower: Fraction
    upper: Fraction
    witness_time: Fraction
    subdivisions: int
    precision_reached: bool
    budget_exhausted: bool
    goal: str = "minimum"

    @property
    def stopping_reason(self):
        if self.goal == "sign" and self.status != "unknown":
            return "sign_proved"
        return "precision_reached" if self.precision_reached else "budget_exhausted"


def certify_minimum(coefficients, duration, tolerance="1e-10", max_subdivisions=4096):
    """Enclose min h(t) with exact arithmetic; h>=0 includes boundary contact.

    The convex hull of Bernstein coefficients encloses the polynomial range.
    Branch on the smallest lower bound and retain an evaluated upper witness.
    Budget or precision limits never turn an unresolved sign into 'safe'.
    """
    return _certify(coefficients, duration, tolerance, max_subdivisions, "minimum")


def certify_sign(coefficients, duration, tolerance="1e-10", max_subdivisions=4096):
    """Prove nonnegativity or a negative witness, stopping once either is known.

    The returned bounds still enclose the minimum but need not meet the requested
    width. Precision and subdivision limits stop unresolved work with `unknown`.
    Boundary contact is allowed; exact zero is safe only with a nonnegative bound.
    """
    return _certify(coefficients, duration, tolerance, max_subdivisions, "sign")


def _certify(coefficients, duration, tolerance, max_subdivisions, goal):
    duration, tolerance = positive(duration, "duration"), positive(tolerance, "tolerance")
    if isinstance(max_subdivisions, bool) or not isinstance(max_subdivisions, int) or max_subdivisions < 0:
        raise ValueError("max_subdivisions must be a nonnegative integer")
    b = _bernstein(coefficients, duration)
    upper, witness = min((b[0], Fraction(0)), (b[-1], duration))
    heap = [(min(b), 0, Fraction(0), duration, b)]
    count = 0
    while heap and upper-heap[0][0] > tolerance and count < max_subdivisions:
        if goal == "sign" and (heap[0][0] >= 0 or upper < 0):
            break
        lower, _, left, right, b = heappop(heap)
        if lower >= upper:
            continue
        l, r = _split(b)
        middle = (left+right)/2
        if l[-1] < upper:
            upper, witness = l[-1], middle
        count += 1
        for index, lo, hi, child in ((2*count, left, middle, l), (2*count+1, middle, right, r)):
            bound = min(child)
            if bound < upper:
                heappush(heap, (bound, index, lo, hi, child))
    lower = min(upper, heap[0][0]) if heap else upper
    status = "safe" if lower >= 0 else "unsafe" if upper < 0 else "unknown"
    precision = upper-lower <= tolerance
    return Certificate(status, lower, upper, witness, count, precision,
                       not precision and count >= max_subdivisions and (goal == "minimum" or status == "unknown"), goal)
