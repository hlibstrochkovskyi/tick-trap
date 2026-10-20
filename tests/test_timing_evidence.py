from copy import deepcopy
import unittest

from tick_trap.certification_study import certification_study
from tick_trap.timing_evidence import verify_timing_evidence


class TimingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = {"base": {"grid_points": 2}, "strategies": ["sacbf_relaxed", "minimum", "sign", "auxiliary_sign", "sturm"],
                    "repeats": 2, "seed": 71, "tolerances": ["1e-12"], "budgets": [0, 8], "cases": [
                        {"name": "approach", "p": ["1.67", 0], "v": [-1, 0], "nominal": [1, -1],
                         "duration": 1, "a_max": 2, "obstacles": [{"center": [0, 0], "radius": 1}]}]}
        cls.study = certification_study(cls.spec)

    def test_layout_and_aggregates_match_the_saved_repeats(self):
        verified = verify_timing_evidence(self.spec, self.study)
        self.assertEqual(verified["timed_rows"], len(self.study["measurements"]))
        self.assertEqual(verified["elapsed_samples"], 2*len(self.study["measurements"]))
        self.assertEqual(verified["groups"], 8)
        self.assertEqual(verified["paired_settings"], 20)

    def test_tampered_samples_schedule_groups_and_pairs_are_rejected(self):
        changes = [
            lambda s: s["measurements"][0]["all_predicate_ns"].__setitem__(0, False),
            lambda s: s["measurements"][0]["all_predicate_ns"].pop(),
            lambda s: s["measurements"][0].__setitem__("predicate_ns_median", -1),
            lambda s: s["measurements"][0]["sample_positions"].__setitem__(0, -1),
            lambda s: s["measurements"].pop(),
            lambda s: s["measurements"].append(deepcopy(s["measurements"][0])),
            lambda s: s["groups"][0].__setitem__("accepted", -1),
            lambda s: s["groups"][0]["all_repeat_ns_distribution"].__setitem__("median", -1),
            lambda s: s["paired_comparisons"][0]["paired_repeat_time_ratio"].__setitem__("p90", -1),
            lambda s: s["paired_comparisons"][0]["transitions"][0].__setitem__("controls", 999),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                study = deepcopy(self.study)
                change(study)
                with self.assertRaises(ValueError):
                    verify_timing_evidence(self.spec, study)

    def test_seed_changes_are_detected_but_consistent_evidence_has_no_clock_authentication_claim(self):
        with self.assertRaises(ValueError):
            verify_timing_evidence(self.spec | {"seed": 72}, self.study)
        self.assertIn("clock authenticity is not verified", verify_timing_evidence(self.spec, self.study)["scope"])


if __name__ == "__main__":
    unittest.main()
