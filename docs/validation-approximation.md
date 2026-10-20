# Approximation contracts and practical-safety audit — 20 October 2026

This step strengthens the research instrument's treatment of approximate maps,
sampled-state properties, continuous paths and enlarged sets. It does not add a
Taylor controller or certify a practical-safety family. All 187 tests pass;
[source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39471439845)
passes on Python 3.11–3.14.

The [mathematical contract note](taylor-contracts.md) pins the paper version and
derives the restricted calculations. The key literature distinction is that
[Taylor et al., 2203.11470v2](https://arxiv.org/html/2203.11470v2) uses sampled
invariance and a family-level practical-safety statement. A one-hold decrement
check, accurate next-state map, or observed radius containment is insufficient
to establish that theorem's hypotheses or exact inter-sample invariance.
The cases below are diagnostics of different contracts, not counterexamples to
the published theorem.

## Revisions and complete evidence

All recorded calculations and exact regeneration identify clean source
`aa1c40ed93cbbd6f0976a7b35de8a39f55f2b63d`, runtime source SHA-256
`90f32744e802f22d5f281c800dab65b3ef90f46a748be719269abc8e0fc8037d`.

- [Compact results and worked cases](data/approximation-summary.json)
- [Complete evidence archive](data/approximation-evidence.tar.gz): 12 files,
  537,477 uncompressed bytes; 20,185 compressed bytes
- [Per-file and archive hashes](data/approximation-manifest.json)

The archive contains every exact map comparison, polynomial, sign reference,
projection and distance classification, configuration, source provenance, report,
CSVs, saved-record verification and hosted CI run/job records. Earlier controller
and certification artifacts remain unchanged.

## What is being measured

Eight prescribed state/input cases at four periods give 32 physical holds. Each
is evaluated in two declared state metrics, yielding 64 held-metric cases,
128 map comparisons and 320 distance classifications. There is no controller
synthesis, learning, random sampling, timing benchmark or actuation-delay model
in this audit.

The physical assumptions are exact `d_dot=-v, v_dot=u`, admissible scalar held
acceleration `|u|<=10`, exact observations and instantaneous execution over the
declared interval. Individual cases declare tau and the fixed comparison gain.
The barrier is `b=d-tau*v`; its halfspace is C_b. Geometric clearance d and ideal
wall viability are reported separately. Contact at zero is allowed.

| Field | Precisely checked property |
| --- | --- |
| `approximate_decrement_satisfied` | b at the approximate next state is at least `(1-k*T)*b0` |
| `pointwise_ingredients_satisfied` | The decrement, b0>=0 and k*T<=1 hold at this particular input/state/period |
| `exact_sampled_barrier_safe` | b is nonnegative at both actual sampled endpoints |
| `barrier_path_status` | The exact minimum b on the entire physical hold has the stated sign |
| `geometric_path_status` | The exact minimum d on the entire hold has the stated sign |
| `path_within_dilation` | This observed path stays within the declared normalized distance of C_b |
| `practical_safety_family_certificate` | Always `not_established`; no invariant controller-map family is constructed |

All maps and path values are rational. Analytical quadratic minima agree in sign
with the independent square-free/Sturm reference. Membership in an observed
dilation uses exact squared-distance comparisons, without floating root thresholds.
Positive radii never overwrite the original exact-set statuses.

## Map accuracy and path behavior

Euler has normalized state error at most `a*T²/(2*L)`. Explicit midpoint is
exact on this held affine model. The squared Euler error divided by T^4 is
constant across the chosen periods for all 16 case/metric combinations; 12 have
nonzero error. These observations agree with the analytical formula. They are
not an estimated order claim for nonlinear systems.

For the unit metric's 32 physical holds:

| Map | Nonzero map errors | Pointwise ingredients pass | Pass / actual next b outside | Pass / actual b samples inside but b path outside |
| --- | ---: | ---: | ---: | ---: |
| Euler | 24 | 11 | 1 | 0 |
| Midpoint | 0 | 11 | 0 | 4 |

The other metric yields the same physical and decrement results. Each map has
two cases violating the step-size restriction; these remain explicit exclusions
from the pointwise ingredient flag. These controlled cases are not independent
statistical trials or comparisons of synthesized controller performance.

Three exact examples explain the differences:

1. **Approximate decrement versus the actual sample.** At `d=0.6, v=0, u=4,
   T=0.4, tau=0.3, k=2`, Euler predicts next b=0.12, exactly meeting its decrement
   target. The actual next b is -0.2. Geometric clearance still stays positive,
   with minimum 0.28. Exact midpoint rejects that decrement. This is a barrier
   violation from approximation error, not a geometric collision.
2. **Exact endpoint map versus the continuous barrier.** At `d=0.31, v=1,
   u=-2.4, T=0.2, tau=0.3, k=4`, midpoint is exact and satisfies the decrement.
   Actual next b=1/500 is positive. Nevertheless b has minimum -19/3000 at
   t=7/60. Geometric clearance remains positive. Accurate sampled prediction
   does not settle an inter-sample barrier constraint.
3. **A viable state and safe samples can hide collision.** At `d=0.06, v=1,
   u=-4.25, T=0.4, tau=0.01, k=2.2`, the initial ideal stopping-distance margin
   is positive. Midpoint satisfies the decrement with residual 1/1000, and both
   actual endpoints meet the geometric and barrier conditions. The geometric
   trajectory has minimum -49/850 at t=4/17. This is a free-motion collision
   witness; no physical post-contact dynamics are simulated.

There are three such hidden geometric collisions among the midpoint pointwise
passes in each metric: one from a viable initial state and two from an already
nonviable state. They are retained separately. A collision from an unrecoverable
initial condition must not be scored as equivalent to losing recoverable safety.
None of these finite inputs constitutes the theorem's required controller family.

## Enlargement is a different property

Both metrics use normalized coordinates `(d/L,v/V)` with L=1; V is 1 or 10.
The radius is dimensionless in that declared state metric, not a physical wall
clearance allowance. The target is C_b alone. It is not an obstacle-free set,
the intersection of geometric and barrier constraints, or a viability kernel.

At radius 0, both metrics classify 21/32 sampled endpoint pairs and 16/32 whole
paths as contained. At radius 0.1, the unit metric contains 27/32 paths, including
11 with a genuine exact-barrier violation. The V=10 metric contains all 32 paths,
including 16 exact-barrier violations. Their original `barrier_path_status`
remains unsafe. Radius 0 is an exact-set diagnostic; the paper's practical-safety
quantifier concerns strictly positive radii.

For the first worked example, the maximum squared distance is 4/109 with V=1
and 1/250 with V=10. A radius of 0.1 excludes the former and includes the latter,
without changing the physical trajectory or its negative b minimum. Declaring
the metric is therefore necessary to interpret a finite enlargement result.
No invariant enlarged set or sampling threshold is inferred from these counts.

## The theorem gate remains explicit

| Ingredient | Status for this instrument |
| --- | --- |
| Exact held-flow existence and uniqueness | Established for the affine wall model |
| Uniform one-step error bound | Derived exactly for the two declared maps and bounded inputs |
| Fixed linear candidate signs, Lipschitz and set-distance properties | Derived directly for C_b in the declared metric |
| Uniform comparison function over a sample-period family | A fixed k is used within each case; pointwise checks are not a proof of the complete family |
| A globally enforcing admissible controller family on the declared domain | Not constructed; bounded inputs cannot enforce the decrement everywhere on the unbounded halfspace |
| Forward-invariant enlarged C_T for that controller family | Not established by observed hold containment |
| Original paper synthesis and nonlinear-system experiments | Not reproduced |

The compactness shortcut in the paper is not assumed for C_b. The existing
`endpoint` diagnostic remains a diagnostic rather than a Taylor implementation.
No original algorithm, publication-level novelty, physical-safety guarantee or
hard execution-time bound is claimed.

## Validation and reproduction

Every deterministic field regenerates, including exact states, polynomials,
distance projections, classifications and aggregate counts. Tampered map errors,
metric scales, path labels, purported family certificates and record coverage
are rejected. Regeneration uses the same declared model and audit formulas,
with an independent polynomial sign cross-check; it is not a formally verified
program or an independent implementation of every calculation.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap approximation-audit --config configs/approximation-audit.json --output results/approximation-reproduction
PYTHONPATH=src python -m tick_trap verify-approximation --audit results/approximation-reproduction/audit.json --output results/approximation-reproduction/verification
python scripts/summarize-approximation.py --input results/approximation-reproduction --output results/approximation-reproduction/summary.json
```

Use a clean committed checkout to record provenance. Scientific fields are
deterministic; source revision, timestamps and transient paths change on a later
reproduction. The compact exporter checks verification input hashes, physical
identity across metrics, the Euler period law and preservation of exact-set
statuses at radius zero.

Still open: an actual applicable SD-BF family and its uniform-domain proof,
constructive invariant enlargements, original paper experiments, nonlinear
validated flow bounds, observation/model uncertainty, and a justified learning
extension. These remain research gates rather than completed controller features.
