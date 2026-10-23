# Planar control and the properties being compared

The plant is `p_dot=v`, `v_dot=u`, with componentwise actuator bounds
`|u_x|,|u_y|<=a`. Each static circle's radius includes the robot's collision
radius. The geometric barrier is `h=||p-c||²-R²`. Nonnegative values permit
boundary contact. These controllers assume exact state, model and held execution;
uncertainty, moving obstacles and execution delay are not covered here.

## Emulated HOCBF baseline

The recursive high-order construction is established in
[Xiao and Belta, 1903.04706v1, Section III](https://arxiv.org/html/1903.04706v1).
We specialize it with positive linear gains `lambda1,lambda2`:

```
r = p-c
h_dot = 2*r·v
psi1 = h_dot + lambda1*h
psi2 = 2*v·v + 2*r·u + (lambda1+lambda2)*h_dot + lambda1*lambda2*h
```

The initial set requires `h>=0` and `psi1>=0` for every obstacle. At an update,
we project nominal acceleration onto all `psi2>=0` constraints and the actuator
box. Enforcing only the sampled inequality does not establish the
continuous-feedback theorem's hypothesis over a hold. The trajectory oracle
independently checks what the applied action actually does.

The two-input reference QP enumerates the nominal point, projections onto single
boundaries, and intersections of two boundaries. Compactness of the actuator box
and strict convexity of the objective justify this enumeration, including line
or point feasible sets. All arithmetic and constraint residuals are rational.

Physical commands use a declared rational quantum. Four lattice neighbours of
the exact continuous solution are checked against the original constraints and
actuator bounds. The closest feasible neighbour is used, if one exists. Otherwise
the result is `command_unresolved`, rather than a claim that the continuous QP is
infeasible. The continuous optimum and applied-command cost are both recorded.
This local rounding search is not an exact mixed-integer QP solver.

## Shared finite-candidate comparisons

Candidate methods use exactly the same input set at a given state and nominal:
a quantized Cartesian actuator grid, clipped/quantized nominal, zero input, and
a clipped/quantized one-period velocity-cancelling input. The last two are merely
candidates: neither is assumed safe. Duplicate commands are removed. Candidates
are ordered by exact squared distance from the raw nominal, with a deterministic
lexicographic tie-break. The first accepted action is the closest among the
declared candidates; no continuous-input optimality is claimed.

| Method | Acceptance property for every obstacle |
| --- | --- |
| `endpoint_candidates` | `h(T)>=(1-gamma)*h(0)` |
| `segment_candidates` | Nonnegative minimum on the chord from `p(0)` to `p(T)` |
| `zocbf_candidates` | Endpoint difference plus the local buffer below |
| `sacbf_candidates` | Sampling-aware high-order condition with an exponential endpoint target |
| `sacbf_relaxed_candidates` | Sampling-aware high-order condition with the permitted zero target |
| `high_order_trajectory_candidates` | Validated minima of both actual h and auxiliary psi paths |
| `high_order_sign_candidates` | The same two path properties, stopping on proved signs |
| `auxiliary_sign_candidates` | Validated psi sign and a comparison proof of geometric safety |
| `trajectory_candidates` | Validated nonnegative minimum on the actual curved trajectory |
| `backup_candidates` | Safe hold plus certified stopping continuation, or execution of a previously certified plan |

Segment checking is an exact geometric diagnostic, not a reproduction of the
Segment-Safe MPC paper. A safe chord can coexist with a colliding physical path.
The [chord contract](segment-contracts.md) derives the exact held-acceleration
deviation and a sufficient inflated-chord implication, with independent signed
trajectory cases. This offline diagnostic does not alter `segment_candidates`
or the termination logic; failed implications remain unknown.
The endpoint method is likewise a diagnostic, not Taylor et al.'s full method.

For `trajectory_candidates`, a negative witness for any obstacle rejects the
action. If there is no such witness but at least one unresolved obstacle, the
action remains unknown. Only a safe certificate for every obstacle permits it.

An exhausted finite search returns `search_exhausted`; it does not prove there
is no admissible real-valued input. If potentially safe candidates have unresolved
certificates it returns `uncertified`. Both stop execution without substituting
an action. Only the exact linear QP can return proven `infeasible` for its own
constraint set.

## Planar zero-order buffer

The sampled difference and buffer construction come from
[Tan et al., 2411.17079v2, Eq. (4) and Lemma 1](https://arxiv.org/html/2411.17079v2).
For this specialization, a local tube enclosing all bounded held inputs has:

```
A = sqrt(2)*a
V = ||v0|| + A*T
rho = ||p0-c|| + ||v0||*T + A*T²/2
||h_x|| <= 2*rho
||f+g*u|| <= sqrt(V²+A²)
delta = 2*rho*sqrt(V²+A²)*T
```

Rational upper square-root enclosures keep the buffer conservative. The tube
bounds hold even on potentially unsafe portions, so the integral difference
argument is not conditional on already knowing path safety. With `0<gamma<=1`,
the test `h(T)>=(1-gamma)*h(0)+delta` implies safety on this hold. It may reject many
safe candidate actions. We do not assert global ZOCBF existence or recursive
feasibility with bounded actuation.

## Viability remains a separate property

Passing a trajectory check proves the current hold safe. It does not establish
that another safe input can be found at the next update. The wall's exact
viability formula is not applied to planar robots. Planar viability is recorded
as unknown unless a separate sufficient continuation certificate is supplied.
There is no guarantee of task convergence from the safety filter alone.

The runner now checks a particular stopping continuation: brake each component
at its actuator bound, use a residual command at an update boundary, then hold
zero after rest. At most five constant-input pieces are required. Each piece is
certified against every obstacle. The plan respects the same update period,
actuator box and command quantum as the controller. If exact rest is unreachable
on that lattice, or any part cannot be certified, viability remains unknown.
These diagnostics do not silently become fallback actions when a filter fails.
The separate [stateful continuation reference](continuations.md) does maintain an
online certified plan and explicitly reports each action taken from it.

## Sampling-aware high-order conditions

The [SACBF specialization and local proof](sampling-aware.md) implement Liu et al.'s
unrelaxed condition and its relaxed feasibility envelope. Both require the same
`h>=0, psi1>=0` initial domain as the linear-gain HOCBF. Exact candidate-specific
second-derivative bounds protect the actual held path. The zero-target variant
uses the greatest allowed feasibility relaxation, rather than duplicating the
paper's QP preference for a multiplier near one. Both use the shared finite
candidate set and report exhaustion explicitly. Neither retains a future plan.

`configs/sampling-baselines.json` compares them with HOCBF, the local zero-order
buffer, trajectory checks and stored continuations over matched eight-second
tasks. This does not reproduce the original papers' complete experiment setups.

## High-order polynomial references

The two high-order references check both `h(t)` and
`psi(t)=h_dot(t)+lambda1*h(t)` against every obstacle over the entire hold.
They share the SACBF initial domain and the same ordered finite command set.
They accept only when both certificates are safe. A negative witness for either
property rejects the action; unresolved evidence cannot authorize it. This
removes the Taylor sufficient-condition restriction while preserving the two
trajectory properties promised by the relaxed SACBF specialization. It does not
add reach-and-remain constraints, a future feasible input, or a terminal plan.

`high_order_trajectory_candidates` requests minimum-enclosure precision;
`high_order_sign_candidates` uses the [sign stopping goal](certificate-goals.md).
With the same tolerance and subdivision budget, both traverse the same proof
prefix and classify each candidate identically. Once a sign is proved, further
refinement cannot reverse it. Thus their deterministic selected commands are
the same, while their numerical work and minimum widths can differ. This is a
comparison of computation, not a different safety guarantee.

`configs/high-order-baselines.json` compares these references with relaxed SACBF
on matched eight-second tasks. The saved-run verifier replays their geometric
and auxiliary proofs, declared query goals and stopping flags. A sign-proved
interval must not be mistaken for a precision-qualified minimum enclosure.

`auxiliary_sign_candidates` retains the same initial domain and ordered commands
but queries only `psi`. The [linear comparison proof](auxiliary-certification.md)
derives geometric nonnegativity from `h(0)>=0`. Saved inference records are
distinct from numerical geometric certificates and carry no minimum bounds.
The offline geometric oracle is still run, and saved-run verification reconstructs
the polynomial, gain, initial value, interval and auxiliary proof. A failed or
unknown auxiliary condition authorizes no action. At finite work limits its
classification can differ from the dual query in either direction; the required
safety guarantee has not changed. The matched rollout configuration is
`configs/auxiliary-baselines.json`.

## Matched-control audit

`planar-audit` evaluates every declared candidate at exactly the same initial
state. It records safe controls admitted, unsafe controls admitted, safe controls
excluded, and accepted controls whose continuous status is unknown. HOCBF
initial-set exclusions are marked not applicable rather than counted as rejected
controls. SACBF has the same domain and uses the same exclusion rule. A finite
audit is evidence about those controls, not the volume of the
continuous feasible set. It does not establish that the standard constructions
used here are the strongest versions of their respective papers.

Audit timing fields separate per-control predicate work from shared endpoint and
buffer construction. The zero-order margin uses the endpoint computation already
recorded for the endpoint predicate. These components must be combined before
comparing complete evaluation expense; per-predicate timings alone are not an
end-to-end runtime ranking. Controller rollouts measure the complete filter call.

The audit's geometric table uses actual `h(t)` safety. SACBF also preserves
`psi(t)=h_dot(t)+lambda1*h(t)`, so a second table uses separate validated
certificates for that auxiliary polynomial. It distinguishes rejected paths with
safe `h` and safe `psi` from safe geometric paths that leave the auxiliary set,
or whose auxiliary sign remains unresolved. Only the first category measures
exclusion relative to the same two required trajectory properties. The
zero-order buffer and trajectory filter do not promise auxiliary-set preservation.
