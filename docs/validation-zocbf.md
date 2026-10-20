# Zero-order contract audit — 20 October 2026

This offline audit tests inter-sample buffers, input pairing and numerical
endpoint error on prescribed holds. All 201 tests pass, and
[source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39475616354)
passes on Python 3.11–3.14. No controller is added or changed.

The [derivation](zocbf-contracts.md) pins
[Tan et al., arXiv:2411.17079v2](https://arxiv.org/html/2411.17079v2),
Definition 1/Eq. (4), Lemma 1/Eq. (5), Theorem 1 and the numerical-model
tightening in Eqs. (19)–(20). The recurrence uses the previous command at the
initial state and the new held command at the terminal state. The buffer and
prediction margin play different roles; neither can replace the other.

## Exact source and evidence

The generation, regeneration and compact exporter use clean revision
`c99c98e4551d2c0e9e0b8ef531425c6de26de61e`, runtime source SHA-256
`43939220b9107efaad7579b9db0001568ca663b3d495415e00c454c6f3e845f3`.

- [Compact groups, transitions, premise strata and worked cases](data/zocbf-summary.json)
- [Complete evidence archive](data/zocbf-evidence.tar.gz): 11 files,
  1,159,854 uncompressed bytes; 28,441 compressed bytes
- [Archive and individual file hashes](data/zocbf-manifest.json)

The archive preserves all 40 holds, 240 buffer assessments and 1,440 condition
assessments, exact polynomials and extrema, independent sign references,
configuration, provenance, report, CSV, verification and hosted CI run/job records.
Its SHA-256 is `f4ea1baa2419197ee4c89b1a15266a54459890bf65ad897b20bd23bc28084d89`.
The compact file is byte-identical to the archived summary.

## Property and experimental scope

The exact model is `d_dot=-v, v_dot=u`, with bounded scalar acceleration,
exact observation, instantaneous command changes and zero-order hold. Each
case declares its actuator limit, tau, sigma and gamma. The affine proxy is
`h=d-tau*v-sigma*u`, with tau,sigma>=0 and comparison gain gamma in (0,1].
It is not a rollover model or a general collision/viability condition. Geometric
clearance and ideal stopping-distance viability remain separate fields.
The terminal constraint uses the current held command, immediately before the
next update. No future input jump is certified by this hold.

Ten prescribed cases at four periods yield 40 physical holds. Of these, 36 have
a nonnegative previous-command left value; 24 have a safe actual proxy path.
Among the 36 safe-left holds, 20 have a safe proxy path and 16 do not. The four
unsafe-left cases are kept as a separate recursion-premise stratum, not removed
from the evidence or automatically classified as unsafe new holds.

All six buffer choices and six prediction/input-pairing variants evaluate those
identical holds. There is no action search, synthesized controller, statistical
sampling, timing benchmark, deadline measurement or execution-delay model here.
The earlier matched timing studies remain separate evidence.

## Buffers and exclusions

This table uses the correct previous-input/exact-endpoint recurrence and only
the 36 safe-left holds. A condition pass is not automatically a valid certificate.

| Buffer | Condition passes | Passes with unsafe actual proxy path | Safe proxy holds rejected |
| --- | ---: | ---: | ---: |
| Norm-product tube | 10 | 0 | 10 |
| Projected tube | 10 | 0 | 10 |
| Candidate derivative | 13 | 0 | 7 |
| Exact absolute-difference reference | 14 | 0 | 6 |
| Exact backward-drop reference | 17 | 0 | 3 |
| Endpoint only, delta=0 | 20 | 3 | 3 |

The first five satisfy the required backward-difference bound for every
declared hold. The endpoint-only diagnostic has no general inter-sample bound.
Its three unsafe passes violate that local buffer premise, not the published
theorem. More permissive finite-case counts do not establish a better online
algorithm or a computation advantage.

The norm-product tube is the restricted Eq. (5) recipe, with rational upper
enclosures of both square roots. At tau=sigma=0 it matches the existing wall
comparator. The other bounds are explicitly derived local offline references;
some vanish. They do not constitute full published controllers, positive uniform
constants on the unbounded domain, or new certification algorithms.

For `d=0.45, v=1.2, u=-2, tau=0.3, T=0.4`, the proxy is
`h(t)=0.09-0.6*t+t²`, with an exact tangency at t=0.3. At gamma=1 the backward
reference delta=0.01 accepts; the absolute reference delta=0.08 rejects.
Both statements follow from exact extrema. Contact at zero is permitted.
An independent square-free/Sturm sign reference agrees with the quadratic
minimum; no floating root tolerance is used to turn a near-zero value into zero.

## Prediction and input arguments

The following counts are unsafe-proxy condition passes among the same 36
safe-left holds. Each cell is a diagnostic count, not a controller collision rate.

| Buffer | Unadjusted Euler | Error-tightened Euler | Endpoint with stale input |
| --- | ---: | ---: | ---: |
| Norm-product tube | 0 | 0 | 7 |
| Projected tube | 0 | 0 | 7 |
| Candidate derivative | 0 | 0 | 8 |
| Absolute reference | 1 | 0 | 8 |
| Backward-drop reference | 3 | 0 | 9 |
| Endpoint only | 4 | 1 | 11 |

Exact midpoint matches the exact recurrence in every assessment. The Euler
constraint discrepancy is exactly `abs(u)*T²/2`. Tightening by that bound is the
paper's numerical-error construction specialized to this affine model. It
restores the exact endpoint implication, but does not supply a missing hold
buffer: the endpoint-only column still has an unsafe pass. Conversely a valid
buffer alone does not repair an invalid endpoint prediction.

At `d=0.1, v=-0.45, u=10, T=0.2`, the exact endpoint is -0.01, whereas Euler
predicts 0.19. Its margin is 0.2. The valid absolute reference delta=0.120125
allows unadjusted Euler to pass but rejects the tightened condition. These
numbers concern the proxy and free-motion model; they are not hardware results.

For the stale-input example `d=10, v=0, previous_u=0, new_u=1, sigma=20,
tau=0.3, T=0.1`, the initial left value is 10 but the new right value is -10.
The actual endpoint is -10.035; evaluating it with the previous input instead
gives 9.965. Even the norm-product buffer can then pass the wrong endpoint
condition. Geometric clearance remains positive. The instrument never deploys
this diagnostic variant as a safety certificate.

Resetting the start reference to the new input is also not the published
history relation. It can nevertheless prove a hold independently: combining
its passing inequality with the valid backward bound implies a nonnegative
new right value and whole held path. No unsafe reset-start pass occurs with
any of the first five valid buffers. Tests include both a safe control excluded
and a safe control admitted relative to the original history relation. Their
different acceptance sets must not be mistaken for automatic unsoundness.

## Proof, observations and remaining gates

The exact held polynomial, quadratic extrema, buffer hierarchy, prediction-error
formula and the restricted one-hold implication are derived in the mathematical
note. The measured finite-case counts, transition matrices and agreement with
the independent sign implementation are reproducible observations.

`one_hold_implication_ingredients` requires a nonnegative target
`(1-gamma)*h_start`, a valid backward bound, a valid lower endpoint prediction
and a passing residual. The bound and prediction flags can be checked offline
against the exact path; a flag for one selected input is not an a priori
online bound over an entire domain. The Euler tightening and the first five
buffer formulas have the separate analytical arguments stated above.
No unsupported online assumption is inferred from a post hoc check.

A unit test also preserves the valid gamma=1 case with an unsafe previous pair:
the target is zero, so correct new-endpoint and hold bounds can certify the new
hold. The safe-left recursive theorem premise remains false, and neither the
preceding interval nor global attraction is certified by that test.

Still unverified: existence of a global ZOCBF over the declared unbounded proxy
set, uniform positive buffer feasibility, recursive admissible synthesis,
the paper's nonlinear rollover experiments, nonlinear validated flow prediction,
uncertainty calibration and hardware execution deadlines. No physical-safety,
new-method or publication-level novelty claim follows from this audit.

## Reproduction

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m tick_trap zocbf-audit --config configs/zocbf-audit.json --output results/zocbf-reproduction
PYTHONPATH=src python -m tick_trap verify-zocbf --audit results/zocbf-reproduction/audit.json --output results/zocbf-reproduction/verification
python scripts/summarize-zocbf.py --input results/zocbf-reproduction --output results/zocbf-reproduction/summary.json
```

Use a clean committed checkout. Deterministic scientific fields regenerate;
timestamps, paths and source identity change on later revisions. Verification
rejects changed history inputs, margins, bounds, statuses, labels or coverage.
The exporter checks hash linkage, clean source identity, the buffer ordering,
midpoint agreement and reconciliation of unsafe-pass premise strata. The archive
tool reads back and hashes every saved member. None is a formally verified
implementation or a proof of all assumptions in the original paper.
