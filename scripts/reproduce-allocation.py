"""Explain the committed certification audit using hash-checked original inputs."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("docs/data/audit-evidence.tar.gz"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/data/audit-manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("results/work-allocation"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root/"src"))
    from tick_trap.reporting import provenance, write_json

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory to avoid mixing evidence")
    source = provenance({})
    if source["git_status"] != "":
        raise ValueError("Commit source changes before recording allocation evidence")
    manifest = json.loads(args.manifest.read_text())
    if sha256(args.archive.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Original evidence archive hash mismatch")
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(root/"src"), PYTHONNOUSERSITE="1", PYTHONHASHSEED="0")
    commands = []
    with tempfile.TemporaryDirectory(prefix="tick-trap-allocation-") as folder:
        temporary = Path(folder)
        configurations = []
        with tarfile.open(args.archive, "r:gz") as archive:
            # Check all original members, extracting only the two study inputs.
            for entry in manifest["files"]:
                data = archive.extractfile(entry["path"]).read()
                if len(data) != entry["bytes"] or sha256(data).hexdigest() != entry["sha256"]:
                    raise ValueError("Original archive member hash mismatch: "+entry["path"])
            for directory, label in (("auxiliary-cost", "per-polynomial"), ("auxiliary-total-work", "per-control")):
                inputs = temporary/label
                inputs.mkdir()
                for name in ("study.json", "metadata.json"):
                    (inputs/name).write_bytes(archive.extractfile(directory+"/"+name).read())
                config = json.loads((inputs/"metadata.json").read_text())["configuration"]
                configurations.append({k: v for k, v in config.items() if k != "budget_scope"})
                command = [sys.executable, "-m", "tick_trap", "allocation-audit", "--study", str(inputs/"study.json"),
                           "--output", str(output/label)]
                print("Replaying " + label, flush=True)
                with (output/(label+".log")).open("w") as stream:
                    subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT, check=True)
                commands.append(command)
        if configurations[0] != configurations[1]:
            raise ValueError("Allocation policies used different input configurations")
    write_json(output/"environment.json", provenance({"input_archive_sha256": manifest["archive_sha256"],
               "input_source_commit": manifest["source_git_commit"], "input_source_sha256": manifest["source_sha256"],
               "input_manifest_sha256": sha256(args.manifest.read_bytes()).hexdigest(), "commands": commands}))
    reports = {name: json.loads((output/name/"audit.json").read_text()) for name in ("per-control", "per-polynomial")}
    shared_rows, full_rows = reports["per-control"]["measurements"], reports["per-polynomial"]["measurements"]
    if len(shared_rows) != len(full_rows):
        raise ValueError("Counterfactual measurement coverage mismatch")
    identity = ("case_index", "candidate_index", "case", "action_exact", "strategy", "tolerance_exact", "budget", "independent_joint_status")
    for shared_row, full_row in zip(shared_rows, full_rows):
        if any(shared_row[k] != full_row[k] for k in identity) or shared_row["full_per_polynomial_status"] != full_row["status"]:
            raise ValueError("Counterfactual differs from the replayed per-polynomial experiment")
        if [t["full_per_polynomial_certificate"] for t in shared_row["trace"]] != [t["certificate"] for t in full_row["trace"]]:
            raise ValueError("Counterfactual polynomial evidence differs from the original policy replay")
    selected = []
    shared = reports["per-control"]
    for case, strategy, action in (("interior_braking_margin", "minimum", ["1", "-1"]),
                                   ("negative_geometry_auxiliary_unknown", "sign", ["1/2", "0"]),
                                   ("auxiliary_exact_tangent", "auxiliary_sign", ["544/625", "0"])):
        selected.append(next(row for row in shared["measurements"] if row["case"] == case and row["strategy"] == strategy
                             and row["action_exact"] == action and row["budget"] == 8
                             and row["tolerance_exact"] == "1/1000000000000"))
    keys = ("status", "budget_scope", "property_configurations", "replayed_queries",
            "unique_bernstein_replays", "unique_independent_sign_references", "groups", "scope")
    summary = {"replay_source": {k: source[k] for k in ("git_commit", "source_sha256", "python", "platform", "git_status")},
               "input_archive_sha256": manifest["archive_sha256"], "input_source_commit": manifest["source_git_commit"],
               "counterfactual_matched_configurations": len(shared_rows),
               "results": {name: {k: report[k] for k in keys} for name, report in reports.items()}, "examples": selected,
               "output_hashes": {str(path.relative_to(output)): sha256(path.read_bytes()).hexdigest()
                                 for path in sorted(output.rglob("*")) if path.is_file()}}
    write_json(output/"summary.json", summary)
    print("Both allocation policies replayed; original archived evidence was preserved", flush=True)


if __name__ == "__main__":
    main()
