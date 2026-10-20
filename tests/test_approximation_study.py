from copy import deepcopy
import unittest

from tick_trap.approximation_audit import approximation_study, verify_approximation_study


class ApproximationStudyTests(unittest.TestCase):
    def spec(self):
        return {"durations": ["0.4", "0.2"], "radii": [0, "0.1", "0.2"],
                "normalizations": [{"name": "unit", "position_scale": 1, "velocity_scale": 1},
                                   {"name": "scaled", "position_scale": 1, "velocity_scale": 10}],
                "cases": [{"name": "euler_error", "d": "0.6", "v": 0, "u": 4},
                          {"name": "hidden_collision", "d": "0.06", "v": 1, "u": "-4.25", "tau": "0.01", "gain": "2.2"}]}

    def test_matched_physical_holds_keep_metric_changes_separate(self):
        result = approximation_study(self.spec())
        self.assertEqual(len(result["records"]), 8)
        for a, b in zip(result["records"][::2], result["records"][1::2]):
            self.assertEqual(a["actual_end_state"], b["actual_end_state"])
            self.assertEqual(a["barrier_minimum_exact"], b["barrier_minimum_exact"])
            self.assertEqual(a["maps"], b["maps"])
        first, scaled = result["records"][:2]
        self.assertNotEqual(first["metric"]["maximum_path_distance_squared_exact"], scaled["metric"]["maximum_path_distance_squared_exact"])
        self.assertFalse(first["dilations"][1]["path_within_dilation"])
        self.assertTrue(scaled["dilations"][1]["path_within_dilation"])
        self.assertEqual(first["barrier_path_status"], "unsafe")
        self.assertEqual(scaled["barrier_path_status"], "unsafe")

    def test_group_counts_and_verified_record_coverage(self):
        result = approximation_study(self.spec())
        replay = verify_approximation_study(self.spec(), result)
        self.assertEqual(replay["held_metric_cases"], 8)
        self.assertEqual(replay["map_comparisons"], 16)
        self.assertEqual(replay["distance_classifications"], 24)
        for group in result["groups"]:
            self.assertEqual(group["holds"], 4)
            self.assertEqual(group["established_practical_safety_families"], 0)
            if group["method"] == "midpoint":
                self.assertEqual(group["nonzero_map_errors"], 0)
                self.assertEqual(group["pointwise_pass_but_exact_sample_outside_b"], 0)
                self.assertGreater(group["pointwise_pass_and_exact_samples_safe_but_geometric_collision"], 0)

    def test_replay_rejects_changed_certificates_statuses_metrics_and_counts(self):
        original = approximation_study(self.spec())
        for change in (
            lambda r: r["records"][0].__setitem__("barrier_path_status", "safe"),
            lambda r: r["records"][0]["maps"][0].__setitem__("normalized_error_squared_exact", "0"),
            lambda r: r["records"][0]["metric"].__setitem__("velocity_scale_exact", "100"),
            lambda r: r["records"][0]["dilations"][0].__setitem__("path_within_dilation", True),
            lambda r: r["groups"][0].__setitem__("established_practical_safety_families", 1),
            lambda r: r["records"].pop(),
        ):
            changed = deepcopy(original)
            change(changed)
            with self.assertRaises(ValueError):
                verify_approximation_study(self.spec(), changed)

    def test_input_coefficients_match_two_distinct_actions(self):
        from fractions import Fraction as F
        a = approximation_study(self.spec())["records"][0]
        spec = self.spec()
        spec["cases"][0]["u"] = 5
        b = approximation_study(spec)["records"][0]
        for x, y in zip(a["maps"], b["maps"]):
            self.assertEqual(F(y["approximate_end_state"]["d_exact"])-F(x["approximate_end_state"]["d_exact"]), F(x["position_input_coefficient_exact"]))
            self.assertEqual(F(y["approximate_end_barrier_exact"])-F(x["approximate_end_barrier_exact"]), F(x["barrier_input_coefficient_exact"]))

    def test_invalid_or_ambiguous_configuration_is_rejected(self):
        for change in ({"unknown": 1}, {"base": {"delay": 1}}, {"durations": []}, {"radii": [0, 0]},
                       {"durations": ["0.1", "1/10"]}, {"normalizations": []}):
            with self.assertRaises(ValueError):
                approximation_study(self.spec() | change)
        spec = self.spec()
        spec["cases"][0]["typo"] = 1
        with self.assertRaises(ValueError):
            approximation_study(spec)


if __name__ == "__main__":
    unittest.main()
