# Approximate maps and practical-safety contracts

Source: [Taylor et al., arXiv:2203.11470v2](https://arxiv.org/html/2203.11470v2),
Definitions 3–8, Theorem 3 and its three-case proof; Theorems 4–5 examined for
input dependence and synthesis scope. Theorem 3 connects a consistent approximate
controller-map family and uniform sampled-data barrier hypotheses to practical
invariance at sample times. It does not assert exact inter-sample invariance.
The radius quantifier is: for each positive R, sufficiently small sample periods
admit an invariant enlarged set inside the R-neighborhood. A finite trajectory
inside a chosen enlargement does not establish that family-level statement.

The compact regular-value result in Theorem 2 is a sufficient route to a uniform
outside-set condition; its compactness premise is not silently assigned to an
unbounded wall halfspace. A general barrier-decrement check at one state is not
the full theorem's hypothesis. The implementation here is an offline contract
audit, not the paper's optimization controller or its pendulum experiments.

## Exact restricted-model calculations

Use `d_dot=-v, v_dot=u`, `|u|<=a`, exact state and constant held input on [0,T].
For the wall barrier `b=d-tau*v`, with positive tau, compare:

```
Exact:    (d-v*T-u*T²/2, v+u*T)
Euler:    (d-v*T,        v+u*T)
Midpoint: (d-v*T-u*T²/2, v+u*T).
```

Midpoint is implemented from its explicit stage, not by calling the exact map.
For this affine model it agrees with that map. Euler's position discrepancy is
`-u*T²/2`; its velocity discrepancy is zero. For |u|<=a, the Euclidean state error
in normalized coordinates `(d/L,v/V)` is at most `a*T²/(2*L)`. Thus
`rho(T)=a*T/(2*L)` supplies a class-K-infinity consistency bound `T*rho(T)`.
For exact midpoint error, the tight error bound is zero, but the zero function
is not class K infinity. The audit records the conservative witness `rho(T)=T`.
These are analytical uniform bounds in this restricted model, not fitted rates.

The approximate position's coefficient on u is zero for Euler and `-T²/2` for
midpoint. Its barrier coefficient is `-tau*T` or `-tau*T-T²/2`, respectively.
This makes explicit why an Euler check of position alone cannot change the
chosen acceleration, while a velocity-dependent barrier already sees it.
No general nonlinear or convexity assertion follows from this special case.

## A pointwise decrement is only one ingredient

For a fixed comparison gain k, the recorded decrement residual is

```
b(F_approx(x,u)) - (1-k*T)*b(x).
```

The audit separately records its sign, b(x)>=0, and k*T<=1. They describe this
particular state/input/period. For a fixed family `s_T=b`, one fixed alpha(s)=k*s
works for the candidate decrement-size condition on `0<T<1/k`; a rate-dependent
gain does not by itself provide the uniform alpha required by the definition.
No family-level certificate is returned even when all pointwise flags are true.

In particular, bounded controls cannot enforce this decrement globally on the
unbounded wall halfspace: at b=0, sufficiently large approaching velocity
exceeds the available braking term. The required controller family and uniform
decrement over its declared domain must be established separately. There is no
uncertified fallback, new controller synthesis, or inferred infinite-horizon
invariance in this audit.

## Enlargement means distance to a declared set

The target here is **C_b={d-tau*v>=0}**, not its intersection with geometric
clearance, a viability kernel, or a planar high-order set. Geometric safety is
recorded separately. Define positive position and velocity scales L,V, and use
Euclidean distance in `(d/L,v/V)`. A radius R is dimensionless in that metric;
changing state scaling changes the enlargement even for the same physical path.

The halfspace normal is `(L,-tau*V)` and its squared norm is
`N²=L²+(tau*V)²`. Exact projection gives

```
distance_squared(x,C_b) = max(-b(x),0)²/N².
```

For negative b, the closest physical state is
`(d-b*L²/N², v+b*tau*V²/N²)`. It lies on b=0 and its normalized squared displacement
matches the distance above. No floating root or epsilon decides membership.

The actual b trajectory is the quadratic
`b(t)=b0-(v+tau*u)t-u*t²/2`. Its exact minimum b_min occurs at an endpoint or
the interior vertex. Therefore its largest squared distance from C_b is
`max(-b_min,0)²/N²`, and containment of the **observed hold** in the R-dilation
is exactly the rational comparison of this quantity with R².

Original geometric/barrier path statuses remain safe or unsafe according to
their exact nonnegative constraints, irrespective of any enlargement. The field
`path_within_dilation` never replaces them or authorizes an action. Independent
square-free/Sturm signs cross-check both quadratic path minima.

## What remains unverified

This instrument verifies restricted one-hold arithmetic and observations. It
does not construct a Taylor SD-BF controller family, a forward-invariant C_T,
the theorem's small-period threshold for such a family, or a continuous-time
physical-safety guarantee. Full original-system replication, admissibility and
uniform-family proofs, nonlinear approximation bounds and actuation uncertainty
remain separate research gates. Exact endpoint prediction alone is insufficient
to settle those questions, even when endpoint checks are satisfied.

The [validation ledger](validation-approximation.md) gives the source revision,
complete evidence, exact examples and remaining theorem gates. Radius zero is
included as an exact-set diagnostic, not as the paper's positive-radius theorem.
