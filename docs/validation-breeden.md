# Published wall conditions — 20 October 2026

This comparison closes a specific prior-art gap: tick-trap previously implemented
only Breeden et al.'s local Lipschitz condition. It now also specializes their
reachable-error and second-order conditions on the same wall model. All are
published methods; none is a new controller contribution. The [mathematical
derivation](breeden-wall.md) records the exact model reduction and equation numbers.

The suite passes 174 tests. [Source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39370259169)
passes on Python 3.11–3.14. All experiments and saved-record verification identify
clean source `037ab01aa803855654704f1afbc0c90c5fd6d76c`, runtime SHA-256
`276a79e09080d2a385459c3a3a3dac6f505de5e14488005736638df77a3bd317`.

- [Compact source-hashed results](data/breeden-summary.json)
- [Complete evidence](data/breeden-evidence.tar.gz): 14 files,
  20,871,995 uncompressed bytes; 1,397,063 compressed bytes
- [Per-file and archive hash manifest](data/breeden-manifest.json)

The archive contains every held-control reference, exact admissible interval,
selected input and margin, all 256 rollout records, reports, configuration,
source provenance, verification and hosted CI records.

## Assumptions and comparison policy

The model is `d_dot=-v, v_dot=u`, with componentwise scalar bound `|u|<=10`,
exact observations and dynamics, instantaneous actuation, zero delay, and a
constant rational command through each hold. Contact is allowed. All methods use
the same barrier `b=d-0.3v` and initial domain `d>=0, b>=0`. The physical horizon
is two seconds, nominal acceleration zero, and periods are 0.02/0.1/0.2/0.4 s.

The [configuration](../configs/breeden-study.json) has eight initial states, two
gain policies and 21 identical control candidates per state/rate/policy. There
are 64 held-state comparisons and 1,344 control cases. One state is viable but
outside the barrier domain; another is in that domain but already physically
nonviable under the ideal stopping-distance test. Those labels remain distinct.

| Method | Restricted condition | Effective gain |
| --- | --- | --- |
| `continuous_cbf` | Continuous condition evaluated only at updates; diagnostic | k |
| `breeden` | Existing local Lipschitz tube margin, Theorem 1 | k |
| `breeden_reachable` | Exact local reachable-error margin, Theorem 2 | k |
| `breeden_second_order` | Exact second-derivative bound, Theorem 3 | gamma/T |

The fixed policy sets k=2 in the first three methods. The matched policy sets
k=gamma/T, with gamma=1, so all four use the same coefficient on b. Theorem 3
always uses gamma/T, independently of the generic gain setting. The 32 paired
Theorem 3 trajectories have identical commands and outcomes across policies.
Differences in fixed-gain comparisons must not be attributed entirely to margins.

These are specializations of [Breeden et al., 2103.03677v1, Section III](https://arxiv.org/html/2103.03677v1),
not reproductions of its unicycle or spacecraft experiments. No global CBF
existence, uniform feasibility, robust guarantee, or physical-model validation
is inferred from the one-hold arguments.

## Admitted controls and complete horizons

For each policy, 588 control cases are in the barrier domain: 399 preserve both
geometric clearance and b on the hold, and 189 violate at least one. Independent
exact algebraic signs agree with analytical quadratic minima for every case.
Held-control counts include the initially nonviable state's short holds: a safe
next hold need not preserve the possibility of future safety.

Horizon counts below instead use only the 24 **viable, in-domain** tasks per
method and policy: six eligible initial states times four periods.

| Gain policy | Published condition | Safe held controls admitted | Safe held controls excluded | Barrier-safe full horizons / 24 |
| --- | --- | ---: | ---: | ---: |
| Fixed | Theorem 1, Lipschitz | 140 | 259 | 11 |
| Fixed | Theorem 2, reachable error | 177 | 222 | 16 |
| Fixed | Theorem 3, second order | 355 | 44 | 24 |
| Matched | Theorem 1, Lipschitz | 162 | 237 | 8 |
| Matched | Theorem 2, reachable error | 219 | 180 | 12 |
| Matched | Theorem 3, second order | 355 | 44 | 24 |

Every published condition admits zero reference-unsafe b/geometric control cases.
Every feasible published rollout hold preserves b and geometric clearance. There
are no observed collisions. Infeasible decisions stop explicitly without a
fallback. The 44 safe commands still excluded by Theorem 3 show that even this
stronger sufficient condition is not the exact held-control safe set.

Each method/policy also has four runs excluded by the initial barrier domain
and four initially nonviable runs. The latter terminate at infeasibility; they
are not counted as safe completed horizons or equivalent controller failures
from recoverable states. Extra infeasible stops from viable states are reported
separately by the complete records. Stopping a simulation is not physical braking.

Theorem 2's interval contains Theorem 1's at each matched state and equal gain,
consistent with its exact error margin being bounded by the Lipschitz margin.
This does not itself prove an ordering of whole closed-loop tasks with different
trajectories. Table results are observations on these finite cases. Exact input
interval widths are saved separately; finite grid counts are not volumes, and
a feasible singleton interval can have zero width.

## Two interpretation checks

At `d=0.6, v=1, T=0.1, tau=0.3, gamma=1`, b=0.3. With matched k=10, the
reachable-error margin is 5.5, giving upper action bound -35/3, below the minimum
admissible input -10. The second-order margin is 0.5 at the same effective gain,
giving upper bound 5. The latter accepts nominal zero. This is an improvement
already provided by the published condition, not evidence that tick-trap has
invented a better controller.

The emulated continuous-CBF diagnostic completes all 24 eligible tasks under
either policy, but admits four unsafe b paths with fixed gains and 11 with matched
gains in the held-control audit. For example, at rest with `d=0.6, T=0.4, k=2`,
it accepts `u=4`: geometric clearance stays positive, while b reaches -0.2.
The zero nominal action in the rollout does not exercise that bad admission.
Collision-free rollouts alone therefore do not establish the diagnostic filter's
hold guarantee. A barrier violation is not automatically a geometric collision.

Separately, the analytical state `d=1.2, v=4` is geometrically viable for a=10
and lies at b=0. Yet even maximum braking gives initial `b_dot=-4+0.3*10=-1`.
No admissible input can preserve this particular barrier set from that state.
Thus the full unbounded cone b>=0 is not controlled invariant for bounded
acceleration, and the uniform feasibility hypothesis cannot be silently assumed.
The actual safety statements remain conditional on feasible successive holds.

## Validation scope and remaining work

Saved-record regeneration verified all 256 runs, 5,744 executed holds and 1,344
fixed-control references. It recomputes states, commands, conditions, minima,
labels and the aggregate counts used by reports. Empirical solve/oracle
times and deadline observations are explicitly excluded from regeneration.
It uses the same exact model and controllers, plus independent algebraic signs
for the fixed-control reference; it is not an independent experiment implementation.

Tests include reachable-error witnesses and piecewise input histories, exact
projection, accepted-path sign checks, gain policy, zero-width feasibility,
initial-domain/viability distinctions, and rejection of tampered saved evidence.
The proofs in the linked derivation establish restricted mathematical implications;
tests and replay support program correctness without formally proving it.

Still open: the paper's original systems and experimental reproduction, the
remaining cross-paper theorem-assumption comparison, uncertainty/delay validity,
real-time bounds, and a targeted novelty assessment for any proposed improvement.
No learned controller or training experiment was introduced in this work.

## Reproduce

From a clean checkout:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap wall-conditions --config configs/breeden-study.json --output results/breeden-study
PYTHONPATH=src python -m tick_trap verify-wall-study --study results/breeden-study/study.json --output results/breeden-study/verification
python scripts/summarize-wall-conditions.py --input results/breeden-study --output results/breeden-study/summary.json
```

All scientific fields regenerate; timestamps and measured timing observations
vary. The compact exporter requires clean matching source revisions and verifies
that the saved replay belongs to those exact study/run hashes. Full input sets,
effective gains and every exact controller action are retained in the outputs.
