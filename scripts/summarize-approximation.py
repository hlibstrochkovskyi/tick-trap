"""Export source-hashed endpoint, path and enlargement diagnostic results."""

import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/approximation-audit"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/approximation-summary.json"))
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text())
    digest = lambda path: sha256(path.read_bytes()).hexdigest()
    audit, source = read(args.input/"audit.json"), read(args.input/"metadata.json")
    verified, replay = read(args.input/"verification/verification.json"), read(args.input/"verification/metadata.json")
    if source["git_status"] != "" or replay["git_status"] != "" or source["git_commit"] != replay["git_commit"]:
        raise ValueError("Audit and replay must identify the same clean source revision")
    if (verified["status"] != "verified" or replay["configuration"]["audit_sha256"] != digest(args.input/"audit.json")
            or replay["configuration"]["input_metadata_sha256"] != digest(args.input/"metadata.json")):
        raise ValueError("Verification does not match the exact input files")
    physical, error_coefficients = {}, {}
    for row in audit["records"]:
        key = (row["case_index"], row["duration_exact"])
        identity = {k: row[k] for k in ("state", "action_exact", "duration_exact", "a_max_exact", "tau_exact", "gain_exact",
                                       "actual_end_state", "barrier_minimum_exact", "geometric_minimum_exact", "initial_viable")}
        if key in physical and physical[key] != identity:
            raise ValueError("Normalization changed the physical hold")
        physical[key] = identity
        if row["practical_safety_family_certificate"] != "not_established":
            raise ValueError("One-hold diagnostics cannot establish a practical-safety family")
        for radius in row["dilations"]:
            if F(radius["radius_exact"]) == 0 and (
                    radius["path_within_dilation"] != (row["barrier_path_status"] == "safe") or
                    radius["sampled_within_dilation"] != row["exact_sampled_barrier_safe"]):
                raise ValueError("Zero-radius distance check contradicts the original set")
        for model in row["maps"]:
            if model["method"] == "midpoint" and F(model["normalized_error_squared_exact"]) != 0:
                raise ValueError("Midpoint was not exact for the affine held model")
            if model["method"] == "euler":
                coefficient = F(model["normalized_error_squared_exact"])/F(row["duration_exact"])**4
                error_coefficients.setdefault((row["case_index"], row["normalization"]), set()).add(coefficient)
    if any(len(coefficients) != 1 for coefficients in error_coefficients.values()):
        raise ValueError("Euler squared error did not follow the exact fourth-power period law")
    examples = []
    targets = {("euler_endpoint_error", "2/5"), ("curved_barrier_only", "1/5"), ("viable_hidden_collision", "2/5"),
               ("unrecoverable_collision", "1/5"), ("invalid_step_gain", "2/5")}
    for row in audit["records"]:
        if (row["case"], row["duration_exact"]) in targets:
            examples.append(row)
    collision_strata = []
    for group in audit["groups"]:
        events = [r for r in audit["records"] if r["normalization"] == group["normalization"]
                  and r["exact_sampled_barrier_safe"] and r["exact_sampled_geometric_safe"]
                  and r["geometric_path_status"] == "unsafe"
                  and next(m for m in r["maps"] if m["method"] == group["method"])["pointwise_ingredients_satisfied"]]
        collision_strata.append({"normalization": group["normalization"], "method": group["method"],
                                 "viable_initial_hidden_collisions": sum(r["initial_viable"] for r in events),
                                 "nonviable_initial_hidden_collisions": sum(not r["initial_viable"] for r in events)})
    summary = {"scope": audit["scope"], "source": source, "verification": verified,
               "source_artifacts": {name: {"sha256": digest(args.input/name)} for name in
                                    ("audit.json", "metadata.json", "verification/verification.json")},
               "distinct_physical_holds": len(physical), "groups": audit["groups"], "dilation_groups": audit["dilation_groups"],
               "hidden_collision_initial_state_strata": collision_strata,
               "euler_squared_error_period_law_groups_checked": len(error_coefficients),
               "nonzero_euler_error_groups": sum(next(iter(c)) > 0 for c in error_coefficients.values()),
               "examples": examples}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(f"Exported {len(physical)} physical holds and {verified['map_comparisons']} verified map comparisons")


if __name__ == "__main__":
    main()
