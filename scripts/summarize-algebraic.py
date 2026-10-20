"""Export a checked algebraic-versus-Bernstein cost comparison on matched holds."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from tick_trap.timing_evidence import verify_timing_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/algebraic-cost"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/algebraic-summary.json"))
    args = parser.parse_args()
    read = lambda name: json.loads((args.input/name).read_text())
    digest = lambda name: sha256((args.input/name).read_bytes()).hexdigest()
    study, source = read("study.json"), read("metadata.json")
    replay, replay_source = read("replay/audit.json"), read("replay/metadata.json")
    if (source["git_status"] != "" or replay_source["git_status"] != ""
            or source["git_commit"] != replay_source["git_commit"]):
        raise ValueError("Study and replay must identify the same clean source revision")
    links = replay_source["configuration"]
    if (replay["status"] != "verified" or links["study_sha256"] != digest("study.json")
            or links["input_metadata_sha256"] != digest("metadata.json")
            or replay["property_configurations"] != len(study["measurements"])):
        raise ValueError("Scientific replay does not match the exact study input")
    timing = verify_timing_evidence(source["configuration"], study)
    groups = [{k: v for k, v in g.items() if not k.startswith("reference_") and k != "accepted_reference_unknown"}
              for g in study["groups"]]
    cases = []
    for index, case in enumerate(study["reference"]):
        rows = [r for r in study["measurements"] if r["case_index"] == index]
        cases.append({"case": case["name"], "controls": case["candidate_count"],
                      "in_initial_domain": case["hocbf_applicable"],
                      "joint_truth_counts": dict(Counter(c["independent_high_order_status"] for c in case["candidates"]
                                                         if "independent_high_order_status" in c)),
                      "first_control_exact": case["candidates"][0]["action_exact"],
                      "first_control_results": [{k: r[k] for k in ("strategy", "tolerance_exact", "budget", "predicate_ns_median")} |
                                                {"status": r["result"]["status"], "subdivisions": r["result"]["subdivisions"]}
                                                for r in rows if r["candidate_index"] == 0]})
    algebraic = [r for r in study["measurements"] if r["strategy"] == "sturm"]
    if not algebraic or any(r["budget"] is not None or r["tolerance_exact"] is not None or
                            r["result"]["status"] == "unknown" for r in algebraic):
        raise ValueError("Missing or misrepresented algebraic comparator")
    result = {"source": source, "source_artifacts": {name: {"sha256": digest(name)} for name in
              ("study.json", "metadata.json", "replay/audit.json", "replay/metadata.json")},
              "scientific_replay": {k: replay[k] for k in ("status", "property_configurations", "replayed_queries",
                                                           "unique_independent_sign_references", "scope")},
              "timing_evidence": timing, "budget_scope": study["budget_scope"],
              "controls": len(algebraic), "joint_truth_counts": dict(Counter(r["independent_reference_status"] for r in algebraic)),
              "groups": groups, "paired_comparisons": study["paired_comparisons"], "cases": cases,
              "scope": "Offline fixed-input cost comparison targeting both h and psi under the exact planar held-input model; Sturm has no subdivision budget and uses the same algebra as the offline truth reference. No controller decisions are changed, no clock or hard deadline is certified, and no algorithmic novelty is claimed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(f"Exported {len(algebraic)} controls and {timing['elapsed_samples']} checked elapsed samples")


if __name__ == "__main__":
    main()
