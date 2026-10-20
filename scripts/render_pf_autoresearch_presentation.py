"""Render a focused deck on the two October 13 autoresearch questions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.render_pf_research_presentation import (  # noqa: E402
    ARMS,
    GROUNDING,
    MEASUREMENT,
    MEASUREMENT_ROWS,
    cards,
    flow,
    grouped_chart,
    load,
    slide,
    stacked_chart,
    table,
)

OUTPUT = ROOT / "docs/status/PF_AUTORESEARCH_PRESENTATION.html"
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
STYLE = """
html { scroll-snap-type: y proximity; }
body { margin: 0; font: 18px/1.5 system-ui, -apple-system, Segoe UI, sans-serif;
  color: #1d2733; background: #fff; }
.slide { min-height: 100vh; box-sizing: border-box; padding: 56px 8vw; max-width: 1180px;
  margin: 0 auto; scroll-snap-align: start; border-bottom: 1px solid #e3e9ef; }
.kicker { margin: 0 0 8px; color: #6b7a8a; font-size: 14px; letter-spacing: .08em; }
h2 { font-size: 34px; line-height: 1.2; margin: 0 0 20px; }
h3 { font-size: 22px; margin: 26px 0 10px; }
.lead { font-size: 23px; color: #2f3d4c; margin: 0 0 18px; }
.note { font-size: 15px; color: #596878; margin: 14px 0; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px; margin: 18px 0; }
.card { border: 1px solid #d3dce6; border-radius: 10px; padding: 16px 18px; background: #f8fafc; }
.card p { margin: 8px 0 0; font-size: 16px; }
.flow { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 20px 0; }
.node { border: 1px solid #b8c7d6; border-radius: 10px; padding: 12px 14px;
  background: #f5f8fb; min-width: 150px; font-size: 16px; }
.arrow { color: #6b7a8a; font-size: 22px; }
table { border-collapse: collapse; width: 100%; font-size: 16px; margin: 14px 0; }
th, td { border-bottom: 1px solid #dde4ec; padding: 9px 10px; text-align: left;
  vertical-align: top; }
th { background: #f5f8fb; font-weight: 600; }
.chart { width: 100%; max-width: 980px; height: auto; margin: 10px 0; }
.axis { font-size: 15px; fill: #24303d; }
.value { font-size: 14px; fill: #24303d; }
.records { margin-top: 28px; font-size: 14px; color: #596878; }
.records ul { margin: 6px 0 0 18px; padding: 0; }
a { color: #245f9b; }
@media print { .slide { min-height: auto; page-break-after: always; } }
"""


def main() -> None:
    grounding = load(GROUNDING)
    measurement = load(MEASUREMENT)

    high = measurement["same_task_high_score_findings"]
    if high["denominator"] != 41 or high["with_agreed_original_anchor_tension"] != 0:
        raise ValueError("High-score audit no longer matches the report")
    if high["with_agreed_additional_concern"] != 0 or measurement["catalog_tasks"] != 54:
        raise ValueError("High-score audit no longer matches the report")
    checklist = measurement["rates"]["fixed_checklist"]
    if (checklist["pass"], checklist["unknown"]) != (10, 44):
        raise ValueError("Checklist counts changed")
    judges = measurement["judge_status_distributions"]
    if judges["gpt41"]["preserved_discovery"] != {"supported": 54}:
        raise ValueError("Judge distribution changed")
    quotes = measurement["quote_fidelity"]
    measurement_rows = [
        (
            label,
            measurement["rates"][key]["pass"],
            measurement["rates"][key]["concern"],
            measurement["rates"][key]["unknown"],
        )
        for label, key in MEASUREMENT_ROWS
    ]

    grounding_values = []
    for label, key in GROUNDING_ROWS:
        counts = grounding["rates"][key]
        for arm, _, _ in ARMS:
            if counts[arm]["scheduled"] != 20:
                raise ValueError(f"Unexpected grounding denominator for {key}/{arm}")
        grounding_values.append((label, [counts[arm]["supported"] for arm, _, _ in ARMS]))
    primary = grounding["rates"]["fixed_checklist"]
    if [primary[arm]["supported"] for arm, _, _ in ARMS] != [0, 1, 0]:
        raise ValueError("Primary grounding outcome changed")
    if sum(primary[arm]["unknown"] for arm, _, _ in ARMS) != 59:
        raise ValueError("Primary grounding unknowns changed")
    mathematics = grounding["rates"]["mathematics"]
    if sum(mathematics[arm]["unknown"] for arm, _, _ in ARMS) != 53:
        raise ValueError("Mathematics unknowns changed")

    slides = [
        slide(
            1,
            "Two autoresearch questions",
            '<p class="lead">1. Do high model scores hide problems in the same tasks?<br>'
            "2. Does grounding generation in curriculum evidence help?</p>"
            '<p class="note">Results from 13 October 2026. Every judgment here is from a model '
            "or a rule, not from human raters or students.</p>",
        ),
        slide(
            2,
            "The answers at a glance",
            table(
                ["Question", "Short answer", "What it does not show"],
                [
                    [
                        "1. Do high scores conceal problems?",
                        "<strong>Not under our strict rule.</strong> No concern was confirmed by both "
                        "judges on any of the 41 tasks scoring 14–15.",
                        "It does not show the tasks are good. Judges were lenient and 44 of 54 "
                        "checklist outcomes stayed unknown.",
                    ],
                    [
                        "2. Does grounding help?",
                        "<strong>Partly, and not conclusively.</strong> Curriculum gave the most "
                        "support on several properties. Learning Commons gave mixed signals. The "
                        "primary outcome was unresolved.",
                        "It does not establish an educational benefit, or the absence of one. The "
                        "primary difference was a single task.",
                    ],
                ],
            ),
        ),
        slide(
            3,
            "Question 1: do high scores conceal problems?",
            '<p class="lead">We scored the same saved tasks twice: once with the original rating, '
            "once with new blinded reviews.</p>"
            + flow(
                [
                    "<strong>54 saved tasks</strong><br>original score kept aside",
                    "<strong>Two model reviews</strong><br>same blinded inputs",
                    "<strong>Exact quote</strong><br>needed for each concern",
                    "<strong>Agreement</strong><br>both judges flag the same property",
                ]
            )
            + cards(
                [
                    (
                        "Why we asked",
                        "Earlier reviews found faults in a different set of tasks. That did not "
                        "show whether the high scores on the same tasks were misleading.",
                    ),
                    (
                        "The rule",
                        "A concern counts only when both judges name the same property and quote "
                        "the task exactly. A single judge's flag stays a disputed candidate.",
                    ),
                ]
            ),
        ),
        slide(
            4,
            "Question 1 result: no confirmed concern among high scorers",
            '<p class="lead">Among 41 tasks scoring 14–15, zero concerns were confirmed by both '
            "judges.</p>"
            + "<h3>Support by checklist part, out of 54 tasks</h3>"
            + stacked_chart(measurement_rows, 54)
            + '<p class="note">Blue: supported. Red: agreed concern, none found. Grey: unknown or '
            "disputed. Unknown is not failure.</p>"
            + cards(
                [
                    ("Confirmed high-score concerns", "0 of 41"),
                    ("Single-judge flags left disputed", "16 tasks"),
                    ("Fully supported checklist", "10 of 54; 44 unknown"),
                ]
            ),
            (
                (
                    "Same-task report",
                    "../../experiments/results/pf_measurement_gap_study_20261013/"
                    "analysis_v1_3/report.html",
                ),
            ),
        ),
        slide(
            5,
            "Question 1 limits: why zero is not a clean pass",
            table(
                ["Check", "Result", "Meaning"],
                [
                    [
                        "Calibration controls, development set",
                        "GPT-4.1: 19 of 27. GPT-5.4: 26 of 27",
                        "Both judges miss some known cases; GPT-4.1 is more accepting",
                    ],
                    [
                        "Calibration controls, held-out set",
                        "GPT-4.1: 5 of 6. GPT-5.4: 6 of 6",
                        "Few cases; not enough to certify either judge",
                    ],
                    [
                        "Preserved discovery and useful contrast",
                        "GPT-4.1 supported both on all 54 tasks",
                        "A lenient judge can hide concerns through agreement",
                    ],
                    [
                        "Quoted evidence",
                        f"{quotes['verified_exact_quotes']:,} of "
                        f"{quotes['quoted_spans_checked']:,} spans match the task text",
                        "Confirms the quote exists, not that the reading is correct",
                    ],
                ],
            )
            + '<p class="note">The strict rule is conservative. It prevents false alarms, but it can '
            "also miss real problems. Human review of the disputed cases is the next evidence "
            "needed.</p>",
        ),
        slide(
            6,
            "Question 2: design of the grounding comparison",
            '<p class="lead">The learner’s prior learning stayed fixed; only the references '
            "available during design changed.</p>"
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
                        "Five Grade 8 specifications, four repeats per arm, 60 scheduled tasks",
                    ],
                    [
                        "Transfer status",
                        "Broader topics had been inspected earlier, so this is transfer evidence, "
                        "not untouched validation",
                    ],
                    [
                        "Learning Commons",
                        "The top three unfiltered results were kept; some were advanced or off-topic",
                    ],
                    [
                        "Stopping rule",
                        "No automatic tuning, and no failed attempt was replaced",
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
            7,
            "Question 2 result: supported outputs out of 20 per arm",
            "<h3>Supported by both auditors</h3>"
            + grouped_chart(grounding_values, ARMS, 20)
            + '<p class="note">Unknown is not failure. Mathematical support was unresolved for 53 '
            "of 60 tasks, so the primary outcome could rarely be decided.</p>"
            + table(
                ["Primary outcome: all five properties", "A · none", "B · curriculum", "C · both"],
                [["Supported", "0 of 20", "1 of 20", "0 of 20"]],
            ),
            (
                (
                    "Final comparison report",
                    "../../experiments/results/pf_grounding_study_20261013/"
                    "final_comparison/report.html",
                ),
            ),
        ),
        slide(
            8,
            "Question 2 interpretation and corrections",
            cards(
                [
                    (
                        "What the data support",
                        "Curriculum had the highest support on target relevance, distinct ideas and "
                        "useful contrast. Learning Commons had the highest choice support, but lower "
                        "target relevance, distinct ideas and useful contrast than curriculum.",
                    ),
                    (
                        "What they do not support",
                        "A general quality gain. The primary difference was one task, and 59 of 60 "
                        "primary outcomes were unresolved.",
                    ),
                ]
            )
            + "<h3>What went wrong before the result was trusted</h3>"
            + table(
                ["Step", "Finding"],
                [
                    [
                        "First audit",
                        "The evaluator dropped the taught-history input; 0 of 60 accessible starts "
                        "could be assessed. Kept as a failed record",
                    ],
                    [
                        "Repair",
                        "A tested adapter restored the same history; the 60 tasks were not regenerated",
                    ],
                    [
                        "Check",
                        "Six calibration judgments parsed; the corrected 120-judgment audit "
                        "contains the history and no condition labels",
                    ],
                ],
            ),
        ),
        slide(
            9,
            "What comes next for these two questions",
            table(
                ["Priority", "Action", "Why"],
                [
                    [
                        "1",
                        "Blinded human review of the disputed tasks",
                        "Model agreement cannot show whether a task is a real PF problem",
                    ],
                    [
                        "2",
                        "Domain-capable mathematical checking",
                        "53 of 60 grounding tasks were unresolved on mathematics",
                    ],
                    [
                        "3",
                        "No further automatic tuning",
                        "The protocol is closed; a new question needs a new authorized design",
                    ],
                ],
            )
            + '<p class="note">Thesis wording: report these as a bounded computational pilot. '
            "Neither question establishes classroom or student outcomes.</p>",
        ),
    ]

    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Autoresearch: high scores and grounding</title>"
        f"<style>{STYLE}</style><body>{''.join(slides)}</body></html>\n"
    )
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(slides)} slides")


if __name__ == "__main__":
    main()
