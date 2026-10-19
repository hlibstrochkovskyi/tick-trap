import unittest

from tick_trap.experiments import RunConfig
from tick_trap.learning import fit_affine, learning_study


class LearningTests(unittest.TestCase):
    def test_identifies_noiseless_affine_actuator(self):
        result = fit_affine([-2, -1, 0, 1, 2], [-3, -1, 1, 3, 5])
        self.assertEqual(result["gain"], 2)
        self.assertEqual(result["bias"], 1)
        self.assertEqual(result["training_rmse"], 0)

    def test_degenerate_training_data_rejected(self):
        for commands, observations in [([0, 0], [1, 1]), ([1], [1]), ([0, 1], [0]), ([0, 1], [1, float("nan")])]:
            with self.assertRaises(ValueError):
                fit_affine(commands, observations)

    def test_learning_distribution_change_is_explicit(self):
        result = learning_study(samples=16, methods=["exact_hold"], run_config={"steps": 3})
        self.assertEqual(len(result["runs"]), 4)
        errors = {(r["plant"], r["model"]): r["heldout_mean_acceleration_rmse"] for r in result["evaluation"]}
        self.assertLess(errors[("training_distribution", "learned_model")],
                        errors[("training_distribution", "unit_model")])
        self.assertGreater(errors[("shifted_dynamics", "learned_model")],
                           errors[("training_distribution", "learned_model")])
        for run in result["runs"]:
            self.assertIn("actuation_model_mismatch", run["assumption_violations"])
        repeated = learning_study(samples=16, methods=["exact_hold"], run_config={"steps": 3})
        self.assertEqual(result["model"], repeated["model"])
        self.assertEqual(result["training_accelerations"], repeated["training_accelerations"])

    def test_invalid_study_inputs(self):
        for kwargs in [{"samples": 1}, {"noise_std": -1}, {"methods": []}]:
            with self.assertRaises(ValueError):
                learning_study(**kwargs)


if __name__ == "__main__":
    unittest.main()
