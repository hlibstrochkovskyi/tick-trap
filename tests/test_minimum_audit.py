from copy import deepcopy
import unittest

from tick_trap.certification_study import certification_study
from tick_trap.minimum_audit import minimum_reference_audit, verify_minimum_reference_audit


class MinimumAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = {"base": {"grid_points": 2}, "strategies": ["auxiliary_sign", "sturm"],
                    "budgets": [0], "repeats": 1, "cases": [
                        {"name": "duplicate_obstacles", "p": ["1.67", 0], "v": [-1, 0], "nominal": [1, -1],
                         "duration": 1, "a_max": 2, "obstacles": [{"center": [0, 0], "radius": 1}]*2},
                        {"name": "outside_domain", "p": [1, 0], "v": [-5, 0], "nominal": [0, 0],
                         "duration": 1, "a_max": 2, "obstacles": [{"center": [0, 0], "radius": 1}]}]}
        cls.study = certification_study(cls.spec)
        cls.settings = {"tolerances": ["1e-6"], "budgets": [0, 8]}
        cls.audit = minimum_reference_audit(cls.spec, cls.study, cls.settings)

    def test_deduplication_preserves_all_property_uses_and_domain_exclusions(self):
        audit = self.audit
        self.assertEqual(audit["cases"], 2)
        self.assertEqual(audit["applicable_cases"], 1)
        self.assertEqual(audit["controls"], self.study["reference"][0]["candidate_count"])
        self.assertEqual(audit["property_uses"], audit["controls"]*4)
        self.assertEqual(sum(len(q["uses"]) for q in audit["queries"]), audit["property_uses"])
        self.assertLess(audit["unique_queries"], audit["property_uses"])
        for group in audit["groups"]:
            self.assertEqual(group["overlapping_matched_enclosures"], audit["unique_queries"])
            self.assertEqual(group["overlapping_archived_enclosures"], audit["unique_queries"])
        self.assertEqual(verify_minimum_reference_audit(self.spec, self.study, self.settings, audit)["status"], "verified")

    def test_original_high_precision_minimum_tampering_is_rejected(self):
        study = deepcopy(self.study)
        study["reference"][0]["candidates"][0]["certificates"][0]["lower_exact"] = "-999"
        with self.assertRaisesRegex(ValueError, "Archived Bernstein minimum"):
            minimum_reference_audit(self.spec, study, self.settings)

    def test_regeneration_rejects_changed_bounds_root_coverage_statuses_and_counts(self):
        changes = [lambda a: a["queries"][0]["assessments"][0]["stationary"].__setitem__("lower_exact", "999"),
                   lambda a: a["queries"][0]["assessments"][0]["stationary"].__setitem__("stationary_roots_open", 99),
                   lambda a: a["queries"][0]["assessments"][0]["matched_bernstein"].__setitem__("status", "unknown"),
                   lambda a: a["queries"][0]["uses"].pop(),
                   lambda a: a["groups"][0].__setitem__("unique_queries", 999)]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                altered = deepcopy(self.audit)
                change(altered)
                with self.assertRaises(ValueError):
                    verify_minimum_reference_audit(self.spec, self.study, self.settings, altered)

    def test_invalid_or_duplicated_numerical_settings_are_rejected(self):
        for change in ({"tolerances": []}, {"budgets": []}, {"budgets": [True]}, {"budgets": [-1]},
                       {"tolerances": [0]}, {"tolerances": ["0.1", "1/10"]}, {"budgets": [0, 0]}, {"unknown": 1}):
            with self.assertRaises(ValueError):
                minimum_reference_audit(self.spec, self.study, self.settings | change)


if __name__ == "__main__":
    unittest.main()
