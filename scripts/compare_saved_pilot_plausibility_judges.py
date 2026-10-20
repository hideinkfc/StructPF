"""Compare GPT-4.1 and GLM plausibility judgments on the saved 10-question pilot."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, median
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    JUDGE_MODEL,
    RESULTS_PATH,
    WORKERS,
    cached_judge_json,
    get_judge_client,
    plausibility_prompt,
)

OUTPUT_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "saved_pilot_plausibility_judges.json"
)
GLM_JUDGE_MODEL = "zai-org/GLM-4.7-Flash"
JUDGES = {
    "gpt41mini": JUDGE_MODEL,
    "glm": GLM_JUDGE_MODEL,
}
JUDGE_TIMEOUTS = {
    "gpt41mini": 180.0,
    "glm": 240.0,
}
JUDGE_MAX_TOKENS = {
    "gpt41mini": 2048,
    "glm": 8192,
}
JUDGE_WORKERS = 1

EXPECTATIONS = {
    "valid_outputs": "Both judges should return parseable scores in the compact 0-2 format for most available distractors.",
    "agreement": "The judges may disagree because plausibility is subjective; agreement is descriptive, not a correctness target.",
    "model_bias": "GPT-4.1-mini is the designated independent judge. GLM is also the generator model for the saved pilot, so its scores may show self-evaluation bias.",
    "winner": "No judge is declared better without human labels or student-response evidence.",
}


def write_payload(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))


def judge_one(
    task: tuple[str, str, dict[str, Any], int, dict[str, Any]], client: Any
) -> dict[str, Any]:
    judge_name, model, record, distractor_index, distractor = task
    try:
        result, cache_hit = cached_judge_json(
            plausibility_prompt(record, distractor),
            client=client,
            model=model,
            timeout=JUDGE_TIMEOUTS[judge_name],
            max_tokens=JUDGE_MAX_TOKENS[judge_name],
        )
        score = int(result.get("score", -1))
        if score not in (0, 1, 2):
            raise ValueError("score must be 0, 1, or 2")
        return {
            "judge": judge_name,
            "model": model,
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": score,
            "reason": str(result.get("reason", "")),
            "cache_hit": cache_hit,
        }
    except Exception as error:
        return {
            "judge": judge_name,
            "model": model,
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": None,
            "reason": f"{type(error).__name__}: {error}",
            "cache_hit": False,
        }


def run_judges(records: list[dict[str, Any]], client: Any) -> list[dict[str, Any]]:
    tasks = [
        (judge_name, model, record, index, distractor)
        for judge_name, model in JUDGES.items()
        for record in records
        for index, distractor in enumerate(record.get("distractors", []), start=1)
    ]
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(WORKERS, max(1, len(tasks)))) as pool:
        futures = [pool.submit(judge_one, task, client) for task in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
    return sorted(rows, key=lambda row: (row["judge"], row["question_id"], row["distractor_index"]))


def summarize(rows: list[dict[str, Any]], judge_name: str) -> dict[str, Any]:
    judged = [row for row in rows if row["judge"] == judge_name and row["score"] is not None]
    scores = [row["score"] for row in judged]
    return {
        "judge": judge_name,
        "model": JUDGES[judge_name],
        "distractors_judged": len(scores),
        "valid_score_rate": round(len(scores) / sum(row["judge"] == judge_name for row in rows), 3)
        if rows
        else None,
        "mean_score": round(mean(scores), 3) if scores else None,
        "median_score": median(scores) if scores else None,
        "screen_rate_score_at_least_1": round(sum(score >= 1 for score in scores) / len(scores), 3)
        if scores
        else None,
        "score_counts": {str(score): scores.count(score) for score in (0, 1, 2)},
    }


def compare_judges(rows: list[dict[str, Any]]) -> dict[str, Any]:
    paired: dict[tuple[int, int], dict[str, int | None]] = {}
    for row in rows:
        key = (row["question_id"], row["distractor_index"])
        paired.setdefault(key, {})[row["judge"]] = row["score"]
    pairs = [
        pair
        for pair in paired.values()
        if pair.get("gpt41mini") is not None and pair.get("glm") is not None
    ]
    valid_by_judge = {
        judge_name: sum(row["judge"] == judge_name and row["score"] is not None for row in rows)
        for judge_name in JUDGES
    }
    total_by_judge = {
        judge_name: sum(row["judge"] == judge_name for row in rows) for judge_name in JUDGES
    }
    complete = all(
        valid_by_judge[judge_name] == total_by_judge[judge_name] for judge_name in JUDGES
    )
    if not pairs:
        return {
            "paired_distractors": 0,
            "complete_judgments": complete,
            "comparison_status": "inconclusive",
            "exact_score_agreement": None,
            "screen_agreement": None,
            "mean_absolute_score_difference": None,
        }
    exact = sum(pair["gpt41mini"] == pair["glm"] for pair in pairs)
    screen = sum((pair["gpt41mini"] >= 1) == (pair["glm"] >= 1) for pair in pairs)
    distance = mean(abs(pair["gpt41mini"] - pair["glm"]) for pair in pairs)
    return {
        "paired_distractors": len(pairs),
        "complete_judgments": complete,
        "comparison_status": "descriptive_only" if complete else "inconclusive_incomplete_outputs",
        "exact_score_agreement": round(exact / len(pairs), 3),
        "screen_agreement": round(screen / len(pairs), 3),
        "mean_absolute_score_difference": round(distance, 3),
    }


def main() -> None:
    records = json.loads(RESULTS_PATH.read_text())
    if len(records) != 10:
        raise ValueError(f"Expected 10 saved records, found {len(records)}")
    available_questions = [record for record in records if record.get("distractors")]
    available_distractors = sum(len(record.get("distractors", [])) for record in records)
    payload: dict[str, Any] = {
        "status": "running",
        "expectations": EXPECTATIONS,
        "source": str(RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "questions_seen": len(records),
        "questions_with_distractors": len(available_questions),
        "questions_without_distractors": [
            record["question_id"] for record in records if not record.get("distractors")
        ],
        "available_distractors": available_distractors,
        "judges": JUDGES,
    }
    write_payload(payload)

    rows = run_judges(records, get_judge_client())
    summaries = {judge_name: summarize(rows, judge_name) for judge_name in JUDGES}
    payload.update(
        {
            "status": "complete",
            "judgments": rows,
            "summaries": summaries,
            "comparison": compare_judges(rows),
        }
    )
    write_payload(payload)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Questions: {len(records)} seen, {len(available_questions)} with distractors")
    for judge_name in JUDGES:
        print(judge_name, summaries[judge_name])
    print("comparison", payload["comparison"])


if __name__ == "__main__":
    main()
