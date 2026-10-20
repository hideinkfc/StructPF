"""Run Test 5 negative controls for the functional-diversity calibration."""

from __future__ import annotations

import argparse
import json
import random
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
from scripts.run_test4_known_good import (  # noqa: E402
    normalized_mutual_information,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "functional_diversity_test5_negative_controls.json"
)
KNOWN_GOOD_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "functional_diversity_test4_known_good.json"
)
DEFAULT_MODELS = ("gpt41", "gpt41mini")
DEFAULT_WORKERS = 20
DEFAULT_REPEATS = 20
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT = 60.0
DEFAULT_PERMUTATIONS = 200


def _nonsense_options() -> list[str]:
    return ["-999", "999", "0"]


def build_tasks() -> list[dict[str, Any]]:
    source_tasks = load_tasks_with_options()
    by_question: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for task in source_tasks:
        by_question[task["question_id"]].append(task)
    tasks = []
    for question_id, question_tasks in sorted(by_question.items()):
        base = question_tasks[0]
        correct_option = next(
            option for option in "ABCD" if option not in {task["option"] for task in question_tasks}
        )
        bad_letters = [option for option in "ABCD" if option != correct_option]
        base_wrong_text = base["options"][base["option"]]
        base_answer = base["expected_answers"][0]
        same_error_options = [
            base_wrong_text,
            base_answer,
            f"The answer is {base_answer}",
        ]
        conditions = {
            "same_error": same_error_options,
            "nonsense": _nonsense_options(),
        }
        for condition, bad_options in conditions.items():
            options = {correct_option: base["options"][correct_option]}
            options.update(dict(zip(bad_letters, bad_options)))
            for index in range(3):
                tasks.append(
                    {
                        **base,
                        "condition": condition,
                        "profile_id": f"{condition}_q{question_id}_p{index + 1}",
                        "option": "UNASSIGNED",
                        "options": options,
                        "expected_answers": base["expected_answers"],
                        "expected_parts": base.get("expected_parts", []),
                    }
                )
    if len(tasks) != 72:
        raise ValueError(f"Expected 72 negative-control tasks, found {len(tasks)}.")
    return tasks


def permutation_nmi(
    pairs: list[tuple[str, str]],
    permutations: int,
    seed: int,
) -> dict[str, float | None]:
    observed = normalized_mutual_information(pairs)
    if observed is None:
        return {"observed": None, "null_mean": None, "adjusted": None, "p_value": None}
    rng = random.Random(seed)
    profiles = [profile for profile, _ in pairs]
    choices = [choice for _, choice in pairs]
    null_values = []
    for _ in range(permutations):
        shuffled = profiles[:]
        rng.shuffle(shuffled)
        value = normalized_mutual_information(list(zip(shuffled, choices)))
        if value is not None:
            null_values.append(value)
    null_mean = sum(null_values) / len(null_values) if null_values else None
    p_value = (
        (sum(value >= observed for value in null_values) + 1) / (len(null_values) + 1)
        if null_values
        else None
    )
    return {
        "observed": round(observed, 3),
        "null_mean": round(null_mean, 3) if null_mean is not None else None,
        "adjusted": round(observed - null_mean, 3) if null_mean is not None else None,
        "p_value": round(p_value, 3) if p_value is not None else None,
    }


def known_good_nmi() -> dict[str, float]:
    if not KNOWN_GOOD_PATH.exists():
        return {}
    payload = json.loads(KNOWN_GOOD_PATH.read_text())
    return {
        label: summary["profile_option_nmi_mean"]
        for label, summary in payload.get("summaries", {}).items()
        if summary.get("profile_option_nmi_mean") is not None
    }


def summarize_model(
    rows: list[dict[str, Any]],
    model_label: str,
    wall_seconds: float,
    workers: int,
    permutations: int,
    good_reference: float | None,
) -> dict[str, Any]:
    successful = [row for row in rows if row["success"]]
    by_condition_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_condition_question[(row["condition"], row["question_id"])].append(row)

    matrices = {}
    scores: dict[str, list[dict[str, float | None]]] = defaultdict(list)
    for (condition, question_id), question_rows in sorted(by_condition_question.items()):
        pairs = [
            (row["profile_id"], row["selected_option"] or "UNPARSEABLE")
            for row in question_rows
        ]
        score = permutation_nmi(pairs, permutations, seed=42 + question_id)
        scores[condition].append(score)
        counts: dict[str, Counter[str]] = defaultdict(Counter)
        for row in question_rows:
            counts[row["profile_id"]][row["selected_option"] or "UNPARSEABLE"] += 1
        matrices[f"{condition}:{question_id}"] = {
            "counts": {
                profile: {
                    choice: profile_counts.get(choice, 0)
                    for choice in ("A", "B", "C", "D", "OTHER", "UNPARSEABLE")
                }
                for profile, profile_counts in sorted(counts.items())
            },
            "nmi": score,
        }

    condition_summary = {}
    for condition, condition_scores in scores.items():
        observed = [
            score["observed"]
            for score in condition_scores
            if score["observed"] is not None
        ]
        adjusted = [
            score["adjusted"]
            for score in condition_scores
            if score["adjusted"] is not None
        ]
        mean_observed = sum(observed) / len(observed) if observed else None
        mean_adjusted = sum(adjusted) / len(adjusted) if adjusted else None
        gap = (
            good_reference - mean_observed
            if good_reference is not None and mean_observed is not None
            else None
        )
        condition_summary[condition] = {
            "questions": len(condition_scores),
            "mean_observed_nmi": round(mean_observed, 3) if mean_observed is not None else None,
            "mean_adjusted_nmi": round(mean_adjusted, 3) if mean_adjusted is not None else None,
            "known_good_nmi_reference": good_reference,
            "gap_from_known_good": round(gap, 3) if gap is not None else None,
            "negative_control_pass": bool(gap is not None and gap >= 0.30),
        }

    latencies = [row["elapsed_seconds"] for row in successful]
    return {
        "model_label": model_label,
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
        "answer_rule_following_rate": round(
            sum(row["answer_rule_followed"] for row in rows) / len(rows),
            3,
        )
        if rows
        else None,
        "conditions": condition_summary,
        "wall_seconds": round(wall_seconds, 3),
        "effective_calls_per_second": round(len(rows) / wall_seconds, 3)
        if wall_seconds
        else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3)
        if latencies
        else None,
        "matrices": matrices,
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
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if (
        args.workers < 1
        or args.repeats < 1
        or args.max_tokens < 1
        or args.timeout <= 0
        or args.permutations < 1
    ):
        parser.error("workers, repeats, max-tokens, timeout, and permutations must be positive")

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url, api_key, models = load_azure_config()
    tasks = build_tasks()
    model_names = {label: models[label] for label in args.models}
    clients = {
        label: OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
        for label in args.models
    }
    scheduled = [
        (label, task, repeat)
        for label in args.models
        for condition_task in (task for task in tasks)
        for repeat in range(1, args.repeats + 1)
        for task in (condition_task,)
    ]
    print(
        f"Test 5: {len(tasks)} tasks x {args.repeats} repeats x "
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
            row["condition"] = task["condition"]
            rows.append(row)
            status = row["selected_option"] or "UNPARSEABLE"
            if not row["success"]:
                status = "api-failed"
            print(
                f"[{completed}/{len(scheduled)}] {label} {task['condition']} "
                f"Q{row['question_id']} {task['profile_id']} repeat {repeat}: {status}",
                flush=True,
            )

    wall_seconds = time.perf_counter() - started
    good_reference = known_good_nmi()
    summaries = {
        label: summarize_model(
            [row for row in rows if row["model_label"] == label],
            label,
            wall_seconds,
            args.workers,
            args.permutations,
            good_reference.get(label),
        )
        for label in args.models
    }
    payload = {
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "test": "Test 5: negative controls",
        "design_note": (
            "The same profile procedure is repeated across rows in each negative control. "
            "This is a metric-specific null control: profile identity should not create separation."
        ),
        "models": model_names,
        "source_profiles": str(PROFILE_PATH.relative_to(PROJECT_ROOT)),
        "source_questions": str(QUESTION_PATH.relative_to(PROJECT_ROOT)),
        "known_good_reference": good_reference,
        "conditions": {
            "same_error": (
                "Three surface variants of one wrong answer with the same repeated "
                "profile procedure."
            ),
            "nonsense": (
                "Three unrelated wrong options with the same repeated profile "
                "procedure."
            ),
        },
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
            "workers": args.workers,
            "repeats": args.repeats,
            "permutations": args.permutations,
            "answer_options_shown": True,
        },
        "summaries": summaries,
        "calls": sorted(
            rows,
            key=lambda row: (
                row["model_label"],
                row["condition"],
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
