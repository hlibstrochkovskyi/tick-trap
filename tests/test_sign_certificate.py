from fractions import Fraction as F
import random
import unittest

from tick_trap.polynomial import certify_minimum, certify_sign, evaluate


class SignCertificateTests(unittest.TestCase):
    def test_positive_enclosure_stops_without_minimum_precision(self):
        polynomial = [2, -1, 1, 0, 1]
        sign = certify_sign(polynomial, 1, max_subdivisions=0)
        minimum = certify_minimum(polynomial, 1)
        self.assertEqual(sign.status, "safe")
        self.assertEqual(sign.subdivisions, 0)
        self.assertFalse(sign.precision_reached)
        self.assertFalse(sign.budget_exhausted)
        self.assertEqual(sign.stopping_reason, "sign_proved")
        self.assertGreater(minimum.subdivisions, sign.subdivisions)
        self.assertTrue(minimum.precision_reached)
        self.assertLessEqual(sign.lower, minimum.lower)
        self.assertGreaterEqual(sign.upper, minimum.upper)

    def test_negative_witness_stops_without_minimizing(self):
        result = certify_sign([-1, -1, 1], 1, max_subdivisions=0)
        self.assertEqual(result.status, "unsafe")
        self.assertEqual(evaluate([-1, -1, 1], result.witness_time), result.upper)
        self.assertLess(result.upper, 0)
        self.assertFalse(result.precision_reached)
        self.assertFalse(result.budget_exhausted)

    def test_unresolved_budget_precision_and_tangency_are_explicit(self):
        budget = certify_sign([F("0.26"), -1, 1], 1, max_subdivisions=0)
        self.assertEqual(budget.status, "unknown")
        self.assertTrue(budget.budget_exhausted)
        self.assertEqual(budget.stopping_reason, "budget_exhausted")
        positive = certify_sign([F("0.26"), -1, 1], 1)
        self.assertEqual(positive.status, "safe")
        tangent = certify_sign([F("0.09"), F("-0.6"), 1], 1)
        self.assertEqual(tangent.status, "unknown")
        self.assertTrue(tangent.precision_reached)
        self.assertEqual(tangent.stopping_reason, "precision_reached")
        self.assertEqual(certify_sign([F("0.25"), -1, 1], 1).status, "safe")
        tiny = certify_sign([F("0.09")-F(1, 10**20), F("-0.6"), 1], 1)
        self.assertNotEqual(tiny.status, "safe")

    def test_sign_and_minimum_have_consistent_status_and_valid_bounds(self):
        rng = random.Random(271828)
        for _ in range(50):
            polynomial = [F(rng.randrange(-30, 31), 10) for _ in range(5)]
            for budget in (0, 2, 64):
                sign = certify_sign(polynomial, F(7, 5), "1e-8", budget)
                minimum = certify_minimum(polynomial, F(7, 5), "1e-8", budget)
                self.assertEqual(sign.status, minimum.status)
                self.assertLessEqual(sign.subdivisions, minimum.subdivisions)
                self.assertLessEqual(sign.lower, minimum.lower)
                self.assertGreaterEqual(sign.upper, minimum.upper)
                self.assertEqual(evaluate(polynomial, sign.witness_time), sign.upper)
                for i in range(21):
                    self.assertLessEqual(sign.lower, evaluate(polynomial, F(7*i, 100)))

    def test_sign_query_rejects_invalid_numeric_limits(self):
        for kwargs in ({"tolerance": 0}, {"max_subdivisions": True}, {"max_subdivisions": -1}):
            with self.assertRaises(ValueError):
                certify_sign([1, 2], 1, **kwargs)


if __name__ == "__main__":
    unittest.main()
