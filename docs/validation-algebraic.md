# Algebraic cost comparison — 22 October 2026

The independent square-free/Sturm reference is now measured alongside the four
existing certification strategies on identical candidate controls. In this
finite study it resolves the exact tangency that bounded Bernstein checks leave
unknown, while costing more than sign-only Bernstein on most controls. No
controller, execution decision or fallback changes.

Measurements were recorded on 20 October; the saved evidence was checked again
and published on 22 October. All 207 tests pass. The
[evidence-source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39476919342)
passes on Python 3.11–3.14.

## Source and complete evidence

Generation and scientific replay identify clean revision
`5a46e9469ad56fe640675a04c66aafd2a654183c`, runtime source SHA-256
`9d23e76eb8a22eca7e89eee8cea94fc3f4ba3a6de248336f769406daebec805d`.

- [Compact counts, transitions, distributions and case summaries](data/algebraic-summary.json)
- [Complete evidence archive](data/algebraic-evidence.tar.gz): 13 files,
  29,972,321 uncompressed bytes; 1,058,574 compressed bytes
- [Archive and individual member hashes](data/algebraic-manifest.json)

The archive preserves the configuration, every timed condition result, exact
algebraic evidence, raw elapsed samples and shuffled positions, Bernstein work
allocation replay, reports, CSVs, provenance and hosted CI run/job records.
Its SHA-256 is `e90628344051b0bec6a01cb4f544e08efbb648ad5216db9a34ca4d0a9552e114`.
The versioned compact file is byte-identical to the archived `compact.json`.

## Matched property and work scope

The exact plant is `p_dot=v, v_dot=u`, with static circles, exact state and model,
instantaneous execution and constant acceleration during each hold. Commands
obey the componentwise actuator box and quantum in the configuration. For each
obstacle, all strategies target nonnegative geometric clearance polynomial
`h=||p-c||²-R²` and auxiliary polynomial `psi=h_dot+lambda1*h` throughout the hold.
All ten states satisfy the same initial domain `h(0)>=0, psi(0)>=0`. Contact at
zero is allowed. Joint path safety is distinct from geometric safety, viability
and recursive feasibility.

The [configuration](../configs/algebraic-cost.json) retains the earlier auxiliary
study's ten states, 259 ordered controls, two tolerances, budgets 0/8/64, five
repeats and seed 20261020. There are 5,180 timed configurations, 25,900 elapsed
samples and 60 paired comparison settings. Timing includes polynomial/condition
construction and evidence assembly, excluding candidate search, action selection
and the separate offline truth calculation. No controller rollout or hardware
deadline is measured here.

The three Bernstein strategies share the declared split allowance across every
queried obstacle/property for a control. Minimum refinement pursues an enclosure
width; dual sign stops at sign resolution; auxiliary only proves psi and derives
h by linear comparison. Native relaxed SACBF retains the restricted published
condition and initial-domain assumptions documented in [sampling-aware methods](sampling-aware.md).
It is not the full paper's optimizer or nonlinear experiment reproduction.

`sturm` reruns the [existing exact algebra](algebraic-reference.md) inside the
timed region on both h and psi for every obstacle. It does not retrieve cached
offline answers. It has no subdivision allowance or minimum-width tolerance;
its zero split count is **not zero work or an equal-work guarantee**. Rational
coefficient growth and elapsed computation are unbounded by the Bernstein
budget. Its single measured group, like the parameter-free SACBF group, is
reused across numerical-setting comparisons. Those repeated appearances are
not additional independent trials.

## Decisions and measured cost

At tolerance 1e-12 and 64 total Bernstein splits per control:

| Strategy | Safe controls accepted | Unsafe h/psi controls rejected | Safe controls rejected | Unknown | Total splits | Median per-control time (µs) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Relaxed SACBF | 48 | 113 | 98 | 0 | 0 | 141.6 |
| Minimum refinement | 145 | 113 | 0 | 1 | 5,712 | 1,322.0 |
| Dual sign | 145 | 113 | 0 | 1 | 250 | 264.6 |
| Auxiliary only | 145 | 113 | 0 | 1 | 144 | 183.2 |
| Exact square-free/Sturm | 146 | 113 | 0 | 0 | 0, inapplicable as work measure | 1,214.0 |

No strategy accepts a joint-unsafe control at any setting. The three bounded
polynomial methods retain their exact auxiliary tangency unknown. The native
condition's rejection of a safe control means exclusion by a sufficient test,
not a negative physical witness. An unsafe psi alone need not mean collision.

Sturm's transition from each of the three bounded polynomial methods at the
main setting is 145 accepted→accepted, 113 rejected→rejected and one
unknown→accepted. This last transition is a separately evaluated offline answer,
not a change to an online unknown or authorization to execute that control.

For each control, divide its baseline median elapsed time by its Sturm median:

| Baseline / Sturm | p10 | Median | p90 |
| --- | ---: | ---: | ---: |
| Relaxed SACBF | 0.108 | 0.118 | 0.131 |
| Minimum refinement | 0.208 | 1.060 | 2.137 |
| Dual sign | 0.190 | 0.221 | 0.332 |
| Auxiliary only | 0.137 | 0.161 | 0.216 |

Ratios below one mean the baseline is faster. These are distributions of paired
per-control medians, not ratios of pooled medians or confidence intervals.
They show a completeness/cost trade-off for these implementations and inputs,
not universal algorithm dominance. The evidence also retains paired repeat
ratios, differences and per-case distributions. Cross-study timing differences
must not be attributed to a mathematical improvement.

The controlled tangent family's first candidate illustrates the exception to
the typical sign-only cost pattern:

| Obstacle radius | Auxiliary-only result / time (µs) | Sturm result / time (µs) |
| --- | --- | --- |
| 0.599999999 | Accepted / 952.3 | Accepted / 1,333.8 |
| 0.6 | Unknown / 1,153.0 | Accepted / 1,030.1 |
| 0.600000001 | Rejected / 552.0 | Rejected / 828.1 |

The nominal command, initial state and all numerical settings remain matched.
The full artifact records all other candidates and settings; these three rows
are not a representative speed estimate on their own.

## What is proved, checked and still unverified

The mathematical [sign argument](algebraic-reference.md) uses exact rational
square-free decomposition and Sturm root counting for degree at most four,
including repeated roots and boundary contact. This is classical algebra, not
an original tick-trap method. Exact algebraic sign evidence is not a numerical
minimum enclosure. The benchmark uses the same algebra as its offline truth
reference, so agreement with that reference is not independent validation of
Sturm itself. Known-factor tests and agreement with resolved Bernstein answers
provide separate implementation checks, not a formal proof of the program.

Scientific replay reconstructs all 5,180 condition results and 10,080 Bernstein
polynomial queries from the saved configuration and candidate order. It also
regenerates 550 distinct algebraic sign references. Changed algebraic evidence,
work labels, commands, domains, result flags or query allowances are rejected.

The timing verifier reconstructs the seeded order, raw-sample medians, group
counts, distributions and paired transitions. Tests reject changed samples,
positions, medians, coverage, group counts and paired distributions. This
establishes internal consistency; it cannot authenticate the clock or detect
arbitrary replacement of both raw samples and all matching derived statistics.
The archive hash/read-back checks establish that the saved evidence has not
changed relative to its manifest, not that an arbitrary manifest is trustworthy.

Still unverified: formal program correctness; optimized external algebra/CCD
implementation comparisons; scaling beyond this finite low-degree grid; hard
execution-time bounds; uncertain dynamics/observations; delay-aware physical
guarantees; recursive synthesis and full published experiment replications.
No new controller, learned uncertainty claim, original algorithm or
publication-level novelty is established.

## Reproduction

From a clean committed checkout, with Python 3.11+ and the standard library:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap certification-study --config configs/algebraic-cost.json --output results/algebraic-reproduction
PYTHONPATH=src python -m tick_trap allocation-audit --study results/algebraic-reproduction/study.json --output results/algebraic-reproduction/replay
PYTHONPATH=src python scripts/summarize-algebraic.py --input results/algebraic-reproduction --output results/algebraic-reproduction/compact.json
```

The exporter requires matching clean source revisions and exact input-hash
linkage for generation and replay, then checks timing layout and statistics.
Deterministic mathematical decisions and query allocations should reproduce;
timestamps, empirical times, paths and source identity change on later runs.
