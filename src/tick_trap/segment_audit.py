"""Offline chord/held-trajectory contracts, separate from any MPC controller.

The tube implication is elementary interpolation geometry, not an implementation
of Pagnini--Malis SSCBF. Failed sufficient conditions remain unknown. The exact
polynomial sign reference is retained separately and never authorizes execution.
"""

from collections import Counter
from fractions import Fraction
import json

from .algebraic_reference import exact_sign_reference
from .dynamics import Circle, PlanarState
from .numbers import positive, vector2
from .planar_control import segment_minimum
from .qp import dot


ASSUMPTIONS = {
    "model": "Exact planar double integrator p_dot=v, v_dot=u; static circular forbidden interiors; radius includes robot size",
    "initial_set": "The specified exact state; a successful one-hold certificate includes its initial geometric safety, not viability or a high-order filter domain",
    "actuation": "The specified acceleration is held exactly and lies in the recorded componentwise actuator box",
    "observation": "Exact state, obstacle center and total collision radius; no measurement or model uncertainty",
    "numerical": "Exact rational arithmetic; radical-free tube test; separately implemented square-free/Sturm polynomial sign reference; no formal program proof",
    "execution": "Exactly the specified positive hold duration; zero delay, no disturbance or contact dynamics; boundary contact is permitted",
}


def _exact(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Segment audit requires exact rational inputs")
    return Fraction(value)


def segment_hold_audit(state, action, obstacle, duration, a_max):
    """Audit one hold without synthesizing or executing an action.

    L(t) is the chord parameterized over [0,T]. The exact deviation is
    p(t)-L(t) = u*t*(t-T)/2, with squared peak rho²=||u||²*T⁴/64.
    If D is the minimum chord distance, D>=R+rho implies geometric safety.
    Writing A=D²-R²-rho² avoids radicals: A>=0 AND A²>=4*R²*rho².
    Both guards are necessary for this equivalence. Failure means unknown,
    including when the independent actual-trajectory reference decides a sign.
    """
    duration = positive(_exact(duration), "duration")
    a_max = positive(_exact(a_max), "a_max")
    action = vector2(tuple(_exact(x) for x in action))
    if max(abs(x) for x in action) > a_max:
        raise ValueError("Action lies outside the recorded actuator box")
    margin = segment_minimum(state, action, obstacle, duration)
    rho_squared = dot(action, action)*duration**4/64
    excess = margin-rho_squared
    squared_slack = excess**2-4*obstacle.radius**2*rho_squared
    tube_status = "safe" if excess >= 0 and squared_slack >= 0 else "unknown"
    polynomial = obstacle.polynomial(state, action)
    reference = exact_sign_reference(polynomial, duration)
    initial, final = polynomial[0], sum(c*duration**i for i, c in enumerate(polynomial))
    if tube_status == "safe" and reference["status"] != "safe":
        raise ArithmeticError("Tube implication contradicts exact polynomial sign reference")
    return {
        "initial_barrier_exact": str(initial), "final_barrier_exact": str(final),
        "sampled_status": "safe" if min(initial, final) >= 0 else "unsafe",
        "chord_minimum_barrier_exact": str(margin),
        "chord_status": "safe" if margin >= 0 else "unsafe",
        "deviation_squared_peak_exact": str(rho_squared),
        "deviation_peak_time_exact": str(duration/2),
        "tube_excess_exact": str(excess), "tube_squared_slack_exact": str(squared_slack),
        "tube_status": tube_status,
        "trajectory_polynomial_exact": [str(c) for c in polynomial],
        "trajectory_reference": reference,
    }


def segment_contract_study(spec):
    """Reproduce a finite exact-geometry test catalog; no timing or MPC claims."""
    if not isinstance(spec, dict) or set(spec) != {"cases"}:
        raise ValueError("Expected a segment catalog with cases only")
    if not isinstance(spec["cases"], list) or not spec["cases"]:
        raise ValueError("Expected a nonempty list of cases")
    records, names = [], set()
    fields = {"name", "p", "v", "action", "obstacles", "duration", "a_max"}
    for case in spec["cases"]:
        if not isinstance(case, dict) or set(case) != fields:
            raise ValueError("Unexpected segment case fields")
        name = case["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("Case names must be nonempty and unique")
        names.add(name)
        if not isinstance(case["obstacles"], list) or not case["obstacles"]:
            raise ValueError("Each case requires at least one obstacle")
        if any(not isinstance(o, dict) or set(o) != {"center", "radius"}
               for o in case["obstacles"]):
            raise ValueError("Only static circles with center and radius are supported")
        state = PlanarState(tuple(_exact(x) for x in case["p"]),
                            tuple(_exact(x) for x in case["v"]))
        action = vector2(tuple(_exact(x) for x in case["action"]))
        obstacles = [Circle(tuple(_exact(x) for x in o["center"]), _exact(o["radius"]))
                     for o in case["obstacles"]]
        assessments = [segment_hold_audit(state, action, o, case["duration"], case["a_max"])
                       for o in obstacles]
        joint = lambda key: "safe" if all(a[key] == "safe" for a in assessments) else "unsafe"
        reference_status = "safe" if all(a["trajectory_reference"]["status"] == "safe"
                                        for a in assessments) else "unsafe"
        records.append({"name": name, "input": case, "obstacles": assessments,
                        "sampled_status": joint("sampled_status"), "chord_status": joint("chord_status"),
                        "tube_status": "safe" if all(a["tube_status"] == "safe" for a in assessments) else "unknown",
                        "trajectory_status": reference_status})
    transitions = Counter((r["chord_status"], r["trajectory_status"]) for r in records)
    counts = {"holds": len(records), "obstacle_queries": sum(len(r["obstacles"]) for r in records),
              "sampled_safe_but_trajectory_unsafe": sum(r["sampled_status"] == "safe" and r["trajectory_status"] == "unsafe" for r in records),
              "tube_certified_safe": sum(r["tube_status"] == "safe" for r in records),
              "tube_unknown_safe": sum(r["tube_status"] == "unknown" and r["trajectory_status"] == "safe" for r in records),
              "tube_unknown_unsafe": sum(r["tube_status"] == "unknown" and r["trajectory_status"] == "unsafe" for r in records)}
    return {"assumptions": ASSUMPTIONS.copy(), "counts": counts,
            "chord_to_trajectory": [{"chord": a, "trajectory": b, "holds": transitions[a, b]}
                                    for a in ("safe", "unsafe") for b in ("safe", "unsafe")],
            "records": records,
            "scope": "Offline elementary chord-deviation contract on fixed exact holds; no controller changes, viability claim, timings, MPC reproduction or novel algorithm"}


def verify_segment_contract_study(spec, saved):
    expected = segment_contract_study(spec)
    if json.dumps(saved, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("Segment audit differs from exact regeneration")
    return {"status": "verified", **expected["counts"],
            "scope": "Exact regeneration of inputs, chord minima, tube implications and full independent polynomial sign evidence; not formal program verification"}
