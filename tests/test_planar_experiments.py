import unittest
from fractions import Fraction as F

from tick_trap.dynamics import Circle, PlanarState
from tick_trap.planar_experiments import PlanarConfig, braking_continuation, load_planar_grid, run_planar


class PlanarExperimentTests(unittest.TestCase):
    def test_backup_plan_certifies_a_sufficient_future(self):
        state = PlanarState((-2, 0), (1, 0))
        obstacles = [Circle((0, 0), "0.5")]
        plan = braking_continuation(state, obstacles, "0.1", 2)
        self.assertEqual(plan["viability"], "certified")
        self.assertEqual(plan["steps"], 5)
        for piece in plan["pieces"]:
            state = state.at(tuple(map(F, piece["action_exact"])), F(piece["duration_exact"]))
        self.assertEqual(state.v, (0, 0))
        # This particular braking plan collides; the full viability question is
        # still unknown because steering was not ruled out.
        failed = braking_continuation(PlanarState(("1.01", 0), (-10, 0)), obstacles, "0.1", 2)
        self.assertEqual(failed["plan_status"], "unsafe")
        self.assertEqual(failed["viability"], "unknown")

    def test_stopping_plan_obeys_command_lattice_for_unequal_velocities(self):
        state = PlanarState((-10, -10), ("1.13", "0.47"))
        plan = braking_continuation(state, [], "0.1", 2, command_quantum="0.1")
        self.assertEqual(plan["viability"], "certified")
        self.assertLessEqual(len(plan["pieces"]), 5)
        for piece in plan["pieces"]:
            action = tuple(map(F, piece["action_exact"]))
            self.assertTrue(all(abs(u) <= 2 and (u/F("0.1")).denominator == 1 for u in action))
            self.assertEqual(F(piece["duration_exact"]), piece["steps"]*F("0.1"))
            state = state.at(action, F(piece["duration_exact"]))
        self.assertEqual(state.v, (0, 0))
        unresolved = braking_continuation(PlanarState((-10, 0), ("1.131", 0)), [], "0.1", 2, command_quantum="0.1")
        self.assertEqual(unresolved["viability"], "unknown")
        self.assertEqual(unresolved["plan_status"], "not_constructed")

    def test_curved_endpoint_collision_in_rollout(self):
        config = PlanarConfig(method="endpoint_candidates", p=("0.04", 0), v=(-1, 0),
                              obstacles=({"center": [-1, 0], "radius": 1},), nominal_policy="constant",
                              nominal=(10, 0), a_max="10", duration="0.2", horizon="0.2")
        result = run_planar(config)
        self.assertTrue(result["sampled_safe_observed"])
        self.assertTrue(result["collision_observed"])
        self.assertEqual(result["termination"], "collision_interval")

    def test_safe_multi_obstacle_rollout_and_goal_metric(self):
        config = PlanarConfig(p=(-2, 0), v=(0, 0), goal=(-2, 0), horizon="0.2",
                              obstacles=({"center": [0, 0], "radius": "0.5"},
                                         {"center": [0, 2], "radius": "0.5"}))
        result = run_planar(config)
        self.assertTrue(result["completed_safe_horizon"])
        self.assertEqual(result["initial_viability"], "certified")
        self.assertTrue(result["goal_reached_at_end"])
        self.assertEqual(result["executed_steps"], 2)
        self.assertEqual(result["goal_first_time_exact"], "0")
        self.assertEqual(len(result["records"][0]["obstacles"]), 2)

    def test_search_exhaustion_has_no_unverified_fallback(self):
        result = run_planar(PlanarConfig(p=("1.01", 0), v=(-100, 0), duration="0.01", horizon="0.01",
                                         a_max="1", obstacles=({"center": [0, 0], "radius": 1},)))
        self.assertEqual(result["termination"], "search_exhausted")
        self.assertEqual(result["executed_steps"], 0)
        self.assertFalse(result["completed_safe_horizon"])
        self.assertEqual(result["observed_continuous_status"], "not_executed")
        self.assertNotIn("action_exact", result["records"][0])

    def test_initial_viability_does_not_use_wall_formula(self):
        result = run_planar(PlanarConfig(p=(0, 0), v=(0, 0), horizon="0.1",
                                         obstacles=({"center": [0, 0], "radius": 1},)))
        self.assertEqual(result["termination"], "initially_unsafe")
        self.assertEqual(result["initial_viability"], "unknown")
        self.assertFalse(result["initial_geometric_safe"])

    def test_empty_obstacle_scene_is_valid(self):
        result = run_planar(PlanarConfig(obstacles=(), horizon="0.1"))
        self.assertTrue(result["completed_safe_horizon"])
        self.assertIsNone(result["minimum_barrier_lower_exact"])

    def test_grid_and_configuration_validation(self):
        configs = list(load_planar_grid({"base": {"horizon": "1"},
                                        "grid": {"method": ["hocbf", "trajectory_candidates"], "duration": ["0.1", "0.2"]}}))
        self.assertEqual(len(configs), 4)
        for kwargs in [{"duration": "0.3"}, {"grid_points": True}, {"gamma": 2},
                       {"max_subdivisions": -1}, {"command_quantum": "3"}]:
            with self.assertRaises(ValueError):
                PlanarConfig(**kwargs)
        for spec in [{"base": []}, {"grid": {"p": []}}, {"base": {"typo": 1}}]:
            with self.assertRaises(ValueError):
                list(load_planar_grid(spec))

    def test_retained_plan_finishes_when_stateless_search_has_no_budget(self):
        for method in ["trajectory_candidates", "backup_candidates"]:
            result = run_planar(PlanarConfig(method=method, p=(-2, 0), v=(1, 0), horizon="1", max_candidates=0))
            if method == "trajectory_candidates":
                self.assertEqual(result["termination"], "budget_exhausted")
                self.assertEqual(result["executed_steps"], 0)
                self.assertIsNone(result["retained_continuation_after_every_update"])
            else:
                self.assertTrue(result["completed_safe_horizon"])
                self.assertTrue(result["retained_continuation_after_every_update"])
                self.assertEqual(result["controller_initialization_status"], "ready")
                self.assertGreater(result["controller_initialization_ns"], 0)
                self.assertEqual(result["stored_plan_steps"], 5)
                self.assertEqual(result["terminal_hold_steps"], 5)
                self.assertEqual(result["final_state"]["v_exact"], ["0", "0"])

    def test_losing_recovery_is_distinct_from_a_safe_next_interval(self):
        results = {}
        for method in ["trajectory_candidates", "backup_candidates"]:
            config = PlanarConfig(method=method, p=("1.06", 0), v=("-0.3", 0), horizon="1", a_max="1",
                                  nominal_policy="constant", nominal=(-1, 0), obstacles=({"center": [0, 0], "radius": 1},))
            results[method] = run_planar(config)
        self.assertEqual(results["trajectory_candidates"]["termination"], "search_exhausted")
        self.assertEqual(results["trajectory_candidates"]["executed_steps"], 1)
        self.assertTrue(results["backup_candidates"]["completed_safe_horizon"])
        self.assertTrue(results["backup_candidates"]["retained_continuation_after_every_update"])

    def test_backup_initialization_failure_has_no_action(self):
        result = run_planar(PlanarConfig(method="backup_candidates", p=("1.01", 0), v=(-10, 0), horizon="0.1",
                                         obstacles=({"center": [0, 0], "radius": 1},)))
        self.assertEqual(result["termination"], "initialization_failed")
        self.assertEqual(result["executed_steps"], 0)
        self.assertFalse(result["completed_safe_horizon"])

    def test_candidate_budget_validation(self):
        for kwargs in [{"max_candidates": -1}, {"max_candidates": True}, {"method": "hocbf", "max_candidates": 1}]:
            with self.assertRaises(ValueError):
                PlanarConfig(**kwargs)


if __name__ == "__main__":
    unittest.main()
