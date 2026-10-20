"""Export anonymous PF attempts and summarize an externally coded diagnostic."""

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

from scripts import run_pf_fresh_comparison as files  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402


def load_results(output: Path) -> tuple[dict, dict]:
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Only a completed probe can be summarized")
    records = {
        item["id"]: json.loads((output / item["result_path"]).read_text())
        for item in manifest["attempts"]
    }
    if (
        len(records) != len(manifest["attempts"])
        or len(records) != len(manifest["requests"])
        or set(records) != {request["id"] for request in manifest["requests"]}
    ):
        raise ValueError("Probe has missing or repeated attempts")
    return manifest, records


def prepare_review(output: Path) -> dict:
    manifest, records = load_results(output)
    fresh = [request for request in manifest["requests"] if request["phase"] == "fresh"]
    random.Random(20261011).shuffle(fresh)
    packet, key = {}, {}
    for index, request in enumerate(fresh, 1):
        label = f"attempt_{index:02d}"
        record = records[request["id"]]
        prompt = json.loads(request["prompt"]["user"])
        packet[label] = {
            "student_task": prompt["student_task"],
            "response_status": record["status"],
            "attempt": record["attempt"],
            "unparsed_raw_text": record["raw_text"] if record["attempt"] is None else None,
        }
        key[label] = request["id"]
    files.save(output / "review_packet.json", packet)
    files.save(output / "review_key.json", key)
    return packet


def summarize(output: Path) -> dict:
    manifest, records = load_results(output)
    requests = {request["id"]: request for request in manifest["requests"]}
    phases = {}
    for phase in ("calibration", "fresh"):
        counts = Counter()
        by_model = {}
        elapsed = 0.0
        usage = Counter()
        for request in manifest["requests"]:
            if request["phase"] != phase:
                continue
            record = records[request["id"]]
            counts["attempted"] += 1
            counts[record["status"]] += 1
            item = next(row for row in manifest["attempts"] if row["id"] == request["id"])
            trace = output / item["result_path"].replace("result.json", "model_calls.jsonl")
            stats = benchmark._trace_stats(trace)
            if stats["calls"] != 1 or stats["finished"] != 1 or stats["malformed_lines"]:
                raise ValueError(f"Request trace mismatch: {request['id']}")
            counts["requests"] += stats["calls"]
            counts["api_errors"] += stats["errors"]
            elapsed += stats["elapsed_seconds"]
            if stats["usage"] is not None:
                usage.update(stats["usage"])
            model = by_model.setdefault(request["model"], Counter())
            model["attempted"] += 1
            model[record["status"]] += 1
            finish_reason = (record["model_metadata"] or {}).get("finish_reason")
            counts[f"finish_reason/{finish_reason}"] += 1
            if phase == "calibration" and record["attempt"] is not None:
                counts["exact_arithmetic_answer"] += int(
                    record["attempt"]["answer"].strip() == request["expected_answer"]
                )
        phases[phase] = {
            **dict(counts),
            "by_model": {key: dict(value) for key, value in by_model.items()},
            "usage": dict(usage),
            "summed_request_seconds": round(elapsed, 3),
        }
    report = {
        "phases": phases,
        "limitations": manifest["protocol"]["limitations"],
        "evidence_type": "Written LLM attempts, not human cognition or learning",
    }
    coding_path = output / "review_coding.json"
    if coding_path.exists():
        coding = json.loads(coding_path.read_text())
        key = json.loads((output / "review_key.json").read_text())
        if set(coding["attempts"]) != set(key):
            raise ValueError("Coding does not cover every attempted response")
        groups = {}
        family_groups = {}
        model_groups = {}
        totals = Counter()
        families = {task["id"]: task["family"] for task in manifest["protocol"].get("tasks", [])}
        for label, row in coding["attempts"].items():
            if row["mathematics_status"] not in {"supported", "invalid", "unknown"}:
                raise ValueError(f"Unknown mathematics classification: {label}")
            if not isinstance(row["named_advanced_procedure"], bool):
                raise ValueError(f"Named procedure flag must be a boolean: {label}")
            request = requests[key[label]]
            group_id = f"{request['task_id']}/{request['profile_id']}"
            buckets = [groups.setdefault(group_id, Counter()), totals]
            model_id = f"{request['task_id']}/{request['profile_id']}/{request['model']}"
            buckets.append(model_groups.setdefault(model_id, Counter()))
            family = families.get(request["task_id"])
            if family is not None:
                family_id = f"{family}/{request['profile_id']}"
                buckets.append(family_groups.setdefault(family_id, Counter()))
            for group in buckets:
                group["attempted"] += 1
                group[f"math/{row['mathematics_status']}"] += 1
                group["named_advanced_procedure"] += int(row["named_advanced_procedure"])
                for approach in set(row["approaches"]):
                    group[f"approach/{approach}"] += 1
        report["coding_provenance"] = coding["provenance"]
        report["task_profile_groups"] = {key: dict(value) for key, value in groups.items()}
        report["family_profile_groups"] = {key: dict(value) for key, value in family_groups.items()}
        report["task_profile_model_groups"] = {
            key: dict(value) for key, value in model_groups.items()
        }
        report["coding_totals"] = dict(totals)
    files.save(output / "summary.json", report)
    return report


def render(output: Path) -> None:
    manifest, records = load_results(output)
    summary = summarize(output)
    coding_path = output / "review_coding.json"
    coding = json.loads(coding_path.read_text()) if coding_path.exists() else None
    reverse_key = (
        {value: key for key, value in json.loads((output / "review_key.json").read_text()).items()}
        if coding
        else {}
    )
    panels = []
    findings = ""
    if coding and summary["family_profile_groups"]:
        bars = []
        labels = [
            ("ordinary_solver", "Ordinary solver"),
            ("recent_prerequisites", "Recent prerequisites"),
            ("one_prerequisite_gap", "One prerequisite omitted"),
        ]
        for index, (profile, label) in enumerate(labels):
            counts = summary["family_profile_groups"].get(f"loibl_variance/{profile}")
            if counts is None:
                continue
            value = counts["named_advanced_procedure"]
            total = counts["attempted"]
            width = 440 * value / total
            y = 35 + index * 48
            bars.append(
                f"<text x='12' y='{y + 18}'>{html.escape(label)}</text>"
                f"<rect x='250' y='{y}' width='440' height='26' fill='#e1e7ee'/>"
                f"<rect x='250' y='{y}' width='{width}' height='26' fill='#3175a9'/>"
                f"<text x='705' y='{y + 18}'>{value}/{total} attempts</text>"
            )
        findings = (
            "<h2>The profile changes the written approach</h2>"
            "<p>Consistency tasks: attempts explicitly applying a named variance or "
            "standard-deviation procedure. These are observed LLM outputs under "
            "hypothetical profiles, not human students.</p>"
            "<svg viewBox='0 0 900 195' role='img' "
            "aria-label='Named advanced procedure use by hypothetical learner profile' "
            "style='width:100%;font:16px system-ui'>" + "".join(bars) + "</svg>"
            "<p>Learner-role replies use range, concentration and absolute departures "
            "instead. But omitting mean from the record does not reliably remove "
            "the model's ability to calculate it. Prompt responsiveness is not "
            "learner fidelity.</p>"
            "<p>Fair-division replies repeatedly use competing claims and allocation "
            "repairs. Some contain value or scheduling errors; these do not establish "
            "that real learners would make the same mistakes. Different allocations "
            "are not automatically different mathematical methods.</p>"
        )
    for request in manifest["requests"]:
        if request["phase"] != "fresh":
            continue
        record = records[request["id"]]
        task = json.loads(request["prompt"]["user"])["student_task"]
        attempt = record["attempt"]
        text = (
            attempt["written_work"] + "\n\nAnswer: " + attempt["answer"]
            if attempt
            else record["raw_text"]
        )
        source = f"fresh/{request['id']}/result.json"
        panel = (
            "<details><summary>"
            + html.escape(
                f"{request['task_id']} / {request['profile_id']} / "
                f"{request['model']} / repeat {request['repeat']} / {record['status']}"
            )
            + "</summary><h3>Exercise</h3><pre>"
            + html.escape(task)
            + "</pre><h3>Written attempt</h3><pre>"
            + html.escape(text)
            + "</pre>"
        )
        if coding:
            row = coding["attempts"][reverse_key[request["id"]]]
            panel += "<p><b>Assistant coding:</b> " + html.escape(row["rationale"]) + "</p>"
        panel += f"<p><a href='{source}'>Full saved response</a></p></details>"
        panels.append(panel)
    phases = summary["phases"]
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>LLM students: first PF diagnostic</title><style>"
        "body{font:17px/1.55 system-ui;max-width:1100px;margin:35px auto;padding:0 24px;"
        "background:#f6f8fb;color:#243247}pre{white-space:pre-wrap;font:inherit}"
        "details{background:white;border:1px solid #ccd6df;padding:16px;margin:14px 0;"
        "border-radius:8px}summary{cursor:pointer;font-weight:600}"
        ".flow{padding:20px;background:#e8f0f6;border-radius:10px}</style>"
        "<h1>Can an LLM attempt a PF exercise as a learner?</h1>"
        "<p class='flow'>Frozen exercise + prerequisite record &rarr; independent "
        "written attempt &rarr; mathematical-method review</p>"
        "<p>Ordinary solver &middot; recent prerequisites &middot; one prerequisite gap. "
        "No solution, desired mistake, ideal approach or generator label was supplied. "
        "These profiles are hypothetical, not diagnosed real students.</p>"
        f"<p><b>Completed:</b> {phases['fresh']['attempted']} fresh requests; "
        f"{phases['fresh'].get('parsed', 0)} parseable attempts; "
        f"{phases['fresh'].get('invalid_response', 0)} malformed responses retained. "
        f"Calibration: {phases['calibration'].get('exact_arithmetic_answer', 0)}/"
        f"{phases['calibration']['attempted']} exact arithmetic answers.</p>"
        "<p>Written-work variety is not human fidelity or learning. Token-truncated "
        "responses are execution limitations, not student failure. No attempt was "
        "regenerated to obtain a desired approach.</p>"
        "<p><a href='summary.json'>Separate counts and usage</a> &middot; "
        "<a href='manifest.json'>Frozen inputs and request provenance</a></p>"
        + findings
        + "".join(panels)
        + "</html>"
    )
    (output / "attempts.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-review", action="store_true")
    args = parser.parse_args()
    if args.prepare_review:
        packet = prepare_review(args.output)
        print(f"Exported {len(packet)} anonymous attempts")
    else:
        report = summarize(args.output)
        render(args.output)
        print(json.dumps(report, indent=2))
