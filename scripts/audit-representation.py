"""Reproduce representation/tolerance diagnostics on the archived polynomial catalog."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from tick_trap.representation_study import representation_study, verify_representation_study
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
        if (len(archive.getnames()) != len(manifest["files"])
                or set(archive.getnames()) != {f["path"] for f in manifest["files"]}):
            raise ValueError("Source archive member coverage mismatch")
        for item in manifest["files"]:
            data = archive.extractfile(item["path"]).read()
            if len(data) != item["bytes"] or sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Source archive member hash mismatch")
        raw, raw_source = archive.extractfile("audit.json").read(), archive.extractfile("metadata.json").read()
    source = json.loads(raw_source)
    if (source["git_status"] != "" or source["git_commit"] != manifest["source_git_commit"]
            or source["source_sha256"] != manifest["source_sha256"]):
        raise ValueError("Source identity mismatch")
    return json.loads(raw), {"archive": str(path), "archive_sha256": digest(path),
           "manifest_sha256": digest(manifest_path), "input_catalog_sha256": sha256(raw).hexdigest(),
           "input_metadata_sha256": sha256(raw_source).hexdigest(),
           "input_source_commit": source["git_commit"], "input_source_sha256": source["source_sha256"]}


def metadata(spec):
    result = provenance(spec)
    result["timing_scope"] = "No elapsed-time samples; deterministic offline representation and width-policy audit"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/representation-study.json"))
    parser.add_argument("--verify", type=Path, help="Regenerate a saved output directory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        root = args.verify
        source = json.loads((root/"metadata.json").read_text())
        if source["git_status"] != "" or not source["git_commit"]:
            raise ValueError("Saved study must identify a clean source revision")
        catalog, dependencies = inputs(source["configuration"])
        saved = json.loads((root/"audit.json").read_text())
        if saved["input_dependencies"] != dependencies:
            raise ValueError("Saved input dependencies do not match")
        verified = verify_representation_study(catalog, source["configuration"]["settings"],
                                               {k: v for k, v in saved.items() if k != "input_dependencies"})
        output = args.output or root/"verification"
        output.mkdir(parents=True, exist_ok=True)
        write_json(output/"verification.json", verified)
        write_json(output/"metadata.json", metadata({"input_source_commit": source["git_commit"],
                   "audit_sha256": digest(root/"audit.json"), "input_metadata_sha256": digest(root/"metadata.json"),
                   "input_archive_sha256": dependencies["archive_sha256"]}))
        examples = []
        for query in saved["queries"]:
            if not any(u["property"] == "psi" and u["candidate_index"] == 0 and u["case"] in
                       ("auxiliary_exact_tangent", "auxiliary_tangent_positive", "auxiliary_tangent_negative") for u in query["uses"]):
                continue
            representations = [r for r in query["representations"] if r["time_basis"] == "physical"]
            examples.append({k: v for k, v in query.items() if k != "representations"} | {"representations": representations})
        summary = {"source": source, "input_dependencies": dependencies, "verification": verified,
                   "source_artifacts": {name: {"sha256": digest(root/name)} for name in ("audit.json", "metadata.json")},
                   "verification_artifacts": {name: {"sha256": digest(output/name)} for name in ("verification.json", "metadata.json")},
                   "source_queries": saved["source_queries"], "property_uses": saved["property_uses"],
                   "controls": len(saved["controls"]), "joint_truth_counts": saved["joint_truth_counts"],
                   "unique_backend_evaluations": saved["unique_backend_evaluations"],
                   "groups": saved["groups"], "examples": examples, "scope": saved["scope"]}
        write_json(root/"compact.json", summary)
        print(f"Verified {verified['certificate_evaluations']} represented certificates across {verified['groups']} settings")
        return
    spec = read_json(args.config)
    catalog, dependencies = inputs(spec)
    result = representation_study(catalog, spec["settings"]) | {"input_dependencies": dependencies}
    output = args.output or Path("results/representation-study")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/"audit.json", result)
    write_json(output/"metadata.json", metadata(spec))
    lines = ["# Representation and tolerance study", "", result["scope"], "",
             "| Method | Base tolerance | Budget | Scale | Time basis | Width policy | Safe controls accepted | Unsafe controls rejected | Safe unknown | Unsafe unknown |",
             "| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for g in result["groups"]:
        lines.append(f"| {g['method']} | {g['base_tolerance_exact']} | {g['budget']} | {g['scale_exact']} | {g['time_basis']} | "
                     f"{g['tolerance_policy']} | {g['accepted_safe_controls']} | {g['rejected_unsafe_controls']} | "
                     f"{g['unknown_safe_controls']} | {g['unknown_unsafe_controls']} |")
    lines += ["", "Equivalent-width and pure-time substitutions preserve converted certificates and work counts exactly.",
              "Fixed absolute widths can change unknown outcomes without changing physical safety.",
              "Controls are fixed-input joint h-and-psi assessments, not executed controller decisions.",
              "No timing data or equal primitive-work guarantee is claimed. Controller behavior is unchanged.", ""]
    (output/"report.md").write_text("\n".join(lines))
    print(f"Audited {result['source_queries']} polynomials and {len(result['controls'])} fixed controls")


if __name__ == "__main__":
    main()
