"""Calibrate a procedural Test 2 prompt with answer and option outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from scripts.run_azure_mcq_plausibility import load_azure_config  # noqa: E402
from scripts.run_test1_rule_following import (  # noqa: E402
    parse_task_response,
)
from scripts.run_test2_rule_following_with_options import (  # noqa: E402
    QUESTION_PATH,
    load_tasks_with_options,
)

PROFILE_PATH = PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test1_profiles.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "functional_diversity_revised_test2_calibration_gpt41.json"
)
DEFAULT_QUESTION_IDS = (221, 796, 1035)
DEFAULT_WORKERS = 10
DEFAULT_REPEATS = 5
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT = 60.0

SYSTEM_PROMPT = """# Role

You simulate a learner with a fixed misconception. You are not a tutor and you are
not solving the question normally.

# Simulation protocol

1. Treat the student's wrong procedure as the only procedure available for this task.
2. Apply it mechanically to the question.
3. Calculate the answer produced by that procedure.
4. Compare that produced answer with the option texts.
5. Select the option whose text matches the produced answer.
6. If no option matches, return OTHER.
7. Do not replace the produced answer with the mathematically correct answer.

Do not explain or repair the mistake. Return only the requested JSON."""

USER_TEMPLATE = """# Student state

Skill being attempted: {skill}

Available wrong procedure:
{error_rule}

The learner does not use the correct procedure to check or repair the result.

# Question

{question}

# Answer options

{options}

# Output

Return JSON only:
{{"simulated_answer": "...", "selected_option": "A"}}"""

FEW_SHOT_EXAMPLES = """# Worked examples

These examples demonstrate the required process. Apply the current student's wrong
procedure to the current question; do not copy an example's answer.

<example>
Wrong procedure: To find 20% of a number, add 20 to the number.
Question: What is 20% of 50?
Options: A. 10   B. 70   C. 30   D. 100
Apply the wrong procedure: 50 + 20 = 70.
Output: {"simulated_answer": "70", "selected_option": "B"}
</example>

<example>
Wrong procedure: When dividing a fraction by an integer, multiply the numerator
by the integer and leave the denominator unchanged.
Question: Calculate 2/5 divided by 3.
Options: A. 6/5   B. 2/15   C. 15/2   D. 6/15
Apply the wrong procedure: 2 x 3 over 5 = 6/5.
Output: {"simulated_answer": "6/5", "selected_option": "A"}
</example>

<example>
Wrong procedure: When expanding a bracket, multiply only the first term by the
outside number and leave the second term unchanged.
Question: Expand 2(x + 4).
Options: A. 2x + 8   B. 2x + 4   C. x + 8   D. 6x
Apply the wrong procedure: 2 x x + 4 = 2x + 4.
Output: {"simulated_answer": "2x + 4", "selected_option": "B"}
</example>"""


def parse_output(raw: str, task: dict[str, Any]) -> dict[str, Any]:
    cleaned = (raw or "").strip()
    json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = json_text.find("{"), json_text.rfind("}")
    payload: dict[str, Any] = {}
    format_status = "unparseable"
    if start >= 0 and end > start:
        try:
            candidate = json.loads(json_text[start : end + 1])
            if isinstance(candidate, dict):
                payload = candidate
                format_status = "json"
        except json.JSONDecodeError:
            pass

    simulated_answer = str(payload.get("simulated_answer", ""))
    selected_option = str(payload.get("selected_option", "")).strip().upper()
    if selected_option not in set("ABCD") | {"OTHER"}:
        selected_option = ""
    answer_result = parse_task_response(
        simulated_answer,
        task["expected_answers"],
        task.get("expected_parts"),
    )
    option_text = task["options"].get(selected_option, "")
    option_result = (
        parse_task_response(
            option_text,
            task["expected_answers"],
            task.get("expected_parts"),
        )
        if option_text
        else {"rule_followed": False}
    )
    return {
        "simulated_answer": simulated_answer,
        "selected_option": selected_option,
        "format_status": format_status,
        "answer_rule_followed": answer_result["rule_followed"],
        "selected_option_matches_answer": option_result["rule_followed"],
        "selected_option_matches_expected": selected_option == task["option"],
    }


def build_prompt(task: dict[str, Any], include_examples: bool = False) -> str:
    options = "\n".join(f"{letter}. {task['options'][letter]}" for letter in "ABCD")
    prompt = USER_TEMPLATE.format(
        skill=task["skill"],
        error_rule=task["error_rule"],
        question=task["question"],
        options=options,
    )
    if include_examples:
        return f"{FEW_SHOT_EXAMPLES}\n\n# Current task\n\n{prompt}"
    return prompt


def invoke(
    client: OpenAI,
    model: str,
    task: dict[str, Any],
    temperature: float,
    max_tokens: int,
    timeout: float,
    repeat: int,
    include_examples: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    row = {
        "question_id": task["question_id"],
        "profile_id": task["profile_id"],
        "expected_option": task["option"],
        "repeat": repeat,
        "success": False,
        "simulated_answer": "",
        "selected_option": "",
        "format_status": "api_failed",
        "answer_rule_followed": False,
        "selected_option_matches_answer": False,
        "selected_option_matches_expected": False,
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
                    "content": build_prompt(task, include_examples=include_examples),
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        raw = response.choices[0].message.content or ""
        parsed = parse_output(raw, task)
        usage = getattr(response, "usage", None)
        row.update(
            {
                "success": True,
                **parsed,
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


def summarize(rows: list[dict[str, Any]], wall_seconds: float, workers: int) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    by_question: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)

    def rate(key: str) -> float | None:
        return round(sum(row[key] for row in rows) / len(rows), 3) if rows else None

    def group_summary(group_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "calls": len(group_rows),
            "answer_rule_followed": sum(row["answer_rule_followed"] for row in group_rows),
            "answer_rule_rate": round(
                sum(row["answer_rule_followed"] for row in group_rows) / len(group_rows),
                3,
            ),
            "selected_option_matches_answer": sum(
                row["selected_option_matches_answer"] for row in group_rows
            ),
            "selected_option_matches_expected": sum(
                row["selected_option_matches_expected"] for row in group_rows
            ),
        }

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
        "answer_rule_followed": sum(row["answer_rule_followed"] for row in rows),
        "answer_rule_following_rate": rate("answer_rule_followed"),
        "selected_option_matches_answer": sum(
            row["selected_option_matches_answer"] for row in rows
        ),
        "selected_option_matches_answer_rate": rate("selected_option_matches_answer"),
        "selected_option_matches_expected": sum(
            row["selected_option_matches_expected"] for row in rows
        ),
        "selected_option_expected_rate": rate("selected_option_matches_expected"),
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3) if wall_seconds else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "questions": {str(key): group_summary(value) for key, value in sorted(by_question.items())},
    }


def rescore_existing(path: Path, tasks: list[dict[str, Any]]) -> None:
    payload = json.loads(path.read_text())
    rows = payload["calls"]
    task_map = {(task["profile_id"], repeat): task for task in tasks for repeat in range(1, 6)}
    for row in rows:
        task = task_map[(row["profile_id"], row["repeat"])]
        if row["success"]:
            row.update(parse_output(row.get("raw_response", ""), task))
    previous_summary = payload["summary"]
    payload["summary"] = summarize(
        rows,
        previous_summary["wall_seconds"],
        previous_summary["workers"],
    )
    payload["scoring_revision"] = (
        "Normalized LaTeX spacing and final-answer punctuation. "
        "No API calls were made during rescore."
    )
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Rescored: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-ids", nargs="+", type=int, default=list(DEFAULT_QUESTION_IDS))
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--model", choices=("gpt41", "gpt41mini"), default="gpt41")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--rescore-existing",
        action="store_true",
        help="Rescore saved raw responses without making API calls.",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error("workers, repeats, max-tokens, and timeout must be positive")

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    all_tasks = load_tasks_with_options()
    tasks = [task for task in all_tasks if task["question_id"] in set(args.question_ids)]
    if len(tasks) != len(args.question_ids) * 3:
        raise ValueError("Each requested question must have exactly three profiles.")
    if args.rescore_existing:
        rescore_existing(args.output, tasks)
        return
    model = models[args.model]
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    scheduled = [(task, repeat) for repeat in range(1, args.repeats + 1) for task in tasks]
    print(
        f"Revised Test 2: {len(tasks)} profiles x {args.repeats} repeats = "
        f"{len(scheduled)} calls; GPT-4.1 with {args.workers} workers."
    )

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
            row = future.result()
            rows.append(row)
            status = "option-match" if row["selected_option_matches_expected"] else "miss"
            if not row["success"]:
                status = "api-failed"
            print(
                f"[{completed}/{len(scheduled)}] Q{row['question_id']} {row['profile_id']} "
                f"repeat {row['repeat']}: {status} ({row['elapsed_seconds']}s)",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    summary = summarize(rows, wall_seconds, args.workers)
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Revised Test 2: procedural prompt with visible options",
        "model_label": args.model,
        "model": model,
        "provider": "Azure OpenAI-compatible endpoint",
        "source_profiles": str(PROFILE_PATH.relative_to(PROJECT_ROOT)),
        "source_questions": str(QUESTION_PATH.relative_to(PROJECT_ROOT)),
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
            "workers": args.workers,
            "repeats": args.repeats,
            "question_ids": args.question_ids,
            "answer_options_shown": True,
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
