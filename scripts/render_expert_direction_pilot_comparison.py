"""Render the 12 saved expert-direction pilot tasks in four aligned columns."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments" / "results" / "pf_expert_direction_pilot_20260929"
OUTPUT = RUN / "side_by_side.html"
STRATL_PATH = ROOT / "data" / "pf_exercises" / "puech_macina_2025_stratl_full.yaml"

CONDITIONS = (
    ("V1", "Direct · no fixed hypotheses"),
    ("V2", "Direct · curator hypotheses"),
    ("V3", "Direct · Luna-inferred hypotheses"),
    ("PIPELINE", "Grounded multi-stage pipeline"),
)
CASES = (
    {
        "id": "kapur_average_speed",
        "title": "Average speed",
        "subtitle": "Kapur expert-task direction",
        "exercise_id": "puech2025_stratl_biking",
    },
    {
        "id": "loibl_variance",
        "title": "Spread and consistency",
        "subtitle": "Loibl expert-task direction",
        "exercise_id": "puech2025_stratl_consistency",
    },
    {
        "id": "kerrigan_fair_division",
        "title": "Fair division",
        "subtitle": "Kerrigan expert-task direction",
        "exercise_id": "puech2025_stratl_land_sharing",
    },
)


def render_body(text: str) -> str:
    blocks = []
    for block in text.split("\n\n"):
        lines = block.splitlines()
        if len(lines) >= 2 and lines[0].startswith("|") and re.fullmatch(r"[\s|:\-]+", lines[1]):
            rows = []
            for index, line in enumerate(lines):
                if index == 1:
                    continue
                tag = "th" if index == 0 else "td"
                cells = "".join(
                    f"<{tag}>{html.escape(cell.strip())}</{tag}>"
                    for cell in line.strip().strip("|").split("|")
                )
                rows.append(f"<tr>{cells}</tr>")
            blocks.append('<div class="table-wrap"><table>' + "".join(rows) + "</table></div>")
        elif lines and all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in lines)
            blocks.append(f"<ul>{items}</ul>")
        else:
            blocks.append('<p class="prose">' + html.escape(block) + "</p>")
    return "".join(blocks)


def render_card(case_id: str, condition: str, label: str) -> str:
    attempt_dir = RUN / case_id / "attempts" / condition / "001"
    attempt = json.loads((attempt_dir / "attempt.json").read_text(encoding="utf-8"))
    task = attempt["task"]
    judgment_path = attempt_dir / "judgment.json"
    judgment = (
        json.loads(judgment_path.read_text(encoding="utf-8")) if judgment_path.is_file() else {}
    )
    total = judgment.get("scores", {}).get("TOTAL")
    rating = f"Luna rubric: {total}/15" if isinstance(total, (int, float)) else "Not rated"
    task_content = (
        f"<h3>{html.escape(task['title'])}</h3>"
        + render_body(task["body"])
        + f'<div class="question"><strong>Student challenge</strong><p>{html.escape(task["question"])}</p></div>'
        if task["status"] == "ready"
        else "<p>Blocked: " + html.escape("; ".join(task.get("blocking_issues", []))) + "</p>"
    )
    source = f"{case_id}/attempts/{condition}/001/attempt.json"
    return (
        f'<article><div class="card-head"><span class="condition">{html.escape(label)}</span>'
        f'<span class="rating">{html.escape(rating)}</span></div>'
        f'<span class="status">{html.escape(attempt["status"])}</span>'
        f'{task_content}<a href="{html.escape(source, quote=True)}">Saved attempt JSON</a></article>'
    )


def load_stratl_exercises() -> tuple[dict, dict[str, dict]]:
    document = yaml.safe_load(STRATL_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("metadata"), dict):
        raise ValueError(f"Invalid StratL exercise file: {STRATL_PATH}")
    exercises = document.get("exercises")
    if not isinstance(exercises, list):
        raise ValueError(f"StratL exercise file has no exercise list: {STRATL_PATH}")
    by_id = {
        item["id"]: item
        for item in exercises
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return document["metadata"], by_id


def render_human_reference(case: dict[str, str], metadata: dict, exercises: dict[str, dict]) -> str:
    exercise = exercises.get(case["exercise_id"])
    if not isinstance(exercise, dict) or not isinstance(exercise.get("problem"), str):
        raise ValueError(f"Missing exercise text for {case['exercise_id']}")
    source = "../../../data/pf_exercises/puech_macina_2025_stratl_full.yaml"
    problem = render_body(exercise["problem"])
    original_source = exercise.get("source_reference", "Not specified")
    return (
        '<article class="human-reference"><div class="card-head">'
        '<span class="condition">Human PF exercise · CC BY 4.0</span></div>'
        f"<h3>{html.escape(str(exercise.get('topic', case['title'])))}</h3>"
        f'<p class="exercise-id">Exercise ID: <code>{html.escape(case["exercise_id"])}</code></p>'
        f'<div class="human-task">{problem}</div>'
        f'<p class="source-note">Source task attribution: {html.escape(str(original_source))}. '
        f"{html.escape(str(metadata['source']))}. "
        f'License: <a href="https://creativecommons.org/licenses/by/4.0/" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(str(metadata["license"]))}</a>.'
        " Task text reproduced from the licensed dataset.</p>"
        f'<a href="{html.escape(source, quote=True)}">Dataset record</a>'
        '<a class="doi" href="https://arxiv.org/abs/2410.03781" target="_blank" '
        'rel="noopener noreferrer">Dataset paper</a></article>'
    )


def render() -> str:
    metadata, exercises = load_stratl_exercises()
    sections = []
    for case in CASES:
        cards = "".join(
            render_card(case["id"], condition, label) for condition, label in CONDITIONS
        )
        sections.append(
            f"<section><header><p>{html.escape(case['subtitle'])}</p>"
            f'<h2>{html.escape(case["title"])}</h2></header><div class="grid">'
            + render_human_reference(case, metadata, exercises)
            + cards
            + "</div></section>"
        )
    return (
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expert-direction PF pilot: side-by-side tasks</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f2;color:#24352c;
font:15px/1.55 system-ui,sans-serif}
.intro{padding:24px 32px;background:#173e31;color:#fff}
.intro h1{margin:0 0 8px;font-size:27px}.intro p{margin:5px 0}
main{padding:22px;max-width:2200px;margin:auto}
section{margin:0 0 28px}section>header{margin:0 0 12px}
section>header p{margin:0;color:#60736a;font-size:13px}
h2{margin:2px 0 12px;font-size:22px}
.grid{display:grid;grid-template-columns:repeat(5,minmax(310px,1fr));gap:14px;
overflow-x:auto;padding-bottom:8px}
article{min-width:310px;background:#fff;border:1px solid #d5ded7;border-radius:10px;
padding:16px;box-shadow:0 1px 2px #20302012}
.human-reference{background:#fffaf0;border-color:#d7bd82}
.human-reference .condition{color:#795817}
.exercise-id{font-size:13px;color:#53675a}
.source-note{font-size:12px;color:#647167;background:#f2f4f0;padding:9px;border-radius:6px}
.human-task{margin:10px 0}
.human-reference a{display:block;margin-top:8px}
.human-reference .doi{font-size:12px}
.card-head{display:flex;justify-content:space-between;gap:8px;align-items:start}
.condition{font-weight:700;color:#315a43}.rating{font-size:11px;color:#687a6e;
white-space:nowrap}.status{display:inline-block;margin:8px 0;padding:2px 7px;
border-radius:12px;background:#e7f1e7;color:#345c3d;font-size:11px;text-transform:uppercase}
h3{font-size:19px;line-height:1.3;margin:7px 0 14px}
.prose{white-space:pre-wrap}.question{margin:14px 0;padding:11px 12px;
background:#edf3ea;border-left:3px solid #7a9a6b}
.question p{margin:5px 0 0;white-space:pre-wrap}
ul{padding-left:22px}.table-wrap{overflow:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{padding:5px 7px;text-align:left;border:1px solid #dce4dd}
th{background:#edf2ed}article a{font-size:12px;color:#356548}
footer{padding:18px 0;color:#5d6e63;font-size:12px}
@media(max-width:700px){.intro{padding:18px}.intro h1{font-size:22px}
main{padding:14px}.grid{grid-template-columns:repeat(5,minmax(280px,82vw))}}
</style></head><body><div class="intro">
<h1>Generated PF tasks, side by side</h1>
<p>Each row starts with a full, attributed CC BY 4.0 human PF exercise, followed by the four generated versions.</p>
<p>12 saved tasks · one attempt per version and direction · ratings are Luna model judgments, not student evidence.</p>
</div><main>"""
        + "".join(sections)
        + """<footer>Generated task wording and data are rendered from the saved attempt JSON.
The human exercise panels reproduce the corresponding text from the CC BY 4.0 StratL dataset,
with attribution and links. The Loibl-direction task is the dataset's related consistency
invention task (source reference: Kapur, 2015), not the exact Loibl &amp; Rummel exercise.
V2 used curator-authored hypotheses informed by the expert designs; it is not a blind
holdout condition. Horizontal scrolling may be needed to compare all five cards.
</footer></main></body></html>
"""
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists: {OUTPUT}")
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"Rendered {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
