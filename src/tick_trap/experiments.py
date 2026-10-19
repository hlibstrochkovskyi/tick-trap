"""Controlled wall rollouts and reproducible Cartesian experiment grids."""

from dataclasses import asdict, dataclass, fields
from fractions import Fraction
from itertools import product
from random import Random
from time import perf_counter_ns

from .controllers import METHODS, decide
from .dynamics import WallState
from .numbers import nonnegative, positive, q
from .oracle import wall_interval


@dataclass(frozen=True)
class RunConfig:
    method: str = "exact_hold"
    d: str = "0.6"
    v: str = "1"
    duration: str = "0.1"
    steps: int = 20
    a_max: str = "10"
    nominal: str = "0"
    tau: str = "0.3"
    cbf_gain: str = "2"
    gamma: str = "1"
    plant_gain: str = "1"
    plant_bias: str = "0"
    model_gain: str = "1"
    model_bias: str = "0"
    measurement_d: str = "0"
    measurement_v: str = "0"
    delay: str = "0"
    previous_action: str = "0"
    deadline: str | None = None
    seed: int = 7

    def __post_init__(self):
        if self.method not in METHODS:
            raise ValueError(f"Unknown method {self.method!r}")
        if isinstance(self.steps, bool) or not isinstance(self.steps, int) or self.steps < 1:
            raise ValueError("steps must be a positive integer")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        for name in ("duration", "a_max", "tau", "cbf_gain", "plant_gain", "model_gain", "gamma"):
            positive(getattr(self, name), name)
        for name in ("measurement_d", "measurement_v", "delay"):
            nonnegative(getattr(self, name), name)
        for name in ("d", "v", "nominal", "plant_bias", "model_bias", "previous_action"):
            q(getattr(self, name))
        if q(self.gamma) > 1:
            raise ValueError("gamma must be in (0,1]")
        if q(self.delay) >= q(self.duration):
            raise ValueError("delay must be less than duration")
        if abs(q(self.previous_action)) > q(self.a_max):
            raise ValueError("previous_action exceeds actuator limits")
        if self.deadline is not None:
            positive(self.deadline, "deadline")
        if q(self.plant_gain)*q(self.a_max)-q(self.plant_bias) <= 0:
            raise ValueError("Plant must retain strictly positive braking authority")
        if q(self.model_gain)*q(self.a_max)-abs(q(self.model_bias)) <= 0:
            raise ValueError("Model must have a positive symmetric acceleration range")


def _number_dict(state):
    return {"d": float(state.d), "v": float(state.v),
            "d_exact": str(state.d), "v_exact": str(state.v)}


def run(config: RunConfig):
    rng = Random(config.seed)
    state = WallState(config.d, config.v)
    duration, a_max = q(config.duration), q(config.a_max)
    plant_gain, plant_bias = q(config.plant_gain), q(config.plant_bias)
    model_gain, model_bias = q(config.model_gain), q(config.model_bias)
    model_acceleration_limit = model_gain*a_max-abs(model_bias)
    physical_braking = plant_gain*a_max-plant_bias
    delay = q(config.delay)
    previous = q(config.previous_action)
    initial_viable = state.viability_margin(physical_braking) >= 0
    assumption_violations = [name for name, active in (
        ("actuation_model_mismatch", plant_gain != model_gain or plant_bias != model_bias),
        ("measurement_error", q(config.measurement_d) != 0 or q(config.measurement_v) != 0),
        ("execution_delay", delay != 0)) if active]
    records = []
    termination = "horizon"
    deadline = q(config.deadline) if config.deadline is not None else duration
    if state.d < 0:
        termination = "initially_unsafe"
    else:
        for index in range(config.steps):
            measured = WallState(state.d+q(rng.uniform(-1, 1))*q(config.measurement_d),
                                 state.v+q(rng.uniform(-1, 1))*q(config.measurement_v))
            start = perf_counter_ns()
            decision = decide(config.method, measured, config.nominal, duration, model_acceleration_limit,
                              config.tau, config.cbf_gain, config.gamma)
            solve_ns = perf_counter_ns()-start
            deadline_missed = Fraction(solve_ns, 10**9) > deadline
            record = {"step": index, "time": float(index*duration), "state": _number_dict(state),
                      "measurement": _number_dict(measured), "decision": decision.status,
                      "reason": decision.reason, "details": decision.details,
                      "solve_ns": solve_ns, "deadline_missed": deadline_missed,
                      "true_viable_before": state.viability_margin(physical_braking) >= 0,
                      "residual_exact": str(decision.residual) if decision.residual is not None else None}
            if decision.status != "feasible":
                records.append(record)
                termination = decision.status
                break
            action = (decision.action-model_bias)/model_gain
            if abs(action) > a_max:
                raise ArithmeticError("Mapped command exceeded actuator bounds")
            record["action"] = float(action)
            record["action_exact"] = str(action)
            record["filtered_acceleration"] = float(decision.action)
            record["filtered_acceleration_exact"] = str(decision.action)
            pieces = []
            current = state
            elapsed = Fraction(0)
            for held_action, dt in ((previous, delay), (action, duration-delay)):
                if dt == 0:
                    continue
                actual = plant_gain*held_action+plant_bias
                oracle = wall_interval(current, actual, dt)
                pieces.append({**oracle, "start_offset_exact": str(elapsed),
                               "duration_exact": str(dt), "actual_acceleration_exact": str(actual)})
                current = current.at(actual, dt)
                elapsed += dt
            record.update({"end_state": _number_dict(current), "pieces": pieces,
                           "sampled_safe": state.d >= 0 and current.d >= 0,
                           "continuous_safe": all(p["continuous_status"] == "safe" for p in pieces),
                           "minimum_clearance": min(p["minimum_clearance"] for p in pieces),
                           "certification_ns": sum(p["certification_ns"] for p in pieces),
                           "true_viable_after": current.viability_margin(physical_braking) >= 0})
            records.append(record)
            state, previous = current, action
            if not record["continuous_safe"]:
                termination = "collision_interval"
                break
    executed = [r for r in records if "continuous_safe" in r]
    collision = any(not r["continuous_safe"] for r in executed)
    full = termination == "horizon"
    misses = sum(r["deadline_missed"] for r in records)
    initial_domain = None
    if records:
        initial_domain = records[0]["decision"] != "outside_domain"
    return {"config": asdict(config), "initial_geometric_safe": q(config.d) >= 0,
            "initial_viable": initial_viable, "initial_controller_domain": initial_domain,
            "assumption_violations": assumption_violations,
            "termination": termination, "executed_steps": len(executed),
            "sampled_safe_observed": all(r["sampled_safe"] for r in executed) and q(config.d) >= 0,
            "continuous_safe_observed": not collision and q(config.d) >= 0,
            "completed_safe_horizon": full and not collision,
            "collision_observed": collision, "deadline_misses": misses,
            "minimum_clearance": min((r["minimum_clearance"] for r in executed), default=float(q(config.d))),
            "intervention_l1": sum(abs(r["filtered_acceleration"]-float(q(config.nominal))) for r in executed),
            "solve_ns_total": sum(r["solve_ns"] for r in records),
            "certification_ns_total": sum(r["certification_ns"] for r in executed),
            "records": records}


def load_grid(spec):
    if set(spec)-{"base", "grid"}:
        raise ValueError("Experiment accepts only 'base' and 'grid'")
    base, grid = spec.get("base", {}), spec.get("grid", {})
    valid = {f.name for f in fields(RunConfig)}
    if (set(base) | set(grid))-valid:
        raise ValueError(f"Unknown configuration fields: {(set(base) | set(grid))-valid}")
    for name, values in grid.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"Grid field {name} must be a nonempty list")
    names = list(grid)
    for values in product(*(grid[name] for name in names)):
        yield RunConfig(**(base | dict(zip(names, values))))
