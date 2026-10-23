"""Reproduce elementary chord/held-trajectory contracts without running MPC."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tick_trap.reporting import provenance, read_json, write_json
from tick_trap.segment_audit import segment_contract_study, verify_segment_contract_study


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def metadata(spec):
    result = provenance(spec)
    result["timing_scope"] = "No timing samples; deterministic offline geometric contract audit"
    result["audit_script_sha256"] = digest(__file__)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/segment-contracts.json"))
    parser.add_argument("--verify", type=Path, help="Regenerate a saved output directory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        root = args.verify
        source = read_json(root/"metadata.json")
        spec = source["configuration"]
        configuration_hash = sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        if (source["git_status"] != "" or not source["git_commit"]
                or configuration_hash != source["configuration_sha256"]):
            raise ValueError("Saved audit must identify its clean source and intact configuration")
        saved = read_json(root/"audit.json")
        verified = verify_segment_contract_study(spec, saved)
        output = args.output or root/"verification"
        output.mkdir(parents=True, exist_ok=True)
        write_json(output/"verification.json", verified)
        write_json(output/"metadata.json", metadata({"input_source_commit": source["git_commit"],
                   "input_metadata_sha256": digest(root/"metadata.json"),
                   "audit_sha256": digest(root/"audit.json")}))
        compact = {"source": source, "verification": verified,
                   "source_artifacts": {name: {"sha256": digest(root/name)}
                                        for name in ("audit.json", "metadata.json")},
                   "verification_artifacts": {name: {"sha256": digest(output/name)}
                                              for name in ("verification.json", "metadata.json")},
                   "counts": saved["counts"], "chord_to_trajectory": saved["chord_to_trajectory"],
                   "cases": [{k: r[k] for k in ("name", "sampled_status", "chord_status", "tube_status", "trajectory_status")}
                             for r in saved["records"]],
                   "assumptions": saved["assumptions"], "scope": saved["scope"]}
        write_json(root/"compact.json", compact)
        print(f"Verified {verified['holds']} holds and {verified['obstacle_queries']} obstacle queries")
        return
    spec = read_json(args.config)
    result = segment_contract_study(spec)
    output = args.output or Path("results/segment-contracts")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/"audit.json", result)
    write_json(output/"metadata.json", metadata(spec))
    lines = ["# Chord and held-trajectory contracts", "", result["scope"], "",
             "| Fixed hold | Sampled endpoints | Connecting chord | Tube sufficient condition | Actual trajectory sign reference |",
             "| --- | --- | --- | --- | --- |"]
    for r in result["records"]:
        lines.append(f"| {r['name']} | {r['sampled_status']} | {r['chord_status']} | {r['tube_status']} | {r['trajectory_status']} |")
    lines += ["", "Failed tube implications remain unknown, even when the separate offline sign reference resolves them.",
              "This is elementary exact interpolation geometry, not a published SSCBF/MPC implementation or a new controller.",
              "No execution, recursive feasibility, runtime ranking or hardware guarantee is inferred.", ""]
    (output/"report.md").write_text("\n".join(lines))
    print(f"Audited {result['counts']['holds']} fixed holds")


if __name__ == "__main__":
    main()
