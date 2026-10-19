"""Replay saved planar dynamics, commands and certificate evidence.

This checks artifact consistency using the declared exact model and the existing
validated polynomial engine. It does not validate physical model assumptions or
provide a mathematically independent implementation of polynomial certification.
"""

from .dynamics import Circle, PlanarState
from .numbers import positive, q, vector2
from .polynomial import certify_minimum, certify_sign, evaluate
from .sampling import sacbf_assessment


class VerificationError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise VerificationError(message)


def _integer(value, name, minimum=0):
    _require(not isinstance(value, bool) and isinstance(value, int) and value >= minimum, f"Invalid {name}")
    return value


def _state(record):
    return PlanarState(record["p_exact"], record["v_exact"])


def _command(action, a_max, quantum):
    action = vector2(action)
    _require(all(abs(u) <= a_max and (u/quantum).denominator == 1 for u in action),
             "Command violates actuator bounds or the command quantum")
    return action


def _certificate(polynomial, duration, record, tolerance, cache, offline=False, expected_goal=None):
    count = _integer(record["subdivisions"], "subdivisions")
    goal = record.get("goal", "minimum")
    _require(goal in ("minimum", "sign") and (expected_goal is None or goal == expected_goal), "Incorrect certificate goal")
    key = (tuple(polynomial), duration, q(tolerance), count, goal)
    if key not in cache:
        certifier = certify_sign if goal == "sign" else certify_minimum
        cache[key] = certifier(polynomial, duration, tolerance, count)
    cert = cache[key]
    lower = "minimum_lower_exact" if offline else "lower_exact"
    upper = "minimum_upper_exact" if offline else "upper_exact"
    status = "continuous_status" if offline else "status"
    _require((cert.lower, cert.upper, cert.witness_time, cert.status, cert.subdivisions) ==
             (q(record[lower]), q(record[upper]), q(record["witness_time_exact"]), record[status], count),
             "Saved certificate does not match deterministic exact replay")
    for field in ("precision_reached", "budget_exhausted", "stopping_reason"):
        if field in record:
            _require(record[field] == getattr(cert, field), f"Incorrect certificate {field}")
    return cert.status


def _plan(plan, expected_state, obstacles, period, a_max, quantum, tolerance, cache):
    _require(_state(plan["expected_state"]) == expected_state, "Retained plan has the wrong expected state")
    consumed = _integer(plan["consumed_steps"], "consumed_steps")
    proofs, original = plan["original_proofs"], []
    current = _state(proofs[0]["start_state"]) if proofs else expected_state
    origin = current
    for proof in proofs:
        _require(_state(proof["start_state"]) == current, "Original proof segments do not form a connected trajectory")
        steps = _integer(proof["steps"], "proof steps", 1)
        action = _command(proof["action_exact"], a_max, quantum)
        dt = steps*period
        _require(q(proof["duration_exact"]) == dt, "Proof interval does not match the update period")
        _require(len(proof["certificates"]) == len(obstacles), "Missing obstacle certificate in retained plan")
        for obstacle, cert in zip(obstacles, proof["certificates"]):
            status = _certificate(obstacle.polynomial(current, action), dt, cert, tolerance, cache)
            _require(status == "safe", "An unresolved or unsafe proof was used in a retained plan")
        _require(proof["status"] == "safe", "Retained segment is not marked certified")
        original.append((action, steps))
        current = current.at(action, dt)
    _require(current.v == (0, 0) and _state(plan["terminal_state"]) == current,
             "Plan does not end at the recorded exact rest state")
    _require(all(o.polynomial(current, (0, 0))[0] >= 0 for o in obstacles), "Terminal rest position is unsafe")
    _require(consumed <= sum(n for _, n in original), "Plan consumed more updates than its proof covers")
    suffix, prefix, shifted = [], consumed, origin
    for action, steps in original:
        used = min(prefix, steps)
        if not suffix:
            shifted = shifted.at(action, used*period)
        prefix -= used
        if used < steps:
            suffix.append((action, steps-used))
    _require(shifted == expected_state, "Consumed proof prefix does not reach the current state")
    declared = [(_command(p["action_exact"], a_max, quantum), _integer(p["steps"], "remaining steps", 1))
                for p in plan["remaining_pieces"]]
    _require(declared == suffix, "Remaining plan is not the declared suffix of its original proofs")
    _require(_integer(plan["remaining_steps"], "remaining_steps") == sum(n for _, n in suffix),
             "Remaining step count is inconsistent")


def _sampling_aware(record, config, state, action, obstacles, period, totals):
    """Replay the accepted condition, then independently check its auxiliary path."""
    checked = record["details"]["checked"]
    _require(checked and checked[-1]["accepted"] is True, "Missing accepted SACBF candidate")
    selected = checked[-1]
    _require(vector2(selected["action_exact"]) == action, "SACBF evidence belongs to another action")
    relaxed = config["method"] == "sacbf_relaxed_candidates"
    expected = [sacbf_assessment(state, action, obstacle, period, config["lambda1"], config["lambda2"], relaxed)
                for obstacle in obstacles]
    _require(selected["sampling_assessments"] == expected and all(a["accepted"] for a in expected),
             "Saved SACBF condition does not match exact replay")
    _require(selected["margins_exact"] == [a["margin_exact"] for a in expected], "SACBF margin evidence is wrong")
    lambda1 = positive(config["lambda1"], "lambda1")
    for obstacle in obstacles:
        h = obstacle.polynomial(state, action)
        psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
        cert = certify_minimum(psi, period, config["oracle_tolerance"], config["oracle_max_subdivisions"])
        _require(cert.status != "unsafe", "Accepted SACBF action violates its continuous auxiliary barrier")
        totals["auxiliary_"+cert.status+"_checks"] += 1
    totals["sampling_aware_holds"] += 1


def _high_order_reference(record, config, state, action, obstacles, period, cache, totals):
    checked = record["details"]["checked"]
    _require(checked and checked[-1]["accepted"] is True, "Missing accepted high-order reference candidate")
    selected = checked[-1]
    _require(vector2(selected["action_exact"]) == action, "High-order evidence belongs to another action")
    _require(len(selected["certificates"]) == len(obstacles) and len(selected["auxiliary_certificates"]) == len(obstacles),
             "Missing geometric or auxiliary reference certificate")
    goal = "sign" if config["method"] == "high_order_sign_candidates" else "minimum"
    lambda1 = positive(config["lambda1"], "lambda1")
    for obstacle, h_cert, psi_cert in zip(obstacles, selected["certificates"], selected["auxiliary_certificates"]):
        h = obstacle.polynomial(state, action)
        psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
        for polynomial, cert in ((h, h_cert), (psi, psi_cert)):
            _require(_integer(cert["subdivisions"], "subdivisions") <= _integer(config["max_subdivisions"], "configured subdivision budget"),
                     "Online reference certificate exceeds the configured subdivision budget")
            status = _certificate(polynomial, period, cert, config["tolerance"], cache, expected_goal=goal)
            _require(status == "safe", "An unresolved or unsafe reference certificate authorized an action")
            totals["high_order_reference_certificates"] += 1
    totals["high_order_reference_holds"] += 1


def _auxiliary_reference(record, config, state, action, obstacles, period, cache, totals):
    checked = record["details"]["checked"]
    _require(checked and checked[-1]["accepted"] is True, "Missing accepted auxiliary candidate")
    selected = checked[-1]
    _require(vector2(selected["action_exact"]) == action, "Auxiliary evidence belongs to another action")
    _require(selected["certificates"] == [], "Auxiliary-only inference must not claim a numerical geometric minimum")
    proofs, implications = selected["auxiliary_certificates"], selected["geometric_implications"]
    _require(len(proofs) == len(obstacles) and len(implications) == len(obstacles), "Missing auxiliary proof or geometric implication")
    lambda1 = positive(config["lambda1"], "lambda1")
    for index, (obstacle, cert, implication) in enumerate(zip(obstacles, proofs, implications)):
        h = obstacle.polynomial(state, action)
        _require(h[0] >= 0, "Comparison proof starts outside the geometric set")
        psi = tuple(lambda1*c+((i+1)*h[i+1] if i+1 < len(h) else 0) for i, c in enumerate(h))
        _require(_integer(cert["subdivisions"], "subdivisions") <= _integer(config["max_subdivisions"], "configured subdivision budget"),
                 "Auxiliary certificate exceeds the configured subdivision budget")
        status = _certificate(psi, period, cert, config["tolerance"], cache, expected_goal="sign")
        _require(status == "safe", "An unresolved or unsafe auxiliary certificate authorized an action")
        expected = {"rule": "linear_comparison", "initial_h_exact": str(h[0]), "lambda1_exact": str(lambda1),
                    "duration_exact": str(period), "status": "safe"}
        _require(implication == expected, "Geometric comparison assumptions or conclusion are wrong")
        offline = record["obstacles"][index]["continuous_status"]
        _require(offline != "unsafe", "Comparison proof contradicts a negative offline geometric witness")
        totals["derived_safe_offline_unknown"] += offline == "unknown"
        totals["auxiliary_reference_certificates"] += 1
    totals["auxiliary_reference_holds"] += 1


def verify_planar_runs(runs):
    _require(isinstance(runs, list), "Expected a list of planar run records")
    cache = {}
    totals = {"runs": len(runs), "executed_holds": 0, "retained_plans": 0,
              "unsafe_intervals": 0, "unknown_intervals": 0,
              "sampling_aware_holds": 0, "auxiliary_safe_checks": 0, "auxiliary_unknown_checks": 0,
              "high_order_reference_holds": 0, "high_order_reference_certificates": 0,
              "auxiliary_reference_holds": 0, "auxiliary_reference_certificates": 0, "derived_safe_offline_unknown": 0}
    for run_index, run in enumerate(runs):
        try:
            config = run["config"]
            state = PlanarState(config["p"], config["v"])
            period = positive(config["duration"], "duration")
            a_max, quantum = positive(config["a_max"], "a_max"), positive(config["command_quantum"], "command_quantum")
            obstacles = tuple(Circle(**o) for o in config["obstacles"])
            initial_safe = all(o.polynomial(state, (0, 0))[0] >= 0 for o in obstacles)
            _require(run["initial_geometric_safe"] == initial_safe, "Incorrect initial geometric safety")
            backup = config["method"] == "backup_candidates"
            previous = run.get("controller_initial_plan") if backup else None
            if backup and run["controller_initialization_status"] == "ready":
                _require(previous is not None, "Missing certified initialization plan")
                _plan(previous, state, obstacles, period, a_max, quantum, config["tolerance"], cache)
            statuses, sampled = [], []
            for index, record in enumerate(run["records"]):
                _require(record["step"] == index and q(record["time_exact"]) == index*period,
                         "Recorded control update order or time is wrong")
                _require(_state(record["state"]) == state, "Recorded state disagrees with exact forward dynamics")
                if "action_exact" not in record:
                    _require(record["decision"] != "feasible" and index == len(run["records"])-1,
                             "Missing action or a failed decision followed by more execution")
                    continue
                _require(record["decision"] == "feasible", "An action was applied after a failed decision")
                action = _command(record["action_exact"], a_max, quantum)
                end = state.at(action, period)
                _require(_state(record["end_state"]) == end, "Recorded endpoint disagrees with exact forward dynamics")
                _require(len(record["obstacles"]) == len(obstacles), "Missing executed-interval obstacle evidence")
                interval_status, interval_sampled = [], []
                for obstacle, evidence in zip(obstacles, record["obstacles"]):
                    polynomial = obstacle.polynomial(state, action)
                    _require(tuple(map(q, evidence["polynomial_exact"])) == polynomial, "Recorded polynomial is wrong")
                    interval_status.append(_certificate(polynomial, period, evidence, config["oracle_tolerance"], cache, True))
                    sample_safe = polynomial[0] >= 0 and evaluate(polynomial, period) >= 0
                    _require(evidence["sampled_safe"] == sample_safe, "Obstacle sampled-safety evidence is wrong")
                    interval_sampled.append(sample_safe)
                status = "unsafe" if "unsafe" in interval_status else "unknown" if "unknown" in interval_status else "safe"
                _require(record["continuous_status"] == status and record["sampled_safe"] == all(interval_sampled),
                         "Recorded safety classifications disagree with replay")
                statuses.append(status)
                sampled.append(all(interval_sampled))
                if config["method"] in ("sacbf_candidates", "sacbf_relaxed_candidates"):
                    _sampling_aware(record, config, state, action, obstacles, period, totals)
                if config["method"] in ("high_order_trajectory_candidates", "high_order_sign_candidates"):
                    _high_order_reference(record, config, state, action, obstacles, period, cache, totals)
                if config["method"] == "auxiliary_sign_candidates":
                    _auxiliary_reference(record, config, state, action, obstacles, period, cache, totals)
                if backup:
                    _require(previous is not None, "An uninitialized backup filter applied an action")
                    plan = record["details"]["retained_plan"]
                    _plan(plan, end, obstacles, period, a_max, quantum, config["tolerance"], cache)
                    source = record["control_source"]
                    if source == "certified_candidate":
                        first = plan["original_proofs"][0]
                        _require(_state(first["start_state"]) == state and vector2(first["action_exact"]) == action
                                 and first["steps"] == 1 and plan["consumed_steps"] == 1,
                                 "Renewed plan does not certify the selected hold")
                    elif source == "stored_continuation":
                        _require(previous["remaining_pieces"] and vector2(previous["remaining_pieces"][0]["action_exact"]) == action,
                                 "Applied action is not the next stored command")
                        _require(plan["original_proofs"] == previous["original_proofs"] and plan["consumed_steps"] == previous["consumed_steps"]+1,
                                 "Stored proof was changed while consuming its prefix")
                    elif source == "terminal_hold":
                        _require(not previous["remaining_pieces"] and state.v == (0, 0) and action == (0, 0) and plan == previous,
                                 "Terminal zero input was not applied at certified rest")
                    else:
                        raise VerificationError("Unknown backup action source")
                    _require(record["retained_continuation_certified"] is True, "Missing retained-continuation outcome")
                    previous = plan
                    totals["retained_plans"] += 1
                state = end
            _require(_state(run["final_state"]) == state and run["executed_steps"] == len(statuses), "Final state or executed step count is wrong")
            _require(run["collision_observed"] == ("unsafe" in statuses), "Collision summary disagrees with interval evidence")
            expected_safe = (run["termination"] == "horizon" and initial_safe and len(statuses)*period == q(config["horizon"])
                             and all(s == "safe" for s in statuses))
            _require(run["completed_safe_horizon"] == expected_safe, "Safe completion summary is wrong")
            _require(run["sampled_safe_observed"] == (initial_safe and all(sampled)), "Sampled safety summary is wrong")
            if backup:
                _require(run["final_retained_plan"] == previous, "Final retained plan is inconsistent")
                _require(run["retained_continuation_after_every_update"] == (True if statuses else None), "Retained-plan summary is wrong")
            totals["executed_holds"] += len(statuses)
            totals["unsafe_intervals"] += statuses.count("unsafe")
            totals["unknown_intervals"] += statuses.count("unknown")
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise VerificationError(f"Run {run_index}: {exc}") from exc
    return totals | {"status": "verified", "unique_certificate_replays": len(cache),
                     "scope": "artifact consistency under the reported exact model; uses the existing polynomial certifier"}
