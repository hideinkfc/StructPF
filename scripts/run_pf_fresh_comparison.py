"""Matched fresh PF generation with fixed teacher context and expert references."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import sys
from collections import Counter
from fractions import Fraction
from itertools import product
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import design_brief_stage as briefs  # noqa: E402
from scripts import design_data_stage as data_stage  # noqa: E402
from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from scripts import run_situation_skeletons as situation  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.render_expert_direction_pilot_comparison import render_body  # noqa: E402

CONFIG_ROOT = ROOT / "experiments/configs/pf_expert_direction_pilot_20260929"
CASES = ("kapur_average_speed", "loibl_variance", "kerrigan_fair_division")
REFERENCES = {
    "kapur_average_speed": {
        "path": "data/pf_exercises/kapur_bielaczyc_2012.yaml",
        "summary": "Choose a bicycle handover point so two travellers arrive together. "
        "Different walking and riding rates connect a variable distance split to total time.",
        "boundary": "Paper-grounded design and student-method evidence; "
        "repository task text is normalized.",
    },
    "loibl_variance": {
        "path": "data/pf_exercises/loibl_rummel_2014.yaml",
        "summary": "Invent a consistency measure for data sets whose familiar summaries "
        "do not distinguish them. The choice of measure is itself part of the task.",
        "boundary": "Repository design reconstruction, not a complete original numerical table. "
        "The StratL consistency exercise is a different Kapur (2015) reference.",
    },
    "kerrigan_fair_division": {
        "path": "data/pf_exercises/kerrigan_weber_chinn_2021.yaml",
        "summary": "Divide a resource among people with different valuations. "
        "Whole-piece allocation creates conflicting claims, but subdivision can resolve them.",
        "boundary": "Course-sequence-grounded reference; this is not the part-to-whole ratio case.",
    },
}


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def task_is_produced(task: object) -> bool:
    return (
        isinstance(task, dict)
        and task.get("status") == "ready"
        and all(
            isinstance(task.get(field), str) and task[field].strip()
            for field in ("title", "body", "question")
        )
    )


def fixed_inputs(case_name: str) -> tuple[dict, dict, dict]:
    source = CONFIG_ROOT / f"{case_name}.json"
    config = json.loads(source.read_text())
    case = config["case"]
    learner = config["learner_context"]
    packet = {
        "schema_version": "pf-fixed-teacher-context/v1",
        "origin": "fixed_teacher_context_not_generated_D1",
        "source_config": str(source.relative_to(ROOT)),
        "records": [
            {
                "case_id": case["id"],
                "condition": "grounded",
                "result": {
                    "schema_version": "pf-fixed-teacher-context/v1",
                    "condition": "grounded",
                    "recommendations": [
                        {
                            **resource,
                            "provenance": {
                                "type": "teacher",
                                "source": "Frozen learner specification in expert-direction pilot",
                            },
                        }
                        for resource in learner["assumed_prior_knowledge"]
                    ],
                },
            }
        ],
    }
    shared = {"learner_context": learner, "benchmark_context": case["benchmark_context"]}
    return case, packet, shared


def direct_system() -> str:
    base = yaml.safe_load((CONFIG_ROOT / "direct_prompt_no_examples.yaml").read_text())["system"]
    proposal = briefs._prompts()["PROPOSE_BRIEF_SYSTEM"]
    guidance = proposal.split("DESIGN OPPORTUNITY CHECK\n", 1)[1].split(
        "SELF-AUTHORED FORMAT EXAMPLE", 1
    )[0]
    example = proposal.split("SELF-AUTHORED FORMAT EXAMPLE", 1)[1].split("{rubric_guidance}", 1)[0]
    return (
        base
        + "\n\nSHARED DESIGN GUIDANCE\n"
        + "Preserve the complete goal and necessary assumptions. Keep a successful route "
        "attainable; do not replace the target with a narrow local proxy. "
        "Anticipated approaches are hypotheses, not student evidence.\n"
        + "DESIGN OPPORTUNITY CHECK\n"
        + guidance
        + "\nThe example below is teacher-facing design guidance, not your response format. "
        "Any number requirements should be realized in your task, not returned as fields.\n"
        + "SELF-AUTHORED FORMAT EXAMPLE"
        + example
        + "\nReturn only status, title, body, question."
    )


def run(case_name: str, output: Path, repeats: int, phase: str) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    output.mkdir(parents=True, exist_ok=False)
    case, packet, shared = fixed_inputs(case_name)
    d1_path = output / "fixed_d1.json"
    save(d1_path, packet)
    context = situation._prior_context_from_d1(d1_path, case["id"])
    system = direct_system()
    user = (
        "Generate one new student-facing PF exercise directly, not a solution or design brief.\n"
        "CASE\n"
        + json.dumps(case, indent=2)
        + "\nPRIOR KNOWLEDGE\n"
        + situation._format_prior_context(context)
        + "\nSHARED BENCHMARK CONTEXT\n"
        + json.dumps(shared, indent=2)
    )
    source_hashes = diagnostic.compute_source_hashes()
    for source in (
        Path(__file__),
        CONFIG_ROOT / f"{case_name}.json",
        CONFIG_ROOT / "direct_prompt_no_examples.yaml",
        ROOT / "scripts/run_pf_paper_benchmark.py",
    ):
        source_hashes[str(source.relative_to(ROOT))] = hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
    for relative, digest in source_hashes.items():
        source = ROOT / relative
        contents = source.read_bytes()
        if hashlib.sha256(contents).hexdigest() != digest:
            raise ValueError(f"Source changed while freezing comparison: {relative}")
        snapshot = output / "source_snapshot" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(contents)
    rng = random.Random(20261010 + CASES.index(case_name))
    schedule = []
    for number in range(1, repeats + 1):
        methods = ["direct", "pipeline"]
        rng.shuffle(methods)
        schedule.extend({"number": number, "method": method} for method in methods)
    manifest = {
        "schema_version": "pf-fresh-matched-comparison/v1",
        "case_name": case_name,
        "phase": phase,
        "status": "running",
        "case": case,
        "shared_context": shared,
        "prior_context": context,
        "source_hashes": source_hashes,
        "direct_prompts": {"system": system, "user": user},
        "brief_prompt_snapshot": briefs._prompts(),
        "schedule": schedule,
        "attempts": [],
        "protocol": {
            "model": "luna",
            "pipeline_proposal_k": 2,
            "pipeline_max_calls_per_attempt": (
                (2 + briefs.MAX_SELECTION_REVISIONS) * (situation.PROPOSAL_RETRY_MAX + 1)
                + briefs.MAX_SELECTION_REVISIONS
                + 1
                + 2 * data_stage.MAX_CALLS
            ),
            "direct_calls_per_attempt": 1,
            "transport_retries": 0,
            "golden_tasks_in_generation": False,
            "prior_source": (
                "fixed teacher specification; D1 generation and LC retrieval not tested"
            ),
            "limitations": "Descriptive, not budget-matched, not blind human or student evidence. "
            "The same design opportunity guidance and hypothetical example reach both methods.",
        },
    }
    save(output / "manifest.json", manifest)
    client, model = load_client("luna")
    client = client.with_options(max_retries=0)
    manifest["protocol"]["resolved_model"] = model
    save(output / "manifest.json", manifest)
    for item in schedule:
        attempt_dir = output / f"{item['number']:03d}" / item["method"]
        if item["method"] == "direct":
            attempt_dir.mkdir(parents=True, exist_ok=False)
            response, raw, metadata, error = benchmark._call_json(
                client,
                model,
                system,
                user,
                max_tokens=6000,
                retries=0,
                trace_path=attempt_dir / "model_calls.jsonl",
                stage="direct.generate",
            )
            status, schema_error = (
                ("api_error", error) if error is not None else benchmark._validate_task(response)
            )
            record = {
                "status": status,
                "error": schema_error,
                "task": response,
                "raw_text": raw,
                "model_metadata": metadata,
            }
            save(attempt_dir / "result.json", record)
        else:
            record = diagnostic.run_case_worker(
                case["id"],
                str(attempt_dir),
                "luna",
                2,
                str(d1_path),
                case_override=case,
                shared_context=shared,
            )
        manifest["attempts"].append(
            {
                **item,
                "status": record["status"],
                "error": record.get("error"),
                "path": str((attempt_dir / "result.json").relative_to(output)),
            }
        )
        save(output / "manifest.json", manifest)
        print(case_name, phase, item["number"], item["method"], record["status"], flush=True)
    manifest["status"] = "completed"
    save(output / "manifest.json", manifest)
    return manifest


def render(output: Path) -> None:
    sections = []
    assessment_path = output / "assessment.json"
    assessment = json.loads(assessment_path.read_text()) if assessment_path.exists() else None
    summary_table = ""
    if assessment is not None and "methods" in assessment:
        methods = assessment["methods"]
        rows = [
            ("Produced drafts", "produced", False),
            ("Mathematics supported", "mathematics_status/supported", False),
            ("Consequential student choices", "consequential_choice/yes", False),
            ("Explicit method/conclusion giveaways", "disclosure_count", False),
            ("Model requests", "calls", True),
        ]
        summary_table = "<h2>What the comparison found</h2><table>"
        summary_table += "<tr><th>Separate outcome</th><th>Direct</th><th>Pipeline</th></tr>"
        for label, field, raw_count in rows:
            summary_table += "<tr><td>" + html.escape(label) + "</td>"
            for method in ("direct", "pipeline"):
                counts = methods[method]
                count = (
                    sum(
                        counts.get(f"disclosure/{kind}", 0)
                        for kind in ("method", "conclusion", "both")
                    )
                    if field == "disclosure_count"
                    else counts.get(field, 0)
                )
                value = str(count) if raw_count else f"{count}/{counts['attempted']}"
                summary_table += "<td>" + value + "</td>"
            summary_table += "</tr>"
        summary_table += "</table><p class='note'>Counts are assistant judgments, except "
        summary_table += "production and traced requests. Unsupported mathematics stays unknown, "
        summary_table += "not invalid. Choices are opportunities in task text, not observed "
        summary_table += "student approaches. Fewer requests means lower request cost, not "
        summary_table += "automatically better educational quality.</p>"
    for manifest_path in sorted(output.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        name = manifest["case_name"]
        reference = REFERENCES[name]
        source = Path(os.path.relpath(ROOT / reference["path"], output))
        reference_card = (
            "<article class='reference'><h3>Human-expert design anchor</h3><p>"
            + html.escape(reference["summary"])
            + "</p><p class='note'>"
            + html.escape(reference["boundary"])
            + f"</p><a href='{source.as_posix()}'>Source record</a></article>"
        )
        for number in sorted({item["number"] for item in manifest["attempts"]}):
            cards = [reference_card]
            for method in ("direct", "pipeline"):
                path = manifest_path.parent / f"{number:03d}" / method / "result.json"
                if not path.exists():
                    cards.append(f"<article><h3>{method}</h3><p>Not completed</p></article>")
                    continue
                record = json.loads(path.read_text())
                task = (
                    record.get("task")
                    if method == "direct"
                    else record.get("stages", {}).get("D2_D3", {}).get("task")
                )
                content = f"<p>Status: {html.escape(record['status'])}</p>"
                if task_is_produced(task):
                    content += f"<h3>{html.escape(task['title'])}</h3>"
                    content += render_body(task["body"])
                    content += (
                        "<p><b>Question</b></p><pre>" + html.escape(task["question"]) + "</pre>"
                    )
                    if task.get("quality_findings"):
                        content += "<p><b>Unresolved internal findings</b></p><ul>"
                        content += "".join(
                            "<li>" + html.escape(str(finding)) + "</li>"
                            for finding in task["quality_findings"]
                        )
                        content += "</ul>"
                else:
                    content += "<p>" + html.escape(str(record.get("error") or "")) + "</p>"
                content += f"<a href='{path.relative_to(output).as_posix()}'>Full saved result</a>"
                if assessment is not None:
                    finding = assessment["tasks"][f"{name}/{number:03d}/{method}"]
                    content += "<hr><p><b>Design assessment</b></p><p>"
                    content += html.escape(finding["impression"]) + "</p>"
                    content += "<p class='note'>" + html.escape(finding["mathematics"]) + "</p>"
                cards.append(f"<article><h3>{method.capitalize()}</h3>{content}</article>")
            sections.append(
                f"<section><h2>{html.escape(name)} / fresh set {number}</h2>"
                + "<div class='row'>"
                + "".join(cards)
                + "</div></section>"
            )
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Fresh PF comparison</title><style>"
        "body{font:16px/1.5 system-ui;margin:28px;background:#f5f7fa;color:#233044}"
        ".row{display:grid;grid-template-columns:1fr 1.5fr 1.5fr;gap:16px}"
        "article{padding:20px;background:white;border:1px solid #ccd3db;border-radius:8px}"
        ".reference{background:#fff9e9}pre{white-space:pre-wrap;font:inherit}"
        "article{min-width:0}.prose{white-space:pre-wrap}.table-wrap{overflow-x:auto}"
        "table{border-collapse:collapse;width:100%;font-size:14px}"
        "th,td{border:1px solid #ccd3db;padding:7px;text-align:left}th{background:#eef2f6}"
        ".note{font-size:13px}section{margin:30px 0}"
        "@media(max-width:900px){.row{grid-template-columns:1fr}}</style>"
        "<h1>Fresh PF generation: direct versus pipeline</h1>"
        "<p>Identical targets and fixed learner knowledge; two pipeline design candidates. "
        "Expert tasks are evaluation anchors, not prompt examples. Summaries are paraphrases. "
        "Completion is not PF success. No student outcomes or human ratings are available.</p>"
        + (
            "<p><b>Assessment:</b> " + html.escape(assessment["conclusion"]) + "</p>"
            if assessment is not None
            else ""
        )
        + summary_table
        + "".join(sections)
        + "</html>"
    )
    (output / "side_by_side.html").write_text(page, encoding="utf-8")


def verify_math(output: Path) -> dict:
    inputs = json.loads((output / "numeric_inputs.json").read_text())
    results = {}
    for key, spec in inputs.items():
        source = output / spec["source"]
        result = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        if spec["kind"] == "spread":
            rows = {}
            for name, raw in spec["values"].items():
                values = [Fraction(value) for value in raw]
                mean = sum(values) / len(values)
                rows[name] = {
                    "mean": str(mean),
                    "range": str(max(values) - min(values)),
                    "population_variance": str(sum((x - mean) ** 2 for x in values) / len(values)),
                    "mean_absolute_deviation": str(
                        sum(abs(x - mean) for x in values) / len(values)
                    ),
                }
            result["computed"] = rows
        elif spec["kind"] == "speed":
            rows = {}
            for name, row in spec["values"].items():
                distances = [Fraction(x) for x in row["distances_km"]]
                times = [Fraction(x) for x in row["moving_minutes"]]
                if len(distances) != len(times):
                    raise ValueError(f"{key}/{name}: distances and times must match")
                elapsed = sum(times) + Fraction(row["waiting_minutes"])
                rows[name] = {
                    "overall_km_per_hour": str(sum(distances) * 60 / elapsed),
                    "unweighted_moving_stage_mean_km_per_hour": str(
                        sum(d * 60 / t for d, t in zip(distances, times)) / len(distances)
                    ),
                }
            result["computed"] = rows
        elif spec["kind"] == "indivisible_allocation":
            values = [[Fraction(x) for x in row] for row in spec["values"]]
            n = len(values)
            if len({len(row) for row in values}) != 1:
                raise ValueError(f"{key}: valuation rows must have equal length")
            thresholds = [sum(row) / n for row in values]
            count = 0
            example = None
            for allocation in product(range(n), repeat=len(values[0])):
                received = [
                    sum(values[i][j] for j, owner in enumerate(allocation) if owner == i)
                    for i in range(n)
                ]
                if all(value >= threshold for value, threshold in zip(received, thresholds)):
                    count += 1
                    if example is None:
                        example = {
                            "owners_zero_based": list(allocation),
                            "received_values": [str(x) for x in received],
                        }
            result["computed"] = {
                "totals": [str(sum(row)) for row in values],
                "fair_share_thresholds": [str(x) for x in thresholds],
                "allocations_enumerated": n ** len(values[0]),
                "fair_allocations": count,
                "example": example,
            }
        else:
            raise ValueError(f"{key}: unsupported independent-check kind {spec['kind']!r}")
        results[key] = result
    report = {
        "provenance": "Exact Fraction arithmetic and exhaustive finite allocation enumeration. "
        "Inputs are manually transcribed from final task text, not generated calculation plans. "
        "This does not establish task openness, student behavior, or general procedure guarantees.",
        "inputs_sha256": hashlib.sha256((output / "numeric_inputs.json").read_bytes()).hexdigest(),
        "results": results,
    }
    save(output / "independent_math.json", report)
    return report


def prepare_review(output: Path) -> dict:
    entries = []
    for path in sorted(output.glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        for item in manifest["attempts"]:
            record = json.loads((path.parent / item["path"]).read_text())
            task = (
                record.get("task")
                if item["method"] == "direct"
                else record.get("stages", {}).get("D2_D3", {}).get("task")
            )
            entries.append(
                (
                    {
                        "case_name": manifest["case_name"],
                        "target_concept": manifest["case"]["target_concept"],
                        "learner_context": manifest["shared_context"]["learner_context"],
                        "task": (
                            {key: task.get(key) for key in ("title", "body", "question")}
                            if isinstance(task, dict)
                            else None
                        ),
                    },
                    f"{manifest['case_name']}/{item['number']:03d}/{item['method']}",
                )
            )
    if not entries:
        raise ValueError("No comparison attempts available for review")
    random.Random(20261011).shuffle(entries)
    packet = {f"task_{index:02d}": entry for index, (entry, _) in enumerate(entries, 1)}
    key = {f"task_{index:02d}": source for index, (_, source) in enumerate(entries, 1)}
    save(output / "review_packet.json", packet)
    save(output / "review_key.json", key)
    return packet


def summarize(output: Path) -> dict:
    phases = {}
    for phase in ("calibration", "calibration_v2", "fresh"):
        outcomes = Counter()
        calls = Counter()
        errors = 0
        for path in sorted((output / phase).glob("*/manifest.json")):
            manifest = json.loads(path.read_text())
            for item in manifest["attempts"]:
                record = json.loads((path.parent / item["path"]).read_text())
                task = (
                    record.get("task")
                    if item["method"] == "direct"
                    else record.get("stages", {}).get("D2_D3", {}).get("task")
                )
                delivered = task_is_produced(task)
                outcomes[f"{item['method']}/attempted"] += 1
                outcomes[f"{item['method']}/delivered"] += int(delivered)
                outcomes[f"{item['method']}/{item['status']}"] += 1
        for path in sorted((output / phase).glob("*/*/*/model_calls.jsonl")):
            for line in path.read_text().splitlines():
                event = json.loads(line)
                if event["event"] in {"model_call_started", "call_started"}:
                    calls[event["stage"]] += 1
                elif event.get("error"):
                    errors += 1
        phases[phase] = {
            "outcomes": dict(outcomes),
            "model_calls": sum(calls.values()),
            "calls_by_stage": dict(calls),
            "api_errors": errors,
        }
    report = {"phases": phases, "calibration_is_not_pooled_with_fresh": True}
    save(output / "summary.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--phase", choices=("calibration", "fresh"), default="calibration")
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--verify-math-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--prepare-review-only", action="store_true")
    args = parser.parse_args()
    if (
        sum(
            (args.render_only, args.verify_math_only, args.summarize_only, args.prepare_review_only)
        )
        > 1
    ):
        parser.error("choose only one reporting operation")
    if args.prepare_review_only:
        prepare_review(args.output)
    elif args.summarize_only:
        summarize(args.output)
    elif args.verify_math_only:
        verify_math(args.output)
    elif args.render_only:
        render(args.output)
    elif args.case is None:
        parser.error("--case is required for generation")
    else:
        run(args.case, args.output, args.repeats, args.phase)


if __name__ == "__main__":
    main()
