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

## Measuring cost at matched controls

`certification-study` builds the declared finite command set at each fixed state
and obtains a separate, tighter geometric/auxiliary reference audit. Only
high-order in-domain states enter its timed comparisons. Each command is tested
with relaxed SACBF, minimum refinement and sign stopping. Polynomial methods
check both properties at every obstacle, including after an earlier negative
witness, so the timed query scope is consistent. They use the same tolerance
and per-polynomial subdivision budget.

Five repeats by default are shuffled with a recorded seed for every control.
Every setting's exact evidence must remain unchanged across repeats; measurement
order and all elapsed times are retained. Reported cost includes constructing
the condition/polynomials and serializable exact evidence. Candidate generation,
nominal-action selection and offline reference certification are excluded. This
measures a fixed property predicate, not a full controller call or worst-case
execution time. The reference uses the same Bernstein engine with its separately
declared limits; it is neither a second numerical implementation nor an oracle
that always resolves tangency.

An unknown result is kept separate from rejection. SACBF rejection fails a
sufficient condition; polynomial rejection has a negative path witness. The
report separately counts excluded reference-safe controls and unresolved
reference-safe controls. If a predicate proves safety where the reference was
unknown, the reference is still recorded unknown, and that outcome is counted
explicitly. Exact contradictions against a resolved reference abort the study.

```sh
PYTHONPATH=src python -m tick_trap certification-study --config configs/certification-cost.json --output results/certification-cost
```

This writes full JSON evidence, group CSV metrics, a Markdown table and
configuration/source provenance. The default study compares four states from
the earlier audit. Its finite controls and seeded timing experiment support
specific comparisons only; broader systems and original paper experiments
remain outside its scope.
