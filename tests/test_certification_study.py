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


if __name__ == "__main__":
    unittest.main()
