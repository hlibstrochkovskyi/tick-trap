# Implemented methods and their scope

All wall methods use `d_dot=-v`, `v_dot=u`, `|u|<=a`. Clearance is in metres,
velocity in metres/second, and acceleration in metres/second². Nonnegative
clearance permits boundary contact. Strict contact avoidance needs a positive
clearance offset. Configurations use SI numerical coordinates, including in norms.

Each filter minimizes squared deviation from the nominal acceleration by exact
scalar projection. There is no iterative QP solver in this first version. The
returned linear-constraint residual is independently recomputed; positive means
violation. This removes solver tolerance as a confound in the initial experiments.

| Identifier | Implemented condition | Interpretation |
| --- | --- | --- |
| `nominal` | Clip to actuator bounds | No safety claim |
| `continuous_cbf` | `-v-tau*u+k*(d-tau*v)>=0` at updates | Emulated continuous feedback; no hold guarantee |
| `endpoint` | `d(T)>=(1-gamma)*d(0)` | Sampled endpoint constraint only |
| `breeden` | Continuous CBF condition tightened by a reachable-tube margin | Published sampled-data sufficient condition, specialized here |
| `breeden_reachable` | Exact reachable-error margin for the wall barrier | Breeden v1 Theorem 2 specialization |
| `breeden_second_order` | Second-derivative upper bound; effective gain gamma/T | Breeden v1 Theorem 3 specialization |
| `zocbf` | `d(T)>=(1-gamma)*d(0)+delta` | Published zero-order condition with a local flow bound |
| `exact_hold` | `min d(t)>=0` and viable terminal state | Restricted-system reference, not a novel controller |

## Continuous CBF and initial sets

Let `b=d-tau*v`, with `tau>0`. Then `b_dot=-v-tau*u`; enforce
`b_dot+k*b>=0`. The continuous-feedback comparison argument preserves `b>=0`.
Together with `d(0)>=0`, `b>=0` implies `d_dot>=-d/tau` and hence `d>=0`.
These initial-set requirements are stronger than geometric safety and differ
from the exact viability kernel. Invalid initial sets produce `outside_domain`;
an empty control constraint intersection produces `infeasible`. These statuses
do not mean the same thing.

## Breeden condition

[Breeden, Garg, Panagou (2021), v1, Theorem 1, Eq. (11)](https://arxiv.org/html/2103.03677v1)
provides a local Lipschitz sampled-data margin. In their sign convention use
`h=-b`, and `alpha(s)=k*s`. The relevant Lipschitz constants are `1`, `0`, and
`k*sqrt(1+tau²)`. A tube enclosing all held inputs has
`|v(t)|<=V=|v0|+a*T`; thus a flow-norm upper bound is `Delta=sqrt(V²+a²)`.
We use `margin=(1+k*sqrt(1+tau²))*T*Delta`, with rational square-root upper
enclosures. The state and input model must match; the inequalities must remain
feasible at each update. This implements their sufficient condition on a simple
system, not their controller's published experiments or their least conservative
variant.

Two additional published conditions are now specialized on the same wall model.
The [derivation and assumptions](breeden-wall.md) give the exact reachable-error
supremum and second-order bound, including the latter's distinct effective gain
gamma/T. The original `breeden` implementation remains unchanged.

## Zero-order condition

[Tan, Daş, Ames, Burdick, 2411.17079v2 (April 2025), Eq. (4) and Lemma 1](https://arxiv.org/html/2411.17079v2)
use a sampled barrier difference with an inter-sample buffer. We set `h=d` and
`gamma(s)=gamma*s`, `0<gamma<=1`. Here `||h_x||=1` and
`delta=T*sqrt(V²+a²)`. Our local reachable tube bounds the flow even outside
the safe set. Consequently `|d(T)-d(t)|<=delta` throughout this interval, so
`d(T)>=delta` proves hold safety. This is a local specialization with a direct
one-interval argument; we do not assert global ZOCBF existence for unbounded
velocity and bounded acceleration. Repeated safety is conditional on subsequent
feasibility. The flow-norm bound can be substantially conservative.

## Exact wall reference

For approaching velocity, braking distance is `v²/(2*a)`; for departing motion
it is zero. The ideal viability margin is `d-max(v,0)²/(2*a)`. The reference
checks the quadratic trajectory at endpoints and its interior vertex. Terminal
viability prevents a safe interval from ending in an unrecoverable state.

Both hold clearance and terminal viability are nonincreasing functions of held
acceleration. Maximum braking is feasible from every viable initial state.
We bracket the closest admissible action with 64 exact bisections and return the
feasible side. The remaining action error is recorded. This reference exploits
the wall model's special structure; its viability formula is not used for planar
obstacles, delays, measurement uncertainty, or uncertain dynamics.

## Trajectory certification

A planar quadratic position produces a quartic squared-distance barrier. The
numerical estimator recursively isolates real derivative roots and evaluates
candidate critical points. Its answer is labelled an estimate.

The independent certificate converts the exact rational polynomial on `[0,T]`
to Bernstein coefficients. Their convex hull gives a lower bound. Exact
de Casteljau subdivision refines the minimum enclosure; an evaluated trajectory
point gives the upper bound. Pruning intervals whose lower bound exceeds an
existing witness preserves the global minimum enclosure.

`safe` requires a nonnegative lower bound; `unsafe` requires a negative upper
witness; otherwise the result is `unknown`. Precision is an absolute barrier
width in m², not a clearance threshold, and cannot turn a negative lower bound
into a safety claim. Non-dyadic tangencies can remain unknown. Resource limits
bound subdivisions, not wall-clock execution or integer bit complexity.

Decimal strings are interpreted as exact decimal rationals. Python floats are
interpreted as their exact binary values. Arithmetic certificates cover these
values and the ideal dynamics, not an uncertainty neighbourhood of physical
measurements. Float fields in reports are for display; rational fields carry the
certificate and exact executed wall state.

An additional [offline algebraic sign reference](algebraic-reference.md) uses
square-free decomposition and Sturm counting for rational degree <=4 inputs.
It is independent of the Bernstein implementation and resolves repeated roots
and exact tangencies without a floating epsilon. It supplies signs, not minimum
enclosures, and never replaces an online unknown automatically.

The [execution evidence audit](execution-evidence.md) distinguishes unresolved
offline geometry from recognized, replay-validated online comparison proofs.
Raw oracle statuses and bounds are retained even when another valid argument
proves the executed hold safe. The [current validation ledger](validation-audit.md)
separates mathematical arguments, finite experimental observations and remaining
verification limits.
