# tick-trap

Continuous-time safety analysis for sampled robot control.

tick-trap is a small research instrument for comparing sampled-state safety,
continuous-trajectory safety, and viability. It starts with analytically solvable
wall braking and planar acceleration-controlled robots. There is no claim of a
new safety controller or publication-level novelty.

The implementation uses the Python standard library. Run the reference checks:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Exact rational wall trajectories reproduce the 4 cm → −1 cm → 4 cm counterexample.
Planar circle checks combine a numerical stationary-point estimate with a separate
validated Bernstein polynomial minimum enclosure. Unresolved certificates return
`unknown`; a floating-point root estimate never establishes a guarantee.

All guarantees concern the declared mathematical model and input values. They do
not cover contact dynamics, unmodelled disturbances, or physical hardware.
