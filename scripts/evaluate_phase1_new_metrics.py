#!/usr/bin/env python3
"""Evaluate saved Phase 1a generations with the current MCQ metric contract."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_basic_glm_correctness_pilot import (
    _same_error_prompt,
    cached_judge_json,
    classify_correctness,
    coherence_prompt,
    compute_pm,
    get_judge_client,
    get_judge_model,
    plausibility_prompt,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "full_v3_20260810"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "full_v3_new_metrics_20260810"
)
TEST_SET_PATH = PROJECT_ROOT / "data" / "eedi" / "test_set_200.json"
DEFAULT_WORKERS = 8
JUDGE_TIMEOUT_S = 60.0
JUDGE_MAX_TOKENS = 256
PATH_JUDGE_MAX_TOKENS = 512

CONDITIONS = [
    "01_basic_direct",
    "02_expert_direct",
    "03_pedagogical_direct",
    "04_expert_cot",
    "05_expert_self_critique",
    "06_lookalike_direct",
    "07_expert_mc_random",
    "08_expert_mc_names",
    "09_expert_mc_causal",
    "10_pedagogical_cot_mc_causal",
    "11_fewshot_rag",
]


def load_questions() -> dict[int, dict[str, Any]]:
    questions = json.loads(TEST_SET_PATH.read_text())
    return {int(question["QuestionId"]): question for question in questions}


def adapt_record(raw: dict[str, Any], question: dict[str, Any], condition: str) -> dict[str, Any]:
    correct_letter = question["CorrectAnswer"]
    generated = raw.get("generated", [])
    return {
        "condition": raw.get("condition", f"{condition}_run{raw['run']}"),
        "question_id": raw["question_id"],
        "subject": raw.get("subject", question.get("SubjectName", "")),
        "run": raw["run"],
        "question_text": str(question.get("QuestionText", "")),
        "correct_answer": str(question.get(f"Answer{correct_letter}Text", "")),
        "distractors": generated[:3],
        "raw_distractor_count": len(generated),
        "output_contract_valid": len(generated) == 3,
    }


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def _judge_one(
    task: tuple[str, int, int, int, dict[str, Any], dict[str, Any]],
    client: Any,
    model: str,
) -> dict[str, Any]:
    condition, question_id, run, index, record, distractor = task
    try:
        result, cache_hit = cached_judge_json(
            plausibility_prompt(record, distractor),
            client=client,
            model=model,
            timeout=JUDGE_TIMEOUT_S,
            max_tokens=JUDGE_MAX_TOKENS,
        )
        score = int(result.get("score", -1))
        if score not in (0, 1, 2):
            raise ValueError("student plausibility score must be 0, 1, or 2")
        return {
            "condition": condition,
            "question_id": question_id,
            "run": run,
            "distractor_index": index,
            "score": score,
            "plausible_screen": score >= 1,
            "reason": str(result.get("reason", "")),
            "cache_hit": cache_hit,
            "error": "",
        }
    except Exception as error:
        return {
            "condition": condition,
            "question_id": question_id,
            "run": run,
            "distractor_index": index,
            "score": None,
            "plausible_screen": None,
            "reason": "",
            "cache_hit": False,
            "error": f"{type(error).__name__}: {error}",
        }


def _coherence_one(
    task: tuple[str, int, int, int, dict[str, Any], dict[str, Any]],
    client: Any,
    model: str,
) -> dict[str, Any]:
    condition, question_id, run, index, record, distractor = task
    if not distractor.get("reasoning_steps") or not distractor.get("faulty_step"):
        return {
            "condition": condition,
            "question_id": question_id,
            "run": run,
            "distractor_index": index,
            "coherent": None,
            "status": "unknown",
            "reason": "missing faulty_step or reasoning_steps",
            "cache_hit": False,
            "error": "",
        }
    try:
        result, cache_hit = cached_judge_json(
            coherence_prompt(record, distractor),
            client=client,
            model=model,
            timeout=JUDGE_TIMEOUT_S,
            max_tokens=PATH_JUDGE_MAX_TOKENS,
        )
        coherent = result.get("matches_text", result.get("coherent"))
        if coherent not in (True, False, None):
            raise ValueError("matches_text must be true, false, or null")
        return {
            "condition": condition,
            "question_id": question_id,
            "run": run,
            "distractor_index": index,
            "coherent": coherent,
            "status": "pass" if coherent is True else "fail" if coherent is False else "unknown",
            "final_from_steps": result.get("final_from_steps"),
            "reason": str(result.get("reason", "")),
            "cache_hit": cache_hit,
            "error": "",
        }
    except Exception as error:
        return {
            "condition": condition,
            "question_id": question_id,
            "run": run,
            "distractor_index": index,
            "coherent": None,
            "status": "unknown",
            "reason": "",
            "cache_hit": False,
            "error": f"{type(error).__name__}: {error}",
        }


def _pathway_diversity_one(
    record: dict[str, Any],
    correctness: list[str],
    plausibility: dict[int, dict[str, Any]],
    coherence: dict[int, dict[str, Any]],
    client: Any,
    model: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    valid_indices = [
        index
        for index, status in enumerate(correctness, start=1)
        if status == "incorrect"
        and plausibility.get(index, {}).get("score") is not None
        and plausibility[index]["score"] >= 1
        and coherence.get(index, {}).get("status") == "pass"
    ]
    if len(valid_indices) < 2:
        return (
            {
                "status": "not_measurable",
                "value": None,
                "valid_distractors": len(valid_indices),
                "reason": "fewer than two incorrect, plausible, coherent distractors",
            },
            [],
        )

    options = {index: record["distractors"][index - 1] for index in valid_indices}
    edges: list[tuple[int, int, bool]] = []
    judgments: list[dict[str, Any]] = []
    for left, right in itertools.combinations(valid_indices, 2):
        try:
            result, cache_hit = cached_judge_json(
                _same_error_prompt(record, options[left], options[right]),
                client=client,
                model=model,
                timeout=JUDGE_TIMEOUT_S,
                max_tokens=PATH_JUDGE_MAX_TOKENS,
            )
            same_error = result.get("same_error")
            if same_error not in (True, False):
                raise ValueError("same_error must be boolean")
            edges.append((left, right, same_error))
            judgments.append(
                {
                    "condition": record["condition"],
                    "question_id": record["question_id"],
                    "run": record["run"],
                    "left_index": left,
                    "right_index": right,
                    "same_error": same_error,
                    "shared_faulty_step": result.get("shared_faulty_step", ""),
                    "reason": str(result.get("reason", "")),
                    "cache_hit": cache_hit,
                    "error": "",
                }
            )
        except Exception as error:
            judgments.append(
                {
                    "condition": record["condition"],
                    "question_id": record["question_id"],
                    "run": record["run"],
                    "left_index": left,
                    "right_index": right,
                    "same_error": None,
                    "shared_faulty_step": "",
                    "reason": "",
                    "cache_hit": False,
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    parent = {index: index for index in valid_indices}

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left, right, same_error in edges:
        if same_error:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root
    classes = len({find(index) for index in valid_indices})
    return (
        {
            "status": "measured"
            if len(edges) == len(list(itertools.combinations(valid_indices, 2)))
            else "partial",
            "value": (classes - 1) / (len(valid_indices) - 1),
            "valid_distractors": len(valid_indices),
            "error_classes": classes,
            "reason": "pairwise faulty-step judgments",
        },
        judgments,
    )


def evaluate_records(
    raw_records: list[tuple[str, dict[str, Any]]],
    questions: dict[int, dict[str, Any]],
    workers: int,
    measure_paths: bool = False,
    llm_verify_pm: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    adapted: list[tuple[str, dict[str, Any]]] = []
    for condition, raw in raw_records:
        question = questions[raw["question_id"]]
        adapted.append((condition, adapt_record(raw, question, condition)))

    tasks = [
        (condition, record["question_id"], record["run"], index, record, distractor)
        for condition, record in adapted
        for index, distractor in enumerate(record["distractors"], start=1)
    ]
    client = get_judge_client()
    model = get_judge_model()
    judgments: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_judge_one, task, client, model) for task in tasks]
        for future in as_completed(futures):
            judgments.append(future.result())
    judgments.sort(
        key=lambda row: (row["condition"], row["question_id"], row["run"], row["distractor_index"])
    )

    coherence_rows: list[dict[str, Any]] = []
    if measure_paths:
        coherence_tasks = [
            (condition, record["question_id"], record["run"], index, record, distractor)
            for condition, record in adapted
            for index, distractor in enumerate(record["distractors"], start=1)
        ]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_coherence_one, task, client, model) for task in coherence_tasks]
            for future in as_completed(futures):
                coherence_rows.append(future.result())
        coherence_rows.sort(
            key=lambda row: (
                row["condition"],
                row["question_id"],
                row["run"],
                row["distractor_index"],
            )
        )

    llm_pm_rows: list[dict[str, Any]] = []
    llm_pm_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    if llm_verify_pm:

        def _compute_llm_pm(
            item: tuple[str, dict[str, Any]],
        ) -> tuple[tuple[str, int, int], dict[str, Any]]:
            condition, record = item
            question = questions[record["question_id"]]
            result = compute_pm(
                record,
                question,
                llm_verify=True,
                judge_client=client,
                judge_model=model,
            )
            return (condition, record["question_id"], record["run"]), result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_compute_llm_pm, item) for item in adapted]
            for future in as_completed(futures):
                key, result = future.result()
                llm_pm_by_key[key] = result
                llm_pm_rows.append(
                    {
                        "condition": key[0],
                        "question_id": key[1],
                        "run": key[2],
                        "pm_llm": result.get("pm_llm"),
                        "llm_unknown_pairs": result.get("llm_unknown_pairs", 0),
                        "matches_llm": result.get("matches_llm", []),
                    }
                )

    judgment_by_key = {
        (row["condition"], row["question_id"], row["run"], row["distractor_index"]): row
        for row in judgments
    }
    coherence_by_key = {
        (row["condition"], row["question_id"], row["run"], row["distractor_index"]): row
        for row in coherence_rows
    }
    plausibility_by_record: dict[tuple[str, int, int], dict[int, dict[str, Any]]] = {}
    for row in judgments:
        plausibility_by_record.setdefault(
            (row["condition"], row["question_id"], row["run"]),
            {},
        )[row["distractor_index"]] = row
    pathway_rows: list[dict[str, Any]] = []
    per_record: list[dict[str, Any]] = []
    for condition, record in adapted:
        question = questions[record["question_id"]]
        correctness = [
            classify_correctness(
                distractor.get("text", ""),
                record["correct_answer"],
                record["question_text"],
            )[0]
            for distractor in record["distractors"]
        ]
        decisive = [status for status in correctness if status in {"correct", "incorrect"}]
        incorrect = sum(status == "incorrect" for status in decisive)
        judged = [
            judgment_by_key[(condition, record["question_id"], record["run"], index)]
            for index in range(1, len(record["distractors"]) + 1)
        ]
        scores = [row["score"] for row in judged if row["score"] is not None]
        screens = [row["plausible_screen"] for row in judged if row["plausible_screen"] is not None]
        pm = compute_pm(record, question)
        record_key = (condition, record["question_id"], record["run"])
        has_paths = any(
            distractor.get("reasoning_steps") or distractor.get("faulty_step")
            for distractor in record["distractors"]
        )
        coherence_for_record = [
            coherence_by_key.get((condition, record["question_id"], record["run"], index))
            for index in range(1, len(record["distractors"]) + 1)
        ]
        if measure_paths and has_paths:
            coherent_statuses = [row["status"] for row in coherence_for_record if row is not None]
            path_coherence = {
                "status": "measured" if coherent_statuses else "not_measurable",
                "pass": coherent_statuses.count("pass"),
                "fail": coherent_statuses.count("fail"),
                "unknown": coherent_statuses.count("unknown"),
                "rate": (
                    coherent_statuses.count("pass")
                    / (coherent_statuses.count("pass") + coherent_statuses.count("fail"))
                    if any(status in {"pass", "fail"} for status in coherent_statuses)
                    else None
                ),
                "reason": "structured pathway coherence judgments",
            }
        else:
            path_coherence = {
                "status": "not_measurable",
                "pass": 0,
                "fail": 0,
                "unknown": len(record["distractors"]),
                "rate": None,
                "reason": "No structured pathway evaluation requested or fields are absent.",
            }
        if measure_paths and has_paths:
            path_diversity, path_judgments = _pathway_diversity_one(
                record,
                correctness,
                plausibility_by_record.get(record_key, {}),
                {
                    index: coherence_by_key.get(
                        (condition, record["question_id"], record["run"], index), {}
                    )
                    for index in range(1, len(record["distractors"]) + 1)
                },
                client,
                model,
            )
        else:
            path_diversity, path_judgments = (
                {
                    "status": "not_measurable",
                    "value": None,
                    "valid_distractors": 0,
                    "reason": "No structured pathway evaluation requested or fields are absent.",
                },
                [],
            )
        pathway_rows.extend(path_judgments)
        llm_pm = llm_pm_by_key.get(record_key, {})
        per_record.append(
            {
                "condition": condition,
                "question_id": record["question_id"],
                "run": record["run"],
                "subject": record["subject"],
                "n_distractors": len(record["distractors"]),
                "raw_distractor_count": record["raw_distractor_count"],
                "output_contract_valid": record["output_contract_valid"],
                "incorrectness": {
                    "status_counts": {
                        status: correctness.count(status) for status in sorted(set(correctness))
                    },
                    "incorrect": incorrect,
                    "decisive": len(decisive),
                    "unknown": correctness.count("unknown"),
                    "unusable": correctness.count("unusable"),
                    "rate": incorrect / len(decisive) if decisive else None,
                },
                "student_plausibility": {
                    "scores": scores,
                    "mean_score_0_to_2": _mean([float(score) for score in scores]),
                    "screening_rate_ge_1": _mean([float(value) for value in screens]),
                    "judged": len(scores),
                    "failures": sum(row["score"] is None for row in judged),
                    "cache_hits": sum(bool(row["cache_hit"]) for row in judged),
                },
                "path_coherence": path_coherence,
                "pathway_diversity": path_diversity,
                "pm": {
                    "raw": pm.get("pm_raw"),
                    "normalized": pm.get("pm_normalized"),
                    "typed": pm.get("pm_typed"),
                    "llm": llm_pm.get("pm_llm"),
                    "llm_unknown_pairs": llm_pm.get("llm_unknown_pairs"),
                },
            }
        )
    return per_record, {
        "plausibility": judgments,
        "coherence": coherence_rows,
        "pathway": pathway_rows,
        "pm_llm": llm_pm_rows,
    }


def summarize(
    per_record: list[dict[str, Any]],
    judgment_bundle: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    judgments = judgment_bundle["plausibility"]
    for condition in CONDITIONS:
        rows = [row for row in per_record if row["condition"] == condition]
        condition_judgments = [row for row in judgments if row["condition"] == condition]
        summary[condition] = {
            "condition": condition,
            "question_runs": len(rows),
            "complete_three_distractor_sets": sum(row["n_distractors"] == 3 for row in rows),
            "output_contract_violations": sum(not row["output_contract_valid"] for row in rows),
            "raw_extra_distractors": sum(max(0, row["raw_distractor_count"] - 3) for row in rows),
            "incorrectness_rate": _mean(
                [
                    row["incorrectness"]["rate"]
                    for row in rows
                    if row["incorrectness"]["rate"] is not None
                ]
            ),
            "incorrectness_measured_question_runs": sum(
                row["incorrectness"]["rate"] is not None for row in rows
            ),
            "unknown_distractor_rate": _mean(
                [
                    row["incorrectness"]["unknown"] / row["n_distractors"]
                    for row in rows
                    if row["n_distractors"]
                ]
            ),
            "student_plausibility_mean_0_to_2": _mean(
                [
                    row["student_plausibility"]["mean_score_0_to_2"]
                    for row in rows
                    if row["student_plausibility"]["mean_score_0_to_2"] is not None
                ]
            ),
            "student_plausibility_screening_rate_ge_1": _mean(
                [
                    row["student_plausibility"]["screening_rate_ge_1"]
                    for row in rows
                    if row["student_plausibility"]["screening_rate_ge_1"] is not None
                ]
            ),
            "plausibility_judged_distractors": sum(
                row["score"] is not None for row in condition_judgments
            ),
            "plausibility_judge_failures": sum(row["score"] is None for row in condition_judgments),
            "path_coherence": (
                "measured"
                if any(row["path_coherence"]["status"] == "measured" for row in rows)
                else "not_measurable"
            ),
            "pathway_diversity": (
                "measured"
                if any(
                    row["pathway_diversity"]["status"] in {"measured", "partial"} for row in rows
                )
                else "not_measurable"
            ),
            "path_coherence_measured_question_runs": sum(
                row["path_coherence"]["status"] == "measured" for row in rows
            ),
            "path_coherence_rate": _mean(
                [
                    row["path_coherence"]["rate"]
                    for row in rows
                    if row["path_coherence"]["rate"] is not None
                ]
            ),
            "pathway_diversity_measured_question_runs": sum(
                row["pathway_diversity"]["status"] in {"measured", "partial"} for row in rows
            ),
            "pathway_diversity_mean": _mean(
                [
                    row["pathway_diversity"]["value"]
                    for row in rows
                    if row["pathway_diversity"]["value"] is not None
                ]
            ),
            "PM_raw": _mean([row["pm"]["raw"] for row in rows if row["pm"]["raw"] is not None]),
            "PM_normalized": _mean(
                [row["pm"]["normalized"] for row in rows if row["pm"]["normalized"] is not None]
            ),
            "PM_typed": _mean(
                [row["pm"]["typed"] for row in rows if row["pm"]["typed"] is not None]
            ),
            "PM_llm": _mean([row["pm"]["llm"] for row in rows if row["pm"]["llm"] is not None]),
            "PM_llm_unknown_pairs": sum(row["pm"]["llm_unknown_pairs"] or 0 for row in rows),
        }
    return summary


def load_source_records(
    source_dir: Path,
    limit: int | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    for condition in CONDITIONS:
        path = source_dir / f"{condition}.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if limit is not None:
            rows = rows[:limit]
        records.extend((condition, row) for row in rows)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-records-per-condition", type=int, default=None)
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--measure-paths", action="store_true")
    parser.add_argument("--llm-pm", action="store_true", help="Run LLM answer-equivalence PM")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    questions = load_questions()
    source_records = load_source_records(args.source_dir, args.max_records_per_condition)
    per_record, judgment_bundle = evaluate_records(
        source_records,
        questions,
        args.workers,
        measure_paths=args.measure_paths,
        llm_verify_pm=args.llm_pm,
    )
    summary = summarize(per_record, judgment_bundle)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "per_record.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in per_record)
    )
    for name, rows in judgment_bundle.items():
        (args.output_dir / f"{name}_judgments.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
    (args.output_dir / "aggregated.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Evaluated records: {len(per_record)}")
    print(f"Plausibility judgments: {len(judgment_bundle['plausibility'])}")
    print(f"Coherence judgments: {len(judgment_bundle['coherence'])}")
    print(f"Pathway judgments: {len(judgment_bundle['pathway'])}")
    print(f"LLM PM records: {len(judgment_bundle['pm_llm'])}")
    print(f"Saved: {args.output_dir}")


if __name__ == "__main__":
    main()
