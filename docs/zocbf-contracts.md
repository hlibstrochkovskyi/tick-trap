# Zero-order buffers and state-input pairing

Source: [Tan, Daş, Ames and Burdick, arXiv:2411.17079v2](https://arxiv.org/html/2411.17079v2),
Definition 1/Eq. (4), Lemma 1/Eq. (5), Theorem 1 and Section IV-D/Eqs. (19)–(20).
The recurrence uses the previous input at the current state and the new input
at the predicted endpoint. The lemma connects an endpoint buffer with hold
safety. The numerical implementation additionally tightens by a valid bound
on the discrepancy in the predicted constraint value. These are published
constructions, not new algorithms introduced by this audit.

The implementation here evaluates those contracts on a restricted exact model.
It does not implement a state-input ZOCBF controller or the paper's rollover
model. Existing wall and planar ZOCBF controllers remain unchanged.

## Declared proxy and local bounds

Use `d_dot=-v, v_dot=u`, scalar bound `|u|<=a`, exact state, instantaneous input
changes at updates and constant input inside each hold. The deliberately simple
constraint proxy is

```
h(d,v,u) = d - tau*v - sigma*u,
tau>=0, sigma>=0.
```

This proxy need not imply geometric clearance or viability. Those properties
are measured separately. The initial left value is `h_left=h(x,u_previous)`;
the new right value is `h_right=h(x,u_new)`. Their jump is exactly
`-sigma*(u_new-u_previous)`. The actual held polynomial is

```
h(t) = h_right - (v+tau*u_new)*t - u_new*t²/2.
```

The terminal value uses the current held input, namely the left limit before
the next update. A future command jump is not part of this hold; it requires
its own next-step argument.

For gamma in (0,1], the Eq. (4) residual is
`h_end_new - (1-gamma)*h_left - delta`. Previous-pair safety and a nonnegative
residual imply `h_end_new>=delta`. If a proven bound satisfies
`h_end_new-h(t)<=delta` throughout the hold, the new right value and every later
held value are nonnegative, including immediately after the input jump.

Our enclosing tube satisfies `|v(t)|<=V=|v0|+a*T`, even outside the proxy's safe
set. In the same SI numerical coordinate norm as the existing comparator,
the norm-product bound is

```
delta_norm = sqrt(1+tau²)*sqrt(V²+a²)*T.
```

Both square roots use rational upper enclosures. At tau=sigma=0 this is exactly
the existing state-only wall buffer. The bound is local to this initial state,
input limit and hold, not a global constant on an unbounded safe set.

The audit also records four explicitly derived **offline references**:

```
delta_projected = (V+tau*a)*T
delta_candidate = max(abs(v+tau*u), abs(v+(tau+T)*u))*T
delta_absolute  = max(h_end-h_min, h_max-h_end)
delta_backward  = h_end-h_min.
```

The first two bound the magnitude of the held time derivative. The candidate
derivative is affine in time, so its largest absolute value is at an endpoint.
Exact quadratic extrema give the last two. Consequently

```
0 <= delta_backward <= delta_absolute <= delta_candidate
   <= delta_projected <= delta_norm.
```

The references prove the required one-sided backward-difference bound directly.
They are not all literal norm-product implementations of Eq. (5), constant
buffers across states/inputs, or complete published controller reproductions.
Some equal zero; this does not meet the paper's positive-constant definition but
can still prove a particular hold through a separate exact argument. The zero
`endpoint_only` diagnostic has no such a priori bound; the audit checks whether
it happens to bound the selected hold rather than assuming it does.

## Input-pairing diagnostics

Evaluating the endpoint with the *old* input can hide an actual unsafe jump.
For instance `d=10, v=0, u_previous=0, u_new=1, sigma=20, tau=0.3` has a safe
left value 10 and an unsafe new right value -10. An endpoint evaluated with the
old command omits the same command penalty. The audit records that value as a
diagnostic; it never uses it as a valid current-input endpoint certificate.

Replacing the start reference by `h_right` is also not Eq. (4). However it must
not automatically be called unsafe. With a valid backward-difference bound,

```
h_end >= (1-gamma)*h_right+delta
h_end-h_right <= delta
```

imply `gamma*h_right>=0`, hence `h_right>=0` and `h_end>=delta`. Thus the
reset-start relation can independently establish one-hold proxy safety, while
accepting or rejecting different controls from the published history relation.
The instrument keeps contract fidelity and an actual valid safety implication
separate instead of discarding this argument.

## Numerical endpoint error

For this affine proxy and double integrator, the Euler constraint prediction
differs from the exact endpoint by `u*T²/2`, while explicit midpoint is exact.
Therefore a defensible absolute discrepancy bound is

```
m_Euler(T,u)=abs(u)*T²/2,    m_midpoint=0.
```

The Eq. (20) residual uses `h_predicted-(1-gamma)*h_left-delta-m`. Passing this
condition implies the exact recurrence if the endpoint and input arguments are
correct and the error bound is valid. A numerical margin does not repair a
stale endpoint input that evaluates a different constraint. Unadjusted Euler
can occasionally be conservative already; its acceptance alone does not supply
the general discrepancy proof. Adding a validated prediction-error margin is
explicit prior art, not a new tick-trap safety algorithm.

## Scope

Quadratic extrema are exact rational calculations and independent algebraic
sign references check the actual held proxy. `one_hold_implication_ingredients`
requires a nonnegative endpoint target `(1-gamma)*h_start`, a valid backward bound,
a valid lower endpoint prediction and a passing condition. It concerns only
this proxy and hold, not geometric collision avoidance or future feasibility.
Left-pair-unsafe starts remain failures of the published safe-left recursion
premise. When gamma=1 the endpoint target is zero even for a negative left
value, so a valid local argument can still certify the new hold. This does not
certify the preceding interval or establish the full theorem. No global
ZOCBF existence, attraction theorem, uniform recursive feasibility, nonlinear
rollover dynamics or approximate-model confidence guarantee is established.
