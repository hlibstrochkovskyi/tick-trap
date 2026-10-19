from fractions import Fraction as F
import unittest

from tick_trap.barrier_paths import auxiliary_polynomial, certify_auxiliary_path
from tick_trap.dynamics import Circle, PlanarState
from tick_trap.polynomial import certify_sign, evaluate


class BarrierPathTests(unittest.TestCase):
    def test_auxiliary_polynomial_matches_the_independent_physical_expression(self):
        state, obstacle = PlanarState((2, 1), (-1, 2)), Circle((1, -1), F(1, 2))
        action, gain = (F(7, 10), F(-2, 5)), F(3)
        psi = auxiliary_polynomial(obstacle.polynomial(state, action), gain)
        for t in (F(0), F(1, 3), F(1)):
            path = state.at(action, t)
            r = tuple(p-c for p, c in zip(path.p, obstacle.center))
            expected = 2*sum(x*v for x, v in zip(r, path.v))+gain*(sum(x*x for x in r)-obstacle.radius**2)
            self.assertEqual(evaluate(psi, t), expected)

    def test_geometric_sign_can_follow_from_psi_when_its_direct_query_is_unknown(self):
        state, obstacle = PlanarState(("-0.3", "1.06"), (1, 0)), Circle((0, 0), 1)
        h = obstacle.polynomial(state, (0, 0))
        self.assertEqual(certify_sign(h, 1, max_subdivisions=0).status, "unknown")
        cert, implication = certify_auxiliary_path(h, 3, 1, max_subdivisions=0)
        self.assertEqual(cert.status, "safe")
        self.assertEqual(auxiliary_polynomial(h, 3)[:3], (F("0.0408"), F("0.2"), F(3)))
        self.assertEqual(implication, {"rule": "linear_comparison", "initial_h_exact": "267/1250",
                                      "lambda1_exact": "3", "duration_exact": "1", "status": "safe"})
        self.assertNotIn("lower_exact", implication)
        self.assertNotIn("upper_exact", implication)
        # Independent geometry: y is constant above the radius throughout.
        self.assertGreater(state.p[1]**2-obstacle.radius**2, 0)

    def test_unknown_auxiliary_proof_cannot_hide_a_geometric_violation(self):
        state, obstacle = PlanarState((2, 0), (-1, 0)), Circle((0, 0), 1)
        h = obstacle.polynomial(state, (0, 0))
        self.assertEqual(certify_sign(h, "2.9", max_subdivisions=0).status, "unsafe")
        cert, implication = certify_auxiliary_path(h, 2, "2.9", max_subdivisions=0)
        self.assertEqual(cert.status, "unknown")
        self.assertEqual(implication["status"], "not_certified")

    def test_auxiliary_violation_does_not_claim_a_geometric_collision(self):
        state, obstacle = PlanarState(("1.231168", 0), ("-0.90112", 0)), Circle((0, 0), "0.600000001")
        h = obstacle.polynomial(state, (F("0.8704"), 0))
        self.assertEqual(certify_sign(h, 1, "1e-12", 64).status, "safe")
        cert, implication = certify_auxiliary_path(h, 2, 1, "1e-12", 64)
        self.assertEqual(cert.status, "unsafe")
        self.assertEqual(implication["status"], "not_certified")

    def test_boundary_contact_and_invalid_implication_assumptions(self):
        cert, implication = certify_auxiliary_path((0,), 2, 1)
        self.assertEqual((cert.status, implication["status"]), ("safe", "safe"))
        for h, gain, duration in (((-1, 2), 1, 1), ((1,), 0, 1), ((1,), 2, 0), ((), 2, 1)):
            with self.assertRaises(ValueError):
                certify_auxiliary_path(h, gain, duration)


if __name__ == "__main__":
    unittest.main()
