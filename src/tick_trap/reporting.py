"""Portable experiment artifacts with source, configuration and timing provenance."""

import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import get_clock_info

from . import __version__


def read_json(path):
    # Preserve a JSON decimal's intended value instead of first rounding to float.
    return json.loads(Path(path).read_text(), parse_float=str,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant {value}")))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def provenance(spec):
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for source in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(source.name.encode()+b"\0"+source.read_bytes()+b"\0")
    prefix = ["git", "-C", str(root)]
    if (root/".tick-trap-git").is_dir():
        prefix += [f"--git-dir={root/'.tick-trap-git'}", f"--work-tree={root}"]
    def git(*args):
        try:
            result = subprocess.run(prefix+list(args), capture_output=True, text=True, timeout=3)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    clock = get_clock_info("perf_counter")
    return {"schema_version": 1, "project": "tick-trap", "version": __version__,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
            "dependencies": "Python standard library only", "argv": sys.argv,
            "source_sha256": digest.hexdigest(), "git_commit": git("rev-parse", "HEAD"),
            "git_status": git("status", "--porcelain"),
            "configuration_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
            "configuration": spec,
            "clock": {"implementation": clock.implementation, "resolution_seconds": clock.resolution,
                      "monotonic": clock.monotonic},
            "arithmetic": "exact rational inputs and dynamics; floats are display/learning estimates",
            "safety_boundary": "nonnegative clearance; contact at zero is permitted",
            "timing_scope": "empirical controller runtime; offline certification measured separately"}


def write_runs(output, runs, spec):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/"metadata.json", provenance(spec))
    write_json(output/"runs.json", runs)
    columns = ["run", "method", "d", "v", "duration", "seed", "plant_gain", "plant_bias",
               "model_gain", "model_bias", "measurement_d", "measurement_v", "delay", "termination",
               "initial_viable", "initial_controller_domain", "assumption_violations", "executed_steps",
               "completed_safe_horizon", "sampled_safe_observed", "collision_observed", "minimum_clearance",
               "intervention_l1", "solve_us_median", "oracle_us_median", "deadline_misses"]
    with (output/"summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index, run in enumerate(runs):
            row = {k: run["config"][k] for k in columns if k in run["config"]}
            row.update({k: run[k] for k in columns if k in run})
            solve = [r["solve_ns"]/1000 for r in run["records"]]
            oracle = [r["certification_ns"]/1000 for r in run["records"] if "certification_ns" in r]
            row.update({"run": index, "assumption_violations": ";".join(run["assumption_violations"]),
                        "solve_us_median": median(solve) if solve else "",
                        "oracle_us_median": median(oracle) if oracle else ""})
            writer.writerow(row)
    groups = defaultdict(list)
    for run in runs:
        groups[(run["config"]["method"], run["initial_viable"],
                ", ".join(run["assumption_violations"]) or "nominal model")].append(run)
    lines = ["# tick-trap experiment", "",
             "Counts describe these configurations only. A stopped run is not a safe completed horizon.", "",
             "| Method | Initially viable* | Assumptions | Runs | Safe complete | Collision | Infeasible | Outside domain | Deadline misses |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for (method, viable, assumptions), group in sorted(groups.items()):
        lines.append(f"| {method} | {viable} | {assumptions} | {len(group)} | "
                     f"{sum(r['completed_safe_horizon'] for r in group)} | "
                     f"{sum(r['collision_observed'] for r in group)} | "
                     f"{sum(r['termination']=='infeasible' for r in group)} | "
                     f"{sum(r['termination']=='outside_domain' for r in group)} | "
                     f"{sum(r['deadline_misses'] for r in group)} |")
    lines += ["", "*Viability uses the ideal no-delay wall formula with true braking authority.", "",
              "Different update periods with a fixed number of steps have different physical horizons.",
              "A model match does not give endpoint-only or emulated continuous filters a hold guarantee.",
              "Timing measurements are empirical; fixed simulated delay is configured independently.",
              "The oracle is offline; its time is excluded from controller deadline measurements.", "",
              "- [Full records](runs.json)", "- [Per-run metrics](summary.csv)",
              "- [Configuration and software provenance](metadata.json)", ""]
    (output/"report.md").write_text("\n".join(lines))


def counterexample_svg():
    """Standalone scientific illustration of an analytical curve (no raster asset)."""
    def x(t):
        return 90+620*t/0.2
    def y(d):
        return 250-3400*d
    path = " ".join(f"{'M' if i == 0 else 'L'} {x(i/1000):.3f},{y(.04-i/1000+5*(i/1000)**2):.3f}"
                    for i in range(201))
    ticks = "".join(f'<text x="{x(t)}" y="319" text-anchor="middle">{int(t*1000)}</text>'
                    for t in [0, .05, .1, .15, .2])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="385" viewBox="0 0 800 385" role="img" aria-labelledby="title desc">
<title id="title">The tick trap: safe samples, unsafe trajectory</title>
<desc id="desc">Clearance is 4 centimetres at 0 and 200 milliseconds, but minus 1 centimetre at 100 milliseconds. The initial state is not viable with maximum braking of 10 metres per second squared.</desc>
<rect width="800" height="385" fill="#faf9f6"/>
<g font-family="sans-serif" fill="#24313a" font-size="14">
<text x="90" y="35" font-size="23" font-weight="bold">tick-trap / the collision between updates</text>
<text x="90" y="61">Exact clearance: d(t) = 0.04 − t + 5t²</text>
<rect x="90" y="250" width="620" height="42" fill="#fde4df"/>
<path d="M90 90 V295 H720 M90 250 H720" fill="none" stroke="#9ca6aa"/>
<path d="M90 {y(.04)} H710" stroke="#809c91" stroke-dasharray="6 5" fill="none"/>
<path d="{path}" stroke="#b93e2d" stroke-width="3" fill="none"/>
<circle cx="90" cy="{y(.04)}" r="5" fill="#24745b"/>
<circle cx="710" cy="{y(.04)}" r="5" fill="#24745b"/>
<circle cx="400" cy="{y(-.01)}" r="5" fill="#b93e2d"/>
<text x="78" y="{y(.04)+5}" text-anchor="end">4 cm</text>
<text x="78" y="255" text-anchor="end">0</text>
<text x="78" y="289" text-anchor="end">−1 cm</text>
<text x="405" y="273" fill="#b93e2d">collision</text>
{ticks}<text x="400" y="344" text-anchor="middle">Time (ms)</text>
<text x="90" y="372" font-size="12">Free-motion prediction. Boundary crossings: 55.3 ms and 144.7 ms. Initial state is nonviable.</text>
</g></svg>'''
