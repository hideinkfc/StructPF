"""Interactively collect and run Learning Commons standard searches."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.learning_commons_api import (
    BASE_URL,
    LearningCommonsAPIError,
    LearningCommonsClient,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "data" / "learning_commons" / "target_selection.json"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "results" / "learning_commons_queries"


def load_targets(path: Path = DEFAULT_SELECTION) -> list[dict[str, str]]:
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in target selection: {path}") from exc

    if not isinstance(selection, dict) or not isinstance(selection.get("targets"), list):
        raise ValueError(f"Target selection must contain a targets list: {path}")

    targets = []
    seen_ids = set()
    for index, target in enumerate(selection["targets"], start=1):
        if not isinstance(target, dict):
            raise ValueError(f"Target {index} must be an object")
        target_id = target.get("id")
        learning_target = target.get("learning_target")
        context = target.get("context")
        target_fields = (target_id, learning_target, context)
        if not all(isinstance(value, str) and value.strip() for value in target_fields):
            raise ValueError(f"Target {index} must have non-empty id, learning_target, and context")
        if target_id in seen_ids:
            raise ValueError(f"Duplicate target id in selection: {target_id}")
        seen_ids.add(target_id)
        targets.append({"id": target_id, "learning_target": learning_target, "context": context})
    return targets


def prompt_query_jobs(
    targets: list[dict[str, str]],
    *,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    read = input if input_fn is None else input_fn
    write = print if output_fn is None else output_fn
    jobs: list[dict[str, Any]] = []

    while True:
        write("Leave jurisdiction blank to search across frameworks; non-US coverage is limited.")
        write("\nPF targets:")
        for index, target in enumerate(targets, start=1):
            write(f"{index}. {target['learning_target']} ({target['context']})")
        prompt = "Choose a number, 'c' for another task, or Enter to run queued searches: "
        selection = read(prompt).strip()
        if not selection:
            return jobs

        if selection.casefold() in {"c", "custom"}:
            target_name = read("Additional task: ").strip()
            context = read("Task context: ").strip()
            if not target_name or not context:
                write("Task name and context are required; try again.")
                continue
            target_id = "custom"
            subject = read("Academic subject [Mathematics]: ").strip() or "Mathematics"
            if subject.casefold() == "none":
                subject = ""
        else:
            try:
                target_index = int(selection) - 1
            except ValueError:
                write("Enter a listed number, 'c', or Enter to finish.")
                continue
            if not 0 <= target_index < len(targets):
                write("That target number is not in the list.")
                continue
            target = targets[target_index]
            target_id = target["id"]
            target_name = target["learning_target"]
            context = target["context"]
            subject = "Mathematics"

        query = read("Plain-language search phrase (blank cancels this task): ").strip()
        if not query:
            write("Skipped this task.")
            continue
        grade_text = read("Grade levels, comma-separated (blank = no filter): ").strip()
        grade_levels = [value.strip() for value in grade_text.split(",") if value.strip()]
        jurisdiction = read("Jurisdiction filter (blank = no filter): ").strip() or None
        jobs.append(
            {
                "target_id": target_id,
                "target_name": target_name,
                "context": context,
                "query": query,
                "grade_levels": grade_levels,
                "academic_subject": subject or None,
                "jurisdiction": jurisdiction,
            }
        )


def run_queries(
    client: LearningCommonsClient,
    jobs: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    results = []
    for job in jobs:
        response = client.search_standards(
            query=job["query"],
            grade_levels=job["grade_levels"],
            academic_subject=job["academic_subject"],
            jurisdiction=job["jurisdiction"],
            limit=limit,
        )
        results.append({**job, "results": response})
    return results


def default_output_path(now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return DEFAULT_OUTPUT_DIR / f"guided_search_{timestamp:%Y%m%dT%H%M%S%fZ}.json"


def save_run(record: dict[str, Any], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing query results: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--limit", type=int, default=5, help="Maximum results per query (1-50)")
    parser.add_argument("--output", type=Path, help="Result path; defaults to a timestamped file")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    api_key = os.environ.get("LEARNING_COMMONS_API_KEY", "").strip()
    if not api_key:
        parser.error("set LEARNING_COMMONS_API_KEY in the environment")
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")

    try:
        targets = load_targets(args.selection)
        jobs = prompt_query_jobs(targets)
        if not jobs:
            print("No searches queued; no API requests made.")
            return
        output_path = args.output or default_output_path()
        if output_path.exists():
            parser.error(f"refusing to overwrite existing query results: {output_path}")
        responses = run_queries(LearningCommonsClient(api_key), jobs, limit=args.limit)
        record = {
            "source": "Learning Commons Knowledge Graph API",
            "api_base_url": BASE_URL,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "limit_per_query": args.limit,
            "queries": responses,
        }
        save_run(record, output_path)
    except (OSError, ValueError, LearningCommonsAPIError) as exc:
        parser.error(str(exc))

    print(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"\nSaved {len(responses)} query result(s) to {output_path}")


if __name__ == "__main__":
    main()
