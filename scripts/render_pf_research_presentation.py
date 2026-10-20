"""Render a slide deck for the PF research record from saved result summaries."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/status/PF_RESEARCH_PRESENTATION.html"
GROUNDING = ROOT / "experiments/results/pf_grounding_study_20261013/final_comparison/summary.json"
MEASUREMENT = (
    ROOT / "experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/summary.json"
)

SUPPORTED = "#2f6f9f"
CONCERN = "#b5523b"
UNKNOWN = "#d5dde5"
ARMS = (
    ("A", "No added references", "#8a97a6"),
    ("B", "Curriculum", "#2f6f9f"),
    ("C", "Curriculum + Learning Commons", "#4f9d69"),
)
GROUNDING_ROWS = (
    ("Target relevance", "target_relevance"),
    ("Accessible start", "accessible_start"),
    ("Consequential choice", "consequential_choice"),
    ("Distinct idea opportunities", "distinct_mathematical_ideas"),
    ("Discovery preserved", "preserved_discovery"),
    ("Useful prior contrast", "useful_prior_contrast"),
    ("Mathematical support", "mathematics"),
    ("All five together", "fixed_checklist"),
)
MEASUREMENT_ROWS = (
    ("Target relevance", "target_relevance"),
    ("Accessible start", "accessible_start"),
    ("Task specification", "task_specification"),
    ("Discovery preserved", "preserved_discovery"),
    ("Consequential choice", "consequential_choice"),
    ("Distinct idea opportunities", "distinct_mathematical_ideas"),
    ("Useful prior contrast", "useful_prior_contrast"),
    ("Mathematical support", "mathematics"),
    ("All five checklist parts", "fixed_checklist"),
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stacked_chart(rows: list[tuple[str, int, int, int]], total: int) -> str:
    label_width, bar_width, row_height = 300, 470, 34
    width = label_width + bar_width + 110
    height = row_height * len(rows) + 12
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
        'aria-label="Audit outcomes per property">'
    ]
    for index, (label, supported, concern, unknown) in enumerate(rows):
        if supported + concern + unknown != total:
            raise ValueError(f"{label} does not sum to {total}")
        y = 8 + index * row_height
        parts.append(f'<text x="0" y="{y + 19}" class="axis">{esc(label)}</text>')
        x = label_width
        for count, color in ((supported, SUPPORTED), (concern, CONCERN), (unknown, UNKNOWN)):
            segment = bar_width * count / total
            if segment:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y + 4}" width="{segment:.1f}" height="22" '
                    f'fill="{color}"/>'
                )
            x += segment
        parts.append(
            f'<text x="{label_width + bar_width + 10}" y="{y + 20}" class="value">'
            f"{supported}/{total}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def grouped_chart(rows: list[tuple[str, list[int]]], series: tuple, maximum: int) -> str:
    label_width, bar_width, bar_height, gap = 300, 400, 15, 14
    group_height = len(series) * bar_height + gap
    width = label_width + bar_width + 80
    height = 34 + group_height * len(rows)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
        'aria-label="Supported outputs by condition">'
    ]
    x = 0
    for _, name, color in series:
        parts.append(f'<rect x="{x}" y="4" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{x + 18}" y="15" class="axis">{esc(name)}</text>')
        x += 34 + 8 * len(name)
    for index, (label, values) in enumerate(rows):
        base = 34 + index * group_height
        parts.append(
            f'<text x="0" y="{base + len(series) * bar_height / 2 + 4:.1f}" '
            f'class="axis">{esc(label)}</text>'
        )
        for offset, ((_, _, color), value) in enumerate(zip(series, values)):
            y = base + offset * bar_height
            size = bar_width * value / maximum
            parts.append(
                f'<rect x="{label_width}" y="{y}" width="{size:.1f}" '
                f'height="{bar_height - 3}" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{label_width + size + 6:.1f}" y="{y + bar_height - 3}" '
                f'class="value">{value}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def bar_chart(rows: list[tuple[str, float, str, str]], maximum: float) -> str:
    label_width, bar_width, row_height = 300, 420, 40
    width = label_width + bar_width + 210
    height = row_height * len(rows) + 10
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
        'aria-label="Single measure comparison">'
    ]
    for index, (label, value, color, note) in enumerate(rows):
        y = 8 + index * row_height
        size = bar_width * value / maximum
        parts.append(f'<text x="0" y="{y + 20}" class="axis">{esc(label)}</text>')
        parts.append(
            f'<rect x="{label_width}" y="{y + 4}" width="{size:.1f}" height="22" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{label_width + size + 8:.1f}" y="{y + 20}" class="value">{esc(note)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def flow(steps: list[str]) -> str:
    pieces = []
    for index, step in enumerate(steps):
        pieces.append(f'<div class="node">{step}</div>')
        if index < len(steps) - 1:
            pieces.append('<div class="arrow">→</div>')
    return f'<div class="flow">{"".join(pieces)}</div>'


def cards(items: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<div class="card"><strong>{esc(title)}</strong><p>{text}</p></div>'
        for title, text in items
    )
    return f'<div class="cards">{body}</div>'


def slide(number: int, title: str, body: str, records: tuple[tuple[str, str], ...] = ()) -> str:
    sources = ""
    if records:
        items = "".join(
            f'<li><a href="{esc(link)}">{esc(label)}</a></li>' for label, link in records
        )
        sources = f'<footer class="records"><strong>Records</strong><ul>{items}</ul></footer>'
    return (
        f'<section class="slide" id="s{number}"><p class="kicker">{number:02d}</p>'
        f"<h2>{esc(title)}</h2>{body}{sources}</section>"
    )


def main() -> None:
    grounding = load(GROUNDING)
    measurement = load(MEASUREMENT)

    grounding_values = []
    for label, key in GROUNDING_ROWS:
        counts = grounding["rates"][key]
        for arm, _, _ in ARMS:
            arm_counts = counts[arm]
            total = arm_counts["supported"] + arm_counts["concern"] + arm_counts["unknown"]
            if total != 20 or arm_counts["scheduled"] != 20:
                raise ValueError(f"Unexpected grounding denominator for {key}/{arm}")
        grounding_values.append((label, [counts[arm]["supported"] for arm, _, _ in ARMS]))

    primary = grounding["rates"]["fixed_checklist"]
    primary_supported = sum(primary[arm]["supported"] for arm, _, _ in ARMS)
    primary_unknown = sum(primary[arm]["unknown"] for arm, _, _ in ARMS)
    if primary_supported != 1 or primary_unknown != 59:
        raise ValueError("The grounding primary outcome no longer matches the report")

    measurement_rows = []
    for label, key in MEASUREMENT_ROWS:
        counts = measurement["rates"][key]
        measurement_rows.append((label, counts["pass"], counts["concern"], counts["unknown"]))
    high = measurement["same_task_high_score_findings"]
    if (
        high["denominator"] != 41
        or high["with_agreed_original_anchor_tension"] != 0
        or high["with_agreed_additional_concern"] != 0
    ):
        raise ValueError("High-score audit no longer matches the report")
    if measurement["catalog_tasks"] != 54:
        raise ValueError("Measurement denominator changed")

    slides = [
        slide(
            1,
            "Can LLMs design Productive Failure exercises?",
            '<p class="lead">What we did, why we did it, what we found, and what remains. '
            "Status as of 13 October 2026.</p>"
            '<p class="note">Productive Failure (PF): students attempt an ill-structured '
            "problem before they are taught the method. This deck summarizes the work; exact "
            "protocols and caveats are in the linked records.</p>",
        ),
        slide(
            2,
            "Why this question matters",
            '<p class="lead">A fluent word problem is not yet a PF exercise.</p>'
            + cards(
                [
                    (
                        "What PF needs",
                        "Students can start from what they know, several sensible approaches "
                        "are possible, some approaches fail usefully, and the key idea stays "
                        "for them to find.",
                    ),
                    (
                        "What we feared",
                        "An LLM can write a polished story that reduces to one procedure, or "
                        "announces the answer, while looking ready for a classroom.",
                    ),
                    (
                        "What we needed",
                        "Evidence that separates real PF properties from fluency, plus honest "
                        "limits on what model judges can show.",
                    ),
                ]
            ),
            (("Thesis overview", "../status/THESIS_OVERVIEW.md"),),
        ),
        slide(
            3,
            "Five research questions and where they stand",
            table(
                ["Question", "Current answer"],
                [
                    [
                        "RQ1 Do well-rated LLM tasks contain the PF mechanism?",
                        "<strong>Inconclusive.</strong> Model reviews raised candidate flaws, "
                        "but the paired audit did not corroborate them.",
                    ],
                    [
                        "RQ2 Can LLMs anticipate what students will bring?",
                        "<strong>Partly.</strong> Mistake pathways trade realism against "
                        "variety; generated method lists recalled 20–27% of frequent real errors.",
                    ],
                    [
                        "RQ3 Does explicit decomposition beat strong direct prompting?",
                        "<strong>Not in general.</strong> Equal results in the expert-direction "
                        "comparison, with about nine times the requests.",
                    ],
                    [
                        "RQ4 Can simulated students improve task design?",
                        "<strong>Diagnostic only.</strong> Feedback did not reliably beat strong "
                        "review.",
                    ],
                    [
                        "RQ5 Does curriculum grounding improve PF tasks?",
                        "<strong>Pilot inconclusive.</strong> Component gains appeared, but the "
                        "primary outcome was almost entirely unresolved.",
                    ],
                ],
            )
            + '<p class="note">Each answer reflects the strength of evidence reached. Model '
            "judgments and simulated attempts are not human ratings or student outcomes.</p>",
            (("Thesis overview, research questions", "../status/THESIS_OVERVIEW.md"),),
        ),
        slide(
            4,
            "How the work unfolded",
            '<p class="lead">Each phase asked a question raised by the previous result.</p>'
            + flow(
                [
                    "<strong>Diagnose</strong><br>Rahimi-style tasks",
                    "<strong>Anticipate</strong><br>mistakes and prior methods",
                    "<strong>Design</strong><br>pipeline and direct comparison",
                    "<strong>Simulate</strong><br>solution-blind learners",
                    "<strong>Audit and ground</strong><br>same tasks; curriculum evidence",
                ]
            )
            + '<p class="note">The overview contains eight narrative steps. The last phase '
            "combines the October 13 check of the same tasks with the three-arm grounding "
            "study.</p>",
            (("Canonical PF record", "../pf-generation/PF_PIPELINE.md"),),
        ),
        slide(
            5,
            "Good ratings did not show what was inside",
            cards(
                [
                    (
                        "Early LLM judge",
                        "Gave <strong>6 of 9</strong> development tasks the maximum 15/15 on "
                        "Rahimi's five-part rubric.",
                    ),
                    (
                        "Separate blind AI review",
                        "Put multiple representations and solutions at the floor, "
                        "<strong>1 of 3</strong>, across 21 tasks, and listed concrete faults.",
                    ),
                ]
            )
            + "<h3>Faults named in the review</h3>"
            + table(
                ["Fault", "Example"],
                [
                    [
                        "The trap is not real",
                        "78:52:65 reduces to 6:4:5, so the “wrong” split works",
                    ],
                    [
                        "The wrong method is valid",
                        "Same-size containers make the absolute comparison correct",
                    ],
                    [
                        "The story announces the mistake",
                        "A character says “add 1 to both sides”",
                    ],
                    ["Numbers conflict", "14 gallons of input for a 12-gallon mixture"],
                    ["Only one route", "Every path ends in the same calculation"],
                ],
            )
            + '<p class="note">These came from two different task sets and two different AI '
            "raters. They are leads for checking, not proof.</p>",
            (
                ("Early judge, 9 tasks", "../../notebooks/05_pf_evaluation_round1.ipynb"),
                (
                    "Review pool, 21 tasks",
                    "../../experiments/results/agent_scores_round1_deepseek.csv",
                ),
            ),
        ),
        slide(
            6,
            "Anticipating what students will try",
            '<p class="lead">Mistake pathways were realistic or varied, rarely both.</p>'
            + table(
                ["Approach", "Match with real Eedi answers", "Plausibility (0–2)",
                 "Distinct reasoning paths"],
                [
                    ["Expert-direct baseline", "0.236", "1.46", "0.747"],
                    ["Retrieved similar questions", "<strong>0.353</strong>", "1.40", "0.776"],
                    ["Named misconception prompts", "0.167", "1.22", "<strong>0.855</strong>"],
                ],
            )
            + '<p class="note">Higher is better in each column, but these are model-scored '
            "signals over 19,800 distractors. Diversity is measured only where enough usable "
            "paths exist.</p>"
            + "<h3>Generated prior-method lists</h3>"
            + cards(
                [
                    (
                        "Plausible but narrow",
                        "Judged plausible (about 1.85/2), yet they recovered only 20–27% of "
                        "frequent real errors.",
                    ),
                    (
                        "Wrong kind of object",
                        "They listed error types, while PF needs taught tools that are correct "
                        "but insufficient.",
                    ),
                ]
            ),
            (("MCQ evaluation overview", "../mcq/MCQ_EVALUATION_OVERVIEW.md"),),
        ),
        slide(
            7,
            "A more structured pipeline did not beat strong direct prompting",
            "<h3>Rahimi's setting: mean rating out of 15</h3>"
            + bar_chart(
                [
                    ("First run · direct prompt", 14.43, "#8a97a6", "14.43 · 30 of 30 produced"),
                    ("First run · pipeline", 10.47, "#b5523b", "10.47 · 17 of 30 produced"),
                    ("Rerun · direct prompt", 14.40, "#8a97a6", "14.40 · 30 of 30 produced"),
                    ("Rerun · pipeline", 11.82, "#b5523b", "11.82 · 22 of 30 produced"),
                ],
                15,
            )
            + "<h3>Expert design directions: direct versus pipeline</h3>"
            + table(
                ["Measure", "Direct", "Pipeline"],
                [
                    ["Tasks produced", "9 of 9", "9 of 9"],
                    ["Real consequential choice", "6 of 9", "6 of 9"],
                    ["All requirements at once", "5 of 9", "5 of 9"],
                    ["Model requests", "9", "78"],
                ],
            )
            + '<p class="note">The direct prompt was rated higher in Rahimi’s setting. The judge '
            "gave every direct task the top variety score, so ratings could not separate the "
            "methods.</p>",
            (
                (
                    "Rahimi-setting benchmark",
                    "../../experiments/results/pf_paper_benchmark/20260923_luna_v4/comparison.html",
                ),
                (
                    "Expert-direction comparison",
                    "../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/side_by_side.html",
                ),
            ),
        ),
        slide(
            8,
            "Simulated students: steerable, but narrower than real students",
            "<h3>Assigned wrong rule followed by GPT-4.1</h3>"
            + bar_chart(
                [
                    ("Options hidden", 94, "#8a97a6", "94%"),
                    ("Options visible", 68, "#b5523b", "68%"),
                ],
                100,
            )
            + '<p class="note">Prescribing an error makes the result circular, so we built '
            "learners that see only the task and their prior learning.</p>"
            + table(
                ["Feedback test", "Original", "Review only", "Review + simulated feedback"],
                [
                    ["Raw attempts", "5 of 6", "6 of 6", "4 of 6 (worse)"],
                    [
                        "Path-coverage feedback",
                        "2 of 3",
                        "2 of 3",
                        "3 of 3 (predefined gain was +2)",
                    ],
                ],
            )
            + '<p class="note">Designed route reached on fair division: 0 of 8 GPT-4.1 learner '
            "attempts versus 4 of 4 GPT-5.4 attempts. Reachability depends on the simulator.</p>",
            (
                (
                    "Learning-record study",
                    "../../experiments/results/pf_learning_record_20261011/learning_record.html",
                ),
                (
                    "Final path-coverage report",
                    "../../experiments/results/pf_path_coverage_final_20261012/final_report.html",
                ),
            ),
        ),
        slide(
            9,
            "New audit: do high scores hide shared problems?",
            '<p class="lead">Among 41 tasks scoring 14–15, no concern was corroborated by both '
            "judges.</p>"
            + flow(
                [
                    "<strong>54 saved tasks</strong><br>original score kept aside",
                    "<strong>Two model reviews</strong><br>same blinded inputs",
                    "<strong>Exact quote required</strong><br>for each concern",
                    "<strong>Agreement</strong><br>both judges must agree",
                ]
            )
            + "<h3>Support by checklist part, out of 54 tasks</h3>"
            + stacked_chart(measurement_rows, 54)
            + '<p class="note">Blue: supported. Red: agreed concern (none). Grey: unknown or '
            "disputed; unknown is not failure. These are model reviews, not human ratings.</p>"
            + cards(
                [
                    (
                        "What the null means",
                        "Sixteen single-judge concerns remain disputed candidates; the strict "
                        "rule did not confirm a broad hidden-flaw pattern.",
                    ),
                    (
                        "What it does not mean",
                        "It does not validate the tasks. One judge was lenient, controls were "
                        "uneven, and 44 of 54 checklist outcomes stayed unknown.",
                    ),
                ]
            ),
            (
                (
                    "Same-task report",
                    "../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/report.html",
                ),
            ),
        ),
        slide(
            10,
            "Grounding study: change only the references available",
            '<p class="lead">The learner’s prior learning stayed fixed; only design-time '
            "references changed.</p>"
            + flow(
                [
                    "<strong>Fixed learner packet</strong><br>same taught history",
                    "<strong>A · none</strong><br>20 tasks",
                    "<strong>B · curriculum</strong><br>20 tasks",
                    "<strong>C · curriculum + Learning Commons</strong><br>20 tasks",
                    "<strong>Blinded audit</strong><br>same two model series",
                ]
            )
            + table(
                ["Design choice", "What we did"],
                [
                    [
                        "Tasks",
                        "Five Grade 8 specifications, four repeats per condition, "
                        "60 scheduled tasks",
                    ],
                    [
                        "Transfer status",
                        "Broader topics had been inspected earlier, so this is transfer "
                        "evidence, not untouched validation",
                    ],
                    [
                        "Learning Commons",
                        "Top three unfiltered results were kept; some were advanced or off-topic",
                    ],
                    [
                        "Stopping rule",
                        "No automatic tuning and no quality-based replacement of failed attempts",
                    ],
                ],
            ),
            (
                (
                    "Grounding study configuration",
                    "../../experiments/configs/pf_overnight_research_20261013.json",
                ),
            ),
        ),
        slide(
            11,
            "Grounding result: directional gains, unresolved primary outcome",
            "<h3>Supported outputs out of 20 per condition</h3>"
            + grouped_chart(grounding_values, ARMS, 20)
            + '<p class="note">Supported means both model auditors agreed and quoted the task. '
            "Unknown is not a failure; mathematical support was unresolved for 53 of 60 "
            "tasks.</p>"
            + cards(
                [
                    (
                        "Curriculum",
                        "Higher support on target relevance and useful contrast. One task had "
                        "all five properties supported, versus none without references; this is "
                        "not evidence of a general gain.",
                    ),
                    (
                        "Learning Commons",
                        "Choice support rose slightly, but target relevance, distinct ideas and "
                        "useful contrast fell. No consistent incremental benefit.",
                    ),
                ]
            ),
            (
                (
                    "Final comparison report",
                    "../../experiments/results/pf_grounding_study_20261013/final_comparison/report.html",
                ),
            ),
        ),
        slide(
            12,
            "What went wrong, and how it was handled",
            table(
                ["Problem", "Effect", "Handling"],
                [
                    [
                        "Evaluator input dropped the taught history",
                        "The first 120-judgment audit could not assess accessible starts",
                        "Preserved; tested adapter; six calibration judgments; corrected audit of "
                        "the same tasks",
                    ],
                    [
                        "One malformed field discarded a whole audit",
                        "Valid findings were lost",
                        "Field-level validation with explicit errors; reparsing made no new calls",
                    ],
                    [
                        "Export helper rejected outputs outside the repository",
                        "Integration test failure",
                        "Absolute path recorded; no experimental result changed",
                    ],
                    [
                        "Research agents sent progress messages into the main chat",
                        "Could start extra turns",
                        "Channel stopped; agents return results directly",
                    ],
                    [
                        "Unattributed documentation edits and a deployment-failed alternate run",
                        "Competing records",
                        "Not reverted; canonical record names only the completed campaign",
                    ],
                ],
            ),
            (("Process notes in the PF record", "../pf-generation/PF_PIPELINE.md"),),
        ),
        slide(
            13,
            "What we can and cannot claim",
            flow(
                [
                    "<strong>Software tests</strong><br>reached",
                    "<strong>Exact arithmetic</strong><br>partly: 196 verified, 253 unknown",
                    "<strong>Model judgments</strong><br>reached, with leniency",
                    "<strong>Simulated attempts</strong><br>reached, diagnostic only",
                    "<strong>Blinded human ratings</strong><br>not yet",
                    "<strong>Real students and learning</strong><br>not yet",
                ]
            )
            + table(
                ["Claim", "Supported now?"],
                [
                    [
                        "Rating scores can look high while the same-task model audit finds no "
                        "shared concern",
                        "Yes, bounded to this sample and rule",
                    ],
                    [
                        "Curriculum evidence improves generated PF tasks",
                        "No; directional signals only",
                    ],
                    [
                        "Learning Commons improves tasks beyond curriculum",
                        "No consistent benefit detected",
                    ],
                    [
                        "Simulated learners predict real student behaviour",
                        "No; narrower and steerable",
                    ],
                    ["Generated tasks help real students learn", "Not tested"],
                ],
            ),
            (("Evidence boundaries", "../status/THESIS_STATUS.md"),),
        ),
        slide(
            14,
            "Campaign accounting and deliverables",
            table(
                ["Item", "Count"],
                [
                    ["Model requests in the canonical campaign", "861"],
                    ["Reported tokens", "5,336,367"],
                    ["Grounding tasks generated", "60 main + 3 calibration"],
                    ["Same-task judgments", "136 measurement + 246 grounding audit"],
                    ["Focused campaign tests", "81 passed, with Ruff and compilation"],
                ],
            )
            + '<p class="note">Currency cost is unavailable because no verified pricing was '
            "supplied. The failed alternate deployment is excluded from these totals.</p>",
            (
                (
                    "Generation summary",
                    "../../experiments/results/pf_grounding_study_20261013/generation_summary.json",
                ),
            ),
        ),
        slide(
            15,
            "Next steps",
            table(
                ["Priority", "Action", "Why"],
                [
                    [
                        "1",
                        "Blinded human adjudication of disputed tasks",
                        "Turns model disagreements into evidence a teacher could interpret",
                    ],
                    [
                        "2",
                        "Domain-capable mathematical checking",
                        "Most unknowns came from mathematics the checker could not parse",
                    ],
                    [
                        "3",
                        "Write the discussion and conclusion from these findings",
                        "The thesis needs a clear claim boundary",
                    ],
                    [
                        "4",
                        "Install LaTeX and build the PDF",
                        "The current build is blocked by missing latexmk",
                    ],
                    [
                        "5",
                        "Finish reference checks",
                        "Several background citations still need verification",
                    ],
                ],
            )
            + '<p class="note">The simulation campaign and the grounding comparison stop here. '
            "Any further generation tuning needs a new authorized protocol.</p>",
            (("Thesis status", "../status/THESIS_STATUS.md"),),
        ),
    ]

    page = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PF exercises with LLMs: research presentation</title>
<style>
html {{ scroll-snap-type: y proximity; }}
body {{ margin: 0; font: 18px/1.5 system-ui, -apple-system, Segoe UI, sans-serif;
  color: #1d2733; background: #fff; }}
.slide {{ min-height: 100vh; box-sizing: border-box; padding: 56px 8vw; max-width: 1180px;
  margin: 0 auto; scroll-snap-align: start; border-bottom: 1px solid #e3e9ef; }}
.kicker {{ margin: 0 0 8px; color: #6b7a8a; font-size: 14px; letter-spacing: .08em; }}
h2 {{ font-size: 34px; line-height: 1.2; margin: 0 0 20px; }}
h3 {{ font-size: 22px; margin: 26px 0 10px; }}
.lead {{ font-size: 23px; color: #2f3d4c; margin: 0 0 18px; }}
.note {{ font-size: 15px; color: #596878; margin: 14px 0; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px; margin: 18px 0; }}
.card {{ border: 1px solid #d3dce6; border-radius: 10px; padding: 16px 18px; background: #f8fafc; }}
.card p {{ margin: 8px 0 0; font-size: 16px; }}
.flow {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 20px 0; }}
.node {{ border: 1px solid #b8c7d6; border-radius: 10px; padding: 12px 14px;
  background: #f5f8fb; min-width: 150px; font-size: 16px; }}
.arrow {{ color: #6b7a8a; font-size: 22px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 16px; margin: 14px 0; }}
th, td {{ border-bottom: 1px solid #dde4ec; padding: 9px 10px; text-align: left;
  vertical-align: top; }}
th {{ background: #f5f8fb; font-weight: 600; }}
.chart {{ width: 100%; max-width: 980px; height: auto; margin: 10px 0; }}
.axis {{ font-size: 15px; fill: #24303d; }}
.value {{ font-size: 14px; fill: #24303d; }}
.records {{ margin-top: 28px; font-size: 14px; color: #596878; }}
.records ul {{ margin: 6px 0 0 18px; padding: 0; }}
a {{ color: #245f9b; }}
@media print {{ .slide {{ min-height: auto; page-break-after: always; }} }}
</style>
<body>
{"".join(slides)}
</body>
</html>
"""
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(slides)} slides")


if __name__ == "__main__":
    main()
