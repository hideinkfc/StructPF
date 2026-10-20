#!/usr/bin/env python3
"""Dry-run the main condition grid on N questions with progress bar."""

import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tqdm import tqdm
from scripts.run_phase1_mcq import CONDITIONS, _build_condition_components
from src.evaluation.mcq_metrics import ConditionResults

N = 3

base = Path(__file__).resolve().parents[1]
results_dir = base / "experiments" / "results" / "phase1_mcq"
results_dir.mkdir(parents=True, exist_ok=True)

with open(base / "data" / "eedi" / "test_set_200.json") as f:
    test_set = json.load(f)

component_cache = {}
questions = test_set[:N]

total = len(CONDITIONS) * N
pbar = tqdm(total=total, desc="Generating", unit="gen")

all_results = []
per_q = []

for name, sys_var, inst, strat, fs, mc_d in CONDITIONS:
    component_key = "fewshot_rag" if strat == "fewshot_rag" else "default"
    if component_key not in component_cache:
        component_cache[component_key] = _build_condition_components(
            (name, sys_var, inst, strat, fs, mc_d)
        )
    _, gen, evaluator = component_cache[component_key]
    cond_metrics = []
    for q in questions:
        cl = q["CorrectAnswer"]
        ct = q.get(f"Answer{cl}Text", "")
        qid = q["QuestionId"]
        try:
            r = gen.generate(
                question_text=str(q["QuestionText"]),
                correct_answer=str(ct),
                strategy=strat, n_distractors=3, temperature=0.7,
                system_variant=sys_var, instruction_variant=inst,
                fewshot_mode=fs or "rationale",
                mc_cond_depth=mc_d or "names",
                question_metadata=q,
            )
            m = evaluator.evaluate_generation(
                question_id=qid,
                generated_distractors=[d.model_dump() for d in r.distractors],
            )
            m.condition = name
            cond_metrics.append(m)
            per_q.append({
                "condition": name, "question_id": qid,
                "texts": [d.text for d in r.distractors],
                "misconceptions": [d.target_misconception for d in r.distractors],
                "pm": m.pm,
                "validity": m.validity, "diversity": m.diversity,
                "conditioning": getattr(r, "model_extra", {}).get("conditioning_metadata", {}),
            })
            pbar.set_postfix_str(f"{name} Q{qid} PM={m.pm:.2f}")
        except Exception as e:
            pbar.write(f"  FAIL {name} Q{qid}: {e}")
        pbar.update(1)

    cr = ConditionResults(condition_name=name, n_questions=len(cond_metrics))
    cr.metrics = cond_metrics
    all_results.append(cr)

pbar.close()

# Save
with open(results_dir / "dry_run_with_fewshot_rag_per_question.json", "w") as f:
    json.dump(per_q, f, indent=2)
with open(results_dir / "dry_run_with_fewshot_rag_aggregated.json", "w") as f:
    summaries = [
        {"condition": c.condition_name, "n": c.n_questions, **c.summary()}
        for c in all_results
    ]
    json.dump(summaries, f, indent=2)

# Print table
print(f"\n{'Condition':<25} {'PM':>8} {'Valid':>8} {'Div':>8}")
print("-" * 58)
for cr in all_results:
    s = cr.summary()
    print(f"{s['condition']:<25} {s['PM']:>8.3f} {s['Validity']:>8.3f} {s['Diversity']:>8.3f}")
print("-" * 58)
print("Saved to experiments/results/phase1_mcq/dry_run_with_fewshot_rag_*.json")
