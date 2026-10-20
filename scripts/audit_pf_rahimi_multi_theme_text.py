"""Text-pattern audit of the multi-theme Rahimi run: what the Table 1 rubric does not score.

Reads saved ready tasks and judgments only; makes no model calls. Every flag is a
regular-expression heuristic over student-facing text, so counts are approximate
and examples must be read before a claim is made.
"""

from __future__ import annotations

import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/results/pf_rahimi_multi_theme_20261013/main_30"
OUT = RUN / "text_pattern_audit.json"

PATTERNS = {
    "names_method_list": (
        "question",
        r"for example|such as|e\.g\.|possible representations|you may use|you could use",
    ),
    "hint": ("text", r"\bhint\b"),
    "addresses_pedagogy_to_student": (
        "text",
        r"you have (recently |just )?(learned|practiced|worked|studied)"
        r"|have not (yet )?been taught|not yet teaching|skills you (have )?(just )?learned"
        r"|use (what|your prior) (you know|knowledge)",
    ),
    "demands_multiple_methods": (
        "question",
        r"at least (two|2|one) (different )?(types of )?"
        r"(representation|method|way|approach|measure|strateg)"
        r"|more than one (method|way|approach)|different (ways|methods|strategies|approaches)",
    ),
}
TARGET_NAMED = {
    "sports_basketball_ratio": ("question", r"proportional"),
    "music_compare_distributions": (
        "question",
        r"measure(s)? of (center|variability)|\bIQR\b|mean absolute deviation|\bMAD\b",
    ),
    "garden_composite_area": ("text", r"decompos|break (it|the|each|them)|split|separately"),
}
SAMPLE_FRAMING = r"random(ly)? (sample|select|pick|chose)|sample of|sampled"
SUBPART = r"(?m)^\s*(?:\(?\d+[\).]|\([a-e]\)|[a-e]\)|- )"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flags(task: dict, cell: str) -> dict:
    fields = {"question": task["question"], "text": task["body"] + "\n" + task["question"]}
    result = {
        "words": len(fields["text"].split()),
        "question_subparts": len(re.findall(SUBPART, task["question"])),
    }
    for name, (field, pattern) in PATTERNS.items():
        result[name] = bool(re.search(pattern, fields[field], re.I))
    if cell in TARGET_NAMED:
        field, pattern = TARGET_NAMED[cell]
        result["names_target_or_method"] = bool(re.search(pattern, fields[field], re.I))
    if cell == "music_compare_distributions":
        result["random_sample_framing"] = bool(re.search(SAMPLE_FRAMING, fields["text"], re.I))
    return result


def main() -> None:
    scores = read(RUN / "scores.json")["tasks"]
    concerns: dict[str, int] = defaultdict(int)
    for path in (RUN / "judgments").rglob("*.json"):
        record = read(path)
        if record.get("rating"):
            concerns[record["task_key"]] += len(record["rating"]["mathematical_concerns"])
    rows = []
    for path in sorted((RUN / "attempts").glob("*.json")):
        attempt = read(path)
        if attempt["status"] != "ready":
            continue
        key = attempt["key"]
        rows.append(
            {
                "key": key,
                "cell": attempt["cell_id"],
                "model": attempt["model_requested"],
                "final": scores[key]["final"],
                "judge_math_concerns": concerns[key],
                "title": attempt["task"]["title"],
                **flags(attempt["task"], attempt["cell_id"]),
            }
        )
    summary: dict[str, dict] = {}
    for model in ("gpt-5-mini", "gpt-4.1"):
        group = [row for row in rows if row["model"] == model]
        entry = {
            "ready_tasks": len(group),
            "median_words": st.median(row["words"] for row in group),
            "tasks_with_3plus_question_subparts": sum(
                row["question_subparts"] >= 3 for row in group
            ),
            **{name: sum(row[name] for row in group) for name in PATTERNS},
            "tasks_with_judge_math_concern": sum(row["judge_math_concerns"] > 0 for row in group),
        }
        for cell in TARGET_NAMED:
            cell_rows = [row for row in group if row["cell"] == cell]
            entry[f"names_target_or_method__{cell}"] = (
                f"{sum(row['names_target_or_method'] for row in cell_rows)}/{len(cell_rows)}"
            )
        music = [row for row in group if row["cell"] == "music_compare_distributions"]
        entry["music_random_sample_framing"] = (
            f"{sum(row['random_sample_framing'] for row in music)}/{len(music)}"
        )
        for cell in sorted({row["cell"] for row in group}):
            titles = Counter(row["title"] for row in group if row["cell"] == cell)
            entry[f"distinct_titles__{cell}"] = f"{len(titles)}/{sum(titles.values())}"
        summary[model] = entry
    OUT.write_text(
        json.dumps(
            {
                "method": "Regular-expression heuristics over student-facing task text; see PATTERNS. "
                "Approximate counts, not human coding.",
                "patterns": {name: pattern for name, (_, pattern) in PATTERNS.items()},
                "target_patterns": {cell: pattern for cell, (_, pattern) in TARGET_NAMED.items()},
                "summary": summary,
                "tasks": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
