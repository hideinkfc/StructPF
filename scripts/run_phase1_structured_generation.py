#!/usr/bin/env python3
"""Generate structured Phase 1a distractors without running legacy judges."""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_phase1_mcq import CONDITIONS, _build_condition_components, load_test_set
from scripts.run_basic_glm_correctness_pilot import is_viable

DEFAULT_TEST_SET = Path("data/eedi/test_set_200.json")
DEFAULT_OUTPUT_DIR = Path("experiments/results/phase1_mcq/structured_generation_v1_20260810")
DEFAULT_WORKERS = 8


def _generate_one(
    question: dict[str, Any],
    generator: Any,
    condition: tuple,
    run: int,
    attempts: int = 2,
) -> dict[str, Any]:
    name, system, instruction, strategy, fewshot_mode, mc_cond_depth = condition
    started = time.time()
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            result = generator.generate(
                question_text=str(question.get("QuestionText", "")),
                correct_answer=str(question.get(f"Answer{question['CorrectAnswer']}Text", "")),
                strategy=strategy,
                n_distractors=3,
                temperature=0.7,
                system_variant=system,
                instruction_variant=instruction,
                fewshot_mode=fewshot_mode or "rationale",
                mc_cond_depth=mc_cond_depth or "names",
                structured_paths=True,
                question_metadata=question,
            )
            generated = [item.model_dump() for item in result.distractors]
            if len(generated) != 3:
                raise ValueError(f"structured generation returned {len(generated)} distractors")
            if any(
                not item.get("faulty_step", "").strip()
                or not item.get("reasoning_steps")
                or any(not str(step).strip() for step in item["reasoning_steps"])
                for item in generated
            ):
                raise ValueError("structured generation returned an empty pathway field")
            return {
                "condition": f"{name}_run{run}",
                "question_id": question["QuestionId"],
                "subject": question.get("SubjectName", ""),
                "run": run,
                "generated": generated,
                "conditioning": (getattr(result, "model_extra", {}) or {}).get(
                    "conditioning_metadata", {}
                ),
                "generation_s": round(time.time() - started, 2),
                "attempts": attempt,
                "generation_error": "",
            }
        except Exception as error:
            last_error = f"{type(error).__name__}: {error}"
    return {
        "condition": f"{name}_run{run}",
        "question_id": question["QuestionId"],
        "subject": question.get("SubjectName", ""),
        "run": run,
        "generated": [],
        "conditioning": {},
        "generation_s": round(time.time() - started, 2),
        "attempts": attempts,
        "generation_error": last_error,
    }


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        for record in sorted(records, key=lambda row: (row["run"], row["question_id"])):
            handle.write(json.dumps(record) + "\n")


def run(
    test_set: list[dict[str, Any]],
    conditions: list[tuple],
    output_dir: Path,
    runs: int,
    workers: int,
    resume: bool,
    retry_failures: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    component_cache: dict[str, tuple] = {}

    for condition in conditions:
        name = condition[0]
        path = output_dir / f"{name}.jsonl"
        existing_keys = set()
        if resume and path.exists():
            existing_rows = [
                json.loads(line)
                for line in path.read_text().splitlines()
                if line.strip()
            ]
            if retry_failures:
                existing_rows = [row for row in existing_rows if not row.get("generation_error")]
                path.write_text(
                    "".join(json.dumps(row) + "\n" for row in existing_rows)
                )
            existing_keys = {
                (row["question_id"], row["run"])
                for row in existing_rows
            }
        component_key = "fewshot_rag" if condition[3] == "fewshot_rag" else "default"
        if component_key not in component_cache:
            component_cache[component_key] = _build_condition_components(condition)
        _, generator, _ = component_cache[component_key]

        jobs = [
            (question, run_index)
            for run_index in range(runs)
            for question in test_set
            if (question["QuestionId"], run_index) not in existing_keys
        ]
        print(f"{name}: {len(jobs)} structured generations", flush=True)
        started = time.time()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_generate_one, question, generator, condition, run_index)
                for question, run_index in jobs
            ]
            batch: list[dict[str, Any]] = []
            for index, future in enumerate(as_completed(futures), start=1):
                record = future.result()
                batch.append(record)
                if index % 20 == 0 or index == len(futures):
                    print(f"  {index}/{len(futures)} ({time.time() - started:.0f}s)", flush=True)
        _write_records(path, batch)
        failures = sum(bool(row["generation_error"]) for row in batch)
        print(f"  saved {len(batch)}; failures {failures}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--n", type=int, default=None, help="Use only the first N test questions")
    parser.add_argument("--viable-only", action="store_true", help="Keep numeric/equation text-only questions")
    parser.add_argument("--condition", default="", help="Run a condition name prefix")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    args = parser.parse_args()

    test_set = load_test_set(DEFAULT_TEST_SET)
    if args.viable_only:
        test_set = [question for question in test_set if is_viable(question)]
    if args.n is not None:
        test_set = test_set[:args.n]
    conditions = [condition for condition in CONDITIONS if not args.condition or condition[0].startswith(args.condition)]
    print(f"Structured generation: {len(conditions)} conditions, {len(test_set)} questions, {args.runs} runs")
    run(
        test_set,
        conditions,
        args.results_dir,
        args.runs,
        args.workers,
        args.resume,
        args.retry_failures,
    )


if __name__ == "__main__":
    main()