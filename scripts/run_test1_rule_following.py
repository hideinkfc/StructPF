"""Run Test 1: measure whether GPT-4.1 follows fixed wrong rules without options."""

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
from src.evaluation.mcq_metrics import normalize_expression  # noqa: E402

PROFILE_PATH = PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test1_profiles.json"
QUESTION_PATH = (
    PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test0_questions.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "functional_diversity_test1_rule_following_gpt41.json"
)
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
if the correct method is familiar. Do not give the correct answer and do not explain
or repair the mistake.

Question:
{question}

Return JSON only, with the answer written as a short string:
{{"answer": "..."}}"""


def canonical_answer(value: str) -> str:
    normalized = normalize_expression(value or "")
    normalized = re.sub(r"\\boxed\s*", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("~", " ")
    normalized = normalized.replace("degrees", "°")
    normalized = re.sub(r"\bdivided by\b", "÷", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\btimes\b", "×", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bproblem\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "", normalized.lower())
    return normalized


def extract_answer(raw: str) -> tuple[str, str]:
    cleaned = (raw or "").strip()
    json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = json_text.find("{"), json_text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(json_text[start : end + 1])
            if isinstance(payload, dict) and "answer" in payload:
                return str(payload["answer"]), "json"
        except json.JSONDecodeError:
            pass
    return cleaned, "raw_fallback"


def load_tasks() -> list[dict[str, Any]]:
    profile_payload = json.loads(PROFILE_PATH.read_text())
    question_payload = json.loads(QUESTION_PATH.read_text())
    questions = {item["question_id"]: item for item in question_payload["questions"]}
    tasks = []
    for question_group in profile_payload["questions"]:
        question_id = question_group["question_id"]
        if question_id not in questions:
            raise ValueError(f"Question {question_id} is missing from Test 0 questions.")
        question = questions[question_id]
        for profile in question_group["profiles"]:
            tasks.append(
                {
                    "question_id": question_id,
                    "skill": question["skill"],
                    "question": question["question_text"],
                    **profile,
                }
            )
    expected_profiles = profile_payload["profiles_per_question"]
    question_count = len(profile_payload["questions"])
    if len(tasks) != question_count * expected_profiles:
        raise ValueError("Test 1 profile configuration has an unexpected task count.")
    return tasks


def build_prompt(task: dict[str, Any]) -> str:
    return USER_TEMPLATE.format(
        skill=task["skill"],
        error_rule=task["error_rule"],
        question=task["question"],
    )


def parse_task_response(
    raw: str,
    expected_answers: list[str],
    expected_parts: list[str] | None = None,
) -> dict[str, Any]:
    answer, format_status = extract_answer(raw)
    actual = canonical_answer(answer)
    expected = [canonical_answer(value) for value in expected_answers]
    matches = actual in expected
    parts = [canonical_answer(value) for value in (expected_parts or [])]
    if parts:
        position = 0
        matches = True
        for part in parts:
            position = actual.find(part, position)
            if position < 0:
                matches = False
                break
            position += len(part)
    if not matches and "=" in actual:
        final_result = canonical_answer(actual.rsplit("=", 1)[1]).rstrip(".,;:")
        matches = final_result in expected
    return {
        "answer": answer,
        "format_status": format_status,
        "canonical_answer": actual,
        "expected_canonical_answers": expected,
        "expected_canonical_parts": parts,
        "rule_followed": bool(actual) and matches,
    }


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
        "option": task["option"],
        "misconception_id": task["misconception_id"],
        "repeat": repeat,
        "success": False,
        "answer": "",
        "format_status": "api_failed",
        "canonical_answer": "",
        "expected_canonical_answers": [
            canonical_answer(value) for value in task["expected_answers"]
        ],
        "expected_canonical_parts": [
            canonical_answer(value) for value in task.get("expected_parts", [])
        ],
        "rule_followed": False,
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
        parsed = parse_task_response(
            raw,
            task["expected_answers"],
            task.get("expected_parts"),
        )
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


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentage / 100 * len(ordered)) - 1)
    return round(ordered[index], 3)


def summarize(rows: list[dict[str, Any]], wall_seconds: float, workers: int) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    valid_answers = [row for row in successful if row["answer"]]
    matched = [row for row in rows if row["rule_followed"]]
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
            "rule_followed": sum(row["rule_followed"] for row in group_rows),
            "rule_following_rate": round(
                sum(row["rule_followed"] for row in group_rows) / len(group_rows), 3
            )
            if group_rows
            else None,
        }

    return {
        "calls": len(rows),
        "workers": workers,
        "successful_api_calls": len(successful),
        "api_success_rate": round(len(successful) / len(rows), 3) if rows else None,
        "valid_answer_count": len(valid_answers),
        "json_format_count": len(json_outputs),
        "json_format_rate": round(len(json_outputs) / len(rows), 3) if rows else None,
        "rule_followed_count": len(matched),
        "rule_following_rate_all_calls": round(len(matched) / len(rows), 3) if rows else None,
        "rule_following_rate_valid_answers": round(len(matched) / len(valid_answers), 3)
        if valid_answers
        else None,
        "decision": (
            "continue"
            if len(matched) / len(rows) >= 0.70
            else "stop"
            if len(matched) / len(rows) < 0.50
            else "borderline"
        )
        if rows
        else "not_measurable",
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3) if wall_seconds else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "p50_latency_seconds": percentile(latencies, 50),
        "p95_latency_seconds": percentile(latencies, 95),
        "profiles": {key: group_summary(value) for key, value in sorted(by_profile.items())},
        "questions": {str(key): group_summary(value) for key, value in sorted(by_question.items())},
    }


def rescore_existing(path: Path, tasks: list[dict[str, Any]]) -> None:
    payload = json.loads(path.read_text())
    task_map = {(task["profile_id"], repeat): task for task in tasks for repeat in range(1, 6)}
    rows = payload["calls"]
    for row in rows:
        task = task_map[(row["profile_id"], row["repeat"])]
        if row["success"]:
            row.update(
                parse_task_response(
                    row.get("raw_response", ""),
                    task["expected_answers"],
                    task.get("expected_parts"),
                )
            )
    previous_summary = payload["summary"]
    payload["summary"] = summarize(
        rows,
        previous_summary["wall_seconds"],
        previous_summary["workers"],
    )
    payload["scoring_revision"] = (
        "Accept final right-hand side when working is included and ordered operation "
        "parts for the operation-selection question. No API calls were made during rescore."
    )
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Rescored: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--rescore-existing",
        action="store_true",
        help="Rescore saved raw responses without making API calls.",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error("workers, repeats, max-tokens, and timeout must be positive")

    tasks = load_tasks()
    if args.rescore_existing:
        rescore_existing(args.output, tasks)
        return

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    model = models["gpt41"]
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    scheduled = [(task, repeat) for repeat in range(1, args.repeats + 1) for task in tasks]
    print(
        f"Test 1: {len(tasks)} profiles x {args.repeats} repeats = {len(scheduled)} calls; "
        f"GPT-4.1 with {args.workers} workers."
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
            status = "followed" if row["rule_followed"] else "did-not-follow"
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
        "test": "Test 1: rule-following without answer options",
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
            "answer_options_shown": False,
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
