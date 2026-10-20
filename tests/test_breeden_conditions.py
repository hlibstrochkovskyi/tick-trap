from fractions import Fraction as F
from itertools import product
import unittest

from tick_trap.algebraic_reference import exact_sign_reference
from tick_trap.controllers import decide
from tick_trap.dynamics import WallState


class BreedenConditionTests(unittest.TestCase):
    def test_reachable_supremum_matches_a_reachable_endpoint_or_the_initial_state(self):
        for velocity in (-20, -2, 0, 1, 5):
            for duration, tau, gain in ((F(1, 10), F(3, 10), F(2)), (F(3, 4), F(3, 4), F(4))):
                state, a = WallState(100, velocity), F(4)
                decision = decide("breeden_reachable", state, 0, duration, a, tau, gain)
                margin = F(decision.details["margin_exact"])
                # Evaluate the paper's Lie-derivative error directly at a state,
                # rather than using the implemented quadratic coefficient formula.
                def error(end):
                    return end.v-state.v-gain*((end.d-tau*end.v)-(state.d-tau*state.v))
                self.assertEqual(margin, max(F(0), error(state.at(a, duration))))
                time = F(decision.details["supremum_time_exact"])
                self.assertEqual(error(state.at(a, time)), margin)
                for controls in product((-a, F(0), a), repeat=3):
                    end = state
                    for control in controls:
                        end = end.at(control, duration/3)
                        self.assertLessEqual(error(end), margin)

    def test_zero_reachable_margin_for_fast_departing_motion(self):
        state = WallState(1, -20)
        local = decide("breeden_reachable", state, 10, "0.1", 10)
        continuous = decide("continuous_cbf", state, 10, "0.1", 10)
        self.assertEqual(local.details["margin_exact"], "0")
        self.assertEqual(local.action, continuous.action)

    def test_existing_lipschitz_condition_is_no_less_conservative_at_equal_gain(self):
        for velocity, duration in product((-10, -1, 0, 1, 3), (F(1, 100), F(1, 10), F(2, 5))):
            state = WallState(10, velocity)
            old = decide("breeden", state, 10, duration, 10)
            local = decide("breeden_reachable", state, 10, duration, 10)
            self.assertLessEqual(F(local.details["margin_exact"]), F(old.details["margin_exact"]))
            if old.status == "feasible":
                self.assertEqual(local.status, "feasible")
                self.assertGreaterEqual(local.action, old.action)

    def test_second_order_constants_projection_and_effective_gain(self):
        state = WallState("0.6", 1)
        decision = decide("breeden_second_order", state, 10, "0.1", 10)
        self.assertEqual(decision.action, 5)
        self.assertEqual(decision.details["second_derivative_upper_exact"], "10")
        self.assertEqual(decision.details["margin_exact"], "1/2")
        self.assertEqual(decision.details["effective_gain_exact"], "10")
        self.assertEqual(decide("breeden_second_order", state, 10, "0.1", 10, gain=100), decision)
        self.assertEqual(decision.residual, 0)
        self.assertLess(decide("breeden_second_order", state, 10, "0.1", 10, gamma="0.5").action, decision.action)

    def test_feasible_actions_preserve_barrier_and_geometry_with_independent_sign_checks(self):
        counts = {m: 0 for m in ("breeden_reachable", "breeden_second_order")}
        for method, d, velocity, duration, nominal in product(counts, (F(3, 10), F(1), F(5)),
                                                            (-2, 0, 1, 3), (F(1, 20), F(1, 5), F(1)), (-10, 0, 10)):
            state, tau = WallState(d, velocity), F(3, 10)
            decision = decide(method, state, nominal, duration, 10, tau)
            if decision.status != "feasible":
                continue
            counts[method] += 1
            u = decision.action
            geometric = [state.d, -state.v, -u/2]
            barrier = [state.d-tau*state.v, -state.v-tau*u, -u/2]
            self.assertEqual(exact_sign_reference(geometric, duration)["status"], "safe")
            self.assertEqual(exact_sign_reference(barrier, duration)["status"], "safe")
            self.assertLessEqual(abs(u), 10)
        self.assertTrue(all(c > 0 for c in counts.values()))

    def test_initial_domain_and_pointwise_infeasibility_are_explicit(self):
        for method in ("breeden_reachable", "breeden_second_order"):
            self.assertEqual(decide(method, WallState("0.1", 1), 0, "0.1", 10).status, "outside_domain")
            self.assertEqual(decide(method, WallState("0.3", 1), 0, 1, 10).status, "infeasible")
            self.assertIsNone(decide(method, WallState("0.3", 1), 0, 1, 10).action)


if __name__ == "__main__":
    unittest.main()
