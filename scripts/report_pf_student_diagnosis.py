"""Report checklist agreement and evidence-linked baseline PF diagnosis."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_student_probe as student_report  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from src.evaluation.pf_attempt_feedback import FINDINGS, retain_panel_review  # noqa: E402


def derive_reviews(review_path: Path) -> dict:
    manifest = json.loads((review_path / "manifest.json").read_text())
    panels = json.loads((review_path / "panels.json").read_text())
    keys = json.loads((review_path / "panel_key.json").read_text())
    derived = {}
    for item in manifest["results"]:
        panel_id = item["panel"]
        record = json.loads((review_path / item["result_path"]).read_text())
        try:
            review = retain_panel_review(record["payload"], panels[panel_id])
        except ValueError as exc:
            review, error = None, str(exc)
        else:
            error = None
        derived[panel_id] = {
            "key": keys[panel_id],
            "review": review,
            "error": error,
            "original_status": record["status"],
            "derivation": "Same saved response; no replayed model requests.",
        }
    benchmark._write_json(review_path / "derived_reviews.json", derived)
    return derived


def agreement(first: dict, second: dict) -> dict:
    if set(first) != set(second):
        raise ValueError("Agreement requires coding of the same attempted responses")
    fields = {}
    for field in ("approaches", "mathematics_status", "named_advanced_procedure"):
        disagreements = []
        for label in first:
            a, b = first[label][field], second[label][field]
            if field == "approaches":
                a, b = sorted(set(a)), sorted(set(b))
            if a != b:
                disagreements.append(
                    {
                        "attempt": label,
                        "first": a,
                        "second": b,
                        "first_reason": first[label]["rationale"],
                        "second_reason": second[label]["rationale"],
                    }
                )
        fields[field] = {
            "compared": len(first),
            "agreed": len(first) - len(disagreements),
            "disagreements": disagreements,
        }
    return fields


def calibration(output: Path) -> dict:
    protocol = json.loads(
        (ROOT / "experiments/configs/pf_student_diagnosis_20261011.json").read_text()
    )
    old = ROOT / protocol["review"]["old_probe"]
    original = json.loads((old / "review_coding.json").read_text())["attempts"]
    original_key = json.loads((old / "review_key.json").read_text())
    reverse_key = {value: key for key, value in original_key.items()}
    cal_path = output / "checklist_calibration"
    second = json.loads((cal_path / "second_reader_coding.json").read_text())["attempts"]
    result = {
        "second_reader": agreement(original, second),
        "limits": "Assistant coding agreement, not human agreement or learner-fidelity validation.",
    }
    derived = derive_reviews(cal_path / "model_review")
    model_coding = {}
    evidence_counts = Counter()
    for item in derived.values():
        review = item["review"]
        if review is None:
            continue
        evidence_counts["usable_panels"] += 1
        evidence_counts["unverified_evidence_fields"] += len(review["evidence_errors"])
        for label, row in review["attempts"].items():
            model_coding[reverse_key[item["key"]["attempts"][label]]] = row
    result["model_evidence"] = dict(evidence_counts)
    if set(model_coding) == set(original):
        result["model_vs_original"] = agreement(original, model_coding)
        result["model_vs_second_reader"] = agreement(second, model_coding)
    else:
        result["model_coding_coverage"] = {
            "available": len(model_coding),
            "attempted": len(original),
        }
    benchmark._write_json(cal_path / "agreement.json", result)
    return result


def report(output: Path) -> dict:
    cal = calibration(output)
    probe_path = output / "panel"
    manifest, records = student_report.load_results(probe_path)
    execution = student_report.summarize(probe_path)
    requests = {request["id"]: request for request in manifest["requests"]}
    spec_by_id = {spec["id"]: spec for spec in manifest["protocol"]["tasks"]}
    review_path = output / "task_reviews"
    derived = derive_reviews(review_path)
    results = {}
    families = {}
    for panel_id, item in derived.items():
        task_id = item["key"]["task_id"]
        spec = spec_by_id[task_id]
        review = item["review"]
        stats = Counter()
        learner_methods, solver_methods = Counter(), Counter()
        by_profile = {}
        if review is not None:
            for label, row in review["attempts"].items():
                request = requests[item["key"]["attempts"][label]]
                stats[f"math/{row['mathematics_status']}"] += 1
                bucket = by_profile.setdefault(request["profile_id"], Counter())
                bucket["attempted"] += 1
                bucket[f"math/{row['mathematics_status']}"] += 1
                methods = (
                    solver_methods
                    if request["profile_id"] == "ordinary_solver"
                    else learner_methods
                )
                for method in set(row["approaches"]):
                    methods[method] += 1
        family = families.setdefault(spec["family"], Counter())
        family["panels_attempted"] += 1
        for name in FINDINGS:
            status = review["findings"][name]["status"] if review else "unknown"
            family[f"{name}/{status}"] += 1
        stats["response_attempted"] = len(item["key"]["attempts"])
        for request_id in item["key"]["attempts"].values():
            stats[f"execution/{records[request_id]['status']}"] += 1
        results[task_id] = {
            "family": spec["family"],
            "source": spec["path"],
            "panel_id": panel_id,
            "review": review,
            "review_error": item["error"],
            "counts": dict(stats),
            "learner_method_occurrences": dict(learner_methods),
            "solver_method_occurrences": dict(solver_methods),
            "by_profile": {key: dict(value) for key, value in by_profile.items()},
        }
    expected_tasks = set(spec_by_id)
    if set(results) != expected_tasks:
        raise ValueError(f"Missing task panels: {sorted(expected_tasks - set(results))}")
    counts = Counter()
    counts["panels_attempted"] = len(results)
    feedback = []
    for task_id, result in results.items():
        review = result["review"]
        if review is None:
            counts["unusable_review"] += 1
            continue
        counts["usable_review"] += 1
        counts["unverified_evidence_fields"] += len(review["evidence_errors"])
        for item in review["feedback"]:
            counts[f"feedback/{item['attribution']}"] += 1
            feedback.append(
                {
                    "task_id": task_id,
                    "source": result["source"],
                    "proposed_only": True,
                    **item,
                }
            )
    review_usage = Counter()
    calls = 0
    for phase_path in (output / "checklist_calibration/model_review", review_path):
        for trace in phase_path.glob("*/model_calls.jsonl"):
            stats = benchmark._trace_stats(trace)
            if stats["calls"] != stats["finished"] or stats["malformed_lines"]:
                raise ValueError(f"Incomplete task-review trace: {trace}")
            calls += stats["calls"]
            if stats["usage"] is not None:
                review_usage.update(stats["usage"])
    report = {
        "status": "completed_baseline_diagnosis",
        "calibration_agreement": {
            key: {
                field: {"agreed": value["agreed"], "compared": value["compared"]}
                for field, value in cal[key].items()
            }
            for key in ("second_reader", "model_vs_original", "model_vs_second_reader")
            if key in cal
        },
        "execution": execution["phases"],
        "review_counts": dict(counts),
        "families": {key: dict(value) for key, value in families.items()},
        "review_requests": calls,
        "review_usage": dict(review_usage),
        "tasks": results,
        "limits": manifest["protocol"]["limitations"],
        "revision_status": "No task changes made; feedback is proposed only.",
    }
    adjudication_path = output / "feedback_adjudication.json"
    if adjudication_path.exists():
        report["feedback_adjudication"] = json.loads(adjudication_path.read_text())
    benchmark._write_json(output / "summary.json", report)
    benchmark._write_json(output / "proposed_feedback.json", feedback)
    render(output, report)
    return report


def render(output: Path, report: dict) -> None:
    labels = {
        "kapur_average_speed": "Average speed",
        "loibl_variance": "Consistency",
        "kerrigan_fair_division": "Fair division",
    }
    panels = []
    for task_id, item in report["tasks"].items():
        review = item["review"]
        text = review["summary"] if review else item["review_error"]
        findings = ""
        if review:
            findings = (
                "<ul>"
                + "".join(
                    "<li><b>"
                    + html.escape(name.replace("_", " "))
                    + "</b>: "
                    + html.escape(value["status"])
                    + ". "
                    + html.escape(value["reason"])
                    + "</li>"
                    for name, value in review["findings"].items()
                )
                + "</ul>"
            )
            if review["evidence_errors"]:
                findings += (
                    "<p><b>Unverified evidence:</b> "
                    + html.escape("; ".join(review["evidence_errors"]))
                    + "</p>"
                )
        adjudication = report.get("feedback_adjudication", {}).get("candidates", {}).get(task_id)
        if adjudication:
            findings += (
                "<p><b>Subsequent assistant check:</b> "
                + html.escape(adjudication["verdict"].replace("_", " "))
                + ". "
                + html.escape(adjudication["reason"])
                + "</p>"
            )
        panels.append(
            "<details><summary>"
            + html.escape(task_id)
            + "</summary><p>"
            + html.escape(text or "Review unavailable")
            + "</p>"
            + findings
            + f"<p><a href='task_reviews/{item['panel_id']}/result.json'>Original review</a>"
            + " &middot; <a href='proposed_feedback.json'>Proposed feedback only</a></p></details>"
        )
    rows = []
    for family, counts in report["families"].items():
        rows.append(
            "<tr><td>"
            + labels[family]
            + "</td>"
            + "".join(
                f"<td>{counts.get(f'{key}/observed', 0)}/{counts['panels_attempted']}</td>"
                for key in (
                    "accessible_start",
                    "familiar_method_limit",
                    "distinct_approaches",
                    "missing_or_ambiguous_information",
                )
            )
            + "</tr>"
        )
    execution = report["execution"]["fresh"]
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>PF research: from attempts to feedback</title><style>"
        "body{font:17px/1.6 system-ui;max-width:1100px;margin:35px auto;padding:0 24px;"
        "color:#213246;background:#f5f7fa}table{border-collapse:collapse;width:100%}"
        "td,th{padding:10px;border:1px solid #cbd5df;text-align:left}"
        "details{padding:14px;background:white;border:1px solid #cbd5df;margin:12px 0}"
        "summary{cursor:pointer;font-weight:bold}.flow{background:#e5eef5;padding:20px}"
        "</style><h1>From LLM attempts to useful PF feedback</h1>"
        "<p class='flow'>Frozen exercises &rarr; independent attempts &rarr; "
        "quoted observations &rarr; proposed task feedback</p>"
        f"<p><b>Completed:</b> 18 exercises, {execution['attempted']} fresh requests, "
        f"{execution.get('parsed', 0)} complete parseable responses. "
        "No exercise has been revised in this study.</p>"
        "<h2>What we can use now</h2>"
        "<p><b>A concrete feedback candidate:</b> some book-delivery attempts treat "
        "leg times as durations; another subtracts them as cumulative timestamps. "
        "Explicit duration labels are a testable wording change, without telling "
        "learners how to calculate average speed.</p>"
        "<p><b>Do not apply every suggestion:</b> the reviewer incorrectly called "
        "valid stage durations a timing contradiction and proposed supplying a "
        "joint decision rule that learners were asked to invent. Those required "
        "changes were rejected; original reviews are preserved below.</p>"
        "<p><b>The research boundary:</b> attempts are useful diagnostic material. "
        "We have not shown that feedback improves exercises, matches real students, "
        "or causes learning. Those need the next controlled comparison.</p>"
        "<h2>Provisional model-review findings</h2>"
        "<p>The automated reviewer matched the original assistant's exact method "
        "sets in only 16/48 calibration attempts. Its detailed diversity labels "
        "are not a validated instrument. Source-matched quotations also do not "
        "guarantee correct interpretation; see the subsequent checks below.</p>"
        "<table><tr><th>Task family</th>"
        "<th>Visible start</th><th>Familiar method reaches a limit</th>"
        "<th>Distinct methods across panel</th><th>Missing/ambiguous inputs</th></tr>"
        + "".join(rows)
        + "</table>"
        "<p>These count task panels, not students or learning gains. Each panel "
        "contains ordinary-solver controls as well as hypothetical learner roles; "
        "method variety across a mixed panel is not learner-only diversity. "
        "Unmatched quotes become unknown, not observed. Attribution to the task "
        "remains a model hypothesis. Convergence alone does not prove rigidity.</p>"
        "<p><a href='summary.json'>Full counts and per-profile methods</a> &middot; "
        "<a href='checklist_calibration/agreement.json'>Reader disagreements</a> &middot; "
        "<a href='feedback_adjudication.json'>Subsequent feedback checks</a> &middot; "
        "<a href='panel/attempts.html'>Actual written attempts</a></p>"
        + "".join(panels)
        + "</html>"
    )
    (output / "diagnosis.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-only", action="store_true")
    args = parser.parse_args()
    result = calibration(args.output) if args.calibration_only else report(args.output)
    compact = (
        {key: result[key] for key in ("calibration_agreement", "review_counts", "families")}
        if not args.calibration_only
        else {
            key: {
                field: {"agreed": value["agreed"], "compared": value["compared"]}
                for field, value in result[key].items()
            }
            for key in ("second_reader", "model_vs_original", "model_vs_second_reader")
            if key in result
        }
    )
    print(json.dumps(compact, indent=2))
