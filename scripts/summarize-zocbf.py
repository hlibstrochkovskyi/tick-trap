"""Export source-hashed local ZOCBF contracts without promoting offline references."""

import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/zocbf-audit"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/zocbf-summary.json"))
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
    identities = set()
    for row in audit["records"]:
        identity = (row["case_index"], row["duration_exact"])
        if identity in identities:
            raise ValueError("Repeated physical hold")
        identities.add(identity)
        if row["independent_sign_reference"]["status"] != row["constraint_path_status"]:
            raise ValueError("Independent sign reference disagrees")
        deltas = [F(b["delta_exact"]) for b in row["assessments"]]
        if deltas != sorted(deltas, reverse=True):
            raise ValueError("Analytical buffer hierarchy was violated")
        for buffer in row["assessments"]:
            variants = {v["variant"]: v for v in buffer["variants"]}
            exact, midpoint = variants["exact_previous"], variants["midpoint_previous"]
            if any(exact[k] != midpoint[k] for k in exact if k != "variant"):
                raise ValueError("Midpoint must equal the exact endpoint condition on this model")
            if F(variants["euler_tightened"]["prediction_margin_exact"]) != F(row["euler_endpoint_error_bound_exact"]):
                raise ValueError("Euler discrepancy margin was changed")
            for variant in variants.values():
                if variant["one_hold_implication_ingredients"] and row["constraint_path_status"] != "safe":
                    raise ValueError("Valid local ingredients admitted an unsafe proxy hold")
    transitions, failure_strata = [], []
    for group in audit["groups"]:
        policy, name = group["buffer_policy"], group["variant"]
        counts = {"reject_to_accept": 0, "accept_to_reject": 0, "accept_to_accept": 0, "reject_to_reject": 0}
        failures = {"invalid_buffer_only": 0, "invalid_endpoint_lower_bound_only": 0, "both_invalid": 0}
        for row in audit["records"]:
            buffer = next(b for b in row["assessments"] if b["buffer_policy"] == policy)
            exact = next(v for v in buffer["variants"] if v["variant"] == "exact_previous")
            variant = next(v for v in buffer["variants"] if v["variant"] == name)
            old = "accept" if exact["condition_passed"] else "reject"
            new = "accept" if variant["condition_passed"] else "reject"
            counts[f"{old}_to_{new}"] += 1
            if row["left_pair_safe"] and variant["condition_passed"] and row["constraint_path_status"] == "unsafe":
                bad_buffer = not buffer["backward_difference_bound_valid"]
                bad_endpoint = not variant["endpoint_lower_bound_valid"]
                if not (bad_buffer or bad_endpoint):
                    raise ValueError("Unsafe safe-left pass has no identified failed local premise")
                key = "both_invalid" if bad_buffer and bad_endpoint else (
                    "invalid_buffer_only" if bad_buffer else "invalid_endpoint_lower_bound_only")
                failures[key] += 1
        if sum(failures.values()) != group["passes_with_safe_left_and_unsafe_proxy"]:
            raise ValueError("Unsafe-pass strata do not reconcile with group counts")
        transitions.append({"buffer_policy": policy, "variant": name, **counts})
        failure_strata.append({"buffer_policy": policy, "variant": name, **failures})
    examples = []
    targets = {("stale_endpoint_jump", "1/10"), ("jump_then_recover", "1"),
               ("reset_excludes_safe_contract", "1"), ("reset_admits_outside_contract", "1/10"),
               ("euler_error", "1/5"), ("curved_hidden_collision", "2/5"), ("barrier_tangent", "2/5")}
    for row in audit["records"]:
        if (row["case"], row["duration_exact"]) not in targets:
            continue
        examples.append({k: v for k, v in row.items() if k not in ("assessments", "independent_sign_reference")} | {
            "selected_assessments": [b for b in row["assessments"] if b["buffer_policy"] in
                                     ("norm_tube", "oracle_absolute", "oracle_backward_drop", "endpoint_only")]})
    summary = {"scope": audit["scope"], "source": source, "verification": verified,
               "source_artifacts": {name: {"sha256": digest(args.input/name)} for name in
                                    ("audit.json", "metadata.json", "verification/verification.json", "verification/metadata.json")},
               "distinct_physical_holds": len(identities),
               "safe_left_holds": sum(r["left_pair_safe"] for r in audit["records"]),
               "safe_proxy_holds": sum(r["constraint_path_status"] == "safe" for r in audit["records"]),
               "groups": audit["groups"], "paired_condition_transitions_from_exact_history": transitions,
               "unsafe_safe_left_pass_premise_failures": failure_strata, "examples": examples,
               "measurement_scope": "Exact prescribed-input local-condition audit, no timings or synthesized controller comparison"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(f"Exported {len(identities)} holds and {verified['condition_assessments']} verified condition assessments")


if __name__ == "__main__":
    main()
