# Planar decision-replay audit — 22 October 2026

The instrument now checks whether saved experiments reproduce the declared
controller and task logic, alongside their physical trajectories and accepted
safety proofs. Both saved cohorts reproduce: 48 runs, 1,829 decisions and 3,222
candidate assessments. All 230 tests pass; the
[checking-source CI](https://github.com/hlibstrochkovskyi/tick-trap/actions/runs/39689519325)
passes on Python 3.11–3.14.

This does not change any controller, online certificate, fallback or published
experimental outcome. It adds a stricter, separate audit. The
[contract note](decision-replay.md) defines its exact projection and scope.

## Why the additional check matters

The physical verifier checks dynamics and safety evidence. It does not certify
every controller decision field or the entire candidate search. In a stationary
endpoint-filter example, changing a saved endpoint margin from `15/4` to `999`
leaves the actual trajectory and its safety proof unchanged. The physical
verifier therefore still accepts the trajectory. The new decision audit rejects
the changed margin. This is a scope distinction, not a counterexample to the
existing trajectory guarantee.

Tests also reject changed HOCBF objective values, segment and zero-order margins,
rejected candidate prefixes and order, nominal inputs, goal/viability flags,
failure labels and JSON types. Declared cohort coverage catches omitted,
reordered or replaced configurations even when individual remaining runs are
otherwise valid. It does not authenticate an arbitrary manifest or source file.

## Exact sources and evidence

Generation and checking use clean source
`33ba2cedcfaf45e7e7363109cc569a4826e8d479`, runtime source SHA-256
`e84fc71903afa8ad10105b19e4860e09b328ba2c7dde00c85459efe5cc10791b`.

- [Compact source-linked results and per-run scientific hashes](data/decision-replay-summary.json)
- [Complete replay evidence](data/decision-replay-evidence.tar.gz): 16 files,
  17,583,077 uncompressed bytes; 1,036,949 compressed bytes
- [Individual member and archive hashes](data/decision-replay-manifest.json)

The archive contains both complete input run files, their metadata, both full
verification results and checking provenance, configuration, method/case labels,
report, command logs and hosted CI run/job records. Its SHA-256 is
`62ea8f44529d67391b6ff3f38d81e6ab16ea8771810b520db2b12f1be9db62ca`.
The compact file is byte-identical to archived `summary.json`.

The archived cohort originates from clean source
`8aa08b50cd0d59a10b67f48c51c3c9e6a74bca34` in the original
[audit archive](data/audit-evidence.tar.gz). Its run-file bytes are preserved,
with original SHA-256
`3426eeeda627cd0cf3745739aaea8ac062bca8b34bdda2fccf4f696036f16b5d`.
The new archive records that input revision separately from the current
checking revision. Historical controller timings are not rewritten or reused
as measurements of this new audit's cost.

## Coverage and outcomes

| Cohort | Runs | Decision updates | Executed holds | Failed decisions | Candidate assessments |
| --- | ---: | ---: | ---: | ---: | ---: |
| Archived eight-second tasks | 24 | 1,800 | 1,800 | 0 | 3,153 |
| Generated method/edge-case matrix | 24 | 29 | 23 | 6 | 69 |
| Total | 48 | 1,829 | 1,823 | 6 | 3,222 |

The archived cohort retains its two initial positions, four update periods and
three controller methods: relaxed SACBF, high-order dual sign, and auxiliary
sign with comparison. Its configuration grid and ordering are checked from the
original metadata. Every retained scientific field reproduces under the current
implementation. This reproduces tick-trap's experiments, not the original
papers' nonlinear systems, optimizers or experimental setups.

The generated cohort exercises all twelve supported methods at a stationary
state, then adds explicit branches from the [configuration](../configs/decision-replay.json):

| Additional case | Reproduced outcome |
| --- | --- |
| Zero candidate allowance | `budget_exhausted`, no action |
| Infeasible HOCBF constraint/actuator intersection | `infeasible`, no action |
| Outside the high-order initial intersection | `outside_domain`, no action |
| Stopping construction cannot reach exact rest on its command lattice | `initialization_failed`, no action |
| Initially unsafe geometry | `initially_unsafe`, no decision or action |
| Exhausted finite endpoint search | `search_exhausted`, no action |
| Unresolved polynomial search | `uncertified`, no action |
| Valid comparison with a bounded offline oracle unknown | Two executed holds; certified horizon completes |
| Unknown execution without a comparison argument | One hold; `oracle_unresolved` |
| Endpoint-only collision witness | One hold; `collision_interval`, completion is unsafe |
| Stored stopping-plan prefix and rest policy | Five stored-continuation actions, then a terminal hold |
| Rejected candidate prefix | All checked candidates reproduce, including rejected ones |

These are deterministic coverage cases, not independent statistical trials or a
method ranking. Some start from restricted or unrecoverable states; they must
not be interpreted as comparable controller failures. Failed stopping-plan
construction leaves viability unknown, not proved impossible. Simulation
termination does not physically stop a robot or certify an emergency action.

The generated physical replay contains one unsafe interval and two offline
unknown intervals. One unknown has a valid online auxiliary comparison; the
other genuinely uncertified execution stops. A verified collision trace is
faithful evidence of a collision, not a safe controller result. None of these
labels is silently replaced by `safe` during decision replay.

## What is checked and what remains open

The checker first applies the existing physical/certificate verifier, then
regenerates the complete experiment using its recorded `PlanarConfig`. Strict
comparison covers configuration and nominal policy, all candidate evidence,
QP results, selected controls, initialization, retained plans, stopping
diagnostics, termination, intervention values, goal flags and exact aggregates.
Per-run scientific hashes are computed from that retained projection.

Only explicitly located clocks, deadline observations, floating state/action
duplicates and uncertified root/clearance estimates are excluded. Configuration
values, including deadlines and tolerances, remain checked. A timing-like field
inserted into controller evidence is not hidden by a recursive name filter.
Changing only excluded observations can leave the scientific replay valid;
timing accuracy, authenticity and hard deadlines are not verified here.

This is deterministic implementation-fidelity replay using the same runner,
controllers and certificate engine. A shared bug can reproduce. The separate
[independent minimum reference](validation-minimum-reference.md) addresses a
different numerical cross-check; it does not formally verify the entire runner.
Current-version schema or algorithm changes can legitimately prevent replay of
an older artifact without invalidating that artifact's original safety proof.

Still unverified: formal program correctness, physical model/observation/
actuation validity, uncertain or delayed execution, full planar viability,
global recursive guarantees for stateless filters, optimized external numerical
baselines and complete source-paper experiment reproductions. No new controller,
original algorithm or publication-level novelty is claimed.

## Reproduction

Use a clean committed checkout with Python 3.11+ and the versioned original
audit archive:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/reproduce-decision-replay.py --config configs/decision-replay.json --output results/decision-replay-reproduction
```

The driver checks the source archive/manifest, preserves its input run bytes,
generates the explicit case matrix, and invokes `verify-decisions` on both
cohorts. Each verification checks declared coverage and records exact input
hashes and both revisions. Scientific records should reproduce; clocks, floating
display estimates, timestamps, paths and source identity may differ in later runs.
