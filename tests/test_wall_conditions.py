from copy import deepcopy
from fractions import Fraction as F
import unittest

from tick_trap.controllers import decide
from tick_trap.dynamics import WallState
from tick_trap.wall_conditions import wall_condition_study


class WallConditionStudyTests(unittest.TestCase):
    def spec(self):
        return {"base": {"horizon": "0.4"}, "durations": ["0.1", "0.4"], "grid_points": 5,
                "cases": [{"name": "approach", "d": "0.6", "v": 1},
                          {"name": "excluded_but_viable", "d": "0.1", "v": 1}]}

    def test_candidates_and_admissions_match_actual_projection_for_every_method(self):
        result = wall_condition_study(self.spec())
        self.assertEqual(len(result["runs"]), 32)
        for case in result["single_hold_cases"]:
            state = WallState(**case["state_exact"])
            for control in case["controls"]:
                for method, admitted in control["admissions"].items():
                    decision = decide(method, state, control["action_exact"], case["duration_exact"], 10,
                                      gain=case["comparison_gain_exact"])
                    if admitted is None:
                        self.assertEqual(decision.status, "outside_domain")
                    else:
                        self.assertEqual(admitted, decision.status == "feasible" and decision.action == F(control["action_exact"]))
        for run in result["runs"]:
            self.assertEqual(run["assumption_violations"], [])
            if run["config"]["method"] != "continuous_cbf":
                self.assertTrue(all(r.get("barrier_safe", True) for r in run["records"]))

    def test_gain_policy_is_explicit_and_second_order_ignores_generic_gain(self):
        result = wall_condition_study(self.spec())
        cases = [c for c in result["single_hold_cases"] if c["name"] == "approach" and c["duration_exact"] == "1/10"]
        fixed, matched = cases
        self.assertEqual(fixed["comparison_gain_exact"], "2")
        self.assertEqual(matched["comparison_gain_exact"], "10")
        self.assertEqual(fixed["selected"]["breeden_second_order"], matched["selected"]["breeden_second_order"])
        self.assertNotEqual(fixed["selected"]["breeden_reachable"], matched["selected"]["breeden_reachable"])

    def test_zero_width_feasible_interval_is_not_infeasibility(self):
        result = wall_condition_study({"cases": [{"name": "boundary", "d": "0.3", "v": 1}],
                                       "durations": ["0.4"], "base": {"horizon": "0.4"}, "grid_points": 2})
        for case in result["single_hold_cases"]:
            interval = case["control_intervals"]["breeden_second_order"]
            self.assertEqual(interval, {"lower_exact": "-10", "upper_exact": "-10", "width_exact": "0"})
            self.assertEqual(case["selected"]["breeden_second_order"]["status"], "feasible")
            self.assertEqual(case["counts"]["breeden_second_order"]["accepted_safe"], 1)

    def test_continuous_emulation_can_violate_b_without_a_geometric_collision(self):
        result = wall_condition_study({"cases": [{"name": "rest", "d": "0.6", "v": 0}],
                                       "durations": ["0.4"], "base": {"horizon": "0.4"}, "grid_points": 21})
        case = result["single_hold_cases"][0]
        control = next(c for c in case["controls"] if c["action_exact"] == "4")
        self.assertTrue(control["admissions"]["continuous_cbf"])
        self.assertFalse(control["joint_safe"])
        self.assertLess(F(control["barrier_minimum_exact"]), 0)
        self.assertGreater(F(control["geometric_minimum_exact"]), 0)

    def test_domain_exclusions_and_initial_nonviability_stay_separate(self):
        spec = self.spec()
        spec["cases"].append({"name": "nonviable_in_domain", "d": 4, "v": 10})
        result = wall_condition_study(spec)
        for case in result["single_hold_cases"]:
            if case["name"] == "excluded_but_viable":
                self.assertTrue(case["initial_viable"])
                self.assertFalse(case["in_domain"])
                self.assertTrue(all(c["applicable"] == 0 for c in case["counts"].values()))
            elif case["name"] == "nonviable_in_domain":
                self.assertFalse(case["initial_viable"])
                self.assertTrue(case["in_domain"])

    def test_invalid_or_unmatched_experiments_are_rejected(self):
        for change in ({"unknown": 1}, {"base": {"delay": "0.1"}}, {"durations": ["0.3"]}, {"grid_points": True},
                       {"methods": ["exact_hold"]}, {"gain_policies": ["adaptive"]}, {"durations": ["0.1", "1/10"]}):
            with self.assertRaises(ValueError):
                wall_condition_study(self.spec() | change)
        for changed in ({"d": -1}, {"typo": 1}, {"name": ""}):
            spec = deepcopy(self.spec())
            spec["cases"][0].update(changed)
            with self.assertRaises(ValueError):
                wall_condition_study(spec)


if __name__ == "__main__":
    unittest.main()
