"""Finalize two-judge plausibility evaluation for the 19-question subset."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compare_saved_pilot_plausibility_judges import (  # noqa: E402
    JUDGES,
    compare_judges,
    run_judges,
    summarize,
)
from scripts.run_basic_glm_correctness_pilot import evaluate_records, get_judge_client  # noqa: E402

INPUT_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_20_two_judge_plausibility.json"
)
OUTPUT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "phase1_mcq"
    / "mcq_19_two_judge_plausibility_final.json"
)
EXCLUDED_QUESTION_ID = 1052


def main() -> None:
    payload = json.loads(INPUT_PATH.read_text())
    records = [
        record
        for record in payload["generated_records"]
        if record["question_id"] != EXCLUDED_QUESTION_ID
    ]
    records.sort(key=lambda record: record["question_id"])
    if len(records) != 19:
        raise ValueError(f"Expected 19 records after exclusion, found {len(records)}")
    if any(
        len(record.get("distractors", [])) != 3 or record.get("parse_error") for record in records
    ):
        raise ValueError("The retained records are not all complete three-distractor sets")

    rows = run_judges(records, client=get_judge_client())
    summaries = {judge_name: summarize(rows, judge_name) for judge_name in JUDGES}
    _, correctness = evaluate_records(records)
    correctness_summary = correctness.iloc[0].to_dict() if not correctness.empty else {}
    question_means: dict[str, dict[str, float | None]] = defaultdict(dict)
    for judge_name in JUDGES:
        for record in records:
            scores = [
                row["score"]
                for row in rows
                if row["judge"] == judge_name
                and row["question_id"] == record["question_id"]
                and row["score"] is not None
            ]
            question_means[str(record["question_id"])][judge_name] = (
                round(sum(scores) / len(scores), 3) if scores else None
            )

    final = {
        "status": "complete",
        "source": str(INPUT_PATH.relative_to(PROJECT_ROOT)),
        "excluded_question_id": EXCLUDED_QUESTION_ID,
        "questions_evaluated": len(records),
        "distractors_expected": len(records) * 3,
        "expectations": payload["expectations"],
        "judges": JUDGES,
        "generation_summary": {
            "questions_evaluated": len(records),
            "complete_three_distractor_sets": len(records),
            "distractors_evaluated": len(records) * 3,
        },
        "correctness_summary": correctness_summary,
        "plausibility_judgments": rows,
        "plausibility_summaries": summaries,
        "question_means": dict(question_means),
        "judge_comparison": compare_judges(rows),
        "interpretation": "Descriptive LLM-proxy comparison only; no judge is treated as ground truth without human or student-response labels.",
    }
    OUTPUT_PATH.write_text(json.dumps(final, indent=2))
    print(f"Saved: {OUTPUT_PATH}")
    print("questions", len(records), "distractors", len(records) * 3)
    print(
        "correctness",
        {
            key: correctness_summary.get(key)
            for key in (
                "incorrect_distractors",
                "accidentally_correct",
                "unknown_equivalence",
                "incorrectness_rate",
                "duplicate_distractors",
            )
        },
    )
    for judge_name in JUDGES:
        print(judge_name, summaries[judge_name])
    print("comparison", final["judge_comparison"])


if __name__ == "__main__":
    main()
