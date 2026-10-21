"""Strict current-implementation replay of saved planar scientific records.

This complements physical/certificate verification. It checks controller choices,
failed searches and task summaries, not timing authenticity or program proofs.
"""

from collections import Counter
from hashlib import sha256
import json

from .planar_experiments import PlanarConfig, load_planar_grid, run_planar
from .verification import VerificationError, verify_planar_runs

TIMING_FIELDS = {
    "run": ("initial_viability_check_ns", "controller_initialization_ns", "solve_ns_total",
            "certification_ns_total", "deadline_misses"),
    "record": ("solve_ns", "deadline_missed", "offline_proof_replay_ns", "certification_ns",
               "estimation_ns", "continuation_check_ns"),
    "obstacle": ("certification_ns", "estimation_ns"),
}
DISPLAY_FIELDS = {
    "run": ("minimum_clearance_estimate",),
    "record": ("action",),
    "state": ("p", "v"),
    "obstacle": ("minimum_estimate", "time_estimate", "critical_times_estimate", "clearance_estimate"),
}


def scientific_planar_record(run):
    """Omit only documented fields at their actual schema locations.

    In particular, p/v in configuration and unrecognized timing-like names in
    controller evidence are retained. No recursive name-based wildcard is used.
    """
    def keep(value, scope):
        excluded = set(TIMING_FIELDS.get(scope, ())) | set(DISPLAY_FIELDS.get(scope, ()))
        return {k: v for k, v in value.items() if k not in excluded}
    result = keep(run, "run")
    result["final_state"] = keep(run["final_state"], "state")
    records = []
    for record in run["records"]:
        row = keep(record, "record")
        for state_name in ("state", "end_state"):
            if state_name in row:
                row[state_name] = keep(row[state_name], "state")
        if "obstacles" in row:
            row["obstacles"] = [keep(obstacle, "obstacle") for obstacle in row["obstacles"]]
        records.append(row)
    result["records"] = records
    return result


def _difference(saved, expected, path="$"):
    if type(saved) is not type(expected):
        return path
    if isinstance(saved, dict):
        for key in sorted(saved.keys() | expected.keys()):
            if key not in saved or key not in expected:
                return path+"."+key
            mismatch = _difference(saved[key], expected[key], path+"."+key)
            if mismatch:
                return mismatch
    elif isinstance(saved, list):
        if len(saved) != len(expected):
            return path+".length"
        for index, (a, b) in enumerate(zip(saved, expected)):
            mismatch = _difference(a, b, f"{path}[{index}]")
            if mismatch:
                return mismatch
    elif saved != expected:
        return path
    return None


def verify_planar_decisions(runs, specification=None):
    """Replay full scientific records after checking original physical evidence.

    The current runner/controllers are used for regeneration, so this is an
    implementation-fidelity check, not an independent controller implementation.
    Older revisions with changed algorithms or scientific schemas can legitimately
    fail this stricter check; their original physical proof is not revoked.
    """
    if specification is not None:
        if isinstance(specification, list):
            configurations = [PlanarConfig(**config) for config in specification]
        elif isinstance(specification, dict) and set(specification) <= {"base", "grid"}:
            configurations = list(load_planar_grid(specification))
        elif isinstance(specification, dict):
            configurations = [PlanarConfig(**specification)]
        else:
            raise VerificationError("Expected a planar configuration, grid or explicit configuration list")
        mismatch = _difference([r["config"] for r in runs], [c.record() for c in configurations])
        if mismatch:
            raise VerificationError(f"Declared planar cohort differs at {mismatch}")
    physical = verify_planar_runs(runs)
    rows = []
    for index, saved in enumerate(runs):
        expected = run_planar(PlanarConfig(**saved["config"]))
        actual_science = scientific_planar_record(saved)
        mismatch = _difference(actual_science, scientific_planar_record(expected))
        if mismatch:
            raise VerificationError(f"Run {index}: scientific decision replay differs at {mismatch}")
        encoded = json.dumps(actual_science, sort_keys=True, separators=(",", ":"), allow_nan=False)
        records = saved["records"]
        rows.append({"run_index": index, "method": saved["config"]["method"],
                     "scientific_sha256": sha256(encoded.encode()).hexdigest(),
                     "decision_updates": len(records), "executed_holds": saved["executed_steps"],
                     "failed_decisions": sum("action_exact" not in r for r in records),
                     "checked_candidates": sum(len(r["details"].get("checked", [])) for r in records),
                     "termination": saved["termination"], "completed_safe_horizon": saved["completed_safe_horizon"],
                     "goal_reached_at_end": saved["goal_reached_at_end"],
                     "control_sources": dict(Counter(r["control_source"] for r in records if "action_exact" in r))})
    groups = []
    for method in sorted({r["method"] for r in rows}):
        group = [r for r in rows if r["method"] == method]
        groups.append({"method": method, "runs": len(group),
                       **{k: sum(r[k] for r in group) for k in
                          ("decision_updates", "executed_holds", "failed_decisions", "checked_candidates")},
                       "terminations": dict(Counter(r["termination"] for r in group))})
    return {"status": "verified", "runs": len(rows), "declared_coverage_checked": specification is not None,
            "decision_updates": sum(r["decision_updates"] for r in rows),
            "failed_decisions": sum(r["failed_decisions"] for r in rows),
            "checked_candidates": sum(r["checked_candidates"] for r in rows),
            "physical_artifact_replay": physical, "groups": groups, "per_run": rows,
            "excluded_timing_fields": {k: list(v) for k, v in TIMING_FIELDS.items()},
            "excluded_display_fields": {k: list(v) for k, v in DISPLAY_FIELDS.items()},
            "scope": "Strict scientific-record regeneration under the current declared planar implementation, including candidate order, failed decisions, nominal policy, retained plans and task flags. Uses the same runner/controllers and certificate engine; not independent program verification, physical-model validation, timing authentication or an execution-policy change."}
