import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from .benchmark import benchmark
from .allocation_audit import allocation_audit
from .certification_study import certification_study
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
    allocation = sub.add_parser("allocation-audit", help="Replay certification evidence and trace shared subdivision work")
    allocation.add_argument("--study", default="results/audit-final/auxiliary-total-work/study.json")
    allocation.add_argument("--metadata", help="Input metadata (defaults to metadata.json beside the study)")
    allocation.add_argument("--output", default="results/allocation-audit")
    for command, help_text, default in [
        ("run", "Run a single wall configuration", "configs/wall.json"),
        ("sweep", "Run a reproducible Cartesian experiment grid", "configs/baselines.json"),
        ("certify", "Analyze a planar held trajectory against a circle", "configs/planar.json"),
        ("learn", "Fit a small actuator model and test changed dynamics", "configs/learning.json"),
        ("benchmark", "Measure trajectory certificate precision and cost", "configs/certification.json"),
        ("certification-study", "Measure matched high-order property checks", "configs/certification-cost.json"),
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
        elif args.command == "allocation-audit":
            study_path = Path(args.study)
            metadata_path = Path(args.metadata) if args.metadata else study_path.with_name("metadata.json")
            source = read_json(metadata_path)
            if source["git_status"] != "" or not source["git_commit"] or not source["source_sha256"]:
                raise ValueError("Input study must identify a clean source snapshot")
            result = allocation_audit(source["configuration"], read_json(study_path))
            output.mkdir(parents=True, exist_ok=True)
            write_json(output/"audit.json", result)
            spec = {"study_file": str(study_path.resolve()), "study_sha256": hashlib.sha256(study_path.read_bytes()).hexdigest(),
                    "input_metadata_file": str(metadata_path.resolve()),
                    "input_metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
                    "input_source_commit": source["git_commit"], "input_source_sha256": source["source_sha256"]}
            write_json(output/"metadata.json", provenance(spec))
            columns = ["strategy", "tolerance_exact", "budget", "controls", "accepted", "rejected", "unknown",
                       "allocation_limited_controls", "unknown_at_full_per_polynomial_limits", "allocation_limited_unknown_queries",
                       "total_subdivisions", "subdivisions_after_sign_decisions"]
            with (output/"summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(result["groups"])
            lines = ["# Certification work allocation audit", "", result["scope"], "",
                     "| Strategy | Tolerance | Budget | Accepted | Rejected | Unknown | Allocation-limited unknown controls | Unknown at full per-polynomial limits | Splits beyond sign decisions |",
                     "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for g in result["groups"]:
                lines.append(f"| {g['strategy']} | {g['tolerance_exact']} | {g['budget']} | {g['accepted']} | {g['rejected']} | {g['unknown']} | "
                             f"{g['allocation_limited_controls']} | {g['unknown_at_full_per_polynomial_limits']} | {g['subdivisions_after_sign_decisions']} |")
            lines += ["", "Full per-polynomial allowances can spend more total work than the shared budget. They are an offline counterfactual.",
                      "Refinement after a sign decision can still be needed for the minimum-enclosure width request.",
                      "Unknown at the full allowance means unresolved at these limits, not mathematically undecidable.",
                      "These traces do not change controller decisions, certify a fallback, or bound elapsed computation time.",
                      "[Exact query traces](audit.json) · [Input hashes and replay source](metadata.json)", ""]
            (output/"report.md").write_text("\n".join(lines))
            print(f"Replayed {result['property_configurations']} property configurations and {result['replayed_queries']} polynomial queries.")
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
            elif args.command == "certification-study":
                result = certification_study(spec)
                output.mkdir(parents=True, exist_ok=True)
                write_json(output/"study.json", result)
                write_json(output/"metadata.json", provenance(spec))
                columns = ["strategy", "tolerance_exact", "budget", "queries", "accepted", "rejected", "unknown",
                           "accepted_safe_controls", "accepted_unsafe_controls", "rejected_unsafe_controls", "rejected_safe_controls",
                           "unknown_safe_controls", "unknown_unsafe_controls", "geometrically_unsafe_rejected",
                           "reference_safe_excluded", "reference_safe_unresolved", "accepted_reference_unknown",
                           "polynomial_checks", "geometric_implications_proved",
                           "total_subdivisions", "median_per_control_ns"]
                with (output/"summary.csv").open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(result["groups"])
                lines = ["# tick-trap matched high-order certification cost", "", result["scope"], "",
                         "| Strategy | Width tolerance | Splits per polynomial | Queries | Accepted | Rejected | Unknown | Reference-safe excluded | Reference-safe unresolved | Total splits | Median per-control time (µs) |",
                         "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
                for row in result["groups"]:
                    lines.append(f"| {row['strategy']} | {row['tolerance_exact']} | {row['budget']} | {row['queries']} | "
                                 f"{row['accepted']} | {row['rejected']} | {row['unknown']} | {row['reference_safe_excluded']} | "
                                 f"{row['reference_safe_unresolved']} | {row['total_subdivisions']} | {row['median_per_control_ns']/1000:.1f} |")
                if result["decision_comparisons"]:
                    lines += ["", "| Width tolerance | Budget | Dual sign decision | Auxiliary-only decision | Controls |",
                              "| --- | ---: | --- | --- | ---: |"]
                    for pair in result["decision_comparisons"]:
                        for row in pair["transitions"]:
                            lines.append(f"| {pair['tolerance_exact']} | {pair['budget']} | {row['dual_sign']} | {row['auxiliary_sign']} | {row['controls']} |")
                lines += ["", "| Strategy | Tolerance | Budget | Independently safe accepted | Unsafe h or psi rejected | Safe excluded | Safe unknown | Unsafe unknown |",
                          "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
                for row in result["groups"]:
                    lines.append(f"| {row['strategy']} | {row['tolerance_exact']} | {row['budget']} | {row['accepted_safe_controls']} | "
                                 f"{row['rejected_unsafe_controls']} | {row['rejected_safe_controls']} | {row['unknown_safe_controls']} | {row['unknown_unsafe_controls']} |")
                lines += ["", "| Baseline / candidate | Tolerance | Budget | Paired time ratio p10 | Median | p90 |",
                          "| --- | --- | ---: | ---: | ---: | ---: |"]
                for pair in result["paired_comparisons"]:
                    d = pair["paired_median_time_ratio"]
                    lines.append(f"| {pair['baseline']} / {pair['candidate']} | {pair['tolerance_exact']} | {pair['budget']} | {d['p10']:.3f} | {d['median']:.3f} | {d['p90']:.3f} |")
                lines += ["", "All strategies target continuous h and psi safety at the same declared controls.",
                          "auxiliary_sign certifies psi and derives h by linear comparison; it reports no numerical geometric minimum.",
                          "SACBF rejection is a failed sufficient condition; polynomial rejection has a negative witness.",
                          "Initial-domain exclusions are not counted as rejections. Unknown reference signs remain unknown.",
                          "Minimum and sign queries use identical tolerances/budgets; sign stopping need not attain the minimum width.",
                          f"Subdivision budget scope: {result['budget_scope']}. Native SACBF has no subdivisions; its repeated measurements are reused across tolerance/budget comparisons.",
                          "Independent exact algebraic signs distinguish safe/unsafe h-and-psi paths; unsafe psi alone does not mean collision.",
                          "Online unknowns remain unknown even if the independent offline reference resolves their signs.",
                          "Paired ratios divide the baseline per-control median by the candidate median; full repeat distributions and query order are saved.",
                          "These are descriptive distributions on this finite set, not confidence intervals or hard deadline bounds.",
                          f"{result['repeats']} seeded, interleaved repeats per setting and control.",
                          "[Exact evidence, reference audit and all timings](study.json).", ""]
                (output/"report.md").write_text("\n".join(lines))
                print(f"{result['applicable_cases']} applicable states; {len(result['measurements'])} matched property configurations.")
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
