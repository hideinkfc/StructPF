"""Run Test 4 on Eedi's known-good distractor sets."""

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
    PROFILE_PATH,
    QUESTION_PATH,
    invoke,
)
from scripts.run_test2_rule_following_with_options import (  # noqa: E402
    load_tasks_with_options,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "functional_diversity_test4_known_good.json"
)
DEFAULT_MODELS = ("gpt41", "gpt41mini")
DEFAULT_WORKERS = 20
DEFAULT_REPEATS = 20
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


def load_tasks() -> list[dict[str, Any]]:
    tasks = load_tasks_with_options()
    if len(tasks) != 36:
        raise ValueError(f"Expected 36 known-good profile tasks, found {len(tasks)}.")
    question_ids = {task["question_id"] for task in tasks}
    if len(question_ids) != 12:
        raise ValueError(f"Expected 12 known-good questions, found {len(question_ids)}.")
    by_question = defaultdict(list)
    for task in tasks:
        by_question[task["question_id"]].append(task)
    if any(len(question_tasks) != 3 for question_tasks in by_question.values()):
        raise ValueError("Each known-good question must have exactly three profiles.")
    if any(
        len({task["option"] for task in question_tasks}) != 3
        for question_tasks in by_question.values()
    ):
        raise ValueError("Each known-good question must have three distinct expected options.")
    return tasks


def summarize_model(
    rows: list[dict[str, Any]],
    wall_seconds: float,
    workers: int,
) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    expected_matches = [row for row in rows if row["selected_option_matches_expected"]]
    answer_matches = [row for row in rows if row["answer_rule_followed"]]
    by_question: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)
        by_profile[row["profile_id"]].append(row)

    question_scores = []
    matrices = {}
    for question_id, question_rows in sorted(by_question.items()):
        pairs = [
            (row["profile_id"], row["selected_option"] or "UNPARSEABLE")
            for row in question_rows
        ]
        nmi = normalized_mutual_information(pairs)
        question_scores.append(nmi) if nmi is not None else None
        matrix = defaultdict(Counter)
        expected = {}
        for row in question_rows:
            matrix[row["profile_id"]][row["selected_option"] or "UNPARSEABLE"] += 1
            expected[row["profile_id"]] = row["expected_option"]
        matrices[str(question_id)] = {
            "expected_option_by_profile": expected,
            "counts": {
                profile: {
                    choice: counts.get(choice, 0)
                    for choice in ("A", "B", "C", "D", "OTHER", "UNPARSEABLE")
                }
                for profile, counts in sorted(matrix.items())
            },
            "target_option_recovery": round(
                sum(row["selected_option_matches_expected"] for row in question_rows)
                / len(question_rows),
                3,
            ),
            "profile_option_nmi": round(nmi, 3) if nmi is not None else None,
        }

    profile_recovery = {
        profile: round(
            sum(row["selected_option_matches_expected"] for row in profile_rows)
            / len(profile_rows),
            3,
        )
        for profile, profile_rows in sorted(by_profile.items())
    }
    target_recovery = len(expected_matches) / len(rows) if rows else None
    nmi_values = [value for value in question_scores if value is not None]
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
        "answer_rule_following_rate": round(len(answer_matches) / len(rows), 3)
        if rows
        else None,
        "target_option_recovery": (
            round(target_recovery, 3) if target_recovery is not None else None
        ),
        "alignment_score": round(target_recovery, 3) if target_recovery is not None else None,
        "profile_option_nmi_mean": round(sum(nmi_values) / len(nmi_values), 3)
        if nmi_values
        else None,
        "profile_target_recovery": profile_recovery,
        "decision": "continue"
        if target_recovery is not None and target_recovery >= 0.60
        else "stop",
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3)
        if wall_seconds
        else None,
        "mean_latency_seconds": round(
            sum(row["elapsed_seconds"] for row in successful) / len(successful),
            3,
        )
        if successful
        else None,
        "question_matrices": matrices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=("gpt41", "gpt41mini"),
        default=list(DEFAULT_MODELS),
    )
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
    tasks = load_tasks()
    model_names = {label: models[label] for label in args.models}
    clients = {
        label: OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
        for label in args.models
    }
    scheduled = [
        (label, task, repeat)
        for label in args.models
        for repeat in range(1, args.repeats + 1)
        for task in tasks
    ]
    print(
        f"Test 4: {len(tasks)} profiles x {args.repeats} repeats x "
        f"{len(args.models)} models = {len(scheduled)} calls; {args.workers} workers."
    )

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(scheduled))) as pool:
        futures = {
            pool.submit(
                invoke,
                clients[label],
                model_names[label],
                task,
                args.temperature,
                args.max_tokens,
                args.timeout,
                repeat,
                False,
            ): (label, task, repeat)
            for label, task, repeat in scheduled
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            label, task, repeat = futures[future]
            row = future.result()
            row["model_label"] = label
            rows.append(row)
            status = "match" if row["selected_option_matches_expected"] else "miss"
            if not row["success"]:
                status = "api-failed"
            print(
                f"[{completed}/{len(scheduled)}] {label} Q{row['question_id']} "
                f"{row['profile_id']} repeat {repeat}: {status}",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    summaries = {
        label: summarize_model(
            [row for row in rows if row["model_label"] == label],
            wall_seconds,
            args.workers,
        )
        for label in args.models
    }
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Test 4: known-good Eedi distractor sets",
        "prompt_variant": "revised procedural prompt without worked examples",
        "models": model_names,
        "source_profiles": str(PROFILE_PATH.relative_to(PROJECT_ROOT)),
        "source_questions": str(QUESTION_PATH.relative_to(PROJECT_ROOT)),
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
            "workers": args.workers,
            "repeats": args.repeats,
            "answer_options_shown": True,
            "alignment_score_definition": (
                "fraction of calls selecting the predeclared Eedi target option"
            ),
        },
        "summaries": summaries,
        "calls": sorted(
            rows,
            key=lambda row: (
                row["model_label"],
                row["question_id"],
                row["profile_id"],
                row["repeat"],
            ),
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
