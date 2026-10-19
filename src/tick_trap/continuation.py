"""Certified finite continuations to the invariant set of collision-free rest.

Stored proof intervals retain their original scope when execution consumes a
prefix. In particular, an old upper witness is not a minimum enclosure for a
shorter suffix; only its nonnegative lower bound is inherited by that suffix.
"""

from dataclasses import dataclass, replace
from fractions import Fraction

from .numbers import positive, vector2
from .polynomial import certify_minimum


def _state(state):
    return {"p_exact": [str(x) for x in state.p], "v_exact": [str(x) for x in state.v]}


def _status(statuses):
    return "unsafe" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "safe"


def _limits(duration, a_max, command_quantum, tolerance, max_subdivisions):
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    quantum = positive(command_quantum, "command_quantum")
    positive(tolerance, "tolerance")
    if (a_max/quantum).denominator != 1:
        raise ValueError("a_max must be an integer multiple of command_quantum")
    if isinstance(max_subdivisions, bool) or not isinstance(max_subdivisions, int) or max_subdivisions < 0:
        raise ValueError("max_subdivisions must be a nonnegative integer")
    return duration, a_max, quantum


@dataclass(frozen=True)
class PlanPiece:
    action: tuple
    steps: int

    def __post_init__(self):
        object.__setattr__(self, "action", vector2(self.action))
        if isinstance(self.steps, bool) or not isinstance(self.steps, int) or self.steps < 1:
            raise ValueError("Plan piece steps must be a positive integer")


@dataclass(frozen=True)
class SegmentProof:
    state: object
    piece: PlanPiece
    duration: Fraction
    obstacles: tuple
    certificates: tuple

    @property
    def status(self):
        return _status([c.status for c in self.certificates])

    def record(self):
        return {"start_state": _state(self.state), "steps": self.piece.steps,
                "duration_exact": str(self.piece.steps*self.duration),
                "action_exact": [str(x) for x in self.piece.action], "status": self.status,
                "certificates": [{"status": c.status, "lower_exact": str(c.lower), "upper_exact": str(c.upper),
                                  "witness_time_exact": str(c.witness_time), "subdivisions": c.subdivisions}
                                 for c in self.certificates]}


def certify_segment(state, action, steps, obstacles, duration, a_max,
                     command_quantum="1e-6", tolerance="1e-12", max_subdivisions=4096):
    duration, a_max, quantum = _limits(duration, a_max, command_quantum, tolerance, max_subdivisions)
    piece, obstacles = PlanPiece(action, steps), tuple(obstacles)
    if any(abs(u) > a_max or (u/quantum).denominator != 1 for u in piece.action):
        raise ValueError("Continuation command violates actuator bounds or the command quantum")
    certificates = tuple(certify_minimum(o.polynomial(state, piece.action), steps*duration, tolerance, max_subdivisions)
                         for o in obstacles)
    return SegmentProof(state, piece, duration, obstacles, certificates)


@dataclass(frozen=True)
class CertifiedContinuation:
    """Produced by the certifying factories; report dictionaries are not trusted plans."""

    state: object
    obstacles: tuple
    duration: Fraction
    a_max: Fraction
    command_quantum: Fraction
    pieces: tuple
    proofs: tuple
    terminal_state: object
    consumed_steps: int = 0

    def __post_init__(self):
        if self.terminal_state.v != (0, 0) or any(p.status != "safe" for p in self.proofs):
            raise ValueError("Certified continuation requires safe proofs and terminal rest")
        if any(o.polynomial(self.terminal_state, (0, 0))[0] < 0 for o in self.obstacles):
            raise ValueError("Terminal rest position is not geometrically safe")

    def matches(self, state, obstacles):
        return self.state == state and self.obstacles == tuple(obstacles)

    @property
    def next_action(self):
        return self.pieces[0].action if self.pieces else (Fraction(0), Fraction(0))

    def advance(self):
        """Consume exactly one update, retaining proofs of the original intervals."""
        if not self.pieces:
            return self
        first, *tail = self.pieces
        if first.steps > 1:
            tail.insert(0, PlanPiece(first.action, first.steps-1))
        return replace(self, state=self.state.at(first.action, self.duration), pieces=tuple(tail),
                       consumed_steps=self.consumed_steps+1)

    def record(self):
        return {"expected_state": _state(self.state), "terminal_state": _state(self.terminal_state),
                "remaining_steps": sum(p.steps for p in self.pieces), "consumed_steps": self.consumed_steps,
                "remaining_pieces": [{"steps": p.steps, "action_exact": [str(x) for x in p.action]} for p in self.pieces],
                "proof_scope": "original certified intervals; remaining plan is a suffix with inherited nonnegative lower bounds",
                "original_proofs": [p.record() for p in self.proofs],
                "terminal_policy": "zero input forever at collision-free rest"}


@dataclass(frozen=True)
class ContinuationAssessment:
    status: str
    continuation: CertifiedContinuation | None
    pieces: tuple = ()
    proofs: tuple = ()
    duration: Fraction = Fraction(0)
    reason: str = ""

    def record(self):
        return {"viability": "certified" if self.continuation is not None else "unknown", "plan_status": self.status,
                "reason": self.reason, "steps": sum(p.steps for p in self.pieces),
                "duration_exact": str(sum(p.steps for p in self.pieces)*self.duration),
                "pieces": [{"steps": p.steps, "duration_exact": str(p.steps*self.duration),
                            "action_exact": [str(x) for x in p.action], "statuses": [c.status for c in proof.certificates]}
                           for p, proof in zip(self.pieces, self.proofs)],
                "certificates": [{"status": c.status, "lower_exact": str(c.lower), "upper_exact": str(c.upper),
                                  "witness_time_exact": str(c.witness_time)} for proof in self.proofs for c in proof.certificates],
                "command_scope": "configured actuator bounds, update period and command quantum"}


def assess_stopping(state, obstacles, duration, a_max, tolerance="1e-12", max_subdivisions=4096,
                    command_quantum="1e-6"):
    """Construct and certify componentwise braking. Failure leaves viability unknown."""
    duration, a_max, quantum = _limits(duration, a_max, command_quantum, tolerance, max_subdivisions)
    obstacles = tuple(obstacles)
    limit = int(a_max/quantum)
    velocity_units = tuple(v/(duration*quantum) for v in state.v)
    if any(n.denominator != 1 for n in velocity_units):
        return ContinuationAssessment("not_constructed", None, duration=duration,
                                      reason="Velocity cannot reach exact rest on this update/command lattice")
    stop_steps = tuple((abs(n.numerator)+limit-1)//limit for n in velocity_units)
    boundaries = sorted({0, *stop_steps, *(n-1 for n in stop_steps if n)})
    current, pieces, proofs = state, [], []
    for start, end in zip(boundaries, boundaries[1:]):
        action = tuple(-min(a_max, abs(v)/duration)*(1 if v > 0 else -1 if v < 0 else 0) for v in current.v)
        proof = certify_segment(current, action, end-start, obstacles, duration, a_max,
                                quantum, tolerance, max_subdivisions)
        pieces.append(proof.piece)
        proofs.append(proof)
        current = current.at(action, (end-start)*duration)
    if current.v != (0, 0):
        raise ArithmeticError("Stopping-plan construction did not reach rest")
    status = _status([proof.status for proof in proofs])
    if any(o.polynomial(current, (0, 0))[0] < 0 for o in obstacles):
        status = "unsafe"
    plan = CertifiedContinuation(state, obstacles, duration, a_max, quantum, tuple(pieces), tuple(proofs), current) if status == "safe" else None
    return ContinuationAssessment(status, plan, tuple(pieces), tuple(proofs), duration)


def prepend_hold(proof, continuation):
    """Compose a newly certified hold with a certified continuation from its end."""
    if proof.status != "safe" or proof.piece.steps != 1:
        raise ValueError("Expected a certified one-period hold")
    end = proof.state.at(proof.piece.action, proof.duration)
    if proof.duration != continuation.duration or not continuation.matches(end, proof.obstacles):
        raise ValueError("Hold endpoint or environment does not match the continuation")
    if any(abs(u) > continuation.a_max or (u/continuation.command_quantum).denominator != 1 for u in proof.piece.action):
        raise ValueError("Hold does not obey the continuation's command limits")
    return CertifiedContinuation(proof.state, proof.obstacles, proof.duration, continuation.a_max,
                                 continuation.command_quantum, (proof.piece,)+continuation.pieces,
                                 (proof,)+continuation.proofs, continuation.terminal_state)
