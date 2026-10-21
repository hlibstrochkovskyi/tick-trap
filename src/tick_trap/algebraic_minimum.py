"""Offline rational minimum enclosures from stationary roots and interval Horner.

Classical Sturm counting and bisection supply a reference independent of the
Bernstein engine. No controller uses this code or its additional offline work.
"""

from fractions import Fraction as F

from .algebraic_reference import _derivative, _exact_divide, _gcd, _monic, _sturm, _trim, _value, _variations


def _interval_value(polynomial, left, right):
    lower = upper = polynomial[-1]
    for coefficient in reversed(polynomial[:-1]):
        products = (lower*left, lower*right, upper*left, upper*right)
        lower, upper = min(products)+coefficient, max(products)+coefficient
    return lower, upper


def _open_roots(square_free, left, right):
    # Remove endpoint roots first. The remaining Sturm evaluations have nonzero
    # endpoints, avoiding ambiguity about open versus half-open conventions.
    counting, removed = square_free, []
    for endpoint in (left, right):
        if _value(counting, endpoint) == 0:
            counting = _exact_divide(counting, (-endpoint, F(1)))
            removed.append(str(endpoint))
    chain = _sturm(counting)
    variations = (_variations(chain, left), _variations(chain, right))
    count = variations[0]-variations[1]
    if not 0 <= count < len(counting):
        raise ArithmeticError("Invalid stationary root count")
    return count, {"count_polynomial_exact": [str(c) for c in counting],
                   "removed_endpoint_factors_exact": removed,
                   "sturm_chain_exact": [[str(c) for c in row] for row in chain],
                   "endpoint_variations": list(variations), "open_roots": count}


def enclose_algebraic_minimum(coefficients, duration, tolerance="1e-10", max_subdivisions=4096):
    """Bound min p on [0,T] for exact rational p of degree at most four.

    Every global minimum is at a domain endpoint or stationary point. Root-count
    boxes cover all open-interval stationary points, including repeated ones;
    interval Horner bounds their values. Evaluated rational samples bound the
    minimum from above. Budget/width stopping never resolves an unknown sign.
    The split count does not bound exact-algebra work or elapsed execution time.
    """
    values = list(coefficients)
    if not values or any(isinstance(c, (float, bool)) for c in [*values, duration, tolerance]):
        raise ValueError("Minimum reference requires nonempty exact rational inputs")
    polynomial = _trim(tuple(F(c) for c in values))
    end, tolerance = F(duration), F(tolerance)
    if len(polynomial) > 5 or end <= 0 or tolerance <= 0:
        raise ValueError("Require degree <= 4, positive duration and positive tolerance")
    if isinstance(max_subdivisions, bool) or not isinstance(max_subdivisions, int) or max_subdivisions < 0:
        raise ValueError("max_subdivisions must be a nonnegative integer")
    derivative = _derivative(polynomial)
    fixed = [(_value(polynomial, F(0)), F(0)), (_value(polynomial, end), end)]
    upper, witness = min(fixed)
    square_free, initial_count, initial_proof = None, None, None
    boxes, points, calls, subdivisions = [], [], 0, 0

    def box(left, right, roots, proof):
        nonlocal upper, witness
        lower, range_upper = _interval_value(polynomial, left, right)
        middle = (left+right)/2
        value = _value(polynomial, middle)
        if (value, middle) < (upper, witness):
            upper, witness = value, middle
        return {"left": left, "right": right, "roots": roots, "lower": lower,
                "range_upper": range_upper, "proof": proof}

    if len(polynomial) > 1:
        square_free = _monic(_exact_divide(derivative, _gcd(derivative, _derivative(derivative))))
        initial_count, initial_proof = _open_roots(square_free, F(0), end)
        calls += 1
        if initial_count:
            boxes.append(box(F(0), end, initial_count, initial_proof))

    def lower_bound():
        lower = min([v for v, t in fixed]+[b["lower"] for b in boxes])
        if lower > upper:
            raise ArithmeticError("Minimum enclosure contradicts an evaluated upper witness")
        return lower

    lower = lower_bound()
    while upper-lower > tolerance and subdivisions < max_subdivisions:
        if not boxes:
            raise ArithmeticError("Missing stationary coverage for a nonzero enclosure width")
        chosen = min(range(len(boxes)), key=lambda i: (boxes[i]["lower"], boxes[i]["left"]))
        parent = boxes.pop(chosen)
        left, right = parent["left"], parent["right"]
        middle = (left+right)/2
        is_root = _value(square_free, middle) == 0
        if is_root:
            value = _value(polynomial, middle)
            fixed.append((value, middle))
            points.append({"time_exact": str(middle), "value_exact": str(value)})
            if (value, middle) < (upper, witness):
                upper, witness = value, middle
        children = []
        for a, b in ((left, middle), (middle, right)):
            count, proof = _open_roots(square_free, a, b)
            calls += 1
            if count:
                children.append(box(a, b, count, proof))
        if sum(b["roots"] for b in children)+is_root != parent["roots"]:
            raise ArithmeticError("Bisection lost a stationary root")
        boxes.extend(children)
        subdivisions += 1
        lower = lower_bound()
    if initial_count is not None and sum(b["roots"] for b in boxes)+len(points) != initial_count:
        raise ArithmeticError("Final stationary-root coverage changed")
    precision = upper-lower <= tolerance
    return {"method": "stationary_sturm_interval_horner", "goal": "minimum",
            "status": "safe" if lower >= 0 else "unsafe" if upper < 0 else "unknown",
            "lower_exact": str(lower), "upper_exact": str(upper), "witness_time_exact": str(witness),
            "precision_reached": precision, "budget_exhausted": not precision and subdivisions >= max_subdivisions,
            "stopping_reason": "precision_reached" if precision else "budget_exhausted",
            "subdivisions": subdivisions, "root_count_calls": calls,
            "polynomial_exact": [str(c) for c in polynomial], "duration_exact": str(end),
            "tolerance_exact": str(tolerance), "max_subdivisions": max_subdivisions,
            "derivative_exact": [str(c) for c in derivative],
            "square_free_derivative_exact": None if square_free is None else [str(c) for c in square_free],
            "stationary_roots_open": initial_count, "initial_root_count_proof": initial_proof,
            "exact_stationary_points": points,
            "stationary_boxes": [{"left_exact": str(b["left"]), "right_exact": str(b["right"]),
                                   "roots": b["roots"], "value_lower_exact": str(b["lower"]),
                                   "value_upper_exact": str(b["range_upper"]), "root_count_proof": b["proof"]}
                                  for b in sorted(boxes, key=lambda b: b["left"])],
            "scope": "Offline degree<=4 minimum enclosure, independent of Bernstein; constant polynomials need no stationary-root isolation. No online unknown, model assumption or execution decision is changed"}
