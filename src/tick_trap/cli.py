import argparse
import json
import sys
from pathlib import Path

from .dynamics import Circle, PlanarState, WallState
from .experiments import RunConfig, load_grid, run
from .oracle import circle_interval, wall_interval
from .reporting import counterexample_svg, provenance, read_json, write_json, write_runs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tick-trap", description="Continuous-time safety analysis for sampled robot control")
    sub = parser.add_subparsers(dest="command", required=True)
    example = sub.add_parser("counterexample", help="Reproduce the analytical hidden collision")
    example.add_argument("--output", default="results/counterexample")
    for command, help_text, default in [
        ("run", "Run a single wall configuration", "configs/wall.json"),
        ("sweep", "Run a reproducible Cartesian experiment grid", "configs/baselines.json"),
        ("certify", "Analyze a planar held trajectory against a circle", "configs/planar.json"),
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
        else:
            spec = read_json(args.config)
            if args.command == "certify":
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
