"""Empirical certificate precision/cost study on declared analytical trajectories."""

from statistics import median

from .dynamics import Circle, PlanarState
from .oracle import circle_interval


def benchmark(spec):
    if set(spec)-{"cases", "tolerances", "budgets", "repeats"}:
        raise ValueError("Unknown certification benchmark field")
    repeats = spec.get("repeats", 3)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    cases = spec.get("cases", [])
    tolerances = spec.get("tolerances", ["1e-10"])
    budgets = spec.get("budgets", [4096])
    if not all(isinstance(x, list) and x for x in (cases, tolerances, budgets)):
        raise ValueError("cases, tolerances and budgets must be nonempty lists")
    results = []
    for case in cases:
        if set(case)-{"name", "p", "v", "u", "center", "radius", "duration"}:
            raise ValueError("Unknown trajectory case field")
        for tolerance in tolerances:
            for budget in budgets:
                measurements = [circle_interval(PlanarState(case["p"], case["v"]), case["u"],
                                                Circle(case["center"], case["radius"]), case["duration"],
                                                tolerance, budget) for _ in range(repeats)]
                results.append({"case": case["name"], "tolerance": tolerance, "budget": budget,
                                "repeats": repeats, "result": measurements[0],
                                "certificate_ns_median": median(r["certification_ns"] for r in measurements),
                                "certificate_ns_max": max(r["certification_ns"] for r in measurements),
                                "estimate_ns_median": median(r["estimation_ns"] for r in measurements),
                                "all_certification_ns": [r["certification_ns"] for r in measurements]})
    return results
