# Foundation validation — 19 October 2026

The first tick-trap foundation passes 40 automated checks under Python 3.12.13.
The checks cover independent analytical cases, explicit infeasibility, signed
velocity viability, published-condition constants, exact delayed dynamics,
polynomial enclosure witnesses, random quartic lower-bound checks, repeated
critical points, tangencies, deterministic scientific outputs, and CLI artifacts.
Random dense checks supplement the enclosure tests; the enclosure argument itself
is analytical and does not rely on a grid.

## Executed experiments

These results were generated from commit
`d1229c0b19df2bbf136cce4220e7e1d73a4941f1`, with a clean tracked working tree.
The package source SHA-256 was
`b35a7cce2a08749b8b1f686d818820d8c835b05b5ca248b165a24a0dcdd47e6a`.
Later documentation commits do not change that source.

| Experiment | Cases | Completed safe horizons | Collision intervals | Infeasible stops | Outside-domain stops |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matched two-second baseline sweep | 24 | 10 | 5 | 9 | 0 |
| Matched one-second stress grid | 480 | 57 | 64 | 210 | 149 |
| Learned model and dynamics-change study | 16 | 1 | 2 | 10 | 3 |

No controller deadline misses were observed in these runs. This is an empirical
observation on this host, not a worst-case execution-time bound. The groups in the
stress grid mix initial infeasibility, model violations, and distinct controller
domains; their aggregate collision counts are not a method ranking.

The original analytical example returns safe sampled states and continuous
unsafety, with exact minimum `-1/100 m` at `1/10 s`. It correctly labels the initial
state nonviable. A separate test begins at `d=0.06 m, v=1 m/s`, which is viable
under `a=10 m/s²`, and demonstrates endpoint-only filtering missing a collision
over a `0.4 s` hold.

The planar curved example also returns safe endpoints and an unsafe continuous
trajectory. Its exact minimum squared-distance barrier is `-0.0199 m²`.

The 36-configuration certificate-cost benchmark spans six trajectories, three
precision settings, and two subdivision budgets, with three timing repetitions.
Near-tangent positive and negative margins resolve at the tightest setting;
the non-dyadic exact tangency remains unknown. More subdivisions or a different
validated method would be needed for a conclusive tangency certificate. These
are expected limits of the chosen enclosure method, not evidence of novelty.

The 32-observation affine actuator fit gives gain `0.7997299971` and bias
`0.0961911435` for training dynamics with gain `0.8` and bias `0.1`.
Held-out mean-acceleration RMSE is approximately `0.00383 m/s²`, compared with
`1.19730 m/s²` for the unit model. After changing the true dynamics to gain `0.55`
and bias `0.2`, the learned model's RMSE rises to `1.48942 m/s²`.
The exact-hold reference collides under both models in the shifted case. Better
prediction error therefore cannot be reported as a robust safety certificate.

## Acceptance requirements

| Requirement from the audit | Foundation evidence and remaining scope |
| --- | --- |
| Reproduce the collision counterexample | Exact rational witness, test and SVG |
| Validate known mathematical results | Independent cases and derived constants pass; full external theorem/paper replication remains pending |
| Separate sampled and continuous safety | Distinct fields and certificates; unresolved signs remain unknown |
| Handle infeasibility explicitly | Stops recorded with reasons; no fallback action is invented |
| Compare relevant published methods | Breeden and Tan conditions specialized to the wall; stronger variants and full modern paper experiments remain pending |
| Quantify computational overhead | Controller and offline certification timed separately; empirical deadline misses recorded; no real-time guarantee |
| Preserve reproducibility | Embedded configs, seeds, exact values, tolerances, source/config hashes, version, platform, Git revision, and raw observations |

At this first snapshot, planar controller synthesis, delay-aware viability, calibrated learned uncertainty,
iterative QP tolerance experiments, and publication-level comparisons are not
implemented. These are explicit next research stages, not silently assumed
capabilities of this foundation.

The subsequent planar control milestone is documented separately in
[planar validation](validation-planar.md).

## Reproduce locally

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap counterexample
PYTHONPATH=src python -m tick_trap sweep --config configs/baselines.json --output results/baselines
PYTHONPATH=src python -m tick_trap sweep --config configs/stress.json --output results/stress
PYTHONPATH=src python -m tick_trap certify
PYTHONPATH=src python -m tick_trap learn --output results/learning
PYTHONPATH=src python -m tick_trap benchmark --output results/certification
```

Each output directory contains configuration and software provenance. Scientific
outputs are reproducible within the recorded runtime; timestamps and empirical
timing fields vary. Learning data are saved to avoid dependence on future random
generator implementations. Generated run artifacts live under ignored `results/`.
