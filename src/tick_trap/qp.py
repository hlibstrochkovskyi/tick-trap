"""Exact Euclidean projection onto a bounded two-dimensional polyhedron.

This small reference solver enumerates zero, one and two active boundaries.
It is intended for low-dimensional validation, not as a general QP backend.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from .numbers import positive, q, vector2


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


@dataclass(frozen=True)
class HalfSpace:
    normal: tuple
    rhs: Fraction
    name: str = "constraint"

    def __post_init__(self):
        object.__setattr__(self, "normal", vector2(self.normal))
        object.__setattr__(self, "rhs", q(self.rhs))

    def residual(self, action):
        """Positive means violation of normal dot action >= rhs."""
        return self.rhs-dot(self.normal, vector2(action))


@dataclass(frozen=True)
class Projection:
    status: str
    action: tuple | None = None
    cost: Fraction | None = None
    residuals: tuple = ()
    active: tuple = ()


def project_box(nominal, constraints, a_max):
    """Minimize ||action-nominal||² subject to half-spaces and |u_i|<=a.

    The actuator box is compact. A nonempty feasible set has a unique minimizer,
    lying at nominal, a boundary projection, or a boundary intersection. Those
    candidates also cover lower-dimensional feasible sets. All feasibility and
    objective comparisons use exact rationals; no solver tolerance is hidden.
    """
    nominal, a_max = vector2(nominal), positive(a_max, "a_max")
    constraints = tuple(constraints)+(
        HalfSpace((1, 0), -a_max, "u_x_min"), HalfSpace((-1, 0), -a_max, "u_x_max"),
        HalfSpace((0, 1), -a_max, "u_y_min"), HalfSpace((0, -1), -a_max, "u_y_max"),
    )
    candidates = {nominal}
    for constraint in constraints:
        norm = dot(constraint.normal, constraint.normal)
        if norm == 0:
            if constraint.rhs > 0:
                return Projection("infeasible")
            continue
        shift = constraint.residual(nominal)/norm
        candidates.add(tuple(u+shift*n for u, n in zip(nominal, constraint.normal)))
    for first, second in combinations(constraints, 2):
        x1, y1 = first.normal
        x2, y2 = second.normal
        determinant = x1*y2-y1*x2
        if determinant:
            candidates.add(((first.rhs*y2-y1*second.rhs)/determinant,
                            (x1*second.rhs-first.rhs*x2)/determinant))
    feasible = [u for u in candidates if all(c.residual(u) <= 0 for c in constraints)]
    if not feasible:
        return Projection("infeasible")
    cost = lambda u: sum((x-y)**2 for x, y in zip(u, nominal))
    action = min(feasible, key=lambda u: (cost(u), u))
    residuals = tuple(c.residual(action) for c in constraints)
    active = tuple(c.name for c, residual in zip(constraints, residuals) if residual == 0)
    return Projection("feasible", action, cost(action), residuals, active)
