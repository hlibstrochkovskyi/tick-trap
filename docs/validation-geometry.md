# Matched geometric certification costs — 23 October 2026

On the same 259 prescribed commands, a command-specific tube certifies more
geometric paths than an actuator-box tube, while Bernstein sign checking resolves
more decisions. Geometric acceptance is not auxiliary-set preservation: 20 of
the command-tube acceptances violate `psi`. These results quantify a restricted
comparison, not a new controller or a published SSCBF/MPC reproduction.

All 257 tests pass in a fresh Python 3.14.8 virtual environment without installing
the project or runtime dependencies. [Source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39921032208)
passes on Python 3.11–3.14. Tests cover the absence of an offline oracle in the
measured tube path, exact cohort reconstruction, inadmissible commands, shared
budgets, auxiliary-property labels, full proof replay and outcome-conditioned
timing statistics. The earlier algebraic benchmark's 5,180 timed rows and
statistics also still verify after the reusable timing-code changes.

## Exact source and archived evidence

Generation, sequential clean tests and exact verification use clean source
`08e6e0aa61ce79cf0e686f575e219c3a7177f064`, package source SHA-256
`69e5f74db70df90764b17fb647f7e5a69d0c71b9ed6ef32906b1baffa99fdb4c`.
The benchmark-script SHA-256 is
`005e48bb3606522389278331a5336954fe8ebf0ce33f42683d4c19289aeb0046`.

- [Compact decisions, paired distributions and provenance](data/geometry-summary.json)
- [Complete evidence archive](data/geometry-evidence.tar.gz): 11 files,
  8,658,387 uncompressed bytes; 588,568 compressed bytes
- [Archive and per-member hashes](data/geometry-manifest.json)

The compressed archive SHA-256 is
`88d537fc4d42535063d8feeae6cc8cf1d46d7df1f769acbef030657dd442ad85`.
It retains physical inputs, ordered commands, initial-domain records, full
geometric and auxiliary sign evidence, every predicate proof, raw elapsed
samples, repeat positions, outcome-conditioned distributions, configuration,
software/seed provenance, complete test log, exact replay and hosted CI records.
The versioned compact file is byte-identical to archived `compact.json`.

Inputs come from the [algebraic evidence archive](data/algebraic-evidence.tar.gz),
SHA-256 `e90628344051b0bec6a01cb4f544e08efbb648ad5216db9a34ca4d0a9552e114`,
generated from clean source `5a46e9469ad56fe640675a04c66aafd2a654183c`.
Its manifest, study and metadata hashes are retained separately. All archive
members are checked, and physical candidate order and complete `h`/`psi`
evidence are reconstructed afresh from that embedded configuration.
Historical elapsed times are not used as the new benchmark's measurements.

## Model and required property

The [protocol and mathematical contract](geometry-comparison.md) name the exact
plant, initial-set, actuation, observation, numerical and execution assumptions.
The plant is the planar double integrator, with known exact initial states and
static circles, prescribed bounded held acceleration, and the recorded positive
duration. Radii include robot size; nonnegative `h=||p-c||²-R²` permits boundary
contact. There is no observation error, delay, model mismatch or disturbance.
Rational arithmetic validates the mathematical queries; it does not validate
hardware or contact dynamics, and has no formal program-correctness proof.

The ten states and 259 commands retain the earlier HOCBF-domain cohort for
matching. Viability and future safe continuation are not inferred from that
membership. All methods see identical states, commands, obstacles and physical
hold horizons. This experiment requires geometry only. The additional condition
`psi=h_dot+lambda1*h>=0` remains separately labeled; geometry-safe commands must
not be promoted to joint high-order certificates.

## What is proved, and what this catalog observes

The elementary identity `p(t)-L(t)=u*t*(t-T)/2` gives a peak deviation
`rho=||u||*T²/8`. Replacing `||u||²` with `2*a_max²` gives a valid larger bound
for commands in the componentwise actuator box. Each condition concerns that
specific command's chord. Minimum chord distance `D>=R+rho` implies geometric
safety for this one hold. The radical-free guard is evaluated exactly; failure
remains unknown. A successful box condition implies a successful command
condition, without claiming they have equal cost or describe every admissible
command using one fixed chord.

Complete sign truth gives 184 geometrically safe and 75 geometrically unsafe
commands. Only 146 preserve both geometric and auxiliary path properties; the
other 38 geometrically safe commands violate `psi`. Endpoint diagnostics label
33 unsafe physical paths safe. Chord diagnostics label six unsafe paths safe
and exclude three safe physical paths. These are prescribed-input observations,
not rates of failures by published controllers.

At width `1e-12` and a maximum of 64 Bernstein splits shared across each command's
obstacles, the observed results are:

| Predicate | Geometry-safe accepted | Unsafe proved | Unknown safe / unsafe | Accepted but auxiliary-unsafe | Bernstein splits | Median us/control |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Command-specific tube | 148 | 0 | 36 / 75 | 20 | 0* | 94.949 |
| Actuator-box tube | 122 | 0 | 62 / 75 | 11 | 0* | 93.526 |
| Bernstein minimum | 183 | 75 | 1 / 0 | 37 | 2,959 | 813.642 |
| Bernstein sign | 183 | 75 | 1 / 0 | 37 | 106 | 146.365 |
| Exact square-free/Sturm | 184 | 75 | 0 / 0 | 38 | 0* | 498.268 |

*The tube and algebraic methods have no comparable subdivision allowance or
hard runtime bound; zero Bernstein splits does not mean zero computation.
No method accepts a geometrically unsafe command. Failed tube conditions are
unknown, not certified unsafe. The command bound gains 26 geometric certificates
over the box bound on these identical commands. Its joint-safe accepted subset
is 128 commands, versus 111 for the box condition. Those subsets do not turn
either geometry-only method into a joint-property filter.

## Pair timings by the answers returned

Measurements include input checks, condition/polynomial construction and exact
evidence assembly. They exclude candidate generation, offline truth, selection
and execution. Five repetitions shuffle method/setting order per command using
seed `20261023`; no separate warm-up is performed. The experiment has 3,885
predicate records and 19,425 raw elapsed samples over 15 settings, with 60 paired
setting comparisons. Parameter-free samples are reused across the numeric
tables; those tables are not independent replications.

At `1e-12`/64, the median paired command-tube/sign time ratio is `0.817` over
the full cohort. On the 148 commands both accept, it is `0.825`. The 35 commands
where the tube is unknown and sign checking accepts have ratio `0.804`; the 75
unknown/rejected cases have ratio `0.785`. These distinct outcomes must accompany
any cost comparison: an inexpensive unknown supplies a different answer from a
resolved sign. Full distributions and the one unknown/unknown case are saved.

Minimum and sign checking return identical decisions on all 259 commands at
every matched numerical setting here. At `1e-12`/64 their median paired time
ratio is `5.248` over the cohort and `3.335` on matching acceptances. Sign/Sturm
has ratio `0.252` overall and `0.245` on matching acceptances. Ratios are
baseline/candidate, so values above one mean the baseline took longer. These are
medians of paired ratios, not ratios of the two marginal median times in the
table. They describe this implementation, host and cohort, without causal,
statistical independence, clock authenticity or real-time guarantees.

## The remaining geometric boundary case

The only unknown bounded geometric query at allowance eight or 64 is the
`negative_geometry_auxiliary_unknown` case with command `(1/2,0)` and `T=2.9`.
Here `p_x=2-t+t²/4`, `p_y=0`, and `R=1`. With `z=t-2`,

```
h(t) = z²/2 + z⁴/16 >= 0.
```

The exact root at `t=2` is not a dyadic subdivision point on this hold. The
Bernstein methods remain unknown while the complete sign method establishes
nonnegativity. With the recorded `lambda1=2`, that command has
`psi(1.9)=-7219/80000<0` before the tangency.
Resolving its geometric sign therefore does not add a joint-safe command.
The measured Sturm method and offline truth share the same algebraic code;
their agreement is replay, not a second independent algorithm validation.

## Reproduce and limits

From a clean committed checkout, choosing an unused output directory:

```sh
python -m venv /tmp/tick-trap-geometry-clean
PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONHASHSEED=0 /tmp/tick-trap-geometry-clean/bin/python -m unittest discover -s tests -v
PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONHASHSEED=0 /tmp/tick-trap-geometry-clean/bin/python scripts/benchmark-geometry.py --output results/geometry-reproduction
PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONHASHSEED=0 /tmp/tick-trap-geometry-clean/bin/python scripts/benchmark-geometry.py --verify results/geometry-reproduction
```

Exact scientific results and seeded layout regenerate; new elapsed values,
timestamps and their byte hashes can differ. The recorded archive uses
`scripts/archive-audit.py --input results/geometry-final-outcomes
--output docs/data/geometry-evidence.tar.gz --manifest docs/data/geometry-manifest.json`.
Members are read back and hash-checked before publication. Hosted CI evidence is
for its recorded revision and is not manufactured by local reproduction.

This remains an offline one-hold comparison. No controller or execution fallback
changes, no strengthened joint guarantee, full SSCBF theorem reconstruction,
external optimized CCD/algebra benchmark, calibrated learned uncertainty, hard
deadline guarantee or original algorithm is established. Those remain research
gates. The useful outcome is a matched record of the geometric precision/cost
trade-off and a concrete demonstration of why required properties must accompany
acceptance counts.
