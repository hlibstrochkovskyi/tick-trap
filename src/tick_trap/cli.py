import argparse
import hashlib
import json
import sys
from pathlib import Path

from .benchmark import benchmark
from .dynamics import Circle, PlanarState, WallState
from .experiments import RunConfig, load_grid, run
from .learning import learning_study
from .oracle import circle_interval, wall_interval
from .planar_audit import audit_cases
from .planar_experiments import PlanarConfig, load_planar_grid, run_planar
from .planar_reporting import write_planar_runs
from .reporting import counterexample_svg, provenance, read_json, write_json, write_runs
from .verification import verify_planar_runs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tick-trap", description="Continuous-time safety analysis for sampled robot control")
    sub = parser.add_subparsers(dest="command", required=True)
    example = sub.add_parser("counterexample", help="Reproduce the analytical hidden collision")
    example.add_argument("--output", default="results/counterexample")
    verification = sub.add_parser("verify", help="Replay exact planar run records and retained-plan proofs")
    verification.add_argument("--runs", default="results/continuations/runs.json")
    verification.add_argument("--output", default="results/verification")
    for command, help_text, default in [
        ("run", "Run a single wall configuration", "configs/wall.json"),
        ("sweep", "Run a reproducible Cartesian experiment grid", "configs/baselines.json"),
        ("certify", "Analyze a planar held trajectory against a circle", "configs/planar.json"),
        ("learn", "Fit a small actuator model and test changed dynamics", "configs/learning.json"),
        ("benchmark", "Measure trajectory certificate precision and cost", "configs/certification.json"),
        ("planar-run", "Run a controlled planar scene", "configs/planar-control.json"),
        ("planar-sweep", "Compare planar filters on matched scenes", "configs/planar-baselines.json"),
        ("planar-audit", "Audit admitted controls against the trajectory certificates", "configs/planar-audit.json"),
    ]:
        item = sub.add_parser(command, help=help_text)
        item.add_argument("--config", default=default)
        item.add_argument("--output", default=f"results/{command}")
    args = parser.parse_args(argv)
    try:
        output = Path(args.output)
        if args.command == "counterexample":
            output.mkdir(parents=True, exist_ok=True)
            state = WallState("0.04", 1)
            result = wall_interval(state, -10, "0.2")
            result.update({"initial_viable": state.viability_margin(10) >= 0,
                           "trajectory": "d(t)=0.04-t+5t^2", "initial_d_exact": "1/25",
                           "initial_v_exact": "1", "held_u_exact": "-10", "duration_exact": "1/5",
                           "interpretation": "free-motion witness; no physical contact model"})
            write_json(output/"counterexample.json", result)
            write_json(output/"metadata.json", provenance(result))
            (output/"counterexample.svg").write_text(counterexample_svg())
            print("Safe samples; unsafe continuous trajectory. Minimum: -0.01 m at 0.1 s. Initial state: nonviable.")
        elif args.command == "verify":
            result = verify_planar_runs(read_json(args.runs))
            output.mkdir(parents=True, exist_ok=True)
            write_json(output/"verification.json", result)
            spec = {"runs_file": str(Path(args.runs).resolve()),
                    "runs_sha256": hashlib.sha256(Path(args.runs).read_bytes()).hexdigest()}
            write_json(output/"metadata.json", provenance(spec))
            print(f"Verified {result['runs']} runs, {result['executed_holds']} holds and {result['retained_plans']} retained plans.")
        else:
            spec = read_json(args.config)
            if args.command == "planar-audit":
                results = audit_cases(spec)
                output.mkdir(parents=True, exist_ok=True)
                write_json(output/"audit.json", results)
                write_json(output/"metadata.json", provenance(spec))
                lines = ["# tick-trap matched-control audit", "",
                         "Counts concern declared finite candidate sets and a single hold. Unknown truth is kept separate.", "",
                         "| Case | Predicate | Applicable controls | Safe admitted | Unsafe admitted | Safe excluded | Admitted / truth unknown |",
                         "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
                for case in results:
                    for predicate, counts in case["counts"].items():
                        lines.append(f"| {case['name']} | {predicate} | {counts['applicable']} | {counts['safe_admitted']} | "
                                     f"{counts['unsafe_admitted']} | {counts['safe_excluded']} | {counts['accepted_truth_unknown']} |")
                lines += ["", "| Case | SACBF predicate | Safe h and psi paths excluded | Safe h / unsafe psi excluded | Safe h / unknown psi excluded | Unsafe h or psi admitted | Admitted / high-order truth unknown |",
                          "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
                for case in results:
                    for predicate in ("sacbf", "sacbf_relaxed"):
                        counts = case["counts"][predicate]
                        lines.append(f"| {case['name']} | {predicate} | {counts['safe_high_order_paths_excluded']} | "
                                     f"{counts['geometrically_safe_auxiliary_unsafe_excluded']} | {counts['geometrically_safe_auxiliary_unknown_excluded']} | "
                                     f"{counts['unsafe_high_order_paths_admitted']} | {counts['accepted_high_order_truth_unknown']} |")
                lines += ["", "HOCBF and SACBF initial-domain exclusions are not counted as rejected controls.",
                          "The first table uses geometric h safety; SACBF also preserves psi, evaluated separately in the second table.",
                          "The relaxed SACBF predicate uses the zero-target feasibility envelope, not a slack-penalized QP.",
                          "Endpoint and chord acceptance do not assert a physical hold guarantee.",
                          "Safe-control exclusion by a sufficient condition is not a theorem violation.",
                          "[Exact per-control evidence and timings](audit.json).", ""]
                (output/"report.md").write_text("\n".join(lines))
                print(f"{len(results)} matched states; {sum(c['candidate_count'] for c in results)} controls audited.")
            elif args.command in ("planar-run", "planar-sweep"):
                configs = list(load_planar_grid(spec)) if args.command == "planar-sweep" else [PlanarConfig(**spec)]
                results = [run_planar(config) for config in configs]
                write_planar_runs(output, results, spec)
                print(f"{len(results)} planar runs; {sum(r['completed_safe_horizon'] for r in results)} safe completed horizons; "
                      f"{sum(r['collision_observed'] for r in results)} observed collisions.")
            elif args.command == "benchmark":
                results = benchmark(spec)
                output.mkdir(parents=True, exist_ok=True)
                write_json(output/"benchmark.json", results)
                write_json(output/"metadata.json", provenance(spec))
                lines = ["# tick-trap certificate cost", "",
                         "Empirical times; subdivision limits do not bound worst-case execution time.", "",
                         "| Case | Width tolerance (m²) | Subdivision budget | Status | Subdivisions | Median certificate (µs) |",
                         "| --- | --- | ---: | --- | ---: | ---: |"]
                for row in results:
                    result = row["result"]
                    lines.append(f"| {row['case']} | {row['tolerance']} | {row['budget']} | {result['continuous_status']} | "
                                 f"{result['subdivisions']} | {row['certificate_ns_median']/1000:.1f} |")
                lines += ["", "[Exact enclosures, all timings, and estimates](benchmark.json).", ""]
                (output/"report.md").write_text("\n".join(lines))
                print(f"{len(results)} certificate configurations measured.")
            elif args.command == "learn":
                result = learning_study(**spec)
                runs = result.pop("runs")
                write_runs(output, runs, spec)
                write_json(output/"learning.json", result)
                with (output/"report.md").open("a") as report:
                    report.write("\n[Learned model, training data, and held-out prediction errors](learning.json).\n\n"
                                 "Prediction errors do not establish a valid uncertainty bound or safety guarantee.\n")
                print(f"Learned actuator gain {result['model']['gain']:.6f}, bias {result['model']['bias']:.6f}; {len(runs)} control runs.")
            elif args.command == "certify":
                allowed = {"p", "v", "u", "center", "radius", "duration", "tolerance", "max_subdivisions"}
                if set(spec)-allowed:
                    raise ValueError(f"Unknown planar configuration keys: {set(spec)-allowed}")
                result = circle_interval(PlanarState(spec["p"], spec["v"]), spec["u"],
                                         Circle(spec["center"], spec["radius"]), spec["duration"],
                                         spec.get("tolerance", "1e-10"), spec.get("max_subdivisions", 4096))
                output.mkdir(parents=True, exist_ok=True)
                write_json(output/"certificate.json", result)
                write_json(output/"metadata.json", provenance(spec))
                print(f"Continuous trajectory: {result['continuous_status']}; sampled safe: {result['sampled_safe']}")
            else:
                configs = list(load_grid(spec)) if args.command == "sweep" else [RunConfig(**spec)]
                results = [run(config) for config in configs]
                write_runs(output, results, spec)
                print(f"{len(results)} runs; {sum(r['completed_safe_horizon'] for r in results)} safe completed horizons; "
                      f"{sum(r['collision_observed'] for r in results)} observed collisions.")
        print(f"Artifacts: {output.resolve()}")
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"tick-trap: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
