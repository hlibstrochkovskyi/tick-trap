import copy
import unittest
from unittest.mock import patch

from tick_trap.planar_control import decide_planar
from tick_trap.planar_experiments import PlanarConfig, run_planar
from tick_trap.verification import VerificationError, verify_planar_runs


class ExecutionEvidenceTests(unittest.TestCase):
    def config(self, **changes):
        return PlanarConfig(**(dict(method="auxiliary_sign_candidates", p=("-0.3", "1.06"), v=(1, 0),
                                   obstacles=({"center": [0, 0], "radius": 1},), nominal_policy="constant",
                                   nominal=(0, 0), lambda1="3", a_max="1", duration="1", horizon="2",
                                   max_subdivisions=0, oracle_max_subdivisions=0, max_candidates=1) | changes))

    def test_valid_comparison_continues_without_relabeling_oracle_unknown(self):
        run = run_planar(self.config())
        self.assertEqual(run["executed_steps"], 2)
        self.assertEqual(run["records"][0]["continuous_status"], "unknown")
        self.assertEqual(run["records"][0]["execution_status"], "safe")
        self.assertEqual(run["records"][0]["execution_basis"], "online_auxiliary_comparison")
        self.assertEqual(run["observed_continuous_status"], "unknown")
        self.assertEqual(run["certified_execution_status"], "safe")
        self.assertTrue(run["completed_safe_horizon"])
        self.assertFalse(run["oracle_confirmed_horizon"])
        self.assertEqual(verify_planar_runs([run])["derived_safe_offline_unknown"], 1)

    def test_no_comparison_proof_stops_at_unknown(self):
        run = run_planar(self.config(method="nominal", max_candidates=None))
        self.assertEqual(run["termination"], "oracle_unresolved")
        self.assertEqual(run["executed_steps"], 1)
        self.assertEqual(run["records"][0]["execution_status"], "unknown")
        self.assertFalse(run["completed_safe_horizon"])
        verify_planar_runs([run])

    def test_unresolved_online_tangency_is_not_authority_to_execute(self):
        run = run_planar(self.config(p=("1.231168", 0), v=("-0.90112", 0),
                                    nominal=("0.8704", 0), lambda1="2", a_max="2",
                                    obstacles=({"center": [0, 0], "radius": "0.6"},)))
        self.assertEqual(run["executed_steps"], 0)
        self.assertFalse(run["completed_safe_horizon"])

    def test_replay_rejects_changed_proofs_and_fabricated_execution_classifications(self):
        original = run_planar(self.config())
        changes = [
            lambda r: r["records"][0].__setitem__("continuous_status", "safe"),
            lambda r: r["records"][0].__setitem__("execution_status", "unknown"),
            lambda r: r["records"][0].__setitem__("execution_basis", "offline_geometric"),
            lambda r: r.__setitem__("oracle_confirmed_horizon", True),
            lambda r: r.__setitem__("observed_continuous_status", "safe"),
            lambda r: r["records"][0]["details"]["checked"][-1]["auxiliary_certificates"][0].__setitem__("status", "unknown"),
        ]
        for change in changes:
            altered = copy.deepcopy(original)
            change(altered)
            with self.assertRaises(VerificationError):
                verify_planar_runs([altered])
        altered = copy.deepcopy(original)
        altered["config"]["method"] = "nominal"
        # Removing all new fields does not permit continuing an old-style unknown.
        for record in altered["records"]:
            record.pop("execution_status")
        with self.assertRaises(VerificationError):
            verify_planar_runs([altered])

    def test_invalid_online_evidence_fails_closed_in_runner(self):
        def corrupt(*args, **kwargs):
            decision = decide_planar(*args, **kwargs)
            decision.details["checked"][-1]["geometric_implications"][0]["duration_exact"] = "99"
            return decision
        with patch("tick_trap.planar_experiments.decide_planar", side_effect=corrupt):
            with self.assertRaises(VerificationError):
                run_planar(self.config())

    def test_offline_replay_checks_its_own_budget_and_goal(self):
        original = run_planar(self.config(oracle_max_subdivisions=4096))
        self.assertGreater(original["records"][0]["obstacles"][0]["subdivisions"], 0)
        altered = copy.deepcopy(original)
        altered["config"]["oracle_max_subdivisions"] = 0
        with self.assertRaisesRegex(VerificationError, "Offline certificate exceeds"):
            verify_planar_runs([altered])
        altered = copy.deepcopy(original)
        altered["records"][0]["obstacles"][0]["goal"] = "sign"
        with self.assertRaisesRegex(VerificationError, "Incorrect certificate goal"):
            verify_planar_runs([altered])

    def test_a_negative_witness_cannot_be_overridden(self):
        # Deliberately inconsistent mocked proof authority tests the explicit guard.
        config = self.config(method="nominal", max_candidates=None, p=(2, 0), v=(-1, 0),
                             lambda1="2", duration="2.9", horizon="2.9")
        with patch("tick_trap.planar_experiments.validate_online_comparison", return_value="mock_invalid_proof"):
            with self.assertRaisesRegex(ArithmeticError, "contradicts"):
                run_planar(config)


if __name__ == "__main__":
    unittest.main()
