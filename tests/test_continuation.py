import unittest
from fractions import Fraction as F

from tick_trap.continuation import PlanPiece, assess_stopping, certify_segment, prepend_hold
from tick_trap.dynamics import Circle, PlanarState
from tick_trap.polynomial import certify_minimum


class ContinuationTests(unittest.TestCase):
    def test_consuming_the_plan_reaches_rest_without_recertification(self):
        state = PlanarState((-10, -10), ("1.13", "0.47"))
        obstacles = (Circle((0, 0), "0.5"),)
        assessment = assess_stopping(state, obstacles, "0.1", 2, command_quantum="0.1")
        plan = assessment.continuation
        self.assertIsNotNone(plan)
        original_proofs = plan.proofs
        for _ in range(assessment.record()["steps"]):
            self.assertTrue(plan.matches(state, obstacles))
            action = plan.next_action
            for obstacle in obstacles:
                self.assertEqual(certify_minimum(obstacle.polynomial(state, action), F("0.1")).status, "safe")
            state = state.at(action, "0.1")
            plan = plan.advance()
            self.assertIs(plan.proofs, original_proofs)
        self.assertEqual(state.v, (0, 0))
        self.assertEqual(plan.next_action, (0, 0))
        self.assertEqual(plan.advance(), plan)
        self.assertEqual(plan.state, assessment.continuation.terminal_state)

    def test_shifted_proof_keeps_original_interval_scope(self):
        assessment = assess_stopping(PlanarState((-2, 0), (1, 0)), (Circle((0, 0), "0.5"),), "0.1", 2)
        before = assessment.continuation.record()
        after = assessment.continuation.advance().record()
        self.assertEqual(before["original_proofs"], after["original_proofs"])
        self.assertEqual(after["remaining_steps"], before["remaining_steps"]-1)
        self.assertEqual(after["consumed_steps"], 1)
        self.assertNotEqual(before["expected_state"], after["expected_state"])

    def test_new_hold_composes_only_with_its_actual_end_state(self):
        state = PlanarState((-5, 0), (1, 0))
        obstacles = (Circle((0, 0), 1),)
        proof = certify_segment(state, (0, 0), 1, obstacles, "0.1", 2)
        end = state.at((0, 0), "0.1")
        tail = assess_stopping(end, obstacles, "0.1", 2).continuation
        combined = prepend_hold(proof, tail)
        self.assertEqual(combined.advance().state, tail.state)
        self.assertEqual(combined.advance().pieces, tail.pieces)
        wrong = assess_stopping(state, obstacles, "0.1", 2).continuation
        with self.assertRaises(ValueError):
            prepend_hold(proof, wrong)

    def test_unsafe_unknown_and_lattice_failures_never_produce_a_plan(self):
        unsafe = assess_stopping(PlanarState(("1.01", 0), (-10, 0)), (Circle((0, 0), 1),), "0.1", 2)
        self.assertEqual(unsafe.status, "unsafe")
        self.assertIsNone(unsafe.continuation)
        # The stopping path touches a circle at a non-dyadic polynomial time.
        unknown = assess_stopping(PlanarState(("-0.3", 1), (1, 0)), (Circle((0, 0), 1),), "0.1", 1,
                                  max_subdivisions=0)
        self.assertEqual(unknown.status, "unknown")
        self.assertIsNone(unknown.continuation)
        lattice = assess_stopping(PlanarState((-10, 0), ("1.131", 0)), (), "0.1", 2, command_quantum="0.1")
        self.assertEqual(lattice.status, "not_constructed")
        self.assertIsNone(lattice.continuation)

    def test_even_degenerate_inputs_validate_certificate_and_command_limits(self):
        for kwargs in [{"tolerance": 0}, {"max_subdivisions": -1}, {"command_quantum": 3}]:
            with self.assertRaises(ValueError):
                assess_stopping(PlanarState((0, 0), (0, 0)), (), "0.1", 2, **kwargs)
        for action in [(3, 0), (F(1, 3), 0)]:
            with self.assertRaises(ValueError):
                certify_segment(PlanarState((0, 0), (0, 0)), action, 1, (), "0.1", 2)
        with self.assertRaises(ValueError):
            PlanPiece((0, 0), 0)


if __name__ == "__main__":
    unittest.main()
