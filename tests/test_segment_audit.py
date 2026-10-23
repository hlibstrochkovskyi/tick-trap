from copy import deepcopy
from fractions import Fraction as F
import unittest

from tick_trap.dynamics import Circle, PlanarState
from tick_trap.segment_audit import (segment_contract_study, segment_hold_audit,
                                     verify_segment_contract_study)


class SegmentAuditTests(unittest.TestCase):
    def audit(self, p, v, u, radius=1, center=(0, 0), duration=1, a_max=32):
        return segment_hold_audit(PlanarState(p, v), u, Circle(center, radius), duration, a_max)

    def test_chord_and_physical_path_can_disagree_in_both_directions(self):
        inward = self.audit((F("0.04"), 0), (-1, 0), (10, 0), center=(-1, 0), duration="0.2")
        self.assertEqual((inward["sampled_status"], inward["chord_status"],
                          inward["trajectory_reference"]["status"], inward["tube_status"]),
                         ("safe", "safe", "unsafe", "unknown"))
        self.assertEqual(F(inward["deviation_squared_peak_exact"]), F(1, 400))
        # h(t) = (1-2t)^2 + 16*t^2*(1-t)^2 - 1/4.
        # With s=t*(1-t), h=16*(s-1/8)^2+1/2 > 0.
        outward = self.audit((-1, 0), (2, 4), (0, -8), radius=F(1, 2))
        self.assertEqual((outward["chord_status"], outward["trajectory_reference"]["status"],
                          outward["tube_status"]), ("unsafe", "safe", "unknown"))

    def test_peak_deviation_matches_independently_evaluated_paths(self):
        state, u, duration = PlanarState((2, -3), (5, 7)), (F(6), F(8)), F(2, 3)
        record = segment_hold_audit(state, u, Circle((20, 20), 1), duration, 10)
        peak = F(record["deviation_squared_peak_exact"])
        for s in (F(0), F(1, 5), F(1, 2), F(9, 10), F(1)):
            physical = state.at(u, duration*s).p
            end = state.at(u, duration).p
            chord = tuple((1-s)*p+s*e for p, e in zip(state.p, end))
            gap = sum((a-b)**2 for a, b in zip(physical, chord))
            self.assertLessEqual(gap, peak)
            if s == F(1, 2):
                self.assertEqual(gap, peak)
        # ||u||=10, T=2/3, so the exact peak distance is 5/9.
        self.assertEqual(peak, F(25, 81))

    def test_tube_boundary_and_arbitrarily_small_signed_perturbations(self):
        epsilon = F(1, 10**80)
        # p(.5)=(0,y-1) and the chord lies at height y; peak deviation=1.
        for delta, expected in ((epsilon, "safe"), (F(0), "safe"), (-epsilon, "unsafe")):
            record = self.audit((-1, 2+delta), (2, -4), (0, 8))
            self.assertEqual(record["trajectory_reference"]["status"], expected)
            self.assertEqual(record["tube_status"], "safe" if delta >= 0 else "unknown")
        self.assertEqual(F(self.audit((-1, 2), (2, -4), (0, 8))["tube_squared_slack_exact"]), 0)

    def test_zero_acceleration_reduces_to_exact_chord_including_tangency(self):
        epsilon = F(1, 10**80)
        for delta, expected in ((epsilon, "safe"), (F(0), "safe"), (-epsilon, "unsafe")):
            record = self.audit((-1, 1+delta), (2, 0), (0, 0))
            self.assertEqual(record["chord_status"], expected)
            self.assertEqual(record["trajectory_reference"]["status"], expected)
            self.assertEqual(record["tube_status"], "safe" if expected == "safe" else "unknown")
        stationary = self.audit((2, 0), (0, 0), (0, 0))
        self.assertEqual(F(stationary["chord_minimum_barrier_exact"]), 3)
        self.assertEqual(stationary["tube_status"], "safe")

    def test_squaring_does_not_lose_sign_guard_or_cross_term(self):
        sign_trap = self.audit((0, 0), (0, -16), (0, 32))
        self.assertLess(F(sign_trap["tube_excess_exact"]), 0)
        self.assertGreater(F(sign_trap["tube_squared_slack_exact"]), 0)
        self.assertEqual(sign_trap["tube_status"], "unknown")
        # D²=9/4 > R²+rho²=2 is insufficient: D=3/2 < R+rho=2.
        cross_term = self.audit((-1, F(3, 2)), (2, -4), (0, 8))
        self.assertGreater(F(cross_term["tube_excess_exact"]), 0)
        self.assertLess(F(cross_term["tube_squared_slack_exact"]), 0)
        self.assertEqual((cross_term["tube_status"], cross_term["trajectory_reference"]["status"]),
                         ("unknown", "unsafe"))

    def test_rigid_coordinate_change_preserves_exact_assessment(self):
        record = self.audit((2, 0), (F(-1, 2), F(-1, 2)), (1, 1))
        # Rotate (x,y)->(-y,x), then translate (7,-2), including the center.
        transformed = self.audit((7, 0), (F(1, 2), F(-1, 2)), (-1, 1), center=(7, -2))
        self.assertEqual(record, transformed)
        self.assertEqual(record["tube_status"], "safe")

    def test_study_keeps_joint_unknown_and_rejects_changed_proof_evidence(self):
        spec = {"cases": [{"name": "two_obstacles", "p": [-1, 1], "v": [2, 4], "action": [0, -8],
                            "duration": 1, "a_max": 8, "obstacles": [
                                {"center": [0, 0], "radius": 1}, {"center": [20, 20], "radius": 1}]}]}
        saved = segment_contract_study(spec)
        self.assertEqual(saved["counts"]["tube_unknown_safe"], 1)
        self.assertEqual(saved["records"][0]["tube_status"], "unknown")
        self.assertEqual(saved["records"][0]["obstacles"][1]["tube_status"], "safe")
        self.assertEqual(verify_segment_contract_study(spec, saved)["status"], "verified")
        corrupted = deepcopy(saved)
        corrupted["records"][0]["obstacles"][0]["trajectory_reference"]["probe_time_exact"] = "0"
        with self.assertRaises(ValueError):
            verify_segment_contract_study(spec, corrupted)
        for change in ({"cases": []}, {"cases": spec["cases"]*2}):
            with self.assertRaises(ValueError):
                segment_contract_study(change)
        moving = deepcopy(spec)
        moving["cases"][0]["obstacles"][0]["velocity"] = [1, 0]
        with self.assertRaises(ValueError):
            segment_contract_study(moving)

    def test_invalid_or_inadmissible_hold_is_not_certified(self):
        for changes in ({"duration": 0}, {"duration": 0.5}, {"a_max": True}, {"a_max": 7}):
            with self.assertRaises(ValueError):
                self.audit((-1, 2), (2, -4), (0, 8), **changes)
        with self.assertRaises(ValueError):
            self.audit((-1, 2), (2, -4), (0, 8.0))


if __name__ == "__main__":
    unittest.main()
