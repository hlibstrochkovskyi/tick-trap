# Independent stationary-point minimum enclosure

`algebraic_minimum.py` bounds the minimum of an exact rational polynomial of
degree at most four on `[0,T]`, T>0. It uses stationary-root counts and interval
Horner arithmetic, independently of Bernstein subdivision, its evaluator and
floating root estimates. It shares the existing algebraic reference's exact
Euclidean polynomial arithmetic and Sturm implementation. It is an offline
reference, not a new controller or an original numerical algorithm.

## Root coverage

For a nonconstant p, form d=p' and its monic square-free part
`s=d/gcd(d,d')`, up to a nonzero normalization. This retains every distinct
stationary point, including repeated derivative roots. Constant derivatives
have no roots. A constant p needs no stationary isolation; its returned open
root count is `null`, rather than pretending that its zero derivative has
finitely many stationary points.

Sturm variation differences count roots. The standard
[root-count convention](https://macaulay2.com/doc/Macaulay2/share/doc/Macaulay2/RealRoots/html/_sturm__Count.html)
is half-open `(a,b]`; our code first divides out any factors at a or b and then
counts the remaining roots between nonroot endpoints. This gives the number
strictly inside `(a,b)`. Domain endpoint values are evaluated separately.
The [square-free sequence documentation](https://macaulay2.com/doc/Macaulay2/share/doc/Macaulay2/RealRoots/html/_sturm__Sequence.html)
provides additional primary implementation context; Macaulay2 is not a dependency
and its software benchmarks are not reproduced here.

When a box `[a,b]` is bisected at m, the code checks exactly

```
roots(a,b) = roots(a,m) + roots(m,b) + [s(m)=0].
```

A rational root found at m is retained as an exact stationary point. Children
with zero open roots are discarded; children containing stationary roots remain
covered. Final box counts plus retained exact points must equal the initial
open root count. This handles a split landing on a root without dropping or
counting it twice. Retaining maxima and stationary inflections is harmless.

## Minimum bounds

Continuity on a compact interval ensures a global minimum exists. Fermat's
theorem places it at a domain endpoint or a stationary point in the interior.
All such points are therefore included among exact retained values and boxes.

Interval Horner evaluates p on each box using exact rational interval operations.
For an interval y and box I, multiplication uses the extrema of the four
endpoint products; adding an exact coefficient translates both bounds. Induction
through Horner's recurrence proves that the resulting range contains p(t) for
every t in I. Dependency can widen the enclosure but cannot invalidate it.

Let L be the minimum of exact endpoint/retained stationary values and all box
range lower bounds. Let U be the smallest exactly evaluated p at any retained
rational sample, with its time saved as a witness. Then

```
L <= min(p(t), t in [0,T]) <= U.
```

The code bisects the box with smallest range lower bound, breaking ties by
its left endpoint. Midpoint evaluations can improve U. The budget counts these
bisections only. Root counting, exact divisions and rational coefficient growth
also cost work; neither this budget nor a Bernstein split limit bounds elapsed
time or gives equal primitive-operation work across implementations.

## Stopping and sign semantics

The width request is reached only when `U-L<=tolerance`. Otherwise the declared
split limit ends refinement. Both cases still return a valid enclosure.

- `safe` requires L>=0.
- `unsafe` requires U<0, with an exactly evaluated negative witness.
- Otherwise the sign remains `unknown`, including a narrow interval containing zero.

These fields describe the supplied polynomial under exact rational semantics.
They are not claims about uncertain dynamics, observation, actuation or contact
physics. A separate complete Sturm sign calculation may resolve a tangency
while this numerical minimum enclosure still has an unknown sign. That result
never silently changes an online certificate or execution decision.

The output records the derivative and square-free derivative, exact stationary
points, all surviving root boxes with their counting proofs and value bounds,
upper witness, requested tolerance, split count and number of root-count calls.
Tests use independently constructed factored derivatives and their exact
stationary values, repeated roots, endpoints, nondyadic tangencies, irrational
minimizers with margins ±10^-100, and intersections with Bernstein enclosures.
This supports implementation correctness but does not formally verify the Python
program or every rational input.
