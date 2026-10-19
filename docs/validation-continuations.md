# Stored-continuation validation — 19 October 2026

The stored-plan milestone passes 94 automated checks. It adds prefix reuse of
validated stopping proofs, explicit retained-plan control, operation budgets,
separate initialization timing and exact replay of saved experiment evidence.

The results below use clean published commit
`68813f3df885cbbf773d89da9910bf7dfc944c81`, with package source SHA-256
`a132f0ab87f72954f1380981a93cb176c7011ddbebc61090981b5f3121a6972a`.
The construction follows established predictive safety-filter ideas; it is a
restricted exact-model reference, not a new algorithm or full paper replication.

## Matched eight-second experiment

`configs/continuations.json` compares the one-interval trajectory filter with the
stored-plan reference over four periods, two initial positions and three
candidate budgets. Each row below contains eight configurations. All initial
states have a certified admissible stopping continuation.

| Method | Candidate budget per update | Safe full horizon | At goal at end | Budget stops | Exhausted full search |
| --- | --- | ---: | ---: | ---: | ---: |
| One-interval trajectory | 0 | 0 | 0 | 8 | 0 |
| One-interval trajectory | 1 | 4 | 4 | 4 | 0 |
| One-interval trajectory | Unrestricted | 6 | 6 | 0 | 2 |
| Stored continuation | 0 | 8 | 0 | 0 | 0 |
| Stored continuation | 1 | 8 | 4 | 0 | 0 |
| Stored continuation | Unrestricted | 8 | 8 | 0 | 0 |

No collisions or unresolved executed intervals occurred in this experiment.
Every one of the 24 stored-plan runs retained a certified admissible continuation
after every executed update. At zero search budget these robots stopped safely,
without reaching their goals. Safe stopping and task completion are separate
outcomes. Terminal goal flags were checked against the exact final positions,
velocities and configured tolerances.

An analytical radial test isolates the distinction: begin at position
`(1.06,0)`, velocity `(-0.3,0)`, circle radius `1`, acceleration bound `1`, and
period `0.1`. The nominal acceleration `(-1,0)` keeps the next hold safe but leaves
clearance `0.025` and approach speed `0.4`. Its subsequent radial braking distance
is `0.08`, so the prescribed continuation collides. The stored-plan reference
instead selects `(0.5,0)` from the declared candidate set and keeps a certified
future plan. This test does not rule out every possible steering manoeuvre or
claim to compute the planar viability kernel.

## Computation and proof reuse

Initialization is measured before simulated execution. All candidate, hold and
replacement-plan checks are included in online solve time. Offline stopping and
trajectory diagnostics are excluded from that online measurement and reported
separately.

For the representative period `0.1`, initial position `(-2,0.3)` run:

| Stored-plan search budget | Initialization (µs) | Median controller update (µs) | At goal at end |
| --- | ---: | ---: | --- |
| 0 | 557.4 | 24.5 | False |
| 1 | 594.0 | 835.1 | False |
| Unrestricted | 564.4 | 1535.7 | True |

These are empirical times from a single host along different state trajectories,
not a controlled microbenchmark or a worst-case bound. No deadline misses were
observed in the 48 runs. Operation-count limits do not establish hard real-time
safety. With zero search budget, candidate construction, sorting and new
trajectory certification are skipped; those absences are explicitly tested.

Proofs retain their original intervals when a prefix is consumed. Their
nonnegative lower bounds apply to remaining subintervals; old upper witnesses are
not reinterpreted as minima of shorter suffixes. An unknown new certificate cannot
authorize an action, but does not undo an already certified plan. Tests also
confirm that state, obstacle or update-period mismatches revoke the plan rather
than apply a stale fallback.

## Saved-evidence replay

The verifier reconstructed all 2,539 executed intervals and 1,800 retained plans
in the continuation experiment, with 5,000 distinct certificate replays. It found
zero unsafe or unresolved intervals. Altered actions, endpoint states, proof
bounds, consumed prefixes and completion summaries are rejected by tests.

As a separate check, the earlier 48-run planar baseline was replayed: 1,206
executed intervals, including its four correctly recorded collision witnesses.
That replay returned verified records with four unsafe intervals. Thus a
verified artifact is not confused with a safe experiment.

Replay uses the same validated polynomial engine; it checks the exported control
and proof bookkeeping independently of running the controller, but is not a
second mathematical certification implementation. It does not validate physical
model fidelity, uncertainty estimates or actual deadline execution.

## Reproduce

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/continuations.json --output results/continuations
PYTHONPATH=src python -m tick_trap verify --runs results/continuations/runs.json --output results/continuation-verification
```

The experiment exports exact JSON evidence, CSV metrics, a Markdown report,
source/configuration provenance and quadratic-path SVGs. Dashed path segments
identify stored-plan execution. The local Git bundle retains the full history.

The next research gate remains a stronger published sampled-data comparator and
the line-by-line theorem-assumption comparison. These results demonstrate a
working research instrument and a known recoverability distinction; they do not
establish publication-level novelty, robust learned safety or delayed-execution
guarantees.
