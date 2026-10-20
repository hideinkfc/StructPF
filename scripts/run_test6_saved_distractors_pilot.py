"""Run a small Test 6 pilot on saved generated distractors."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from scripts.run_azure_mcq_plausibility import load_azure_config  # noqa: E402
from scripts.run_revised_test2_calibration import (  # noqa: E402
    invoke,
)

PROFILE_PATH = PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test1_profiles.json"
QUESTION_PATH = (
    PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test0_questions.json"
)
GENERATION_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "01_basic_direct.jsonl"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "functional_diversity_test6_saved_pilot_gpt41mini.json"
)
DEFAULT_CONDITION = "01_basic_direct_run0"
DEFAULT_QUESTION_IDS = (587, 1437)
DEFAULT_WORKERS = 10
DEFAULT_REPEATS = 5
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT = 60.0


def mutual_information(pairs: list[tuple[str, str]]) -> float:
    sample_count = len(pairs)
    joint = Counter(pairs)
    profile_counts = Counter(profile for profile, _ in pairs)
    choice_counts = Counter(choice for _, choice in pairs)
    return sum(
        (count / sample_count)
        * math.log(
            (count / sample_count)
            / ((profile_counts[profile] / sample_count) * (choice_counts[choice] / sample_count))
        )
        for (profile, choice), count in joint.items()
    )


def normalized_mutual_information(pairs: list[tuple[str, str]]) -> float | None:
    profiles = {profile for profile, _ in pairs}
    choices = {choice for _, choice in pairs}
    if len(profiles) < 2 or len(choices) < 2:
        return None
    denominator = math.log(min(len(profiles), len(choices)))
    return mutual_information(pairs) / denominator if denominator else None


def load_generated_rows(
    condition: str,
    question_ids: set[int],
) -> dict[int, dict[str, Any]]:
    matches: dict[int, dict[str, Any]] = {}
    for line in GENERATION_PATH.read_text().splitlines():
        payload = json.loads(line)
        question_id = int(payload["question_id"])
        if payload.get("condition") != condition or question_id not in question_ids:
            continue
        if question_id in matches:
            raise ValueError(f"Duplicate saved generation for Q{question_id} and {condition}.")
        generated = payload.get("generated", [])
        if len(generated) != 3:
            raise ValueError(f"Q{question_id} has {len(generated)} generated distractors, not 3.")
        matches[question_id] = payload
    missing = question_ids - matches.keys()
    if missing:
        raise ValueError(f"Saved generation is missing requested questions: {sorted(missing)}")
    return matches


def load_tasks(condition: str, question_ids: list[int]) -> list[dict[str, Any]]:
    question_payload = json.loads(QUESTION_PATH.read_text())
    profile_payload = json.loads(PROFILE_PATH.read_text())
    questions = {item["question_id"]: item for item in question_payload["questions"]}
    profiles = {item["question_id"]: item["profiles"] for item in profile_payload["questions"]}
    requested_ids = set(question_ids)
    generated_rows = load_generated_rows(condition, requested_ids)
    tasks: list[dict[str, Any]] = []

    for question_id in question_ids:
        if question_id not in questions or question_id not in profiles:
            raise ValueError(
                f"Q{question_id} is missing from the profile or question configuration."
            )
        question = questions[question_id]
        generated = generated_rows[question_id]["generated"]
        generated_letters = [letter for letter in "ABCD" if letter != question["correct_option"]]
        options = {question["correct_option"]: question["correct_text"]}
        options.update(
            {letter: item["text"] for letter, item in zip(generated_letters, generated)}
        )
        if set(options) != set("ABCD"):
            raise ValueError(f"Q{question_id} does not have four constructed options.")
        for profile in profiles[question_id]:
            tasks.append(
                {
                    "question_id": question_id,
                    "skill": question["skill"],
                    "question": question["question_text"],
                    "options": options,
                    "generated_options": generated,
                    "generated_option_letters": generated_letters,
                    "generation_condition": condition,
                    "reference_option": profile["option"],
                    **profile,
                }
            )
    return tasks


def annotate_row(row: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    row.update(
        {
            "reference_option": task["reference_option"],
            "error_rule": task["error_rule"],
            "expected_answers": task["expected_answers"],
            "generated_option_letters": task["generated_option_letters"],
            "generated_options": task["generated_options"],
            "generation_condition": task["generation_condition"],
        }
    )
    return row


def summarize(rows: list[dict[str, Any]], wall_seconds: float, workers: int) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    by_question: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)
        by_profile[row["profile_id"]].append(row)

    matrices: dict[str, Any] = {}
    nmi_values: list[float] = []
    for question_id, question_rows in sorted(by_question.items()):
        generated_letters = question_rows[0]["generated_option_letters"]
        pairs = [
            (row["profile_id"], row["selected_option"] or "UNPARSEABLE")
            for row in question_rows
        ]
        nmi = normalized_mutual_information(pairs)
        if nmi is not None:
            nmi_values.append(nmi)
        matrix: dict[str, Counter[str]] = defaultdict(Counter)
        for row in question_rows:
            matrix[row["profile_id"]][row["selected_option"] or "UNPARSEABLE"] += 1
        selected_generated = {
            letter
            for row in question_rows
            for letter in generated_letters
            if row["selected_option"] == letter
        }
        profiles = {}
        for profile, counts in sorted(matrix.items()):
            profile_rows = by_profile[profile]
            profiles[profile] = {
                "reference_option": profile_rows[0]["reference_option"],
                "error_rule": profile_rows[0]["error_rule"],
                "expected_answers": profile_rows[0]["expected_answers"],
                "answer_rule_following_rate": round(
                    sum(row["answer_rule_followed"] for row in profile_rows) / len(profile_rows),
                    3,
                ),
                "counts": {
                    choice: counts.get(choice, 0)
                    for choice in ("A", "B", "C", "D", "OTHER", "UNPARSEABLE")
                },
            }
        matrices[str(question_id)] = {
            "options": {
                choice: question_rows[0]["generated_options"][index]["text"]
                if choice in generated_letters
                else next(
                    row["generated_options"][index]["text"]
                    for row in question_rows
                    for index, letter in enumerate(generated_letters)
                    if letter == choice
                )
                for index, choice in enumerate(generated_letters)
            },
            "generated_option_letters": generated_letters,
            "uncovered_generated_options": sorted(set(generated_letters) - selected_generated),
            "profile_option_nmi": round(nmi, 3) if nmi is not None else None,
            "profiles": profiles,
        }

    return {
        "calls": len(rows),
        "workers": workers,
        "successful_api_calls": len(successful),
        "api_success_rate": round(len(successful) / len(rows), 3) if rows else None,
        "json_format_rate": round(
            sum(row["format_status"] == "json" for row in rows) / len(rows), 3
        )
        if rows
        else None,
        "answer_rule_following_rate": round(
            sum(row["answer_rule_followed"] for row in rows) / len(rows), 3
        )
        if rows
        else None,
        "selected_generated_option_rate": round(
            sum(row["selected_option"] in row["generated_option_letters"] for row in rows)
            / len(rows),
            3,
        )
        if rows
        else None,
        "other_rate": round(sum(row["selected_option"] == "OTHER" for row in rows) / len(rows), 3)
        if rows
        else None,
        "profile_option_nmi_mean": round(sum(nmi_values) / len(nmi_values), 3)
        if nmi_values
        else None,
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3)
        if wall_seconds
        else None,
        "question_matrices": matrices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enable-functional-diversity",
        action="store_true",
        help="Explicitly opt in to the archived functional-diversity Test 6 pilot.",
    )
    parser.add_argument("--question-ids", nargs="+", type=int, default=list(DEFAULT_QUESTION_IDS))
    parser.add_argument("--condition", default=DEFAULT_CONDITION)
    parser.add_argument("--model", choices=("gpt41", "gpt41mini"), default="gpt41mini")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.enable_functional_diversity:
        parser.error(
            "functional-diversity Test 6 is inactive; pass "
            "--enable-functional-diversity to run the archived pilot"
        )
    if args.workers < 1 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error("workers, repeats, max-tokens, and timeout must be positive")

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    tasks = load_tasks(args.condition, args.question_ids)
    model = models[args.model]
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    scheduled = [
        (task, repeat)
        for repeat in range(1, args.repeats + 1)
        for task in tasks
    ]
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(scheduled))) as pool:
        futures = {
            pool.submit(
                invoke,
                client,
                model,
                task,
                args.temperature,
                args.max_tokens,
                args.timeout,
                repeat,
            ): (task, repeat)
            for task, repeat in scheduled
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            task, _ = futures[future]
            row = annotate_row(future.result(), task)
            rows.append(row)
            print(
                f"[{completed}/{len(scheduled)}] Q{row['question_id']} {row['profile_id']} "
                f"repeat {row['repeat']}: {row['selected_option'] or 'UNPARSEABLE'}",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    summary = summarize(rows, wall_seconds, args.workers)
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Test 6 saved generated-distractor pilot",
        "model_label": args.model,
        "model": model,
        "provider": "Azure OpenAI-compatible endpoint",
        "source_profiles": str(PROFILE_PATH.relative_to(PROJECT_ROOT)),
        "source_questions": str(QUESTION_PATH.relative_to(PROJECT_ROOT)),
        "source_generations": str(GENERATION_PATH.relative_to(PROJECT_ROOT)),
        "parameters": {
            "condition": args.condition,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
            "workers": args.workers,
            "repeats": args.repeats,
            "question_ids": args.question_ids,
            "answer_options_shown": True,
            "profiles_built_independently": False,
        },
        "summary": summary,
        "calls": sorted(
            rows,
            key=lambda row: (row["question_id"], row["profile_id"], row["repeat"]),
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
