"""Compare manual plausibility labels with Apertus and GLM judge scores."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

FINAL_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_19_two_judge_plausibility_final.json"
GENERATED_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_20_two_judge_plausibility.json"
MANUAL_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_19_manual_plausibility_labels.json"
OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_19_manual_vs_judges.json"


def agreement(rows: list[dict], judge: str) -> dict:
    pairs = [row for row in rows if row[judge] is not None]
    exact = sum(row["manual"] == row[judge] for row in pairs)
    screen = sum((row["manual"] >= 1) == (row[judge] >= 1) for row in pairs)
    return {
        "paired": len(pairs),
        "exact_agreement": round(exact / len(pairs), 3) if pairs else None,
        "mean_absolute_difference": round(mean(abs(row["manual"] - row[judge]) for row in pairs), 3) if pairs else None,
        "screen_agreement": round(screen / len(pairs), 3) if pairs else None,
        "score_counts": dict(sorted(Counter(row[judge] for row in pairs).items())),
    }


def main() -> None:
    final = json.loads(FINAL_PATH.read_text())
    generated = json.loads(GENERATED_PATH.read_text())["generated_records"]
    manual = json.loads(MANUAL_PATH.read_text())
    manual_by = {(row["question_id"], row["distractor_index"]): row for row in manual["labels"]}
    judge_by = {(row["question_id"], row["distractor_index"], row["judge"]): row for row in final["plausibility_judgments"]}

    rows = []
    for record in generated:
        if record["question_id"] == manual.get("excluded_question_id"):
            continue
        for index, distractor in enumerate(record.get("distractors", []), start=1):
            key = (record["question_id"], index)
            rows.append(
                {
                    "question_id": record["question_id"],
                    "subject": record["subject"],
                    "distractor_index": index,
                    "text": str(distractor.get("text", "")),
                    "manual": manual_by[key]["label"],
                    "manual_reason": manual_by[key]["reason"],
                    "apertus": judge_by.get(key + ("apertus",), {}).get("score"),
                    "glm": judge_by.get(key + ("glm",), {}).get("score"),
                }
            )

    metrics = {
        "manual": {"count": len(rows), "mean": round(mean(row["manual"] for row in rows), 3), "score_counts": dict(sorted(Counter(row["manual"] for row in rows).items()))},
        "manual_vs_apertus": agreement(rows, "apertus"),
        "manual_vs_glm": agreement(rows, "glm"),
    }
    disagreements = sorted(
        [row for row in rows if row["apertus"] is not None and row["glm"] is not None and (row["apertus"] != row["manual"] or row["glm"] != row["manual"])],
        key=lambda row: (abs(row["apertus"] - row["manual"]) + abs(row["glm"] - row["manual"]), row["question_id"], row["distractor_index"]),
        reverse=True,
    )
    output = {
        "status": "complete",
        "manual_label_source": manual["label_source"],
        "excluded_question_id": manual.get("excluded_question_id"),
        "rubric": manual["rubric"],
        "metrics": metrics,
        "rows": rows,
        "largest_disagreements": disagreements[:20],
        "interpretation": "Manual labels are exploratory assistant annotations, not independent human ground truth. GLM is also the generator model, so its agreement may reflect self-evaluation bias.",
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Saved: {OUTPUT_PATH}")
    print(json.dumps(metrics, indent=2))
    print("largest disagreements:")
    for row in disagreements[:10]:
        print(row["question_id"], row["distractor_index"], row["text"], "manual", row["manual"], "A", row["apertus"], "G", row["glm"])


if __name__ == "__main__":
    main()
