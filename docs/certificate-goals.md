# Minimum enclosure and sign decisions

`certify_minimum` refines the rational Bernstein minimum enclosure toward a
declared absolute width. `certify_sign` uses the same initial conversion,
de Casteljau splits, branch order and evaluated witnesses, but stops as soon as
the lower bound is nonnegative or an upper witness is negative. The latter query
answers whether a held trajectory satisfies the nonnegative safety constraint.
It does not promise an equally narrow minimum enclosure.

For a polynomial in Bernstein form, the nonnegative basis functions sum to one,
so its range lies between its smallest and largest coefficients. Subdivision
retains this convex-hull bound on every child interval. The minimum of the active
lower bounds bounds the global minimum from below, while any evaluated value
bounds it from above. Therefore early stopping on these signs preserves the
safety implication. No requested width or budget can turn an unresolved sign
into a positive certificate.

Both queries return exact bounds, an evaluated upper witness, subdivision count,
the requested goal, precision/budget flags and a stopping reason. A sign-proved
answer can have `precision_reached=False`. In that case its wider interval is
still valid; it must not be advertised as meeting the width tolerance. The sign
query reports budget exhaustion only when the sign is still unresolved and the
width tolerance has not already stopped refinement. Non-dyadic tangencies may
remain unknown. Contact at zero is permitted by the mathematical model.

These are established polynomial techniques. In particular,
[Tang, Tong, Wang and Manocha, *Fast and Exact Continuous Collision Detection
with Bernstein Sign Classification*](https://wangzhendong619.github.io/papers/BSC.pdf)
reduces mesh collision queries to polynomial sign tests and distinguishes Boolean
collision queries from computing contact times. Its mesh geometry, exact
computation machinery and floating-point filters are not reproduced here. The
tick-trap change merely avoids unnecessary minimum refinement for an existing
validated sign decision; no new collision-detection method is claimed.
