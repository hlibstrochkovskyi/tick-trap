"""Export compact, traceable high-order rollout and paired-predicate results."""

import argparse
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
from statistics import median


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def case_key(run):
    return json.dumps({k: v for k, v in run["config"].items() if k != "method"}, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", choices=("minimum-sign", "sign-auxiliary"), default="minimum-sign")
    parser.add_argument("--study", type=Path)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--verification", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    auxiliary = args.comparison == "sign-auxiliary"
    names = ("auxiliary-cost", "auxiliary-baselines", "auxiliary-verification", "auxiliary-summary") if auxiliary else (
        "certification-cost", "high-order-baselines", "high-order-verification", "certification-summary")
    args.study = args.study or Path("results")/names[0]/"study.json"
    args.runs = args.runs or Path("results")/names[1]/"runs.json"
    args.verification = args.verification or Path("results")/names[2]/"verification.json"
    args.output = args.output or Path("docs/data")/(names[3]+".json")
    method_pair = ("high_order_sign_candidates", "auxiliary_sign_candidates") if auxiliary else (
        "high_order_trajectory_candidates", "high_order_sign_candidates")
    strategy_pair = ("sign", "auxiliary_sign") if auxiliary else ("minimum", "sign")
    paths = {"study": args.study, "runs": args.runs, "verification": args.verification}
    sources = {name: read(path.parent/"metadata.json") for name, path in paths.items()}
    require(all(p["git_status"] == "" for p in sources.values()), "Artifacts must identify clean source snapshots")
    study, runs, verification = read(args.study), read(args.runs), read(args.verification)
    require(verification["status"] == "verified" and sources["verification"]["configuration"]["runs_sha256"] == digest(args.runs),
            "Rollout verification is missing or belongs to another input")
    require(verification["runs"] == len(runs) and verification["executed_holds"] == sum(r["executed_steps"] for r in runs),
            "Rollout verification counts disagree")
    methods = sorted({r["config"]["method"] for r in runs})
    case_sets = [{case_key(r) for r in runs if r["config"]["method"] == method} for method in methods]
    require(case_sets and all(cases == case_sets[0] for cases in case_sets), "Unmatched rollout configurations")
    for method, cases in zip(methods, case_sets):
        require(len(cases) == sum(r["config"]["method"] == method for r in runs), "Duplicate rollout configuration")
    paired_runs = [{case_key(r): r for r in runs if r["config"]["method"] == method}
                   for method in method_pair]
    require(paired_runs[0] and paired_runs[0].keys() == paired_runs[1].keys(), "Missing matched polynomial rollouts")
    identical_actions, identical_outcomes = 0, 0
    for key in paired_runs[0]:
        a, b = (group[key] for group in paired_runs)
        same_actions = [r.get("action_exact") for r in a["records"]] == [r.get("action_exact") for r in b["records"]]
        same_outcome = a["termination"] == b["termination"] and a["final_state"] == b["final_state"]
        identical_actions += same_actions
        identical_outcomes += same_outcome
        if not auxiliary:
            require(same_actions and same_outcome, "Minimum/sign rollouts differ in commands or outcomes")
    per_run, totals = [], []
    for run in runs:
        config, final = run["config"], run["final_state"]
        goal = (sum((F(p)-F(g))**2 for p, g in zip(final["p_exact"], config["goal"])) <= F(config["position_tolerance"])**2
                and sum(F(v)**2 for v in final["v_exact"]) <= F(config["speed_tolerance"])**2)
        require(goal == run["goal_reached_at_end"], "Incorrect exact terminal goal flag")
        proofs = [proof for r in run["records"] for c in r["details"].get("checked", [])
                  for proof in c.get("certificates", [])+c.get("auxiliary_certificates", [])]
        implications = [p for r in run["records"] for c in r["details"].get("checked", []) for p in c.get("geometric_implications", [])]
        per_run.append({"method": config["method"], "period_exact": str(config["duration"]), "initial_p_exact": config["p"],
                        "termination": run["termination"], "safe_full_horizon": run["completed_safe_horizon"],
                        "goal_at_end": goal, "executed_holds": run["executed_steps"],
                        "final_p_exact": final["p_exact"], "final_v_exact": final["v_exact"],
                        "online_polynomial_checks": len(proofs), "online_subdivisions": sum(c["subdivisions"] for c in proofs),
                        "geometric_implications_proved": sum(p["status"] == "safe" for p in implications),
                        "proved_sign_without_width": sum(c["status"] != "unknown" and not c["precision_reached"] for c in proofs),
                        "median_controller_ns": median(r["solve_ns"] for r in run["records"]) if run["records"] else None,
                        "deadline_misses": run["deadline_misses"]})
    for method in methods:
        group = [r for r in per_run if r["method"] == method]
        totals.append({"method": method, "runs": len(group), "safe_horizons": sum(r["safe_full_horizon"] for r in group),
                       "goals_at_end": sum(r["goal_at_end"] for r in group), "terminations": dict(Counter(r["termination"] for r in group)),
                       "online_subdivisions": sum(r["online_subdivisions"] for r in group),
                       "online_polynomial_checks": sum(r["online_polynomial_checks"] for r in group),
                       "geometric_implications_proved": sum(r["geometric_implications_proved"] for r in group),
                       "deadline_misses": sum(r["deadline_misses"] for r in group)})
    pairs = []
    for group in study["groups"]:
        if group["strategy"] != strategy_pair[0]:
            continue
        matched = [{(r["case_index"], r["candidate_index"]): r for r in study["measurements"]
                    if (r["strategy"], r["tolerance_exact"], r["budget"]) == (strategy, group["tolerance_exact"], group["budget"])}
                   for strategy in strategy_pair]
        require(matched[0] and matched[0].keys() == matched[1].keys(), "Missing paired property measurements")
        ratios = []
        for key in matched[0]:
            a, b = (rows[key] for rows in matched)
            require(a["result"]["subdivisions"] >= b["result"]["subdivisions"], "Comparison increased the subdivision count")
            if auxiliary:
                require((a["result"]["status"], b["result"]["status"]) in {
                    ("accepted", "accepted"), ("rejected", "rejected"), ("rejected", "unknown"),
                    ("unknown", "unknown"), ("unknown", "accepted")}, "Contradictory auxiliary implication or proof subset")
            else:
                require(a["result"]["status"] == b["result"]["status"], "Paired property proof-prefix consistency failed")
            ratios.append(a["predicate_ns_median"]/b["predicate_ns_median"])
        pair = {"tolerance_exact": group["tolerance_exact"], "budget": group["budget"], "controls": len(ratios),
                "baseline_strategy": strategy_pair[0], "candidate_strategy": strategy_pair[1],
                "median_paired_baseline_over_candidate_time": median(ratios), "min_ratio": min(ratios), "max_ratio": max(ratios)}
        if not auxiliary:
            pair["median_paired_minimum_over_sign_time"] = median(ratios)
        pairs.append(pair)
    cases = [{"name": c["name"], "candidate_count": c["candidate_count"], "high_order_truth_counts": c["high_order_truth_counts"],
              "first_ordered_action_exact": c["candidates"][0]["action_exact"],
              "first_reference_status": c["candidates"][0]["high_order_path_status"],
              "first_action_sign_queries": [{"strategy": r["strategy"], "tolerance_exact": r["tolerance_exact"], "budget": r["budget"],
                                             "status": r["result"]["status"], "subdivisions": r["result"]["subdivisions"]}
                                            for r in study["measurements"] if r["case_index"] == index
                                            and r["candidate_index"] == 0
                                            and r["strategy"] in (strategy_pair if auxiliary else ("sign",))]}
             for index, c in enumerate(study["reference"])]
    summary = {"scope": "Paired exact-model property queries and matched rollouts; empirical costs, no novelty or hard deadline claim",
               "source_artifacts": {name: {"path": str(path), "sha256": digest(path)} for name, path in paths.items()},
               "provenance": sources, "rollout_verification": verification, "rollout_totals": totals, "per_run": per_run,
               "rollout_comparison": {"baseline_method": method_pair[0], "candidate_method": method_pair[1],
                                      "matched_cases": len(paired_runs[0]), "identical_actions": identical_actions,
                                      "identical_outcomes": identical_outcomes},
               "predicate_groups": study["groups"], "decision_comparisons": study.get("decision_comparisons", []),
               "paired_timing_ratios": pairs, "seed": study["seed"], "repeats": study["repeats"], "cases": cases}
    if not auxiliary:
        summary["identical_minimum_sign_rollouts"] = len(paired_runs[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(f"Exported {len(runs)} rollouts and {len(study['measurements'])} matched property configurations to {args.output}")


if __name__ == "__main__":
    main()
