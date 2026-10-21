# Independent polynomial sign reference

`algebraic_reference.py` is an offline, exact rational implementation of classical
square-free decomposition and Sturm root counting for degree at most four. It
does not import the Bernstein certificate engine or its polynomial evaluation.
It supplies a second sign decision, **not a minimum enclosure**, a new online
algorithm, or an independent validation of the dynamics model.

For nonzero rational p, Euclidean GCD and exact division decompose
`p = a product(f_i ** i)` into monic square-free factors. Reconstruction is checked
exactly. Write `p = q s²`, with `q = a product(f_i for odd i)` and s the remaining
half multiplicities. Thus q is square-free, and its sign away from zeros is p's
sign. An interior root of q changes sign and proves p negative on some open
subinterval. With no interior roots of q, one nonroot rational interior probe
settles its constant sign. Zeros of s are allowed contact. Endpoint values are
checked separately. This also covers polynomials with no real roots.

Endpoint factors are divided out **only for root counting**. The original q is
used for the sign probe; dividing by `(t-T)` otherwise could reverse its sign.
For the resulting endpoint-nonzero polynomial the Sturm chain is
`q, q', -rem(q,q'), ...`; zeros in a chain evaluation are skipped. The difference
of sign variations at 0 and T counts interior roots exactly. Degree bounds give
enough rational probes to find one not at a root. There is no numerical epsilon
or floating point conversion in this reference.

These are established algebraic methods. Primary implementation references:
[Sage polynomial documentation](https://doc.sagemath.org/html/en/reference/polynomial_rings/sage/rings/polynomial/polynomial_element.html)
and [Classical Sturmian sequences](https://arxiv.org/abs/1904.03789).
Our short implementation is independently coded; Sage is not installed or called.

Tests cover known factorizations of every degree 1–4 on a finite rational root
set, both global signs, endpoint roots, repeated roots, nondyadic tangencies,
near tangencies, physical h/psi polynomials, and positive/negative perturbations
down to 10^-400. These checks support implementation correctness; they are not a
formal proof of the Python program or an exhaustive test of all rational inputs.

An algebraic `safe` result never changes an online `unknown` certificate or its
recorded work budget. Offline comparisons store both answers. A disagreement
between resolved answers is an error. Reference work is excluded from timed
online predicates and measured separately.

The optional `sturm` strategy in `certification-study` additionally reruns this
same algebra inside the measured region on both h and psi. It rebuilds all
polynomials and sign evidence, rather than looking up offline answers. Its
single parameter-free measurement group is reused across numerical settings.
It is an offline cost comparator, not an online controller, and never replaces
a recorded Bernstein unknown. Zero subdivisions do not imply zero work: exact
rational coefficient growth is not bounded by a Bernstein split allowance or
a hard execution deadline. Agreement with its own offline reference is not
an independent validation of the algebraic method; the factored test cases and
resolved Bernstein comparisons supply separate checks.

The later [independent minimum reference](algebraic-minimum.md) bounds numerical
minimum values through stationary-root coverage and rational interval Horner.
It shares this module's exact polynomial arithmetic and Sturm implementation,
while remaining independent of Bernstein. Its width and sign fields remain
distinct from this module's complete sign decision; see the
[550-polynomial validation](validation-minimum-reference.md).
