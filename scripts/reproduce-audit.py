"""Reproduce this audit in a clean local clone and fresh stdlib-only venv."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def worker(output):
    from tick_trap.algebraic_reference import exact_sign_reference
    from tick_trap.planar_experiments import PlanarConfig, run_planar
    from tick_trap.polynomial import certify_sign
    from tick_trap.reporting import provenance, write_json
    from tick_trap.verification import verify_planar_runs

    output.mkdir(parents=True, exist_ok=True)
    commands = []
    def run(arguments, log):
        command = [sys.executable, *arguments]
        print("Running " + " ".join(arguments), flush=True)
        with (output/log).open("w") as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        commands.append({"argv": command, "log": log})

    run(["-m", "unittest", "discover", "-s", "tests", "-v"], "tests.log")
    for config, directory in (("auxiliary-cost", "auxiliary-cost"), ("auxiliary-total-work", "auxiliary-total-work")):
        run(["-m", "tick_trap", "certification-study", "--config", f"configs/{config}.json",
             "--output", str(output/directory)], directory+".log")
    run(["-m", "tick_trap", "planar-sweep", "--config", "configs/auxiliary-baselines.json",
         "--output", str(output/"auxiliary-baselines")], "auxiliary-baselines.log")
    run(["-m", "tick_trap", "verify", "--runs", str(output/"auxiliary-baselines/runs.json"),
         "--output", str(output/"auxiliary-verification")], "auxiliary-verification.log")
    run(["-m", "tick_trap", "counterexample", "--output", str(output/"counterexample")], "counterexample.log")
    for name in ("auxiliary-cost", "auxiliary-total-work"):
        run(["scripts/summarize-certification.py", "--comparison", "sign-auxiliary",
             "--study", str(output/name/"study.json"), "--runs", str(output/"auxiliary-baselines/runs.json"),
             "--verification", str(output/"auxiliary-verification/verification.json"),
             "--output", str(output/(name+"-summary.json"))], name+"-summary.log")

    from fractions import Fraction as F
    corpus = [("zero", [0]), ("positive_constant", [F(1, 10**400)]),
              ("negative_constant", [-F(1, 10**400)]), ("endpoint_contact", [0, 1, -1]),
              ("exact_tangency", [F(9, 100), F(-3, 5), 1]),
              ("tiny_positive", [F(9, 100)+F(1, 10**400), F(-3, 5), 1]),
              ("tiny_negative", [F(9, 100)-F(1, 10**400), F(-3, 5), 1]),
              ("irrational_repeated_roots", [F(1, 4), 0, -1, 0, 1])]
    references = []
    for name, coefficients in corpus:
        online = [certify_sign(coefficients, 1, "1e-30", b) for b in (0, 8, 64)]
        reference = exact_sign_reference(coefficients, 1)
        assert all(c.status in (reference["status"], "unknown") for c in online)
        references.append({"name": name, "coefficients_exact": [str(c) for c in coefficients], "duration_exact": "1",
                           "independent": reference,
                           "online": [{"budget": b, "status": c.status, "lower_exact": str(c.lower),
                                       "upper_exact": str(c.upper), "subdivisions": c.subdivisions}
                                      for b, c in zip((0, 8, 64), online)]})
    write_json(output/"reference-corpus.json", references)
    common = dict(p=("-0.3", "1.06"), v=(1, 0), nominal_policy="constant", nominal=(0, 0),
                  obstacles=({"center": [0, 0], "radius": 1},), lambda1="3", a_max="1", duration="1",
                  horizon="2", max_subdivisions=0, oracle_max_subdivisions=0)
    runs = [run_planar(PlanarConfig(method=m, **common)) for m in ("nominal", "auxiliary_sign_candidates")]
    write_json(output/"execution-evidence.json", runs)
    write_json(output/"execution-verification.json", verify_planar_runs(runs))
    snapshot = provenance({"study_configs": ["configs/auxiliary-cost.json", "configs/auxiliary-total-work.json",
                                          "configs/auxiliary-baselines.json"], "commands": commands})
    if snapshot["git_status"] != "":
        raise RuntimeError("Reproduction source must remain clean")
    write_json(output/"environment.json", snapshot)
    print("All audit commands completed successfully", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/audit-milestone"))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.worker:
        worker(output)
        return
    root = Path(__file__).resolve().parents[1]
    git = ["sh", str(root/"scripts/git-local")]
    if subprocess.check_output([*git, "status", "--porcelain"], cwd=root).strip():
        raise RuntimeError("Commit all source changes before reproducing the audit")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory to avoid mixing evidence")
    temporary = Path(tempfile.mkdtemp(prefix="tick-trap-audit-"))
    clone = temporary/"source"
    repository = root/".tick-trap-git" if (root/".tick-trap-git").is_dir() else root
    subprocess.run(["git", "clone", "--no-hardlinks", str(repository), str(clone)], check=True)
    venv.EnvBuilder(with_pip=False).create(temporary/"venv")
    env = os.environ.copy()
    env.update(PYTHONPATH=str(clone/"src"), PYTHONNOUSERSITE="1", PYTHONHASHSEED="0")
    subprocess.run([str(temporary/"venv/bin/python"), str(clone/"scripts/reproduce-audit.py"),
                    "--worker", "--output", str(output)], cwd=clone, env=env, check=True)
    print(f"Clean source and virtual environment retained at {temporary}")


if __name__ == "__main__":
    main()
