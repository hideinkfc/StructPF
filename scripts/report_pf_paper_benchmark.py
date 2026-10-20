"""Audit saved benchmark artifacts and render a compact, model-only comparison."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.pf_rubric import (  # noqa: E402
    judge_input,
    parse_rating,
    student_task_text,
)


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def audit_run(root: Path) -> dict:
    manifest = _read(root / "manifest.json")
    config = _read(root / "config.json")
    summary = _read(root / "summary.json")
    if manifest["status"] not in {
        "completed",
        "completed_with_failures",
        "completed_with_missing_ratings",
    }:
        raise ValueError(f"Run is not complete with intact provenance: {manifest['status']}")
    if manifest.get("source_integrity_unchanged") is not True:
        raise ValueError("Source-integrity verification did not pass")
    for relative, expected in manifest["source_hashes"].items():
        snapshot = root / manifest["source_snapshot_dir"] / relative
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen source snapshot differs: {relative}")
    expected_count = config["n_per_condition"]
    schedule = manifest["attempts"]
    if Counter(item["condition"] for item in schedule.values()) != Counter(
        {condition: expected_count for condition in config["conditions"]}
    ):
        raise ValueError("Scheduled condition counts differ from the frozen configuration")
    stages = defaultdict(lambda: {"started": 0, "finished": 0, "errors": 0, "seconds": 0.0})
    responses = Counter()
    request_models = Counter()
    items = []
    totals = defaultdict(list)
    trace_problems = []
    for identifier, scheduled in schedule.items():
        path = root / scheduled["path"]
        attempt = _read(path / "attempt.json")
        if attempt["status"] in {"pending", "started", "missing"}:
            raise ValueError(f"Unfinished attempt: {identifier}")
        if attempt["attempt_id"] != identifier or attempt["condition"] != scheduled["condition"]:
            raise ValueError(f"Attempt identity mismatch: {identifier}")
        task = attempt.get("task")
        text = student_task_text(task) if attempt["status"] == "ready" else None
        rating_path = path / "judgment.json"
        rating = _read(rating_path) if rating_path.is_file() else {}
        if rating.get("status") in {"scored", "insufficient_evidence"}:
            parsed = parse_rating(rating["raw_response"])
            if parsed["scores"] != rating["scores"]:
                raise ValueError(f"Saved rating differs from raw response: {identifier}")
            total = parsed["scores"]["TOTAL"]
            if total is not None:
                totals[scheduled["condition"]].append(total)
        judge_responses = 0
        for kind, trace in (
            ("generation", path / "model_trace.jsonl"),
            ("judge", path / "judge_trace.jsonl"),
        ):
            if not trace.is_file() and kind == "generation":
                trace = path / "pipeline" / "model_trace.jsonl"
            if not trace.is_file():
                continue
            started, finished = Counter(), Counter()
            for line_number, line in enumerate(trace.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    trace_problems.append(f"{identifier}/{kind}:{line_number}: malformed JSON")
                    continue
                stage = stages[f"{scheduled['condition']}/{event.get('stage', kind)}"]
                if event.get("event") == "model_call_started":
                    started[event["call_id"]] += 1
                    stage["started"] += 1
                    request_models[event["model"]] += 1
                    if kind == "judge" and event["user_prompt"] != judge_input(
                        text, config["learner_context"]
                    ):
                        raise ValueError(
                            f"Judge input is not the blinded fixed input: {identifier}"
                        )
                elif event.get("event") == "model_call_finished":
                    finished[event["call_id"]] += 1
                    stage["finished"] += 1
                    stage["seconds"] += event.get("elapsed_seconds", 0)
                    stage["errors"] += bool(event.get("error"))
                    if "usage" in event and event.get("model"):
                        responses[event["model"]] += 1
                    if kind == "judge" and not event.get("error"):
                        judge_responses += 1
            if started != finished or any(count != 1 for count in started.values()):
                trace_problems.append(f"{identifier}/{kind}: unmatched or duplicate call IDs")
        if judge_responses > 1:
            raise ValueError(f"More than one successful final rating response: {identifier}")
        fill = attempt.get("pipeline_result", {}).get("stages", {}).get("D2_D3", {}).get("fill")
        items.append(
            {
                "attempt_id": identifier,
                "condition": scheduled["condition"],
                "status": attempt["status"],
                "error": attempt.get("error") or attempt.get("pipeline_result", {}).get("error"),
                "judge_status": rating.get("status", "not_rated"),
                "total": (rating.get("scores") or {}).get("TOTAL"),
                "mathematical_concerns": (rating.get("rating") or {}).get("mathematical_concerns"),
                "deterministic_fill_accepted": fill.get("accepted")
                if isinstance(fill, dict)
                else None,
                "student_text_sha256": hashlib.sha256(text.encode()).hexdigest() if text else None,
            }
        )
    for condition, values in summary["conditions"].items():
        own = [item for item in items if item["condition"] == condition]
        counts = values["counts"]
        if counts["ready"] != sum(item["status"] == "ready" for item in own):
            raise ValueError(f"Ready denominator mismatch: {condition}")
        if counts["rated"] != len(totals[condition]):
            raise ValueError(f"Rated denominator mismatch: {condition}")
        if totals[condition]:
            mean = sum(totals[condition]) / len(totals[condition])
            if abs(values["scores"]["TOTAL"]["mean"] - mean) > 1e-9:
                raise ValueError(f"Mean mismatch: {condition}")
    return {
        "status": "audited",
        "source_integrity_unchanged": True,
        "request_models": dict(request_models),
        "response_models_when_available": dict(responses),
        "trace_problems": trace_problems,
        "stages": dict(stages),
        "attempts": items,
        "limitations": [
            "One Luna rating per ready task; not independent human validation.",
            "Scores are conditional on completion; missing scores are not zeros.",
            "Pipeline token usage and response-model metadata are unavailable.",
            "Pipeline checks and judge mathematical concerns are different evidence.",
            "No student outcomes were observed; this is not an exact paper replication.",
        ],
    }


def render_report(summary: dict, audit: dict) -> str:
    def number(value):
        return "unavailable" if value is None else f"{value:.2f}"

    rows, contrasts, costs, dimensions = [], [], [], []
    for condition, result in summary["conditions"].items():
        counts = result["counts"]
        total = result["scores"]["TOTAL"]
        rows.append(
            f"<tr><th>{condition}</th><td>{counts['ready']}/{counts['scheduled']}</td>"
            f"<td>{counts['blocked']}</td><td>{counts['failed'] + counts['interrupted']}</td>"
            f"<td>{counts['rated']}/{counts['ready']}</td>"
            f"<td>{number(total['mean'])}</td><td>{number(total['sd'])}</td></tr>"
        )
        dimensions.append(
            f"<tr><th>{condition}</th>"
            + "".join(
                f"<td>{number(result['scores'][key]['mean'])}</td>"
                for key in ("APK", "SSC", "AE", "MR", "OE")
            )
            + "</tr>"
        )
        diff = result.get("differences_vs_V1", {}).get("TOTAL")
        if diff:
            interval = diff["bootstrap_95ci"]
            ci = "unavailable" if interval is None else " to ".join(map(number, interval))
            contrasts.append(
                f"<tr><th>{condition} - V1</th><td>{number(diff['difference'])}</td>"
                f"<td>{ci}</td><td>{diff['n']} / {diff['baseline_n']}</td></tr>"
            )
        calls = result["generation"]["calls"]
        costs.append(
            f"<tr><th>{condition}</th><td>{calls['calls']}</td>"
            f"<td>{calls['calls_with_usage']}/{calls['finished']}</td>"
            f"<td>{number(result['generation']['elapsed_seconds'] / 60)}</td></tr>"
        )
    concerns = sum(bool(item["mathematical_concerns"]) for item in audit["attempts"])
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>PF benchmark: Luna comparison</title>
<style>body{{font:17px system-ui;max-width:1050px;margin:40px auto;padding:0 24px;
color:#172b40;background:#fafbfc}}table{{border-collapse:collapse;width:100%;background:white}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #dce2e8}}th{{font-weight:600}}
small,p{{line-height:1.5}}.note{{background:#eaf1f7;padding:16px;border-radius:8px}}</style>
<h1>Which method produces stronger tasks?</h1>
<p class="note">Measured evidence: generated tasks and Luna's ratings, not student learning.
Thirty scheduled attempts per method; no replacements for failures.</p>
<h2>Completion and model ratings</h2>
<table><tr><th>Method</th><th>Ready / attempted</th><th>Blocked</th><th>Failed</th>
<th>Rated / ready</th><th>Mean / 15</th><th>SD</th></tr>{"".join(rows)}</table>
<p>Higher scores mean stronger Luna rubric ratings (5-15). SD describes score spread.
Means include only complete ratings of ready tasks, not blocked or failed attempts.</p>
<h2>What the judge rewarded</h2><table><tr><th>Method</th><th>Prior knowledge</th>
<th>Difficulty fit</th><th>Engagement</th><th>Approach variety</th><th>Openness</th></tr>
{"".join(dimensions)}</table>
<p>Each dimension runs from 1 (low) to 3 (high). These are model judgments of the text,
not observed student engagement or approaches.</p>
<h2>Difference from direct generation without misconceptions</h2>
<table><tr><th>Comparison</th><th>Mean difference</th><th>95% interval</th>
<th>Rated tasks</th></tr>{"".join(contrasts)}</table>
<p>PIPELINE - V1 is primary; the others are secondary. Positive differences favor the named
method. Intervals use independent-group resampling (2,000 resamples), not human-rater
uncertainty or the original paper's t-test.</p>
<h2>Generation cost</h2><table><tr><th>Method</th><th>API requests</th>
<th>Responses with token counts</th><th>Sum of attempt minutes</th></tr>{"".join(costs)}</table>
<p>Parallel work overlaps, so summed attempt minutes are not total elapsed runtime.
Pipeline token counts are unavailable, not zero.</p>
<p>{concerns} rated tasks have unverified model-reported mathematical concerns.
These are not confirmed errors; deterministic pipeline checks are recorded separately.</p>
<details><summary>Evidence limits and audit</summary>
<ul>{"".join(f"<li>{html.escape(item)}</li>" for item in audit["limitations"])}</ul>
<p>Trace problems: {len(audit["trace_problems"])}. Source hashes unchanged.</p></details>
<p><a href="summary.json">Full scores</a> &middot; <a href="audit.json">Attempt-level audit</a>
 &middot; <a href="manifest.json">Frozen run manifest</a></p></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    audit = audit_run(args.run)
    (args.run / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (args.run / "comparison.html").write_text(
        render_report(_read(args.run / "summary.json"), audit), encoding="utf-8"
    )
    print(json.dumps({"audit": audit["status"], "trace_problems": audit["trace_problems"]}))


if __name__ == "__main__":
    main()
