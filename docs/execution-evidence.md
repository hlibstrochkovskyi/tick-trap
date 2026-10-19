# Oracle uncertainty and execution evidence

For exact rational planar double-integrator dynamics with constant acceleration
through each declared hold, static circular obstacles, exact observations,
instantaneous bounded commands on the declared lattice, and contact allowed,
the offline geometric oracle and the controller's online certificate are two
different sources of evidence. Neither validates these physical assumptions.

The runner previously ended every hold with geometric oracle status `unknown`.
That was conservative but conflated a budget-limited numerical minimum enclosure
with absence of a safety argument. In particular, an existing valid proof of
`psi = h' + lambda1 h >= 0`, together with `h(0)>=0` and `lambda1>0`, already
implies `h(t)>=exp(-lambda1*t)h(0)>=0` throughout that same hold.

The runner now records:

| Field | Meaning |
| --- | --- |
| `continuous_status` / `observed_continuous_status` | Unmodified offline geometric oracle answer per hold / run |
| `online_proof_source` | Recognized online evidence validated against actual state, action, obstacles, duration and numerical settings, or null |
| `execution_status` / `certified_execution_status` | Safety supported by the offline oracle or the validated existing online proof, per hold / run |
| `execution_basis` | Offline geometric bound, specific online proof, negative witness, or unresolved |
| `oracle_confirmed_horizon` | Full horizon with every offline geometric oracle answer safe |
| `completed_safe_horizon` | Full horizon with every executed hold certified by either recognized source |

Recognized online evidence in this audit comprises the auxiliary-only comparison,
dual h/psi minimum or sign certificates, and the existing native SACBF sufficient
condition (including its initial domain and exact Taylor bound). No predicate,
gain, tolerance, candidate ordering, work budget or published assumption changes.
Other controllers retain the existing conservative oracle-based stopping policy;
this is not a general verifier for every possible controller proof.

The evidence replay checks the selected actual action, exact polynomial,
subdivision count within the configured online budget, goal, rational bounds,
witness, flags, initial h, positive gain, duration, and the declared comparison
implication. SACBF conditions are rebuilt exactly using the declared relaxation.
Names, guarantee text and a bare `accepted` flag provide no proof authority.
Malformed recognized evidence raises an error even if the offline oracle is safe.
An offline negative witness always stops execution; a simultaneous purported
valid online proof raises an explicit contradiction error. Without either valid
source an `unknown` ends execution. No fallback action is manufactured.

Proof replay is **offline audit instrumentation** and has its own
`offline_proof_replay_ns`. The online evidence was already generated within
`solve_ns`. Offline replay and geometric oracle cost are excluded from the
controller's empirical deadline comparison, as before. Deploying either audit
in an actual online implementation would require including its execution cost.
Recorded runtime is not a bound on real-time computation or simulated delay.

Regression: `p=(-0.3,1.06), v=(1,0), u=(0,0), R=1, T=1, lambda1=3` yields
`h=.2136-.6t+t²` and `psi=.0408+.2t+3t²`. With zero subdivisions the geometric
Bernstein lower bound is negative but its witness is positive (`unknown`), while
psi has a nonnegative Bernstein bound (`safe`). The runner can complete two
such holds using the existing auxiliary comparison, retaining the first raw
unknown. With the nominal controller and the same command it stops after the
first hold because that controller supplies no recognized proof. The offline
algebraic reference is not used to authorize either run.

Historical records lacking the new fields retain the old oracle-only meaning
when replayed. Verification rejects continuation after a genuinely uncertified
hold and checks both new aggregate statuses without rewriting old artifacts.
