from copy import deepcopy
from fractions import Fraction as F
import unittest
from unittest.mock import patch

from tick_trap.certification_study import certification_study
from tick_trap.dynamics import Circle, PlanarState
from tick_trap.geometry_study import evaluate_geometry, geometry_study, outcome_timing, verify_geometry_study


class GeometryStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_spec = {"base": {"grid_points": 2}, "strategies": ["sturm"], "repeats": 1,
                           "budgets": [0], "cases": [
            {"name": "safe_path_losing_auxiliary", "p": [2, 0], "v": [-1, 0], "nominal": [0, 0],
             "obstacles": [{"center": [0, 0], "radius": 1}, {"center": [0, 3], "radius": 1}],
             "duration": "0.9", "a_max": 1},
            {"name": "outside_domain", "p": [1, 0], "v": [-5, 0], "nominal": [0, 0],
             "obstacles": [{"center": [0, 0], "radius": 1}], "duration": 1, "a_max": 2}]}
        cls.source = certification_study(cls.source_spec)
        cls.spec = {"strategies": ["command_tube", "box_tube", "minimum", "sign", "sturm"],
                    "tolerances": ["1e-12"], "budgets": [0, 8], "repeats": 2, "seed": 19}
        cls.study = geometry_study(cls.source_spec, cls.source, cls.spec)

    def test_identical_cohort_and_shared_budgets_keep_geometry_and_auxiliary_separate(self):
        study = self.study
        self.assertEqual(study["controls"], self.source["reference"][0]["candidate_count"])
        self.assertEqual(study["applicable_cases"], 1)
        self.assertFalse(study["reference"][1]["hocbf_applicable"])
        self.assertFalse(study["reference"][1]["candidates"])
        for row in study["measurements"]:
            self.assertEqual(row["case_index"], 0)
            if row["budget"] is not None:
                self.assertLessEqual(row["result"]["subdivisions"], row["budget"])
            if row["action_exact"] == ["0", "0"]:
                # p_x=2-t >= 1.1 throughout, but psi(.9)=-1.78 < 0.
                self.assertEqual(row["independent_reference_status"], "safe")
                self.assertEqual(row["auxiliary_reference_status"], "unsafe")
                self.assertEqual(row["joint_reference_status"], "unsafe")
                if row["strategy"] in ("command_tube", "sturm"):
                    self.assertEqual(row["result"]["status"], "accepted")
                if row["strategy"] == "box_tube":
                    self.assertEqual(row["result"]["status"], "unknown")
        result = verify_geometry_study(self.source_spec, self.source, self.spec, study)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["timing"]["elapsed_samples"], 2*len(study["measurements"]))
        self.assertEqual(len(study["groups"]), 7)

    def test_measured_tube_path_cannot_read_polynomial_or_offline_answers(self):
        state, obstacles = PlanarState((2, 0), (-1, 0)), (Circle((0, 0), 1), Circle((0, 3), 1))
        with patch("tick_trap.geometry_study.exact_sign_reference", side_effect=AssertionError("Reference called")), \
             patch("tick_trap.segment_audit.exact_sign_reference", side_effect=AssertionError("Reference called")), \
             patch.object(Circle, "polynomial", side_effect=AssertionError("Polynomial constructed")):
            result = evaluate_geometry("command_tube", state, (F(0), F(0)), obstacles, F(9, 10), F(1))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(len(result["proofs"]), 2)
        self.assertTrue(all(p["goal"] == "tube_sufficiency" for p in result["proofs"]))
        for method in ("command_tube", "box_tube", "minimum", "sign", "sturm"):
            with self.subTest(method=method), self.assertRaises(ValueError):
                evaluate_geometry(method, state, (F(2), F(0)), obstacles, F(9, 10), F(1), F(1, 10**12), 8)

    def test_changed_proofs_coverage_clock_layout_and_property_labels_are_rejected(self):
        changes = [
            lambda s: s["measurements"][0]["result"]["proofs"][0]["evidence"].__setitem__("tube_excess_exact", "999"),
            lambda s: s["measurements"][0].__setitem__("auxiliary_reference_status", "safe"),
            lambda s: s["measurements"][0]["all_predicate_ns"].__setitem__(0, False),
            lambda s: s["measurements"][0]["sample_positions"].__setitem__(0, -1),
            lambda s: s["measurements"].pop(),
            lambda s: s["groups"][0].__setitem__("accepted_auxiliary_unsafe_controls", 999),
            lambda s: s["paired_comparisons"][0]["outcome_costs"][0]["paired_median_time_ratio"].__setitem__("median", 999),
            lambda s: s["diagnostics"]["chord_status"][0].__setitem__("controls", 999),
            lambda s: s.__setitem__("scope", "All future trajectories guaranteed"),
        ]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                altered = deepcopy(self.study)
                change(altered)
                with self.assertRaises(ValueError):
                    verify_geometry_study(self.source_spec, self.source, self.spec, altered)

    def test_source_actions_domains_and_complete_sign_evidence_are_reconstructed(self):
        changes = [
            lambda s: s["reference"][0]["candidates"][0]["action_exact"].__setitem__(0, "999"),
            lambda s: s["reference"][0]["candidates"][0]["independent_evidence"][0]["psi"].__setitem__("probe_time_exact", "0"),
            lambda s: s["reference"][0].__setitem__("hocbf_applicable", False),
            lambda s: s["reference"].pop(),
        ]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                source = deepcopy(self.source)
                change(source)
                with self.assertRaises(ValueError):
                    geometry_study(self.source_spec, source, self.spec)

    def test_default_settings_replay_and_timing_alone_does_not_authenticate_the_clock(self):
        study = geometry_study(self.source_spec, self.source, {})
        result = verify_geometry_study(self.source_spec, self.source, {}, study)
        self.assertIn("clock authenticity is not verified", result["timing"]["scope"])
        with self.assertRaises(ValueError):
            verify_geometry_study(self.source_spec, self.source, self.spec | {"seed": 23}, self.study)

    def test_unsupported_or_duplicated_settings_are_rejected(self):
        for change in ({"strategies": []}, {"strategies": ["SSCBF"]}, {"strategies": ["sign", "sign"]},
                       {"budgets": [True]}, {"budgets": [-1]}, {"budgets": [0, 0]}, {"tolerances": [0]},
                       {"tolerances": ["0.1", "1/10"]}, {"repeats": 0}, {"budget_scope": "per_polynomial"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                geometry_study(self.source_spec, self.source, self.spec | change)

    def test_timing_for_matching_acceptances_is_distinct_from_unknown_versus_resolved(self):
        rows = []
        for index, a_time, b_time, a_status in ((0, 100, 50, "accepted"), (1, 200, 500, "unknown")):
            for method, elapsed, status in (("command_tube", a_time, a_status), ("sign", b_time, "accepted")):
                rows.append({"case_index": 0, "candidate_index": index, "strategy": method,
                             "tolerance_exact": None if method == "command_tube" else "1/1000000000000",
                             "budget": None if method == "command_tube" else 64, "result": {"status": status},
                             "predicate_ns_median": elapsed, "all_predicate_ns": [elapsed, elapsed]})
        costs = outcome_timing(rows, {"baseline": "command_tube", "candidate": "sign",
                                     "tolerance_exact": "1/1000000000000", "budget": 64})
        self.assertEqual([c["controls"] for c in costs], [1, 1])
        self.assertEqual(costs[0]["paired_median_time_ratio"]["median"], 2)
        self.assertEqual(costs[1]["paired_median_time_ratio"]["median"], 0.4)
        self.assertEqual(costs[0]["paired_median_difference_ns"]["median"], 50)
        self.assertEqual(costs[1]["paired_repeat_time_ratio"]["count"], 2)


if __name__ == "__main__":
    unittest.main()
