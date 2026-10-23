# Matched geometric predicate comparison

This offline experiment asks a single common question: does the prescribed held
trajectory satisfy `h(t)=||p(t)-c||²-R²>=0` for every circle and every `t in [0,T]`?
It compares standard sufficient geometry bounds, Bernstein checks and exact
polynomial signs. It adds no controller, action search or SSCBF/MPC implementation.

## Model, initial set and property

The exact plant is `p_dot=v, v_dot=u`. State and static circle geometry are known
without observation error; radii include robot size. The prescribed acceleration
is held exactly in the recorded componentwise actuator box. Durations are exact
and positive, with no delay, disturbance, prediction error or actuator mismatch.
Boundary contact is permitted; trajectories are free-motion predictions and
do not describe subsequent physical contact. No uncertainty calibration or
hardware validity is inferred.

The same finite candidate cohort is rebuilt from the archived algebraic
comparison's embedded configuration. Names, candidate counts, order, exact
actions and initial high-order domain labels must regenerate. Cases excluded
from that original HOCBF-domain cohort remain excluded here for matching. That
cohort choice is not a necessary domain restriction of every geometric method.
These exact initial states are not claimed to characterize a planar viability
kernel or to admit safe continuation after the hold.

The reference separately reconstructs complete signs of both `h` and
`psi=h_dot+lambda1*h`. The latter is required by the existing high-order path
references. A geometric certificate is not a certificate of that stronger
joint property. `accepted_auxiliary_unsafe_controls` counts this distinction
explicitly; it does not label a correct geometric implication as a failure.
The initial set, physical horizon and fixed commands are identical across all
methods within a row. Aggregates mix the catalog's different states/hold durations
and are descriptive of that finite cohort, not universal method rankings.

## Compared predicates

| Predicate | Required property and decision | Work allowance |
| --- | --- | --- |
| `command_tube` | Standard inflated-chord sufficient condition with `rho²=(u dot u)*T⁴/64`; success certifies geometry, failure is unknown | No subdivision allowance or runtime bound |
| `box_tube` | Same condition with `rho²=2*a_max²*T⁴/64`; success certifies geometry, failure is unknown | No subdivision allowance or runtime bound |
| `minimum` | Validated rational Bernstein minimum refinement of geometric `h` only; unsafe requires a negative witness | One split allowance shared across the control's obstacles |
| `sign` | Same Bernstein construction, stopping once a sign is established | Same tolerance, allowance and obstacle order as `minimum` |
| `sturm` | Complete exact square-free/Sturm nonnegativity of geometric `h` only | No subdivision allowance or hard runtime bound |

The [chord contract](segment-contracts.md) derives the interpolation identity and
radical-free tube test. The box radius is at least the command radius because
`u dot u<=2*a_max²`; thus a successful box test implies a successful command
test for the same chord. Both use that specific command's chord. A uniform
deviation bound does not make that chord common to every possible command.
Neither tube test claims to implement a published numbered SSCBF condition.

Every obstacle is checked, including after a negative witness. For bounded
methods, the next obstacle receives the unused portion of the control's split
allowance; it does not receive a fresh allowance. Subdivisions are counts of
Bernstein splits, not comparable primitive-operation or elapsed-time budgets
for algebra and tube arithmetic. Tolerance has the units of this unscaled
squared-distance barrier; it is not directly a physical clearance error.
Unresolved signs and failed sufficient conditions remain unknown.

Safe sampled endpoints and exact chord safety are reported as separate
diagnostics. Neither is a physical held-trajectory certificate. The sampled
diagnostic checks both endpoints; it is not a reproduction of a paper's
discrete barrier recursion or optimizer.

## Measured region and pairing

Each measured call receives the same already materialized state, circles,
duration and action. It includes input/actuator validation, the selected
condition or polynomial construction, its exact arithmetic and evidence
assembly. It excludes candidate generation, source reconstruction, offline
truth, action selection and execution. Tubes construct no path polynomial and
call no offline oracle. The measured Sturm comparator constructs and solves
its own polynomial query afresh; it reads no cached reference answer.

Five repetitions use a recorded seed to shuffle method/setting order within
each fixed command. There is no separate warm-up phase. Raw nanosecond samples,
per-control medians and repeat positions are retained. Pairing compares methods
at the same command and repeat number; the calls are sequential, not simultaneous.
External load and interpreter effects can still affect these observations.

Each numeric setting has paired decision transitions and distributions of
baseline/candidate time ratios and baseline-minus-candidate differences.
Ratios greater than one mean the baseline took longer. Quantiles use linear
interpolation of sorted empirical observations. No confidence interval,
statistical independence, clock authentication or worst-case runtime is claimed.
Parameter-free rows are measured once per repeat and reused in every compatible
tolerance/budget comparison; those repeated tables are not additional samples.

All safety decisions and proofs use exact rational arithmetic. Floating point
is used only for descriptive timing statistics and display. Observation error,
learned model error, execution delay and hard deadlines are outside this experiment.

## Reproduction and verification

```sh
PYTHONPATH=src python scripts/benchmark-geometry.py --output results/geometry-cost
PYTHONPATH=src python scripts/benchmark-geometry.py --verify results/geometry-cost
```

Generation requires a clean committed source and an empty output directory,
then checks that source identity and package/script hashes remained unchanged.
Every input archive member and the source metadata/configuration are hash-checked.
Raw input hashes are retained with the generating revision, package/script hashes,
software provenance, seed, tolerances and budgets.

Verification regenerates candidate identities, domain labels, full independent
sign evidence, every exact predicate result, diagnostic/property counts and
aggregates. It separately reconstructs the seeded measurement schedule and
statistics from the saved raw samples. It does not reproduce historical elapsed
times or establish their authenticity. A verification record has its own source
and input hashes, separate from the experiment's provenance.
