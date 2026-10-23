# Connecting segments and held-acceleration paths

This is an offline geometric reference, not a new controller or an implementation
of a published SSCBF. It strengthens the interpretation of the existing
`segment_candidates` diagnostic. Controller choices, initial-domain checks,
execution rules and existing certificates are unchanged.

## Model and assumptions

The plant is the exact planar double integrator
`p_dot = v, v_dot = u`, with a prescribed acceleration held over `[0,T]`, `T>0`.
The provided exact initial state and static circle centers/radii are known without
observation error. Circle radii include robot size; the permitted boundary is
`||p-c||²-R² >= 0`. This is a free-motion prediction, not a contact model.
Each prescribed command is checked against the recorded componentwise actuator
box. There is no delay, disturbance, prediction error or actuator mismatch.

The result concerns only this one hold from its specified initial state. It does
not prove viability, recursive feasibility, a high-order filter's initial-domain
membership, or safety after the hold. The diagnostic also permits initially
unsafe examples to expose invalid algebraic implications; those cannot receive
a successful tube certificate. Exact rational arithmetic avoids floating point
rounding in this test. The separate square-free/Sturm reference has independent
polynomial logic, but neither implementation has a formal program proof.

## Exact interpolation identity

Let `p_T = p_0 + v_0*T + u*T²/2` and parameterize the connecting chord by

```
L(t) = p_0 + (t/T)*(p_T-p_0).
p(t) - L(t) = (u/2)*t*(t-T).
```

For `t in [0,T]`, `t*(T-t) <= T²/4`, with equality at `t=T/2`.
Consequently the maximum Euclidean deviation from the same-time chord point is

```
rho = ||u||*T²/8,
rho² = (u dot u)*T⁴/64.
```

This identity is independent of initial position and velocity. Zero acceleration
makes the chord and path identical; coincident endpoints alone do not.

## A sufficient implication, with exact arithmetic

For a circle of radius `R>0`, let `D` be the minimum distance from its center to
the chord. The existing exact rational closest-point calculation returns
`m = D²-R²`. The triangle inequality gives

```
||p(t)-c|| >= ||L(t)-c|| - ||p(t)-L(t)|| >= D-rho.
```

Thus `D >= R+rho` is sufficient for nonnegative geometric safety throughout the
hold. This is elementary tube geometry; it does not require or reproduce an MPC
feasibility theorem. The tube can include points the trajectory never visits,
so the condition is not necessary for trajectory safety.

No square root enclosure is needed to evaluate this particular implication.
Set `A = m-rho²`. Since `R,rho >= 0`,

```
D >= R+rho  iff  A >= 0 and A² >= 4*R²*rho².
```

The `A >= 0` guard must be checked before squaring. The cross term
`2*R*rho` must also be retained: adding only `rho²` to the squared collision
radius is insufficient. Equality is accepted under the declared boundary rule.

A failed implication is **unknown**, even if the chord intersects the obstacle
or an independent trajectory query decides the actual path's sign. It is never
converted into permission to execute. All obstacle implications must succeed to
certify a multi-obstacle hold. The offline polynomial sign result is stored
separately; the audit checks that no successful implication contradicts it.

## Independent analytical cases

The existing collision example has `p_0=(.04,0)`, `v_0=(-1,0)`, `u=(10,0)`,
`T=.2`, `c=(-1,0)`, `R=1`. The chord is the constant initial point. Its barrier
is `.0816`, while the physical path reaches `p=(−.01,0)` at `.1 s`, with
barrier `−.0199`. Its peak chord deviation is `.05 m`. Safe endpoints and a safe
chord therefore do not imply a safe held trajectory. This is a prescribed-path
test; no planar viability conclusion is inferred.

The reverse disagreement is also possible. With `p_0=(-1,0)`, `v_0=(2,4)`,
`u=(0,-8)`, `T=1`, `c=(0,0)`, `R=1/2`, the chord passes through the circle.
Writing `s=t*(1-t)`, the actual barrier is

```
h(t) = (1-2t)² + 16*t²*(1-t)² - 1/4
     = 16*(s-1/8)² + 1/2 > 0.
```

Hence exact segment safety and exact trajectory safety are not ordered on this
class of curved paths. That observation is geometric, not a ranking of published
controllers with different assumptions.

An equality case has `p_0=(-1,2)`, `v_0=(2,-4)`, `u=(0,8)`, `T=1`, `R=1`.
Here `D=2`, `rho=1`, and the path touches the circle at the midpoint. Setting
`z=t-1/2` gives `h=12*z²+16*z⁴ >= 0`. Tests perturb the initial height by
`±10^-80`; the negative case is unsafe at the midpoint and the positive case is
strictly safe. Separate zero-acceleration cases cover exact linear tangency and
the same signed perturbations. These are exact rationals, not simulation grids.

## Published source and remaining reading gate

Pagnini and Malis, *Segment-safe control barrier functions for model predictive
control*, European Journal of Control, article 101582, publisher's in-press
corrected-proof record available online 23 July 2026,
[DOI 10.1016/j.ejcon.2026.101582](https://doi.org/10.1016/j.ejcon.2026.101582).
On 23 October the [publisher abstract and section
snippets](https://www.sciencedirect.com/science/article/pii/S0947358026001354)
were accessible through search. They distinguish the guarantee on connecting
segments from empirical performance when actual trajectories differ. The
[author's HAL publication list](https://cv.hal.science/andreapagnini) also records
an ECC 2026 deposit, `hal-05578359v1`; its
[full text](https://inria.hal.science/hal-05578359v1/document) was inaccessible
in this environment. No full theorem, equation, proof or MPC experiment from
either version has been reconstructed in this step. The versions have not been
established to be identical.

The local `segment_candidates` method checks the chord's geometry only. It
does not implement the paper's SSCBF construction or MPC. The elementary tube
test above is also not attributed to an unread equation from that paper.
Curved-path counterexamples do not refute a theorem restricted to segments.
Full source access, numbered condition/proof review, domain and feasibility
comparison, and reconstruction of the original experiments remain open gates.

## Reproduce the finite catalog

```sh
PYTHONPATH=src python scripts/audit-segments.py --output results/segment-contracts
PYTHONPATH=src python scripts/audit-segments.py --verify results/segment-contracts
```

The catalog fixes states, commands, circles, actuator limits and physical
durations. It contains deliberate diagnostic examples, not a random sample or
a performance ranking. Outputs retain full exact polynomial sign evidence,
configuration, source revision/package hash, audit-script hash and software
provenance. Replay regenerates all scientific fields; its own provenance remains
separate. No elapsed-time distributions or deadline claims are collected here.
