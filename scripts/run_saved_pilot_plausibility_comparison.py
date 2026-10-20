"""Compare plausibility of saved and fresh GLM distractors on five sampled questions."""

from __future__ import annotations

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, median
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    RESULTS_PATH,
    WORKERS,
    cached_judge_json,
    evaluate_records,
    generate_distractors,
    get_client,
    get_judge_client,
    load_questions,
    plausibility_prompt,
)

OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "basic_glm_plausibility_comparison_5.json"
SAMPLE_SIZE = 5
SAMPLE_SEED = 42
JUDGE_WORKERS = WORKERS

EXPECTATIONS = {
    "saved": "Most saved distractors were generated as plausible candidates, so scores should usually be 1 or 2; no claim is made that all should score 2.",
    "fresh_glm": "A fresh draw from the same GLM and basic prompt is not expected to be systematically better than the saved draw.",
    "comparison": "Call a condition better only if it has a higher mean plausibility score without a lower deterministic incorrectness rate; otherwise report inconclusive.",
    "evidence_limit": "The judge is an LLM proxy. This comparison is exploratory and does not establish real-student plausibility.",
}


def _write_payload(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))


def _judge_one(task: tuple[str, dict[str, Any], int, dict[str, Any]], client: Any) -> dict[str, Any]:
    source, record, distractor_index, distractor = task
    try:
        result, cache_hit = cached_judge_json(plausibility_prompt(record, distractor), client=client)
        score = int(result.get("score", -1))
        if score not in (0, 1, 2):
            raise ValueError("score must be 0, 1, or 2")
        return {
            "source": source,
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": score,
            "reason": str(result.get("reason", "")),
            "cache_hit": cache_hit,
        }
    except Exception as error:
        return {
            "source": source,
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": None,
            "reason": f"{type(error).__name__}: {error}",
            "cache_hit": False,
        }


def judge_records(records_by_source: dict[str, list[dict[str, Any]]], client: Any) -> list[dict[str, Any]]:
    tasks = [
        (source, record, index, distractor)
        for source, records in records_by_source.items()
        for record in records
        for index, distractor in enumerate(record.get("distractors", []), start=1)
    ]
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(JUDGE_WORKERS, max(1, len(tasks)))) as pool:
        futures = [pool.submit(_judge_one, task, client) for task in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
    return sorted(rows, key=lambda row: (row["source"], row["question_id"], row["distractor_index"]))


def summarize_judgments(rows: list[dict[str, Any]], source: str) -> dict[str, Any]:
    scores = [row["score"] for row in rows if row["source"] == source and row["score"] is not None]
    return {
        "source": source,
        "distractors_judged": len(scores),
        "mean_plausibility_score": round(mean(scores), 3) if scores else None,
        "median_plausibility_score": median(scores) if scores else None,
        "screen_rate_score_at_least_1": round(sum(score >= 1 for score in scores) / len(scores), 3) if scores else None,
        "score_counts": {str(score): scores.count(score) for score in (0, 1, 2)},
    }


def compare_conditions(
    judgment_summary: dict[str, dict[str, Any]],
    correctness_summary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    saved = judgment_summary["saved"]
    fresh = judgment_summary["fresh_glm"]
    saved_correctness = correctness_summary["saved"]["incorrectness_rate"]
    fresh_correctness = correctness_summary["fresh_glm"]["incorrectness_rate"]
    if saved["mean_plausibility_score"] is None or fresh["mean_plausibility_score"] is None:
        winner = "inconclusive"
    elif fresh["mean_plausibility_score"] > saved["mean_plausibility_score"] and fresh_correctness >= saved_correctness:
        winner = "fresh_glm"
    elif saved["mean_plausibility_score"] > fresh["mean_plausibility_score"] and saved_correctness >= fresh_correctness:
        winner = "saved"
    else:
        winner = "inconclusive"
    return {
        "winner_under_pre_registered_rule": winner,
        "saved_mean_minus_fresh_mean": round(saved["mean_plausibility_score"] - fresh["mean_plausibility_score"], 3) if saved["mean_plausibility_score"] is not None and fresh["mean_plausibility_score"] is not None else None,
        "interpretation": "This is a paired exploratory comparison of two stochastic GLM draws, not a model-quality claim.",
    }


def main() -> None:
    saved_records = json.loads(RESULTS_PATH.read_text())
    if len(saved_records) != 10:
        raise ValueError(f"Expected 10 saved records, found {len(saved_records)}")

    selected = random.Random(SAMPLE_SEED).sample(saved_records, SAMPLE_SIZE)
    question_ids = [record["question_id"] for record in selected]
    question_map = {question["QuestionId"]: question for question in load_questions()}
    questions = [question_map[question_id] for question_id in question_ids]

    payload: dict[str, Any] = {
        "status": "running",
        "expectations": EXPECTATIONS,
        "sampling": {"source": str(RESULTS_PATH.relative_to(PROJECT_ROOT)), "seed": SAMPLE_SEED, "sample_size": SAMPLE_SIZE, "question_ids": question_ids},
        "saved_records": selected,
    }
    _write_payload(payload)

    glm_client = get_client()
    with ThreadPoolExecutor(max_workers=min(WORKERS, len(questions))) as pool:
        futures = [pool.submit(generate_distractors, question, glm_client, structured_paths=False) for question in questions]
        fresh_records = [future.result() for future in futures]
    fresh_records.sort(key=lambda record: record["question_id"])

    judge_client = get_judge_client()
    judgment_rows = judge_records({"saved": selected, "fresh_glm": fresh_records}, judge_client)
    judgment_summary = {source: summarize_judgments(judgment_rows, source) for source in ("saved", "fresh_glm")}
    correctness_summary = {}
    for source, records in (("saved", selected), ("fresh_glm", fresh_records)):
        _, summary = evaluate_records(records)
        correctness_summary[source] = summary.iloc[0].to_dict() if not summary.empty else {}

    payload.update(
        {
            "status": "complete",
            "fresh_glm_records": fresh_records,
            "plausibility_judgments": judgment_rows,
            "plausibility_summary": judgment_summary,
            "correctness_summary": correctness_summary,
            "comparison": compare_conditions(judgment_summary, correctness_summary),
        }
    )
    _write_payload(payload)

    print(f"Saved: {OUTPUT_PATH}")
    for source in ("saved", "fresh_glm"):
        print(source, judgment_summary[source])
    print("comparison", payload["comparison"])


if __name__ == "__main__":
    main()
