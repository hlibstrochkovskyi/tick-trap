import unittest
from fractions import Fraction as F

from tick_trap.dynamics import Circle, PlanarState, WallState
from tick_trap.numbers import q, sqrt_upper


class DynamicsTests(unittest.TestCase):
    def test_audit_counterexample_exactly(self):
        state = WallState("0.04", 1)
        self.assertEqual(state.at(-10, "0.2"), WallState("0.04", -1))
        self.assertEqual(state.minimum(-10, "0.2"), (F("-0.01"), F("0.1")))
        self.assertEqual(state.viability_margin(10), F("-0.01"))

    def test_signed_velocity_viability(self):
        self.assertEqual(WallState("0.01", -100).viability_margin(10), F("0.01"))
        self.assertEqual(WallState("0.05", 1).viability_margin(10), 0)

    def test_minimum_endpoints_and_degenerate_acceleration(self):
        self.assertEqual(WallState(1, 1).minimum(0, "0.2"), (F("0.8"), F("0.2")))
        self.assertEqual(WallState(1, -1).minimum(-10, "0.2"), (F(1), F(0)))
        self.assertEqual(WallState(1, 0).minimum(1, 1), (F("0.5"), F(1)))

    def test_planar_polynomial_matches_independent_geometry(self):
        state = PlanarState(("1.3", "-0.7"), ("-2.1", "0.8"))
        circle = Circle(("0.2", "0.3"), "0.4")
        u = (F("1.7"), F("-0.9"))
        coefficients = circle.polynomial(state, u)
        for t in [F(0), F(1, 7), F(1, 2), F(2)]:
            point = state.at(u, t)
            h = sum((p-c)**2 for p, c in zip(point.p, circle.center))-circle.radius**2
            self.assertEqual(sum(c*t**i for i, c in enumerate(coefficients)), h)

    def test_rational_square_root_bounds(self):
        for x in [F(0), F(2), F(1, 7), F(10**30), F(1, 10**30)]:
            upper = sqrt_upper(x)
            self.assertGreaterEqual(upper**2, x)
            if upper > 0:
                self.assertLess((upper-F(1, 10**12))**2, x)

    def test_invalid_inputs(self):
        for invalid in [True, float("nan"), float("inf"), "oops"]:
            with self.assertRaises(ValueError):
                q(invalid)
        for call in [lambda: WallState(1, 1).minimum(0, 0),
                     lambda: WallState(1, 1).viability_margin(0),
                     lambda: PlanarState((1,), (1, 2)),
                     lambda: Circle((0, 0), -1)]:
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
