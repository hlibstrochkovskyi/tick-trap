# tick-trap

[![tests](https://github.com/hlibstrochkovskyi/tick-trap/actions/workflows/tests.yml/badge.svg)](https://github.com/hlibstrochkovskyi/tick-trap/actions/workflows/tests.yml)

Continuous-time safety analysis for sampled robot control.

tick-trap is a small research instrument for comparing sampled-state safety,
continuous-trajectory safety, and viability. It starts with analytically solvable
wall braking and planar acceleration-controlled robots. There is no claim of a
new safety controller or publication-level novelty.

The [certification audit](docs/validation-audit.md) compares four strategies
using matched commands and explicit work budgets.
It adds an independent exact polynomial sign reference and distinguishes an
unresolved offline oracle from a valid online comparison proof. The
[source-hashed summary](docs/data/audit-summary.json) links to complete archived
evidence; all guarantees remain conditional on the declared ideal model.

The [work allocation follow-up](docs/validation-allocation.md) replays 20,160
polynomial queries to explain which unresolved decisions result from prior
queries consuming a shared budget. The [published wall-condition
comparison](docs/validation-breeden.md) adds Breeden's tighter reachable-error
and second-order conditions, with matched gain policies and exact saved-record
regeneration. The [approximation contract audit](docs/validation-approximation.md)
separates map accuracy, sampled checks, continuous paths and enlarged-set
observations without claiming a Taylor controller reproduction. The current
suite passes 187 tests.

![Exact safe-sample collision counterexample](docs/data/counterexample.svg)

The implementation uses the Python standard library and Python 3.11+. To run
without installing anything:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap counterexample
PYTHONPATH=src python -m tick_trap run
PYTHONPATH=src python -m tick_trap sweep --config configs/baselines.json
PYTHONPATH=src python -m tick_trap certify --config configs/planar.json
PYTHONPATH=src python -m tick_trap learn --config configs/learning.json
PYTHONPATH=src python -m tick_trap benchmark --config configs/certification.json
PYTHONPATH=src python -m tick_trap planar-run
PYTHONPATH=src python -m tick_trap planar-sweep --output results/planar-baselines
PYTHONPATH=src python -m tick_trap planar-audit
```

Or install with `uv sync`, then use `.venv/bin/tick-trap counterexample` and the
other commands above. A run writes JSON records, CSV metrics, a Markdown report,
and a provenance manifest under `results/`. The counterexample also produces a
standalone SVG figure. Use `--output DIRECTORY` to choose the artifact directory.

Exact rational wall trajectories reproduce the 4 cm → −1 cm → 4 cm counterexample.
Planar circle checks combine a numerical stationary-point estimate with a separate
validated Bernstein polynomial minimum enclosure. Unresolved certificates return
`unknown`; a floating-point root estimate never establishes a guarantee.

All guarantees concern the declared mathematical model and input values. They do
not cover contact dynamics, unmodelled disturbances, or physical hardware.

Six baseline/reference filters are available: unfiltered nominal input,
continuous-time CBF emulation, endpoint-only checking, Breeden's sampled-data
condition, Tan's zero-order barrier condition, and an exact wall reference.
Published methods are documented specializations, not replications of complete
published experiments. Read the [equations and assumptions](docs/methods.md) and
[experiment semantics](docs/experiments.md) before interpreting comparisons.

The stress grid varies initial feasibility, update period, actuation mismatch,
measurement noise, and fixed delay:

```sh
PYTHONPATH=src python -m tick_trap sweep --config configs/stress.json --output results/stress
```

Infeasibility stops execution explicitly. Safe completion is reported separately
from absence of an observed collision. Empirical computation timings do not
establish real-time guarantees; configured delay and measured runtime are separate.

The learning study fits an affine actuator model from noisy supervised data,
measures held-out prediction error, and runs the filters under original and
changed dynamics. Fitted parameters and all training data are saved. This is a
small model-identification experiment; prediction errors are not calibrated
uncertainty bounds.

The certification benchmark varies minimum-enclosure precision and subdivision
budget on six analytical trajectories, including tiny positive/negative margins
and a non-dyadic tangency. It records `unknown` outcomes alongside empirical cost.

Planar experiments compare a conventional HOCBF QP with endpoint, chord,
zero-order barrier, sampling-aware high-order conditions and validated trajectory
checks against multiple circles.
Reports include exact quadratic trajectory SVGs and sufficient stopping-plan
certificates. Candidate-search exhaustion, proven QP infeasibility, unresolved
certificates, and task progress remain separate outcomes. The matched-control
audit measures which safe controls a condition excludes and which unsafe curves
an endpoint or chord check admits. Read the [planar method assumptions](docs/planar-methods.md).

The [sampling-aware comparator](docs/sampling-aware.md) uses exact derivative
bounds on our model and distinguishes the unrelaxed condition from its allowed
feasibility relaxation. Compare it on matched eight-second tasks with:

```sh
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/sampling-baselines.json --output results/sampling-baselines
```

The [stored-continuation reference](docs/continuations.md) keeps a proved plan to
rest available when a new action cannot be certified. It measures initialization,
candidate search, plan reuse and terminal holding separately:

```sh
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/continuations.json --output results/continuations
PYTHONPATH=src python -m tick_trap verify --runs results/continuations/runs.json
```

See the [research plan and literature ledger](docs/research-plan.md) for the scope
of this foundation and the work required before making a research claim.
The [validation record](docs/validation.md) maps the original acceptance criteria
to the checks and experiments actually completed, including their limits.
The [stored-continuation results](docs/validation-continuations.md) include the
matched search-budget comparison and saved-evidence replay.
The [sampling-aware results](docs/validation-sampling.md) compare 48 matched tasks,
separate geometric and auxiliary-set exclusions, and reproduce a safe stationary
case with feasible steering. The accompanying compact study data is versioned.

The [high-order certification study](docs/validation-certification.md) compares
the same two trajectory properties at fixed states and commands. It measures
minimum refinement versus sign stopping, includes controlled tangencies, and
checks matched controller action sequences:

```sh
PYTHONPATH=src python -m tick_trap certification-study
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/high-order-baselines.json --output results/high-order-baselines
```

An ordinary Git checkout uses standard Git commands. Notes for the restricted
development workspace and its portable history are in [workspace setup](docs/workspace.md).
