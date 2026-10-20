from fractions import Fraction as F
from itertools import product
import unittest

from tick_trap.controllers import decide
from tick_trap.dynamics import WallState
from tick_trap.zocbf_audit import audit_zocbf_hold


def assessment(result, buffer="norm_tube", variant="exact_previous"):
    row = next(r for r in result["assessments"] if r["buffer_policy"] == buffer)
    return row, next(v for v in row["variants"] if v["variant"] == variant)


class ZocbfAuditTests(unittest.TestCase):
    def test_norm_buffer_matches_the_existing_state_only_wall_specialization(self):
        state = WallState(100, 0)
        result = audit_zocbf_hold(state, 0, 0, "0.75", a_max=4)
        delta, check = assessment(result)
        original = decide("zocbf", state, 0, "0.75", 4, gamma="0.5")
        self.assertEqual(F(delta["delta_exact"]), F("3.75"))
        self.assertEqual(delta["delta_exact"], original.details["delta_exact"])
        self.assertTrue(check["one_hold_implication_ingredients"])

    def test_stale_endpoint_input_can_hide_an_immediate_constraint_jump(self):
        result = audit_zocbf_hold(WallState(10, 0), 0, 1, "0.1", a_max=1, tau="0.3", sigma=20)
        self.assertTrue(result["left_pair_safe"])
        self.assertFalse(result["right_pair_safe"])
        self.assertEqual(result["input_jump_exact"], "-20")
        self.assertEqual(result["constraint_path_status"], "unsafe")
        self.assertEqual(result["geometric_path_status"], "safe")
        _, correct = assessment(result)
        _, stale = assessment(result, variant="stale_end_input")
        self.assertFalse(correct["condition_passed"])
        self.assertTrue(stale["condition_passed"])
        self.assertFalse(stale["endpoint_lower_bound_valid"])

    def test_start_reset_can_change_the_paper_contract_without_losing_hold_safety(self):
        reject_reset = audit_zocbf_hold(WallState(2, 0), 1, 0, 1, a_max=1, sigma=2)
        _, original = assessment(reject_reset)
        _, reset = assessment(reject_reset, variant="reset_start_input")
        self.assertTrue(original["condition_passed"])
        self.assertFalse(reset["condition_passed"])
        admit_reset = audit_zocbf_hold(WallState("1.25", 0), 0, 1, "0.1", a_max=1, sigma=1)
        _, original = assessment(admit_reset)
        _, reset = assessment(admit_reset, variant="reset_start_input")
        self.assertFalse(original["condition_passed"])
        self.assertTrue(reset["condition_passed"])
        self.assertTrue(reset["one_hold_implication_ingredients"])
        self.assertEqual(admit_reset["constraint_path_status"], "safe")

    def test_euler_margin_restores_the_exact_endpoint_implication(self):
        # h=d. With no buffer an Euler endpoint check can admit a collision.
        result = audit_zocbf_hold(WallState("0.1", 0), 0, 10, "0.2", gamma=1)
        _, raw = assessment(result, "endpoint_only", "euler_unadjusted")
        _, corrected = assessment(result, "endpoint_only", "euler_tightened")
        self.assertTrue(raw["condition_passed"])
        self.assertFalse(corrected["condition_passed"])
        self.assertEqual(result["euler_endpoint_error_bound_exact"], "1/5")
        self.assertEqual(result["actual_end_barrier_exact"], "-1/10")
        for buffer in result["assessments"]:
            exact = next(v for v in buffer["variants"] if v["variant"] == "exact_previous")
            midpoint = next(v for v in buffer["variants"] if v["variant"] == "midpoint_previous")
            self.assertEqual(exact["residual_exact"], midpoint["residual_exact"])

    def test_endpoint_only_can_miss_a_jump_that_recovers_during_the_hold(self):
        result = audit_zocbf_hold(WallState(1, -10), 0, 1, 1, a_max=1, sigma=5)
        delta, endpoint = assessment(result, "endpoint_only")
        self.assertTrue(endpoint["condition_passed"])
        self.assertFalse(delta["backward_difference_bound_valid"])
        self.assertEqual(result["right_barrier_exact"], "-4")
        self.assertEqual(result["constraint_path_status"], "unsafe")
        self.assertFalse(assessment(result)[1]["condition_passed"])

    def test_buffer_hierarchy_and_exact_backwards_difference(self):
        for v, u, tau in product((-2, 0, 2), (-2, 0, 2), (F(0), F(3, 10))):
            result = audit_zocbf_hold(WallState(3, v), 0, u, F(2, 5), a_max=2, tau=tau, sigma="0.1")
            deltas = [F(a["delta_exact"]) for a in result["assessments"][:5]]
            self.assertEqual(deltas, sorted(deltas, reverse=True))
            self.assertEqual(deltas[-1], F(result["actual_end_barrier_exact"])-F(result["constraint_minimum_exact"]))
            for row in result["assessments"][:5]:
                self.assertTrue(row["backward_difference_bound_valid"])
                for variant in row["variants"]:
                    if variant["one_hold_implication_ingredients"]:
                        self.assertEqual(result["constraint_path_status"], "safe")

    def test_unit_gamma_can_certify_a_new_hold_even_when_the_left_pair_is_unsafe(self):
        result = audit_zocbf_hold(WallState(1, 0), 1, 0, "0.1", a_max=1, sigma=2, gamma=1)
        _, correct = assessment(result)
        self.assertFalse(result["left_pair_safe"])
        self.assertEqual(correct["endpoint_target_exact"], "0")
        self.assertTrue(correct["one_hold_implication_ingredients"])
        self.assertEqual(result["constraint_path_status"], "safe")

    def test_invalid_commands_and_parameters_are_rejected(self):
        for extra in ({"action": 11}, {"previous_action": -11}, {"tau": -1}, {"sigma": -1},
                      {"gamma": 0}, {"gamma": 2}, {"duration": 0}):
            kwargs = dict(state=WallState(1, 0), previous_action=0, action=0, duration=1)
            with self.assertRaises(ValueError):
                audit_zocbf_hold(**(kwargs | extra))


if __name__ == "__main__":
    unittest.main()
