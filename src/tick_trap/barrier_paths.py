"""Linear high-order barrier implications for exact polynomial held paths."""

from .numbers import nonnegative, positive, q
from .polynomial import certify_sign


def auxiliary_polynomial(geometric, lambda1):
    """Coefficients of psi(t)=h_dot(t)+lambda1*h(t), in ascending order."""
    geometric, lambda1 = tuple(q(c) for c in geometric), positive(lambda1, "lambda1")
    if not geometric:
        raise ValueError("Expected a nonempty geometric polynomial")
    return tuple(lambda1*c+((i+1)*geometric[i+1] if i+1 < len(geometric) else 0)
                 for i, c in enumerate(geometric))


def certify_auxiliary_path(geometric, lambda1, duration, tolerance="1e-10", max_subdivisions=256):
    """Certify psi and derive h>=0 by an integrating factor, without querying h.

    h(0)>=0 and psi>=0 imply (exp(lambda1*t)*h(t))_dot>=0, hence
    h(t)>=exp(-lambda1*t)*h(0)>=0. This inference is a sign guarantee, not
    a numerical enclosure of the geometric minimum. Failed/unknown psi proofs
    give no geometric conclusion. A negative psi witness need not mean h<0.
    """
    geometric, lambda1 = tuple(q(c) for c in geometric), positive(lambda1, "lambda1")
    if not geometric:
        raise ValueError("Expected a nonempty geometric polynomial")
    initial = nonnegative(geometric[0], "initial h")
    duration = positive(duration, "duration")
    psi = auxiliary_polynomial(geometric, lambda1)
    cert = certify_sign(psi, duration, tolerance, max_subdivisions)
    implication = {"rule": "linear_comparison", "initial_h_exact": str(initial),
                   "lambda1_exact": str(lambda1), "duration_exact": str(duration),
                   "status": "safe" if cert.status == "safe" else "not_certified"}
    return cert, implication
