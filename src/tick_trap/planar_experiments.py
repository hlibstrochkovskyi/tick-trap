"""Matched-horizon planar experiments with explicit certificate outcomes."""

from dataclasses import asdict, dataclass, field, fields
from fractions import Fraction
from itertools import product
from time import perf_counter_ns

from .dynamics import Circle, PlanarState
from .numbers import nonnegative, positive, q, vector2
from .oracle import circle_interval
from .planar_control import PLANAR_METHODS, decide_planar, hocbf_constraints
from .polynomial import certify_minimum
from .qp import dot


def _encode(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encode(item) for item in value]
    return value


def _state_record(state):
    return {"p": [float(x) for x in state.p], "v": [float(x) for x in state.v],
            "p_exact": [str(x) for x in state.p], "v_exact": [str(x) for x in state.v]}


def braking_continuation(state, obstacles, duration, a_max, tolerance="1e-12", max_subdivisions=4096,
                         command_quantum="1e-6"):
    """Certify a particular admissible plan to rest on a future update boundary.

    Failure of this plan does not establish nonviability. Saturated componentwise
    braking, residual commands at update boundaries, and then zero define a future
    plan. It respects both actuator bounds and the declared command quantum.
    """
    duration, a_max = positive(duration, "duration"), positive(a_max, "a_max")
    quantum = positive(command_quantum, "command_quantum")
    limit = a_max/quantum
    if limit.denominator != 1:
        raise ValueError("a_max must be an integer multiple of command_quantum")
    velocity_units = tuple(v/(duration*quantum) for v in state.v)
    if any(n.denominator != 1 for n in velocity_units):
        return {"viability": "unknown", "plan_status": "not_constructed", "pieces": [],
                "reason": "Velocity cannot reach exact rest on this update/command lattice"}
    stop_steps = tuple((abs(n.numerator)+int(limit)-1)//int(limit) for n in velocity_units)
    steps = max(stop_steps)
    if not steps:
        safe = all(o.polynomial(state, (0, 0))[0] >= 0 for o in obstacles)
        return {"viability": "certified" if safe else "unknown", "plan_status": "safe" if safe else "unsafe",
                "steps": 0, "pieces": [], "certificates": []}
    # At most five constant-input pieces, even for very large stopping horizons.
    boundaries = sorted({0, *stop_steps, *(n-1 for n in stop_steps if n)})
    current, certificates, pieces = state, [], []
    for start, end in zip(boundaries, boundaries[1:]):
        action = tuple(-min(a_max, abs(v)/duration)*(1 if v > 0 else -1 if v < 0 else 0) for v in current.v)
        dt = (end-start)*duration
        segment = [certify_minimum(o.polynomial(current, action), dt, tolerance, max_subdivisions) for o in obstacles]
        certificates.extend(segment)
        pieces.append({"steps": end-start, "duration_exact": str(dt), "action_exact": [str(x) for x in action],
                       "statuses": [c.status for c in segment]})
        current = current.at(action, dt)
    if current.v != (0, 0):
        raise ArithmeticError("Stopping-plan construction did not reach rest")
    statuses = [c.status for c in certificates]
    status = "unsafe" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "safe"
    return {"viability": "certified" if status == "safe" else "unknown", "plan_status": status,
            "steps": steps, "duration_exact": str(steps*duration), "pieces": pieces,
            "certificates": [{"status": c.status, "lower_exact": str(c.lower), "upper_exact": str(c.upper),
                              "witness_time_exact": str(c.witness_time)} for c in certificates],
            "command_scope": "configured actuator bounds, update period and command quantum"}


@dataclass(frozen=True)
class PlanarConfig:
    method: str = "trajectory_candidates"
    p: tuple = ("-2", "0.7")
    v: tuple = ("1", "0")
    goal: tuple = ("2", "0.7")
    obstacles: tuple = field(default_factory=lambda: (Circle((0, 0), "0.5"),))
    duration: str = "0.1"
    horizon: str = "4"
    a_max: str = "2"
    nominal_policy: str = "pd"
    nominal: tuple = ("0", "0")
    position_gain: str = "1"
    velocity_gain: str = "2"
    position_tolerance: str = "0.05"
    speed_tolerance: str = "0.1"
    lambda1: str = "2"
    lambda2: str = "2"
    gamma: str = "1"
    grid_points: int = 5
    command_quantum: str = "1e-6"
    tolerance: str = "1e-10"
    max_subdivisions: int = 256
    oracle_tolerance: str = "1e-12"
    oracle_max_subdivisions: int = 4096
    deadline: str | None = None

    def __post_init__(self):
        if self.method not in PLANAR_METHODS:
            raise ValueError(f"Unknown planar method {self.method!r}")
        if self.nominal_policy not in ("pd", "constant"):
            raise ValueError("nominal_policy must be 'pd' or 'constant'")
        for name in ("p", "v", "goal", "nominal"):
            object.__setattr__(self, name, vector2(getattr(self, name)))
        for name in ("duration", "horizon", "a_max", "position_gain", "velocity_gain", "lambda1", "lambda2",
                     "gamma", "command_quantum", "tolerance", "oracle_tolerance"):
            positive(getattr(self, name), name)
        for name in ("position_tolerance", "speed_tolerance"):
            nonnegative(getattr(self, name), name)
        for name in ("max_subdivisions", "oracle_max_subdivisions", "grid_points"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < (2 if name == "grid_points" else 0):
                raise ValueError(f"Invalid {name}")
        if q(self.gamma) > 1:
            raise ValueError("gamma must be in (0,1]")
        if (q(self.horizon)/q(self.duration)).denominator != 1:
            raise ValueError("horizon must be an integer multiple of duration")
        if (q(self.a_max)/q(self.command_quantum)).denominator != 1:
            raise ValueError("a_max must be an integer multiple of command_quantum")
        if self.deadline is not None:
            positive(self.deadline, "deadline")
        object.__setattr__(self, "obstacles", tuple(o if isinstance(o, Circle) else Circle(**o) for o in self.obstacles))

    def record(self):
        return _encode(asdict(self))


def run_planar(config: PlanarConfig):
    state = PlanarState(config.p, config.v)
    obstacles = config.obstacles
    duration, a_max = q(config.duration), q(config.a_max)
    steps = int(q(config.horizon)/duration)
    deadline = q(config.deadline) if config.deadline is not None else duration
    initial_safe = all(o.polynomial(state, (0, 0))[0] >= 0 for o in obstacles)
    initial_braking = braking_continuation(state, obstacles, duration, a_max,
                                           config.oracle_tolerance, config.oracle_max_subdivisions, config.command_quantum)
    _, initial_domains = hocbf_constraints(state, obstacles, config.lambda1, config.lambda2)
    records, termination = [], "horizon" if initial_safe else "initially_unsafe"
    goal_first_time = None

    def at_goal(current):
        error = tuple(p-g for p, g in zip(current.p, config.goal))
        return dot(error, error) <= q(config.position_tolerance)**2 and dot(current.v, current.v) <= q(config.speed_tolerance)**2

    if at_goal(state):
        goal_first_time = "0"
    if initial_safe:
        for index in range(steps):
            nominal = config.nominal if config.nominal_policy == "constant" else tuple(
                q(config.position_gain)*(g-p)-q(config.velocity_gain)*v
                for g, p, v in zip(config.goal, state.p, state.v))
            start = perf_counter_ns()
            decision = decide_planar(config.method, state, nominal, obstacles, duration, a_max,
                                     config.lambda1, config.lambda2, config.gamma, config.grid_points,
                                     config.command_quantum, config.tolerance, config.max_subdivisions)
            solve_ns = perf_counter_ns()-start
            record = {"step": index, "time_exact": str(index*duration), "state": _state_record(state),
                      "nominal_exact": [str(x) for x in nominal], "decision": decision.status,
                      "reason": decision.reason, "details": decision.details, "solve_ns": solve_ns,
                      "deadline_missed": Fraction(solve_ns, 10**9) > deadline}
            records.append(record)
            if decision.status != "feasible":
                termination = decision.status
                break
            action = decision.action
            checks = [circle_interval(state, action, o, duration, config.oracle_tolerance,
                                      config.oracle_max_subdivisions) for o in obstacles]
            statuses = [r["continuous_status"] for r in checks]
            continuous = "unsafe" if "unsafe" in statuses else "unknown" if "unknown" in statuses else "safe"
            end = state.at(action, duration)
            start = perf_counter_ns()
            continuation = braking_continuation(end, obstacles, duration, a_max,
                                                config.oracle_tolerance, config.oracle_max_subdivisions, config.command_quantum)
            continuation_ns = perf_counter_ns()-start
            record.update({"action_exact": [str(x) for x in action], "action": [float(x) for x in action],
                           "end_state": _state_record(end), "obstacles": checks,
                           "sampled_safe": all(r["sampled_safe"] for r in checks), "continuous_status": continuous,
                           "certification_ns": sum(r["certification_ns"] for r in checks),
                           "estimation_ns": sum(r["estimation_ns"] for r in checks),
                           "continuation": continuation, "continuation_check_ns": continuation_ns,
                           "intervention_squared_exact": str(sum((a-n)**2 for a, n in zip(action, nominal)))})
            state = end
            if at_goal(state) and goal_first_time is None:
                goal_first_time = str((index+1)*duration)
            if continuous != "safe":
                termination = "collision_interval" if continuous == "unsafe" else "oracle_unresolved"
                break
    executed = [r for r in records if "action_exact" in r]
    all_checks = [check for r in executed for check in r["obstacles"]]
    collision = any(r["continuous_status"] == "unsafe" for r in executed)
    observed = "unsafe" if collision else "unknown" if any(r["continuous_status"] == "unknown" for r in executed) else "safe" if executed else "not_executed"
    return {"config": config.record(), "initial_geometric_safe": initial_safe,
            "initial_viability": initial_braking["viability"], "initial_braking": initial_braking,
            "initial_hocbf_domain": all(d["in_domain"] for d in initial_domains),
            "viability_scope": "sufficient admissible stopping-plan check, not the full planar viability kernel",
            "termination": termination, "executed_steps": len(executed),
            "completed_safe_horizon": termination == "horizon" and observed == "safe",
            "sampled_safe_observed": initial_safe and all(r["sampled_safe"] for r in executed),
            "observed_continuous_status": observed, "collision_observed": collision,
            "minimum_barrier_lower_exact": str(min(q(c["minimum_lower_exact"]) for c in all_checks)) if all_checks else None,
            "minimum_barrier_upper_exact": str(min(q(c["minimum_upper_exact"]) for c in all_checks)) if all_checks else None,
            "minimum_clearance_estimate": min((c["clearance_estimate"] for c in all_checks), default=None),
            "goal_reached_at_end": at_goal(state), "goal_first_time_exact": goal_first_time,
            "final_state": _state_record(state), "deadline_misses": sum(r["deadline_missed"] for r in records),
            "solve_ns_total": sum(r["solve_ns"] for r in records),
            "certification_ns_total": sum(r["certification_ns"] for r in executed), "records": records}


def load_planar_grid(spec):
    if not isinstance(spec, dict) or set(spec)-{"base", "grid"}:
        raise ValueError("Planar experiment accepts only 'base' and 'grid' objects")
    base, grid = spec.get("base", {}), spec.get("grid", {})
    if not isinstance(base, dict) or not isinstance(grid, dict):
        raise ValueError("base and grid must be objects")
    valid = {f.name for f in fields(PlanarConfig)}
    if (set(base) | set(grid))-valid:
        raise ValueError(f"Unknown planar configuration fields: {(set(base) | set(grid))-valid}")
    if any(not isinstance(values, list) or not values for values in grid.values()):
        raise ValueError("Each grid field must contain a nonempty list")
    for values in product(*(grid[name] for name in grid)):
        yield PlanarConfig(**(base | dict(zip(grid, values))))
