# Representation and tolerance audit — 23 October 2026

Positive barrier scaling changes some finite-work certification decisions when
the numerical absolute width tolerance is held fixed. Equivalent original-value
widths restore the converted bounds, witnesses, stopping flags and work counts
in every tested representation. Pure time substitution also preserves those
converted certificates. This is a numerical convention check, not a new method
or a controller change.

All 241 tests pass; [source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39914103336)
passes on Python 3.11–3.14. The [mathematical contract](representation-contracts.md)
derives the transformations and their consequences for the current exact
rational algorithms, including the auxiliary constraint's time derivative.

## Exact source and evidence

Generation and exact regeneration use clean source
`c5dc2c0192b9623a28114ccd4a6d206d982a7c25`, runtime source SHA-256
`c691ef322d1b9fff562f1c2995c4d8b9af3f4752c3a0f1f5cc1fb64df77a3225`.

- [Compact groups and representative tangent cases](data/representation-summary.json)
- [Complete evidence archive](data/representation-evidence.tar.gz): 10 files,
  111,185,875 uncompressed bytes; 2,919,214 compressed bytes
- [Per-member and archive hashes](data/representation-manifest.json)

The archive preserves original and transformed coefficients, exact sign
references, raw and converted certificate bounds/witnesses, final stationary
boxes, tolerances, work counts, input integer bit lengths, joint-control
classifications, configuration, provenance, regeneration and hosted CI evidence.
It does not duplicate every intermediate Sturm chain in this sweep; exact
regeneration rebuilds them. The separate minimum-reference archive retains its
original full counting proofs. The archive SHA-256 is
`3d9801e086657a563701c11049c9e79347ae59a7b3c1970c0f16c4368d0e976a`.
The versioned compact file is byte-identical to archived `compact.json`.

The input is the versioned [minimum-reference archive](data/minimum-reference-evidence.tar.gz),
SHA-256 `fbd9283296d6bf6432e9d1e0dcc8230d28931a917dffb9ceddc98975c3522323`,
from clean source `b49b1faf4e72b582d67ec82d32f1ca3dbd42167d`. Its archive,
manifest, catalog and metadata hashes are recorded as input dependencies. The
underlying physical polynomial construction and original study remain documented
in the [minimum-reference validation](validation-minimum-reference.md).

## Matched experiment

The catalog retains 550 distinct polynomials representing 672 h/psi uses over
the same 259 fixed candidate controls in ten states. The exact planar model,
static circles, held bounded commands, command quantum, exact observation and
initial-domain assumptions are inherited without change. Complete sign truth
is 146 jointly safe controls and 113 violating h or psi. Auxiliary violation
does not necessarily mean geometric collision; viability remains separate.

The [configuration](../configs/representation-study.json) compares Bernstein
minimum refinement, Bernstein sign stopping and stationary-root/interval-Horner
minimum bounds. It uses scales 1e-6/1/1e6, physical or unit-interval time, base
width 1e-12 and individual per-polynomial allowances 0/8/64. Two width policies
give 108 settings and 59,400 represented certificate assessments, plus their
original-representation baselines. Cached identities reuse results; there are
41,310 backend evaluations. These are repeated numerical questions on a fixed
catalog, not independent trials or timings.

For scale a and physical duration T, the transformed polynomial is either
`q(t)=a*p(t)` on `[0,T]` or `q(s)=a*p(T*s)` on `[0,1]`. Positive a preserves its
exact sign. Value bounds are divided by a and unit-time witnesses multiplied
by T when comparing with the original query. Physical sampling periods,
trajectories, control candidates and horizons do not change.

`fixed_absolute` keeps represented tolerance eps=1e-12. Its equivalent original
value width is eps/a. `equivalent_width` uses represented tolerance a*eps, so
the original value-width request remains eps. This is a declared comparison
policy, not an adaptive tolerance estimator or a changed controller default.

## Fixed absolute tolerance changes unresolved outcomes

At allowance 64 with physical-time representation, fixed represented width
1e-12 gives:

| Certifier | Scale | Safe controls accepted | Unsafe h/psi controls rejected | Unknown safe / unsafe | Splits over distinct polynomials |
| --- | --- | ---: | ---: | --- | ---: |
| Bernstein minimum | 1e-6 | 144 | 112 | 2 / 1 | 1,883 |
| Bernstein minimum | 1 | 145 | 113 | 1 / 0 | 3,823 |
| Bernstein minimum | 1e6 | 145 | 113 | 1 / 0 | 5,798 |
| Bernstein sign | 1e-6 | 144 | 112 | 2 / 1 | 147 |
| Bernstein sign | 1 | 145 | 113 | 1 / 0 | 174 |
| Bernstein sign | 1e6 | 145 | 113 | 1 / 0 | 195 |
| Stationary minimum | 1e-6 | 144 | 113 | 2 / 0 | 4,048 |
| Stationary minimum | 1 | 145 | 113 | 1 / 0 | 7,964 |
| Stationary minimum | 1e6 | 145 | 113 | 1 / 0 | 11,878 |

At small scale the two Bernstein modes lose one safe acceptance and one unsafe
rejection to unknown. The stationary method loses one safe acceptance. At large
scale classifications remain unchanged here, but refinement work increases.
No represented certificate contradicts exact sign truth at any setting; no
joint-unsafe control is accepted and no joint-safe control is rejected.

These accepted/rejected labels are offline assessments of both required paths
at an already fixed input. No action search or closed-loop experiment occurs
in this audit. Splits are counted once per distinct polynomial, not per physical
property use; they therefore differ from earlier controller-query totals.
The three routines also perform different primitive arithmetic. No runtime
advantage or equal-cost conclusion follows from this table.

## Equivalent widths and time substitution

With equivalent original-value widths, every scale and time basis recovers the
corresponding baseline at every allowance. All 29,700 equivalent-width certificate
assessments match converted bounds, witness time, status, precision/budget flags,
stopping reason and split counts, including stationary root-count work. At
allowance 64 the common joint classification is `145 accepted / 113 rejected /
1 unknown`; the respective distinct-polynomial split totals remain
3,823 / 174 / 7,964 for the three routines.

Pure time substitution matches after conversion for both width policies in
every assessment. This does not establish equal rational bit complexity or
runtime. Input numerator/denominator bit lengths are saved as encoding
descriptors; intermediate coefficient growth and deadlines are not bounded.
No elapsed-time samples were collected.

The archived psi is composed with physical time, rather than redefined using
the wrong derivative. For `H(s)=h(T*s)`, the existing property is
`psi(T*s)=H'(s)/T+lambda*H(s)`. Replacing it by `H'+lambda*H` would generally
change the constraint. The contract note and regression test check the correct
conversion. A common numerical tolerance on h and psi is still not a common
physical clearance error.

## Interpretation and remaining gates

The analytical scaling/time identities and exact-algorithm covariance argument
are derived in the contract note. The finite-catalog counts and successful
regeneration are observations. Different fixed-width results arise without
floating-point rounding; they reflect a changed original-value stopping request.
This explains a comparison convention, not a newly discovered safety theorem.

Unknown remains unknown, including width-attained intervals around tangencies.
Tests check that consuming an iterable of property statuses cannot silently
promote an unresolved joint requirement. Other tests reject changed tolerances,
bounds, work counts, source signs and missing/duplicate property coverage.
Regeneration compares every recorded field; it is not formal program verification
or independent implementation of every calculation.

Existing controller choices, online proofs, termination and fallback behavior
remain untouched. No original algorithm or publication-level novelty is claimed.
Further work includes shared-total-work and end-to-end execution studies,
intermediate bit growth, actual elapsed costs, optimized external baselines,
uncertain dynamics and complete source-paper experiment reproductions. A scale-
equivalent certificate alone does not establish recursive feasibility or a
physical-robot guarantee.

## Reproduction

From a clean checkout with the versioned input archive and Python 3.11+:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/audit-representation.py --config configs/representation-study.json --output results/representation-reproduction
PYTHONPATH=src python scripts/audit-representation.py --verify results/representation-reproduction
```

Verification writes the compact source-hashed summary after exact regeneration.
Scientific fields are deterministic; timestamps, paths and source identity vary
on later revisions. Archive/member hashes establish consistency with the saved
manifest, not authenticity of an arbitrary replacement manifest.
