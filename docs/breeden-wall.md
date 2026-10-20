# Breeden sampled-data conditions on the wall model

Source: [Breeden, Garg, Panagou, arXiv:2103.03677v1](https://arxiv.org/html/2103.03677v1),
Section III, Theorems 1–3, Eqs. (11), (13)–(14), (18)–(19). The statements and
associated arguments were checked against this version. Their local conditions
give sufficient hold safety, conditional on admissible inputs satisfying the
condition at subsequent updates. The implementation below specializes published
conditions; it does not reproduce their unicycle/spacecraft experiments or claim
that these constructions are original.

## Common model and sign convention

Use `d_dot=-v, v_dot=u`, `u in [-a,a]`, exact state, no disturbance or delay,
instantaneous bounded actuation and constant input throughout each period T.
Let `b=d-tau*v`, with tau>0. The paper uses the opposite sign, `H=-b<=0`, so
`L_f H=v`, `L_g H=tau`. The initial domain is `d>=0` and `b>=0`. Preserving b
then implies `d_dot>=-d/tau`, hence d>=0 by comparison. Contact is permitted.
This domain is different from the ideal stopping-distance viability kernel.

`breeden` retains the existing Theorem 1 specialization with `alpha(s)=k*s`:

```
nu1 = (1 + k*sqrt(1+tau²)) * T * sqrt((abs(v)+a*T)²+a²)
u <= (k*b-v-nu1)/tau.
```

The implementation uses rational upper enclosures for the square roots. These
are valid reachable-tube constants; the safe set itself is unbounded and no
global compact-set bound or global feasibility assumption is introduced.

## Reachable-error condition

`breeden_reachable` specializes Theorem 2. For a reached state z the error
functional in Eq. (13) reduces to

```
error(z) = (1+k*tau)*(v_z-v) - k*(d_z-d).
```

This expression is independent of the separately quantified test input because
`L_g H` is constant. For any measurable acceleration history w in [-a,a] and
elapsed time s:

```
v_z-v = integral_0^s w(r) dr
d_z-d = -v*s - integral_0^s (s-r)*w(r) dr
error(z) = k*v*s + integral_0^s (1+k*tau+k*(s-r))*w(r) dr.
```

The kernel is positive. Thus constant w=a maximizes this error at every s,
including the larger class of measurable admissible histories. Its time
polynomial is

```
q(s) = [k*v+a*(1+k*tau)]*s + k*a*s²/2.
```

Since q is convex, its supremum on the closed horizon is max(q(0),q(T)). The
half-open reachable-set definition in the paper has the same supremum by
continuity. Consequently the exact local margin and resulting input bound are

```
nu2 = max(0, [k*v+a*(1+k*tau)]*T + k*a*T²/2)
u <= (k*b-v-nu2)/tau.
```

The trace saves q's exact coefficients, supremum value and a constant-input
closure witness. This is an analytical reduction of the published reachable-set
optimization, not an approximate root search or a new sampling algorithm.
At the applied action, the initial inequality and `error<=nu2` imply
`b_dot(t)+k*b(t)>=0` throughout the hold. The integrating-factor argument
preserves b>=0. At equal k this exact reachable margin is bounded by the existing
Theorem 1 tube margin; rational square-root upper rounding preserves that order.

## Second-order condition

`breeden_second_order` specializes Theorem 3. Under a held input,
`H_dot=v+tau*u` and `H_ddot=u`, so the exact second-derivative upper bound is a.
For gamma in (0,1], the condition is

```
nu3 = a*T/2
u <= ((gamma/T)*b-v-nu3)/tau.
```

Its effective gain is **gamma/T**. The generic configured CBF gain is not used
by this method, and the effective value is recorded explicitly. Comparisons
must disclose this distinction; matching k=gamma/T in Theorems 1 and 2 removes
one confound. Holding k fixed across rates is a different comparison.

Directly, with b0>=0 and 0<=s<=T:

```
b(s) = b0 - (v+tau*u)*s - u*s²/2
     >= (1-gamma*s/T)*b0 + (a/2)*s*(T-s) >= 0.
```

The first inequality uses the input condition and u<=a. This proves the restricted
one-hold implication independently of a simulation grid. The symbol used for a
second derivative in this paper is not the planar high-order auxiliary barrier
psi used elsewhere in tick-trap.

## Projection, feasibility and tests

Each condition defines an upper bound on u. Intersect it with [-a,a] and project
the clipped nominal action exactly onto that interval. An upper bound below -a
is explicitly `infeasible`, not a collision or proof of nonviability. An initial
domain violation is `outside_domain`. No fallback is generated. Repeated safety
still requires a feasible decision at every update; the paper's additional
uniform-feasibility hypothesis is not established on this unbounded wall domain.

Tests evaluate the reachable-error functional at independently propagated states,
exercise piecewise admissible histories, verify the closure witness and zero
margin case, check ordering against Theorem 1, and check accepted geometric and
barrier polynomials using the independent exact algebraic sign reference. They
also cover effective gains, exact projection, initial exclusions and infeasibility.
These support implementation correctness; they are not a formal proof of the
program or validation of a physical model.

The [validation ledger](validation-breeden.md) reports matched controls, explicit
gain policies, exact saved-record regeneration and the remaining research gates.
