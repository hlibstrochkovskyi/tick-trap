# Sampling-aware validation — 19 October 2026

The current suite passes 108 checks. The new comparator specializes the
sampling-aware high-order condition and its allowed relaxation; it does not
reproduce a complete published QP or experiment. Its equations, local proof and
execution assumptions are in [the method record](sampling-aware.md).

The [compact machine-readable study](data/sampling-summary.json) records all
48 terminal outcomes, timings, seven matched-control audits, artifact hashes and
the source/configuration provenance. Full trajectories and proofs are generated
by the commands below. Every source snapshot used here was clean:

| Artifact | Source commit |
| --- | --- |
| Eight-second rollouts | `33424e5b72d94eefdb6562e5b9b9b3508d9ba1c8` |
| Exact saved-run replay | `7639ddb977ab9b464e6bb3b02f7d2dab8cb9576d` |
| Geometric and auxiliary control audit | `ea646a9c897d6f5d22546ff4b4de2e21ddf672a4` |

## Matched tasks

Each method starts from the same eight configurations: four update periods,
two initial positions, two static circles, exact double-integrator dynamics,
componentwise acceleration bound `2`, and an eight-second horizon. Every initial
state has a certified stopping continuation and lies in the high-order domain.
Nominal control is the same PD policy. Candidate methods share a quantized
finite input set; HOCBF uses its continuous QP plus a checked rounding search.
Thus rollout objective values are not a comparison of identical optimizers.

| Method | Safe full horizons / 8 | At goal at end / 8 | Exhausted searches / 8 |
| --- | ---: | ---: | ---: |
| Emulated HOCBF | 8 | 8 | 0 |
| Local zero-order buffer | 0 | 0 | 8 |
| Unrelaxed SACBF | 8 | 6 | 0 |
| Relaxed SACBF feasibility envelope | 8 | 6 | 0 |
| Geometric trajectory reference | 6 | 6 | 2 |
| Stored stopping continuation | 8 | 8 | 0 |

There were no observed collisions, unresolved executed intervals or measured
deadline misses in these runs. Stopping the simulation on an exhausted search
does not physically stop the robot. The two exhausted trajectory-reference runs
illustrate why certifying one hold does not establish future feasibility.

HOCBF's sampled enforcement still carries no inter-sample guarantee. Its eight
successful observed trajectories do not strengthen its theorem. Likewise, the
local zero-order buffer is a particular sufficient specialization, not the best
possible implementation of that paper. These finite task outcomes are not a
general ranking of the methods.

## Match the trajectory property before measuring exclusion

The control audit covers 178 candidates at seven fixed states. Its geometric
table evaluates `h(t)>=0`; the additional table certifies both `h(t)>=0` and
`psi(t)=h_dot(t)+lambda1*h(t)>=0` with the independent Bernstein path checks.
SACBF preserves both properties, so leaving the auxiliary set is a different
reason for rejection from a conservative Taylor test.

| In-domain state | Candidate controls | Geometrically safe | Safe h and psi | Unrelaxed admitted | Relaxed admitted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Short hold near obstacle | 25 | 25 | 25 | 15 | 25 |
| Multiple-obstacle approach | 25 | 25 | 18 | 9 | 14 |
| Unrelaxed stationary state | 26 | 24 | 18 | 4 | 5 |
| Relaxed stationary state | 26 | 20 | 16 | 2 | 4 |

No SACBF-admitted candidate violated either required property in this audit.
For the multiple-obstacle approach, the relaxed test excludes eleven
geometrically safe controls: seven leave the auxiliary set, while four preserve
both properties. The latter four are a concrete remaining gap between this
Taylor sufficient condition and the full polynomial path check. At the relaxed
stationary state, twelve controls preserving both properties are excluded.
These are finite-set measurements of a standard condition's conservatism, not a
new theorem or evidence that its published guarantee is false.

Three audit states lie outside the high-order initial domain. Their SACBF
predicates are marked not applicable, rather than counting the controls as
rejected. The original geometric tangency case retains five unknown signs.

## Safety and progress remain distinct

At period `0.4`, the unrelaxed run from `(-2,0.3)` stops at rest at `(-0.6,0.3)`;
the relaxed run stops at `(-0.52,0.3)`. Both remain safe through the horizon.
The other two missed goal flags arise from still-moving trajectories at the
horizon; they must not be labeled stationary deadlocks.

The relaxed stationary state is a reproducible exact fixed point of this
finite-candidate controller. Its PD nominal is `(2.52,0.4)`, and zero acceleration
is accepted and preferred. The alternative `(0,1)` is also accepted against both
obstacles, but its squared nominal-distance cost exceeds zero's cost by exactly
`0.2`. The remaining accepted candidates cost more as well. Applying zero at
rest reproduces the same state, nominal and decision on every later update in
this static exact model. This is a lack of task progress despite feasible safe
steering; it is neither an infeasible optimization nor a safety violation.
The construction does not claim a new discovery about safety-filter deadlocks.

## Timing and saved evidence

For the representative period `0.1`, initial position `(-2,0.3)` configuration:

| Method | Median controller call (µs) | Initialization (µs) |
| --- | ---: | ---: |
| HOCBF | 1224.1 | 0 |
| Local zero-order buffer | 563.4 | 0 |
| Unrelaxed SACBF | 1095.9 | 0 |
| Relaxed SACBF | 712.9 | 0 |
| Geometric trajectory reference | 574.2 | 0 |
| Stored continuation | 1335.1 | 564.1 |

The methods follow different trajectories and sometimes stop early. These are
single-host empirical measurements, not controlled per-state speed rankings or
worst-case execution bounds. Controller timing includes its online checks;
offline trajectory and stopping diagnostics remain separate.

The verifier reconstructed all 2,857 executed holds and 600 retained plans. It
also replayed 1,200 accepted SACBF conditions and independently certified all
2,400 obstacle-specific auxiliary paths, with zero unresolved auxiliary signs.
The geometric/retained-plan replay used 8,302 distinct polynomial certificates.
Tests reject altered SACBF actions, derivative bounds, margins and acceptance
records. The replay checks model/artifact consistency using the existing
certifier; it does not validate physical model fidelity or actual execution.

## Reproduce

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/sampling-baselines.json --output results/sampling-baselines
PYTHONPATH=src python -m tick_trap planar-audit --config configs/sampling-audit.json --output results/sampling-audit
PYTHONPATH=src python -m tick_trap verify --runs results/sampling-baselines/runs.json --output results/sampling-verification
python scripts/summarize-sampling.py
```

The summary script checks matched configurations, exact terminal goal flags and
the verification input hash before exporting. It requires clean source snapshots.
Timing values and resulting artifact hashes will differ on another run.

The next comparison should hold the required high-order trajectory property
fixed while varying certification precision and computation cost. Full paper
experiment reproductions, robust learned uncertainty and delayed execution
remain separate research gates. No original algorithm or publication-level
novelty is established by this milestone.
