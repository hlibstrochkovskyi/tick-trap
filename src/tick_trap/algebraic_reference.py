"""Independent exact sign reference for rational polynomials of degree <= 4.

Classical square-free decomposition and Sturm root counting, implemented without
the Bernstein engine, its evaluation routine, or floating point root estimates.
This resolves signs (including exact zeros), not numerical minimum enclosures.
It is an offline cross-check, never an automatic replacement for online unknowns.
"""

from fractions import Fraction


def _trim(p):
    p = list(p)
    while len(p) > 1 and not p[-1]:
        p.pop()
    return tuple(p)


def _value(p, x):
    return sum(c*x**i for i, c in enumerate(p))


def _derivative(p):
    return tuple(i*p[i] for i in range(1, len(p))) or (Fraction(0),)


def _multiply(a, b):
    c = [Fraction(0)]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            c[i+j] += x*y
    return _trim(c)


def _divide(a, b):
    if b == (0,):
        raise ZeroDivisionError("Zero polynomial divisor")
    remainder = list(a)
    quotient = [Fraction(0)]*max(1, len(a)-len(b)+1)
    while len(remainder) >= len(b) and remainder != [0]:
        offset, coefficient = len(remainder)-len(b), remainder[-1]/b[-1]
        quotient[offset] = coefficient
        for i, c in enumerate(b):
            remainder[i+offset] -= coefficient*c
        remainder = list(_trim(remainder))
    return _trim(quotient), tuple(remainder)


def _exact_divide(a, b):
    quotient, remainder = _divide(a, b)
    if remainder != (0,):
        raise ArithmeticError("Nonexact square-free division")
    return quotient


def _monic(p):
    return tuple(c/p[-1] for c in p)


def _gcd(a, b):
    while b != (0,):
        a, b = b, _divide(a, b)[1]
    return _monic(a)


def _square_free(p):
    """Yun's characteristic-zero square-free decomposition over the rationals."""
    f = _monic(p)
    repeated = _gcd(f, _derivative(f))
    remaining = _exact_divide(f, repeated)
    factors, multiplicity = [], 1
    while remaining != (1,):
        common = _gcd(remaining, repeated)
        factor = _exact_divide(remaining, common)
        if factor != (1,):
            factors.append((factor, multiplicity))
        remaining, repeated = common, _exact_divide(repeated, common)
        multiplicity += 1
    rebuilt = (p[-1],)
    for factor, multiplicity in factors:
        for _ in range(multiplicity):
            rebuilt = _multiply(rebuilt, factor)
    if rebuilt != p:
        raise ArithmeticError("Square-free reconstruction failed")
    return factors


def _sturm(p):
    chain = [p]
    if len(p) > 1:
        chain.append(_derivative(p))
        while True:
            remainder = _divide(chain[-2], chain[-1])[1]
            if remainder == (0,):
                break
            chain.append(tuple(-c for c in remainder))
    return chain


def _variations(chain, x):
    signs = [1 if y > 0 else -1 for p in chain if (y := _value(p, x)) != 0]
    return sum(a != b for a, b in zip(signs, signs[1:]))


def exact_sign_reference(coefficients, duration):
    """Decide p>=0 on [0,T] exactly, allowing boundary contact.

    p = odd * square, where square is nonnegative. Every interior root of
    the square-free odd factor changes sign, so its presence proves an unsafe
    open interval. Without such roots, its sign at one nonroot interior rational
    point determines the sign everywhere except the (safe) zeros. Endpoint roots
    are removed only for counting; the original odd factor determines the sign.
    Returned exact algebraic evidence is not a minimum value or contact model.
    """
    values = list(coefficients)
    if not values or any(isinstance(c, (float, bool)) for c in [*values, duration]):
        raise ValueError("Reference requires nonempty exact rational inputs")
    p, end = _trim(tuple(Fraction(c) for c in values)), Fraction(duration)
    if len(p) > 5 or end <= 0:
        raise ValueError("Reference supports degree <= 4 and positive duration")
    endpoints = (_value(p, Fraction(0)), _value(p, end))
    if len(p) == 1:
        return {"status": "safe" if p[0] >= 0 else "unsafe", "method": "exact_constant",
                "value_exact": str(p[0]), "duration_exact": str(end)}
    factors = _square_free(p)
    odd = (p[-1],)
    for factor, multiplicity in factors:
        if multiplicity % 2:
            odd = _multiply(odd, factor)
    count_polynomial = odd
    for endpoint in (Fraction(0), end):
        if _value(count_polynomial, endpoint) == 0:
            count_polynomial = _exact_divide(count_polynomial, (-endpoint, Fraction(1)))
    chain = _sturm(count_polynomial)
    variations = (_variations(chain, Fraction(0)), _variations(chain, end))
    roots = variations[0]-variations[1]
    # A degree n polynomial has at most n roots; n+1 interior probes suffice.
    probe = next(end*Fraction(i, len(odd)+1) for i in range(1, len(odd)+1)
                 if _value(odd, end*Fraction(i, len(odd)+1)) != 0)
    probe_value = _value(odd, probe)
    unsafe = min(endpoints) < 0 or roots > 0 or probe_value < 0
    return {"status": "unsafe" if unsafe else "safe", "method": "square_free_sturm",
            "duration_exact": str(end), "endpoint_values_exact": [str(x) for x in endpoints],
            "leading_coefficient_exact": str(p[-1]),
            "square_free_factors": [{"coefficients_exact": [str(c) for c in f], "multiplicity": m}
                                    for f, m in factors],
            "odd_factor_exact": [str(c) for c in odd],
            "count_polynomial_exact": [str(c) for c in count_polynomial],
            "sturm_chain_exact": [[str(c) for c in s] for s in chain],
            "endpoint_variations": list(variations), "interior_odd_roots": roots,
            "probe_time_exact": str(probe), "odd_probe_value_exact": str(probe_value)}
