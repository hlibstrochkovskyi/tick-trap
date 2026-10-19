"""Analytical zero-order-hold dynamics; no integration step or contact model."""

from dataclasses import dataclass
from fractions import Fraction

from .numbers import nonnegative, positive, q, vector2


@dataclass(frozen=True)
class WallState:
    d: Fraction
    v: Fraction

    def __post_init__(self):
        object.__setattr__(self, "d", q(self.d))
        object.__setattr__(self, "v", q(self.v))

    def at(self, u, t):
        u, t = q(u), nonnegative(t, "time")
        return WallState(self.d - self.v * t - u * t**2 / 2, self.v + u * t)

    def viability_margin(self, a_max):
        a_max = positive(a_max, "a_max")
        return self.d - max(self.v, 0)**2 / (2 * a_max)

    def minimum(self, u, duration):
        """Return exact (clearance, witness time) on a closed hold interval."""
        u, duration = q(u), positive(duration, "duration")
        candidates = [Fraction(0), duration]
        if u < 0:
            critical = -self.v / u
            if 0 < critical < duration:
                candidates.append(critical)
        return min((self.at(u, t).d, t) for t in candidates)


@dataclass(frozen=True)
class PlanarState:
    p: tuple
    v: tuple

    def __post_init__(self):
        object.__setattr__(self, "p", vector2(self.p))
        object.__setattr__(self, "v", vector2(self.v))

    def at(self, u, t):
        u, t = vector2(u), nonnegative(t, "time")
        return PlanarState(
            tuple(p + v*t + a*t*t/2 for p, v, a in zip(self.p, self.v, u)),
            tuple(v + a*t for v, a in zip(self.v, u)),
        )


@dataclass(frozen=True)
class Circle:
    center: tuple
    radius: Fraction

    def __post_init__(self):
        object.__setattr__(self, "center", vector2(self.center))
        object.__setattr__(self, "radius", positive(self.radius, "total collision radius"))

    def polynomial(self, state, u):
        """Ascending powers of ||p(t)-c||²-R², in square metres."""
        u = vector2(u)
        r = tuple(p-c for p, c in zip(state.p, self.center))
        dot = lambda a, b: sum(x*y for x, y in zip(a, b))
        return (dot(r, r)-self.radius**2, 2*dot(r, state.v),
                dot(state.v, state.v)+dot(r, u), dot(state.v, u), dot(u, u)/4)
