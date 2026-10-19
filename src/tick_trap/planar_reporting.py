"""Planar reports and exact quadratic-path SVG exports."""

import csv
from collections import Counter
from html import escape
from pathlib import Path
from statistics import median

from .numbers import q
from .reporting import provenance, write_json


def trajectory_svg(run):
    config = run["config"]
    display_vector = lambda values: tuple(float(q(x)) for x in values)
    points = [display_vector(config["p"]), display_vector(config["goal"])]
    segments = []
    dt = float(q(config["duration"]))
    for record in run["records"]:
        if "action" not in record:
            continue
        start, end = record["state"]["p"], record["end_state"]["p"]
        velocity, action = record["state"]["v"], record["action"]
        control = tuple(p+v*dt/2 for p, v in zip(start, velocity))
        points.extend([start, end, control])
        segments.append((start, control, end, record["continuous_status"]))
    for obstacle in config["obstacles"]:
        center, radius = display_vector(obstacle["center"]), float(q(obstacle["radius"]))
        points.extend([(center[0]-radius, center[1]-radius), (center[0]+radius, center[1]+radius)])
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    span = max(xmax-xmin, ymax-ymin, 1)*1.15
    cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
    scale = 480/span
    transform = lambda p: (320+(p[0]-cx)*scale, 335-(p[1]-cy)*scale)
    pair = lambda p: ",".join(f"{x:.6f}" for x in transform(p))
    title = f"tick-trap / {config['method']}"
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="640" height="660" viewBox="0 0 640 660" role="img" aria-labelledby="title desc">',
             f'<title id="title">{escape(title)}</title>',
             '<desc id="desc">Quadratic held-input paths, circular obstacles, sampled states and target. Curve colors reflect validated offline safety checks. No contact dynamics are simulated.</desc>',
             '<rect width="640" height="660" fill="#faf9f6"/>',
             '<g font-family="sans-serif" fill="#24313a" font-size="13">',
             f'<text x="40" y="35" font-size="21" font-weight="bold">{escape(title)}</text>',
             f'<text x="40" y="60">Outcome: {escape(run["termination"])} / initial viability: {run["initial_viability"]}</text>']
    for obstacle in config["obstacles"]:
        center = display_vector(obstacle["center"])
        x, y = transform(center)
        radius = float(q(obstacle["radius"]))*scale
        lines.append(f'<circle cx="{x:.6f}" cy="{y:.6f}" r="{radius:.6f}" fill="#f3d8d1" stroke="#b93e2d"/>')
    colors = {"safe": "#24745b", "unsafe": "#b93e2d", "unknown": "#a16a12"}
    for start, control, end, status in segments:
        lines.append(f'<path d="M {pair(start)} Q {pair(control)} {pair(end)}" fill="none" stroke="{colors[status]}" stroke-width="2.5"/>')
        x, y = transform(start)
        lines.append(f'<circle cx="{x:.6f}" cy="{y:.6f}" r="2" fill="#24313a"/>')
    initial = display_vector(config["p"])
    gx, gy = transform(display_vector(config["goal"]))
    sx, sy = transform(initial)
    lines += [f'<circle cx="{sx:.6f}" cy="{sy:.6f}" r="5" fill="#345c88"/>',
              f'<path d="M {gx-6:.6f},{gy:.6f} H {gx+6:.6f} M {gx:.6f},{gy-6:.6f} V {gy+6:.6f}" stroke="#345c88" stroke-width="2"/>',
              '<text x="40" y="605">Green: certified path. Red: collision witness. Amber: unresolved.</text>',
              '<text x="40" y="625">Dots: control updates. Cross: goal. Equal spatial scale; metres.</text>',
              '<text x="40" y="645">A failed decision ends the simulation; it does not physically stop the robot.</text>',
              '</g></svg>']
    return "\n".join(lines)


def write_planar_runs(output, runs, spec):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/"trajectories").mkdir(exist_ok=True)
    write_json(output/"metadata.json", provenance(spec))
    write_json(output/"runs.json", runs)
    columns = ["run", "method", "duration", "horizon", "p", "initial_viability", "initial_hocbf_domain", "termination",
               "executed_steps", "completed_safe_horizon", "sampled_safe_observed", "observed_continuous_status",
               "collision_observed", "goal_reached_at_end", "minimum_clearance_estimate", "minimum_barrier_lower_exact",
               "minimum_barrier_upper_exact", "solve_us_median", "oracle_us_median", "deadline_misses"]
    with (output/"summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index, run in enumerate(runs):
            row = {k: run[k] for k in columns if k in run}
            row.update({k: run["config"][k] for k in columns if k in run["config"]})
            solve = [r["solve_ns"]/1000 for r in run["records"]]
            oracle = [r["certification_ns"]/1000 for r in run["records"] if "certification_ns" in r]
            row.update({"run": index, "solve_us_median": median(solve) if solve else "",
                        "oracle_us_median": median(oracle) if oracle else ""})
            writer.writerow(row)
            (output/"trajectories"/f"run-{index:03d}.svg").write_text(trajectory_svg(run))
    lines = ["# tick-trap planar experiment", "",
             "Safety, initial-set membership, sufficient viability and task progress are separate results.",
             "Stopping a simulation at a failed decision is not an emergency braking maneuver.", "",
             "| Method | Runs | Safe full horizon | Collision | QP infeasible | Search exhausted | Uncertified | Other stops |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for method in sorted({r["config"]["method"] for r in runs}):
        group = [r for r in runs if r["config"]["method"] == method]
        counts = Counter(r["termination"] for r in group)
        other = sum(n for status, n in counts.items() if status not in {"horizon", "collision_interval", "infeasible", "search_exhausted", "uncertified"})
        lines.append(f"| {method} | {len(group)} | {sum(r['completed_safe_horizon'] for r in group)} | "
                     f"{counts['collision_interval']} | {counts['infeasible']} | {counts['search_exhausted']} | {counts['uncertified']} | {other} |")
    lines += ["", "| Run / trajectory | Method | Period (s) | Initial p | Initial viability | Outcome | At goal at end |",
              "| --- | --- | ---: | --- | --- | --- | --- |"]
    for index, run in enumerate(runs):
        config = run["config"]
        lines.append(f"| [{index}](trajectories/run-{index:03d}.svg) | {config['method']} | {config['duration']} | "
                     f"{config['p']} | {run['initial_viability']} | {run['termination']} | {run['goal_reached_at_end']} |")
    lines += ["", "`certified` initial viability means a particular admissible stopping plan was certified safe.",
              "`unknown` does not mean nonviable. The complete planar viability kernel is not computed.",
              "Finite candidate exhaustion does not prove continuous-input infeasibility.",
              "Endpoint and segment checks certify different properties from continuous-path checks.",
              "Controller timings include any online trajectory certificates; the offline oracle is measured separately.",
              "The stopping-plan diagnostics are offline and do not become fallback actions.", "",
              "- [Full exact records](runs.json)", "- [Per-run metrics](summary.csv)",
              "- [Configuration and source provenance](metadata.json)", ""]
    (output/"report.md").write_text("\n".join(lines))
