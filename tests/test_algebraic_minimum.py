from fractions import Fraction as F
from itertools import combinations_with_replacement
from random import Random
import unittest

from tick_trap.algebraic_minimum import enclose_algebraic_minimum
from tick_trap.algebraic_reference import exact_sign_reference
from tick_trap.polynomial import certify_minimum


def value(polynomial, time):
    return sum(c*time**i for i, c in enumerate(polynomial))


def multiply(a, b):
    return [sum(a[j]*b[i-j] for j in range(len(a)) if 0 <= i-j < len(b))
            for i in range(len(a)+len(b)-1)]


class AlgebraicMinimumTests(unittest.TestCase):
    def check(self, polynomial, true_minimum, duration=1, tolerance="1e-12", budget=128):
        result = enclose_algebraic_minimum(polynomial, duration, tolerance, budget)
        lower, upper = F(result["lower_exact"]), F(result["upper_exact"])
        self.assertLessEqual(lower, true_minimum)
        self.assertLessEqual(true_minimum, upper)
        self.assertEqual(upper, value(polynomial, F(result["witness_time_exact"])))
        self.assertEqual(result["precision_reached"], upper-lower <= F(tolerance))
        if result["status"] == "safe":
            self.assertGreaterEqual(true_minimum, 0)
        elif result["status"] == "unsafe":
            self.assertLess(true_minimum, 0)
        if result["stationary_roots_open"] is not None:
            self.assertEqual(sum(b["roots"] for b in result["stationary_boxes"])+len(result["exact_stationary_points"]),
                             result["stationary_roots_open"])
        return result

    def test_constants_linear_models_and_invalid_inputs(self):
        for constant in (F(-1), F(0), F(1)):
            result = self.check([constant], constant, budget=0)
            self.assertIsNone(result["stationary_roots_open"])
            self.assertTrue(result["precision_reached"])
        self.check([F(1), F(-1)], F(-1), duration=2, budget=0)
        for p, t, tol, budget in (([], 1, 1, 1), ([1.0], 1, 1, 1), ([True], 1, 1, 1),
                                  ([1], 0, 1, 1), ([1], True, 1, 1), ([1], 1, 0.1, 1),
                                  ([1], 1, 0, 1), ([1]*6, 1, 1, 1), ([1], 1, 1, True), ([1], 1, 1, -1)):
            with self.assertRaises(ValueError):
                enclose_algebraic_minimum(p, t, tol, budget)

    def test_dyadic_and_endpoint_stationary_points_are_not_lost_or_duplicated(self):
        for polynomial, roots in (([F(0), F(0), F(1)], 0),
                                  ([F(1), F(-4), F(6), F(-4), F(1)], 0),
                                  ([F(1), F(-2), F(1)], 1)):
            duration = 2 if roots else 1
            result = self.check(polynomial, F(0), duration=duration)
            self.assertEqual(result["stationary_roots_open"], roots)
            self.assertEqual((result["lower_exact"], result["upper_exact"]), ("0", "0"))
        polynomial = multiply([F(1, 16), F(-1, 2), F(1)], [F(9, 16), F(-3, 2), F(1)])
        result = self.check(polynomial, F(0))
        self.assertEqual(result["stationary_roots_open"], 3)
        self.assertTrue(result["precision_reached"])

    def test_repeated_stationary_roots_are_counted_once(self):
        square = [F(9, 100), F(-3, 5), F(1)]
        result = self.check(multiply(square, square), F(0))
        self.assertEqual(result["stationary_roots_open"], 1)
        self.assertEqual(len(result["square_free_derivative_exact"]), 2)
        self.assertEqual(result["status"], "unknown")

    def test_tiny_positive_and_negative_minima_at_irrational_stationary_points(self):
        for delta in (F(1, 10**100), F(-1, 10**100)):
            polynomial = [F(1, 4)+delta, F(0), F(-1), F(0), F(1)]
            result = self.check(polynomial, delta, tolerance="1e-110", budget=512)
            self.assertTrue(result["precision_reached"])
            self.assertEqual(result["status"], "safe" if delta > 0 else "unsafe")

    def test_a_small_width_or_zero_budget_does_not_resolve_an_unknown_sign(self):
        polynomial = [F(9, 100)-F(1, 10**100), F(-3, 5), F(1)]
        coarse = self.check(polynomial, F(-1, 10**100), tolerance="1e-6")
        self.assertTrue(coarse["precision_reached"])
        self.assertEqual(coarse["status"], "unknown")
        self.assertEqual(exact_sign_reference(polynomial, 1)["status"], "unsafe")
        limited = self.check(polynomial, F(-1, 10**100), budget=0)
        self.assertFalse(limited["precision_reached"])
        self.assertTrue(limited["budget_exhausted"])
        self.assertEqual(limited["status"], "unknown")

    def test_known_factored_derivatives_supply_an_independent_exact_minimum(self):
        rng = Random(20261022)
        roots = (F(-1), F(0), F(1, 3), F(1, 2), F(1), F(2))
        for degree in range(1, 4):
            choices = list(combinations_with_replacement(roots, degree))
            for selected in rng.sample(choices, min(16, len(choices))):
                derivative = [F(1)]
                for root in selected:
                    derivative = multiply(derivative, [-root, F(1)])
                for sign in (-1, 1):
                    polynomial = [F(1, 7), *(sign*c/F(i+1) for i, c in enumerate(derivative))]
                    times = [F(0), F(1), *(r for r in selected if 0 < r < 1)]
                    true_minimum = min(value(polynomial, t) for t in times)
                    for budget in (0, 64):
                        self.check(polynomial, true_minimum, budget=budget)

    def test_independent_and_bernstein_enclosures_intersect_on_a_seeded_grid(self):
        rng = Random(71)
        for degree in range(1, 5):
            for _ in range(8):
                polynomial = [F(rng.randint(-5, 5), rng.randint(1, 9)) for i in range(degree+1)]
                duration = F(rng.randint(1, 4), 2)
                for budget in (0, 8, 64):
                    a = enclose_algebraic_minimum(polynomial, duration, "1e-12", budget)
                    b = certify_minimum(polynomial, duration, "1e-12", budget)
                    self.assertLessEqual(max(F(a["lower_exact"]), b.lower), min(F(a["upper_exact"]), b.upper))
                    if a["status"] != "unknown":
                        self.assertEqual(a["status"], exact_sign_reference(polynomial, duration)["status"])

    def test_budget_prefixes_nest_the_enclosures(self):
        polynomial = [F(1, 4), F(0), F(-1), F(0), F(1)]
        previous = None
        for budget in (0, 1, 2, 8, 64):
            result = self.check(polynomial, F(0), budget=budget)
            bounds = (F(result["lower_exact"]), F(result["upper_exact"]))
            if previous is not None:
                self.assertGreaterEqual(bounds[0], previous[0])
                self.assertLessEqual(bounds[1], previous[1])
            previous = bounds


if __name__ == "__main__":
    unittest.main()
