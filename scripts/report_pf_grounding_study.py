"""Render a grounding comparison from frozen tasks and existing audits; no model calls."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.pf_grounding_statistics import paired_block_summary  # noqa: E402

ARMS = {"A": "No retrieval", "B": "Curriculum", "C": "Curriculum + Learning Commons"}
PROPERTIES = (
    "target_relevance",
    "accessible_start",
    "task_specification",
    "preserved_discovery",
    "consequential_choice",
    "distinct_mathematical_ideas",
    "useful_prior_contrast",
    "mathematics",
    "fixed_checklist",
)
LABELS = {
    "target_relevance": "Target relevance",
    "accessible_start": "Accessible start",
    "task_specification": "Task specification",
    "preserved_discovery": "Discovery preserved",
    "consequential_choice": "Consequential choice",
    "distinct_mathematical_ideas": "Distinct idea opportunities",
    "useful_prior_contrast": "Useful prior contrast",
    "mathematics": "Mathematical support (not full proof)",
    "fixed_checklist": "Five-property conjunction (primary)",
}


def summarize(catalog: list[dict], audit_summary: dict) -> dict:
    tasks = {task["task_id"]: task for task in catalog}
    rows = {row["task_id"]: row for row in audit_summary["rows"]}
    if len(tasks) != len(catalog) or len(rows) != len(audit_summary["rows"]):
        raise ValueError("Task IDs must be unique")
    if tasks.keys() != rows.keys():
        raise ValueError("Every scheduled grounding task must have exactly one audit summary row")
    for task in tasks.values():
        if task["arm"] not in ARMS:
            raise ValueError(f"Unknown arm: {task['arm']}")
    rates: dict[str, dict] = {}
    comparisons: dict[str, dict] = {}
    for property_name in PROPERTIES:
        records = []
        for task_id, task in tasks.items():
            row = rows[task_id]
            if property_name == "fixed_checklist":
                outcome = row["fixed_checklist_value"]
                availability = row["availability"]
                reason = row["availability_reason"]
            else:
                outcome = row["consensus_values"][property_name]
                availability = row["property_availability"][property_name]
                reason = row["property_failure_reasons"].get(property_name)
            record = {
                "case_id": task["case_id"],
                "repeat": task["repeat"],
                "arm": task["arm"],
                "outcome": outcome,
                "availability": availability,
            }
            if availability != "available":
                record["unavailability_reason"] = reason
            records.append(record)
        rates[property_name] = {}
        for arm in ARMS:
            selected = [record for record in records if record["arm"] == arm]
            if not selected:
                raise ValueError(f"No scheduled records in arm {arm}")
            counts = Counter(
                "supported"
                if record["outcome"] is True
                else "concern"
                if record["outcome"] is False
                else "unknown"
                for record in selected
            )
            rates[property_name][arm] = {
                **{key: counts[key] for key in ("supported", "concern", "unknown")},
                "scheduled": len(selected),
                "unavailable": sum(record["availability"] != "available" for record in selected),
                "supported_rate": counts["supported"] / len(selected),
            }
        comparisons[property_name] = {
            name: paired_block_summary(records, treatment=treatment, baseline=baseline)
            for name, treatment, baseline in (
                ("curriculum_vs_none", "B", "A"),
                ("lc_incremental", "C", "B"),
                ("combined_package_vs_none", "C", "A"),
            )
        }
    return {
        "schema_version": "pf-grounding-comparison-analysis/v1",
        "arm_labels": ARMS,
        "scheduled": len(catalog),
        "delivered": {
            arm: sum(
                bool(task.get("produced")) and isinstance(task.get("task"), dict)
                for task in catalog
                if task["arm"] == arm
            )
            for arm in ARMS
        },
        "rates": rates,
        "comparisons": comparisons,
        "scope": (
            "A fixed-prior-reference-availability pilot. Model-supported task affordances "
            "and arithmetic witnesses, not human-validated PF or student learning."
        ),
        "unknown_policy": (
            "Unknown, disputed or unverified evidence is not task failure. Support rates "
            "use every scheduled output; unknown sensitivity is reported separately."
        ),
        "audit_execution": audit_summary["execution"],
        "judge_status_distributions": audit_summary.get("judge_status_distributions", {}),
        "audit_version": audit_summary["analysis_version"],
        "interpretation_boundary": (
            "Component support differences are model-evidence signals only. An unresolved "
            "primary conjunction cannot demonstrate an educational benefit or no effect. "
            "The first audit dropped prior learning; use this corrected-input audit only "
            "for the grounding comparison, and preserve the earlier technical failure."
        ),
    }


def render(summary: dict, task_gallery: str, audit_report: str) -> str:
    primary_counts = {
        state: sum(summary["rates"]["fixed_checklist"][arm][state] for arm in ARMS)
        for state in ("supported", "concern", "unknown")
    }
    primary_heading = (
        "The primary comparison is inconclusive."
        if primary_counts["unknown"] > summary["scheduled"] / 2
        else "The primary outcome is a model-evidence conjunction, not full PF validation."
    )
    bars = []
    for index, (arm, label) in enumerate(ARMS.items()):
        counts = summary["rates"]["fixed_checklist"][arm]
        y = 28 + index * 54
        x = 250.0
        segments = []
        for state, color in (
            ("supported", "#447fa7"),
            ("concern", "#b46456"),
            ("unknown", "#ced7df"),
        ):
            width = 300 * counts[state] / counts["scheduled"]
            segments.append(
                f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="25" fill="{color}"/>'
            )
            x += width
        bars.append(
            f'<text x="0" y="{y + 18}">{html.escape(label)}</text>'
            + "".join(segments)
            + f'<text x="565" y="{y + 18}">{counts["supported"]}/{counts["scheduled"]}</text>'
        )
    chart = (
        '<svg viewBox="0 0 640 190" role="img" aria-label="Supported primary outcomes '
        'out of all scheduled outputs in each condition" style="width:100%;max-width:800px">'
        + "".join(bars)
        + '<text x="250" y="184" font-size="12">Blue: supported; red: concern; grey: unknown</text>'
        + "</svg>"
    )
    table_rows = []
    for property_name in PROPERTIES:
        cells = []
        for arm in ARMS:
            count = summary["rates"][property_name][arm]
            cells.append(
                f"<td><strong>{count['supported']}/{count['scheduled']}</strong>"
                f"<br><small>{count['concern']} concerns; "
                f"{count['unknown']} unknown/disputed</small></td>"
            )
        table_rows.append(f"<tr><th>{html.escape(LABELS[property_name])}</th>{''.join(cells)}</tr>")
    primary = summary["comparisons"]["fixed_checklist"]
    blocks = primary["curriculum_vs_none"]["per_case"]
    block_rows = []
    for block in blocks:
        case = block["case_id"]
        values = [
            next(entry for entry in primary[name]["per_case"] if entry["case_id"] == case)
            for name in ("curriculum_vs_none", "lc_incremental")
        ]
        counts = [values[0]["arms"]["A"], values[0]["arms"]["B"], values[1]["arms"]["C"]]
        block_rows.append(
            f"<tr><th>{html.escape(case.replace('_', ' '))}</th>"
            + "".join(
                f"<td>{count['supported']}/{block['scheduled_pairs']}; "
                f"{count['unknown']} unknown</td>"
                for count in counts
            )
            + "</tr>"
        )
    effects = []
    for name, title in (
        ("curriculum_vs_none", "Curriculum minus no retrieval"),
        ("lc_incremental", "Additional Learning Commons"),
    ):
        comparison = primary[name]
        difference = comparison["equal_case_weighted_supported_rate_difference"] * 100
        interval = [value * 100 for value in comparison["target_block_bootstrap"]["interval_95"]]
        bounds = [
            value * 100 for value in comparison["equal_case_weighted_unknown_sensitivity_bounds"]
        ]
        effects.append(
            f"<h3>{title}</h3><p>Supported-output difference: <strong>{difference:+.1f} "
            f"percentage points</strong>. Exploratory five-specification block interval: "
            f"[{interval[0]:+.1f}, {interval[1]:+.1f}]. Unknown sensitivity bounds: "
            f"[{bounds[0]:+.1f}, {bounds[1]:+.1f}].</p>"
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Curriculum and Learning Commons grounding: bounded results</title>"
        "<style>body{max-width:1100px;margin:40px auto;padding:0 24px;font:17px/1.6 "
        "system-ui;color:#202932}h1,h2{line-height:1.2}table{border-collapse:collapse;"
        "width:100%;margin:24px 0}th,td{padding:12px;border-bottom:1px solid #ccd4dc;"
        "text-align:left;vertical-align:top}small{color:#586875}.scope{background:#edf3f8;"
        "padding:18px;border-left:4px solid #50728f}a{color:#245f9b}</style><body>"
        "<h1>Does grounding improve PF design?</h1>"
        '<p class="scope">Measured computational pilot: 60 scheduled tasks across five '
        "specifications, four repeats and three conditions. All generation priors were "
        "fixed. Support means two-model evidence support, not human validation. "
        "Unknowns are not failures.</p>"
        "<h2>What changed?</h2><p>No retrieval → curriculum → the same curriculum plus "
        "Learning Commons. This tests reference availability during design, not whether "
        "the model independently discovers the class's prior knowledge.</p>"
        "<h2>Separate educational properties</h2>"
        f"<p><strong>{primary_heading}</strong> "
        f"{primary_counts['supported']}/{summary['scheduled']} tasks have all five "
        f"properties supported; {primary_counts['concern']} have agreed concerns and "
        f"{primary_counts['unknown']} are unresolved. Component differences "
        "must not be promoted to a general quality advantage. The earlier audit lost "
        "the prior-learning input; this page uses the repaired-input run.</p>"
        + chart
        + "<p>The chart shows the measured five-property conjunction. A grey segment is "
        "unresolved evidence, not a failed exercise. These are model-supported outcomes, "
        "not an educational-quality scale.</p>"
        + "<p>Each bold number counts supported tasks out of all scheduled tasks. Higher "
        "support is favorable for that property only. The full conjunction is not a "
        "complete or validated PF score.</p>"
        "<table><tr><th>Property</th>"
        + "".join(f"<th>{html.escape(label)}</th>" for label in ARMS.values())
        + "</tr>"
        + "".join(table_rows)
        + "</table>"
        "<h2>Primary outcome by task specification</h2><table><tr><th>Specification</th>"
        + "".join(f"<th>{html.escape(label)}</th>" for label in ARMS.values())
        + "</tr>"
        + "".join(block_rows)
        + "</table>"
        "<h2>Paired comparisons</h2>"
        + "".join(effects)
        + "<p>Repeats are nested in task specifications. Five blocks make uncertainty "
        "fragile; these are descriptive pilot comparisons, not a generalization test "
        "across curricula. Unknown sensitivity can be wider than the bootstrap interval.</p>"
        "<h2>Evidence and limitations</h2><p>Learning Commons search was grade-unfiltered; "
        "some references were advanced or off-topic. Conditions have different text "
        "lengths. Broader topics were already inspected, so this is a transfer check. "
        "The judges are different OpenAI model series with known calibration limitations, "
        "not independent human experts.</p>"
        f'<p><a href="{html.escape(task_gallery, quote=True)}">All generated tasks</a> · '
        f'<a href="{html.escape(audit_report, quote=True)}">Full audit evidence</a> · '
        '<a href="summary.json">Numerical summary</a></p></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--audit-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog_path = args.generation / "all_tasks.json"
    catalog = json.loads(catalog_path.read_text())["tasks"]
    audits = json.loads(args.audit_summary.read_text())
    summary = summarize(catalog, audits)
    summary["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary["input_sha256"] = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (catalog_path, args.audit_summary)
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    from os.path import relpath

    page = render(
        summary,
        relpath(args.generation / "tasks.html", args.output),
        relpath(args.audit_summary.parent / "report.html", args.output),
    )
    (args.output / "report.html").write_text(page)
    print(json.dumps({"scheduled": summary["scheduled"], "delivered": summary["delivered"]}))


if __name__ == "__main__":
    main()
