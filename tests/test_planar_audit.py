import unittest

from tick_trap.planar_audit import audit_case, audit_cases


class CandidateAuditTests(unittest.TestCase):
    def test_exact_curved_collision_witness_is_admitted_by_chord(self):
        result = audit_case("curved", ("0.04", 0), (-1, 0), (10, 0),
                            [{"center": [-1, 0], "radius": 1}], "0.2", 10)
        nominal = result["candidates"][0]
        self.assertEqual(nominal["action_exact"], ["10", "0"])
        self.assertTrue(nominal["predicates"]["endpoint"])
        self.assertTrue(nominal["predicates"]["segment"])
        self.assertEqual(nominal["trajectory_status"], "unsafe")
        self.assertGreater(result["counts"]["segment"]["unsafe_admitted"], 0)

    def test_buffer_exclusions_are_measured_on_matched_safe_controls(self):
        result = audit_case("safe", ("1.2", 0), ("-0.1", 0), (0, 0),
                            [{"center": [0, 0], "radius": 1}], "0.1", 2)
        self.assertEqual(result["initial_braking"]["viability"], "certified")
        self.assertEqual(result["truth_counts"]["safe"], result["candidate_count"])
        self.assertGreater(result["counts"]["zocbf"]["safe_excluded"], 0)
        self.assertEqual(result["counts"]["zocbf"]["unsafe_admitted"], 0)

    def test_domain_and_truth_unknown_are_not_control_rejections(self):
        result = audit_case("tangent", ("-0.3", 1), (1, 0), (0, 0),
                            [{"center": [0, 0], "radius": 1}], 1, 1, max_subdivisions=0)
        self.assertGreater(result["truth_counts"]["unknown"], 0)
        self.assertFalse(result["hocbf_applicable"])
        self.assertEqual(result["counts"]["hocbf"]["safe_excluded"], 0)
        self.assertEqual(result["counts"]["hocbf"]["applicable"], 0)
        self.assertTrue(all(r["predicates"]["hocbf"] is None for r in result["candidates"]))
        for method in ("sacbf", "sacbf_relaxed"):
            self.assertEqual(result["counts"][method]["applicable"], 0)
            self.assertEqual(result["counts"][method]["safe_excluded"], 0)

    def test_sampling_aware_audit_is_safe_and_relaxation_is_a_superset(self):
        result = audit_case("safe", ("1.2", 0), ("-0.1", 0), (0, 0),
                            [{"center": [0, 0], "radius": 1}], "0.1", 2)
        for method in ("sacbf", "sacbf_relaxed"):
            self.assertEqual(result["counts"][method]["unsafe_admitted"], 0)
            self.assertGreater(result["counts"][method]["safe_admitted"], 0)
        for row in result["candidates"]:
            if row["predicates"]["sacbf"]:
                self.assertTrue(row["predicates"]["sacbf_relaxed"])
        self.assertGreater(result["counts"]["sacbf_relaxed"]["safe_admitted"], result["counts"]["zocbf"]["safe_admitted"])

    def test_invalid_catalog_rejected(self):
        for spec in [{}, {"cases": [1]}, {"base": [], "cases": [{}]}, {"unexpected": 1}]:
            with self.assertRaises(ValueError):
                audit_cases(spec)


if __name__ == "__main__":
    unittest.main()
