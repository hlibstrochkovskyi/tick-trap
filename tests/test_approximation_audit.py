from fractions import Fraction as F
import unittest

from tick_trap.approximation_audit import approximate_wall_step, audit_wall_approximation, barrier_distance_squared
from tick_trap.dynamics import WallState


class ApproximationAuditTests(unittest.TestCase):
    def test_midpoint_is_exact_and_euler_error_is_quadratic_in_the_period(self):
        state = WallState("0.6", 1)
        errors = []
        for duration in (F(2, 5), F(1, 5), F(1, 10), F(1, 20)):
            self.assertEqual(approximate_wall_step(state, 4, duration, "midpoint"), state.at(4, duration))
            euler = approximate_wall_step(state, 4, duration, "euler")
            errors.append(abs(state.at(4, duration).d-euler.d))
        self.assertTrue(all(a == 4*b for a, b in zip(errors, errors[1:])))
        with self.assertRaises(ValueError):
            approximate_wall_step(state, 0, 1, "unknown")

    def test_approximate_decrement_can_pass_while_actual_sample_is_outside(self):
        result = audit_wall_approximation(WallState("0.6", 0), 4, "0.4")
        euler, midpoint = result["maps"]
        self.assertTrue(euler["pointwise_ingredients_satisfied"])
        self.assertFalse(result["exact_sampled_barrier_safe"])
        self.assertEqual(result["actual_end_barrier_exact"], "-1/5")
        self.assertFalse(midpoint["approximate_decrement_satisfied"])
        self.assertEqual(midpoint["normalized_error_squared_exact"], "0")
        self.assertGreater(F(midpoint["rho_at_duration_exact"]), 0)

    def test_exact_sample_checks_do_not_certify_the_barrier_between_samples(self):
        result = audit_wall_approximation(WallState("0.31", 1), F(-12, 5), "0.2", gain=4)
        self.assertTrue(result["maps"][1]["pointwise_ingredients_satisfied"])
        self.assertTrue(result["exact_sampled_barrier_safe"])
        self.assertEqual(result["barrier_minimum_exact"], "-19/3000")
        self.assertEqual(result["barrier_witness_time_exact"], "7/60")
        self.assertEqual(result["barrier_path_status"], "unsafe")
        self.assertEqual(result["geometric_path_status"], "safe")

    def test_viable_safe_samples_can_hide_a_geometric_collision(self):
        result = audit_wall_approximation(WallState("0.06", 1), F(-17, 4), "0.4", tau="0.01", gain="2.2")
        self.assertTrue(result["initial_viable"])
        self.assertTrue(result["maps"][1]["pointwise_ingredients_satisfied"])
        self.assertTrue(result["exact_sampled_geometric_safe"])
        self.assertTrue(result["exact_sampled_barrier_safe"])
        self.assertEqual(result["geometric_path_status"], "unsafe")
        self.assertEqual(result["geometric_minimum_exact"], "-49/850")
        self.assertEqual(result["practical_safety_family_certificate"], "not_established")

    def test_dilation_does_not_relabel_a_barrier_violation_as_safe(self):
        result = audit_wall_approximation(WallState("0.6", 0), 4, "0.4", radii=(0, "0.2"))
        self.assertEqual(result["barrier_path_status"], "unsafe")
        self.assertFalse(result["dilations"][0]["path_within_dilation"])
        self.assertTrue(result["dilations"][1]["path_within_dilation"])

    def test_exact_projection_scaling_and_boundary_radius(self):
        state = WallState(F(-1, 4), 0)
        distance, closest = barrier_distance_squared(state, F(3, 4))
        self.assertEqual(distance, F(1, 25))
        self.assertEqual(closest.d-F(3, 4)*closest.v, 0)
        result = audit_wall_approximation(state, 0, 1, tau=F(3, 4), radii=(F(1, 5), F(1, 5)-F(1, 10**100)))
        self.assertTrue(result["dilations"][0]["path_within_dilation"])
        self.assertFalse(result["dilations"][1]["path_within_dilation"])
        scaled, projected = barrier_distance_squared(state, F(3, 4), 2, 3)
        self.assertEqual(projected.d-F(3, 4)*projected.v, 0)
        self.assertNotEqual(distance, scaled)
        self.assertEqual(((projected.d-state.d)/2)**2+((projected.v-state.v)/3)**2, scaled)

    def test_step_restriction_and_invalid_inputs_are_explicit(self):
        result = audit_wall_approximation(WallState(1, 0), 0, 1, gain=2)
        self.assertTrue(result["maps"][0]["approximate_decrement_satisfied"])
        self.assertFalse(result["maps"][0]["step_restriction_satisfied"])
        self.assertFalse(result["maps"][0]["pointwise_ingredients_satisfied"])
        for kwargs in ({"action": 11}, {"duration": 0}, {"position_scale": 0}, {"velocity_scale": -1},
                       {"radii": []}, {"radii": [0, 0]}, {"radii": [-1]}, {"gain": True}):
            args = dict(state=WallState(1, 0), action=0, duration=1)
            with self.assertRaises(ValueError):
                audit_wall_approximation(**(args | kwargs))


if __name__ == "__main__":
    unittest.main()
