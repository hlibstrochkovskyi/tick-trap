"""Export a compact, traceable summary of the matched sampling-aware study.

Run after planar-sweep, planar-audit and verify. Full exact hold evidence remains
in those original artifacts; this small export is suitable for version control.
"""

import argparse
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
from statistics import median


def read(path):
    return json.loads(path.read_text(), parse_float=str)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=Path("results/sampling-baselines/runs.json"))
    parser.add_argument("--audit", type=Path, default=Path("results/sampling-audit/audit.json"))
    parser.add_argument("--verification", type=Path, default=Path("results/sampling-verification/verification.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/sampling-summary.json"))
    args = parser.parse_args()
    runs, audits, verification = read(args.runs), read(args.audit), read(args.verification)
    sources = {name: read(path.parent/"metadata.json") for name, path in
               (("runs", args.runs), ("audit", args.audit), ("verification", args.verification))}
    require(all(source["git_status"] == "" for source in sources.values()),
            "Study artifacts must identify clean source snapshots")
    require(verification["status"] == "verified", "The run replay did not pass")
    require(sources["verification"]["configuration"]["runs_sha256"] == digest(args.runs),
            "The verification belongs to a different runs file")
    require(verification["runs"] == len(runs) and verification["executed_holds"] == sum(r["executed_steps"] for r in runs),
            "Verification and run counts disagree")
    methods = sorted({r["config"]["method"] for r in runs})
    require(bool(methods), "No runs supplied")
    case_sets = []
    for method in methods:
        cases = [json.dumps({k: v for k, v in r["config"].items() if k != "method"}, sort_keys=True)
                 for r in runs if r["config"]["method"] == method]
        require(len(cases) == len(set(cases)), "Duplicate method/configuration pair")
        case_sets.append(set(cases))
    require(all(cases == case_sets[0] for cases in case_sets), "Methods do not have matched configurations")
    per_run, aggregates = [], []
    for run in runs:
        config, state = run["config"], run["final_state"]
        distance2 = sum((F(p)-F(g))**2 for p, g in zip(state["p_exact"], config["goal"]))
        speed2 = sum(F(v)**2 for v in state["v_exact"])
        at_goal = distance2 <= F(config["position_tolerance"])**2 and speed2 <= F(config["speed_tolerance"])**2
        require(at_goal == run["goal_reached_at_end"], "Terminal goal flag does not match exact final state")
        per_run.append({"method": config["method"], "period_exact": str(config["duration"]),
                        "initial_p_exact": config["p"], "termination": run["termination"],
                        "safe_full_horizon": run["completed_safe_horizon"], "goal_reached_at_end": at_goal,
                        "executed_holds": run["executed_steps"], "final_state": {
                            "p_exact": state["p_exact"], "v_exact": state["v_exact"]},
                        "solve_ns_median": median(r["solve_ns"] for r in run["records"]) if run["records"] else None,
                        "initialization_ns": run["controller_initialization_ns"], "deadline_misses": run["deadline_misses"]})
    for method in methods:
        group = [r for r in runs if r["config"]["method"] == method]
        aggregates.append({"method": method, "runs": len(group),
                           "safe_full_horizons": sum(r["completed_safe_horizon"] for r in group),
                           "goals_at_end": sum(r["goal_reached_at_end"] for r in group),
                           "collisions": sum(r["collision_observed"] for r in group),
                           "initial_stopping_certified": sum(r["initial_viability"] == "certified" for r in group),
                           "initial_high_order_domain": sum(r["initial_hocbf_domain"] for r in group),
                           "terminations": dict(Counter(r["termination"] for r in group)),
                           "deadline_misses": sum(r["deadline_misses"] for r in group)})
    summary = {"scope": "Finite matched study; exact-model evidence, not a general method ranking or novelty claim",
               "source_artifacts": {name: {"path": str(path), "sha256": digest(path)} for name, path in
                                    (("runs", args.runs), ("audit", args.audit), ("verification", args.verification))},
               "provenance": sources, "verification": verification,
               "method_totals": aggregates, "per_run": per_run,
               "matched_control_audits": [{"name": c["name"], "candidate_count": c["candidate_count"],
                                            "high_order_applicable": c["hocbf_applicable"],
                                            "truth_counts": c["truth_counts"], "counts": c["counts"]} for c in audits]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(f"Summarized {len(runs)} matched runs and {len(audits)} control audits in {args.output}")


if __name__ == "__main__":
    main()
