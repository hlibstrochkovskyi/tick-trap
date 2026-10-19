import unittest
from fractions import Fraction as F
from itertools import product
from functools import reduce

from tick_trap.algebraic_reference import exact_sign_reference
from tick_trap.polynomial import certify_sign


def multiply(a, b):
    # Test construction deliberately uses a separate convolution.
    return [sum(a[j]*b[i-j] for j in range(len(a)) if 0 <= i-j < len(b))
            for i in range(len(a)+len(b)-1)]


class AlgebraicReferenceTests(unittest.TestCase):
    def check(self, coefficients, expected, duration=1):
        result = exact_sign_reference(coefficients, duration)
        self.assertEqual(result["status"], expected)
        for budget in (0, 8, 64):
            online = certify_sign(coefficients, duration, "1e-30", budget)
            if online.status != "unknown":
                self.assertEqual(online.status, expected)
        return result

    def test_constants_and_invalid_inputs(self):
        for c in (0, 1, -1):
            self.check([c], "safe" if c >= 0 else "unsafe")
        for p, t in (([], 1), ([1.0], 1), ([True], 1), ([1], 0), ([1]*6, 1)):
            with self.assertRaises(ValueError):
                exact_sign_reference(p, t)

    def test_nondyadic_tangencies_and_tiny_margins(self):
        square = [F(9, 100), F(-3, 5), F(1)]  # (t-3/10)^2
        self.check(square, "safe")
        self.assertEqual(certify_sign(square, 1, "1e-30", 64).status, "unknown")
        for exponent in (20, 100, 400):
            epsilon = F(1, 10**exponent)
            for delta, expected in ((epsilon, "safe"), (-epsilon, "unsafe")):
                self.check([square[0]+delta, *square[1:]], expected)
        fourth = multiply(square, square)
        self.check(fourth, "safe")
        self.check([-c for c in fourth], "unsafe")

    def test_endpoint_roots_do_not_change_the_interior_sign(self):
        self.check([0, 1, -1], "safe")   # t(1-t)
        self.check([0, -1, 1], "unsafe")
        self.check([0, 0, 1], "safe")
        self.check([1, -3, 3, -1], "safe")  # (1-t)^3

    def test_irrational_repeated_roots_and_nonunit_intervals(self):
        factor = [F(-1, 2), 0, 1]
        self.check(multiply(factor, factor), "safe")
        self.check(factor, "unsafe")
        self.check([1, -1], "safe", duration=1)
        self.check([1, -1], "unsafe", duration=2)
        self.check([1, -1], "safe", duration=F(1, 3))
        # Two distinct, very close irrational roots create a tiny negative pocket.
        epsilon = F(1, 10**100)
        coefficients = multiply(factor, factor)
        coefficients[0] -= epsilon
        self.check(coefficients, "unsafe")

    def test_known_factored_roots_and_multiplicities(self):
        # Exhaust known factors at exterior, endpoint and interior locations.
        roots = (F(-1), F(0), F(1, 3), F(2, 3), F(1), F(2))
        for degree in range(1, 5):
            for selected in product(roots, repeat=degree):
                # Skip permutations: the known factorization is the truth source.
                if tuple(sorted(selected)) != selected:
                    continue
                p = [F(1)]
                for root in selected:
                    p = multiply(p, [-root, F(1)])
                cuts = sorted({F(0), F(1), *(r for r in selected if 0 < r < 1)})
                probes = [*cuts, *((a+b)/2 for a, b in zip(cuts, cuts[1:]))]
                for sign in (1, -1):
                    coefficients = [sign*c for c in p]
                    # On every open component all factors have constant sign.
                    expected = "safe" if all(sign*reduce(
                        lambda a, b: a*b, (t-r for r in selected), F(1)) >= 0 for t in probes) else "unsafe"
                    self.assertEqual(exact_sign_reference(coefficients, 1)["status"], expected,
                                     (selected, sign))

    def test_physical_auxiliary_exact_and_near_tangencies(self):
        from tick_trap.barrier_paths import auxiliary_polynomial
        from tick_trap.dynamics import Circle, PlanarState
        state, action = PlanarState(("1.231168", 0), ("-0.90112", 0)), (F("0.8704"), 0)
        for radius, expected in (("0.599999999", "safe"), ("0.6", "safe"), ("0.600000001", "unsafe")):
            psi = auxiliary_polynomial(Circle((0, 0), radius).polynomial(state, action), 2)
            self.check(psi, expected)


if __name__ == "__main__":
    unittest.main()
