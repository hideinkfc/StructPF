"""Human-readable paired evidence report and a labels-hidden task review pack."""

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

from src.evaluation.pf_evidence_audit import FINDINGS, PARSED_STATUSES  # noqa: E402
from src.evaluation.pf_rubric import learner_context  # noqa: E402

STYLE = """
body{font:16px/1.5 system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#172033}
h1,h2{line-height:1.2} article{border:1px solid #ccd3df;border-radius:8px;padding:1.3rem;margin:1.5rem 0}
pre{white-space:pre-wrap;font:inherit} table{border-collapse:collapse;width:100%}
td,th{border:1px solid #ccd3df;padding:.5rem;text-align:left} blockquote{border-left:4px solid #678;padding-left:1rem}
.note{background:#eef3f8;padding:1rem} small{color:#4c586a}
"""


def load(path: Path):
    return json.loads(path.read_text())


def esc(value) -> str:
    return html.escape(str(value))


def page(title: str, body: str) -> str:
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{esc(title)}</title><style>{STYLE}</style><body><h1>{esc(title)}</h1>{body}</body></html>'


def task_block(entry: dict) -> str:
    task = entry.get("task") or {}
    return "".join(
        f"<h3>{esc(task.get('title', 'Unavailable task'))}</h3>" if key == "title"
        else f"<pre>{esc(task.get(key, 'Not supplied'))}</pre>"
        for key in ("title", "body", "question")
    )


def review_pack(output: Path, catalog: list[dict]) -> None:
    shuffled = list(catalog)
    random.Random(20261014).shuffle(shuffled)
    mapping = {}
    entries = []
    body = '<p class="note">Task source and all ratings are hidden. This is a review form, not collected human evidence. Review the text before seeing the paired gallery.</p>'
    questions = [
        "What exact task passages support a workable start from the supplied prior knowledge?",
        "Does a passage supply the central method or conclusion, or only legitimate problem support?",
        "Which mathematical choice changes the reasoning or warranted conclusion? Quote its instruction.",
        "Describe two genuinely different mathematical ideas, or explain why apparent routes use the same idea.",
        "Are any necessary data absent or contradictory? Distinguish intentional criterion invention.",
        "Recompute a specific relationship. What assumptions does that calculation require?",
        "For original MR/OE anchors, distinguish limited new properties from evidence against the original wording.",
    ]
    for index, entry in enumerate(shuffled, 1):
        identifier = f"review-{index:03d}"
        mapping[identifier] = entry["task_id"]
        context_error = None
        try:
            context = (
                learner_context(entry["learner_context"])
                if isinstance(entry.get("learner_context"), dict) else None
            )
        except (ValueError, TypeError) as error:
            context = None
            context_error = f"{type(error).__name__}: {error}"
        public = {
            "review_id": identifier, "task": entry.get("task"),
            "learning_target": entry.get("learning_target"),
            "learner_context": context,
            "context_error": context_error,
            "questions": questions,
        }
        entries.append(public)
        body += (
            f"<article><h2>{identifier}</h2><p><strong>Target:</strong> {esc(entry.get('learning_target'))}</p>"
            f"<p><strong>Prior context:</strong> {esc(json.dumps(context, ensure_ascii=False))}</p>"
            f"{task_block(entry)}<ol>" + "".join(f"<li>{esc(question)}<p>Response: ____________________</p></li>" for question in questions)
            + "</ol></article>"
        )
    (output / "review_pack_labels_hidden.html").write_text(page("Labels-hidden task review", body))
    (output / "review_pack_labels_hidden.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    (output / "review_pack_mapping_private.json").write_text(json.dumps(mapping, indent=2) + "\n")


def report_run(output: Path) -> None:
    summary = load(output / "summary.json")
    manifest = load(output / "manifest.json")
    catalog = load(output / "catalog.json")["tasks"]
    judgments = [
        json.loads(line) for line in (output / "judgments.jsonl").read_text().splitlines()
    ]
    indexed = {(row["task_id"], row["judge"]): row for row in judgments}
    catalog_index = {entry["task_id"]: entry for entry in catalog}
    review_pack(output, catalog)
    paired = summary["same_task_high_score_findings"]
    original = summary["original_distribution"]
    sampling_text = (
        "Selection was fixed before audit collection, without selecting by historical scores or known faults. "
        "Pipeline controls are conditional on ready outputs; stopped attempts are not counted as task-quality failures."
        if manifest["sampling"].get("selection_independent_of_old_score_and_faults")
        else "The caller-supplied catalog was frozen before this evaluation. Its selection independence "
        "and representativeness are not established by this evaluator."
    )
    text = [
        "# Same-task PF measurement-gap study",
        "",
        "This is a computational evidence audit, not human validation, learner behavior, or deterministic task-mathematics proof.",
        "",
        f"The frozen catalog has {summary['catalog_tasks']} tasks. {summary['parsed_judgments']} of "
        f"{summary['scheduled_judgments']} scheduled main judgments parsed; "
        f"{summary['missing_judgments']} judgments are missing. GPT-4.1 and GPT-5.4 are two series in the same OpenAI family.",
        "",
        f"Fully schema-valid audits: {summary['fully_valid_judgments']}; partially valid audits: "
        f"{summary['partially_valid_judgments']}. Field validation failures: "
        f"{summary['field_validation_error_counts']}. Invalid fields remain unknown with explicit "
        "validation errors and immutable raw data; other valid fields survive.",
        "",
        f"Delivered denominators: {summary['delivered_denominators']['student_tasks_supplied']} "
        f"student tasks supplied; {summary['delivered_denominators']['paired_parseable_audits']} "
        f"paired parseable audits. Availability counts: {summary['availability_counts']}. "
        "Unavailable tasks or audits are not judged mathematical failures.",
        "",
        "## Scope and original scores",
        "",
        manifest["sampling"]["selection_scope"],
        "",
        sampling_text,
        "",
        f"Saved original total-score distribution: {original['totals']}. "
        f"{original['ceiling_15_count']} paired ratings are at the 15-point ceiling. "
        f"{original['high_score_count']} tasks meet the predeclared total >= 14 screening flag, which is not a quality truth threshold.",
        "",
        "## Same-task findings",
        "",
        f"Among the {paired['denominator']} high-screen tasks, {paired['with_agreed_original_anchor_tension']} have a "
        f"two-judge original-high-anchor tension candidate, and {paired['with_agreed_additional_concern']} have at least one "
        f"additional-property concern. {paired['additional_concern_without_anchor_tension']} have an additional concern "
        "without an original-anchor tension.",
        "",
        "Both require two judges on the same property and exact verified task quotations. An anchor tension is a "
        "candidate for interpretation review, not proof an original high rating is false. Representation diversity "
        "is retained in the original MR definition; consequential choice is not retroactively required by original OE.",
        "",
        "## Separate outcomes",
        "",
        "| Task-evidence property | Agreed support | Agreed concern | Unknown/disputed | All tasks |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, counts in summary["rates"].items():
        text.append(f"| {name} | {counts['pass']} | {counts['concern']} | {counts['unknown']} | {counts['denominator_all_catalog_tasks']} |")
    text.extend([
        "",
        "The fixed checklist is the conjunction of mathematics, target relevance, accessible start, preserved "
        "discovery, and consequential choice. It is NOT all PF requirements. Idea diversity is separate. "
        "Mathematics support means model-supported/no confirmed concern, with model_recomputed and "
        "source-grounded exact arithmetic witnesses; it is not proof "
        "that every requirement is consistent. Math concerns remain unresolved; unsupported arithmetic stays unknown.",
        "",
        "## Agreement and quotation fidelity",
        "",
        "| Property | Matched paired categories | Parsed pairs | Known pairs | Agreement on known pairs |",
        "|---|---:|---:|---:|---:|",
    ])
    for name, values in summary["agreement"].items():
        text.append(
            f"| {name} | {values['matched_categories']} | {values['paired_parsed_denominator']} | "
            f"{values['known_pair_denominator']} | {values['agreement_known_pairs']} |"
        )
    fidelity = summary["quote_fidelity"]
    text.extend([
        "",
        f"Exact source fidelity: {fidelity['verified_exact_quotes']} of {fidelity['quoted_spans_checked']} "
        "finding quotes matched contiguous task text. Exact quote matching checks source fidelity, not the interpretation.",
        "",
        "## Frozen instrument controls",
        "",
    ])
    calibration = summary["execution"].get("calibration")
    if calibration:
        for key, values in calibration["by_role_and_judge"].items():
            text.append(
                f"- {key}: {values['matching_property_checks']} of {values['expected_property_checks']} "
                "predeclared illustrative property expectations matched."
            )
        mismatches = [row for row in calibration["rows"] if not row["matches"]]
        unavailable = sum(row.get("field_validation_error") is not None for row in mismatches)
        text.extend([
            "", f"{len(mismatches)} expected property checks did not match, including "
            f"{unavailable} unavailable because of field validation failure. No prompt tuning followed these results.",
        ])
        for row in mismatches:
            text.append(
                f"- {row['task_id']} / {row['judge']} / {row['property']}: expected "
                f"{row['expected_allowed']}, observed {row['observed']}."
            )
    else:
        text.append("No controls were run in this caller-supplied catalog.")
    text.extend([
        "",
        "## Judge direction and unresolved review queue",
        "",
        "Agreement does not establish validity. Raw status distributions are retained separately from "
        "pass/concern/unknown decisions so that partial evidence is not mistaken for approval.",
        "",
    ])
    for judge, properties in summary["judge_status_distributions"].items():
        for name in ("preserved_discovery", "consequential_choice", "distinct_mathematical_ideas", "useful_prior_contrast"):
            text.append(f"- {judge}, {name}: {properties[name]}.")
    review_ids = [
        row["task_id"] for row in summary["rows"]
        if any("concern" in values for name, values in row["individual_decisions"].items()
               if name in FINDINGS or name.startswith("anchor_"))
        and not row["agreed_additional_concerns"] and not row["agreed_original_anchor_tensions"]
    ]
    text.extend([
        "",
        f"{len(review_ids)} tasks have a one-judge evidence concern without two-judge agreement. "
        "They are disputed review candidates, not verified issues. A judge that nearly always supports "
        "a property may be lenient, so zero consensus concerns must not be read as a validated positive result.",
        "",
    ])
    if summary.get("analysis_correction"):
        text.extend([
            "A runtime-only analysis correction was applied after collection. The frozen prompt, responses, "
            "selection and original ratings were unchanged; original analysis is preserved in analysis_original_v1. "
            "The correction enforces the predeclared unresolved-mathematics policy and adds transparent raw vote "
            "counts. It did not change this study's headline counts.",
            "",
        ])
    if summary.get("parser_correction"):
        text.extend([
            "This is the V1.3 mechanical parser sidecar. The prompt, task sample, original ratings and "
            "raw model responses are unchanged, and no new calls were made. Field-local validation retains "
            "valid findings beside invalid fields; invalid fields remain unknown with their raw data and "
            "explicit validation errors. Strict quoted concern witnesses are accepted as typed evidence, "
            "not converted into prose. Previous reports are archived in previous_analysis_v1_2. "
            "See [old versus corrected counts](comparison_to_previous.json).",
            "",
        ])
    execution = summary["execution"]
    text.extend([
        "",
        "## Execution and limitations",
        "",
        f"Recorded requests: {execution['actual_model_requests']} (cap {execution['request_cap']}); "
        f"prompt tokens {execution['total_prompt_tokens']}; completion tokens {execution['total_completion_tokens']}. "
        "Each saved request has a response ID when returned, token usage, latency, raw/parsed output and input hash. No automatic retries.",
        "",
        "Unknowns and disagreements are retained in the full catalog denominator. Known-only coverage is reported "
        "separately in summary.json and must not be treated as unconditional performance. Two judges can share "
        "biases; exact arithmetic cannot verify arbitrary semantics; no human ratings or student attempts have "
        "been collected. No cross-topic or causal generation-improvement claim follows.",
        "",
        "Review artifacts: [labels-hidden pack](review_pack_labels_hidden.html), "
        "[same-task gallery with historical ratings revealed](same_task_issue_gallery.html), "
        "[disputed same-task review candidates](same_task_disagreement_gallery.html), "
        "[full summary](summary.json), [calibration details](calibration_summary.json).",
    ])
    markdown = "\n".join(text) + "\n"
    (output / "report.md").write_text(markdown)
    try:
        import markdown as markdown_library
    except ImportError:
        body = f"<pre>{esc(markdown)}</pre>"
    else:
        body = markdown_library.markdown(markdown, extensions=["tables"])
    (output / "report.html").write_text(page("Same-task measurement-gap report", body))
    gallery = (
        '<p class="note">Historical ratings are revealed here AFTER blind audit. '
        'Agreed concerns are computational evidence candidates, not human adjudications or proof of learner failure.</p>'
    )
    gallery_rows = []
    for row in summary["rows"]:
        if not row["agreed_additional_concerns"] and not row["agreed_original_anchor_tensions"] and not row["unresolved_mathematical_concern_judges"]:
            continue
        entry = catalog_index[row["task_id"]]
        gallery_rows.append(row["task_id"])
        gallery += (
            f"<article><h2>{esc(row['task_id'])}</h2><p>Source condition: {esc(row['arm'])}; "
            f"immutable original scores: {esc(row['original_scores'])}</p>{task_block(entry)}"
            f"<p>Original-anchor tensions: {esc(row['agreed_original_anchor_tensions'])}</p>"
            f"<p>Additional concerns: {esc(row['agreed_additional_concerns'])}</p>"
            f"<p>Unresolved mathematical concerns: {esc(row['unresolved_mathematical_concern_judges'])}</p>"
        )
        properties = [
            *row["agreed_additional_concerns"],
            *(f"anchor_{name}" for name in row["agreed_original_anchor_tensions"]),
        ]
        if row["unresolved_mathematical_concern_judges"]:
            properties.append("mathematics")
        for judge in summary["judges"]:
            result = indexed.get((row["task_id"], judge))
            if not result or result.get("status") not in PARSED_STATUSES:
                continue
            gallery += f"<h3>{esc(judge)}</h3>"
            for name in properties:
                finding = (
                    result["audit"]["original_high_anchor_support"][name[7:]]
                    if name.startswith("anchor_") else result["audit"][name]
                )
                gallery += f"<h4>{esc(name)}</h4><p>{esc(finding['reason'])}</p>"
                for quote in finding["task_quotes"]:
                    gallery += f"<blockquote>{esc(quote)}</blockquote>"
                gallery += f"<p>Counterevidence: {esc(finding['counterevidence'])}</p>"
            gallery += f"<details><summary>Exact arithmetic witness checks</summary><pre>{esc(json.dumps(result['mathematical_witness_checks'], indent=2))}</pre></details>"
        gallery += "</article>"
    if not gallery_rows:
        gallery += "<p>No agreed concerns or unresolved math concerns were observed.</p>"
    (output / "same_task_issue_gallery.html").write_text(page("Same-task paired evidence gallery", gallery))
    (output / "gallery_index.json").write_text(json.dumps({"tasks": gallery_rows}, indent=2) + "\n")
    disputed = '<p class="note">One-judge concerns without consensus. These are NOT verified issues. Historical scores are revealed after the blind audit for human interpretation review.</p>'
    for task_id in review_ids:
        entry = catalog_index[task_id]
        row = next(row for row in summary["rows"] if row["task_id"] == task_id)
        disputed += (
            f"<article><h2>{esc(task_id)}</h2><p>Original scores: {esc(row['original_scores'])}</p>"
            + task_block(entry)
        )
        for name, votes in row["individual_decisions"].items():
            if "concern" not in votes:
                continue
            disputed += f"<h3>{esc(name)}: {esc(votes)}</h3>"
            for judge in summary["judges"]:
                result = indexed.get((task_id, judge))
                if not result or result["status"] not in PARSED_STATUSES:
                    continue
                finding = (
                    result["audit"]["original_high_anchor_support"][name[7:]]
                    if name.startswith("anchor_") else result["audit"][name]
                )
                disputed += (
                    f"<h4>{esc(judge)}: {esc(finding['status'])}</h4><p>{esc(finding['reason'])}</p>"
                    + "".join(f"<blockquote>{esc(quote)}</blockquote>" for quote in finding["task_quotes"])
                    + f"<p>Counterevidence: {esc(finding['counterevidence'])}</p>"
                )
        disputed += "</article>"
    if not review_ids:
        disputed += "<p>No one-judge concerns were observed.</p>"
    (output / "same_task_disagreement_gallery.html").write_text(page("Disputed same-task review candidates", disputed))
    (output / "disagreement_gallery_index.json").write_text(json.dumps({"tasks": review_ids}, indent=2) + "\n")
    arm_rates = {}
    for arm in sorted({row["arm"] for row in summary["rows"]}):
        rows = [row for row in summary["rows"] if row["arm"] == arm]
        arm_rates[arm] = {
            "tasks": len(rows),
            "fixed_checklist_counts": dict(Counter(row["fixed_checklist"] for row in rows)),
            "additional_concern_tasks": sum(bool(row["agreed_additional_concerns"]) for row in rows),
            "anchor_tension_tasks": sum(bool(row["agreed_original_anchor_tensions"]) for row in rows),
            "property_counts": {
                name: dict(Counter(row["consensus"][name] for row in rows)) for name in FINDINGS
            },
            "scope": "Descriptive unequal sample sizes; not a causal comparison",
        }
    (output / "arm_descriptive_rates.json").write_text(json.dumps(arm_rates, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report_run(args.output)


if __name__ == "__main__":
    main()
