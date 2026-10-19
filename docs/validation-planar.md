# Planar control validation — 19 October 2026

The planar milestone passes 70 automated checks, including the original wall
checks. It adds exact two-input QP projection, independent HOCBF derivative cases,
constraint checks after command rounding, multiple obstacles, finite-search
outcomes, sufficient stopping plans, CLI exports and matched-control audits.

The experiments below were generated from the clean published commit
`b2e856a052463350cbad60e389031bfaaea9aebe`, with package source SHA-256
`b2678d58775ea93ff6fa30f7c6db25aca317f9c3812a4f6b9770e65b36b5d48a`.

## Matched planar rollouts

The default comparison crosses six filters, four update periods and two initial
positions, using the same four-second physical horizon and two circular obstacles.
Every initial state has a certified admissible stopping continuation. This is a
sufficient viability witness, not an evaluation of the complete viability kernel.

| Method | Runs | Safe full horizon | Observed collision | Finite search exhausted |
| --- | ---: | ---: | ---: | ---: |
| Unfiltered nominal | 8 | 4 | 4 | 0 |
| Emulated HOCBF QP | 8 | 8 | 0 | 0 |
| Endpoint candidates | 8 | 6 | 0 | 2 |
| Chord candidates | 8 | 6 | 0 | 2 |
| Zero-order candidates | 8 | 0 | 0 | 8 |
| Validated trajectory candidates | 8 | 6 | 0 | 2 |

There were no empirical deadline misses in this run. These measurements do not
bound worst-case execution time. The zero-order condition used here is the
documented conservative local-tube specialization, not the strongest possible
implementation of the paper. An exhausted search is not continuous-input
infeasibility, and ending a simulation does not safely stop a moving robot.

None of these four-second runs met the configured terminal goal-and-speed
tolerances. Safe completion therefore must not be reported as successful
navigation. The current nominal policy is a simple PD controller; this comparison
does not establish a task-performance ranking or convergence theorem.

## Matched-control audit

Five fixed states and 126 distinct declared commands were audited against exact
continuous-path enclosures. This avoids comparing methods only after they have
already driven the robot to different states.

- In the curved hidden-collision case, endpoint and chord checks each admit five
  commands with validated collision witnesses. The HOCBF initial domain does not
  include that state, and is marked not applicable.
- In a straight-crossing case with a certified braking continuation, endpoint
  checking admits eight unsafe commands and chord checking admits five. The
  geometry of other accelerated candidates can differ from the nominal straight
  trajectory, which is why chord acceptance and path safety differ here too.
- In the short-hold near-obstacle case, all 25 commands are certified safe. The
  local zero-order buffer excludes all 25; the HOCBF condition excludes 10.
- Tangency cases retain five unknown trajectory signs rather than silently
  treating a small numerical estimate as proof of safety.

These are restricted-system diagnostics, not new failure modes or a publication
claim. Rejection by a sufficient condition does not contradict its theorem.
More permissive safe controls need not preserve terminal feasibility or task
progress. The candidate grid does not measure the continuous feasible-set volume.

## Reproduce

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap planar-run
PYTHONPATH=src python -m tick_trap planar-sweep --output results/planar-baselines
PYTHONPATH=src python -m tick_trap planar-audit --output results/planar-audit
```

Each experiment saves exact records, source/configuration provenance and a
Markdown report. Rollouts also export CSV metrics and quadratic-path SVGs for
every run. The SVG curves use the actual held-input quadratic, rather than a
straight interpolation between sampled positions. Float drawing coordinates are
illustrative; the rational fields and certificates carry the safety evidence.

Next scientific work includes preserving a certified continuation during control
selection, tightening and comparing published sampled-data bounds, full paper
experiment reproduction, and testing actual task progress over matched horizons.
Delay-aware planar guarantees and calibrated learned uncertainty remain open.

The subsequent stored-plan and saved-evidence replay milestone is recorded in
[continuation validation](validation-continuations.md).
