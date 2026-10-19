# Sampling-aware high-order comparator

Source: [Liu, Xiao and Belta, 2511.11897v1, Section IV](https://arxiv.org/html/2511.11897v1).
Equation (15) strengthens the held-input derivative inequality using a second
derivative bound and a comparison-function endpoint target. Equation (22) permits
a nonnegative multiplier on that target; Section IV-B penalizes departure from
one. Theorem 2 assumes the initial high-order set, a valid bound throughout each
hold, and repeated feasible enforcement. It does not prove that every future
optimization problem is feasible. The paper's bound estimation, time-varying
reach-and-remain constraints, QP slack objective and unicycle experiments are not
reproduced here.

## Exact specialization used in tick-trap

For the exact planar model and static circular obstacle, let `r=p-c`,
`h=r·r-R²`, and `psi=h_dot+lambda1*h`, with positive linear gains. Within a
constant-acceleration hold, direct differentiation gives

```
h_dot   = 2*r·v
h_ddot  = 2*v·v + 2*r·u
h_dddot = 6*v·u
psi_ddot = 6*v·u + 2*lambda1*(v·v+r·u)
```

Substituting `r(t)=r0+v0*t+u*t²/2` and `v(t)=v0+u*t` makes `psi_ddot` a quadratic.
Its maximum absolute value `M` over `[0,T]` is attained at an endpoint or its
interior vertex. Those rational evaluations give an exact bound **for the chosen
candidate**, including portions of its path that may be unsafe. There is no
assumption that safety was already established when bounding the remainder.

This replaces the paper's norm/tube and quadrature recipe with a restricted
analytical calculation of the quantity its condition requires. The calculation
is candidate dependent: it cannot be inserted as a constant into a continuous
input QP. Each candidate has its own bound. A zero bound is allowed when the
second derivative is identically zero.

The unrelaxed test is

```
h(0)>=0, psi(0)>=0
psi(0) + T*psi_dot(0) - M*T²/2 >= E*psi(0)
E >= exp(-lambda2*T)
```

`E` is an exact rational upper enclosure with absolute error at most `1e-18`.
The reciprocal of a positive exponential Taylor sum is an upper enclosure;
a geometric bound on its remaining tail supplies the stopping criterion.
For large arguments, `exp(1)>2` supplies a small conservative enclosure. No
floating-point exponential decides acceptance.

The relaxed test uses target zero. Since `psi(0)>=0`, this is precisely the
feasibility envelope over nonnegative slack multipliers for a fixed candidate:
if the zero target fails, a positive target cannot pass. This is not the
slack-penalized QP's preferred action or multiplier. Its nominal-control objective
will be the same finite candidate ordering used by the other tick-trap filters.

## Local proof and limits

Taylor's theorem gives `psi(t)>=q(t)=psi(0)+t*psi_dot(0)-M*t²/2`.
The polynomial `q` is concave, so its minimum on this interval is at an endpoint.
Both endpoints are nonnegative under either test. Thus `psi(t)>=0` throughout
the hold. Integrating `h_dot+lambda1*h=psi>=0` from `h(0)>=0` gives `h(t)>=0`.
This also preserves the auxiliary initial-set condition at the next update.

The proof covers exact rational initial data and commands, the declared
double-integrator model, static inflated circles, exact observations and the
declared held execution. Commands must respect the actuator box and quantum in
the calling controller. State uncertainty, plant error, moving obstacles and
delays are outside this guarantee. Safe-set boundary contact is permitted.
An exhausted candidate search stops explicitly; it proves neither continuous
input infeasibility nor a globally nonviable state. Repeated safe operation still
requires an admissible next input or a separately certified retained plan.

Tests compare the derivative polynomial with an independently differentiated
vector expression, check quadratic endpoint/vertex extrema and high-precision
exponential values, and validate both `h` and `psi` on accepted test trajectories
using the separate Bernstein polynomial certifier.
