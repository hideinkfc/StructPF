#!/usr/bin/env python3
"""Phase 1a — MCQ experiment runner.

Runs the current misconception, prompting, and semantic few-shot conditions on
the frozen test set.
Saves per-question results + aggregated summaries.

Parallelism (3 levels):
  L1: validity & diversity self-consistency calls (6 LLM calls in parallel)
  L2: questions within a condition (ThreadPoolExecutor, --workers, default 3)
  L3: conditions (ProcessPoolExecutor, --parallel-conds)

Each question spawns 6 internal judge calls in parallel (evaluate_generation).
Default --workers 3 = 18 concurrent API calls. Crank up if your API allows.

Usage:
    python scripts/run_phase1_mcq.py                          # full run, all parallel
    python scripts/run_phase1_mcq.py --dry-run --n 5          # quick test
    python scripts/run_phase1_mcq.py --workers 10             # 10 concurrent questions (×6=60 calls)
    python scripts/run_phase1_mcq.py --parallel-conds         # parallel conditions too
    python scripts/run_phase1_mcq.py --no-parallel            # serial (debug mode)
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_azure_mcq_plausibility import load_azure_config
from src.evaluation.mcq_metrics import MCQEvaluator, ConditionResults, QuestionMetrics
from src.generation.mcq_generator import MCQGenerator
from src.generation.misconception_bank import MisconceptionBank
from src.utils.llm_client import LLMClient

# ── Paths ────────────────────────────────────────────────────────────────────

TEST_SET_PATH = Path("data/eedi/test_set_200.json")  # 200 random questions with ≥3 distractors
RESULTS_DIR = Path("experiments/results/phase1_mcq")
RAG_EMBED_MODEL = "text-embedding-3-small-EU"

# ── Conditions ───────────────────────────────────────────────────────────────

CONDITIONS = [
    # (name, system, instruction, strategy, fewshot_mode, mc_cond_depth)
    # 1-axis ablations against condition #2 (expert + direct + zero_shot)
    ("01_basic_direct",         "basic",       "direct", "zero_shot",                "", ""),
    ("02_expert_direct",        "expert",      "direct", "zero_shot",                "", ""),  # baseline
    ("03_pedagogical_direct",   "pedagogical", "direct", "zero_shot",                "", ""),
    ("04_expert_cot",           "expert",      "cot",    "zero_shot",                "", ""),
    ("05_expert_self_critique", "expert",      "self_critique", "zero_shot",         "", ""),
    ("06_lookalike_direct",     "lookalike",   "direct", "zero_shot",                "", ""),
    ("07_expert_mc_random",     "expert",      "direct", "misconception_random",      "", "names"),
    ("08_expert_mc_names",      "expert",      "direct", "misconception_conditioned", "", "names"),
    ("09_expert_mc_causal",     "expert",      "direct", "misconception_conditioned", "", "causal"),
    ("10_pedagogical_cot_mc_causal", "pedagogical", "cot", "misconception_conditioned", "", "causal"),
    ("11_fewshot_rag",          "expert",      "direct", "fewshot_rag",               "rationale", ""),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_test_set(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _build_condition_components(condition: tuple) -> tuple[MisconceptionBank, MCQGenerator, MCQEvaluator]:
    """Build clients for one condition without changing global model defaults."""
    if condition[3] == "fewshot_rag":
        azure_base_url, azure_api_key, models = load_azure_config()
        embed_client = LLMClient(
            base_url=azure_base_url,
            model=RAG_EMBED_MODEL,
            api_key=azure_api_key,
        )
        generation_client = LLMClient(
            base_url=azure_base_url,
            model=models["gpt41mini"],
            api_key=azure_api_key,
        )
        bank = MisconceptionBank(
            embed_client=embed_client,
            misconception_cache_key="eedi_misconceptions_azure_text_embedding_3_small_eu_v1",
        ).load()
        gen = MCQGenerator(llm=generation_client, bank=bank)
        gen.build_fewshot_index(
            embed_client=embed_client,
            cache_key="eedi_mcq_fewshot_train_azure_text_embedding_3_small_eu_v1",
        )
        evaluator = MCQEvaluator(bank, embed_client=embed_client)
        return bank, gen, evaluator

    azure_base_url, azure_api_key, _ = load_azure_config()
    embed_client = LLMClient(
        base_url=azure_base_url,
        model=RAG_EMBED_MODEL,
        api_key=azure_api_key,
    )
    bank = MisconceptionBank(
        embed_client=embed_client,
        misconception_cache_key="eedi_misconceptions_azure_text_embedding_3_small_eu_v1",
    ).load()
    gen = MCQGenerator(bank=bank)
    evaluator = MCQEvaluator(bank, embed_client=embed_client)
    return bank, gen, evaluator


def _save_result(
    record: dict,
    condition_name: str,
    results_dir: Path = RESULTS_DIR,
) -> None:
    """Append one result record to the condition's JSONL file (thread-safe)."""
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{condition_name}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def _process_one_question(
    q: dict,
    gen: MCQGenerator,
    evaluator: MCQEvaluator,
    condition: tuple,
    run_idx: int,
    dry_run: bool,
) -> tuple[QuestionMetrics | None, dict | None]:
    """Generate + evaluate one question. Returns (metrics, record) or (None, None)."""
    name, system, instruction, strategy, fewshot_mode, mc_cond_depth = condition
    run_label = f"{name}_run{run_idx}"
    q_id = q["QuestionId"]

    # Resolve correct answer text
    correct_letter = q.get("CorrectAnswer", "")
    correct_text = q.get(f"Answer{correct_letter}Text", "")

    # ── Generate ──
    gen_start = time.time()
    try:
        result = gen.generate(
            question_text=str(q.get("QuestionText", "")),
            correct_answer=str(correct_text),
            strategy=strategy,
            n_distractors=3,
            temperature=0.7,
            system_variant=system,
            instruction_variant=instruction,
            fewshot_mode=fewshot_mode or "rationale",
            mc_cond_depth=mc_cond_depth or "names",
            question_metadata=q,
        )
        gen_time = time.time() - gen_start
    except Exception as e:
        print(f"  ⚠ Gen failed Q{q_id} [{run_label}]: {e}")
        return None, None

    # ── Evaluate ──
    eval_start = time.time()
    try:
        metrics = evaluator.evaluate_generation(
            question_id=q_id,
            generated_distractors=[d.model_dump() for d in result.distractors],
        )
        eval_time = time.time() - eval_start
    except Exception as e:
        print(f"  ⚠ Eval failed Q{q_id} [{run_label}]: {e}")
        return None, None

    metrics.condition = run_label
    metrics.question_id = q_id

    record = {
        "condition": run_label,
        "question_id": q_id,
        "subject": q.get("SubjectName", ""),
        "run": run_idx,
        "generated": [d.model_dump() for d in result.distractors],
        "metrics": asdict(metrics),
        "conditioning": getattr(result, "model_extra", {}).get("conditioning_metadata", {}),
        "timing_s": {"generate": round(gen_time, 2), "evaluate": round(eval_time, 2)},
    }
    return metrics, record


def run_condition_parallel(
    gen: MCQGenerator,
    evaluator: MCQEvaluator,
    test_set: list[dict],
    condition: tuple,
    n_runs: int = 3,
    dry_run_n: int | None = None,
    n_workers: int = 3,
    progress_interval: int = 10,
    results_dir: Path = RESULTS_DIR,
) -> ConditionResults:
    """Run one condition with question-level parallelism and live progress."""
    name = condition[0]
    questions = test_set[:dry_run_n] if dry_run_n else test_set
    all_metrics: list[QuestionMetrics] = []
    n_total = len(questions)

    for run_idx in range(n_runs):
        run_label = f"{name}_run{run_idx}"
        t0 = time.time()

        done_lock = threading.Lock()
        done_count = [0]  # mutable container for closure
        total_questions = n_total  # local for closure

        def _progress_callback(_metrics, _record):
            with done_lock:
                done_count[0] += 1
                n = done_count[0]
                if n % progress_interval == 0 or n == total_questions:
                    elapsed = time.time() - t0
                    rate = elapsed / n
                    eta = rate * (total_questions - n)
                    print(f"\r  [{run_label}] {n}/{total_questions} questions "
                          f"({rate:.1f}s/q, ETA {eta:.0f}s)", end="", flush=True)

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(
                    _process_one_question,
                    q, gen, evaluator, condition, run_idx,
                    dry_run_n is not None,
                ): q
                for q in questions
            }
            for future in as_completed(futures):
                metrics, record = future.result()
                if metrics is not None and record is not None:
                    all_metrics.append(metrics)
                    _save_result(record, name, results_dir)
                    _progress_callback(metrics, record)

        elapsed = time.time() - t0
        n_done = len([m for m in all_metrics if m.condition == run_label])
        print(f"\r  Run {run_idx + 1}/{n_runs}: {n_done} questions "
              f"in {elapsed:.0f}s ({elapsed / max(1, n_done):.1f}s/q)" + " " * 20)

    cond_result = ConditionResults(condition_name=name, n_questions=len(all_metrics))
    cond_result.metrics = all_metrics
    return cond_result


def _run_single_condition(args: tuple) -> ConditionResults:
    """Top-level entry for ProcessPoolExecutor (serial condition run)."""
    (
        condition, test_set, n_runs, dry_run_n, n_workers, results_dir,
    ) = args

    # Each process needs its own bank/gen/eval instances
    _, gen, evaluator = _build_condition_components(condition)

    name = condition[0]
    print(f"\n{'─' * 50}")
    print(f"Condition: {name}")
    print(f"  System={condition[1]}, Instruction={condition[2]}, Strategy={condition[3]}")

    return run_condition_parallel(
        gen=gen, evaluator=evaluator,
        test_set=test_set, condition=condition,
        n_runs=n_runs, dry_run_n=dry_run_n,
        n_workers=n_workers,
        results_dir=results_dir,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 1a — MCQ experiment runner")
    parser.add_argument("--dry-run", action="store_true", help="Run on a small subset")
    parser.add_argument("--n", type=int, default=2, help="Questions per condition in dry-run mode")
    parser.add_argument("--runs", type=int, default=3, help="Number of stochastic runs per condition")
    parser.add_argument("--condition", type=str, default="", help="Run only this condition (name prefix)")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for new result artifacts; RAG runs default to a versioned directory",
    )
    parser.add_argument("--workers", type=int, default=3, help="Thread workers for question parallelism (×6 internal judge calls each)")
    parser.add_argument("--parallel-conds", action="store_true", help="Parallelize conditions via ProcessPool")
    parser.add_argument("--no-parallel", action="store_true", help="Disable all parallelism (debug)")
    args = parser.parse_args()

    n_workers = 1 if args.no_parallel else args.workers
    parallel_conds = args.parallel_conds and not args.no_parallel

    print("=" * 60)
    print("Phase 1a — MCQ Distractor Generation Experiment")
    mode = "dry-run" if args.dry_run else "full"
    print(f"  Mode: {mode} ({args.n} questions)" if args.dry_run else "  Mode: full (200 questions)")
    print(f"  Runs per condition: {args.runs}")
    print(f"  Question workers: {n_workers}")
    print(f"  Parallel conditions: {parallel_conds}")
    print("=" * 60)

    # Load data (shared across threads)
    print("\nLoading test set...")
    test_set = load_test_set(TEST_SET_PATH)
    print(f"  {len(test_set)} questions loaded")

    # Filter conditions
    conditions = [c for c in CONDITIONS if not args.condition or c[0].startswith(args.condition)]
    print(f"  {len(conditions)} conditions to run")

    results_dir = args.results_dir
    if results_dir is None:
        has_rag = any(condition[3] == "fewshot_rag" for condition in conditions)
        results_dir = RESULTS_DIR / "fewshot_rag_v2" if has_rag else RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Results directory: {results_dir}")

    # ── Run ──
    t_total = time.time()
    all_results: list[ConditionResults] = []

    if parallel_conds and len(conditions) > 1:
        # Level 3: condition-level parallelism (ProcessPool)
        max_cond_workers = min(len(conditions), os.cpu_count() or 4)
        print(f"\nRunning {len(conditions)} conditions in parallel "
              f"(ProcessPool, {max_cond_workers} workers)...\n")

        task_args = [
            (cond, test_set, args.runs,
             args.n if args.dry_run else None,
             n_workers, results_dir)
            for cond in conditions
        ]
        with ProcessPoolExecutor(max_workers=max_cond_workers) as pool:
            futures = [pool.submit(_run_single_condition, ta) for ta in task_args]
            n_cond_total = len(conditions)
            n_cond_done = 0
            for future in as_completed(futures):
                cr = future.result()
                all_results.append(cr)
                n_cond_done += 1
                s = cr.summary()
                print(f"\n── [{n_cond_done}/{n_cond_total}] {s['condition']} ──"
                      f"  PM={s['PM']:.3f}±{s['PM_std']:.3f}"
                      f"  TextSim={s['TextSim']:.3f}  EmbedSim={s['EmbedSim']:.3f}"
                      f"  Valid={s['Validity']:.3f}±{s['Validity_std']:.3f}"
                      f"  Div={s['Diversity']:.3f}±{s['Diversity_std']:.3f}")
    else:
        # Serial conditions (question-level parallelism still active inside)
        component_cache = {}

        n_cond_total = len(conditions)
        for i, condition in enumerate(conditions):
            component_key = "fewshot_rag" if condition[3] == "fewshot_rag" else "default"
            if component_key not in component_cache:
                component_cache[component_key] = _build_condition_components(condition)
            _, gen, evaluator = component_cache[component_key]
            name = condition[0]
            print(f"\n{'─' * 50}")
            print(f"[{i + 1}/{n_cond_total}] Condition: {name}")
            print(f"  System={condition[1]}, Instruction={condition[2]}, Strategy={condition[3]}")

            cr = run_condition_parallel(
                gen=gen, evaluator=evaluator,
                test_set=test_set, condition=condition,
                n_runs=args.runs,
                dry_run_n=args.n if args.dry_run else None,
                n_workers=n_workers,
                results_dir=results_dir,
            )
            all_results.append(cr)
            s = cr.summary()
            print(f"  → [{i + 1}/{n_cond_total}] PM={s['PM']:.3f}±{s['PM_std']:.3f}"
                  f"  TextSim={s['TextSim']:.3f}  EmbedSim={s['EmbedSim']:.3f}"
                  f"  Valid={s['Validity']:.3f}±{s['Validity_std']:.3f}"
                  f"  Div={s['Diversity']:.3f}±{s['Diversity_std']:.3f}")

    # ── Final table ──
    print(f"\n{'=' * 95}")
    print(f"{'Condition':<25} {'PM':>10} {'TextSim':>8} {'EmbedSim':>8} {'Valid':>10} {'Div':>8}")
    print(f"{'-' * 95}")
    # Sort by name for consistent output
    all_results.sort(key=lambda cr: cr.condition_name)
    for cr in all_results:
        s = cr.summary()
        print(f"{s['condition']:<25} {s['PM']:>8.3f}±{s['PM_std']:.2f}"
              f" {s['TextSim']:>8.3f} {s['EmbedSim']:>8.3f}"
              f" {s['Validity']:>8.3f}±{s['Validity_std']:.2f}"
              f" {s['Diversity']:>8.3f}±{s['Diversity_std']:.2f}")

    # Save aggregated results
    agg_path = results_dir / "aggregated.json"
    with open(agg_path, "w") as f:
        json.dump({cr.condition_name: cr.summary() for cr in all_results}, f, indent=2)
    print(f"\nAggregated results saved to {agg_path}")

    elapsed = time.time() - t_total
    print(f"Total time: {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print("Done.")


if __name__ == "__main__":
    main()
