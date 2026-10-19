# tick-trap development

The project is named **tick-trap**. It is a research instrument for sampled robot
control; no original controller or publication-level novelty has been established.

- Preserve the distinction between sampled safety, continuous-trajectory safety,
  viability, and a filter's initial domain. Never promote a numerical estimate to
  a validated certificate. Unresolved certificates must remain `unknown`.
- Every safety claim must name its model, initial-set, actuation, observation,
  numerical, and execution assumptions. An infeasible filter stops explicitly;
  do not introduce an unverified fallback.
- When implementing a published condition, record the paper version and equation,
  derive the specialization and constants, and test independent reference cases.
  A simplified sufficient condition is not a complete paper reproduction.
- Compare matched initial conditions and physical horizons. Keep empirical
  computation time distinct from the simulated execution delay and offline oracle.
- Keep configurations, seeds, tolerances, source hashes, and software provenance
  with experiment artifacts. Do not infer calibrated uncertainty from fit error.
- Make small commits with plain descriptions. Use the user's configured Git
  identity and do not add assistant attribution or co-author trailers.
- In this managed workspace `.git` writes are restricted; use
  `sh scripts/git-local ...` for the history in `.tick-trap-git`. Refresh the
  portable bundle after finishing: `sh scripts/git-local bundle create
  tick-trap-history.bundle --all`.

Validation: `.venv/bin/python -m unittest discover -s tests -v`, or
`PYTHONPATH=src python -m unittest discover -s tests -v` without installation.
The package has no runtime dependencies beyond Python 3.11+.
