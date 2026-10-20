"""Readable, provenance-stratified report of frozen computational PF judgments."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.run_pf_measure_campaign import calibration_diagnostics, write
from src.evaluation.pf_task_measures import MEASURES
from src.evaluation.pf_three_role import VERSION

NAMES = {
    "target_alignment": "Target alignment",
    "mathematical_validity": "Mathematical validity",
    "prior_knowledge_accessibility": "Prior-knowledge accessibility",
    "familiar_approach_limits": "Limits of familiar approaches",
    "room_for_invention": "Room for invention",
}
VALUES = ["yes", "partly", "no", "unclear", "not_assessed", "execution_error"]
COLORS = {
    "yes": "#3976a5",
    "partly": "#8cb6d0",
    "no": "#b86345",
    "unclear": "#cbb06b",
    "not_assessed": "#d7dde4",
    "execution_error": "#8a536e",
}


def value_plot(tables):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 560" role="img"'
        ' aria-label="Measured categorical verdict counts by judge series">'
        '<rect width="1100" height="560" fill="white"/>',
        '<text x="20" y="32" font-family="system-ui" font-size="22">'
        "All saved input conditions: measured judgments, not PF-quality scores</text>",
    ]
    for index, value in enumerate(VALUES):
        x = 20 + index * 175
        parts.append(
            f'<rect x="{x}" y="50" width="14" height="14" fill="{COLORS[value]}"/>'
            f'<text x="{x + 20}" y="62" font-family="system-ui" font-size="13">'
            f"{value.replace('_', ' ')}</text>"
        )
    for index, measure in enumerate(MEASURES):
        y = 104 + index * 84
        parts.append(
            f'<text x="20" y="{y}" font-family="system-ui" font-size="16">{NAMES[measure]}</text>'
        )
        for offset, judge in enumerate(["luna", "gpt41"]):
            counts = tables[judge][measure]
            total = sum(counts.values())
            by = y + 8 + offset * 25
            parts.append(
                f'<text x="20" y="{by + 15}" font-family="system-ui" font-size="13">'
                f"{judge}, N={total}</text>"
            )
            x = 180
            for value in VALUES:
                width = counts[value] / total * 880 if total else 0
                parts.append(
                    f'<rect x="{x:.2f}" y="{by}" width="{width:.2f}" height="20"'
                    f' fill="{COLORS[value]}"><title>{judge} {NAMES[measure]}: '
                    f"{value}={counts[value]} of {total}</title></rect>"
                )
                if width >= 35:
                    parts.append(
                        f'<text x="{x + width / 2:.2f}" y="{by + 15}" text-anchor="middle"'
                        f' font-family="system-ui" font-size="12">{counts[value]}</text>'
                    )
                x += width
    parts.append(
        '<text x="20" y="548" font-family="system-ui" font-size="13">'
        "N counts task/target/history conditions; skipped assessments stay visible. "
        "Approach-limit Yes is not a quality pass.</text></svg>"
    )
    return "\n".join(parts)


def benchmark_plot(groups):
    chosen = {
        group.get("condition"): group
        for group in groups
        if "luna_v4" in group.get("run_id", "")
        and group.get("record_role") == "generation_result"
        and group.get("source_scope") == "benchmark_terminal_slot"
    }
    if set(chosen) != {"V1", "V2", "V3", "PIPELINE"}:
        return None
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 360">'
        '<rect width="1000" height="360" fill="white"/>'
        '<text x="20" y="30" font-family="system-ui" font-size="21">'
        "Historical v4: room for invention, primary Luna judgments</text>",
    ]
    categories = ["yes", "partly", "no", "unclear", "execution_error", "no_task_text"]
    colors = {**COLORS, "no_task_text": "#e9edf1"}
    for index, value in enumerate(categories):
        x = 20 + index * 160
        parts.append(
            f'<rect x="{x}" y="48" width="13" height="13" fill="{colors[value]}"/>'
            f'<text x="{x + 18}" y="60" font-family="system-ui" font-size="13">'
            f"{value.replace('_', ' ')}</text>"
        )
    for index, condition in enumerate(["V1", "V2", "V3", "PIPELINE"]):
        group = chosen[condition]
        judged = group["judgments"]["luna"]
        counts = dict(judged["measures"]["room_for_invention"])
        slots = group["occurrence_count"]
        counts["no_task_text"] = slots - judged["evaluated_conditions"]
        if counts["no_task_text"] < 0 or sum(counts[value] for value in categories) != slots:
            raise ValueError("Benchmark slot/condition counts do not reconcile")
        y = 88 + index * 54
        parts.append(
            f'<text x="20" y="{y + 22}" font-family="system-ui" font-size="16">{condition}</text>'
        )
        x = 160
        for value in categories:
            width = counts[value] / slots * 800 if slots else 0
            parts.append(
                f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" height="32"'
                f' fill="{colors[value]}"><title>{condition}: {value}={counts[value]}'
                f" of {slots} saved slots</title></rect>"
            )
            if width >= 25:
                parts.append(
                    f'<text x="{x + width / 2:.2f}" y="{y + 22}" text-anchor="middle" '
                    f'font-family="system-ui" font-size="14">{counts[value]}</text>'
                )
            x += width
    parts.append(
        '<text x="20" y="330" font-family="system-ui" font-size="13">'
        "Counts original generation slots, not students. Missing texts and judge failures "
        'are separate.</text><text x="20" y="350" font-family="system-ui" font-size="13">'
        "Artifact judgments only; no learning outcome or general pipeline advantage "
        "is established.</text></svg>"
    )
    return "\n".join(parts)


def count_rows(results, measure):
    counts = Counter(row["measures"][measure]["value"] or "execution_error" for row in results)
    return {value: counts[value] for value in VALUES}


def occurrence_label(occurrence):
    method = occurrence.get("method") or occurrence.get("condition") or "unspecified"
    run = (
        occurrence.get("run_id")
        or occurrence.get("run")
        or occurrence.get("source_run")
        or occurrence.get("source", "")
    )
    return f"{run} · {method}"


def calibration_section(directory, pack_cases):
    if not (directory / "results.json").exists():
        return {"status": "not_run"}
    results = json.loads((directory / "results.json").read_text())
    diagnostics = calibration_diagnostics(pack_cases, results)
    return {"summary": json.loads((directory / "summary.json").read_text()), **diagnostics}


def generate(catalog_path, pack_path, full_dir, development_dir, transfer_dir, output):
    catalog = json.loads(catalog_path.read_text())
    pack = json.loads(pack_path.read_text())
    results = json.loads((full_dir / "results.json").read_text())
    cases = {case["case_id"]: case for case in catalog["cases"]}
    selected = {
        judge: [
            item
            for item in results
            if item["judge_model"] == judge
            and item["solver_model"] == "luna"
            and item["repeat"] == 0
        ]
        for judge in ["luna", "gpt41"]
    }
    grouped = defaultdict(lambda: defaultdict(list))
    for judge, records in selected.items():
        for result in records:
            occurrence_groups = Counter(
                occurrence_label(occ) for occ in cases[result["case_id"]].get("occurrences", [])
            )
            for label, multiplicity in occurrence_groups.items():
                grouped[label][judge].extend([result] * multiplicity)
    groups = {
        label: {
            judge: {
                "occurrences": len(items),
                "measures": {measure: count_rows(items, measure) for measure in MEASURES},
            }
            for judge, items in judges.items()
        }
        for label, judges in sorted(grouped.items())
    }
    development = calibration_section(
        development_dir, pack["development"] + pack.get("controls", [])
    )
    transfer = calibration_section(transfer_dir, pack["transfer"])
    stats = {
        "instrument": VERSION,
        "human_validated": False,
        "inventory": catalog.get("inventory_summary", {}),
        "unique_input_conditions_evaluated": len(selected["luna"]),
        "total_catalog_conditions": len(cases),
        "saved_metadata_coverage": {
            "target_available": sum(bool(case.get("learning_target")) for case in cases.values()),
            "history_available": sum(
                bool((case.get("learner_context") or {}).get("assumed_prior_knowledge"))
                for case in cases.values()
            ),
            "source_occurrences": sum(len(case.get("occurrences", [])) for case in cases.values()),
        },
        "unassessable_records": len(catalog.get("unassessable", [])),
        "by_judge": {
            judge: {measure: count_rows(items, measure) for measure in MEASURES}
            for judge, items in selected.items()
        },
        "run_method_occurrences": groups,
        "calibration": {"development": development, "reserved_transfer": transfer},
        "execution": json.loads((full_dir / "summary.json").read_text()),
        "limitations": [
            "Two OpenAI model series, not independent families.",
            "Assistant-provisional references, not human-reviewed gold.",
            "Same task/target/prerequisite conditions share assessment, all occurrences retained.",
            "Different historical conditions/history are not pooled as causal comparisons.",
            "Task opportunities, not observed student failure, class frequencies or learning.",
            "Reserved transfer cases are not new untouched topics.",
            "Transfer preceded a bounded missing-field execution correction; no rerun or retuning.",
            "No summed PF score; mathematical validity only for aligned tasks.",
            "No and Unclear differ; execution errors have no educational verdict.",
        ],
    }
    fixture_path = catalog_path.parent / "attempt_fixtures_v2_1_final/diagnostics.json"
    if fixture_path.exists():
        stats["calibration"]["constructed_attempt_fixtures"] = json.loads(fixture_path.read_text())
    coverage_path = catalog_path.parent / "solver_reference_coverage.json"
    if coverage_path.exists():
        stats["calibration"]["solver_reference_coverage"] = json.loads(coverage_path.read_text())
    stats["reliability_assessment"] = {
        "scope": "Computational calibration; no human ratings or independent-family replication.",
        "target_alignment": (
            "Useful diagnostic; partial-alignment boundaries and exact quotes need review."
        ),
        "mathematical_validity": (
            "Use primary verifier evidence; secondary missing-field correction is execution-tested "
            "but not independently validated on the reserved set."
        ),
        "prior_knowledge_accessibility": (
            "Promising for demonstrated existence of a start, not student difficulty or frequency."
        ),
        "familiar_approach_limits": (
            "Weakest task-level measure: solver coverage and review interpretation are material "
            "limitations. No describes examined methods only."
        ),
        "room_for_invention": (
            "Promising artifact judgment; reserved positive references cannot establish "
            "negative-case discrimination or student invention."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    grouping_path = catalog_path.parent / "comparison_groups.json"
    if grouping_path.exists():
        grouping = json.loads(grouping_path.read_text())
        result_by_judge = {
            judge: {item["case_id"]: item for item in items} for judge, items in selected.items()
        }
        stats["comparable_group_results"] = []
        for group in grouping["groups"]:
            entry = {**group, "judgments": {}}
            for judge in selected:
                rows = [
                    result_by_judge[judge][identifier]
                    for identifier in group["case_ids"]
                    if identifier in result_by_judge[judge]
                ]
                entry["judgments"][judge] = {
                    "evaluated_conditions": len(rows),
                    "measures": {measure: count_rows(rows, measure) for measure in MEASURES},
                }
            stats["comparable_group_results"].append(entry)
        stats["grouping_caveats"] = grouping.get("caveats", [])
    write(output / "findings.json", stats)
    with (output / "measure_values.svg").open("x") as stream:
        stream.write(value_plot(stats["by_judge"]))
    benchmark = benchmark_plot(stats.get("comparable_group_results", []))
    if benchmark is not None:
        with (output / "benchmark_v4_invention.svg").open("x") as stream:
            stream.write(benchmark)

    def escape(value):
        return html.escape(str(value))

    chunks = [
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>PF measurement campaign</title><style>"
        "body{font:17px/1.5 system-ui;color:#203040;max-width:1200px;"
        "margin:40px auto;padding:0 24px}"
        "h1,h2{line-height:1.2}table{border-collapse:collapse;width:100%;margin:20px 0}"
        "th,td{text-align:left;border-bottom:1px solid #d9e1e8;padding:8px;vertical-align:top}"
        "th{background:#f2f5f8}.note{color:#506070}.badge{background:#fff1d4;padding:8px 14px}"
        "details{margin:14px 0;border:1px solid #d9e1e8;padding:12px}summary{cursor:pointer}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.5 system-ui}"
        "input{font:inherit;padding:8px;width:75%}.hidden{display:none}"
        ".scroll{overflow:auto}</style><h1>PF task measurements</h1>"
        '<p class="badge">Computational pilot — not human-validated and not a student study.</p>',
        f"<p>Evaluated <strong>{len(selected['luna'])}</strong> distinct saved task/target/history "
        "conditions. Exact duplicates share assessment; occurrence provenance remains recorded. "
        "No historical task was regenerated.</p>",
        '<p class="note">Values are categorical. “Yes” for approach limits means a demonstrated '
        "target-related limitation, not a quality pass. Counts below include explicit skips; "
        "validity applies only to fully aligned tasks.</p><h2>Calibration</h2>",
    ]
    coverage = stats["saved_metadata_coverage"]
    chunks.append(
        f"<p>Saved target available: {coverage['target_available']} / {len(cases)}; "
        f"nonempty saved prerequisite history: {coverage['history_available']} / {len(cases)}. "
        f"{coverage['source_occurrences']} source occurrences include copies and mirrors, "
        "not that many independent trials. Missing inputs remain explicit unknowns/skips.</p>"
    )
    chunks.append(
        f"<p class='note'>{stats['unassessable_records']} source records have no usable "
        "student-task text. These include planned/pending slots, blocked outputs, mirrors "
        "and timeout events; they are not that many independent task failures. Their "
        "Individual provenance and status remain in catalog.json, "
        "outside the judgment denominator.</p>"
    )
    for label, diagnostic in [("Development", development), ("Reserved transfer", transfer)]:
        chunks.append(
            f"<h3>{label}</h3><p>Agreement with assistant-prepared provisional references, "
            "not human accuracy. Each task is reused across repeats; comparisons are "
            "not independent task observations.</p>"
        )
        chunks.append("<table><tr><th>Series / measure</th><th>Reference matches</th></tr>")
        for key, value in diagnostic.get("by_model_measure", {}).items():
            model, measure = key.split(":", 1)
            display = f"{model} · {NAMES[measure]}"
            chunks.append(
                f"<tr><td>{escape(display)}</td><td>{value['matches']} / "
                f"{value['comparisons']}</td></tr>"
            )
        chunks.append("</table>")
        chunks.append(
            "<p>Disagreement records are preserved in findings.json; a mismatch "
            "may reflect a judge error, a provisional reference or a genuine ambiguity.</p>"
        )
    chunks.append(
        "<p class='note'>The reserved run used the frozen prompts once. Afterward, "
        "a separately recorded runtime correction requests missing required validity "
        "within the existing call budget. It is not post-transfer prompt tuning, and "
        "the reserved run does not validate that correction.</p>"
    )
    chunks.append("<h3>What remains uncertain</h3><ul>")
    for measure in MEASURES:
        chunks.append(
            f"<li><strong>{NAMES[measure]}:</strong> "
            f"{escape(stats['reliability_assessment'][measure])}</li>"
        )
    chunks.append("</ul>")
    fixtures = stats["calibration"].get("constructed_attempt_fixtures")
    if fixtures:
        values = "; ".join(
            f"{escape(model)}: {item['matches']} of {item['usable']}"
            for model, item in fixtures["by_model"].items()
        )
        chunks.append(
            f"<p><strong>Constructed attempt diagnostic:</strong> {values}. "
            "Deliberately constructed examples, not observed student work.</p>"
        )
    coverage = stats["calibration"].get("solver_reference_coverage")
    if coverage:
        chunks.append(
            "<h3>Solver coverage of reference actions</h3>"
            "<p>Source-linked manual coding of mathematical actions, not name matching "
            "or human observations. Full / partial / not evidenced are separate.</p><ul>"
        )
        for solver, item in coverage["summary"]["per_solver"].items():
            counts = item["coverage_counts"]
            witnesses = item["reference_limit_witness_counts"]
            chunks.append(
                f"<li>{escape(solver)}: {counts['covered']} covered, {counts['partial']} partial, "
                f"{counts['not_evidenced']} not evidenced, of "
                f"{item['reference_approach_entries']} reference actions. Selected limitation "
                f"witness fully present: {witnesses.get('covered', 0)} / "
                f"{item['reference_positive_limit_cases']}.</li>"
            )
        chunks.append(
            "</ul><p>A judge cannot find a limitation in a method the solver never tried. "
            "That is not evidence that the task has no such opportunity. "
            "<a href='../solver_reference_coverage.json'>Exact quotations and provisional "
            "coverage mapping</a>.</p>"
        )
    chunks.append(
        "<h2>All evaluated conditions</h2>"
        "<img src='measure_values.svg' alt='Measured categorical verdict counts by judge series' "
        "style='width:100%;height:auto'><table><tr><th>Series</th><th>Measure</th>"
    )
    chunks.extend(f"<th>{escape(value)}</th>" for value in VALUES)
    chunks.append("</tr>")
    for judge, table in stats["by_judge"].items():
        for measure, counts in table.items():
            chunks.append(f"<tr><td>{escape(judge)}</td><td>{NAMES[measure]}</td>")
            chunks.extend(f"<td>{counts[value]}</td>" for value in VALUES)
            chunks.append("</tr>")
    chunks.append(
        "</table><h2>Run and method breakdown</h2><p>These are historical task "
        "source occurrences, including mirrors, not independent generated trials or unique "
        "topics. Compare only compatible saved experimental conditions.</p>"
    )
    if benchmark is not None:
        chunks.append(
            "<img src='benchmark_v4_invention.svg' "
            "alt='Historical v4 invention counts with original missing task slots preserved' "
            "style='width:100%;height:auto'>"
        )
    for group in stats.get("comparable_group_results", []):
        if group.get("record_role") != "generation_result":
            continue
        if not any(
            label in str(group.get("run_id", ""))
            for label in [
                "luna_v4",
                "main_30",
                "draft_first",
                "grounding_study",
            ]
        ):
            continue
        label = group["label"]
        chunks.append(
            f"<details><summary>{escape(label)}</summary>"
            f"<p>{escape(group.get('comparability_note', ''))}</p>"
            "<p>Unique evaluated input conditions; not a pooled causal comparison.</p>"
            "<table><tr><th>Series</th><th>Measure</th>"
        )
        chunks.extend(f"<th>{escape(value)}</th>" for value in VALUES)
        chunks.append("</tr>")
        for judge, row in group["judgments"].items():
            for measure, counts in row["measures"].items():
                chunks.append(f"<tr><td>{judge}</td><td>{NAMES[measure]}</td>")
                chunks.extend(f"<td>{counts[value]}</td>" for value in VALUES)
                chunks.append("</tr>")
        chunks.append("</table></details>")
    chunks.append("<details><summary>Complete source-occurrence inventory</summary>")
    for label, table in groups.items():
        chunks.append(
            f"<details><summary>{escape(label)}</summary><div class='scroll'><table>"
            "<tr><th>Series</th><th>Measure</th>"
        )
        chunks.extend(f"<th>{escape(value)}</th>" for value in VALUES)
        chunks.append("</tr>")
        for judge, row in table.items():
            for measure, counts in row["measures"].items():
                chunks.append(f"<tr><td>{judge}</td><td>{NAMES[measure]}</td>")
                chunks.extend(f"<td>{counts[value]}</td>" for value in VALUES)
                chunks.append("</tr>")
        chunks.append("</table></div></details>")
    chunks.append("</details>")
    chunks.append(
        "<h2>Task and evidence gallery</h2><input id='search' "
        "placeholder='Filter by task text, case id or verdict'>"
    )
    for identifier in sorted(cases):
        matching = [
            item
            for item in results
            if item["case_id"] == identifier
            and item["solver_model"] == "luna"
            and item["repeat"] == 0
        ]
        if not matching:
            continue
        case = cases[identifier]
        chunks.append(
            f"<details class='case'><summary>{escape(identifier)}</summary>"
            f"<h3>Student task</h3><pre>{escape(case['student_task'])}</pre>"
            f"<p><strong>Target:</strong> {escape(case['learning_target'])}</p>"
            f"<pre>Prerequisites: {escape(json.dumps(case['learner_context'], ensure_ascii=False))}"
            "</pre>"
        )
        for result in matching:
            chunks.append(f"<h3>{escape(result['judge_model'])}</h3>")
            for measure, row in result["measures"].items():
                evidence_text = escape(json.dumps(row["evidence"], ensure_ascii=False, indent=2))
                chunks.append(
                    f"<p><strong>{NAMES[measure]}: {escape(row['value'] or row['status'])}"
                    f"</strong></p><pre>{evidence_text}</pre>"
                )
        solver = matching[0]["solver"]
        chunks.append(
            "<details><summary>Frozen solver evidence</summary><pre>"
            + escape(json.dumps(solver.get("output"), ensure_ascii=False, indent=2))
            + "</pre></details></details>"
        )
    chunks.append(
        "<h2>Interpretation limits</h2><ul>"
        + "".join(f"<li>{escape(item)}</li>" for item in stats["limitations"])
        + "</ul><script>document.getElementById('search').addEventListener('input',e=>{"
        "const q=e.target.value.toLowerCase();document.querySelectorAll('.case').forEach("
        "el=>el.classList.toggle('hidden',!el.textContent.toLowerCase().includes(q)));"
        "});</script></html>"
    )
    with (output / "report.html").open("x") as stream:
        stream.write("\n".join(chunks))
    print(
        json.dumps(
            {
                key: stats[key]
                for key in [
                    "unique_input_conditions_evaluated",
                    "total_catalog_conditions",
                    "unassessable_records",
                ]
            },
            indent=2,
        )
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--transfer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.catalog, args.pack, args.full, args.development, args.transfer, args.output)


if __name__ == "__main__":
    main()
