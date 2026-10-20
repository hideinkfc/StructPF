"""Join label-hidden task/attempt reviews for the matched revision pilot."""

from __future__ import annotations

import argparse
import html
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_student_probe as student_report  # noqa: E402
from scripts import run_pf_attempt_revision as runner  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402

TASK_OPTIONS = {
    "mathematics": {"supported", "invalid", "unknown"},
    "target": {"preserved", "narrowed", "lost", "unknown"},
    "accessible_start": {"yes", "no", "unknown"},
    "disclosure": {"none", "method", "conclusion", "both", "unknown"},
    "consequential_choice": {"yes", "no", "unknown"},
    "input_clarity": {"yes", "no", "unknown"},
}
METHODS = {
    "whole_journey_rate",
    "unweighted_stage_rates",
    "elapsed_time_comparison",
    "construct_journey_or_schedule",
    "other_rate_method",
    "arithmetic_mean",
    "range",
    "concentration",
    "absolute_departures",
    "squared_departures",
    "maximum_departure",
    "pairwise_departures",
    "other_measure",
    "whole_block_search",
    "greedy_claims_and_repairs",
    "equal_fraction_all_blocks",
    "divider_chooser_extension",
    "other_allocation",
    "unknown",
}


def qualified(row: dict) -> bool:
    for field, allowed in TASK_OPTIONS.items():
        if row[field] not in allowed:
            raise ValueError(f"Unknown task rating: {field}")
    return (
        row["mathematics"] == "supported"
        and row["target"] == "preserved"
        and row["accessible_start"] == "yes"
        and row["disclosure"] == "none"
        and row["consequential_choice"] == "yes"
    )


def prepare_attempt_review(output: Path) -> dict:
    manifest, records = student_report.load_results(output / "attempts")
    by_task = {}
    for request in manifest["requests"]:
        if request["phase"] == "fresh":
            by_task.setdefault(request["task_id"], []).append(request)
    task_key = json.loads((output / "task_review_key.json").read_text())
    config = json.loads(runner.CONFIG.read_text())
    families = {spec["id"]: spec["family"] for spec in config["cases"]}
    panels, key = {}, {}
    for label, spec in task_key.items():
        requests = by_task.get(spec["task_id"], [])
        if len(requests) != 12:
            raise ValueError("Every available version needs twelve independent attempts")
        random.Random(20261013).shuffle(requests)
        entries, entry_key = {}, {}
        task_text = json.loads(requests[0]["prompt"]["user"])["student_task"]
        for number, request in enumerate(requests, 1):
            if json.loads(request["prompt"]["user"])["student_task"] != task_text:
                raise ValueError("Attempt panel mixes different student tasks")
            record = records[request["id"]]
            attempt_id = f"{label}_a{number:02d}"
            entries[attempt_id] = {
                "attempt": record["attempt"],
                "unparsed_raw_text": record["raw_text"] if record["attempt"] is None else None,
                "execution_status": record["status"],
            }
            entry_key[attempt_id] = request["id"]
        panels[label] = {"student_task": task_text, "attempts": entries}
        key[label] = {"task_id": spec["task_id"], "attempts": entry_key}
    save = runner.save
    save(output / "attempt_review_key.json", key)
    for family in sorted(set(families.values())):
        subset = {
            label: panel
            for label, panel in panels.items()
            if families[task_key[label]["case_id"]] == family
        }
        save(output / f"attempt_packet_{family}.json", subset)
    return panels


def validate_attempts(coding: dict, panels: dict) -> dict:
    expected = {
        attempt_id: entry
        for panel in panels.values()
        for attempt_id, entry in panel["attempts"].items()
    }
    if set(coding["attempts"]) != set(expected):
        raise ValueError("Attempt coding does not cover every fresh response")
    for label, row in coding["attempts"].items():
        if not isinstance(row["approaches"], list) or not row["approaches"]:
            raise ValueError("Attempt coding requires a nonempty approach list")
        if set(row["approaches"]) - METHODS:
            raise ValueError("Unknown coarse mathematical approach")
        for flag in ("initial_access", "recognised_limit", "unsupported_assumption"):
            if row[flag] not in {"yes", "no", "unknown"}:
                raise ValueError(f"Unknown attempt outcome: {flag}")
        if row["mathematics"] not in {"supported", "invalid", "unknown"}:
            raise ValueError("Unknown attempt mathematics classification")
        if row["timing_interpretation"] not in {
            "duration",
            "cumulative",
            "ambiguous",
            "not_applicable",
            "unknown",
        }:
            raise ValueError("Unknown timing interpretation")
        entry = expected[label]
        text = (
            entry["attempt"]["written_work"] + "\n" + entry["attempt"]["answer"]
            if entry["attempt"]
            else entry["unparsed_raw_text"] or ""
        )
        if not isinstance(row["evidence"], list) or not row["evidence"]:
            raise ValueError("Attempt judgment requires source-quoted evidence")
        for quote in row["evidence"]:
            if not isinstance(quote, str) or not quote.strip() or quote not in text:
                raise ValueError(f"Attempt quotation does not match source: {label}")
    return coding


def summarize(output: Path) -> dict:
    config = json.loads(runner.CONFIG.read_text())
    ratings = json.loads((output / "task_ratings.json").read_text())
    key = json.loads((output / "task_review_key.json").read_text())
    if set(ratings["tasks"]) != set(key):
        raise ValueError("Task ratings do not cover all eighteen versions")
    attempt_key = json.loads((output / "attempt_review_key.json").read_text())
    manifest, _ = student_report.load_results(output / "attempts")
    requests = {row["id"]: row for row in manifest["requests"]}
    coding = {}
    for family in {spec["family"] for spec in config["cases"]}:
        panels = json.loads((output / f"attempt_packet_{family}.json").read_text())
        family_coding = validate_attempts(
            json.loads((output / f"attempt_coding_{family}.json").read_text()),
            panels,
        )
        coding.update(family_coding["attempts"])
    arms = {arm: Counter() for arm in config["arms"]}
    cases = {}
    for label, spec in key.items():
        row = ratings["tasks"][label]
        qualifies = qualified(row)
        stats = arms[spec["arm"]]
        stats["tasks"] += 1
        stats["supported_undisclosed_choice"] += int(qualifies)
        for field in TASK_OPTIONS:
            stats[f"{field}/{row[field]}"] += 1
        learner, solver = Counter(), Counter()
        by_profile = {}
        for attempt_label, request_id in attempt_key[label]["attempts"].items():
            result = coding[attempt_label]
            profile = requests[request_id]["profile_id"]
            bucket = solver if profile == "ordinary_solver" else learner
            profile_counts = by_profile.setdefault(profile, Counter())
            for counts in (bucket, profile_counts):
                counts["attempted"] += 1
                counts[f"mathematics/{result['mathematics']}"] += 1
                counts[f"recognised_limit/{result['recognised_limit']}"] += 1
                counts[f"timing/{result['timing_interpretation']}"] += 1
                counts[f"unsupported_assumption/{result['unsupported_assumption']}"] += 1
                for method in set(result["approaches"]):
                    counts[f"method/{method}"] += 1
        cases.setdefault(spec["case_id"], {})[spec["arm"]] = {
            "label": label,
            "task_review": row,
            "qualified": qualifies,
            "learner_attempts": dict(learner),
            "solver_attempts": dict(solver),
            "by_profile": {name: dict(value) for name, value in by_profile.items()},
        }
    direct, informed = arms["ordinary_revision"], arms["attempt_revision"]
    margin = informed["supported_undisclosed_choice"] - direct["supported_undisclosed_choice"]
    meets = (
        margin >= 2
        and informed["mathematics/supported"] >= direct["mathematics/supported"]
        and informed["accessible_start/yes"] >= direct["accessible_start/yes"]
    )
    usage = {}
    for arm in config["arms"][1:]:
        totals = Counter()
        for path in (output / "fresh").glob(f"*/{arm}/model_calls.jsonl"):
            stats = benchmark._trace_stats(path)
            if stats["calls"] != 1 or stats["finished"] != 1 or stats["malformed_lines"]:
                raise ValueError("Revision trace has missing or extra requests")
            totals["calls"] += 1
            if stats["usage"]:
                totals.update(stats["usage"])
        usage[arm] = dict(totals)
    summary = {
        "question": config["question"],
        "arms": {name: dict(value) for name, value in arms.items()},
        "cases": cases,
        "task_review_provenance": ratings["provenance"],
        "attempt_coding_provenance": "Three label-hidden assistant readers, one per family.",
        "attempt_execution": student_report.summarize(output / "attempts")["phases"],
        "fresh_revision_usage": usage,
        "predefined_gain_margin": margin,
        "meets_predefined_rule": meets,
        "decision": (
            "Descriptive advantage meets exploratory continuation rule; not learner validation."
            if meets
            else "No promotion: predefined advantage over ordinary revision not established."
        ),
        "limits": config["limits"],
        "global_generator_changed": False,
    }
    verification_path = output / "task_verification.json"
    if verification_path.exists():
        summary["task_verification"] = json.loads(verification_path.read_text())
    runner.save(output / "summary.json", summary)
    render(output, summary)
    return summary


def render(output: Path, summary: dict) -> None:
    sections = []
    task_packet = json.loads((output / "task_review_packet.json").read_text())
    for case_id, arms in summary["cases"].items():
        cards = []
        for arm in ("original", "ordinary_revision", "attempt_revision"):
            review = arms[arm]
            task = task_packet[review["label"]]["student_task"]
            title = {
                "original": "Original",
                "ordinary_revision": "Ordinary revision",
                "attempt_revision": "Attempt-informed revision",
            }[arm]
            content = (
                "<article><h3>"
                + title
                + "</h3><h4>"
                + html.escape(task["title"])
                + "</h4><pre>"
                + html.escape(task["body"])
                + "</pre><b>Challenge</b><pre>"
                + html.escape(task["question"])
                + "</pre><hr><p><b>Task review:</b> "
                + html.escape(review["task_review"]["rationale"])
                + "</p>"
                + "<p><b>Learner methods:</b> "
                + html.escape(
                    ", ".join(
                        f"{key.removeprefix('method/')} ({value}/8)"
                        for key, value in review["learner_attempts"].items()
                        if key.startswith("method/")
                    )
                )
                + "</p></article>"
            )
            cards.append(content)
        sections.append(
            "<section><h2>"
            + html.escape(case_id)
            + "</h2><div class='row'>"
            + "".join(cards)
            + "</div></section>"
        )
    rows = []
    for metric, label in (
        ("mathematics/supported", "Mathematics supported"),
        ("accessible_start/yes", "Accessible start"),
        ("disclosure/none", "Central discovery not supplied"),
        ("consequential_choice/yes", "Consequential mathematical choice"),
        ("input_clarity/yes", "Unambiguous required inputs"),
        ("supported_undisclosed_choice", "All predefined design requirements"),
    ):
        rows.append(
            "<tr><td>"
            + label
            + "</td>"
            + "".join(
                f"<td>{summary['arms'][arm].get(metric, 0)}/6</td>"
                for arm in ("original", "ordinary_revision", "attempt_revision")
            )
            + "</tr>"
        )
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Does student-attempt feedback improve PF tasks?</title><style>"
        "body{font:16px/1.6 system-ui;margin:28px;background:#f5f7fa;color:#213247}"
        ".row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}"
        "article{padding:20px;background:white;border:1px solid #cbd4de;border-radius:8px}"
        "pre{white-space:pre-wrap;font:inherit}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #cbd4de;padding:10px;text-align:left}"
        "@media(max-width:900px){.row{grid-template-columns:1fr}}</style>"
        "<h1>Does feedback from simulated attempts improve PF exercises?</h1>"
        "<p>Six paired exercises. Same revision instructions/model/call cap; only "
        "one arm receives previous learner work. Original versions are retained. "
        "Task review hides labels and precedes fresh-attempt outcomes.</p><p><b>Decision:</b> "
        + html.escape(summary["decision"])
        + "</p>"
        "<h2>Answer to the research question</h2>"
        "<p>This pilot does not establish that simulated-attempt feedback improves "
        "PF design more than a strong ordinary revision. The informed arm added "
        "an unresolved universal fair-division demand and loosened another task's "
        "target. Both speed revisions clarified timing, but fresh original attempts "
        "already read it correctly, so there was no observed extra clarity gain.</p>"
        "<p>Fresh speed work followed the same mathematical routes across arms. "
        "Consistency work remained varied. Fair-division attempts changed, but "
        "more complicated procedures were not consistently correct. These are "
        "separate findings, not a single PF or learning score.</p>"
        "<table><tr><th>Separate outcome</th><th>Original</th>"
        "<th>Ordinary revision</th><th>Attempt-informed revision</th></tr>"
        + "".join(rows)
        + "</table>"
        "<p>These are assistant-reviewed designs and written LLM attempts, not real "
        "student behavior or learning. One revision per arm; additional input "
        "tokens and feedback-acquisition costs are not equal. Unknown never means "
        "valid. Each learner-method count is out of eight learner-role attempts; "
        "ordinary solver controls are counted separately.</p>"
        "<p><a href='summary.json'>All outcomes and request costs</a> &middot; "
        "<a href='task_ratings.json'>Label-hidden task ratings</a> &middot; "
        "<a href='attempts/attempts.html'>All written attempts</a></p>"
        + "".join(sections)
        + "</html>"
    )
    (output / "comparison.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-attempt-review", action="store_true")
    args = parser.parse_args()
    if args.prepare_attempt_review:
        result = prepare_attempt_review(args.output)
        print(f"Prepared {len(result)} neutral task panels")
    else:
        result = summarize(args.output)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "arms",
                        "predefined_gain_margin",
                        "meets_predefined_rule",
                        "decision",
                        "fresh_revision_usage",
                    )
                },
                indent=2,
            )
        )
