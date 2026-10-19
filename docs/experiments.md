# Reading an experiment

`configs/baselines.json` compares six methods over four update periods.
`configs/stress.json` crosses initial clearance, update period, actuator gain,
measurement error, execution delay, and two seeds. Change one grid field at a
time for an interpretable causal comparison; the full grid exposes interactions.
The initial default sweep uses a fixed number of updates, so its physical horizon
varies with period. Compare per-interval behavior or configure equal physical
horizons before interpreting aggregate performance across periods.

`initial_geometric_safe` checks current clearance. `initial_viable` uses the true
plant's maximum deceleration and the ideal no-delay wall viability formula.
It is explicitly a no-delay label; delay-aware viability is not implemented.
`initial_controller_domain` distinguishes a filter's initial-set restriction.
`true_viable_before/after` track the same ideal viability property per update.

`completed_safe_horizon` is true only for a completed, continuously safe run.
`continuous_safe_observed` concerns only executed intervals. A run stopped before
executing any action may have no observed collision but supplies no evidence of
safe completion. Summaries must retain infeasible and outside-domain runs as
separate outcomes, rather than treating them as collision-free successes.

At infeasibility the runner stops and records the decision. It never substitutes
zero input or an uncertified fallback. At the first violating interval it also
stops. The end state of that interval is the analytical free-motion prediction,
which can be used to demonstrate safe endpoints despite collision. It does not
describe physical motion after contact.

Measurement errors are independent seeded uniform draws in the configured bounds.
The plant applies `plant_gain*command+plant_bias`. The controller uses
`model_gain*command+model_bias`, defaulting to the unit-gain ideal model.
It filters desired acceleration using the conservative symmetric achievable
range `±(model_gain*a_max-|model_bias|)` and maps that acceleration back to a
command with the inverse model. Commands always remain inside `±a_max`.
Different true and model parameters are explicitly marked as model mismatch.
The symmetric restriction can exclude admissible commands when bias is nonzero.

Execution delay is a fixed duration shorter than one period: the previous command
continues during the delay, followed by the new command for the remaining period.
Both pieces are checked analytically. Current filters do not compensate delay or
measurement error. Under either, their nominal safety assumptions are invalid.

`solve_ns` measures the controller, including any checks it performs internally.
`certification_ns` measures the separate offline oracle and is not charged to an
online deadline. A deadline miss is an observed computation-time violation.
Measured computation time does not automatically become simulated actuation
delay; the configured delay controls the plant timeline. These runs do not
establish a hard real-time bound. Timing is platform-dependent and nondeterministic.

The intervention metric sums absolute changes from nominal acceleration at control
updates, without time weighting; it is not a performance objective or an integral.
Neither intervention nor collision counts alone establish conservatism. Inspect
feasible sets and use matched initial conditions and horizons for that question.
