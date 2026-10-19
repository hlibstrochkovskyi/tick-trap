import copy
import unittest

from tick_trap.planar_experiments import PlanarConfig, run_planar
from tick_trap.verification import VerificationError, verify_planar_runs


class VerificationTests(unittest.TestCase):
    def run_data(self):
        return run_planar(PlanarConfig(method="backup_candidates", p=(-2, 0), v=(1, 0),
                                       horizon="0.3", max_candidates=0))

    def test_saved_prefix_reuse_is_verified_from_original_proof_intervals(self):
        result = verify_planar_runs([self.run_data()])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["executed_holds"], 3)
        self.assertEqual(result["retained_plans"], 3)
        self.assertEqual(result["unsafe_intervals"], 0)

    def test_rejects_changed_commands_states_witnesses_and_prefixes(self):
        original = self.run_data()
        changes = [
            lambda r: r["records"][0]["action_exact"].__setitem__(0, "0"),
            lambda r: r["records"][0]["end_state"]["p_exact"].__setitem__(0, "-10"),
            lambda r: r["records"][0]["details"]["retained_plan"]["original_proofs"][0]["certificates"][0].__setitem__("lower_exact", "100"),
            lambda r: r["records"][0]["details"]["retained_plan"].__setitem__("consumed_steps", 0),
            lambda r: r.__setitem__("completed_safe_horizon", False),
        ]
        for change in changes:
            altered = copy.deepcopy(original)
            change(altered)
            with self.assertRaises(VerificationError):
                verify_planar_runs([altered])

    def test_renewed_and_terminal_policies_are_replayed(self):
        configs = [PlanarConfig(method="backup_candidates", p=(-2, 0), v=(0, 0), goal=(-2, 0), horizon="0.2"),
                   PlanarConfig(method="backup_candidates", p=(-2, 0), v=(0, 0), horizon="0.2", max_candidates=0)]
        result = verify_planar_runs([run_planar(config) for config in configs])
        self.assertEqual(result["retained_plans"], 4)

    def test_verified_report_can_contain_a_collision_witness(self):
        run = run_planar(PlanarConfig(method="endpoint_candidates", p=("0.04", 0), v=(-1, 0),
                                      obstacles=({"center": [-1, 0], "radius": 1},), nominal_policy="constant",
                                      nominal=(10, 0), a_max="10", duration="0.2", horizon="0.2"))
        result = verify_planar_runs([run])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["unsafe_intervals"], 1)

    def test_sampling_aware_conditions_and_continuous_auxiliary_paths_are_replayed(self):
        runs = [run_planar(PlanarConfig(method=method, p=(-2, 0), v=(1, 0), goal=(-2, 0), horizon="0.3"))
                for method in ("sacbf_candidates", "sacbf_relaxed_candidates")]
        result = verify_planar_runs(runs)
        self.assertEqual(result["sampling_aware_holds"], 6)
        self.assertEqual(result["auxiliary_safe_checks"], 6)
        self.assertEqual(result["auxiliary_unknown_checks"], 0)
        original = runs[0]
        changes = [
            lambda r: r["records"][0]["details"]["checked"][-1]["sampling_assessments"][0].__setitem__("second_derivative_bound_exact", "0"),
            lambda r: r["records"][0]["details"]["checked"][-1]["sampling_assessments"][0].__setitem__("accepted", False),
            lambda r: r["records"][0]["details"]["checked"][-1].__setitem__("sampling_assessments", []),
            lambda r: r["records"][0]["details"]["checked"][-1]["action_exact"].__setitem__(0, "100"),
            lambda r: r["records"][0]["details"]["checked"][-1]["margins_exact"].__setitem__(0, "100"),
        ]
        for change in changes:
            altered = copy.deepcopy(original)
            change(altered)
            with self.assertRaises(VerificationError):
                verify_planar_runs([altered])

    def test_high_order_reference_proofs_replay_their_declared_goal(self):
        runs = [run_planar(PlanarConfig(method=method, p=(-2, 0), v=(1, 0), goal=(-2, 0), horizon="0.3"))
                for method in ("high_order_trajectory_candidates", "high_order_sign_candidates")]
        result = verify_planar_runs(runs)
        self.assertEqual(result["high_order_reference_holds"], 6)
        self.assertEqual(result["high_order_reference_certificates"], 12)
        self.assertEqual([r["action_exact"] for r in runs[0]["records"]], [r["action_exact"] for r in runs[1]["records"]])
        for field, value in (("goal", "minimum"), ("lower_exact", "100"), ("precision_reached", None),
                             ("budget_exhausted", True), ("stopping_reason", "budget_exhausted"), ("subdivisions", 257)):
            altered = copy.deepcopy(runs[1])
            altered["records"][0]["details"]["checked"][-1]["auxiliary_certificates"][0][field] = value
            with self.assertRaises(VerificationError):
                verify_planar_runs([altered])
        for change in (
            lambda c: c.__setitem__("auxiliary_certificates", []),
            lambda c: c["auxiliary_certificates"][0].__setitem__("status", "unknown"),
            lambda c: c.__setitem__("accepted", False),
        ):
            altered = copy.deepcopy(runs[1])
            change(altered["records"][0]["details"]["checked"][-1])
            with self.assertRaises(VerificationError):
                verify_planar_runs([altered])


if __name__ == "__main__":
    unittest.main()
