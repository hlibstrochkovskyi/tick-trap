"""Compare geometric predicates on the hash-checked archived control cohort."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from tick_trap.geometry_study import geometry_study, verify_geometry_study
from tick_trap.reporting import provenance, read_json, write_json


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def inputs(spec):
    if not isinstance(spec, dict) or set(spec) != {"input_archive", "input_manifest", "settings"}:
        raise ValueError("Expected input_archive, input_manifest and settings")
    path, manifest_path = Path(spec["input_archive"]), Path(spec["input_manifest"])
    manifest = json.loads(manifest_path.read_text())
    if digest(path) != manifest["archive_sha256"]:
        raise ValueError("Source archive hash mismatch")
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        if (len(members) != len(manifest["files"]) or not all(m.isfile() for m in members)
                or {m.name for m in members} != {m["path"] for m in manifest["files"]}):
            raise ValueError("Source archive coverage mismatch")
        for entry in manifest["files"]:
            raw = archive.extractfile(entry["path"]).read()
            if len(raw) != entry["bytes"] or sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError("Source archive member hash mismatch")
        raw_study, raw_source = archive.extractfile("study.json").read(), archive.extractfile("metadata.json").read()
    source = json.loads(raw_source)
    if (source["git_status"] != "" or source["git_commit"] != manifest["source_git_commit"]
            or source["source_sha256"] != manifest["source_sha256"]
            or sha256(json.dumps(source["configuration"], sort_keys=True).encode()).hexdigest() != source["configuration_sha256"]):
        raise ValueError("Source identity or embedded configuration mismatch")
    return source["configuration"], json.loads(raw_study), {
        "archive_sha256": digest(path), "manifest_sha256": digest(manifest_path),
        "source_git_commit": source["git_commit"], "source_sha256": source["source_sha256"],
        "study_sha256": sha256(raw_study).hexdigest(), "metadata_sha256": sha256(raw_source).hexdigest()}


def metadata(spec):
    result = provenance(spec)
    result["timing_scope"] = "Empirical matched geometric predicate and evidence construction; excludes offline reference, generation and action search; no simulated execution"
    result["audit_script_sha256"] = digest(__file__)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/geometry-cost.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path, help="Replay exact science and verify the saved empirical timing layout")
    args = parser.parse_args()
    if args.verify:
        root = args.verify
        source = json.loads((root/"metadata.json").read_text())
        spec = source["configuration"]
        if (source["git_status"] != "" or not source["git_commit"]
                or sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest() != source["configuration_sha256"]):
            raise ValueError("Saved study must identify its clean source and intact configuration")
        source_spec, original, dependencies = inputs(spec)
        saved = json.loads((root/"study.json").read_text())
        if saved["input_dependencies"] != dependencies:
            raise ValueError("Saved source dependency hashes differ")
        verified = verify_geometry_study(source_spec, original, spec["settings"],
                                         {k: v for k, v in saved.items() if k != "input_dependencies"})
        output = args.output or root/"verification"
        output.mkdir(parents=True, exist_ok=True)
        write_json(output/"verification.json", verified)
        write_json(output/"metadata.json", metadata({"input_source_commit": source["git_commit"],
                   "study_sha256": digest(root/"study.json"), "input_metadata_sha256": digest(root/"metadata.json"),
                   "input_archive_sha256": dependencies["archive_sha256"]}))
        keys = ("controls", "cases", "applicable_cases", "strategies", "seed", "repeats", "budget_scope",
                "geometric_truth_counts", "joint_truth_counts", "diagnostics", "groups", "paired_comparisons", "assumptions", "scope")
        compact = {"source": source, "input_dependencies": dependencies, "verification": verified,
                   **{k: saved[k] for k in keys},
                   "source_artifacts": {name: {"sha256": digest(root/name)} for name in ("study.json", "metadata.json")},
                   "verification_artifacts": {name: {"sha256": digest(output/name)} for name in ("verification.json", "metadata.json")}}
        write_json(root/"compact.json", compact)
        print(f"Verified {verified['controls']} controls, {verified['predicate_results']} predicates and their empirical timing layout")
        return
    spec = read_json(args.config)
    source = metadata(spec)
    if source["git_status"] != "" or not source["git_commit"]:
        raise ValueError("Commit source changes before recording geometric timing evidence")
    output = args.output or Path("results/geometry-cost")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory to avoid mixing evidence")
    source_spec, original, dependencies = inputs(spec)
    study = geometry_study(source_spec, original, spec["settings"]) | {"input_dependencies": dependencies}
    after = metadata(spec)
    if any(after[k] != source[k] for k in ("git_status", "git_commit", "source_sha256", "audit_script_sha256")):
        raise ValueError("Source changed during the benchmark")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/"study.json", study)
    write_json(output/"metadata.json", source)
    lines = ["# Matched geometric predicate costs", "", study["scope"], "",
             "| Predicate | Tolerance | Shared splits | Geometrically safe accepted | Unsafe rejected | Safe unknown | Unsafe unknown | Accepted auxiliary-unsafe | Median us/control |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for g in study["groups"]:
        lines.append(f"| {g['strategy']} | {g['tolerance_exact']} | {g['budget']} | {g['accepted_safe_controls']} | "
                     f"{g['rejected_unsafe_controls']} | {g['unknown_safe_controls']} | {g['unknown_unsafe_controls']} | "
                     f"{g['accepted_auxiliary_unsafe_controls']} | {g['median_per_control_ns']/1000:.3f} |")
    lines += ["", "These predicates require geometry only. Accepting an auxiliary-unsafe path is not an h-and-psi certificate.",
              "Endpoint/chord diagnostics are reported separately and do not certify the physical path.",
              "Tube failures remain unknown. Zero splits for algebra or tubes do not mean zero cost or an equal-work comparison.",
              "Timing is empirical, interleaved and descriptive; offline references, action search and execution are excluded.", ""]
    (output/"report.md").write_text("\n".join(lines))
    print(f"Measured {study['controls']} fixed controls over {len(study['groups'])} settings")


if __name__ == "__main__":
    main()
