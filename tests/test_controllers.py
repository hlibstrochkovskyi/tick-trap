import unittest
from fractions import Fraction as F

from tick_trap.controllers import METHODS, decide, inequality_residual
from tick_trap.dynamics import WallState


class ControllerTests(unittest.TestCase):
    def test_viable_state_endpoint_filter_can_collide_between_samples(self):
        state = WallState("0.06", 1)
        self.assertGreater(state.viability_margin(10), 0)
        decision = decide("endpoint", state, 0, "0.4", 10)
        self.assertEqual(decision.action, F("-4.25"))
        self.assertEqual(state.at(decision.action, "0.4").d, 0)
        self.assertLess(state.minimum(decision.action, "0.4")[0], 0)

    def test_cbf_projection_and_residual(self):
        state = WallState(1, 1)
        decision = decide("continuous_cbf", state, 10, "0.1", 10)
        self.assertEqual(decision.action, F(4, 3))
        self.assertEqual(-state.v-F("0.3")*decision.action+2*(state.d-F("0.3")*state.v), 0)
        self.assertEqual(decision.residual, 0)
        self.assertEqual(inequality_residual(2, "0.499", 1), F("0.002"))

    def test_published_constants_independently_checked(self):
        state = WallState(100, 0)
        breeden = decide("breeden", state, 0, "0.75", 4, tau="0.75", gain=4)
        self.assertEqual(F(breeden.details["margin_exact"]), F("22.5"))
        zocbf = decide("zocbf", state, 0, "0.75", 4)
        self.assertEqual(F(zocbf.details["delta_exact"]), F("3.75"))

    def test_explicit_infeasibility_and_domain(self):
        state = WallState("0.04", 1)
        self.assertEqual(decide("exact_hold", state, 0, "0.2", 10).status, "infeasible")
        self.assertEqual(decide("breeden", state, 0, "0.2", 10).status, "outside_domain")
        self.assertEqual(decide("zocbf", WallState(0, 0), 0, "0.2", 10).status, "infeasible")

    def test_exact_reference_preserves_hold_and_viability_on_grid(self):
        for v in [-2, 0, 1, 3]:
            for extra in [F(0), F(1, 100), F(1)]:
                state = WallState(F(max(v, 0)**2, 20)+extra, v)
                for duration in [F(1, 100), F(1, 5), F(1)]:
                    result = decide("exact_hold", state, 10, duration, 10)
                    self.assertEqual(result.status, "feasible")
                    self.assertGreaterEqual(state.minimum(result.action, duration)[0], 0)
                    self.assertGreaterEqual(state.at(result.action, duration).viability_margin(10), 0)
                    self.assertLessEqual(abs(result.action), 10)

    def test_sampled_data_conditions_imply_hold_safety_when_feasible(self):
        feasible = {"breeden": 0, "zocbf": 0}
        for method in feasible:
            for d in [F(1, 2), F(1), F(3)]:
                for v in [-1, 0, 1]:
                    for duration in [F(1, 100), F(1, 10)]:
                        state = WallState(d, v)
                        decision = decide(method, state, 10, duration, 10)
                        if decision.status == "feasible":
                            feasible[method] += 1
                            self.assertGreaterEqual(state.minimum(decision.action, duration)[0], 0)
                            if method == "breeden":
                                # Independent minimization of d(t)-tau*v(t).
                                bstate = WallState(d-F("0.3")*v, v+F("0.3")*decision.action)
                                self.assertGreaterEqual(bstate.minimum(decision.action, duration)[0], 0)
        self.assertTrue(all(count > 0 for count in feasible.values()))

    def test_parameter_validation(self):
        for kwargs in [{"method": "unknown"}, {"gamma": 2}, {"tau": 0}, {"duration": 0}]:
            args = dict(method="endpoint", state=WallState(1, 0), nominal=0, duration=1, a_max=10)
            with self.assertRaises(ValueError):
                decide(**(args | kwargs))


if __name__ == "__main__":
    unittest.main()
