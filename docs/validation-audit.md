# Certification audit — 20 October 2026

This is the completed audit snapshot. The [subsequent allocation
replay](validation-allocation.md) explains its shared-budget result with per-query
evidence and extends the suite to 159 tests, retaining the original study data.
The later [minimum-reference audit](validation-minimum-reference.md) supplies
independent numerical value enclosures for the restricted degree-at-most-four
polynomials; the original snapshot and results below remain unchanged.
The [decision-replay follow-up](validation-decision-replay.md) also reproduces
the original 24-run cohort's complete scientific records and candidate searches,
with timing/display exclusions stated explicitly.

This milestone strengthens the existing instrument, without introducing a new
controller. All 150 tests pass in a fresh clone and virtual environment. The
[hosted CI run](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39338053136)
passes on Python 3.11, 3.12, 3.13 and 3.14. The initial 135-test suite also passed
before changes in a separate fresh environment; the
[first CI run](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39337213970)
records that baseline on the same four versions.

All final experiments and the complete test log identify clean published source
`8aa08b50cd0d59a10b67f48c51c3c9e6a74bca34`.
The runtime source SHA-256 is
`84812399cfa36f05c4ccbc90f6affab1e2ac385dd480ebd42a7561452bda3d72`.
Later evidence/documentation commits do not change this runtime source.

- [Compact source-hashed results](data/audit-summary.json)
- [Complete evidence archive](data/audit-evidence.tar.gz): 57 files, 41,185,581
  uncompressed bytes; 2,179,225 compressed bytes
- [Per-file hash manifest](data/audit-manifest.json), including the archive hash

The archive retains both studies, every candidate and exact proof, independent
algebraic evidence, all timing samples and shuffled positions, 24 complete
rollouts, verification, configuration/source provenance, SVGs, CSVs, reports,
test and command logs, numerical corner cases, the termination regression and
hosted CI run/job records. It contains full evidence, not only selected outcomes.

## What is mathematically established

All path arguments assume the **declared exact double-integrator model**, static
inflated circular obstacles, exact state observations, componentwise bounded
commands on the rational command lattice, instantaneous actuation and exact
zero-order holds of the declared duration. Contact at h=0 is allowed. These
assumptions are unchanged and are not established for a physical robot here.

| Statement | Basis and scope |
| --- | --- |
| A quadratic held position gives degree-at-most-four h | Exact substitution in the squared circular clearance |
| Bernstein lower bound and evaluated upper witness enclose the minimum | Convex-hull property and exact rational subdivision; no floating estimate is used as proof |
| h(0)>=0 and psi=h'+lambda1 h>=0 imply h>=0 on the hold | Integrating factor with positive lambda1; no numerical geometric minimum is implied |
| The independent reference decides signs for rational degree <=4 polynomials | Classical square-free decomposition and Sturm counting, with exact rational arithmetic and reconstruction checks; see [derivation](algebraic-reference.md) |
| Unknown at a precision/work limit is not safe | No positive sign is inferred from an unresolved enclosure, regardless of the independent offline answer |

These are conditional mathematical arguments using established methods, not a
machine-checked proof of the Python implementation or an original theorem.
The independently coded algebraic reference shares rational number arithmetic
and model inputs with the Bernstein engine, but does not share its polynomial
evaluation, basis conversion, subdivision or stopping code. Its output resolves
sign, not a minimum value enclosure. Tests include endpoint roots, irrational
and rational repeated roots, exact/near tangencies, known factorizations through
degree four, and perturbations as small as positive and negative 10^-400.

## Matched certification experiments

Both studies use the same ten states, 259 ordered commands, two tolerances,
budgets 0/8/64, five repeats and seed 20261020. Each study has 4,921 timed
configurations and 24,605 evaluations, interleaved in seeded shuffled order.
All four strategies target nonnegative **h and psi** on each hold and use the
same high-order initial domain. Reference calculations are outside timed calls.

Independent truth is 146 jointly safe commands and 113 violating h or psi.
Geometric truth alone is 184 safe and 75 unsafe: 38 geometrically safe paths
violate psi. Therefore an unsafe auxiliary path is not necessarily a collision.
The original tighter Bernstein reference remains recorded as 145 safe, 113
unsafe and one unknown. The additional exact algebraic result resolves that
tangency offline; online decisions remain unchanged.

The native comparator is the existing linear-gain specialization of
[Liu et al., 2511.11897v1](https://arxiv.org/html/2511.11897v1), with a candidate-specific
exact Taylor derivative bound and the permitted zero-target feasibility envelope.
It is not a full slack-penalized QP or reproduction of the paper's experiments.
Its initial domain and relaxation are unchanged. See [equations and
assumptions](sampling-aware.md). A failed sufficient condition is reported as a
rejection, not a negative physical safety witness.

`auxiliary-cost.json` preserves the original budget **per polynomial**. At
absolute tolerance 1e-12 and budget 64:

| Strategy | Safe accepted | Unsafe h/psi rejected | Safe rejected | Unknown safe / unsafe | Splits | Median per-control time (µs) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Relaxed SACBF | 48 | 113 | 98 | 0 / 0 | 0 | 102.7 |
| Minimum refinement | 145 | 113 | 0 | 1 / 0 | 5,715 | 901.3 |
| Dual sign | 145 | 113 | 0 | 1 / 0 | 250 | 240.5 |
| Auxiliary only | 145 | 113 | 0 | 1 / 0 | 144 | 156.6 |

No strategy accepts an independently unsafe command at any setting. All four
reject the 75 geometrically unsafe commands at the main setting. The one
remaining unknown is the exact auxiliary tangency. The polynomial rejections
have a negative h or psi witness; native rejections need not have either.

At zero splits, dual-sign gives `130 accepted / 59 rejected / 70 unknown`;
auxiliary-only gives `131 / 43 / 85`. Its transitions are:

| Dual sign | Auxiliary only | Controls |
| --- | --- | ---: |
| Accepted | Accepted | 130 |
| Rejected | Rejected | 43 |
| Rejected | Unknown | 16 |
| Unknown | Accepted | 1 |
| Unknown | Unknown | 69 |

The extra acceptance has a valid comparison proof; it is not an unknown being
silently accepted. The 16 lost rejections show why removing direct h queries
does not preserve every finite-work classification. With tolerance 1e-6 even
64 splits leave three unknowns. More allowance cannot override an earlier width
stop. Full tables for every setting and strategy pair are archived.

## A shared total work budget changes the comparison

Equal per-polynomial limits allow dual queries more total work than auxiliary
queries. The second configuration, `auxiliary-total-work.json`, instead shares
one subdivision allowance across every obstacle/property for each control.
Queries use obstacle order, h then psi for dual checks, with unused work passed
forward. All methods still see identical candidate inputs. Native SACBF uses no
subdivisions; its timing samples are reused across numeric settings. Neither
budget counts all primitive operations or bounds elapsed time.

At tolerance 1e-12 and **eight total splits per control**:

| Strategy | Accepted | Rejected | Unknown | Unknown safe / unsafe | Total splits over controls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Minimum refinement | 135 | 92 | 32 | 11 / 21 | 1,402 |
| Dual sign | 144 | 111 | 4 | 2 / 2 | 218 |
| Auxiliary only | 144 | 112 | 3 | 2 / 1 | 124 |

Auxiliary-only resolves one dual-sign unknown as rejected here. With shared
work, minimum/sign classification equivalence is no longer required: early
minimum refinement can consume work needed for a later polynomial. This is a
measured allocation effect on these inputs, not a new algorithm or general
dominance theorem.

At 64 total splits, the three polynomial methods again give `145 / 113 / 1`.
Total splits are 5,712 / 250 / 144, and median per-control times are
836.4 / 214.0 / 148.9 µs. Native SACBF takes 95.1 µs at its unchanged
`48 / 211 / 0` decisions. These timings belong to a separate run from the
per-polynomial table.

For each control, divide its baseline median time by its candidate median time.
At the main setting, descriptive paired distributions are:

| Budget scope | Baseline / candidate | p10 | Median | p90 |
| --- | --- | ---: | ---: | ---: |
| Per polynomial | Minimum / dual sign | 0.985 | 5.141 | 9.331 |
| Per polynomial | Minimum / auxiliary only | 1.333 | 7.312 | 12.393 |
| Per polynomial | Dual sign / auxiliary only | 1.262 | 1.378 | 1.568 |
| Per control | Minimum / dual sign | 0.979 | 5.195 | 9.003 |
| Per control | Minimum / auxiliary only | 1.330 | 7.378 | 12.580 |
| Per control | Dual sign / auxiliary only | 1.264 | 1.382 | 1.583 |

All six strategy pairs, repeat-level ratios, paired differences and case strata
are saved. Quantiles interpolate ordered empirical samples. These heterogeneous
finite-set distributions are not confidence intervals or universal speedups.
Costs include condition and evidence construction, excluding candidate search,
control selection, independent references and the offline geometric oracle.

## Rollouts and termination audit

The requested `auxiliary-baselines.json` reproduction contains 24 eight-second
tasks: three methods, four periods and two starting positions with two circles.
All 24 complete a certified horizon. Auxiliary-only and dual-sign reach the goal
in all eight tasks and have identical commands/end states in every matched case.
Relaxed SACBF reaches the goal in six of eight tasks. All 1,800 holds replay
successfully, including 1,200 native auxiliary checks, 2,400 dual h/psi proofs
and 1,200 auxiliary-only proofs. No offline unknowns, collisions or empirical
controller deadline misses occur in this grid. Whole-rollout timings are not
paired fixed-state timing experiments because trajectories can differ.

The separate regression exposes the old termination problem: with zero offline
splits, `p=(-.3,1.06), v=(1,0), u=0, R=1, T=1, lambda1=3` has an unknown
geometric minimum enclosure but a safe auxiliary certificate. The corrected
runner completes two holds with the validated comparison evidence while keeping
the raw geometric oracle summary **unknown**. The nominal controller supplies no
recognized proof and stops after one hold with `oracle_unresolved`. An unresolved
online tangency supplies no authority to execute a candidate.

[Execution evidence](execution-evidence.md) defines the separate fields and
proof registry. Missing, altered, over-budget or unresolved proof evidence is
rejected. Offline goals and budgets are checked too. Negative witnesses are
never overridden; contradictory purported proofs raise an error. Replay audit
cost has its own field outside measured controller time. Halting an offline
simulation does not physically stop a robot or certify a fallback maneuver.

## Acceptance ledger and remaining limits

| Requested task | Completed evidence |
| --- | --- |
| Clean tests and CI | 150 tests; fresh stdlib-only venv and clone; successful four-version hosted CI with pinned action SHAs |
| Reproduce auxiliary cost/baselines | Original configurations retained; complete archive, compact summary, exact source/config hashes |
| Compare four strategies fairly | Identical candidate inputs, both budget scopes, all decision transitions, independent truth, raw timings and paired distributions |
| Audit termination | Separate oracle/execution statuses, replay-validated comparison proofs, genuine unknown stops, tamper/contradiction tests |
| Independent validated reference | Rational square-free/Sturm implementation; exact/near tangency, repeated-root and tiny-margin tests and saved evidence |
| Mathematical documentation | Explicit arguments, assumptions, observed results and unverified scope in this ledger and linked derivations |

No unresolved certificate is marked safe. No valid existing safety argument is
weakened. Published methods retain their precise restricted assumptions. No
new safe-learning controller, simulator integration or training experiment was
started. No original algorithm or publication-level novelty is claimed.

Still unverified: a formal proof of program correctness; independent minimum
enclosures rather than sign decisions; physical model/observation/actuation
validity; robust guarantees under mismatch or delay; hard real-time bounds;
full planar viability or recursive feasibility for the stateless references;
complete source-paper controller/experiment replications; and performance beyond
these finite cases and this host. Those limits remain research gates.

## Reproduce or inspect

From a clean committed checkout, Python 3.11+ and Git suffice; no dependency
download is needed for the local reproduction:

```sh
python scripts/reproduce-audit.py --output results/audit-reproduction
python scripts/archive-audit.py --input results/audit-reproduction --output results/reproduced-audit.tar.gz
python scripts/summarize-audit.py --input results/audit-reproduction --manifest results/audit-manifest.json --output results/reproduced-summary.json
```

The runner creates and retains a fresh local clone and virtual environment,
executes all checks sequentially, and refuses mixed output directories. New
times, timestamps and byte hashes vary. Hosted CI JSON in the saved archive is
external evidence for its recorded revision; a local reproduction does not
manufacture hosted CI results.

To check the committed evidence without rerunning timing experiments:

```sh
mkdir -p /tmp/tick-trap-evidence
tar -xzf docs/data/audit-evidence.tar.gz -C /tmp/tick-trap-evidence
python scripts/summarize-audit.py --input /tmp/tick-trap-evidence --output results/archived-summary.json
PYTHONPATH=src python -m tick_trap verify --runs /tmp/tick-trap-evidence/auxiliary-baselines/runs.json --output results/archived-replay
```

The summary command checks every extracted member against the manifest and the
compressed archive hash before exporting. The replay command checks dynamics
and exact recorded proofs; it does not independently validate physical models.
