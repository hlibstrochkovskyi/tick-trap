"""Check saved benchmark layout and statistics, not the authenticity of a clock."""

import json
from random import Random
from statistics import median

from .certification_study import PARAMETER_FREE, STRATEGIES, distribution, paired_comparisons
from .numbers import positive


def verify_timing_evidence(spec, study):
    """Reconstruct the seeded schedule and aggregates from raw elapsed samples.

    Pair with allocation_audit to replay the mathematical decisions. This check
    cannot establish that saved elapsed values came from a trustworthy clock,
    or turn finite measurements into deadline guarantees.
    """
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def same(a, b):
        return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)

    strategies = spec.get("strategies", list(STRATEGIES[:3]))
    tolerances = [positive(t) for t in spec.get("tolerances", ["1e-10"])]
    budgets, repeats = spec.get("budgets", [256]), spec.get("repeats", 5)
    settings = ([(s, None, None) for s in strategies if s in PARAMETER_FREE] +
                [(s, str(t), b) for t in tolerances for b in budgets for s in strategies if s not in PARAMETER_FREE])
    indexed = {}
    for row in study["measurements"]:
        key = (row["case_index"], row["candidate_index"], row["strategy"], row["tolerance_exact"], row["budget"])
        require(key not in indexed, "Duplicate timed row")
        indexed[key] = row
        samples = row["all_predicate_ns"]
        require(isinstance(samples, list) and len(samples) == repeats and
                all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in samples), "Invalid elapsed samples")
        require(same(row["predicate_ns_median"], median(samples)), "Saved median disagrees with elapsed samples")
    rng, expected = Random(spec.get("seed", 20261019)), set()
    for case_index, case in enumerate(study["reference"]):
        if not case["hocbf_applicable"]:
            continue
        for candidate_index in range(case["candidate_count"]):
            positions = [[] for _ in settings]
            for _ in range(repeats):
                order = list(range(len(settings)))
                rng.shuffle(order)
                for position, index in enumerate(order):
                    positions[index].append(position)
            for index, setting in enumerate(settings):
                key = (case_index, candidate_index, *setting)
                expected.add(key)
                require(key in indexed and same(indexed[key]["sample_positions"], positions[index]),
                        "Missing timed row or incorrect seeded measurement order")
    require(set(indexed) == expected, "Unexpected timed row or excluded-domain measurement")
    groups = {}
    for group in study["groups"]:
        key = (group["strategy"], group["tolerance_exact"], group["budget"])
        require(key not in groups, "Duplicate timing group")
        groups[key] = group
    expected_groups = set()
    for setting in settings:
        rows = [r for k, r in indexed.items() if k[2:] == setting]
        if not rows:
            continue
        expected_groups.add(setting)
        require(setting in groups, "Missing timing group")
        group = groups[setting]
        counts = {"queries": len(rows),
                  "accepted": sum(r["result"]["status"] == "accepted" for r in rows),
                  "rejected": sum(r["result"]["status"] == "rejected" for r in rows),
                  "unknown": sum(r["result"]["status"] == "unknown" for r in rows),
                  "total_subdivisions": sum(r["result"]["subdivisions"] for r in rows),
                  "polynomial_checks": sum(len(r["result"].get("proofs", [])) for r in rows),
                  "median_per_control_ns": median(r["predicate_ns_median"] for r in rows),
                  "per_control_median_ns_distribution": distribution([r["predicate_ns_median"] for r in rows]),
                  "all_repeat_ns_distribution": distribution([t for r in rows for t in r["all_predicate_ns"]])}
        for label, decision in (("accepted", "accepted"), ("rejected", "rejected"), ("unknown", "unknown")):
            for truth in ("safe", "unsafe"):
                counts[f"{label}_{truth}_controls"] = sum(r["result"]["status"] == decision and
                                                         r["independent_reference_status"] == truth for r in rows)
        require(all(same(group[k], value) for k, value in counts.items()), "Group statistics disagree with timed rows")
    require(set(groups) == expected_groups, "Unexpected timing group")
    comparisons = paired_comparisons(study["measurements"], strategies, tolerances, budgets)
    require(same(study["paired_comparisons"], comparisons), "Paired transitions or timing distributions were changed")
    return {"status": "verified", "timed_rows": len(indexed), "elapsed_samples": len(indexed)*repeats,
            "groups": len(groups), "paired_settings": len(comparisons),
            "scope": "Seeded layout, raw-sample medians, decision counts and paired distributions; mathematical decisions require separate replay, and clock authenticity is not verified"}
