from fractions import Fraction as F
import unittest

from tick_trap.algebraic_reference import exact_sign_reference
from tick_trap.barrier_paths import auxiliary_polynomial
from tick_trap.representation_audit import METHODS, representation_certificate, transformed_polynomial


def value(polynomial, time):
    return sum(c*time**i for i, c in enumerate(polynomial))


class RepresentationAuditTests(unittest.TestCase):
    def test_fixed_absolute_width_can_lose_a_negative_witness_without_becoming_safe(self):
        p = [F(9, 100)-F(1, 10**8), F(-3, 5), F(1)]
        for method in ("bernstein_minimum", "bernstein_sign"):
            base = representation_certificate(method, p, 1, "1e-12", 64)
            fixed = representation_certificate(method, p, 1, "1e-12", 64, "1e-6")
            scaled = representation_certificate(method, p, 1, "1e-18", 64, "1e-6")
            self.assertEqual(base["certificate"]["status"], "unsafe")
            self.assertEqual(fixed["certificate"]["status"], "unknown")
            self.assertTrue(fixed["certificate"]["precision_reached"])
            self.assertEqual(base["original_coordinates"], scaled["original_coordinates"])
        self.assertEqual(exact_sign_reference(p, 1)["status"], "unsafe")

    def test_positive_scaling_with_equivalent_width_preserves_bounds_work_and_decisions(self):
        cases = [([F(9, 100), F(-3, 5), F(1)], F(1)),
                 ([F(3), F(-4), F(2), F(-1, 2), F(1, 16)], F(29, 10)),
                 ([F(1, 4)-F(1, 10**20), F(0), F(-1), F(0), F(1)], F(2)),
                 ([F(1)], F(1, 100)), ([F(1), F(-2)], F(1, 3))]
        for method in METHODS:
            for p, duration in cases:
                for budget in (0, 8, 64):
                    baseline = representation_certificate(method, p, duration, "1e-12", budget)
                    for scale in (F(1, 10**6), F(1), F(10**6)):
                        for basis in ("physical", "unit_interval"):
                            result = representation_certificate(method, p, duration, scale*F("1e-12"), budget, scale, basis)
                            self.assertEqual(baseline["original_coordinates"], result["original_coordinates"])

    def test_unit_time_maps_the_evaluated_upper_witness_back_to_physical_time(self):
        p, duration = [F(3), F(-4), F(2), F(-1, 2), F(1, 16)], F(29, 10)
        for method in METHODS:
            result = representation_certificate(method, p, duration, "1e-12", 64, "3/7", "unit_interval")
            raw, original = result["certificate"], result["original_coordinates"]
            transformed = [F(c) for c in result["polynomial_exact"]]
            self.assertEqual(F(raw["upper_exact"]), value(transformed, F(raw["witness_time_exact"])))
            self.assertEqual(F(original["upper_exact"]), value(p, F(original["witness_time_exact"])))
            self.assertEqual(result["duration_exact"], "1")

    def test_auxiliary_polynomial_time_composition_keeps_the_derivative_conversion(self):
        h, duration, gain = (F(2), F(-1), F(3, 5)), F(7, 3), F(2)
        psi = auxiliary_polynomial(h, gain)
        normalized_h = transformed_polynomial(h, duration, time_basis="unit_interval")[0]
        normalized_psi = transformed_polynomial(psi, duration, time_basis="unit_interval")[0]
        self.assertEqual(auxiliary_polynomial(normalized_h, duration*gain), tuple(duration*c for c in normalized_psi))
        self.assertNotEqual(auxiliary_polynomial(normalized_h, gain), tuple(duration*c for c in normalized_psi))

    def test_zero_margin_and_precision_stops_remain_unknown(self):
        p = [F(9, 100), F(-3, 5), F(1)]
        for method in METHODS:
            for scale in (F(1, 10**6), F(10**6)):
                result = representation_certificate(method, p, 1, scale*F("1e-12"), 64, scale)
                self.assertEqual(result["certificate"]["status"], "unknown")
                self.assertTrue(result["certificate"]["precision_reached"])

    def test_invalid_or_inexact_transformations_are_rejected(self):
        for changes in ({"scale": 0}, {"scale": -1}, {"scale": True}, {"scale": 0.1},
                        {"time_basis": "wrong"}, {"method": "unsupported"}, {"budget": True}, {"budget": -1},
                        {"tolerance": 0}, {"duration": 0}, {"coefficients": []}, {"coefficients": [1.0]}):
            with self.assertRaises(ValueError):
                representation_certificate(**({"method": "bernstein_sign", "coefficients": [1, -1],
                                               "duration": 1, "tolerance": "1e-12", "budget": 8} | changes))


if __name__ == "__main__":
    unittest.main()
