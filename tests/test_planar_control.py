import unittest
from unittest.mock import patch
from fractions import Fraction as F

from tick_trap.dynamics import Circle, PlanarState
from tick_trap.planar_control import (candidate_actions, decide_planar, hocbf_constraints,
                                     segment_minimum, zocbf_buffer, _rounded_qp)
from tick_trap.polynomial import certify_minimum
from tick_trap.qp import HalfSpace


class PlanarControlTests(unittest.TestCase):
    def test_hocbf_derivatives_match_independent_trajectory_polynomial(self):
        state = PlanarState((2, 1), (-1, 2))
        obstacle = Circle((0, 0), 1)
        action = (F("0.7"), F("-0.4"))
        coefficients = obstacle.polynomial(state, action)
        constraints, domains = hocbf_constraints(state, [obstacle], 3, 5)
        psi2 = 2*coefficients[2]+8*coefficients[1]+15*coefficients[0]
        self.assertEqual(-constraints[0].residual(action), psi2)
        self.assertEqual(F(domains[0]["psi1_exact"]), coefficients[1]+3*coefficients[0])

    def test_hocbf_action_and_rounded_residuals(self):
        state = PlanarState((2, 0), (-1, 0))
        result = decide_planar("hocbf", state, (-10, 0), [Circle((0, 0), 1)], "0.1", 10)
        self.assertEqual(result.status, "feasible")
        self.assertEqual(result.action, (F(1, 2), F(0)))
        self.assertTrue(all(F(r) <= 0 for r in result.details["constraint_residuals_exact"]))

    def test_curved_path_can_pass_endpoint_and_segment_checks(self):
        state = PlanarState(("0.04", 0), (-1, 0))
        obstacle = Circle((-1, 0), 1)
        for method in ["endpoint_candidates", "segment_candidates"]:
            result = decide_planar(method, state, (10, 0), [obstacle], "0.2", 10)
            self.assertEqual(result.action, (F(10), F(0)))
            self.assertEqual(certify_minimum(obstacle.polynomial(state, result.action), "0.2").status, "unsafe")
        self.assertEqual(segment_minimum(state, (10, 0), obstacle, "0.2"), F("0.0816"))
        result = decide_planar("trajectory_candidates", state, (10, 0), [obstacle], "0.2", 10)
        self.assertFalse(result.details["checked"][0]["accepted"])
        if result.status == "feasible":
            self.assertEqual(certify_minimum(obstacle.polynomial(state, result.action), "0.2").status, "safe")

    def test_unknown_candidate_is_not_accepted(self):
        state = PlanarState(("-0.3", 1), (1, 0))
        result = decide_planar("trajectory_candidates", state, (0, 0), [Circle((0, 0), 1)], 1, 1,
                               max_subdivisions=0)
        self.assertFalse(result.details["checked"][0]["accepted"])
        self.assertEqual(result.details["checked"][0]["certificates"][0]["status"], "unknown")

    def test_multiple_obstacles_and_no_obstacle_case(self):
        state = PlanarState((0, 0), (0, 0))
        obstacles = [Circle((-2, 0), 1), Circle((2, 0), 1)]
        result = decide_planar("trajectory_candidates", state, (0, 0), obstacles, 1, 1)
        self.assertEqual(result.action, (F(0), F(0)))
        self.assertEqual(len(result.details["checked"][0]["certificates"]), 2)
        empty = decide_planar("trajectory_candidates", state, ("0.3", "0.4"), [], 1, 1)
        self.assertEqual(empty.action, (F("0.3"), F("0.4")))

    def test_zocbf_local_buffer_is_sufficient_for_accepted_actions(self):
        state = PlanarState((5, 0), (-1, 0))
        obstacle = Circle((0, 0), 1)
        self.assertGreater(zocbf_buffer(state, obstacle, "0.1", 2), 0)
        result = decide_planar("zocbf_candidates", state, (0, 0), [obstacle], "0.1", 2)
        self.assertEqual(result.status, "feasible")
        self.assertEqual(certify_minimum(obstacle.polynomial(state, result.action), "0.1").status, "safe")

    def test_domain_and_search_exhaustion_are_distinct(self):
        obstacle = Circle((0, 0), 1)
        state = PlanarState(("1.01", 0), (-100, 0))
        self.assertEqual(decide_planar("hocbf", state, (0, 0), [obstacle], "0.01", 1).status, "outside_domain")
        result = decide_planar("trajectory_candidates", state, (0, 0), [obstacle], "0.01", 1)
        self.assertEqual(result.status, "search_exhausted")
        self.assertIsNone(result.action)

    def test_command_set_is_bounded_quantized_and_deterministic(self):
        state = PlanarState((2, 0), ("0.33333333", "-0.75"))
        actions = candidate_actions((4, -4), state, "0.1", 1, 4, "0.01")
        self.assertEqual(actions, candidate_actions((4, -4), state, "0.1", 1, 4, "0.01"))
        self.assertEqual(len(actions), len(set(actions)))
        for action in actions:
            self.assertLessEqual(max(abs(x) for x in action), 1)
            self.assertTrue(all((x/F("0.01")).denominator == 1 for x in action))

    def test_rounding_rechecks_original_inequality(self):
        result = _rounded_qp((F(0), F(0)), [HalfSpace((1, 0), F(1, 3))], F(1), F("1e-6"))
        self.assertEqual(result.action, (F("0.333334"), F(0)))
        self.assertLessEqual(F(result.details["constraint_residuals_exact"][0]), 0)

    def test_feasible_continuous_qp_can_have_unresolved_command_search(self):
        constraints = [HalfSpace((1, 0), F("0.31")), HalfSpace((-1, 0), F("-0.39")),
                       HalfSpace((0, 1), F("0.31")), HalfSpace((0, -1), F("-0.39"))]
        result = _rounded_qp((F(0), F(0)), constraints, F(1), F("0.1"))
        self.assertEqual(result.status, "command_unresolved")
        self.assertIsNone(result.action)

    def test_hocbf_infeasibility_is_proved_for_its_constraints(self):
        result = decide_planar("hocbf", PlanarState((2, 0), (-1, 0)), (0, 0),
                               [Circle((0, 0), 1)], "0.1", "0.1")
        self.assertEqual(result.status, "infeasible")

    def test_candidate_budget_exhaustion_does_not_mean_all_controls_were_checked(self):
        with patch("tick_trap.planar_control.candidate_actions", side_effect=AssertionError("Unexpected candidate generation")):
            result = decide_planar("trajectory_candidates", PlanarState((-2, 0), (1, 0)), (0, 0),
                                   [Circle((0, 0), 1)], "0.1", 2, max_candidates=0)
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(result.details["checked_count"], 0)
        self.assertIsNone(result.details["candidate_count"])
        self.assertFalse(result.details["candidate_set_constructed"])
        self.assertIsNone(result.action)

    def test_backup_filter_cannot_be_accidentally_used_as_a_stateless_method(self):
        with self.assertRaises(ValueError):
            decide_planar("backup_candidates", PlanarState((-2, 0), (1, 0)), (0, 0), [], "0.1", 2)

    def test_sampling_aware_methods_enforce_domain_and_record_candidate_bounds(self):
        obstacle = Circle((0, 0), 1)
        for method in ("sacbf_candidates", "sacbf_relaxed_candidates"):
            decision = decide_planar(method, PlanarState((2, 0), (-4, 0)), (0, 0), [obstacle], "0.1", 10)
            self.assertEqual(decision.status, "outside_domain")
            self.assertIsNone(decision.action)
            decision = decide_planar(method, PlanarState((2, 0), (-1, 0)), (0, 0), [obstacle], "0.1", 2)
            self.assertEqual(decision.status, "feasible")
            assessments = decision.details["checked"][-1]["sampling_assessments"]
            self.assertEqual(len(assessments), 1)
            self.assertTrue(assessments[0]["accepted"])
            self.assertEqual(certify_minimum(obstacle.polynomial(PlanarState((2, 0), (-1, 0)), decision.action), "0.1").status, "safe")

    def test_sampling_aware_zero_budget_does_not_construct_candidates(self):
        with patch("tick_trap.planar_control.candidate_actions", side_effect=AssertionError("Unexpected search")):
            result = decide_planar("sacbf_relaxed_candidates", PlanarState((2, 0), (-1, 0)), (0, 0),
                                   [Circle((0, 0), 1)], "0.1", 2, max_candidates=0)
        self.assertEqual(result.status, "budget_exhausted")
        self.assertFalse(result.details["candidate_set_constructed"])

    def test_relaxed_safe_stationary_choice_is_not_infeasibility(self):
        state = PlanarState(("-0.52", "0.3"), (0, 0))
        obstacles = (Circle((0, 0), "0.5"), Circle(("1.2", "-0.7"), "0.4"))
        decision = decide_planar("sacbf_relaxed_candidates", state, ("2.52", "0.4"), obstacles, "0.4", 2)
        self.assertEqual(decision.action, (0, 0))
        self.assertEqual(state.at(decision.action, "0.4"), state)
        # A feasible steering command exists but costs 0.2 more than holding.
        from tick_trap.sampling import sacbf_assessment
        self.assertTrue(all(sacbf_assessment(state, (0, 1), o, "0.4", relaxed=True)["accepted"] for o in obstacles))
        nominal = (F("2.52"), F("0.4"))
        cost = lambda u: sum((x-y)**2 for x, y in zip(u, nominal))
        self.assertEqual(cost((0, 1))-cost((0, 0)), F("0.2"))


if __name__ == "__main__":
    unittest.main()
