from copy import deepcopy
import unittest

from tick_trap.certification_study import certification_study
from tick_trap.minimum_audit import minimum_reference_audit
from tick_trap.representation_study import _decision, representation_study, verify_representation_study


class RepresentationStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = {"base": {"grid_points": 2}, "strategies": ["auxiliary_sign"], "budgets": [0], "repeats": 1,
                "cases": [{"name": "approach", "p": ["1.67", 0], "v": [-1, 0], "nominal": [1, -1],
                           "duration": 1, "a_max": 2, "obstacles": [{"center": [0, 0], "radius": 1}]}]}
        cls.catalog = minimum_reference_audit(spec, certification_study(spec), {"budgets": [0], "tolerances": ["1e-12"]})
        cls.settings = {"scales": ["1e-6", "1", "1e6"], "tolerances": ["1e-12"], "budgets": [0, 8],
                        "time_bases": ["physical", "unit_interval"], "methods": ["bernstein_minimum", "bernstein_sign", "stationary_minimum"]}
        cls.study = representation_study(cls.catalog, cls.settings)

    def test_unresolved_properties_cannot_be_consumed_or_promoted_by_joint_classification(self):
        for values, expected in ((["safe", "unknown"], "unknown"), (["unknown", "unknown"], "unknown"),
                                 (["unknown", "unsafe"], "rejected"), (["safe", "safe"], "accepted")):
            self.assertEqual(_decision(iter(values)), expected)
        for group in self.study["groups"]:
            self.assertEqual(sum(t["controls"] for t in group["control_transitions"]), group["controls"])
            self.assertEqual(sum(group[k] for k in ("accepted_safe_controls", "rejected_unsafe_controls",
                                                   "unknown_safe_controls", "unknown_unsafe_controls")), group["controls"])

    def test_equivalent_widths_and_pure_time_substitution_preserve_certificates(self):
        for group in self.study["groups"]:
            if group["tolerance_policy"] == "equivalent_width":
                self.assertEqual(group["same_converted_certificate"], group["polynomials"])
                self.assertTrue(all(t["baseline"] == t["represented"] for t in group["control_transitions"]))
        for query in self.study["queries"]:
            for representation in query["representations"]:
                for evaluation in representation["evaluations"]:
                    self.assertTrue(all(p["time_substitution_matches"] for p in evaluation["policies"].values()))
        checked = verify_representation_study(self.catalog, self.settings, self.study)
        self.assertEqual(checked["groups"], 72)
        self.assertEqual(checked["controls"], self.catalog["controls"])

    def test_changed_or_missing_source_evidence_and_property_uses_are_rejected(self):
        changes = [lambda c: c["queries"][0]["complete_sign_reference"].__setitem__("status", "unknown"),
                   lambda c: c["queries"][0]["uses"].append(deepcopy(c["queries"][0]["uses"][0])),
                   lambda c: c["queries"][0].__setitem__("query_index", True),
                   lambda c: c.__setitem__("property_uses", 999)]
        for change in changes:
            catalog = deepcopy(self.catalog)
            change(catalog)
            with self.assertRaises(ValueError):
                representation_study(catalog, self.settings)

    def test_regeneration_rejects_changed_tolerance_bounds_decisions_and_work(self):
        changes = [lambda s: s["groups"][0].__setitem__("accepted_safe_controls", 999),
                   lambda s: s["queries"][0]["representations"][0].__setitem__("time_factor_exact", "999"),
                   lambda s: s["queries"][0]["representations"][0]["evaluations"][0]["policies"]["fixed_absolute"].__setitem__("tolerance_exact", "999"),
                   lambda s: s["queries"][0]["representations"][0]["evaluations"][0]["policies"]["equivalent_width"]["certificate"].__setitem__("subdivisions", 999)]
        for change in changes:
            study = deepcopy(self.study)
            change(study)
            with self.assertRaises(ValueError):
                verify_representation_study(self.catalog, self.settings, study)

    def test_invalid_or_duplicate_settings_are_rejected(self):
        for change in ({"scales": []}, {"scales": [0]}, {"scales": [-1]}, {"scales": ["0.1", "1/10"]},
                       {"tolerances": [0]}, {"budgets": [True]}, {"budgets": [0, 0]}, {"methods": [{}]},
                       {"time_bases": [{}]}, {"methods": ["unknown"]}, {"extra": 1}):
            with self.assertRaises(ValueError):
                representation_study(self.catalog, self.settings | change)


if __name__ == "__main__":
    unittest.main()
