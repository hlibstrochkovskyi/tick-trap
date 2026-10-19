# Retaining a certified continuation

`ContinuationFilter` is a stateful reference for the exact planar double
integrator with static circles, a fixed update period, componentwise actuator
bounds and a declared command quantum. It uses finite candidate search and
validated polynomial trajectory checks. Its terminal set is collision-free
rest, where zero input preserves the state indefinitely.

The general strategy of retaining a feasible future policy towards a safe
terminal set is established predictive safety-filter machinery; see
[Wabersich and Zeilinger, 1812.05506v4, Section 4](https://arxiv.org/html/1812.05506v4).
This restricted reference is not a reproduction of that paper's MPC optimization,
uncertainty treatment, experiments or probabilistic guarantees. No new control
algorithm or novelty claim is made.

## What changes compared with checking the next hold

A trajectory can be safe over the next update interval while losing every
continuation in a prescribed recovery family. Here the family is componentwise
braking to exact rest on the update/command lattice. Failure of this particular
recovery does not establish that all steering manoeuvres are impossible.

The reference starts only if a complete braking plan is certified. At an update:

1. Consider the same ordered finite command set used by the other candidate
   filters. A new action must have a validated safe hold and a certified stopping
   continuation from its actual analytical end state.
2. If both succeed, apply that action and retain its already-certified future
   stopping plan. The recorded proof includes both the hold and the continuation.
3. If no new plan is certified, or the candidate count budget runs out, execute
   one update from the previously retained plan and keep its remaining suffix.
4. At certified rest, zero input is the terminal policy. Zero input is never
   substituted for braking a moving robot.

Initialization failure returns no action. Exact state, obstacle or command-limit
mismatches revoke the stored plan and also return no action. Reinitialization
requires a new certificate. A geometric state that lacks a certificate is not
automatically labelled nonviable.

## Restricted safety argument

Initially the filter has a finite admissible plan with nonnegative barrier lower
bounds on every continuous segment, ending at collision-free rest. A successful
replacement supplies the same property after the selected action. Otherwise the
applied action belongs to the existing certified plan, whose suffix remains
admissible and safe. At the terminal state, zero preserves rest and clearance.
Induction therefore preserves a certified safe continuation after every update,
under the declared exact dynamics and execution assumptions.

This is stronger than checking only the next interval, but it computes neither
the full viability kernel nor a globally least-invasive safe control. The accepted
action is the first certified candidate within the inspected portion of the
declared ordering. A retained action can lie outside the Cartesian candidate grid
while still satisfying the actuator bounds and command quantum.

## Proof reuse and numerical scope

A certificate's original interval is retained in the record as a prefix is
consumed. Its nonnegative lower bound applies to every remaining subinterval.
Its upper witness may lie in the consumed prefix, so it is not reported as a
minimum enclosure for the shorter remaining path. The offline trajectory oracle
can independently compute bounds for the interval actually executed.

`unknown` certificates never authorize new actions. They also do not invalidate
an already proved remaining plan. Candidate and subdivision budgets limit
operation counts; they do not bound wall-clock execution or rational bit growth.
These budget limits can be lowered between updates without recertifying the old
plan. They are not proof of safety under an execution deadline miss.

Initialization expense must be recorded separately before simulated execution.
Online candidate, hold and recovery checks all belong to controller solve time.
Offline diagnostics remain separate. The simulated controller updates are
instantaneous; measured runtime does not silently become physical actuation
delay. State uncertainty, disturbances, moving obstacles, mismatched dynamics and
delayed execution require additional arguments and are not covered here.

Safety does not imply task convergence. Repeatedly following the stored plan can
stop safely without reaching the goal. Performance and safety must be reported
as separate outcomes.

## Experiments

The stateful reference is exposed as `backup_candidates`. The matched experiment
varies update period, initial position and candidate count budget over an
eight-second physical horizon:

```sh
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/continuations.json --output results/continuations
```

`max_candidates` applies to all finite-candidate methods. A stateless filter that
uses up that budget before finding an accepted command returns `budget_exhausted`
and no action. The stored-plan filter can instead use its prior certificate.
The report distinguishes candidate renewals, stored-plan updates, terminal holds,
and budget exhaustion. It records controller initialization expense independently
from solve time and offline viability diagnostics. Dashed SVG segments show
actions taken from the retained plan.

An initialized stored-plan filter reports whether a certified continuation was
retained after every executed update. This field is null when there were no
executed updates; initialization or an unexecuted plan is not a safe completed
horizon. An initial stopping diagnostic can succeed even when a cheaper online
initialization check remains unresolved, so those two results are also separate.

Saved evidence can be replayed without running the controller:

```sh
PYTHONPATH=src python -m tick_trap verify --runs results/continuations/runs.json --output results/continuation-verification
```

The verifier reconstructs exact states and admissible commands, recomputes the
saved polynomial enclosures, and checks initialization, replacements, consumed
prefixes, remaining suffixes and terminal rest. It rejects altered commands,
endpoints, bounds and plan counters. Required initialization proofs must be present
in the input artifact. Plot curves are derived from the exact fields.

`verified` means the exact artifact is consistent with its declared mathematical
model; a correctly recorded collision witness can also be verified. The output
therefore includes unsafe and unresolved interval counts. The verifier shares the
existing polynomial engine and does not independently establish its mathematics,
physical model fidelity, uncertainty coverage or real-time execution properties.
