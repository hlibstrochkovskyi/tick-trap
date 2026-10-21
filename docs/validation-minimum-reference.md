# Independent minimum-reference validation — 22 October 2026

The instrument now has an independently constructed numerical enclosure of the
minimum value, alongside its complete algebraic sign reference. The new
stationary-root/interval-Horner reference agrees with the existing Bernstein
enclosures on every audited polynomial. It remains an offline cross-check;
no controller, online comparison argument or execution decision changes.

All 219 tests pass. The [evidence-source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39687101692)
passes on Python 3.11–3.14. The [mathematical note](algebraic-minimum.md) derives
the root-coverage and minimum bounds, including repeated and endpoint roots.
These are classical numerical/algebraic constructions, not a new algorithm or
publication-level contribution.

## Source and evidence

Generation and exact regeneration identify clean revision
`b49b1faf4e72b582d67ec82d32f1ca3dbd42167d`, runtime source SHA-256
`f706cc0e4b6c0c3b92cfd69f42016e173beb8abd2748aac0be762fda2c036d6d`.

- [Compact counts and tangent cases](data/minimum-reference-summary.json)
- [New audit evidence archive](data/minimum-reference-evidence.tar.gz): 10 files,
  12,813,082 uncompressed bytes; 434,464 compressed bytes
- [Per-file and archive hashes](data/minimum-reference-manifest.json)

The archive records every original minimum reconstruction, independent and
matched Bernstein enclosure, root-count proof, stationary box, upper witness,
property use, numerical setting and aggregate count, plus provenance,
regeneration, report and hosted CI run/job evidence. Its SHA-256 is
`fbd9283296d6bf6432e9d1e0dcc8230d28931a917dffb9ceddc98975c3522323`.
The compact file is byte-identical to archived `compact.json`.

Its input dependency is the existing versioned
[algebraic study archive](data/algebraic-evidence.tar.gz), SHA-256
`e90628344051b0bec6a01cb4f544e08efbb648ad5216db9a34ca4d0a9552e114`,
from clean source `5a46e9469ad56fe640675a04c66aafd2a654183c`.
The new archive does not duplicate that input archive; it records the exact
archive, manifest and input-member hashes. Both archives are present in the
repository. The historical timing data remain unchanged and are not used to
measure the new reference's speed.

## Scope and coverage

The physical assumptions remain exact planar `p_dot=v, v_dot=u`, static circles,
componentwise bounded acceleration, exact observation and model, instantaneous
execution and constant held commands. The audit uses the same ten high-order
initial-domain states and 259 ordered controls as the saved study. Geometric
and auxiliary properties stay separate:

```
h(t) = ||p(t)-c||²-R²,
psi(t) = h_dot(t)+lambda1*h(t).
```

The audit reconstructs their 672 obstacle/property uses. Identical polynomials
with identical interval and historical reference settings share one query,
while retaining every originating case, control, obstacle and property. This
gives 550 distinct queries, not 550 statistically independent robot trials.
The complete algebraic sign reference classifies 414 safe and 136 unsafe.
An unsafe psi alone does not imply geometric collision.

The input predicate study is replayed first: 5,180 condition results and 10,080
Bernstein polynomial queries. The original saved high-precision minimum records
are then reconstructed explicitly. The earlier allocation replay did not check
those original minimum records. A new regression test changes an archived
minimum bound and verifies rejection.

Two absolute value-width tolerances and three bisection allowances produce
3,300 independent/matched enclosure pairs. Every pair has nonempty intersection;
the independent enclosure also intersects the corresponding archived
high-precision enclosure in every case. Intersections support consistency,
not formal program correctness or accuracy of the physical model.

## Accuracy and unresolved signs

| Absolute tolerance | Allowance | Stationary width reached | Bernstein width reached | Stationary unknown signs | Bernstein unknown signs | Stationary bisections | Bernstein splits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1e-6 | 0 | 351 | 353 | 96 | 88 | 0 | 0 |
| 1e-6 | 8 | 354 | 389 | 7 | 4 | 1,571 | 1,536 |
| 1e-6 | 64 | 550 | 550 | 3 | 4 | 4,048 | 1,883 |
| 1e-12 | 0 | 351 | 352 | 96 | 88 | 0 | 0 |
| 1e-12 | 8 | 354 | 354 | 7 | 4 | 1,571 | 1,570 |
| 1e-12 | 64 | 550 | 550 | 2 | 2 | 7,964 | 3,823 |

Each count is over 550 distinct polynomials. At 1e-12 and 64 bisections both
methods classify 412 safe, 136 unsafe and two unknown, despite reaching the
requested value width on all 550. A narrow interval that contains zero still
does not establish a sign. The same numerical width on h and psi is not a common
physical clearance error: they are different quantities in the declared model.

The stationary reference also makes 16,470 root-count calls at that setting.
A bisection can require exact polynomial divisions and Sturm evaluation, while
a Bernstein split performs different arithmetic. Equal split allowances do
not imply equal primitive work, rational bit complexity or elapsed time. No
new timing samples were collected, and no speed advantage is inferred.

The two remaining sign unknowns are actual zero-margin cases:

1. Query 401 is psi for the first `auxiliary_exact_tangent` candidate. Its exact
   minimum is zero at t=3/10. At 1e-12 the stationary method reaches the width
   after 39 bisections and Bernstein after 19 splits; both signs remain unknown.
2. Query 526 is h for candidate 5 in `negative_geometry_auxiliary_unknown`, with
   held command `(1/2,0)` and T=29/10. The exact polynomial is
   `h(t)=(t-2)²*(t²-4*t+12)/16`, so its minimum is zero at t=2. Both numerical
   signs remain unknown after width attainment. A rational stationary time need
   not lie on the bisection grid of the declared interval. This command's joint
   h-and-psi property is unsafe; a geometrically safe tangency is not sufficient
   to preserve the auxiliary property.

The complete algebraic sign reference resolves both polynomials as safe. That
separate argument is retained; it does not change either numerical method's
status. These are polynomial-level unknowns, not two failed robot runs. Nor does
an offline geometric unknown invalidate an already valid online comparison
certificate. Existing termination and certified-execution semantics are unchanged.

## Verification and limits

Tests independently construct derivatives with known rational factors, integrate
them to degree-at-most-four polynomials, and evaluate all exact stationary and
endpoint candidates. Additional tests cover repeated stationary roots, roots
at endpoints and split midpoints, nondyadic tangencies, irrational minimizers
with positive/negative margins of 10^-100, budget nesting and intersections with
Bernstein on a seeded grid. A separate test reaches a narrow interval with an
unknown sign even though complete algebra proves the minimum negative.

Deterministic regeneration rejects changed bounds, root counts, property-use
coverage, statuses and aggregates. Input archive members and both source
revisions are checked through explicit provenance and hashes. The new archive
is read back member by member. None of these checks formally verifies Python,
authenticates an arbitrary manifest or establishes a hardware guarantee.

Remaining gates include optimized external implementations, coefficient-growth
and execution-time bounds, nonlinear validated dynamics, uncertain observations,
physical actuation, recursive viability and full published experiment replication.
The new minimum reference shares rational polynomial arithmetic and Sturm code
with the complete sign reference; independence is from Bernstein, not from every
other implementation or from the assumed physical model.

## Reproduction

Use a clean committed checkout with the versioned input archive and Python 3.11+:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/audit-minimum-reference.py --config configs/minimum-reference.json --output results/minimum-reproduction
PYTHONPATH=src python scripts/audit-minimum-reference.py --verify results/minimum-reproduction
```

Verification writes the compact source-hashed summary after exact regeneration.
Scientific fields are deterministic; timestamps, paths and source identity change
on later revisions. No simulator integration, new safe-learning controller or
training experiment is introduced by this step.
