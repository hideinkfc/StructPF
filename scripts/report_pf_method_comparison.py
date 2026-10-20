"""Join anonymous PF reviews to their sources and report separate design outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_fresh_comparison as comparison  # noqa: E402

DIMENSIONS = {
    "mathematics_status": {"supported", "invalid", "unknown"},
    "target": {"preserved", "narrowed", "lost", "unknown"},
    "accessible_start": {"yes", "no", "unknown"},
    "disclosure": {"none", "method", "conclusion", "both", "unknown"},
    "consequential_choice": {"yes", "no", "unknown"},
}


def outcome_counts(tasks: dict) -> dict:
    counts = Counter(attempted=len(tasks))
    for task in tasks.values():
        for dimension, allowed in DIMENSIONS.items():
            value = task[dimension]
            if value not in allowed:
                raise ValueError(f"Unknown {dimension} rating: {value!r}")
            counts[f"{dimension}/{value}"] += 1
        qualifies = (
            task["mathematics_status"] == "supported"
            and task["target"] == "preserved"
            and task["accessible_start"] == "yes"
            and task["disclosure"] == "none"
            and task["consequential_choice"] == "yes"
        )
        counts["supported_undisclosed_choice"] += int(qualifies)
    return dict(counts)


def report(output: Path) -> dict:
    fresh = output / "fresh"
    expected = {}
    for path in sorted(fresh.glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        if manifest["status"] != "completed":
            raise ValueError(f"Comparison not completed: {path}")
        for item in manifest["attempts"]:
            source = f"{manifest['case_name']}/{item['number']:03d}/{item['method']}"
            expected[source] = json.loads((path.parent / item["path"]).read_text())
    if not expected:
        raise ValueError("No completed comparison found")
    tasks = {}
    numeric = {}
    for key_path in sorted(fresh.glob("review_key_part*.json")):
        suffix = key_path.stem.removeprefix("review_key_")
        key = json.loads(key_path.read_text())
        packet = json.loads((fresh / f"review_packet_{suffix}.json").read_text())
        ratings = json.loads((fresh / f"review_ratings_{suffix}.json").read_text())["tasks"]
        inputs = json.loads((fresh / f"numeric_inputs_{suffix}.json").read_text())
        if set(key) != set(packet) or set(key) != set(ratings) or set(key) != set(inputs):
            raise ValueError(f"Review/input coverage mismatch: {suffix}")
        for anonymous_id, source in key.items():
            if source not in expected or source in tasks:
                raise ValueError(f"Unexpected or repeated review: {source}")
            record = expected[source]
            task = (
                record.get("task")
                if source.endswith("/direct")
                else record.get("stages", {}).get("D2_D3", {}).get("task")
            )
            text = (
                {field: task.get(field) for field in ("title", "body", "question")}
                if isinstance(task, dict)
                else None
            )
            if packet[anonymous_id]["task"] != text:
                raise ValueError(f"Task changed after anonymous review: {source}")
            tasks[source] = {
                **ratings[anonymous_id],
                "review_batch": suffix,
                "anonymous_id": anonymous_id,
                "produced": comparison.task_is_produced(task),
            }
            numeric[source] = {**inputs[anonymous_id], "source": f"{source}/result.json"}
    if set(tasks) != set(expected):
        raise ValueError(f"Unreviewed attempts: {sorted(set(expected) - set(tasks))}")
    methods = {}
    families = {}
    for method in ("direct", "pipeline"):
        rows = {key: task for key, task in tasks.items() if key.endswith(f"/{method}")}
        counts = outcome_counts(rows)
        counts["produced"] = sum(task["produced"] for task in rows.values())
        calls = finished = errors = calls_with_usage = 0
        elapsed = 0.0
        usage = None
        for source in rows:
            trace_path = fresh / source / "model_calls.jsonl"
            if not trace_path.is_file():
                raise ValueError(f"Missing request trace: {source}")
            stats = comparison.benchmark._trace_stats(trace_path)
            if stats["malformed_lines"] or stats["calls"] != stats["finished"]:
                raise ValueError(f"Incomplete or malformed request trace: {source}")
            calls += stats["calls"]
            finished += stats["finished"]
            errors += stats["errors"]
            elapsed += stats["elapsed_seconds"]
            calls_with_usage += stats["calls_with_usage"]
            if stats["usage"] is not None:
                if usage is None:
                    usage = Counter()
                usage.update(stats["usage"])
        methods[method] = {
            **counts,
            "calls": calls,
            "finished_calls": finished,
            "api_errors": errors,
            "call_elapsed_seconds": round(elapsed, 3),
            "calls_with_usage_metadata": calls_with_usage,
            "recorded_usage": dict(usage) if usage is not None else None,
        }
        for family in comparison.CASES:
            families.setdefault(family, {})[method] = outcome_counts(
                {key: task for key, task in rows.items() if key.startswith(f"{family}/")}
            )
    direct = methods["direct"]["supported_undisclosed_choice"]
    pipeline = methods["pipeline"]["supported_undisclosed_choice"]
    conclusion = (
        f"Direct produced {methods['direct']['produced']}/{methods['direct']['attempted']} "
        f"drafts; pipeline produced "
        f"{methods['pipeline']['produced']}/{methods['pipeline']['attempted']}. "
        f"Supported, target-preserving, accessible, undisclosed tasks with consequential "
        f"choices: direct {direct}, pipeline {pipeline}. "
        + (
            "The pipeline has a descriptive advantage on this count, not a general quality claim."
            if pipeline > direct
            else "No general pipeline advantage is established."
        )
        + " Speed remains fixed calculation; consistency supports measure invention; "
        "fair division varies in feasibility and need for new reasoning. "
        "Assistant review and exact checks are not student or independent human evidence."
    )
    assessment = {
        "assessment_type": "Anonymous-label assistant task-text review with shared exact checks",
        "conclusion": conclusion,
        "methods": methods,
        "families": families,
        "tasks": tasks,
        "limitations": json.loads((output / "protocol.json").read_text())["limitations"],
    }
    comparison.save(fresh / "assessment.json", assessment)
    comparison.save(fresh / "numeric_inputs.json", numeric)
    comparison.verify_math(fresh)
    comparison.render(fresh)
    return assessment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.output)
    print(json.dumps({key: result[key] for key in ("conclusion", "methods", "families")}, indent=2))
