from copy import deepcopy
import unittest

from tick_trap.allocation_audit import allocation_audit
from tick_trap.certification_study import certification_study


class AllocationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = {"base": {"grid_points": 2}, "budget_scope": "per_control", "repeats": 1,
                    "strategies": ["sacbf_relaxed", "minimum", "sign", "auxiliary_sign"],
                    "tolerances": ["1e-12"], "budgets": [0, 8], "cases": [
                        {"name": "precision_before_auxiliary", "p": ["1.67", 0], "v": [-1, 0],
                         "nominal": [1, -1], "duration": 1, "a_max": 2,
                         "obstacles": [{"center": [0, 0], "radius": 1}]},
                        {"name": "lost_negative_witness", "p": [2, 0], "v": [-1, 0],
                         "nominal": ["0.5", 0], "duration": "2.9", "a_max": 1,
                         "obstacles": [{"center": [0, 0], "radius": 1}]},
                        {"name": "exact_tangent", "p": ["1.231168", 0], "v": ["-0.90112", 0],
                         "nominal": ["0.8704", 0], "duration": 1, "a_max": 2,
                         "obstacles": [{"center": [0, 0], "radius": "0.6"}]},
                        {"name": "outside_domain", "p": [1, 0], "v": [-5, 0],
                         "nominal": [0, 0], "duration": 1, "a_max": 1,
                         "obstacles": [{"center": [0, 0], "radius": 1}]}]}
        cls.study = certification_study(cls.spec)

    def target_index(self):
        return next(i for i, r in enumerate(self.study["measurements"])
                    if r["case_index"] == 0 and r["candidate_index"] == 0 and r["strategy"] == "minimum" and r["budget"] == 8)

    def test_precision_refinement_exhausts_shared_work_before_psi(self):
        report = allocation_audit(self.spec, self.study)
        target = next(r for r in report["measurements"] if r["case_index"] == 0 and r["candidate_index"] == 0
                      and r["strategy"] == "minimum" and r["budget"] == 8)
        h, psi = target["trace"]
        self.assertEqual((h["property"], h["assigned_budget"], h["certificate"]["status"]), ("h", 8, "safe"))
        self.assertEqual(h["certificate"]["subdivisions"], 8)
        self.assertEqual(h["sign_goal_subdivisions"], 0)
        self.assertEqual((psi["property"], psi["assigned_budget"], psi["certificate"]["status"]), ("psi", 0, "unknown"))
        self.assertEqual(psi["full_per_polynomial_certificate"]["status"], "safe")
        self.assertTrue(target["allocation_limited_control"])
        self.assertEqual(target["status"], "unknown")  # Counterfactual does not authorize execution.
        self.assertEqual(target["full_per_polynomial_status"], "accepted")

    def test_unknowns_are_partitioned_without_claiming_unresolvability(self):
        original = deepcopy(self.study)
        report = allocation_audit(self.spec, self.study)
        self.assertEqual(original, self.study)
        self.assertEqual(report["property_configurations"], len(self.study["measurements"]))
        for group in report["groups"]:
            self.assertEqual(group["allocation_limited_controls"]+group["unknown_at_full_per_polynomial_limits"], group["unknown"])
            self.assertEqual(sum(t["controls"] for t in group["full_to_allocated_transitions"]), group["controls"])
        for row in report["measurements"]:
            if row["trace"]:
                self.assertLessEqual(sum(t["certificate"]["subdivisions"] for t in row["trace"]), row["budget"])
                for trace in row["trace"]:
                    self.assertGreaterEqual(trace["remaining_budget"], 0)
        tangent = next(r for r in report["measurements"] if r["case"] == "exact_tangent"
                       and r["candidate_index"] == 0 and r["strategy"] == "auxiliary_sign" and r["budget"] == 8)
        self.assertEqual(tangent["independent_joint_status"], "safe")
        self.assertEqual(tangent["status"], "unknown")
        self.assertFalse(tangent["allocation_limited_control"])

    def test_sign_query_can_lose_a_negative_witness_through_allocation(self):
        report = allocation_audit(self.spec, self.study)
        target = next(r for r in report["measurements"] if r["case"] == "lost_negative_witness"
                      and r["candidate_index"] == 0 and r["strategy"] == "sign" and r["budget"] == 8)
        self.assertEqual(target["status"], "unknown")
        self.assertEqual(target["full_per_polynomial_status"], "rejected")
        self.assertEqual(target["trace"][0]["certificate"]["status"], "unknown")
        self.assertEqual(target["trace"][1]["assigned_budget"], 0)
        self.assertEqual(target["trace"][1]["full_per_polynomial_certificate"]["status"], "unsafe")

    def test_per_polynomial_scope_has_no_allocation_losses(self):
        spec = self.spec | {"budget_scope": "per_polynomial"}
        report = allocation_audit(spec, certification_study(spec))
        self.assertFalse(any(r["allocation_limited_control"] for r in report["measurements"]))
        self.assertFalse(any(g["allocation_limited_unknown_queries"] for g in report["groups"]))
        self.assertTrue(all(t["remaining_budget"] is None for r in report["measurements"] for t in r["trace"]))

    def test_rejects_missing_duplicated_extra_or_changed_measurements(self):
        target = self.target_index()
        changes = [
            lambda s: s["measurements"].pop(target),
            lambda s: s["measurements"].append(deepcopy(s["measurements"][target])),
            lambda s: s["measurements"][target].__setitem__("case_index", 3),
            lambda s: s["measurements"][target].__setitem__("candidate_index", True),
            lambda s: s["measurements"][target].__setitem__("action_exact", [0, 0]),
            lambda s: s["measurements"][target].__setitem__("budget", 7),
            lambda s: s["measurements"][target]["result"].__setitem__("status", "accepted"),
            lambda s: s["measurements"][target]["result"]["proofs"][0].__setitem__("lower_exact", "999"),
            lambda s: s["measurements"][target]["result"]["proofs"][0].__setitem__("goal", "sign"),
            lambda s: s["measurements"][target]["result"]["proofs"][0].__setitem__("subdivisions", 7),
            lambda s: s["measurements"][target]["result"]["proofs"][0].__setitem__("budget_exhausted", False),
            lambda s: s["measurements"][target].__setitem__("independent_reference_status", "unsafe"),
            lambda s: s["reference"][0]["candidates"][0]["independent_evidence"][0]["psi"].__setitem__("status", "unsafe"),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                study = deepcopy(self.study)
                change(study)
                with self.assertRaises(ValueError):
                    allocation_audit(self.spec, study)

    def test_evidence_order_is_irrelevant_but_candidate_order_is_checked(self):
        study = deepcopy(self.study)
        study["measurements"].reverse()
        self.assertEqual(allocation_audit(self.spec, self.study), allocation_audit(self.spec, study))
        study["reference"][0]["candidates"].reverse()
        with self.assertRaises(ValueError):
            allocation_audit(self.spec, study)

    def test_configuration_mismatch_is_rejected(self):
        for change in ({"budget_scope": "per_polynomial"}, {"budgets": [0, 4]}, {"repeats": 2}, {"seed": 123},
                       {"strategies": ["minimum"]}, {"tolerances": ["1e-6"]}, {"unexpected": 1},
                       {"base": {"grid_points": 2, "duration_typo": "0.1"}}):
            with self.assertRaises(ValueError):
                allocation_audit(self.spec | change, self.study)

    def test_json_types_cannot_disguise_boolean_or_fractional_work_counts(self):
        for value in (False, 0.0):
            study = deepcopy(self.study)
            target = next(r for r in study["measurements"] if r["strategy"] == "sign" and r["budget"] == 0)
            target["result"]["subdivisions"] = value
            with self.assertRaises(ValueError):
                allocation_audit(self.spec, study)

    def test_algebraic_comparator_is_replayed_without_a_fictitious_split_budget(self):
        spec = self.spec | {"strategies": ["sturm", "auxiliary_sign"]}
        study = certification_study(spec)
        report = allocation_audit(spec, study)
        exact = [r for r in report["measurements"] if r["strategy"] == "sturm"]
        self.assertTrue(exact)
        self.assertTrue(all(r["budget"] is None and not r["trace"] and r["status"] != "unknown" for r in exact))
        for change in (
                lambda r: r["result"]["proofs"][0]["evidence"].__setitem__("status", "unsafe"),
                lambda r: r["result"].__setitem__("work_scope", "equal subdivision work"),
                lambda r: r.__setitem__("budget", 0)):
            tampered = deepcopy(study)
            row = next(r for r in tampered["measurements"] if r["strategy"] == "sturm"
                       and r["result"]["proofs"][0]["status"] == "safe")
            change(row)
            with self.assertRaises(ValueError):
                allocation_audit(spec, tampered)


if __name__ == "__main__":
    unittest.main()
