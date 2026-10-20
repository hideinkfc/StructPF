"""Small topic-diverse calibration for plausibility and pathway judges."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    JUDGE_REPEATS,
    evaluate_coherence,
    evaluate_plausibility,
)

OUTPUT_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "distractor_judge_calibration.json"
)


def case(
    case_id: str,
    split: str,
    topic: str,
    question: str,
    correct: str,
    text: str,
    steps: list[str],
    expected_coherence: bool,
    expected_plausibility: tuple[int, int] | None,
) -> dict:
    return {
        "question_id": case_id,
        "subject": topic,
        "question_text": question,
        "correct_answer": correct,
        "calibration_group": topic,
        "calibration_split": split,
        "expected_coherence": expected_coherence,
        "expected_plausibility": expected_plausibility,
        "distractors": [
            {
                "text": text,
                "faulty_step": "Applies a recognizable but incorrect rule",
                "reasoning_steps": steps,
                "target_misconception": "task-specific student error",
                "error_rationale": "The student applies a partial rule incorrectly.",
            }
        ],
    }


def calibration_cases() -> list[dict]:
    return [
        case(
            "dev-time-good",
            "development",
            "time",
            "How many hours are in 5 weeks?",
            "840",
            "120",
            ["Use 24 hours directly for each of 5 weeks: 5 * 24 = 120"],
            True,
            (1, 2),
        ),
        case(
            "dev-fraction-good",
            "development",
            "fraction",
            "What is 3/4 of 20?",
            "15",
            "8",
            ["Treat 3/4 as 0.4", "20 * 0.4 = 8"],
            True,
            (1, 2),
        ),
        case(
            "dev-area-good",
            "development",
            "area",
            "What is the perimeter of a 6 cm by 4 cm rectangle?",
            "20 cm",
            "10 cm",
            ["Add the length and width once: 6 + 4 = 10 cm"],
            True,
            (1, 2),
        ),
        case(
            "dev-random-good",
            "development",
            "arithmetic",
            "How many hours are in 5 weeks?",
            "840",
            "317",
            ["Use an unrelated conversion: 5 * 63.4 = 317"],
            True,
            (0, 0),
        ),
        case(
            "dev-fraction-broken",
            "development",
            "fraction",
            "What is 3/4 of 20?",
            "15",
            "8",
            ["Convert 3/4 to 0.75", "20 * 0.75 = 15"],
            False,
            None,
        ),
        case(
            "dev-area-broken",
            "development",
            "area",
            "What is the perimeter of a 6 cm by 4 cm rectangle?",
            "20 cm",
            "10 cm",
            ["Add all four sides: 6 + 4 + 6 + 4 = 20 cm"],
            False,
            None,
        ),
        case(
            "holdout-ratio-good",
            "holdout",
            "ratio",
            "Split 240 euros in the ratio 1:3.",
            "60 and 180",
            "120 and 120",
            ["There are two clubs", "Split 240 equally: 240 / 2 = 120 each"],
            True,
            (1, 2),
        ),
        case(
            "holdout-equation-good",
            "holdout",
            "equation",
            "Solve x + 7 = 12.",
            "x = 5",
            "x = 19",
            ["Move 7 to the other side by adding it: x = 12 + 7 = 19"],
            True,
            (1, 2),
        ),
        case(
            "holdout-percent-good",
            "holdout",
            "percentage",
            "What is 20% of 50?",
            "10",
            "60",
            ["Add 20% to the original amount: 50 + 10 = 60"],
            True,
            (1, 2),
        ),
        case(
            "holdout-random-good",
            "holdout",
            "arithmetic",
            "What is 20% of 50?",
            "10",
            "999",
            ["Add an unrelated amount: 300 + 699 = 999"],
            True,
            (0, 0),
        ),
        case(
            "holdout-ratio-broken",
            "holdout",
            "ratio",
            "Split 240 euros in the ratio 1:3.",
            "60 and 180",
            "120 and 120",
            ["There are 4 ratio parts: 240 / 4 = 60", "Give the groups 60 and 180"],
            False,
            None,
        ),
        case(
            "holdout-equation-broken",
            "holdout",
            "equation",
            "Solve x + 7 = 12.",
            "x = 5",
            "x = 19",
            ["Subtract 7 from 12: x = 12 - 7 = 5"],
            False,
            None,
        ),
    ]


def accuracy_table(
    details: pd.DataFrame, cases: list[dict], value_column: str, expected_column: str
) -> pd.DataFrame:
    expected = {item["question_id"]: item[expected_column] for item in cases}
    expected_split = {item["question_id"]: item["calibration_split"] for item in cases}
    actual = details.groupby("question_id")[value_column].first().to_dict()
    rows = []
    for question_id, expected_value in expected.items():
        observed = actual.get(question_id)
        if value_column == "status" and isinstance(expected_value, bool):
            expected_value = "pass" if expected_value else "fail"
        if expected_value is None:
            continue
        if isinstance(expected_value, (list, tuple)):
            expected_display = f"{expected_value[0]}-{expected_value[1]}"
            match = observed is not None and expected_value[0] <= observed <= expected_value[1]
        else:
            expected_display = expected_value
            match = observed == expected_value
        rows.append(
            {
                "question_id": question_id,
                "split": expected_split[question_id],
                "expected": expected_display,
                "observed": observed,
                "match": match,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    cases = calibration_cases()
    plausibility_cases = [item for item in cases if item["expected_plausibility"] is not None]
    with ThreadPoolExecutor(max_workers=2) as pool:
        plausibility_future = pool.submit(evaluate_plausibility, plausibility_cases, JUDGE_REPEATS)
        coherence_future = pool.submit(evaluate_coherence, cases)
        plausibility_raw, plausibility = plausibility_future.result()
        coherence_raw, coherence_summary = coherence_future.result()

    case_groups = {item["question_id"]: item["calibration_group"] for item in cases}
    case_splits = {item["question_id"]: item["calibration_split"] for item in cases}
    for table in (plausibility, plausibility_raw, coherence_raw):
        if not table.empty:
            table["topic"] = table["question_id"].map(case_groups)
            table["split"] = table["question_id"].map(case_splits)

    coherence_accuracy = accuracy_table(coherence_raw, cases, "status", "expected_coherence")
    plausibility_accuracy = accuracy_table(
        plausibility, cases, "plausibility_score", "expected_plausibility"
    )
    output = {
        "cases": cases,
        "coherence_raw": coherence_raw.to_dict("records"),
        "coherence_summary": coherence_summary.to_dict("records"),
        "coherence_accuracy": coherence_accuracy.to_dict("records"),
        "plausibility_raw": plausibility_raw.to_dict("records"),
        "plausibility": plausibility.to_dict("records"),
        "plausibility_accuracy": plausibility_accuracy.to_dict("records"),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    print("Saved:", OUTPUT_PATH)
    for name, table in (("coherence", coherence_accuracy), ("plausibility", plausibility_accuracy)):
        print(f"{name} accuracy by split:")
        print(table.groupby("split")["match"].mean().to_string())


if __name__ == "__main__":
    main()
