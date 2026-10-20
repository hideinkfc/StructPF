#!/usr/bin/env python3
"""Test Family 3 — Rahimi et al. (2025) PF rubric on 30 questions.

Runs the baseline condition (02_expert_direct) on 30 questions and prints
the PF rubric scores alongside existing F1 + F2 metrics.

Usage:
    python scripts/test_pf_rubric.py
    python scripts/test_pf_rubric.py --n 10   # quick test on 10 questions
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.evaluation.mcq_metrics import MCQEvaluator
from src.generation.mcq_generator import MCQGenerator
from src.generation.misconception_bank import MisconceptionBank


def main():
    parser = argparse.ArgumentParser(description="Test PF rubric evaluation")
    parser.add_argument("--n", type=int, default=30, help="Number of questions to evaluate")
    parser.add_argument(
        "--condition", type=str, default="02_expert_direct", help="Which condition to run"
    )
    args = parser.parse_args()

    N = min(args.n, 200)

    print("=" * 70)
    print("Family 3 — Rahimi et al. (2025) PF Rubric Test")
    print(f"  Questions: {N}")
    print(f"  Condition: {args.condition}")
    print("  Model: meta-llama/Llama-3.3-70B-Instruct")
    print("=" * 70)

    # Load
    print("\nLoading data...")
    bank = MisconceptionBank().load()
    test_set_path = Path("data/eedi/test_set_200.json")
    with open(test_set_path) as f:
        test_set = json.load(f)
    test_set = test_set[:N]

    gen = MCQGenerator(bank=bank)
    evaluator = MCQEvaluator(bank)

    # Map condition name → variants
    cond_map = {
        "02_expert_direct": ("expert", "direct", "zero_shot", "", ""),
        "05_expert_self_critique": ("expert", "self_critique", "zero_shot", "", ""),
        "06_lookalike_direct": ("lookalike", "direct", "zero_shot", "", ""),
        "07_expert_mc_names": ("expert", "direct", "misconception_conditioned", "", "names"),
    }
    sys_var, inst_var, strat, fs, mc_d = cond_map.get(
        args.condition, ("expert", "direct", "zero_shot", "", "")
    )

    # Run
    all_metrics = []
    pf_scores = []
    t0 = time.time()

    for i, q in enumerate(test_set):
        correct_letter = q.get("CorrectAnswer", "")
        correct_text = q.get(f"Answer{correct_letter}Text", "")

        try:
            result = gen.generate(
                question_text=str(q.get("QuestionText", "")),
                correct_answer=str(correct_text),
                strategy=strat,
                n_distractors=3,
                temperature=0.7,
                system_variant=sys_var,
                instruction_variant=inst_var,
                fewshot_mode=fs or "rationale",
                mc_cond_depth=mc_d or "names",
            )
        except Exception as e:
            print(f"  ⚠ Gen failed Q{q['QuestionId']}: {e}")
            continue

        try:
            metrics = evaluator.evaluate_generation(
                question_id=q["QuestionId"],
                generated_distractors=[d.model_dump() for d in result.distractors],
            )
        except Exception as e:
            print(f"  ⚠ Eval failed Q{q['QuestionId']}: {e}")
            continue

        all_metrics.append(metrics)
        if metrics.pf_rubric:
            pf_scores.append(metrics.pf_rubric)

        # Progress
        elapsed = time.time() - t0
        avg_t = elapsed / (i + 1)
        eta = avg_t * (N - i - 1)
        print(
            f"\r  [{i + 1}/{N}] {elapsed:.0f}s elapsed, {avg_t:.0f}s/q, ETA {eta:.0f}s",
            end="",
            flush=True,
        )

    print()

    # ── Results ──
    print(f"\n{'─' * 80}")
    print(f"PF Rubric Results — {len(pf_scores)} questions evaluated")
    print(f"{'─' * 80}")

    apk_vals = [p.activation_prior_knowledge for p in pf_scores]
    ssc_vals = [p.sweet_spot_calibration for p in pf_scores]
    ae_vals = [p.affective_engagement for p in pf_scores]
    mr_vals = [p.multiple_representations for p in pf_scores]
    oe_vals = [p.open_endedness for p in pf_scores]
    fin_vals = [p.final_score for p in pf_scores]

    print(f"\n{'Dimension':<35s} {'Mean':>8s} {'Std':>8s} {'Min':>6s} {'Max':>6s}")
    print(f"{'─' * 65}")
    for name, vals in [
        ("Activation of Prior Knowledge (APK)", apk_vals),
        ("Sweet Spot Calibration (SSC)", ssc_vals),
        ("Affective Engagement (AE)", ae_vals),
        ("Multiple Representations (MR)", mr_vals),
        ("Open-Endedness (OE)", oe_vals),
        ("FINAL SCORE (sum, 5–15)", fin_vals),
    ]:
        print(
            f"{name:<35s} {np.mean(vals):>8.2f} {np.std(vals):>8.2f} "
            f"{min(vals):>6.1f} {max(vals):>6.1f}"
        )

    # Distribution of final scores
    print("\nFinal Score Distribution:")
    for lo in range(5, 16):
        cnt = sum(1 for v in fin_vals if lo <= v < lo + 1)
        bar = "█" * cnt
        print(f"  {lo:2d}: {bar} ({cnt})")

    # Top-level metrics comparison
    pm_vals = [m.pm for m in all_metrics]
    val_vals = [m.validity for m in all_metrics]
    div_vals = [m.diversity for m in all_metrics]

    print(f"\n{'─' * 80}")
    print(f"Cross-family comparison (n={len(all_metrics)}):")
    print(f"  F1 — PM:        {np.mean(pm_vals):.1%} ± {np.std(pm_vals):.1%}")
    print(f"  F2 — Validity:  {np.mean(val_vals):.1%} ± {np.std(val_vals):.1%}")
    print(f"  F2 — Diversity: {np.mean(div_vals):.1%} ± {np.std(div_vals):.1%}")
    print(
        f"  F3 — PF Final:  {np.mean(fin_vals):.1f}/15 ± {np.std(fin_vals):.1f} "
        f"({np.mean(fin_vals) / 15:.1%})"
    )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s ({elapsed / max(1, len(all_metrics)):.0f}s/q)")
    print("Done.")


if __name__ == "__main__":
    main()
