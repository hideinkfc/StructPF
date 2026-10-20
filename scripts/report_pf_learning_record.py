"""Report the frozen omitted/present/added-learning-record experiment."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_student_probe as probe_report  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from src.evaluation.pf_record_adherence import FLAGS, parse_coding  # noqa: E402

PROFILES = (
    "one_prerequisite_gap",
    "recent_prerequisites",
    "additional_learned_method",
    "ordinary_solver",
)
LABELS = {
    "one_prerequisite_gap": "Prerequisite omitted",
    "recent_prerequisites": "Usual prerequisites",
    "additional_learned_method": "Additional method learned",
    "ordinary_solver": "Ordinary solver",
}


def counts(rows: dict) -> dict:
    result = Counter(attempted=len(rows))
    for row in rows.values():
        for flag in FLAGS:
            result[f"{flag}/{row[flag]}"] += 1
        result[f"mathematics/{row['mathematics_status']}"] += 1
    return dict(result)


def summarize(output: Path) -> dict:
    panel = output / "panel"
    manifest, _ = probe_report.load_results(panel)
    packet = json.loads((panel / "review_packet.json").read_text())
    key = json.loads((panel / "review_key.json").read_text())
    coding = deepcopy(parse_coding(json.loads((output / "record_coding.json").read_text()), packet))
    adjudication_path = output / "coding_adjudication.json"
    adjudication = None
    if adjudication_path.exists():
        adjudication = json.loads(adjudication_path.read_text())
        for label, override in adjudication["overrides"].items():
            if label not in coding["attempts"] or set(override["flags"]) - set(FLAGS):
                raise ValueError("Adjudication references an unknown attempt or coding flag")
            coding["attempts"][label].update(override["flags"])
        parse_coding(coding, packet)
    requests = {request["id"]: request for request in manifest["requests"]}
    if len(key) != len(packet) or len(set(key.values())) != len(key):
        raise ValueError("Anonymous record key has incomplete or repeated attempt mappings")
    fresh_ids = {request["id"] for request in requests.values() if request["phase"] == "fresh"}
    if set(key.values()) != fresh_ids:
        raise ValueError("Record key does not match the complete fresh schedule")
    tasks = {task["id"]: task for task in manifest["protocol"]["tasks"]}
    rows = {}
    for label, row in coding["attempts"].items():
        request = requests[key[label]]
        rows[key[label]] = {
            **row,
            "anonymous_id": label,
            "task_id": request["task_id"],
            "profile": request["profile_id"],
            "model": request["model"],
            "repeat": request["repeat"],
            "family": tasks[request["task_id"]]["family"],
        }
    family_groups, task_groups, model_groups = {}, {}, {}
    for family in sorted({row["family"] for row in rows.values()}):
        for profile in PROFILES:
            subset = {
                key: row
                for key, row in rows.items()
                if row["family"] == family and row["profile"] == profile
            }
            family_groups[f"{family}/{profile}"] = counts(subset)
    for task in tasks:
        for profile in PROFILES:
            subset = {
                key: row
                for key, row in rows.items()
                if row["task_id"] == task and row["profile"] == profile
            }
            task_groups[f"{task}/{profile}"] = counts(subset)
            for model in manifest["protocol"]["models"]:
                model_groups[f"{task}/{profile}/{model}"] = counts(
                    {key: row for key, row in subset.items() if row["model"] == model}
                )
    summary = {
        "question": manifest["protocol"]["question"],
        "evidence": "Label-hidden assistant coding of written model behavior, not human fidelity.",
        "coding_provenance": coding["provenance"],
        "execution": probe_report.summarize(panel)["phases"],
        "family_groups": family_groups,
        "task_groups": task_groups,
        "task_model_groups": model_groups,
        "attempts": rows,
        "limitations": manifest["protocol"]["limitations"],
    }
    agreement_path = output / "coding_agreement.json"
    if agreement_path.exists():
        summary["coding_agreement"] = json.loads(agreement_path.read_text())
    if adjudication is not None:
        summary["coding_adjudication"] = adjudication
    benchmark._write_json(output / "summary.json", summary)
    render(output, summary)
    return summary


def render(output: Path, summary: dict) -> None:
    panels = []
    for request_id, row in summary["attempts"].items():
        evidence = "".join(
            "<p><b>"
            + html.escape(flag.replace("_", " "))
            + "</b>: "
            + html.escape(row[flag])
            + "</p><blockquote>"
            + html.escape("\n".join(row["evidence"][flag]))
            + "</blockquote>"
            for flag in FLAGS
            if row[flag] != "no"
        )
        panels.append(
            "<details><summary>"
            + html.escape(
                f"{row['task_id']} / {LABELS[row['profile']]} / {row['model']} / "
                f"repeat {row['repeat']}"
            )
            + "</summary><p>"
            + html.escape(row["rationale"])
            + "</p>"
            + evidence
            + f"<a href='panel/fresh/{request_id}/result.json'>Original written attempt</a>"
            + "</details>"
        )
    tables = []
    charts = []
    for family, title in (
        ("loibl_variance", "Consistency: actual mean and spread-method use"),
        ("kerrigan_fair_division", "Fair division: actual procedure use"),
    ):
        table = f"<h2>{title}</h2><table><tr><th>Record</th>"
        table += "<th>Prerequisite applied</th><th>Advanced method applied</th>"
        table += "<th>Advanced method mentioned only</th><th>Explicit record-bound stop</th></tr>"
        for profile in PROFILES:
            group = summary["family_groups"][f"{family}/{profile}"]
            table += "<tr><td>" + LABELS[profile] + "</td>"
            for flag in (
                "prerequisite_applied",
                "advanced_applied",
                "advanced_mentioned_only",
                "record_bound_stop",
            ):
                table += f"<td>{group.get(f'{flag}/yes', 0)}/{group['attempted']}"
                unknown = group.get(f"{flag}/unknown", 0)
                if unknown:
                    table += f" ({unknown} unknown)"
                table += "</td>"
            table += "</tr>"
        tables.append(table + "</table>")
        if family == "loibl_variance":
            bars = []
            for index, profile in enumerate(PROFILES):
                group = summary["family_groups"][f"{family}/{profile}"]
                yes = group.get("advanced_applied/yes", 0)
                unknown = group.get("advanced_applied/unknown", 0)
                y = 20 + index * 47
                width = 390 * yes / group["attempted"]
                bars.append(
                    f"<text x='10' y='{y + 18}'>{LABELS[profile]}</text>"
                    f"<rect x='255' y='{y}' width='390' height='26' fill='#e0e7ee'/>"
                    f"<rect x='255' y='{y}' width='{width}' height='26' fill='#3075a6'/>"
                    f"<text x='660' y='{y + 18}'>{yes}/{group['attempted']}"
                    + (f"; {unknown} unknown" if unknown else "")
                    + "</text>"
                )
            charts.append(
                "<h2>Does adding the learned method change actual use?</h2>"
                "<p>Consistency attempts that actually calculate variance or standard "
                "deviation—not merely mention the name. These are measured written "
                "LLM outputs under hypothetical records.</p>"
                "<svg viewBox='0 0 900 215' role='img' "
                "aria-label='Actual variance or standard-deviation use by learning record' "
                "style='width:100%;font:16px system-ui'>" + "".join(bars) + "</svg>"
            )
    execution = summary["execution"]["fresh"]
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Do LLM students follow their learning record?</title><style>"
        "body{font:17px/1.6 system-ui;max-width:1100px;margin:30px auto;padding:0 24px;"
        "color:#253447;background:#f6f8fa}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #cad4de;padding:10px;text-align:left}"
        "details{background:white;border:1px solid #cad4de;padding:14px;margin:12px 0}"
        "summary{cursor:pointer;font-weight:bold}blockquote{white-space:pre-wrap}"
        ".flow{background:#e8f0f6;padding:18px;border-radius:10px}</style>"
        "<h1>Does the learning record change what the LLM actually does?</h1>"
        "<p class='flow'>Same exercise &rarr; omitted / usual / added learning record "
        "&rarr; independent attempt &rarr; actual use versus mere mention</p>"
        f"<p>Four tasks, two models, four conditions, three repetitions: "
        f"{execution['attempted']} fresh requests, {execution.get('parsed', 0)} complete. "
        "Eight arithmetic controls are separate. No exercise or learner instruction "
        "was tuned against these outputs.</p>"
        "<p>Counts are source-quoted assistant judgments of mathematical actions. "
        "Added method names can prime use; a hypothetical learning record is not "
        "measured knowledge. Constructing a new idea from arithmetic is allowed. "
        "Mentioning an unfamiliar method is not automatically a violation, and a "
        "token cutoff is not student failure.</p>"
        "<p>A balanced second reader agreed on prerequisite use in 32/32 cases "
        "and advanced-method use in 31/32. The disputed truncated allocation "
        "response remains unknown in the reported counts; both original ratings "
        "are preserved. This is assistant agreement, not human validation.</p>"
        + "".join(charts)
        + "".join(tables)
        + "<p><a href='summary.json'>Task/model counts and full coding</a> &middot; "
        "<a href='panel/attempts.html'>Written attempts</a> &middot; "
        "<a href='record_coding.json'>Anonymous coding and evidence</a></p>"
        "<p><a href='coding_agreement.json'>Second-reader agreement</a> &middot; "
        "<a href='coding_adjudication.json'>Conservative interpretation</a></p>"
        + "".join(panels)
        + "</html>"
    )
    (output / "learning_record.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.output)
    print(json.dumps(result["family_groups"], indent=2))
