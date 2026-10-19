import random
import unittest
from fractions import Fraction as F

from tick_trap.qp import HalfSpace, project_box


class ProjectionTests(unittest.TestCase):
    def test_slanted_boundary_projection(self):
        result = project_box((0, 0), [HalfSpace((1, 1), 1, "diagonal")], 2)
        self.assertEqual(result.action, (F(1, 2), F(1, 2)))
        self.assertEqual(result.cost, F(1, 2))
        self.assertIn("diagonal", result.active)
        self.assertTrue(all(r <= 0 for r in result.residuals))

    def test_vertex_and_actuator_projection(self):
        result = project_box((-10, -10), [HalfSpace((1, 0), 1), HalfSpace((0, 1), 2)], 3)
        self.assertEqual(result.action, (F(1), F(2)))
        self.assertEqual(project_box((10, -10), [], 2).action, (F(2), F(-2)))

    def test_infeasible_and_degenerate_polygons(self):
        self.assertEqual(project_box((0, 0), [HalfSpace((1, 0), 2)], 1).status, "infeasible")
        self.assertEqual(project_box((0, 0), [HalfSpace((0, 0), 1)], 1).status, "infeasible")
        constraints = [HalfSpace((1, 0), 0), HalfSpace((-1, 0), 0),
                       HalfSpace((0, 1), 0), HalfSpace((0, -1), 0), HalfSpace((0, 0), 0)]
        self.assertEqual(project_box((1, 1), constraints, 2).action, (F(0), F(0)))

    def test_random_projections_dominate_independent_feasible_grid(self):
        rng = random.Random(481)
        for _ in range(25):
            nominal = (F(rng.randint(-30, 30), 10), F(rng.randint(-30, 30), 10))
            # The origin is feasible, but arbitrary slanted boundaries can bind.
            constraints = [HalfSpace((rng.randint(-3, 3), rng.randint(-3, 3)), -rng.randint(0, 3))
                           for _ in range(4)]
            result = project_box(nominal, constraints, 1)
            self.assertEqual(result.status, "feasible")
            for x in range(-10, 11):
                for y in range(-10, 11):
                    point = (F(x, 10), F(y, 10))
                    if all(c.residual(point) <= 0 for c in constraints):
                        cost = sum((p-n)**2 for p, n in zip(point, nominal))
                        self.assertLessEqual(result.cost, cost)

    def test_exact_small_residuals_are_not_tolerated(self):
        constraint = HalfSpace((1, 0), F(1, 10**20))
        self.assertGreater(constraint.residual((0, 0)), 0)
        self.assertEqual(project_box((0, 0), [constraint], 1).action, (F(1, 10**20), F(0)))


if __name__ == "__main__":
    unittest.main()
