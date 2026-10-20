"""Run Test 2: measure rule-following when all answer options are visible."""

from __future__ import annotations

import argparse
import json
import math
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
    QUESTION_PATH,
    load_tasks,
)

PROFILE_PATH = PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test1_profiles.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "functional_diversity_test2_option_following_gpt41.json"
)
TEST1_BASELINE = 0.944
DEFAULT_WORKERS = 10
DEFAULT_REPEATS = 5
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 128
DEFAULT_TIMEOUT = 60.0

SYSTEM_PROMPT = """You simulate a mathematics student who is making one fixed mistake.
Follow the student's wrong rule exactly. Do not correct the mistake, switch to the
normal method, or explain what the correct answer should be."""

USER_TEMPLATE = """Simulated student profile:
- Skill not mastered: {skill}
- Fixed wrong rule: {error_rule}

Apply the fixed wrong rule to this question. The student must use the wrong rule even
if the correct method is familiar. Choose the option this student would select. Do not
choose the mathematically correct answer just because it is visible.

Question:
{question}

Answer options:
{options}

Return JSON only:
{{"choice": "A"}}"""


def load_tasks_with_options() -> list[dict[str, Any]]:
    question_payload = json.loads(QUESTION_PATH.read_text())
    questions = {item["question_id"]: item for item in question_payload["questions"]}
    tasks = []
    for task in load_tasks():
        question = questions[task["question_id"]]
        options = {question["correct_option"]: question["correct_text"]}
        options.update(
            {distractor["option"]: distractor["text"] for distractor in question["distractors"]}
        )
        if set(options) != set("ABCD"):
            raise ValueError(f"Question {task['question_id']} does not have four options.")
        tasks.append({**task, "options": options})
    return tasks


def build_prompt(task: dict[str, Any]) -> str:
    options = "\n".join(f"{letter}. {task['options'][letter]}" for letter in "ABCD")
    return USER_TEMPLATE.format(
        skill=task["skill"],
        error_rule=task["error_rule"],
        question=task["question"],
        options=options,
    )


def extract_choice(raw: str) -> tuple[str, str]:
    cleaned = (raw or "").strip()
    json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = json_text.find("{"), json_text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(json_text[start : end + 1])
            if isinstance(payload, dict):
                for key in ("choice", "selected_option", "answer"):
                    if key in payload:
                        value = str(payload[key]).strip().upper()
                        match = re.search(r"\b([ABCD])\b", value)
                        if match:
                            return match.group(1), "json"
        except json.JSONDecodeError:
            pass

    match = re.search(
        r"(?:choice|option|answer)\s*(?:is|:|-)?\s*\**([ABCD])\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).upper(), "raw_fallback"
    match = re.match(r"\s*\**([ABCD])\b", cleaned, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper(), "raw_fallback"
    return "", "unparseable"


def invoke(
    client: OpenAI,
    model: str,
    task: dict[str, Any],
    temperature: float,
    max_tokens: int,
    timeout: float,
    repeat: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    row = {
        "question_id": task["question_id"],
        "profile_id": task["profile_id"],
        "expected_option": task["option"],
        "misconception_id": task["misconception_id"],
        "repeat": repeat,
        "success": False,
        "choice": "",
        "format_status": "api_failed",
        "choice_matches_rule": False,
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
                {"role": "user", "content": build_prompt(task)},
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
                "choice_matches_rule": choice == task["option"],
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


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentage / 100 * len(ordered)) - 1)
    return round(ordered[index], 3)


def summarize(
    rows: list[dict[str, Any]],
    wall_seconds: float,
    workers: int,
) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    parsed = [row for row in successful if row["choice"]]
    matched = [row for row in rows if row["choice_matches_rule"]]
    latencies = [row["elapsed_seconds"] for row in successful]
    json_outputs = [row for row in successful if row["format_status"] == "json"]
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_question: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_profile[row["profile_id"]].append(row)
        by_question[row["question_id"]].append(row)

    def group_summary(group_rows: list[dict[str, Any]]) -> dict[str, Any]:
        group_successful = [row for row in group_rows if row["success"]]
        return {
            "calls": len(group_rows),
            "successful_api_calls": len(group_successful),
            "choice_matches_rule": sum(row["choice_matches_rule"] for row in group_rows),
            "rule_following_rate": round(
                sum(row["choice_matches_rule"] for row in group_rows) / len(group_rows),
                3,
            )
            if group_rows
            else None,
        }

    rule_following_rate = len(matched) / len(rows) if rows else None
    drop_points = (
        (TEST1_BASELINE - rule_following_rate) * 100 if rule_following_rate is not None else None
    )
    return {
        "calls": len(rows),
        "workers": workers,
        "successful_api_calls": len(successful),
        "api_success_rate": round(len(successful) / len(rows), 3) if rows else None,
        "valid_choice_count": len(parsed),
        "json_format_count": len(json_outputs),
        "json_format_rate": round(len(json_outputs) / len(rows), 3) if rows else None,
        "rule_followed_count": len(matched),
        "rule_following_rate_all_calls": round(rule_following_rate, 3)
        if rule_following_rate is not None
        else None,
        "test1_baseline": TEST1_BASELINE,
        "drop_from_test1_percentage_points": round(drop_points, 2)
        if drop_points is not None
        else None,
        "decision": (
            "continue"
            if drop_points is not None and drop_points < 15
            else "stop"
            if drop_points is not None
            else "not_measurable"
        ),
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3) if wall_seconds else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "p50_latency_seconds": percentile(latencies, 50),
        "p95_latency_seconds": percentile(latencies, 95),
        "profiles": {key: group_summary(value) for key, value in sorted(by_profile.items())},
        "questions": {str(key): group_summary(value) for key, value in sorted(by_question.items())},
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
    if args.workers < 1 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error("workers, repeats, max-tokens, and timeout must be positive")

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    tasks = load_tasks_with_options()
    model = models["gpt41"]
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    scheduled = [(task, repeat) for repeat in range(1, args.repeats + 1) for task in tasks]
    print(
        f"Test 2: {len(tasks)} profiles x {args.repeats} repeats = {len(scheduled)} calls; "
        f"GPT-4.1 with {args.workers} workers and options shown."
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
            status = "followed" if row["choice_matches_rule"] else "did-not-follow"
            if not row["success"]:
                status = "api-failed"
            elif not row["choice"]:
                status = "unparseable-choice"
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
        "test": "Test 2: rule-following with answer options shown",
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
