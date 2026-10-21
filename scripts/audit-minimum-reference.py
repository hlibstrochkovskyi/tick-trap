"""Audit archived planar minima with an independent rational stationary reference."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from tick_trap.minimum_audit import minimum_reference_audit, verify_minimum_reference_audit
from tick_trap.reporting import provenance, read_json, write_json


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def inputs(spec):
    if not isinstance(spec, dict) or set(spec) != {"input_archive", "input_manifest", "settings"}:
        raise ValueError("Expected input_archive, input_manifest and settings")
    archive_path, manifest_path = Path(spec["input_archive"]), Path(spec["input_manifest"])
    manifest = json.loads(manifest_path.read_text())
    if digest(archive_path) != manifest["archive_sha256"]:
        raise ValueError("Source archive hash mismatch")
    with tarfile.open(archive_path, "r:gz") as archive:
        if (len(archive.getnames()) != len(manifest["files"])
                or set(archive.getnames()) != {f["path"] for f in manifest["files"]}):
            raise ValueError("Source archive member coverage mismatch")
        for item in manifest["files"]:
            content = archive.extractfile(item["path"]).read()
            if len(content) != item["bytes"] or sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("Source archive member hash mismatch")
        raw_study, raw_source = archive.extractfile("study.json").read(), archive.extractfile("metadata.json").read()
    source = json.loads(raw_source)
    if (source["git_status"] != "" or source["git_commit"] != manifest["source_git_commit"]
            or source["source_sha256"] != manifest["source_sha256"]):
        raise ValueError("Source archive must identify its clean source revision")
    return json.loads(raw_study), source, {
        "archive_path": str(archive_path), "archive_sha256": digest(archive_path),
        "manifest_path": str(manifest_path), "manifest_sha256": digest(manifest_path),
        "source_git_commit": source["git_commit"], "source_sha256": source["source_sha256"],
        "study_sha256": sha256(raw_study).hexdigest(), "metadata_sha256": sha256(raw_source).hexdigest()}


def metadata(spec):
    result = provenance(spec)
    result["timing_scope"] = "No timing samples collected; deterministic offline minimum-enclosure cross-check"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/minimum-reference.json"))
    parser.add_argument("--verify", type=Path, help="Regenerate a previously saved output directory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        root = args.verify
        source = json.loads((root/"metadata.json").read_text())
        if source["git_status"] != "" or not source["git_commit"]:
            raise ValueError("Saved audit must identify a clean source revision")
        study, original_source, dependencies = inputs(source["configuration"])
        saved = json.loads((root/"audit.json").read_text())
        if saved["input_dependencies"] != dependencies:
            raise ValueError("Source dependencies differ from the saved audit")
        verified = verify_minimum_reference_audit(original_source["configuration"], study,
                                                source["configuration"]["settings"],
                                                {k: v for k, v in saved.items() if k != "input_dependencies"})
        output = args.output or root/"verification"
        output.mkdir(parents=True, exist_ok=True)
        write_json(output/"verification.json", verified)
        write_json(output/"metadata.json", metadata({"input_source_commit": source["git_commit"],
                   "audit_sha256": digest(root/"audit.json"), "input_metadata_sha256": digest(root/"metadata.json"),
                   "input_archive_sha256": dependencies["archive_sha256"]}))
        examples = [q for q in saved["queries"] if any(u["property"] == "psi" and u["candidate_index"] == 0
                    and u["case"] in ("auxiliary_exact_tangent", "auxiliary_tangent_positive", "auxiliary_tangent_negative")
                    for u in q["uses"])]
        compact = {"source": source, "input_dependencies": dependencies, "verification": verified,
                   "source_artifacts": {name: {"sha256": digest(root/name)} for name in ("audit.json", "metadata.json")},
                   "verification_artifacts": {name: {"sha256": digest(output/name)} for name in ("verification.json", "metadata.json")},
                   "counts": {k: saved[k] for k in ("cases", "applicable_cases", "controls", "property_uses", "unique_queries")},
                   "source_predicate_replay": saved["source_predicate_replay"], "groups": saved["groups"],
                   "examples": examples, "scope": saved["scope"]}
        write_json(root/"compact.json", compact)
        print(f"Verified {verified['unique_queries']} unique polynomials and {verified['enclosure_comparisons']} enclosure pairs")
        return
    spec = read_json(args.config)
    study, source, dependencies = inputs(spec)
    audit = minimum_reference_audit(source["configuration"], study, spec["settings"]) | {"input_dependencies": dependencies}
    output = args.output or Path("results/minimum-reference")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/"audit.json", audit)
    write_json(output/"metadata.json", metadata(spec))
    lines = ["# Independent minimum-reference audit", "", audit["scope"], "",
             "| Tolerance | Bisection allowance | Unique polynomials | Stationary width reached | Bernstein width reached | Stationary unknown signs | Bernstein unknown signs |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for g in audit["groups"]:
        lines.append(f"| {g['tolerance_exact']} | {g['budget']} | {g['unique_queries']} | {g['stationary']['precision_reached']} | "
                     f"{g['bernstein']['precision_reached']} | {g['stationary']['unknown']} | {g['bernstein']['unknown']} |")
    lines += ["", "All matched and archived enclosure intersections are nonempty.",
              "Width attainment does not decide a sign across zero; a complete sign reference remains separate.",
              "A root-box bisection and a Bernstein split do not represent equal primitive work. No timing samples were collected.",
              "No controller, online unknown or fallback is changed.", ""]
    (output/"report.md").write_text("\n".join(lines))
    print(f"Audited {audit['property_uses']} property uses over {audit['unique_queries']} unique polynomials")


if __name__ == "__main__":
    main()
