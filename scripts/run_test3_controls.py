"""Run Test 3: evaluate expert and floor control students across two models."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
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
    QUESTION_PATH,
)
from scripts.run_test1_rule_following import load_tasks  # noqa: E402
from scripts.run_test2_rule_following_with_options import (  # noqa: E402
    extract_choice,
)

PROFILE_PATH = (
    PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test1_profiles.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "functional_diversity_test3_controls.json"
)
DEFAULT_WORKERS = 20
DEFAULT_REPEATS = 5
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 128
DEFAULT_TIMEOUT = 60.0

SYSTEM_PROMPT = """You are simulating one control student in a mathematics experiment.
Follow the control student's state exactly. Return JSON only."""

USER_TEMPLATE = """# Control student

Control type: {control_type}

{control_instructions}

# Question

{question}

# Answer options

{options}

Return JSON only:
{{"choice": "A"}}"""


def load_control_questions() -> list[dict[str, Any]]:
    question_payload = json.loads(QUESTION_PATH.read_text())
    question_map = {item["question_id"]: item for item in question_payload["questions"]}
    question_ids = sorted({task["question_id"] for task in load_tasks()})
    questions = []
    for question_id in question_ids:
        if question_id not in question_map:
            raise ValueError(f"Question {question_id} is missing from Test 0 questions.")
        question = question_map[question_id]
        options = {question["correct_option"]: question["correct_text"]}
        options.update(
            {distractor["option"]: distractor["text"] for distractor in question["distractors"]}
        )
        if set(options) != set("ABCD"):
            raise ValueError(f"Question {question_id} does not have four options.")
        questions.append(
            {
                "question_id": question_id,
                "skill": question["skill"],
                "question": question["question_text"],
                "options": options,
                "correct_option": question["correct_option"],
            }
        )
    return questions


def build_prompt(question: dict[str, Any], control_type: str) -> str:
    if control_type == "expert":
        instructions = (
            "You have mastered the relevant mathematics. Solve the question normally "
            "and select the mathematically correct option."
        )
    else:
        instructions = (
            "You have no usable procedure for this question. Do not solve it, calculate "
            "the answer, or use the option texts as clues. Make an uninformed guess among "
            "A, B, C, and D. This control is not expected to be correct."
        )
    options = "\n".join(f"{letter}. {question['options'][letter]}" for letter in "ABCD")
    return USER_TEMPLATE.format(
        control_type=control_type,
        control_instructions=instructions,
        question=question["question"],
        options=options,
    )


def invoke(
    client: OpenAI,
    model: str,
    question: dict[str, Any],
    control_type: str,
    repeat: int,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    row = {
        "model": model,
        "question_id": question["question_id"],
        "control_type": control_type,
        "correct_option": question["correct_option"],
        "repeat": repeat,
        "success": False,
        "choice": "",
        "format_status": "api_failed",
        "correct": False,
        "elapsed_seconds": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "finish_reason": None,
        "raw_response": "",
        "error": None,
    }
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_prompt(question, control_type),
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        raw = response.choices[0].message.content or ""
        choice, format_status = extract_choice(raw)
        usage = getattr(response, "usage", None)
        row.update(
            {
                "success": True,
                "choice": choice,
                "format_status": format_status,
                "correct": control_type == "expert" and choice == question["correct_option"],
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
                "finish_reason": response.choices[0].finish_reason,
                "raw_response": raw[:2000],
            }
        )
    except Exception as error:
        row["error"] = f"{type(error).__name__}: {str(error)[:300]}"
    row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return row


def entropy(counts: Counter[str]) -> float | None:
    total = sum(counts.values())
    if not total:
        return None
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        3,
    )


def summarize(rows: list[dict[str, Any]], wall_seconds: float, workers: int) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    expert = [row for row in rows if row["control_type"] == "expert"]
    floor = [row for row in rows if row["control_type"] == "floor"]
    floor_counts = Counter(row["choice"] or "UNPARSEABLE" for row in floor)
    latencies = [row["elapsed_seconds"] for row in successful]
    return {
        "calls": len(rows),
        "workers": workers,
        "successful_api_calls": len(successful),
        "api_success_rate": round(len(successful) / len(rows), 3) if rows else None,
        "json_format_rate": round(
            sum(row["format_status"] == "json" for row in rows) / len(rows),
            3,
        )
        if rows
        else None,
        "expert_calls": len(expert),
        "expert_correct": sum(row["correct"] for row in expert),
        "expert_accuracy": round(
            sum(row["correct"] for row in expert) / len(expert),
            3,
        )
        if expert
        else None,
        "expert_decision": (
            "continue" if sum(row["correct"] for row in expert) / len(expert) >= 0.90 else "stop"
        )
        if expert
        else "not_measurable",
        "floor_calls": len(floor),
        "floor_choice_counts": dict(sorted(floor_counts.items())),
        "floor_choice_entropy_bits": entropy(floor_counts),
        "floor_dominant_choice_share": round(
            max(floor_counts.values()) / len(floor), 3
        )
        if floor
        else None,
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3)
        if wall_seconds
        else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3)
        if latencies
        else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 2 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error(
            "workers must be at least 2; repeats, max-tokens, and timeout must be positive"
        )

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    questions = load_control_questions()
    model_specs = {label: models[label] for label in ("gpt41", "gpt41mini")}
    clients = {
        label: OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
        for label in model_specs
    }
    scheduled = [
        (label, question, control_type, repeat)
        for label, model in model_specs.items()
        for control_type in ("expert", "floor")
        for repeat in range(1, args.repeats + 1)
        for question in questions
    ]
    print(
        f"Test 3: {len(questions)} questions x 2 controls x {args.repeats} repeats "
        f"x 2 models = {len(scheduled)} calls; {args.workers} total workers."
    )

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(scheduled))) as pool:
        futures = {
            pool.submit(
                invoke,
                clients[label],
                model,
                question,
                control_type,
                repeat,
                args.temperature,
                args.max_tokens,
                args.timeout,
            ): (label, question, control_type, repeat)
            for label, question, control_type, repeat in scheduled
            for model in (model_specs[label],)
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            status = "correct" if row["correct"] else row["choice"] or "unparseable"
            print(
                f"[{completed}/{len(scheduled)}] {row['model']} Q{row['question_id']} "
                f"{row['control_type']}: {status}",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    summaries = {}
    for label in model_specs:
        model_rows = [row for row in rows if row["model"] == model_specs[label]]
        summaries[label] = summarize(model_rows, wall_seconds, args.workers)
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Test 3: expert and floor controls",
        "models": model_specs,
        "source_questions": str(QUESTION_PATH.relative_to(PROJECT_ROOT)),
        "source_profiles": str(PROFILE_PATH.relative_to(PROJECT_ROOT)),
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
            "workers": args.workers,
            "repeats": args.repeats,
            "question_count": len(questions),
            "answer_options_shown": True,
        },
        "summaries": summaries,
        "calls": sorted(
            rows,
            key=lambda row: (row["model"], row["control_type"], row["question_id"], row["repeat"]),
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
