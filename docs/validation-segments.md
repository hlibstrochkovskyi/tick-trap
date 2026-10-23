# Chord and held-trajectory validation — 23 October 2026

The connecting chord and the exact held-acceleration path can have different
safety classifications in either direction. The new offline audit derives and
checks their exact deviation and a standard tube implication. It makes no
controller change and does not close the published SSCBF proof-reading gate.

All 249 tests pass in a fresh Python 3.14.8 virtual environment with no project
or runtime dependency installation. The eight additional tests cover independent
analytical paths, signed perturbations down to `10^-80`, degenerate chords,
coordinate invariance, invalid algebraic squaring, multiple obstacles and exact
replay of sign evidence. Unsupported moving-obstacle fields are rejected rather
than silently interpreted as static geometry.
The generating revision's CI passes on Python 3.11–3.14.

## Exact source and evidence

Generation and exact regeneration use clean source
`8bf0983e6694334a9ba4d9f26f782b0302f95816`, package source SHA-256
`f7cd0b2de5fe5d7226e15af92b55bf0050af06c2bfd21d7336bb4fac0b015f92`.
The audit-script hash is also recorded because the package hash covers only
runtime package sources. Configuration values and their canonical hash are
embedded. This catalog has no randomness, numeric width tolerance, subdivision
allowance or elapsed-time experiment.

- [Compact classifications and provenance](data/segment-summary.json)
- [Complete exact evidence](data/segment-evidence.tar.gz): 11 files,
  160,700 uncompressed bytes; 17,650 compressed bytes
- [Per-member and compressed archive hashes](data/segment-manifest.json)
- [Source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39917336072)

The archive retains full per-obstacle inputs and polynomial sign proofs, chord
minima, peak deviation bounds, both tube-test guards, joint classifications,
report, embedded and original configuration, software/test environment, complete
test log, generation/replay provenance and hosted CI evidence. The versioned
compact summary is byte-identical to archived `compact.json`. Refer to the
manifest for member coverage. The compressed archive SHA-256 is
`c866ccc3ec57b659ef811826ff316a5c1e722094350ac44021fa9ba4d1505e0b`.

## What is proved under the declared model

The [mathematical contract](segment-contracts.md) derives
`p(t)-L(t)=u*t*(t-T)/2`, so the peak chord deviation is
`rho=||u||*T²/8`. For a static circle, a minimum chord distance `D>=R+rho`
is sufficient for safety of the actual path throughout this one hold.
With `A=D²-R²-rho²`, the radical-free condition is
`A>=0 and A²>=4*R²*rho²`; omitting either guard can invalidate the argument.

This is elementary interpolation and triangle-inequality geometry. It is not
presented as a new theorem or as an unread numbered condition from the SSCBF
paper. A failed sufficient condition is `unknown`, never proof of collision or
permission to execute. All obstacle implications must succeed for a certified
multi-obstacle hold. Independent full polynomial sign evidence stays separate.

The model is the exact planar double integrator with static circles whose
radii include robot size. Initial position/velocity and obstacle geometry are
known exactly; commands are bounded and held exactly for the recorded duration.
There is no delay, model mismatch, disturbance or observation error. Contact at
zero barrier is permitted. The initial set is each specified exact state; a
successful tube implication includes its initial geometric safety. No viability,
high-order controller domain or future safe continuation is assumed or proved.
Arithmetic is exact rational; program correctness has not been formally proved.

## What the finite experiment observes

The [configuration](../configs/segment-contracts.json) has 15 fixed holds and 16
obstacle queries. It includes exact tangencies, height perturbations `±10^-40`,
straight motion, coincident endpoints, inward/outward curvature, a nonsquare
acceleration norm and a two-obstacle conjunction. One deliberately initially
unsafe case tests the sign-before-squaring guard. This is an analytical test
catalog, not a representative environment distribution or controller ranking.

| Chord classification | Actual trajectory safe | Actual trajectory unsafe |
| --- | ---: | ---: |
| Safe | 8 | 3 |
| Unsafe | 1 | 3 |

Five holds have safe sampled endpoints but unsafe actual trajectories. Three
also have safe connecting chords. A separate arch has an unsafe chord and a
strictly safe trajectory; its independently factored barrier is
`16*(t*(1-t)-1/8)²+1/2`. Thus rejecting all unsafe chords can also exclude safe
held paths. This geometric observation does not compare the complete methods
or claims of the published controllers.

The tube condition certifies six holds, all safe according to the independent
complete sign reference. Nine remain `unknown`: three actually safe and six
actually unsafe. The audit retains those unknowns, including a joint hold where
only one of two obstacles fails the sufficient condition. Offline sign truth is
not substituted into a controller or used as a fallback action.

## What remains unverified

The publisher's abstract and accessible snippets for Pagnini--Malis article
101582 distinguish formal segment guarantees from empirical curved-path
performance. The author's publication list identifies `hal-05578359v1`, an ECC
2026 deposit, but its full text was inaccessible in this environment. The
[source-access record](segment-contracts.md#published-source-and-remaining-reading-gate)
preserves that limitation. The journal and deposit versions have not been
established to be identical. No numbered SSCBF equation, full proof, MPC
feasibility condition or original experiment has been reconstructed here.

The existing `segment_candidates` method therefore remains an exact chord
diagnostic, not an SSCBF/MPC implementation. The counterexamples do not refute a
theorem about segments. Full published-condition comparisons, validated
uncertainty/delay extensions, physical validity, viable continuation, hard timing
bounds and publication-level novelty remain unestablished.

## Reproduce and regenerate

From a clean committed checkout:

```sh
python -m venv /tmp/tick-trap-segment-clean
PYTHONPATH=src /tmp/tick-trap-segment-clean/bin/python -m unittest discover -s tests -v
PYTHONPATH=src /tmp/tick-trap-segment-clean/bin/python scripts/audit-segments.py --output results/segment-contracts
PYTHONPATH=src /tmp/tick-trap-segment-clean/bin/python scripts/audit-segments.py --verify results/segment-contracts
```

The scientific fields regenerate exactly from the embedded configuration;
timestamps, environment fields and their byte hashes can differ on a new run.
Replay checks full sign evidence, not only the table above. Its own source and
input hashes are retained separately. Hosted CI JSON is evidence for its
recorded revision; local reproduction does not generate new hosted CI evidence.

The existing `scripts/archive-audit.py` packs an evidence directory after its
environment and all replay metadata identify the same clean revision. The
recorded archive was made with `--input results/segment-final`,
`--output docs/data/segment-evidence.tar.gz` and
`--manifest docs/data/segment-manifest.json`. Its member hashes are read back
before publication.

To replay the committed evidence after checking its manifest:

```sh
mkdir -p /tmp/tick-trap-segment-evidence
tar -xzf docs/data/segment-evidence.tar.gz -C /tmp/tick-trap-segment-evidence
PYTHONPATH=src python scripts/audit-segments.py --verify /tmp/tick-trap-segment-evidence --output results/segment-archive-replay
```
