from copy import deepcopy
import unittest

from tick_trap.certification_study import certification_study


class CertificationStudyTests(unittest.TestCase):
    def spec(self):
        return {"base": {"grid_points": 3, "tolerance": "1e-14", "max_subdivisions": 4096},
                "cases": [{"name": "approach", "p": [-2, "0.3"], "v": [1, 0], "nominal": [1, 0],
                           "obstacles": [{"center": [0, 0], "radius": "0.5"}], "duration": "0.4", "a_max": 2}],
                "repeats": 2, "seed": 7, "tolerances": ["1e-8"], "budgets": [0, 64]}

    def test_queries_are_matched_and_resolved_signs_do_no_more_subdivision(self):
        result = certification_study(self.spec())
        self.assertEqual(result["applicable_cases"], 1)
        groups = result["groups"]
        self.assertEqual(len(groups), 5)
        self.assertTrue(all(g["queries"] == groups[0]["queries"] for g in groups))
        for minimum, sign in zip(groups[1::2], groups[2::2]):
            self.assertEqual((minimum["accepted"], minimum["rejected"], minimum["unknown"]),
                             (sign["accepted"], sign["rejected"], sign["unknown"]))
            self.assertLessEqual(sign["total_subdivisions"], minimum["total_subdivisions"])
        for row in result["measurements"]:
            self.assertEqual(len(row["all_predicate_ns"]), 2)
            self.assertEqual(len(row["sample_positions"]), 2)
            if row["reference_status"] == "unsafe":
                self.assertNotEqual(row["result"]["status"], "accepted")
        by_control = {}
        for row in result["measurements"]:
            by_control.setdefault(row["candidate_index"], []).append(row)
        for rows in by_control.values():
            for repeat in range(2):
                self.assertEqual(sorted(row["sample_positions"][repeat] for row in rows), list(range(5)))

    def test_seeded_order_is_reproducible_and_reference_is_separate(self):
        first, second = certification_study(self.spec()), certification_study(self.spec())
        self.assertEqual([r["sample_positions"] for r in first["measurements"]],
                         [r["sample_positions"] for r in second["measurements"]])
        for a, b in zip(first["measurements"], second["measurements"]):
            self.assertEqual(a["result"], b["result"])
        self.assertIn("reference", first)

    def test_outside_domain_is_not_counted_as_rejection(self):
        spec = self.spec()
        spec["cases"][0]["v"] = [4, 0]
        result = certification_study(spec)
        self.assertEqual(result["applicable_cases"], 0)
        self.assertEqual(result["measurements"], [])
        self.assertEqual(result["groups"], [])

    def test_invalid_measurement_settings_are_rejected(self):
        for change in ({"repeats": 0}, {"seed": True}, {"budgets": [-1]}, {"budgets": []},
                       {"budgets": [0, 0]}, {"tolerances": ["0.1", "1/10"]}, {"tolerances": [0]}, {"unexpected": 1},
                       {"strategies": []}, {"strategies": ["sign", "sign"]}, {"strategies": ["unsupported"]}, {"strategies": [{}]}):
            spec = deepcopy(self.spec()) | change
            with self.assertRaises(ValueError):
                certification_study(spec)

    def test_auxiliary_only_classification_differences_are_reported_in_both_directions(self):
        spec = {"base": {"grid_points": 2}, "strategies": ["sign", "auxiliary_sign"], "budgets": [0],
                "repeats": 1, "cases": [
                    {"name": "derive_safe", "p": ["-0.3", "1.06"], "v": [1, 0], "nominal": [0, 0],
                     "obstacles": [{"center": [0, 0], "radius": 1}], "duration": 1, "a_max": 1, "lambda1": 3},
                    {"name": "lose_negative_h_witness", "p": [2, 0], "v": [-1, 0], "nominal": [0, 0],
                     "obstacles": [{"center": [0, 0], "radius": 1}], "duration": "2.9", "a_max": 1}]}
        result = certification_study(spec)
        transitions = {(r["dual_sign"], r["auxiliary_sign"]): r["controls"] for r in result["decision_comparisons"][0]["transitions"]}
        self.assertGreater(transitions[("unknown", "accepted")], 0)
        self.assertGreater(transitions[("rejected", "unknown")], 0)
        for row in result["measurements"]:
            if row["strategy"] == "auxiliary_sign":
                self.assertTrue(all(p["property"] == "psi" for p in row["result"]["proofs"]))
                self.assertEqual(len(row["result"]["proofs"]), len(row["result"]["geometric_implications"]))
                if row["result"]["status"] == "accepted":
                    self.assertNotEqual(row["reference_status"], "unsafe")

    def test_custom_strategy_order_preserves_the_minimum_sign_pairing(self):
        result = certification_study(self.spec() | {"strategies": ["auxiliary_sign", "sign", "minimum"]})
        self.assertEqual(result["strategies"], ["auxiliary_sign", "sign", "minimum"])
        self.assertEqual(len(result["groups"]), 6)

    def test_independent_reference_counts_and_all_paired_distributions(self):
        result = certification_study(self.spec() | {"strategies": ["sacbf_relaxed", "minimum", "sign", "auxiliary_sign"]})
        self.assertEqual(len(result["paired_comparisons"]), 12)  # 6 pairs, 2 budgets
        for group in result["groups"]:
            self.assertEqual(group["accepted_unsafe_controls"], 0)
            self.assertEqual(group["accepted_safe_controls"], group["accepted"])
            self.assertEqual(group["unknown_safe_controls"]+group["unknown_unsafe_controls"], group["unknown"])
            self.assertEqual(group["per_control_median_ns_distribution"]["count"], group["queries"])
        for pair in result["paired_comparisons"]:
            self.assertEqual(sum(t["controls"] for t in pair["transitions"]), pair["controls"])
            self.assertEqual(pair["paired_repeat_time_ratio"]["count"], 2*pair["controls"])
            ratios = pair["paired_median_time_ratio"]
            self.assertLessEqual(ratios["min"], ratios["p10"])
            self.assertLessEqual(ratios["p10"], ratios["median"])
            self.assertLessEqual(ratios["median"], ratios["p90"])
            self.assertLessEqual(ratios["p90"], ratios["max"])

    def test_common_per_control_budget_is_never_exceeded(self):
        result = certification_study(self.spec() | {"strategies": ["minimum", "sign", "auxiliary_sign"],
                                                   "budgets": [0, 1, 8], "budget_scope": "per_control"})
        for row in result["measurements"]:
            self.assertLessEqual(row["result"]["subdivisions"], row["budget"])
            self.assertEqual(row["result"]["subdivisions"], sum(c["subdivisions"] for c in row["result"]["proofs"]))
        self.assertEqual(result["budget_scope"], "per_control")
        with self.assertRaises(ValueError):
            certification_study(self.spec() | {"budget_scope": "unknown"})


if __name__ == "__main__":
    unittest.main()
