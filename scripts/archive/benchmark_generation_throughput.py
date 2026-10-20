"""Compare distractor-generation latency and throughput across model endpoints.

The benchmark sends the same basic MCQ-generation prompt to the existing Swiss-AI
GLM mode and Azure GPT-4.1 deployments. It does not write thesis experiment results.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from scripts.run_azure_mcq_plausibility import load_azure_config  # noqa: E402
from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    BASIC_SYSTEM_PROMPT,
    BASIC_USER_TEMPLATE,
    parse_distractors,
)
from src.utils.config import get_settings  # noqa: E402

QUESTIONS_PATH = (
    PROJECT_ROOT / "experiments" / "configs" / "functional_diversity_test0_questions.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "generation_throughput_benchmark.json"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 180.0
DEFAULT_WORKERS = 3
DEFAULT_LIMIT = 3
DEFAULT_REPEATS = 2


@dataclass(frozen=True)
class ModelSpec:
    label: str
    provider: str
    model: str
    base_url: str
    api_key: str
    extra_body: dict[str, Any] | None = None


def load_questions(limit: int) -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text())
    questions = sorted(payload["questions"], key=lambda question: question["question_id"])
    selected = questions[:limit]
    if len(selected) < limit:
        raise ValueError(f"Requested {limit} questions but only {len(selected)} are available.")
    return selected


def build_prompt(question: dict[str, Any]) -> str:
    return BASIC_USER_TEMPLATE.format(
        question=" ".join(question["question_text"].split()),
        correct_answer=question["correct_text"],
    )


def model_specs(labels: list[str]) -> list[ModelSpec]:
    from scripts.run_basic_glm_correctness_pilot import MODEL as GLM_MODEL

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, azure_models = load_azure_config()
    settings = get_settings()
    if not settings.swissai_api_key:
        raise RuntimeError("CSCS_SERVING_API is missing from .env or the environment.")

    available = {
        "glm": ModelSpec(
            label="glm",
            provider="Swiss AI",
            model=GLM_MODEL,
            base_url=settings.swissai_base_url,
            api_key=settings.swissai_api_key,
            extra_body={"thinking": {"type": "enabled"}},
        ),
        "gpt41": ModelSpec(
            label="gpt41",
            provider="Azure",
            model=azure_models["gpt41"],
            base_url=base_url,
            api_key=api_key,
        ),
        "gpt41mini": ModelSpec(
            label="gpt41mini",
            provider="Azure",
            model=azure_models["gpt41mini"],
            base_url=base_url,
            api_key=api_key,
        ),
    }
    return [available[label] for label in labels]


def invoke(
    spec: ModelSpec,
    question: dict[str, Any],
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    client = OpenAI(base_url=spec.base_url, api_key=spec.api_key, max_retries=0)
    started = time.perf_counter()
    result: dict[str, Any] = {
        "question_id": question["question_id"],
        "success": False,
        "parsed_distractors": 0,
        "elapsed_seconds": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "finish_reason": None,
        "error": None,
    }
    request: dict[str, Any] = {
        "model": spec.model,
        "messages": [
            {"role": "system", "content": BASIC_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "timeout": timeout,
    }
    if spec.extra_body:
        request["extra_body"] = spec.extra_body

    try:
        response = client.chat.completions.create(**request)
        content = response.choices[0].message.content or ""
        parsed = parse_distractors(content)
        usage = getattr(response, "usage", None)
        result.update(
            {
                "success": True,
                "parsed_distractors": len(parsed),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
                "finish_reason": response.choices[0].finish_reason,
            }
        )
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {str(error)[:300]}"
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return result


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentage / 100 * len(ordered)) - 1)
    return round(ordered[index], 3)


def run_model(
    spec: ModelSpec,
    questions: list[dict[str, Any]],
    repeats: int,
    workers: int,
    warmup: int,
    max_tokens: int,
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prompts = {question["question_id"]: build_prompt(question) for question in questions}
    warmup_rows = []
    for _ in range(warmup):
        warmup_rows.append(
            invoke(
                spec,
                questions[0],
                prompts[questions[0]["question_id"]],
                max_tokens,
                timeout,
            )
        )

    tasks = [
        (question, repeat)
        for repeat in range(1, repeats + 1)
        for question in questions
    ]
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
        futures = {
            pool.submit(
                invoke,
                spec,
                question,
                prompts[question["question_id"]],
                max_tokens,
                timeout,
            ): (question, repeat)
            for question, repeat in tasks
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            question, repeat = futures[future]
            row = future.result()
            row["repeat"] = repeat
            rows.append(row)
            status = "ok" if row["success"] else "failed"
            print(
                f"[{spec.label} {completed}/{len(tasks)}] Q{question['question_id']} "
                f"repeat {repeat}: {status} ({row['elapsed_seconds']}s)",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    successful = [row for row in rows if row["success"]]
    latencies = [row["elapsed_seconds"] for row in successful]
    completion_tokens = [
        row["completion_tokens"]
        for row in successful
        if row["completion_tokens"] is not None
    ]
    prompt_tokens = [row["prompt_tokens"] for row in successful if row["prompt_tokens"] is not None]
    total_tokens = [row["total_tokens"] for row in successful if row["total_tokens"] is not None]
    summary = {
        "label": spec.label,
        "provider": spec.provider,
        "model": spec.model,
        "questions": len(questions),
        "repeats": repeats,
        "workload_calls": len(tasks),
        "workers": workers,
        "warmup_calls": warmup,
        "warmup_successes": sum(row["success"] for row in warmup_rows),
        "successful_calls": len(successful),
        "success_rate": round(len(successful) / len(rows), 3) if rows else None,
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(successful) / wall_seconds, 3)
        if wall_seconds
        else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3)
        if latencies
        else None,
        "p50_latency_seconds": percentile(latencies, 50),
        "p95_latency_seconds": percentile(latencies, 95),
        "prompt_tokens": sum(prompt_tokens) if prompt_tokens else None,
        "completion_tokens": sum(completion_tokens) if completion_tokens else None,
        "total_tokens": sum(total_tokens) if total_tokens else None,
        "completion_tokens_per_second": round(sum(completion_tokens) / wall_seconds, 3)
        if completion_tokens and wall_seconds
        else None,
        "parsed_three_distractor_rate": round(
            sum(row["parsed_distractors"] == 3 for row in successful) / len(successful),
            3,
        )
        if successful
        else None,
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=("glm", "gpt41", "gpt41mini"),
        default=["glm", "gpt41", "gpt41mini"],
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.limit < 1 or args.repeats < 1 or args.workers < 1 or args.warmup < 0:
        parser.error("limit, repeats, and workers must be positive; warmup cannot be negative")

    questions = load_questions(args.limit)
    specs = model_specs(args.models)
    payload: dict[str, Any] = {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source": str(QUESTIONS_PATH.relative_to(PROJECT_ROOT)),
        "prompt": "basic MCQ distractor generation prompt used by the GLM pilot",
        "parameters": {
            "temperature": 0.2,
            "max_tokens": args.max_tokens,
            "questions": [question["question_id"] for question in questions],
            "repeats": args.repeats,
            "workers": args.workers,
            "warmup": args.warmup,
        },
        "models": [],
        "calls": [],
    }
    print(
        f"Benchmarking {len(specs)} models on {len(questions)} questions, "
        f"{args.repeats} repeats, {args.workers} workers."
    )
    for spec in specs:
        print(f"Model: {spec.label} ({spec.provider}, {spec.model})")
        summary, rows = run_model(
            spec,
            questions,
            args.repeats,
            args.workers,
            args.warmup,
            args.max_tokens,
            args.timeout,
        )
        payload["models"].append(summary)
        payload["calls"].extend({"model": spec.label, **row} for row in rows)
        print(json.dumps(summary, indent=2))

    payload["status"] = "complete"
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
