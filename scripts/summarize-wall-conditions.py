"""Export traceable results for the verified published wall-condition study."""

import argparse
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/breeden-study"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/breeden-summary.json"))
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text())
    digest = lambda path: sha256(path.read_bytes()).hexdigest()
    study, runs, source = (read(args.input/name) for name in ("study.json", "runs.json", "metadata.json"))
    verification = read(args.input/"verification/verification.json")
    replay_source = read(args.input/"verification/metadata.json")
    if source["git_status"] != "" or replay_source["git_status"] != "" or replay_source["git_commit"] != source["git_commit"]:
        raise ValueError("Experiment and replay must share a clean source revision")
    if (verification["status"] != "verified" or replay_source["configuration"]["runs_sha256"] != digest(args.input/"runs.json")
            or replay_source["configuration"]["study_sha256"] != digest(args.input/"study.json")):
        raise ValueError("Verification does not match the input artifacts")
    native = ("breeden", "breeden_reachable", "breeden_second_order")
    for case in study["single_hold_cases"]:
        intervals = case["control_intervals"]
        if intervals["breeden"] is not None:
            if intervals["breeden_reachable"] is None or F(intervals["breeden_reachable"]["upper_exact"]) < F(intervals["breeden"]["upper_exact"]):
                raise ValueError("Theorem 2 did not contain the Theorem 1 admissible interval at equal gain")
        if any(case["counts"][m]["accepted_unsafe"] for m in native):
            raise ValueError("Published condition admitted a reference-unsafe barrier path")
    # Theorem 3's configured generic gain changes across modes, but its actual
    # gain gamma/T and exact commands/outcomes must not.
    paired = {}
    for run in runs:
        if run["config"]["method"] == "breeden_second_order":
            paired.setdefault((run["study_case"], run["config"]["duration"]), {})[run["gain_policy"]] = run
    paired_equal = 0
    for group in paired.values():
        if "fixed" in group and "matched" in group:
            a, b = group["fixed"], group["matched"]
            if ([r.get("action_exact") for r in a["records"]] != [r.get("action_exact") for r in b["records"]]
                    or a["termination"] != b["termination"] or a["minimum_barrier_exact"] != b["minimum_barrier_exact"]):
                raise ValueError("Theorem 3 changed with an unused generic gain")
            paired_equal += 1
    totals = []
    for policy in ("fixed", "matched"):
        for method in study["methods"]:
            rows = [r for r in runs if r["gain_policy"] == policy and r["config"]["method"] == method]
            counts = [g for g in study["groups"] if g["gain_policy"] == policy and g["method"] == method]
            eligible = [r for r in rows if r["initial_viable"] and r["initial_controller_domain"]]
            totals.append({"gain_policy": policy, "method": method, "runs": len(rows),
                           "viable_in_domain_runs": len(eligible),
                           "viable_in_domain_completed_barrier_horizons": sum(r["completed_barrier_horizon"] for r in eligible),
                           "initially_nonviable_runs": sum(not r["initial_viable"] for r in rows),
                           "initial_domain_exclusions": sum(not r["initial_controller_domain"] for r in rows),
                           "terminations": dict(Counter(r["termination"] for r in rows)),
                           "barrier_horizons": sum(r["completed_barrier_horizon"] for r in rows),
                           **{k: sum(g[k] for g in counts) for k in ("applicable_controls", "accepted_safe", "accepted_unsafe", "safe_excluded", "unsafe_rejected")}})
    examples = [c for c in study["single_hold_cases"] if c["name"] in ("approach", "barrier_boundary") and c["duration_exact"] == "1/10"]
    summary = {"scope": study["scope"], "source": source, "verification": verification,
               "source_artifacts": {name: {"sha256": digest(args.input/name)} for name in ("study.json", "runs.json", "metadata.json", "verification/verification.json")},
               "matched_cases": len(study["single_hold_cases"]), "control_cases": sum(len(c["controls"]) for c in study["single_hold_cases"]),
               "rollout_totals": totals, "groups": study["groups"], "identical_second_order_gain_mode_pairs": paired_equal,
               "examples": [{k: c[k] for k in ("name", "duration_exact", "gain_policy", "comparison_gain_exact", "initial_barrier_exact",
                                               "initial_viable", "selected", "control_intervals", "counts")} for c in examples]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(f"Exported {len(runs)} verified rollouts and {summary['control_cases']} held-control cases")


if __name__ == "__main__":
    main()
