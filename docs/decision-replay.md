# Planar decision replay

Physical trajectory verification and controller fidelity answer different
questions. `verify_planar_runs` checks declared exact dynamics, recorded
certificates and recognized online proof arguments. A trajectory can satisfy
those checks while a saved endpoint margin, QP cost, rejected candidate prefix
or task-progress flag is wrong. That does not invalidate the trajectory's
existing safety argument, but it can invalidate a controller comparison.

`verify_planar_decisions` in `decision_replay.py` first runs that physical
verification, then regenerates each complete experiment with its recorded
`PlanarConfig` using the current implementation. It compares scientific records
strictly, including JSON types, and reports the first differing field path.
It covers all twelve supported planar methods, including stateful continuation
reuse, failed decisions and initialization failures. No controller, fallback
or online acceptance condition is changed.

## Checked properties

The regenerated records include:

- nominal policy and all declared configuration parameters;
- candidate construction, order, rejected prefixes, margins and accepted control;
- exact QP results, solver constraints and command-lattice decisions;
- sufficient-condition, numerical-width and sign evidence with its stated goal;
- explicit distinctions among search exhaustion, count limits, initial-domain
  exclusion, initialization failure and infeasibility;
- stopping-plan diagnostics, retained plans and stateful command sources;
- exact trajectories, offline classifications and existing execution proof sources;
- termination, intervention values, goal flags and scientific aggregates.

The existing runner/controllers and certificate engine are reused. This proves
consistency with that implementation, not correctness of an independent
controller implementation or every program path. It does not complete a source
paper replication or establish physical model/observation/actuation validity.
Artifacts made with changed historical algorithms or scientific schemas can
legitimately fail a current-implementation replay; their original physical
certificate is not thereby revoked. Use their recorded revision when necessary.

## Explicit exclusions

The projection omits measured clocks and deadline observations only at known
schema locations. It also omits floating display state/action duplicates and
uncertified root/clearance estimates. All exact values remain checked.

The returned `excluded_timing_fields` and `excluded_display_fields` record those
locations. For example, `records[*].solve_ns` is excluded, but an unexpected
`details.solve_ns` field is retained and rejected. Configuration p/v, deadline,
tolerances and execution assumptions are retained; the exclusion is not a
recursive wildcard on a field name. The original input is not mutated.

Clock consistency, timing authenticity and hard deadlines are outside this
audit. Changing only excluded fields can leave the scientific replay valid.
It must not be presented as verification of those excluded observations.

## Meaning of a verified result

A verified trace can contain a collision witness or an unresolved execution;
it means that the reported experiment reproduces, not that the controller is
safe. Conversely, a valid online comparison can certify execution when a
bounded offline geometric oracle remains unknown. That distinction is preserved
during regeneration. No unresolved online certificate is promoted to safe.

Per-run hashes use the retained scientific projection with sorted JSON keys.
They tie the report to the checked record contents, but do not authenticate an
arbitrary source file or manifest. Input hashes, exact source revisions and
the mathematical verification scope must accompany published results.
