import unittest
from fractions import Fraction as F

from tick_trap.experiments import RunConfig, load_grid, run


def without_timings(value):
    if isinstance(value, dict):
        return {k: without_timings(v) for k, v in value.items()
                if "_ns" not in k and k not in ("deadline_missed", "deadline_misses")}
    if isinstance(value, list):
        return [without_timings(x) for x in value]
    return value


class ExperimentTests(unittest.TestCase):
    def test_viable_collision_classified_separately(self):
        result = run(RunConfig(method="endpoint", d="0.06", v="1", duration="0.4"))
        self.assertTrue(result["initial_viable"])
        self.assertTrue(result["sampled_safe_observed"])
        self.assertTrue(result["collision_observed"])
        self.assertEqual(result["termination"], "collision_interval")
        self.assertFalse(result["completed_safe_horizon"])

    def test_no_unverified_fallback(self):
        result = run(RunConfig(method="exact_hold", d="0.04", duration="0.2"))
        self.assertFalse(result["initial_viable"])
        self.assertEqual(result["termination"], "infeasible")
        self.assertEqual(result["executed_steps"], 0)
        self.assertFalse(result["completed_safe_horizon"])
        self.assertNotIn("action", result["records"][0])

    def test_exact_reference_completes_viable_horizon(self):
        result = run(RunConfig())
        self.assertTrue(result["completed_safe_horizon"])
        self.assertEqual(result["assumption_violations"], [])
        self.assertTrue(all(r["true_viable_after"] for r in result["records"]))

    def test_fixed_delay_is_executed_as_two_exact_pieces(self):
        result = run(RunConfig(method="nominal", d="10", steps=1, v="1", nominal="-2",
                               previous_action="2", duration="0.2", delay="0.05"))
        record = result["records"][0]
        self.assertEqual(len(record["pieces"]), 2)
        self.assertEqual(F(record["end_state"]["v_exact"]), F("0.8"))
        self.assertEqual(F(record["end_state"]["d_exact"]), F("9.805"))
        self.assertIn("execution_delay", result["assumption_violations"])

    def test_model_mismatch_and_measurement_noise_are_explicit(self):
        config = RunConfig(plant_gain="0.7", measurement_d="0.01", measurement_v="0.01", seed=901)
        first, second = run(config), run(config)
        self.assertEqual(without_timings(first), without_timings(second))
        self.assertEqual(first["assumption_violations"], ["actuation_model_mismatch", "measurement_error"])

    def test_inverse_model_respects_command_limits(self):
        result = run(RunConfig(model_gain="0.7", model_bias="0.2", plant_gain="0.7", plant_bias="0.2"))
        self.assertTrue(result["completed_safe_horizon"])
        self.assertEqual(result["assumption_violations"], [])
        for record in result["records"]:
            self.assertLessEqual(abs(F(record["action_exact"])), 10)
            self.assertEqual(F(record["pieces"][0]["actual_acceleration_exact"]),
                             F(record["filtered_acceleration_exact"]))

    def test_deadline_is_measured_but_does_not_implicitly_change_plant(self):
        config = RunConfig(method="nominal", d="10", deadline="1e-20", steps=1)
        result = run(config)
        self.assertEqual(result["deadline_misses"], 1)
        self.assertEqual(len(result["records"][0]["pieces"]), 1)

    def test_grid_and_input_validation(self):
        configs = list(load_grid({"base": {"steps": 1}, "grid": {"duration": ["0.1", "0.2"],
                                                                              "seed": [1, 2]}}))
        self.assertEqual(len(configs), 4)
        for config in [{"delay": "0.1"}, {"plant_gain": 0}, {"model_bias": 10}, {"steps": 0}]:
            with self.assertRaises(ValueError):
                RunConfig(**config)
        for spec in [{"base": {"typo": 1}}, {"grid": {"seed": []}}, {"bad": 1}]:
            with self.assertRaises(ValueError):
                list(load_grid(spec))


if __name__ == "__main__":
    unittest.main()
