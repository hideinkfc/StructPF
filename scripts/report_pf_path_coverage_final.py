"""Reproducible operational path audit and final bounded research synthesis."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_attempt_revision as task_metrics  # noqa: E402
from scripts import report_pf_student_probe as students  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from src.evaluation.pf_path_coverage import (  # noqa: E402
    path_counts,
    source_text,
    validate_path,
    weighted_path_rate,
)


def baseline_report(output: Path) -> dict:
    audit = json.loads((output / "baseline_coverage.json").read_text())
    config = json.loads(
        (ROOT / "experiments/configs/pf_path_coverage_final_20261012.json").read_text()
    )
    root = ROOT / config["baseline_attempt_root"]
    manifest, records = students.load_results(root)
    requests = {row["id"]: row for row in manifest["requests"]}
    report = {"provenance": audit["provenance"], "tasks": {}}
    for task_id, task in audit["tasks"].items():
        source = json.loads((ROOT / task["source"]).read_text())
        brief = source["stages"]["D2_D3"]["brief_selection"]["selected_brief"]
        text = "\n".join(
            [a["first_action"] for a in brief["approaches"]] + [brief["successful_route"]]
        )
        attempts = {label: records[label] for label in task["learner_attempt_ids"]}
        paths = []
        for path in task["paths"]:
            validate_path(path, attempts, text)
            counts = path_counts(path)
            if (
                counts["reached"] != path["reached_count"]
                or counts["not_observed"] != path["not_observed_count"]
                or counts["unknown"] != path["unknown_count"]
            ):
                raise ValueError("Cached path counts do not match actual classifications")
            profiles = {label: requests[label]["profile_id"] for label in attempts}
            sensitivity = [
                weighted_path_rate(
                    path["attempts"],
                    profiles,
                    {
                        "recent_prerequisites": weight,
                        "one_prerequisite_gap": 1 - weight,
                    },
                )
                for weight in (0.25, 0.5, 0.75)
            ]
            paths.append(
                {
                    **{
                        key: path[key]
                        for key in (
                            "id",
                            "kind",
                            "design_quote",
                            "operational_definition",
                            "same_idea_as",
                        )
                    },
                    "counts": counts,
                    "assumed_mix_sensitivity": sensitivity,
                }
            )
        report["tasks"][task_id] = {
            "source": task["source"],
            "denominator": len(attempts),
            "paths": paths,
            "diagnosis": task["diagnosis"],
            "unexpected": task["new_paths"],
        }
    benchmark._write_json(output / "baseline_report.json", report)
    return report


def prepare_attempt_panels(output: Path) -> dict:
    freeze = json.loads((output / "codebook_freeze.json").read_text())
    codebook_path = ROOT / freeze["codebook"]["path"]
    if hashlib.sha256(codebook_path.read_bytes()).hexdigest() != freeze["codebook"]["sha256"]:
        raise ValueError("Prospective path definitions changed after freeze")
    codebook = json.loads(codebook_path.read_text())
    manifest, records = students.load_results(output / "attempts")
    keys = json.loads((output / "review_key.json").read_text())
    specs = {row["id"]: row for row in manifest["protocol"]["tasks"]}
    panels, panel_keys = {}, {}
    for label, identifier in keys.items():
        requests = [
            r for r in manifest["requests"] if r["phase"] == "fresh" and r["task_id"] == identifier
        ]
        if len(requests) != 18:
            raise ValueError("Available final variant requires eighteen scheduled attempts")
        random.Random(20261014).shuffle(requests)
        entries, mapping = {}, {}
        text = json.loads(requests[0]["prompt"]["user"])["student_task"]
        for index, request in enumerate(requests, 1):
            attempt_label = f"a{index:02d}"
            record = records[request["id"]]
            entries[attempt_label] = {
                "attempt": record["attempt"],
                "unparsed_raw_text": record["raw_text"] if record["attempt"] is None else None,
                "execution_status": record["status"],
            }
            mapping[attempt_label] = request["id"]
        panels[label] = {
            "student_task": text,
            "paths": codebook["tasks"][label]["paths"],
            "attempts": entries,
        }
        panel_keys[label] = {"identifier": identifier, "attempts": mapping}
    benchmark._write_json(output / "attempt_panel_key.json", panel_keys)
    for family in {spec["family"] for spec in specs.values()}:
        benchmark._write_json(
            output / f"attempt_packet_{family}.json",
            {
                label: panel
                for label, panel in panels.items()
                if specs[keys[label]]["family"] == family
            },
        )
    return panels


def validate_panel_coding(coding: dict, packet: dict) -> dict:
    if set(coding["tasks"]) != set(packet):
        raise ValueError("Final path coding must cover every scheduled panel")
    for label, task in coding["tasks"].items():
        original = packet[label]
        definitions = {path["id"]: path for path in original["paths"]}
        if set(task["paths"]) != set(definitions):
            raise ValueError("Final path coding changed the prospective path list")
        for path_id, row in task["paths"].items():
            validate_path(
                {**definitions[path_id], "attempts": row["attempts"]},
                original["attempts"],
                definitions[path_id]["design_quote"],
            )
        if set(task["attempts"]) != set(original["attempts"]):
            raise ValueError("Final attempt coding must keep every outcome")
        for attempt_id, row in task["attempts"].items():
            if row["mathematics"] not in {"supported", "invalid", "unknown"}:
                raise ValueError("Unknown mathematical status in final attempt coding")
            if row["initial_access"] not in {"yes", "no", "unknown"}:
                raise ValueError("Unknown access status in final attempt coding")
            for quote in row["evidence"]:
                if (
                    not isinstance(quote, str)
                    or not quote.strip()
                    or quote not in source_text(original["attempts"][attempt_id])
                ):
                    raise ValueError("Final attempt evidence does not match its response")
        for unexpected in task["unexpected_paths"]:
            if unexpected["attempt"] not in original["attempts"]:
                raise ValueError("Unexpected path references an unscheduled attempt")
            for quote in unexpected["evidence"]:
                if quote not in source_text(original["attempts"][unexpected["attempt"]]):
                    raise ValueError("Unexpected-path evidence does not match its response")
    return coding


def request_group(request: dict) -> str:
    if request["profile_id"] == "ordinary_solver":
        return "solver"
    return "learner_gpt54" if request["model"] == "gpt54" else "learner_gpt41"


def final_report(output: Path) -> dict:
    baseline = baseline_report(output)
    ratings = json.loads((output / "task_ratings_student_only.json").read_text())
    task_keys = json.loads((output / "review_key.json").read_text())
    if set(ratings["tasks"]) != set(task_keys):
        raise ValueError("Final task review lacks a scheduled original or variant")
    panel_keys = json.loads((output / "attempt_panel_key.json").read_text())
    codebook = json.loads((output / "path_codebook.json").read_text())
    manifest, _ = students.load_results(output / "attempts")
    requests = {r["id"]: r for r in manifest["requests"]}
    config = json.loads(
        (ROOT / "experiments/configs/pf_path_coverage_final_20261012.json").read_text()
    )
    tasks = {}
    coding_by_label = {}
    for family in {spec["family"] for spec in config["cases"]}:
        packet = json.loads((output / f"attempt_packet_{family}.json").read_text())
        coding = validate_panel_coding(
            json.loads((output / f"path_coding_{family}.json").read_text()),
            packet,
        )
        coding_by_label.update(coding["tasks"])
    arm_counts = {arm: Counter() for arm in config["arms"]}
    for label, identifier in task_keys.items():
        review = ratings["tasks"][label]
        case_id, arm = identifier.split("_", 1)
        counts = arm_counts[arm]
        counts["tasks"] += 1
        counts["design_requirements"] += int(task_metrics.qualified(review))
        for field in task_metrics.TASK_OPTIONS:
            counts[f"{field}/{review[field]}"] += 1
        coding = coding_by_label[label]
        paths = []
        for definition in codebook["tasks"][label]["paths"]:
            path_id = definition["id"]
            row = coding["paths"][path_id]
            groups = {}
            for condition in ("learner_gpt41", "learner_gpt54", "solver"):
                selected = {
                    aid: value
                    for aid, value in row["attempts"].items()
                    if request_group(requests[panel_keys[label]["attempts"][aid]]) == condition
                }
                groups[condition] = path_counts({"attempts": selected})
            paths.append({**definition, "groups": groups})
        attempts = Counter()
        for aid, value in coding["attempts"].items():
            request = requests[panel_keys[label]["attempts"][aid]]
            group = "solver" if request["profile_id"] == "ordinary_solver" else "learner"
            attempts[f"{group}/attempted"] += 1
            attempts[f"{group}/mathematics/{value['mathematics']}"] += 1
        tasks[identifier] = {
            "case_id": case_id,
            "arm": arm,
            "label": label,
            "task_review": review,
            "path_denominator": len(paths),
            "paths": paths,
            "attempt_counts": dict(attempts),
            "unexpected_paths": coding["unexpected_paths"],
            "diagnosis": coding["diagnosis"],
        }
    stage_calls = 0
    stage_usage = {}
    for phase in ("calibration", "fresh"):
        run = json.loads((output / phase / "manifest.json").read_text())
        for row in run["results"]:
            trace = output / phase / row["result_path"].replace("result.json", "model_calls.jsonl")
            summary = benchmark._trace_stats(trace)
            if summary["calls"] != summary["finished"] or summary["malformed_lines"]:
                raise ValueError("Incomplete structural-generation request trace")
            stage_calls += summary["calls"]
            stage_usage.setdefault(phase, Counter())["calls"] += summary["calls"]
    ordinary = arm_counts["design_review"]["design_requirements"]
    coverage = arm_counts["coverage_feedback"]["design_requirements"]
    result = {
        "boundary": config["boundary"],
        "status": "final_bounded_campaign_complete",
        "baseline": baseline,
        "task_review_provenance": ratings["provenance"],
        "arms": {arm: dict(value) for arm, value in arm_counts.items()},
        "design_gain_margin": coverage - ordinary,
        "design_gain_threshold_met": (
            coverage - ordinary >= 2
            and arm_counts["coverage_feedback"]["mathematics/supported"]
            >= arm_counts["design_review"]["mathematics/supported"]
            and arm_counts["coverage_feedback"]["accessible_start/yes"]
            >= arm_counts["design_review"]["accessible_start/yes"]
        ),
        "tasks": tasks,
        "stage_requests": stage_calls,
        "stage_requests_by_phase": {phase: dict(value) for phase, value in stage_usage.items()},
        "evaluation_execution": students.summarize(output / "attempts")["phases"],
        "actual_total_requests": stage_calls + len(manifest["requests"]),
        "maximum_requests": config["budget"]["max_requests"],
        "limitations": config["limits"],
        "global_generator_promoted": False,
        "learner_fidelity_validated": False,
        "real_student_or_learning_evidence": False,
        "stop": "No further automatic experiments. Findings retained regardless of result.",
    }
    check_path = output / "final_interpretation.json"
    if check_path.exists():
        result["final_interpretation"] = json.loads(check_path.read_text())
    if result["actual_total_requests"] > result["maximum_requests"]:
        raise ValueError("Final campaign exceeded its frozen request budget")
    benchmark._write_json(output / "summary.json", result)
    render(output, result)
    return result


def render(output: Path, result: dict) -> None:
    cards = []
    task_packet = json.loads((output / "task_review_packet.json").read_text())
    for identifier, task in result["tasks"].items():
        rows = []
        for path in task["paths"]:
            learner = path["groups"]["learner_gpt41"]
            transfer = path["groups"]["learner_gpt54"]
            rows.append(
                "<tr><td>"
                + html.escape(path["operational_definition"])
                + "</td><td>"
                + html.escape(path["kind"])
                + f"</td><td>{learner['reached']}/"
                f"{learner['attempted']} ({learner['unknown']} unknown)</td>"
                f"<td>{transfer['reached']}/{transfer['attempted']} "
                f"({transfer['unknown']} unknown)</td></tr>"
            )
        student_task = task_packet[task["label"]]["student_task"]
        text = (
            "<h3>Student exercise</h3><pre>"
            + html.escape(
                student_task["title"]
                + "\n\n"
                + student_task["body"]
                + "\n\n"
                + student_task["question"]
            )
            + "</pre>"
            if student_task is not None
            else "<p>No usable student task was produced.</p>"
        )
        cards.append(
            "<details><summary>"
            + html.escape(identifier)
            + "</summary><p>"
            + html.escape(task["task_review"]["rationale"])
            + "</p>"
            + text
            + "<p>"
            + html.escape(task["diagnosis"])
            + "</p><table>"
            "<tr><th>Intended mathematical action</th><th>Kind</th>"
            "<th>GPT-4.1 learner attempts</th><th>GPT-5.4 learner attempts</th></tr>"
            + "".join(rows)
            + "</table></details>"
        )
    totals = []
    chart = ""
    original_division = result["tasks"].get("division_original")
    if original_division:
        trimming = next(
            (path for path in original_division["paths"] if path["id"] == "p03"),
            None,
        )
        if trimming:
            bars = []
            for index, (group_id, label) in enumerate(
                (
                    ("learner_gpt41", "GPT-4.1 learner conditions"),
                    ("learner_gpt54", "GPT-5.4 learner conditions"),
                )
            ):
                counts = trimming["groups"][group_id]
                y = 20 + index * 52
                width = 390 * counts["reached"] / counts["attempted"]
                bars.append(
                    f"<text x='10' y='{y + 18}'>{label}</text>"
                    f"<rect x='290' y='{y}' width='390' height='28' fill='#dfe7ee'/>"
                    f"<rect x='290' y='{y}' width='{width}' height='28' fill='#3176a5'/>"
                    f"<text x='700' y='{y + 18}'>{counts['reached']}/"
                    f"{counts['attempted']} attempts</text>"
                )
            chart = (
                "<h2>Same original task, different observed path coverage</h2>"
                "<svg viewBox='0 0 950 140' role='img' style='width:100%;font:16px system-ui' "
                "aria-label='Original division intended-trimming reach by model series'>"
                + "".join(bars)
                + "</svg>"
                "<p>Measured model replies under hypothetical learner records. Reaching "
                "the structure does not prove correct execution or human realism.</p>"
            )
    for metric, label in (
        ("mathematics/supported", "Supported mathematics"),
        ("target/preserved", "Target preserved"),
        ("consequential_choice/yes", "Consequential choice"),
        ("disclosure/none", "Central discovery not supplied"),
        ("design_requirements", "All predefined design requirements"),
    ):
        totals.append(
            "<tr><td>"
            + label
            + "</td>"
            + "".join(
                f"<td>{result['arms'][arm].get(metric, 0)}/3</td>"
                for arm in ("original", "design_review", "coverage_feedback")
            )
            + "</tr>"
        )
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Final PF research: designed paths and feedback</title><style>"
        "body{font:17px/1.6 system-ui;max-width:1150px;margin:32px auto;padding:0 24px;"
        "background:#f5f7fa;color:#23364a}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #cbd6df;padding:10px;text-align:left}"
        "details{background:white;border:1px solid #cbd6df;padding:14px;margin:16px 0}"
        "summary{cursor:pointer;font-weight:bold}.flow{background:#e6eff6;padding:20px}"
        "pre{white-space:pre-wrap;font:inherit}</style>"
        "<h1>Designed paths: a diagnostic, not a simulated classroom verdict</h1>"
        "<p class='flow'>Saved design &rarr; intended mathematical actions &rarr; "
        "independent attempts &rarr; reached / not observed / unknown &rarr; "
        "one bounded design-level feedback comparison</p>"
        "<p>The thesis component ends here as a computational pilot: evidence-linked "
        "path diagnosis, simulator-sensitivity findings and matched feedback results. "
        "No human learner distribution, learning effects or SOTA claim is established.</p>"
        f"<p><b>Final campaign:</b> {result['actual_total_requests']}/"
        f"{result['maximum_requests']} maximum model requests. Global generator "
        "promotion: no. Additional automatic rounds: none.</p>"
        "<h2>What the thesis component establishes</h2>"
        "<p><b>Path coverage is useful as a diagnostic:</b> it distinguishes intended "
        "actions, performed actions, uncertain outputs and unexpected valid methods.</p>"
        "<p><b>Its answer depends on the simulator:</b> on the unchanged division "
        "task, the trimming route was reached in 0/8 GPT-4.1 learner attempts but "
        "4/4 GPT-5.4 learner attempts. Neither count is a real student probability "
        "or a guarantee that the procedure is mathematically valid.</p>"
        "<p><b>No added redesign advantage is established:</b> coverage feedback "
        "met task requirements on 3/3 versus 2/3 for specific design review, below "
        "the predefined two-case gain. The difference depends on a tiny literal "
        "precision defect; treating it as approximation would leave a tie. Both "
        "arms added a genuine rest/route choice to speed, but learner methods "
        "still converged on the same aggregate-rate idea.</p>"
        + chart
        + "<h2>Task design review, three cases per arm</h2><table><tr><th>Outcome</th>"
        "<th>Original</th><th>Specific design review</th><th>Review + path coverage</th></tr>"
        + "".join(totals)
        + "</table>"
        "<p>Assistant label-hidden review, not human ratings. Intended-path sets "
        "can change during redesign; their denominators are displayed and are not "
        "an improvement score. A path missing from these samples is not impossible "
        "or evidence of a task defect. Alternative valid paths remain recorded.</p>"
        "<p>The design-review division task's exact decimal values conflict at "
        "roughly 10^-10 precision; the allocation remains feasible in its intended "
        "interpretation. Coverage division permits a whole-block solution, but "
        "unknown within-block values limit its designed fractional route. These "
        "are separate task/data/path limitations, not learner failure.</p>"
        "<p><a href='summary.json'>Final synthesis and all path counts</a> &middot; "
        "<a href='baseline_report.json'>All nine original task audits and assumed mixes</a>"
        " &middot; <a href='attempts/attempts.html'>All fresh written attempts</a></p>"
        + "".join(cards)
        + "</html>"
    )
    (output / "final_report.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("baseline", "prepare_attempts", "final"), required=True)
    args = parser.parse_args()
    if args.phase == "baseline":
        result = baseline_report(args.output)
        print(f"Verified {len(result['tasks'])} retrospective task audits")
    elif args.phase == "prepare_attempts":
        result = prepare_attempt_panels(args.output)
        print(f"Prepared {len(result)} prospective-path evaluation panels")
    else:
        result = final_report(args.output)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in ("arms", "design_gain_margin", "actual_total_requests")
                },
                indent=2,
            )
        )
