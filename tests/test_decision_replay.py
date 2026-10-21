from copy import deepcopy
import unittest

from tick_trap.decision_replay import scientific_planar_record, verify_planar_decisions
from tick_trap.planar_control import PLANAR_METHODS
from tick_trap.planar_experiments import PlanarConfig, run_planar
from tick_trap.verification import VerificationError, verify_planar_runs


class DecisionReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {m: run_planar(PlanarConfig(method=m, p=(-2, 0), v=(0, 0), goal=(-2, 0), horizon="0.1"))
                    for m in PLANAR_METHODS}

    def test_every_planar_controller_reproduces_without_mutating_the_saved_record(self):
        runs = list(self.runs.values())
        original = deepcopy(runs)
        result = verify_planar_decisions(runs)
        self.assertEqual(runs, original)
        self.assertEqual(result["runs"], len(PLANAR_METHODS))
        self.assertEqual(result["decision_updates"], len(PLANAR_METHODS))
        self.assertEqual(result["physical_artifact_replay"]["executed_holds"], len(PLANAR_METHODS))
        self.assertEqual(len(result["groups"]), len(PLANAR_METHODS))

    def test_declared_cohort_checks_missing_reordered_or_replaced_configurations(self):
        runs = list(self.runs.values())
        grid = {"base": {"p": [-2, 0], "v": [0, 0], "goal": [-2, 0], "horizon": "0.1"},
                "grid": {"method": list(PLANAR_METHODS)}}
        self.assertTrue(verify_planar_decisions(runs, grid)["declared_coverage_checked"])
        for altered in (runs[:-1], list(reversed(runs)), [runs[0]]*len(runs)):
            with self.assertRaisesRegex(VerificationError, "Declared planar cohort"):
                verify_planar_decisions(altered, grid)
        configs = [r["config"] for r in runs]
        self.assertTrue(verify_planar_decisions(runs, configs)["declared_coverage_checked"])
        self.assertTrue(verify_planar_decisions(runs[:1], configs[0])["declared_coverage_checked"])

    def test_safe_trajectory_does_not_validate_fabricated_endpoint_segment_or_zero_order_evidence(self):
        for method in ("endpoint_candidates", "segment_candidates", "zocbf_candidates"):
            run = deepcopy(self.runs[method])
            run["records"][0]["details"]["checked"][-1]["margins_exact"][0] = "999"
            self.assertEqual(verify_planar_runs([run])["status"], "verified")
            with self.assertRaisesRegex(VerificationError, "margins_exact"):
                verify_planar_decisions([run])
        run = deepcopy(self.runs["hocbf"])
        run["records"][0]["details"]["continuous_cost_exact"] = "999"
        self.assertEqual(verify_planar_runs([run])["status"], "verified")
        with self.assertRaisesRegex(VerificationError, "continuous_cost_exact"):
            verify_planar_decisions([run])

    def test_rejected_candidate_prefix_and_its_order_are_verified(self):
        run = run_planar(PlanarConfig(method="sacbf_candidates", p=("-0.6", "0.3"), v=(0, 0),
                                      nominal_policy="constant", nominal=("2.6", "0.4"), horizon="0.1"))
        self.assertGreater(len(run["records"][0]["details"]["checked"]), 1)
        for change in (lambda checked: checked.pop(0),
                       lambda checked: checked[0]["margins_exact"].__setitem__(0, "999"),
                       lambda checked: checked.insert(0, checked.pop(1))):
            altered = deepcopy(run)
            change(altered["records"][0]["details"]["checked"])
            self.assertEqual(verify_planar_runs([altered])["status"], "verified")
            with self.assertRaises(VerificationError):
                verify_planar_decisions([altered])

    def test_failed_search_labels_and_initialization_are_reproduced(self):
        cases = [
            (dict(method="trajectory_candidates", max_candidates=0), "budget_exhausted"),
            (dict(method="hocbf", p=(2, 0), v=(-1, 0), a_max="0.1", obstacles=({"center": [0, 0], "radius": 1},)), "infeasible"),
            (dict(method="hocbf", p=(-2, 0), v=(10, 0)), "outside_domain"),
            (dict(method="backup_candidates", v=("1/3", 0)), "initialization_failed"),
            (dict(method="nominal", p=(0, 0)), "initially_unsafe"),
            (dict(method="endpoint_candidates", p=("1.01", 0), v=(-1, 0), a_max="0.1",
                  obstacles=({"center": [0, 0], "radius": 1},)), "search_exhausted"),
            (dict(method="trajectory_candidates", p=("0.04", 0), v=(-1, 0),
                  obstacles=({"center": [-1, 0], "radius": 1},), nominal_policy="constant", nominal=(10, 0),
                  a_max="10", duration="0.2", horizon="0.2", max_subdivisions=0), "uncertified"),
        ]
        for changes, termination in cases:
            run = run_planar(PlanarConfig(**(dict(p=(-2, 0), v=(0, 0), horizon="0.1") | changes)))
            self.assertEqual(run["termination"], termination)
            self.assertEqual(verify_planar_decisions([run])["status"], "verified")
        altered = run_planar(PlanarConfig(method="trajectory_candidates", max_candidates=0, horizon="0.1"))
        altered["termination"] = altered["records"][0]["decision"] = "infeasible"
        self.assertEqual(verify_planar_runs([altered])["status"], "verified")
        with self.assertRaises(VerificationError):
            verify_planar_decisions([altered])

    def test_nominal_policy_task_flags_viability_and_json_types_are_not_hidden(self):
        changes = [lambda r: r["records"][0]["nominal_exact"].__setitem__(0, "999"),
                   lambda r: r.__setitem__("goal_reached_at_end", False),
                   lambda r: r.__setitem__("goal_first_time_exact", "0.1"),
                   lambda r: r.__setitem__("initial_viability", "unknown"),
                   lambda r: r["records"][0]["details"].__setitem__("candidate_count", True)]
        for change in changes:
            run = deepcopy(self.runs["endpoint_candidates"])
            change(run)
            with self.assertRaises(VerificationError):
                verify_planar_decisions([run])

    def test_only_the_documented_clock_and_display_locations_are_excluded(self):
        run = deepcopy(self.runs["endpoint_candidates"])
        expected = verify_planar_decisions([run])
        run["solve_ns_total"] = 999999
        run["records"][0]["solve_ns"] = 999999
        run["records"][0]["deadline_missed"] = True
        run["deadline_misses"] = 1
        run["minimum_clearance_estimate"] = -999.0
        run["records"][0]["obstacles"][0]["minimum_estimate"] = -999.0
        run["records"][0]["action"] = [999.0, 999.0]
        self.assertEqual(verify_planar_decisions([run]), expected)
        run["records"][0]["details"]["solve_ns"] = 123
        with self.assertRaisesRegex(VerificationError, "details.solve_ns"):
            verify_planar_decisions([run])
        self.assertIn("p", scientific_planar_record(run)["config"])

    def test_valid_comparison_survives_an_offline_unknown_and_uncertified_execution_still_stops(self):
        base = dict(p=("-0.3", "1.06"), v=(1, 0), obstacles=({"center": [0, 0], "radius": 1},),
                    nominal_policy="constant", nominal=(0, 0), lambda1="3", a_max="1", duration="1", horizon="2",
                    max_subdivisions=0, oracle_max_subdivisions=0)
        comparison = run_planar(PlanarConfig(method="auxiliary_sign_candidates", max_candidates=1, **base))
        unknown = run_planar(PlanarConfig(method="nominal", **base))
        result = verify_planar_decisions([comparison, unknown])
        self.assertEqual(result["physical_artifact_replay"]["derived_safe_offline_unknown"], 1)
        self.assertTrue(comparison["completed_safe_horizon"])
        self.assertEqual(unknown["termination"], "oracle_unresolved")

    def test_a_faithful_collision_trace_is_verified_without_being_called_safe(self):
        run = run_planar(PlanarConfig(method="endpoint_candidates", p=("0.04", 0), v=(-1, 0),
                                      obstacles=({"center": [-1, 0], "radius": 1},), nominal_policy="constant",
                                      nominal=(10, 0), a_max="10", duration="0.2", horizon="0.2"))
        result = verify_planar_decisions([run])
        self.assertEqual(result["physical_artifact_replay"]["unsafe_intervals"], 1)
        self.assertEqual(result["per_run"][0]["termination"], "collision_interval")
        self.assertFalse(result["per_run"][0]["completed_safe_horizon"])

    def test_backup_reuse_and_terminal_holds_reproduce_stateful_decisions(self):
        run = run_planar(PlanarConfig(method="backup_candidates", p=(-2, 0), v=(1, 0),
                                      horizon="0.6", max_candidates=0))
        verified = verify_planar_decisions([run])
        self.assertEqual(verified["per_run"][0]["control_sources"], {"stored_continuation": 5, "terminal_hold": 1})
        self.assertEqual(verified["decision_updates"], 6)


if __name__ == "__main__":
    unittest.main()
