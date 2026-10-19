import random
import unittest
from fractions import Fraction as F

from tick_trap.dynamics import Circle, PlanarState, WallState
from tick_trap.oracle import circle_interval, wall_interval
from tick_trap.polynomial import certify_minimum, evaluate, stationary_estimate


class OracleTests(unittest.TestCase):
    def test_endpoints_miss_wall_collision(self):
        result = wall_interval(WallState("0.04", 1), -10, "0.2")
        self.assertTrue(result["sampled_safe"])
        self.assertEqual(result["continuous_status"], "unsafe")
        self.assertEqual(result["minimum_clearance_exact"], "-1/100")

    def test_planar_curved_counterexample(self):
        result = circle_interval(PlanarState(("0.04", 0), (-1, 0)), (10, 0),
                                 Circle((-1, 0), 1), "0.2")
        self.assertTrue(result["sampled_safe"])
        self.assertEqual(result["continuous_status"], "unsafe")
        self.assertAlmostEqual(result["minimum_estimate"], -0.0199)
        self.assertAlmostEqual(result["time_estimate"], 0.1)
        self.assertLessEqual(F(result["minimum_lower_exact"]), F("-0.0199"))
        self.assertGreaterEqual(F(result["minimum_upper_exact"]), F("-0.0199"))

    def test_cubic_stationary_points(self):
        # x(t)=-1+8t-8t², h=x²-1: two minima and a central maximum.
        poly = Circle((0, 0), 1).polynomial(PlanarState((-1, 0), (8, 0)), (-16, 0))
        estimate = stationary_estimate(poly, 1)
        self.assertEqual(len(estimate["critical_times_estimate"]), 3)
        self.assertAlmostEqual(estimate["minimum_estimate"], -1)
        cert = certify_minimum(poly, 1)
        self.assertLessEqual(cert.lower, -1)
        self.assertGreaterEqual(cert.upper, -1)
        self.assertEqual(cert.status, "unsafe")

    def test_stationary_and_linear_paths(self):
        for p, v, expected in [((2, 0), (0, 0), 3), ((-2, 0), (4, 0), -1)]:
            poly = Circle((0, 0), 1).polynomial(PlanarState(p, v), (0, 0))
            self.assertAlmostEqual(stationary_estimate(poly, 1)["minimum_estimate"], expected)
            cert = certify_minimum(poly, 1)
            self.assertLessEqual(cert.lower, expected)
            self.assertGreaterEqual(cert.upper, expected)

    def test_budget_does_not_create_guarantee(self):
        cert = certify_minimum([F("0.26"), -1, 1], 1, max_subdivisions=0)
        self.assertEqual(cert.status, "unknown")
        self.assertTrue(cert.budget_exhausted)
        cert = certify_minimum([F("0.26"), -1, 1], 1)
        self.assertEqual(cert.status, "safe")

    def test_tangencies_and_tiny_negative_values(self):
        dyadic = certify_minimum([F("0.25"), -1, 1], 1)
        self.assertEqual(dyadic.status, "safe")
        # Non-dyadic double root: a small numerical estimate is not a proof.
        tangent = certify_minimum([F("0.09"), F("-0.6"), 1], 1)
        self.assertEqual(tangent.status, "unknown")
        self.assertLessEqual(tangent.lower, 0)
        self.assertGreaterEqual(tangent.upper, 0)
        tiny = certify_minimum([F("0.09")-F(1, 10**20), F("-0.6"), 1], 1)
        self.assertNotEqual(tiny.status, "safe")

    def test_random_quartic_enclosures_against_independent_samples(self):
        rng = random.Random(901)
        for _ in range(40):
            coefficients = [F(rng.randrange(-30, 31), 10) for _ in range(5)]
            cert = certify_minimum(coefficients, F(7, 5), tolerance="1e-7")
            for j in range(101):
                value = evaluate(coefficients, F(7*j, 500))
                self.assertLessEqual(cert.lower, value)
            self.assertEqual(evaluate(coefficients, cert.witness_time), cert.upper)
            self.assertLessEqual(cert.lower, cert.upper)

    def test_invalid_certification_parameters(self):
        for kwargs in [{"tolerance": 0}, {"max_subdivisions": -1}, {"max_subdivisions": 0.5}]:
            with self.assertRaises(ValueError):
                certify_minimum([1, 2], 1, **kwargs)


if __name__ == "__main__":
    unittest.main()
