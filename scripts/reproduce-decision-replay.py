"""Preserve strict decision replay of archived runs and an explicit method matrix."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tarfile

from tick_trap.planar_control import PLANAR_METHODS
from tick_trap.planar_experiments import PlanarConfig, run_planar
from tick_trap.reporting import provenance, read_json, write_json


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/decision-replay.json"))
    parser.add_argument("--output", type=Path, default=Path("results/decision-replay"))
    args = parser.parse_args()
    spec = read_json(args.config)
    if set(spec) != {"input_archive", "input_manifest", "runs_member", "metadata_member", "generated"}:
        raise ValueError("Unknown decision study configuration")
    source = provenance(spec)
    if source["git_status"] != "" or not source["git_commit"]:
        raise ValueError("Reproduction requires a clean source revision")
    source["timing_scope"] = "Generated records retain incidental clocks; decision replay excludes clocks, deadlines and floating display estimates"
    archive_path, manifest_path = Path(spec["input_archive"]), Path(spec["input_manifest"])
    manifest = json.loads(manifest_path.read_text())
    if digest(archive_path) != manifest["archive_sha256"]:
        raise ValueError("Input archive hash mismatch")
    with tarfile.open(archive_path, "r:gz") as archive:
        if (len(archive.getnames()) != len(manifest["files"])
                or set(archive.getnames()) != {f["path"] for f in manifest["files"]}):
            raise ValueError("Input archive coverage mismatch")
        for item in manifest["files"]:
            data = archive.extractfile(item["path"]).read()
            if len(data) != item["bytes"] or sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Input archive member hash mismatch")
        raw_runs = archive.extractfile(spec["runs_member"]).read()
        raw_metadata = archive.extractfile(spec["metadata_member"]).read()
    old_source = json.loads(raw_metadata)
    if (old_source["git_status"] != "" or old_source["git_commit"] != manifest["source_git_commit"]
            or old_source["source_sha256"] != manifest["source_sha256"]):
        raise ValueError("Input source identity mismatch")
    root = args.output
    root.mkdir(parents=True, exist_ok=True)
    (root/"archived-runs.json").write_bytes(raw_runs)
    (root/"archived-input-metadata.json").write_bytes(raw_metadata)
    generated = spec["generated"]
    if set(generated) != {"base", "cases"} or not generated["cases"]:
        raise ValueError("Expected a generated base and nonempty case list")
    configurations, names = [], []
    for case in generated["cases"]:
        name = case["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("Generated case labels must be distinct nonempty strings")
        names.append(name)
        configurations.append(PlanarConfig(**(generated["base"] | {k: v for k, v in case.items() if k != "name"})))
    runs = [run_planar(config) for config in configurations]
    write_json(root/"generated-runs.json", runs)
    generated_source = provenance([config.record() for config in configurations])
    generated_source.update(case_labels=names, timing_scope=source["timing_scope"])
    write_json(root/"generated-input-metadata.json", generated_source)
    write_json(root/"environment.json", source)
    write_json(root/"config.json", spec)
    cohorts = {}
    for name in ("archived", "generated"):
        command = [sys.executable, "-m", "tick_trap", "verify-decisions", "--runs", str(root/f"{name}-runs.json"),
                   "--metadata", str(root/f"{name}-input-metadata.json"), "--output", str(root/name)]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        (root/f"{name}-replay.log").write_text(result.stdout+result.stderr)
        checked_source = json.loads((root/name/"metadata.json").read_text())
        if checked_source["git_status"] != "" or checked_source["git_commit"] != source["git_commit"]:
            raise ValueError("Decision checks must use the same clean source as this reproduction")
        checked = json.loads((root/name/"verification.json").read_text())
        if checked["status"] != "verified" or not checked["declared_coverage_checked"]:
            raise ValueError("Missing declared-cohort verification")
        links = checked_source["configuration"]
        if links["runs_sha256"] != digest(root/f"{name}-runs.json") or links["input_metadata_sha256"] != digest(root/f"{name}-input-metadata.json"):
            raise ValueError("Decision verification input hash mismatch")
        cohorts[name] = {"verification": checked, "verification_sha256": digest(root/name/"verification.json"),
                         "checking_metadata_sha256": digest(root/name/"metadata.json"),
                         "runs_sha256": digest(root/f"{name}-runs.json"),
                         "input_metadata_sha256": digest(root/f"{name}-input-metadata.json"),
                         "input_source_commit": checked_source["configuration"]["input_source_commit"]}
        print(name+": "+result.stdout.strip())
    methods = sorted({config.method for config in configurations})
    summary = {"source": source, "input_dependencies": {"archive": str(archive_path), "sha256": digest(archive_path),
               "manifest_sha256": digest(manifest_path), "runs_member": spec["runs_member"],
               "metadata_member": spec["metadata_member"], "source_git_commit": old_source["git_commit"]},
               "cohorts": cohorts, "generated_case_labels": names, "generated_method_coverage": methods,
               "all_supported_methods_covered": set(methods) == set(PLANAR_METHODS),
               "scope": "Deterministic scientific-record replay and declared cohort coverage. Physical certificates, complete decisions and task flags are checked; reused implementation, excluded clocks/display estimates and model validity retain their documented limits."}
    write_json(root/"summary.json", summary)
    lines = ["# Planar decision replay evidence", "", summary["scope"], "",
             "| Cohort | Method | Runs | Decisions | Executed holds | Failed decisions | Candidate assessments |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for cohort, data in cohorts.items():
        for row in data["verification"]["groups"]:
            lines.append(f"| {cohort} | {row['method']} | {row['runs']} | {row['decision_updates']} | {row['executed_holds']} | {row['failed_decisions']} | {row['checked_candidates']} |")
    lines += ["", "Verified means faithful to the current implementation, not necessarily safe.",
              "An unsafe but accurately recorded endpoint-controller example is intentionally retained.",
              "A valid online comparison survives an offline oracle unknown; genuinely uncertified execution stops.",
              "Clocks and floating estimates are explicitly excluded and are not authenticated by this replay.", ""]
    (root/"report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
