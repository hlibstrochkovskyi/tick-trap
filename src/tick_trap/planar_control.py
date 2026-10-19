"""Planar baseline synthesis and finite candidate safety filtering.

Certificates concern a single hold. No planar viability-kernel claim is made.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product

from .numbers import positive, q, sqrt_upper, vector2
from .polynomial import certify_minimum, evaluate
from .qp import HalfSpace, dot, project_box

PLANAR_METHODS = ("nominal", "hocbf", "endpoint_candidates", "segment_candidates",
                  "zocbf_candidates", "trajectory_candidates")


@dataclass(frozen=True)
class PlanarDecision:
    status: str
    action: tuple | None = None
    reason: str = ""
    details: dict = field(default_factory=dict)


def hocbf_constraints(state, obstacles, lambda1=2, lambda2=2):
    """Linear-class-K, relative-degree-two HOCBF specialization."""
    lambda1, lambda2 = positive(lambda1, "lambda1"), positive(lambda2, "lambda2")
    constraints, domains = [], []
    for index, obstacle in enumerate(obstacles):
        r = tuple(p-c for p, c in zip(state.p, obstacle.center))
        h = dot(r, r)-obstacle.radius**2
        h_dot = 2*dot(r, state.v)
        psi1 = h_dot+lambda1*h
        rhs = -2*dot(state.v, state.v)-(lambda1+lambda2)*h_dot-lambda1*lambda2*h
        constraints.append(HalfSpace(tuple(2*x for x in r), rhs, f"obstacle_{index}"))
        domains.append({"h_exact": str(h), "psi1_exact": str(psi1), "in_domain": h >= 0 and psi1 >= 0})
    return tuple(constraints), domains


def segment_minimum(state, action, obstacle, duration):
    """Exact minimum barrier on the straight chord, not on the curved path."""
    r = tuple(p-c for p, c in zip(state.p, obstacle.center))
    end = state.at(action, duration)
    chord = tuple(p-p0 for p, p0 in zip(end.p, state.p))
    norm = dot(chord, chord)
    fraction = max(Fraction(0), min(Fraction(1), -dot(r, chord)/norm)) if norm else Fraction(0)
    closest = tuple(x+fraction*w for x, w in zip(r, chord))
    return dot(closest, closest)-obstacle.radius**2


def zocbf_buffer(state, obstacle, duration, a_max):
    """Tan Eq. (4)/Lemma 1, with an enclosing local tube for box actuation."""
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    acceleration = sqrt_upper(2*a_max**2)
    speed = sqrt_upper(dot(state.v, state.v))+acceleration*duration
    r = tuple(p-c for p, c in zip(state.p, obstacle.center))
    radius = sqrt_upper(dot(r, r))+sqrt_upper(dot(state.v, state.v))*duration+acceleration*duration**2/2
    flow = sqrt_upper(speed**2+acceleration**2)
    return 2*radius*flow*duration


def _clip(action, a_max):
    return tuple(max(-a_max, min(a_max, x)) for x in vector2(action))


def _round(action, quantum):
    return tuple(round(x/quantum)*quantum for x in action)


def candidate_actions(nominal, state, duration, a_max, grid_points=5, command_quantum="1e-6"):
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    quantum = positive(command_quantum, "command_quantum")
    if a_max/quantum != int(a_max/quantum):
        raise ValueError("a_max must be an integer multiple of command_quantum")
    if isinstance(grid_points, bool) or not isinstance(grid_points, int) or grid_points < 2:
        raise ValueError("grid_points must be an integer >=2")
    nominal = vector2(nominal)
    axis = [_round(((-a_max+2*a_max*i/(grid_points-1)),), quantum)[0] for i in range(grid_points)]
    actions = set(product(axis, repeat=2))
    actions.add(_round(_clip(nominal, a_max), quantum))
    actions.add((Fraction(0), Fraction(0)))
    actions.add(_round(_clip(tuple(-v/duration for v in state.v), a_max), quantum))
    return sorted(actions, key=lambda u: (sum((x-y)**2 for x, y in zip(u, nominal)), u))


def _rounded_qp(nominal, constraints, a_max, quantum):
    result = project_box(nominal, constraints, a_max)
    if result.status != "feasible":
        return PlanarDecision("infeasible", reason="Exact HOCBF QP and actuator box have no feasible intersection")
    # Check the lattice neighbours of the exact solution independently. This is
    # a local command search, not a proof of global lattice feasibility.
    neighbours = []
    for value in result.action:
        scaled = value/quantum
        floor = scaled.numerator//scaled.denominator
        neighbours.append((floor*quantum, (floor+1)*quantum))
    feasible = [u for u in product(*neighbours)
                if max(abs(x) for x in u) <= a_max and all(c.residual(u) <= 0 for c in constraints)]
    details = {"continuous_optimum_exact": [str(x) for x in result.action],
               "continuous_cost_exact": str(result.cost), "active_constraints": list(result.active),
               "command_quantum_exact": str(quantum)}
    if not feasible:
        return PlanarDecision("command_unresolved", reason="No feasible command found among neighbouring lattice points", details=details)
    cost = lambda u: sum((x-y)**2 for x, y in zip(u, nominal))
    action = min(feasible, key=lambda u: (cost(u), u))
    details.update({"command_cost_exact": str(cost(action)),
                    "constraint_residuals_exact": [str(c.residual(action)) for c in constraints],
                    "guarantee": "HOCBF condition at this update only"})
    return PlanarDecision("feasible", action, details=details)


def decide_planar(method, state, nominal, obstacles, duration, a_max,
                  lambda1=2, lambda2=2, gamma=1, grid_points=5,
                  command_quantum="1e-6", tolerance="1e-10", max_subdivisions=256):
    if method not in PLANAR_METHODS:
        raise ValueError(f"Unknown planar method {method!r}")
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    quantum, gamma = positive(command_quantum, "command_quantum"), positive(gamma, "gamma")
    if gamma > 1:
        raise ValueError("gamma must be in (0,1]")
    if a_max/quantum != int(a_max/quantum):
        raise ValueError("a_max must be an integer multiple of command_quantum")
    nominal, obstacles = vector2(nominal), tuple(obstacles)
    if any(o.polynomial(state, (0, 0))[0] < 0 for o in obstacles):
        return PlanarDecision("outside_domain", reason="Current geometric constraint is violated")
    if method == "nominal":
        return PlanarDecision("feasible", _round(_clip(nominal, a_max), quantum), details={"guarantee": "none"})
    if method == "hocbf":
        constraints, domains = hocbf_constraints(state, obstacles, lambda1, lambda2)
        if not all(d["in_domain"] for d in domains):
            return PlanarDecision("outside_domain", reason="Outside the HOCBF initial-set intersection", details={"domains": domains})
        decision = _rounded_qp(nominal, constraints, a_max, quantum)
        return PlanarDecision(decision.status, decision.action, decision.reason, decision.details | {"domains": domains})

    actions = candidate_actions(nominal, state, duration, a_max, grid_points, quantum)
    buffers = [zocbf_buffer(state, o, duration, a_max) for o in obstacles] if method == "zocbf_candidates" else []
    checked = []
    unknown_count = 0
    for action in actions:
        margins, certificates = [], []
        accepted, unknown = True, False
        for index, obstacle in enumerate(obstacles):
            polynomial = obstacle.polynomial(state, action)
            if method in ("endpoint_candidates", "zocbf_candidates"):
                margin = evaluate(polynomial, duration)-(1-gamma)*polynomial[0]
                if buffers:
                    margin -= buffers[index]
                margins.append(str(margin))
                accepted = accepted and margin >= 0
            elif method == "segment_candidates":
                margin = segment_minimum(state, action, obstacle, duration)
                margins.append(str(margin))
                accepted = accepted and margin >= 0
            else:
                cert = certify_minimum(polynomial, duration, tolerance, max_subdivisions)
                certificates.append({"status": cert.status, "lower_exact": str(cert.lower),
                                     "upper_exact": str(cert.upper), "witness_time_exact": str(cert.witness_time),
                                     "subdivisions": cert.subdivisions, "precision_reached": cert.precision_reached})
                accepted = accepted and cert.status == "safe"
                unknown = unknown or cert.status == "unknown"
        # A single collision witness rules out the entire action, even when a
        # different obstacle's certificate remains unresolved.
        if certificates and any(c["status"] == "unsafe" for c in certificates):
            unknown = False
        checked.append({"action_exact": [str(x) for x in action], "accepted": accepted,
                        "margins_exact": margins, "certificates": certificates})
        unknown_count += unknown
        if accepted:
            return PlanarDecision("feasible", action, details={"candidate_count": len(actions), "checked": checked,
                                  "buffers_exact": [str(x) for x in buffers], "unknown_count": unknown_count,
                                  "guarantee": {
                                      "endpoint_candidates": "sampled endpoint condition only",
                                      "segment_candidates": "straight chord safety only",
                                      "zocbf_candidates": "continuous safety of this hold",
                                      "trajectory_candidates": "continuous safety of this hold",
                                  }[method], "terminal_viability": "unknown"})
    status = "uncertified" if unknown_count else "search_exhausted"
    return PlanarDecision(status, reason="No admissible action certified in the finite candidate set",
                          details={"candidate_count": len(actions), "checked": checked,
                                   "unknown_count": unknown_count, "buffers_exact": [str(x) for x in buffers]})
