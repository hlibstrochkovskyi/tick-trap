"""Export a compact milestone summary tied to the complete evidence manifest."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/audit-milestone"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/data/audit-manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/audit-summary.json"))
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text())
    manifest = read(args.manifest)
    for entry in manifest["files"]:
        data = (args.input/entry["path"]).read_bytes()
        if len(data) != entry["bytes"] or sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Input differs from archived evidence: "+entry["path"])
    archive = args.manifest.with_name(manifest["archive"])
    if sha256(archive.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive differs from manifest")
    sources = read(args.input/"environment.json")
    studies = {}
    group_keys = ("strategy", "queries", "accepted", "rejected", "unknown", "accepted_safe_controls",
                  "accepted_unsafe_controls", "rejected_unsafe_controls", "rejected_safe_controls",
                  "unknown_safe_controls", "unknown_unsafe_controls", "geometrically_unsafe_rejected",
                  "polynomial_checks", "total_subdivisions", "median_per_control_ns")
    summaries = []
    for name in ("auxiliary-cost", "auxiliary-total-work"):
        data = read(args.input/(name+"-summary.json"))
        summaries.append(data)
        studies[data["budget_scope"]] = {
            "states": len(data["cases"]), "controls": sum(c["candidate_count"] for c in data["cases"]),
            "timed_configurations": sum(g["queries"] for g in data["predicate_groups"]),
            "timed_evaluations": data["repeats"]*sum(g["queries"] for g in data["predicate_groups"]),
            "seed": data["seed"], "repeats": data["repeats"],
            "independent_h_and_psi_truth_counts": data["independent_reference_counts"],
            "main_setting": {"tolerance_exact": "1/1000000000000", "budget": 64},
            "main_groups": [{k: g[k] for k in group_keys} for g in data["predicate_groups"]
                            if g["strategy"] == "sacbf_relaxed" or (g["tolerance_exact"], g["budget"]) == ("1/1000000000000", 64)],
            "main_paired_timings": [{"baseline": p["baseline"], "candidate": p["candidate"],
                                    "paired_median_ratio_distribution": p["paired_median_time_ratio"],
                                    "paired_repeat_ratio_distribution": p["paired_repeat_time_ratio"]}
                                   for p in data["all_paired_comparisons"]
                                   if (p["tolerance_exact"], p["budget"]) == ("1/1000000000000", 64)],
            "dual_to_auxiliary_decisions": data["decision_comparisons"]}
    ci = read(args.input/"ci-source-run.json") if (args.input/"ci-source-run.json").exists() else None
    if ci and (ci["head_sha"] != manifest["source_git_commit"] or ci["conclusion"] != "success"):
        raise ValueError("CI result does not match successful evidence source")
    versions = []
    if ci:
        jobs = read(args.input/"ci-source-jobs.json")["jobs"]
        if len(jobs) != 4 or any(j["conclusion"] != "success" or j["head_sha"] != ci["head_sha"] for j in jobs):
            raise ValueError("CI matrix is incomplete or belongs to another source")
        versions = sorted(re.fullmatch(r"test \(([^)]+)\)", j["name"])[1] for j in jobs)
    tests = (args.input/"tests.log").read_text()
    count = re.search(r"Ran (\d+) tests in", tests)
    if not count or not tests.rstrip().endswith("OK"):
        raise ValueError("Missing successful complete test log")
    result = {"schema_version": 1, "source_git_commit": manifest["source_git_commit"],
              "source_sha256": manifest["source_sha256"], "clean_source": sources["git_status"] == "",
              "python": sources["python"], "platform": sources["platform"],
              "tests": {"count": int(count[1]), "result": "passed", "environment": "fresh clone and stdlib-only virtual environment",
                        "ci_url": ci["html_url"] if ci else None, "ci_python_versions": versions},
              "evidence": {k: manifest[k] for k in ("archive", "archive_sha256", "archive_bytes", "uncompressed_bytes")},
              "studies": studies, "rollouts": summaries[0]["rollout_totals"],
              "rollout_comparison": summaries[0]["rollout_comparison"],
              "rollout_verification": summaries[0]["rollout_verification"],
              "execution_regression": [{k: r[k] for k in ("termination", "executed_steps", "completed_safe_horizon",
                                                         "oracle_confirmed_horizon", "observed_continuous_status", "certified_execution_status")}
                                       | {"method": r["config"]["method"]} for r in read(args.input/"execution-evidence.json")],
              "scope": "Exact double integrator, static circles, bounded held commands and exact observations; unsafe h-or-psi does not necessarily mean collision. Descriptive finite-set times, no hard deadline or physical-safety guarantee. No novelty claim."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(f"Saved {args.output} with manifest-checked inputs")


if __name__ == "__main__":
    main()
