"""Compare the revised Test 2 prompt with and without worked examples."""

from __future__ import annotations

import argparse
import json
import sys
import time
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
    DEFAULT_MAX_TOKENS,
    DEFAULT_REPEATS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    PROFILE_PATH,
    QUESTION_PATH,
    invoke,
    load_tasks_with_options,
    summarize,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "functional_diversity_test2_prompt_ablation.json"
)
DEFAULT_QUESTION_IDS = (221, 796, 1035)
DEFAULT_WORKERS = 10


def run_variant(
    label: str,
    include_examples: bool,
    client: OpenAI,
    model: str,
    tasks: list[dict[str, Any]],
    repeats: int,
    workers: int,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scheduled = [(task, repeat) for repeat in range(1, repeats + 1) for task in tasks]
    print(f"Variant {label}: {len(scheduled)} calls with {workers} workers.")
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(scheduled))) as pool:
        futures = {
            pool.submit(
                invoke,
                client,
                model,
                task,
                temperature,
                max_tokens,
                timeout,
                repeat,
                include_examples,
            ): (task, repeat)
            for task, repeat in scheduled
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            row["variant"] = label
            rows.append(row)
            status = "match" if row["selected_option_matches_expected"] else "miss"
            if not row["success"]:
                status = "api-failed"
            print(
                f"[{label} {completed}/{len(scheduled)}] Q{row['question_id']} "
                f"{row['profile_id']} repeat {row['repeat']}: {status}",
                flush=True,
            )
    summary = summarize(rows, time.perf_counter() - started, workers)
    return summary, rows


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
    args = parser.parse_args()
    if args.workers < 1 or args.repeats < 1 or args.max_tokens < 1 or args.timeout <= 0:
        parser.error("workers, repeats, max-tokens, and timeout must be positive")

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    all_tasks = load_tasks_with_options()
    question_ids = set(args.question_ids)
    tasks = [task for task in all_tasks if task["question_id"] in question_ids]
    if len(tasks) != len(args.question_ids) * 3:
        raise ValueError("Each requested question must have exactly three profiles.")

    model = models[args.model]
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    variants = (("baseline", False), ("examples", True))
    summaries: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for label, include_examples in variants:
        summary, variant_rows = run_variant(
            label,
            include_examples,
            client,
            model,
            tasks,
            args.repeats,
            args.workers,
            args.temperature,
            args.max_tokens,
            args.timeout,
        )
        summaries[label] = summary
        rows.extend(variant_rows)
        print(json.dumps(summary, indent=2))

    baseline = summaries["baseline"]
    examples = summaries["examples"]
    comparison = {
        "answer_rule_following_delta_percentage_points": round(
            (examples["answer_rule_following_rate"] - baseline["answer_rule_following_rate"])
            * 100,
            2,
        ),
        "selected_option_expected_delta_percentage_points": round(
            (examples["selected_option_expected_rate"] - baseline["selected_option_expected_rate"])
            * 100,
            2,
        ),
        "selected_option_matches_answer_delta_percentage_points": round(
            (
                examples["selected_option_matches_answer_rate"]
                - baseline["selected_option_matches_answer_rate"]
            )
            * 100,
            2,
        ),
    }
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Paired prompt ablation for revised Test 2",
        "model_label": args.model,
        "model": model,
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
        "variants": {
            "baseline": "Current procedural prompt without worked examples.",
            "examples": "Current procedural prompt plus three held-out worked examples.",
        },
        "summaries": summaries,
        "comparison": comparison,
        "calls": sorted(
            rows,
            key=lambda row: (row["variant"], row["question_id"], row["profile_id"], row["repeat"]),
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(comparison, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
