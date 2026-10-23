# Polynomial representation and tolerance contracts

This audit changes the representation of an existing exact polynomial, not the
robot trajectory or controller. Positive barrier scaling and time substitution
are established numerical constructions; no original algorithm is claimed.

For positive a and physical duration T, use either `q(t)=a*p(t)` on `[0,T]` or
`q(s)=a*p(T*s)` on `[0,1]`. In coefficient form the latter has
`q_i=a*p_i*T^i`. Consequently

```
min(q) = a*min(p),
p(t)>=0 throughout the hold iff q(s)>=0 throughout its represented interval.
```

Convert returned value bounds by dividing by a. Convert a unit-interval witness
to physical time by multiplying by T. No sample period, deadline, actuation
assumption or physical horizon changes. This is not a claim that replacing T
by one while retaining the original coefficients is valid.

## Absolute width is representation dependent

At represented-value absolute tolerance eps, the equivalent width request in
the original polynomial values is eps/a. Holding the number eps fixed while
changing a therefore changes the numerical question. This can stop refinement
before a sign is proved even with exact rational arithmetic and unchanged safety.
It is not evidence of floating-point rounding or a controller safety violation.

For example, `p(t)=(t-3/10)^2-10^-8` on `[0,1]` has a negative minimum. With
64 splits and tolerance 1e-12, both current Bernstein modes prove it unsafe.
For `q=10^-6*p`, the same numerical tolerance gives an unknown sign after width
attainment. Using represented tolerance 1e-18 restores the original request and
the original result. Unknown is not relabelled safe in either representation.

## Equivalent tolerance and exact covariance

Use `eps_q=a*eps_p` to retain the same original-value width request. For the
current exact rational implementations, this also preserves the numerical
proof path and work counts after the above coordinate conversion:

- Bernstein conversion is linear in p; time normalization forms the same
  coefficients directly. De Casteljau subdivision is linear, so all lower/upper
  values scale by a. Positive scaling preserves heap order, comparisons, witness
  ties and signs. The width test is identical when the tolerance scales too.
- The stationary reference's derivative roots map bijectively under positive
  time substitution; square-free normalization does not change their locations.
  Root-count and midpoint branches correspond. Interval Horner ranges also
  scale by a: at Horner level i the transformed intermediate interval is the
  original interval multiplied by the positive factor a*T^i. Thus its lower-bound
  order, upper witnesses and width comparisons correspond as well.

The audit checks converted bounds, upper-witness time, status, precision and
budget flags, stopping reason, split count and stationary root-count work.
It retains final stationary boxes and exact points but does not duplicate every
intermediate Sturm chain in the sweep; the exact inputs and source allow those
chains to be regenerated. The separate minimum-reference archive retains its
full counting proofs.

These arguments concern the current algorithms and exact rational semantics.
They do not assert equal runtime, intermediate rational bit complexity, or
invariance of arbitrary floating implementations. Input numerator/denominator
bit lengths are descriptors, not a bound on intermediate work or execution time.

## Auxiliary constraints and normalized time

The archived psi polynomial is composed with physical time just like h. It is
not silently rebuilt with a derivative taken in the wrong clock. If
`H(s)=h(T*s)` and `psi(t)=h_dot(t)+lambda*h(t)`, then

```
psi(T*s) = H'(s)/T + lambda*H(s),
H'(s) + (T*lambda)*H(s) = T*psi(T*s).
```

Keeping lambda unchanged in `H'+lambda*H` generally defines another constraint.
The polynomial substitution in this audit retains the existing property. Value
widths on h and psi still refer to different quantities and are not a common
physical clearance error. Geometric safety, auxiliary preservation, viability
and recursive feasibility remain separate.

The experiment is offline. It changes no certifier default, controller,
comparison argument, stored unknown or fallback action. An equivalent-tolerance
comparison is not a new safety controller or a claim of publication novelty.
