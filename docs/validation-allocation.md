# Where shared certification work goes — 20 October 2026

The [previous audit](validation-audit.md) found different unresolved counts under
the same total subdivision limit. This follow-up reconstructs the work spent on
each polynomial, checks the original exact results, and distinguishes allocation
effects from questions still unresolved at the full per-polynomial limit. It
adds offline research instrumentation, not a controller or a novel algorithm.

All 159 tests pass. [CI for the replay source](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39368858285)
passes on Python 3.11–3.14. The original controller predicates, numerical stopping
rules, initial domains, candidate ordering and physical assumptions are unchanged.

## Revisions and saved evidence

| Role | Clean source commit |
| --- | --- |
| Original measured certification studies | `8aa08b50cd0d59a10b67f48c51c3c9e6a74bca34` |
| Allocation replay and counterfactual checks | `790291a8382b642c4b1e7e17c41c7cb9efaa0a95` |

The replay runtime source SHA-256 is
`23ed95c1c2f43cf3db960cd05b9d6c33827865bd5de5b3047c2631f184184413`.
The input archive is checked against its original hash and every member against
the original manifest before either study is read.

- [Compact results and three worked traces](data/allocation-summary.json)
- [Complete replay evidence](data/allocation-evidence.tar.gz): 14 files,
  32,535,899 uncompressed bytes, 455,380 compressed bytes
- [Replay evidence hash manifest](data/allocation-manifest.json)
- [Original measured evidence](data/audit-evidence.tar.gz) and its
  [manifest](data/audit-manifest.json), preserved separately

Both original budget policies replay successfully: 4,921 property configurations
and 10,080 polynomial queries each. The 259 commands and ten states are rebuilt
from the recorded configuration; excluded initial domains stay excluded. All
4,921 per-control counterfactual configurations match the corresponding original
per-polynomial replay, including every polynomial's full-budget certificate.
These are deterministic replays; no new timing experiment is inferred from them.

## What the audit verifies

The audit reconstructs the exact state, candidate set/order, h and psi
polynomials, positive gains, hold duration and numerical settings. It independently
rebuilds algebraic sign evidence, then replays each Bernstein query using the
budget actually available at that point. Merely replaying at the saved split
count would not establish that the earlier queries left that much work available.

Each trace stores its obstacle/property, exact polynomial, assigned allowance,
prior work, remaining work, certificate, and full per-polynomial counterfactual.
Minimum queries additionally record the prefix at which a sign decision would
stop. The audit checks bounds, witness, goal, status, counts and stopping flags,
as well as native SACBF assessments and the auxiliary comparison implications.

Missing, extra, duplicate, reordered-candidate, changed-action, wrong-budget and
altered-proof records are rejected. JSON types are checked when comparing
evidence, so a Boolean cannot disguise an integer work count. Measurement storage
order itself is irrelevant. Unknown or unsupported configuration fields are
rejected rather than silently ignored.

This uses the existing Bernstein implementation for certificate consistency,
with the separate exact algebraic sign reference as a sign cross-check. It does
**not** independently reimplement Bernstein arithmetic, validate measured times,
verify all historical predicates/stopping plans in the input audit, or check its
saved group statistics. The reported allocation groups are recomputed directly
from the verified measurements.

## The observed allocation effect

At tolerance 1e-12 and eight subdivisions **shared across all queried
polynomials of a control**:

| Strategy | Accepted | Rejected | Unknown | Unknown resolved at full per-polynomial allowances | Still unknown at those allowances |
| --- | ---: | ---: | ---: | ---: | ---: |
| Minimum refinement | 135 | 92 | 32 | 29 | 3 |
| Dual sign | 144 | 111 | 4 | 1 | 3 |
| Auxiliary only | 144 | 112 | 3 | 0 | 3 |

For minimum refinement, the 29 lost decisions comprise nine full-budget
acceptances and 20 full-budget rejections. For dual sign, the single lost decision
is a rejection. No recorded unknown becomes an accepted online action here.

We call a control **allocation-limited** only when its shared-budget answer is
unknown and its same-query full per-polynomial counterfactual is resolved.
That counterfactual grants up to eight splits to *each* polynomial and may spend
more than eight in total. This diagnostic does not prove that a different
allocation of the same eight splits would resolve all 29 controls. Unknown at
the full allowance means unresolved at those limits, not mathematically
undecidable or unsafe.

The shared minimum queries use 1,402 splits, of which 1,278 occur beyond the point
where the corresponding sign query would stop. They remain legitimate work for
the stronger minimum-width request. They must not be called unnecessary when
that width is required. The study's time and work comparisons preserve the same
path property while making these different numerical output requests explicit.
All queries are evaluated, even after an earlier property rejects a control,
matching the original timed predicate scope.

## Three exact traces

For `p=(1.67,0), v=(-1,0), u=(1,-1), R=1, T=1, lambda1=2`:

```
h(t)   = 1.7889 - 3.34t + 2.67t² - t³ + 0.5t⁴
psi(t) = 0.2378 - 1.34t + 2.34t² + t⁴
```

The h sign is proved with zero subdivisions. The minimum-width query nevertheless
uses all eight available splits, then psi receives zero and remains unknown.
Its full eight-split counterfactual is safe, making the joint counterfactual
accepted. The existing dual-sign predicate uses zero splits for h and one for
psi and accepts this same command. The recorded minimum-query answer remains
unknown; the trace changes no controller decision.

For `p=(2,0), v=(-1,0), u=(0.5,0), R=1, T=2.9, lambda1=2`:

```
h(t) = 0.5(t-2)² + (t-2)⁴/16 >= 0.
```

This path only touches the permitted geometric boundary at t=2. The nondyadic
normalized root leaves h unknown after eight sign-query splits. That consumes
the shared allowance, leaving psi unknown with zero splits. Giving psi its own
allowance finds a negative witness after one split at t=29/20. Thus the lost
rejection concerns the required auxiliary set, **not a collision**. The unchanged
auxiliary-only predicate can find that witness without spending work on h.

For `p=(1.231168,0), v=(-0.90112,0), u=(0.8704,0), R=0.6, T=1` and gain 2,
the exact auxiliary tangency remains unknown with eight splits under both
policies. Its independent algebraic sign is safe. No prior query starves it in
the auxiliary-only strategy: this is an unresolved query at the declared limits,
not a loss caused by the shared allocation. The earlier factorization and
near-tangency analysis are in [certificate goals](certificate-goals.md).

## Assumptions and remaining questions

All conditional safety arguments still use the exact planar double integrator,
static inflated circles, exact observations and instantaneous bounded rational
commands held for the declared duration. Contact is allowed; neither geometric
nor joint path safety establishes full planar viability or future feasibility.

These results explain a finite-set measurement. They establish no real-time
deadline bound, hardware cost model, robust physical guarantee, improved online
algorithm, general dominance, or publication-level novelty. Further work on
allocation would first need broader cases, precisely matched output requests
and total resource accounting, then its own targeted prior-art comparison.

## Reproduce

From a clean committed checkout:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/reproduce-allocation.py --output results/work-allocation
python scripts/archive-audit.py --input results/work-allocation --output results/allocation-evidence.tar.gz --manifest results/allocation-manifest.json
```

The first command runs all tests. The second checks the original archive hashes,
replays both policies and compares all full-budget counterfactuals against the
original per-polynomial results. The third archives every new output without
overwriting the original audit manifest. Transient extraction paths and new
provenance timestamps vary; exact query evidence and classifications reproduce.

For an individual already-extracted study:

```sh
PYTHONPATH=src python -m tick_trap allocation-audit --study /path/to/auxiliary-total-work/study.json --output results/allocation-audit
```

Its adjacent `metadata.json` supplies the original configuration. The command
saves exact traces, recomputed group metrics, a report and input/source hashes.
