import random
import unittest
from fractions import Fraction as F
from unittest.mock import patch

from tick_trap.backup_filter import ContinuationFilter
from tick_trap.continuation import assess_stopping
from tick_trap.dynamics import Circle, PlanarState, WallState
from tick_trap.oracle import circle_interval
from tick_trap.planar_control import decide_planar


class BackupFilterTests(unittest.TestCase):
    def test_rejects_a_safe_hold_that_loses_the_stopping_continuation(self):
        state = PlanarState(("1.06", 0), ("-0.3", 0))
        obstacles = (Circle((0, 0), 1),)
        greedy = decide_planar("trajectory_candidates", state, (-1, 0), obstacles, "0.1", 1)
        self.assertEqual(greedy.action, (F(-1), F(0)))
        # Independent one-dimensional calculation establishes the hold is safe,
        # but stopping after it cannot avoid the wall on this radial motion.
        wall = WallState("0.06", "0.3")
        self.assertGreater(wall.minimum(1, "0.1")[0], 0)
        self.assertLess(wall.at(1, "0.1").viability_margin(1), 0)
        self.assertEqual(assess_stopping(state.at(greedy.action, "0.1"), obstacles, "0.1", 1).status, "unsafe")
        controller = ContinuationFilter(state, obstacles, "0.1", 1)
        decision = controller.decide(state, (-1, 0))
        self.assertEqual(decision.action, (F("0.5"), F(0)))
        self.assertEqual(decision.details["source"], "certified_candidate")
        self.assertTrue(controller.continuation.matches(state.at(decision.action, "0.1"), obstacles))

    def test_zero_search_budget_executes_the_old_plan_then_holds_rest(self):
        state = PlanarState((-2, 0), (1, 0))
        obstacles = (Circle((0, 0), "0.5"),)
        controller = ContinuationFilter(state, obstacles, "0.1", 2, max_candidates=0)
        # Reuse must not depend on a new root/certificate calculation.
        with patch("tick_trap.backup_filter.certify_segment", side_effect=AssertionError("Unexpected recertification")), \
             patch("tick_trap.backup_filter.assess_stopping", side_effect=AssertionError("Unexpected replanning")), \
             patch("tick_trap.backup_filter.candidate_actions", side_effect=AssertionError("Unexpected candidate generation")):
            for index in range(10):
                result = controller.decide(state, (2, 0))
                self.assertEqual(result.status, "feasible")
                self.assertEqual(result.details["checked_count"], 0)
                self.assertFalse(result.details["candidate_set_constructed"])
                self.assertEqual(result.details["source"], "stored_continuation" if index < 5 else "terminal_hold")
                state = state.at(result.action, "0.1")
        self.assertEqual(state, PlanarState(("-1.75", 0), (0, 0)))

    def test_unknown_new_certificate_preserves_the_previously_proved_plan(self):
        state = PlanarState(("-0.3", "1.001"), (1, 0))
        obstacles = (Circle((0, 0), 1),)
        controller = ContinuationFilter(state, obstacles, 1, 1)
        self.assertIsNotNone(controller.continuation)
        result = controller.decide(state, (0, 0), max_candidates=1, max_subdivisions=0)
        self.assertEqual(result.details["checked"][0]["hold"]["status"], "unknown")
        self.assertEqual(result.details["source"], "stored_continuation")
        self.assertEqual(result.action, (F(-1), F(0)))
        self.assertEqual(controller.continuation.state.v, (0, 0))

    def test_failed_initialization_does_not_invent_a_fallback(self):
        state = PlanarState(("1.01", 0), (-10, 0))
        controller = ContinuationFilter(state, (Circle((0, 0), 1),), "0.1", 2)
        result = controller.decide(state, (0, 0))
        self.assertEqual(result.status, "initialization_failed")
        self.assertIsNone(result.action)
        self.assertIsNone(controller.continuation)

    def test_state_or_environment_changes_revoke_the_plan(self):
        state = PlanarState((-2, 0), (1, 0))
        obstacles = (Circle((0, 0), "0.5"),)
        for actual_state, actual_obstacles in [(PlanarState(("-1.99", 0), (1, 0)), obstacles),
                                                (state, (Circle(("0.1", 0), "0.5"),))]:
            controller = ContinuationFilter(state, obstacles, "0.1", 2)
            result = controller.decide(actual_state, (0, 0), obstacles=actual_obstacles)
            self.assertEqual(result.status, "assumption_violation")
            self.assertIsNone(result.action)
            self.assertEqual(controller.decide(state, (0, 0)).status, "assumption_violation")

    def test_adversarial_nominals_and_budget_changes_keep_every_executed_hold_safe(self):
        rng = random.Random(183)
        state = PlanarState((-2, "0.3"), (1, 0))
        obstacles = (Circle((0, 0), "0.5"), Circle(("1.2", "-0.7"), "0.4"))
        controller = ContinuationFilter(state, obstacles, "0.1", 2)
        for _ in range(30):
            nominal = (rng.randint(-10, 10), rng.randint(-10, 10))
            result = controller.decide(state, nominal, max_candidates=rng.choice([0, 1, 5, 30]))
            self.assertEqual(result.status, "feasible")
            for obstacle in obstacles:
                self.assertEqual(circle_interval(state, result.action, obstacle, "0.1")["continuous_status"], "safe")
            state = state.at(result.action, "0.1")
            self.assertTrue(controller.continuation.matches(state, obstacles))
            self.assertEqual(controller.continuation.terminal_state.v, (0, 0))

    def test_invalid_budgets_are_explicit(self):
        state = PlanarState((-2, 0), (1, 0))
        for kwargs in [{"max_candidates": -1}, {"max_candidates": True}, {"grid_points": 1}, {"max_subdivisions": None}]:
            with self.assertRaises(ValueError):
                ContinuationFilter(state, (), "0.1", 2, **kwargs)

    def test_changing_the_update_period_invalidates_a_stored_proof(self):
        state = PlanarState((-2, 0), (1, 0))
        controller = ContinuationFilter(state, (Circle((0, 0), "0.5"),), "0.1", 2)
        controller.duration = F("0.2")
        result = controller.decide(state, (0, 0), max_candidates=0)
        self.assertEqual(result.status, "assumption_violation")
        self.assertIsNone(result.action)


if __name__ == "__main__":
    unittest.main()
