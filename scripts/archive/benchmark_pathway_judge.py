"""Validate and run the hand-authored pathway-diversity judge benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_azure_mcq_plausibility import load_azure_config  # noqa: E402
from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    _same_error_prompt,
    cached_judge_json,
)

DEFAULT_BENCHMARK = PROJECT_ROOT / "experiments" / "configs" / "pathway_diversity_benchmark.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "pathway_diversity_benchmark_v1.json"
)
REQUIRED_PAIR_FIELDS = {
    "pair_id",
    "split",
    "topic",
    "case_type",
    "question_text",
    "correct_answer",
    "path_a",
    "path_b",
    "gold_same_error",
    "annotation_note",
}
REQUIRED_PATH_FIELDS = {
    "text",
    "faulty_step",
    "reasoning_steps",
    "target_misconception",
    "error_rationale",
}


def load_benchmark(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_benchmark(benchmark: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pairs = benchmark.get("pairs")
    if not isinstance(pairs, list):
        return ["pairs must be a list"]
    if len(pairs) != 30:
        errors.append(f"benchmark must contain 30 pairs, found {len(pairs)}")
    pair_ids = [pair.get("pair_id") for pair in pairs if isinstance(pair, dict)]
    if len(pair_ids) != len(set(pair_ids)):
        errors.append("pair_id values must be unique")
    label_counts = Counter(pair.get("gold_same_error") for pair in pairs if isinstance(pair, dict))
    if label_counts != Counter({True: 15, False: 15}):
        errors.append(f"benchmark labels must contain 15 of each class, found {label_counts}")
    split_counts = Counter(pair.get("split") for pair in pairs if isinstance(pair, dict))
    if split_counts != Counter({"development": 15, "holdout": 15}):
        errors.append(f"benchmark splits must contain 15 each, found {split_counts}")
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            errors.append(f"pair {index} is not an object")
            continue
        missing = REQUIRED_PAIR_FIELDS - pair.keys()
        if missing:
            errors.append(f"{pair.get('pair_id', index)} missing fields: {sorted(missing)}")
        if not isinstance(pair.get("gold_same_error"), bool):
            errors.append(f"{pair.get('pair_id', index)} gold_same_error must be boolean")
        for label in ("path_a", "path_b"):
            path = pair.get(label)
            if not isinstance(path, dict):
                errors.append(f"{pair.get('pair_id', index)} {label} must be an object")
                continue
            missing_path = REQUIRED_PATH_FIELDS - path.keys()
            if missing_path:
                errors.append(
                    f"{pair.get('pair_id', index)} {label} missing fields: {sorted(missing_path)}"
                )
            if not isinstance(path.get("reasoning_steps"), (list, str)):
                errors.append(
                    f"{pair.get('pair_id', index)} {label}.reasoning_steps must be a list or string"
                )
    return errors


def _classification_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observed = [row for row in rows if row["observed_same_error"] is not None]
    true_positive = sum(row["gold_same_error"] and row["observed_same_error"] for row in observed)
    false_positive = sum(
        not row["gold_same_error"] and row["observed_same_error"] for row in observed
    )
    true_negative = sum(
        not row["gold_same_error"] and not row["observed_same_error"] for row in observed
    )
    false_negative = sum(
        row["gold_same_error"] and not row["observed_same_error"] for row in observed
    )
    total = len(observed)
    same_total = true_positive + false_negative
    different_total = true_negative + false_positive
    return {
        "pairs": len(rows),
        "scored_pairs": total,
        "unscored_pairs": len(rows) - total,
        "accuracy": (true_positive + true_negative) / total if total else None,
        "same_error_recall": true_positive / same_total if same_total else None,
        "different_error_recall": true_negative / different_total if different_total else None,
        "balanced_accuracy": (
            (true_positive / same_total + true_negative / different_total) / 2
            if same_total and different_total
            else None
        ),
        "true_positive_same": true_positive,
        "false_positive_same": false_positive,
        "true_negative_different": true_negative,
        "false_negative_different": false_negative,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_split: dict[str, dict[str, Any]] = {}
    by_case_type: dict[str, dict[str, Any]] = {}
    for split in sorted({row["split"] for row in rows}):
        by_split[split] = _classification_summary([row for row in rows if row["split"] == split])
    for case_type in sorted({row["case_type"] for row in rows}):
        by_case_type[case_type] = _classification_summary(
            [row for row in rows if row["case_type"] == case_type]
        )
    return {
        "overall": _classification_summary(rows),
        "by_split": by_split,
        "by_case_type": by_case_type,
    }


def _run_pair(pair: dict[str, Any], client: Any) -> dict[str, Any]:
    try:
        result, cache_hit = cached_judge_json(
            _same_error_prompt(pair, pair["path_a"], pair["path_b"]),
            client=client,
        )
        observed = result.get("same_error")
        if not isinstance(observed, bool):
            raise ValueError("judge field same_error must be boolean")
        return {
            "pair_id": pair["pair_id"],
            "split": pair["split"],
            "topic": pair["topic"],
            "case_type": pair["case_type"],
            "gold_same_error": pair["gold_same_error"],
            "observed_same_error": observed,
            "correct": observed == pair["gold_same_error"],
            "shared_faulty_step": result.get("shared_faulty_step", ""),
            "reason": result.get("reason", ""),
            "cache_hit": cache_hit,
        }
    except Exception as error:
        return {
            "pair_id": pair["pair_id"],
            "split": pair["split"],
            "topic": pair["topic"],
            "case_type": pair["case_type"],
            "gold_same_error": pair["gold_same_error"],
            "observed_same_error": None,
            "correct": None,
            "shared_faulty_step": "",
            "reason": "",
            "cache_hit": False,
            "error": f"{type(error).__name__}: {error}",
        }


def get_benchmark_client(max_retries: int) -> OpenAI:
    base_url, api_key, _ = load_azure_config()
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        max_retries=max_retries,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--split",
        choices=("all", "development", "holdout"),
        default="all",
        help="Subset to validate or run.",
    )
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="SDK retries for transient API errors such as rate limits.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Call the pathway judge. Without this flag, only validate the benchmark locally.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark = load_benchmark(args.benchmark)
    validation_errors = validate_benchmark(benchmark)
    if validation_errors:
        raise SystemExit("Invalid benchmark:\n- " + "\n- ".join(validation_errors))

    pairs = benchmark["pairs"]
    if args.split != "all":
        pairs = [pair for pair in pairs if pair["split"] == args.split]
    counts = Counter(pair["gold_same_error"] for pair in pairs)
    print(
        f"Validated {len(pairs)} pairs: {counts[True]} same-error, "
        f"{counts[False]} different-error ({args.split})."
    )
    if not args.run:
        print("No API calls made. Pass --run to execute the judge.")
        return

    client = get_benchmark_client(args.max_retries)
    with ThreadPoolExecutor(max_workers=min(args.workers, len(pairs))) as pool:
        rows = list(pool.map(lambda pair: _run_pair(pair, client), pairs))
    output = {
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_path": str(args.benchmark),
        "split": args.split,
        "results": rows,
        "summary": summarize(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2))
    print("Saved:", args.output)
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
