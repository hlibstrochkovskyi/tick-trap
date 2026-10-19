"""Finite-candidate safety reference with a retained certified continuation.

This uses the established backup-plan/terminal-invariance construction. It is
neither a new algorithm claim nor a reproduction of a full predictive MPC paper.
"""

from time import perf_counter_ns

from .continuation import assess_stopping, certify_segment, prepend_hold
from .numbers import positive, vector2
from .planar_control import PlanarDecision, candidate_actions


def _budget(value, name):
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{name} must be a nonnegative integer or None")
    return value


class ContinuationFilter:
    """Stateful filter for the declared exact plant, static circles and update grid.

    Returning an action advances the expected state. The caller must execute that
    exact action for one period before calling again. Mismatched state/environment
    revokes the plan. Candidate and subdivision budgets are operation counts,
    not hard wall-clock deadlines.
    """

    def __init__(self, state, obstacles, duration, a_max, grid_points=5,
                 command_quantum="1e-6", tolerance="1e-10", max_subdivisions=256, max_candidates=None):
        self.obstacles = tuple(obstacles)
        self.duration, self.a_max = positive(duration, "duration"), positive(a_max, "a_max")
        self.quantum, self.tolerance = positive(command_quantum, "command_quantum"), positive(tolerance, "tolerance")
        self.max_subdivisions = _budget(max_subdivisions, "max_subdivisions")
        if self.max_subdivisions is None:
            raise ValueError("max_subdivisions must be finite")
        self.max_candidates = _budget(max_candidates, "max_candidates")
        if isinstance(grid_points, bool) or not isinstance(grid_points, int) or grid_points < 2:
            raise ValueError("grid_points must be an integer >=2")
        self.grid_points = grid_points
        start = perf_counter_ns()
        self.initial_assessment = assess_stopping(state, self.obstacles, self.duration, self.a_max,
                                                  self.tolerance, self.max_subdivisions, self.quantum)
        self.initialization_ns = perf_counter_ns()-start
        self._plan = self.initial_assessment.continuation
        self._revoked = False

    @property
    def continuation(self):
        return self._plan

    def decide(self, state, nominal, *, obstacles=None, max_candidates=None, max_subdivisions=None):
        budget = self.max_candidates if max_candidates is None else _budget(max_candidates, "max_candidates")
        subdivisions = self.max_subdivisions if max_subdivisions is None else _budget(max_subdivisions, "max_subdivisions")
        nominal = vector2(nominal)
        actual_obstacles = self.obstacles if obstacles is None else tuple(obstacles)
        if self._revoked:
            return PlanarDecision("assumption_violation", reason="The stored continuation was revoked; reinitialization is required")
        if self._plan is None:
            return PlanarDecision("initialization_failed", reason="No initial stopping continuation was certified",
                                  details={"initial_assessment": self.initial_assessment.record()})
        same_limits = (self.duration == self._plan.duration and self.a_max == self._plan.a_max
                       and self.quantum == self._plan.command_quantum)
        if not same_limits or not self._plan.matches(state, actual_obstacles):
            self._plan, self._revoked = None, True
            return PlanarDecision("assumption_violation", reason="State, obstacles or command limits differ from the stored plan's exact assumptions")
        actions = candidate_actions(nominal, state, self.duration, self.a_max, self.grid_points, self.quantum)
        limit = len(actions) if budget is None else min(len(actions), budget)
        checked = []
        for action in actions[:limit]:
            hold = certify_segment(state, action, 1, self.obstacles, self.duration, self.a_max,
                                   self.quantum, self.tolerance, subdivisions)
            row = {"action_exact": [str(x) for x in action], "hold": hold.record(),
                   "continuation_status": "not_checked", "accepted": False}
            checked.append(row)
            if hold.status != "safe":
                continue
            end = state.at(action, self.duration)
            recovery = assess_stopping(end, self.obstacles, self.duration, self.a_max,
                                       self.tolerance, subdivisions, self.quantum)
            row["continuation_status"] = recovery.status
            row["continuation_assessment"] = recovery.record()
            if recovery.continuation is None:
                continue
            row["accepted"] = True
            self._plan = prepend_hold(hold, recovery.continuation).advance()
            return PlanarDecision("feasible", action, details={
                "source": "certified_candidate", "checked": checked, "candidate_count": len(actions),
                "checked_count": len(checked), "candidate_budget_exhausted": False,
                "subdivision_budget": subdivisions, "retained_plan": self._plan.record(),
                "guarantee": "hold safety with a retained admissible continuation to collision-free rest"})
        source = "stored_continuation" if self._plan.pieces else "terminal_hold"
        action = self._plan.next_action
        self._plan = self._plan.advance()
        return PlanarDecision("feasible", action,
                              reason="Candidate budget exhausted" if limit < len(actions) else "No newly certified continuation found",
                              details={"source": source, "checked": checked, "candidate_count": len(actions),
                                       "checked_count": len(checked), "candidate_budget_exhausted": limit < len(actions),
                                       "subdivision_budget": subdivisions, "retained_plan": self._plan.record(),
                                       "guarantee": "reused certified continuation; zero input only after certified rest"})
