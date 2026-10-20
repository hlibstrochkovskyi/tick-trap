from copy import deepcopy
import unittest

from tick_trap.zocbf_audit import zocbf_contract_study, verify_zocbf_contract_study


class ZocbfStudyTests(unittest.TestCase):
    def spec(self):
        return {"base": {"a_max": 1}, "durations": ["0.1", 1], "cases": [
            {"name": "jump", "d": 10, "v": 0, "previous_action": 0, "action": 1, "sigma": 20, "tau": "0.3"},
            {"name": "safe_hold", "d": 2, "v": 0, "previous_action": 1, "action": 0, "sigma": 2}]}

    def test_all_policies_see_matched_holds_and_midpoint_matches_exact(self):
        result = zocbf_contract_study(self.spec())
        self.assertEqual(len(result["records"]), 4)
        replay = verify_zocbf_contract_study(self.spec(), result)
        self.assertEqual((replay["holds"], replay["buffer_assessments"], replay["condition_assessments"]), (4, 24, 144))
        for record in result["records"]:
            for buffer in record["assessments"]:
                exact, midpoint = buffer["variants"][0], buffer["variants"][3]
                self.assertEqual(exact["condition_passed"], midpoint["condition_passed"])
                self.assertEqual(exact["residual_exact"], midpoint["residual_exact"])

    def test_valid_bounds_and_endpoint_predictions_do_not_admit_unsafe_proxy_holds(self):
        result = zocbf_contract_study(self.spec())
        for group in result["groups"]:
            self.assertEqual(group["holds"], 4)
            if group["buffer_policy"] != "endpoint_only" and group["variant"] in ("exact_previous", "euler_tightened", "midpoint_previous"):
                self.assertEqual(group["passes_with_safe_left_and_unsafe_proxy"], 0)
        stale = next(g for g in result["groups"] if g["buffer_policy"] == "norm_tube" and g["variant"] == "stale_end_input")
        self.assertEqual(stale["passes_with_safe_left_and_unsafe_jump"], 2)
        self.assertGreater(stale["invalid_endpoint_lower_bounds"], 0)

    def test_backward_oracle_with_unit_gamma_is_an_exact_proxy_path_test(self):
        spec = self.spec()
        spec["base"]["gamma"] = 1
        for record in zocbf_contract_study(spec)["records"]:
            oracle = next(b for b in record["assessments"] if b["buffer_policy"] == "oracle_backward_drop")
            self.assertEqual(oracle["variants"][0]["condition_passed"], record["constraint_path_status"] == "safe")

    def test_replay_rejects_changed_history_buffers_margins_and_contract_labels(self):
        original = zocbf_contract_study(self.spec())
        for change in (
            lambda r: r["records"][0].__setitem__("previous_action_exact", "1"),
            lambda r: r["records"][0].__setitem__("constraint_path_status", "safe"),
            lambda r: r["records"][0]["assessments"][0].__setitem__("delta_exact", "0"),
            lambda r: r["records"][0]["assessments"][0]["variants"][2].__setitem__("prediction_margin_exact", "0"),
            lambda r: r["records"][0]["assessments"][0]["variants"][5].__setitem__("matches_paper_input_pairing", True),
            lambda r: r["groups"][0].__setitem__("raw_condition_passes", 999),
            lambda r: r["records"].pop(),
        ):
            changed = deepcopy(original)
            change(changed)
            with self.assertRaises(ValueError):
                verify_zocbf_contract_study(self.spec(), changed)

    def test_invalid_and_ambiguous_inputs_are_rejected(self):
        for change in ({"unknown": 1}, {"base": {"delay": 1}}, {"durations": []}, {"durations": ["0.1", "1/10"]}):
            with self.assertRaises(ValueError):
                zocbf_contract_study(self.spec() | change)
        spec = self.spec()
        spec["cases"][0]["previous_action"] = 2
        with self.assertRaises(ValueError):
            zocbf_contract_study(spec)


if __name__ == "__main__":
    unittest.main()
