from decimal import Decimal, localcontext
from fractions import Fraction as F
import unittest

from tick_trap.dynamics import Circle, PlanarState
from tick_trap.polynomial import certify_minimum, evaluate
from tick_trap.sampling import exp_negative_upper, quadratic_absolute_bound, sacbf_assessment


class SamplingTests(unittest.TestCase):
    def test_exponential_upper_enclosure_against_high_precision_reference(self):
        with localcontext() as context:
            context.prec = 90
            for x in ("0", "0.00001", "0.2", "1", "10", "60", "1000"):
                result = exp_negative_upper(x)
                decimal = Decimal(result.numerator)/Decimal(result.denominator)
                reference = (-Decimal(x)).exp()
                self.assertGreaterEqual(decimal, reference)
                self.assertLessEqual(decimal-reference, Decimal("1e-18"))
        self.assertEqual(exp_negative_upper(0), 1)

    def test_exponential_rejects_invalid_input(self):
        for x in (-1, True):
            with self.assertRaises(ValueError):
                exp_negative_upper(x)
        with self.assertRaises(ValueError):
            exp_negative_upper(1, 0)

    def test_quadratic_bound_handles_vertex_sign_and_degeneracies(self):
        for coefficients in ((1, 2, -2), (-1, -2, 2)):
            self.assertEqual(quadratic_absolute_bound(coefficients, 1), (F(3, 2), F(1, 2)))
        self.assertEqual(quadratic_absolute_bound((0, -2, 0), 1), (2, 1))
        self.assertEqual(quadratic_absolute_bound((0, 0, 0), 1), (0, 0))
        self.assertEqual(quadratic_absolute_bound((0, 0, 1), 1), (1, 1))

    def test_derivative_polynomial_matches_independent_vector_formula(self):
        state, obstacle, action = PlanarState((2, 1), (-1, 2)), Circle((0, 0), 1), (F(7, 10), F(-2, 5))
        result = sacbf_assessment(state, action, obstacle, 1, 3, 5)
        coefficients = [F(x) for x in result["second_derivative_exact"]]
        for t in (F(0), F(1, 3), F(1)):
            evolved = state.at(action, t)
            r, v = evolved.p, evolved.v
            expected = 6*sum(x*u for x, u in zip(v, action))+6*(sum(x*x for x in v)+sum(x*u for x, u in zip(r, action)))
            self.assertEqual(evaluate(coefficients, t), expected)
            self.assertLessEqual(abs(expected), F(result["second_derivative_bound_exact"]))

    def test_relaxation_enlarges_feasibility_without_disabling_bound(self):
        state, obstacle = PlanarState((2, 0), (-1, 0)), Circle((0, 0), 1)
        strict = sacbf_assessment(state, (0, 0), obstacle, F(1, 5))
        relaxed = sacbf_assessment(state, (0, 0), obstacle, F(1, 5), relaxed=True)
        self.assertFalse(strict["accepted"])
        self.assertTrue(relaxed["accepted"])
        self.assertEqual(relaxed["target_exact"], "0")
        self.assertGreater(F(relaxed["second_derivative_bound_exact"]), 0)
        self.assertEqual(certify_minimum(obstacle.polynomial(state, (0, 0)), F(1, 5)).status, "safe")

    def test_geometric_and_psi_domain_required_even_for_relaxation(self):
        for state in (PlanarState((F(1, 2), 0), (0, 0)), PlanarState((2, 0), (-4, 0))):
            result = sacbf_assessment(state, (10, 0), Circle((0, 0), 1), F(1, 10), relaxed=True)
            self.assertFalse(result["in_domain"])
            self.assertFalse(result["accepted"])

    def test_accepted_controls_preserve_geometric_and_auxiliary_barriers(self):
        # Independently reconstruct both quartics and certify their actual paths.
        accepted = 0
        obstacle = Circle((0, 0), 1)
        for p, v in (((2, 0), (-1, 0)), ((F(6, 5), 0), (F(-1, 10), 0)), ((2, 1), (0, -1))):
            state = PlanarState(p, v)
            for x in range(-2, 3):
                for y in range(-2, 3):
                    for relaxed in (False, True):
                        result = sacbf_assessment(state, (x, y), obstacle, F(1, 10), relaxed=relaxed)
                        if not result["accepted"]:
                            continue
                        accepted += 1
                        h = obstacle.polynomial(state, (x, y))
                        psi = tuple(2*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
                        for polynomial in (h, psi):
                            self.assertEqual(certify_minimum(polynomial, F(1, 10)).status, "safe")
        self.assertGreater(accepted, 50)


if __name__ == "__main__":
    unittest.main()
