"""Run and evaluate the improved PF pipeline (Learning Commons graph + D2a/D2b/D3 impasse package).

Executes a bounded 3-family x R-repeat pipeline generation experiment on the three
matched families (kapur_average_speed, loibl_variance, kerrigan_fair_division) using
the frozen learner repertoire plus the Learning Commons v1.14.0 progression graph
(target_standards, prerequisite_standards_builds_towards, supporting_learning_components),
and evaluates every produced task with both the frozen v2.1 evaluator and the frozen
v2.9 evaluator against the matched Direct generation baseline.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts import run_pf_diagnostic as diagnostic
from scripts import run_pf_fresh_comparison as fresh
from scripts.learning_commons_local import graph_progression_bundle
from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation import pf_three_role as v21
from src.evaluation.frozen import pf_three_role_v29 as v29
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/pf_pipeline_lc_impasse_v1_20261015"
CASES = fresh.CASES


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def student_task_text(task: dict) -> str:
    return "\n\n".join(
        str(task.get(k, "")).strip() for k in ("title", "body", "question") if task.get(k)
    )


def generate_one(case_name: str, repeat: int, output: Path) -> dict:
    attempt_dir = output / "generation" / case_name / f"{repeat:03d}"
    result_path = attempt_dir / "result.json"
    if result_path.exists():
        saved = json.loads(result_path.read_text())
        if saved.get("status") != "running":
            return saved
    if attempt_dir.exists():
        shutil.rmtree(attempt_dir)
    case, packet, shared = fresh.fixed_inputs(case_name)
    lc_bundle = graph_progression_bundle(case["id"])
    if lc_bundle is not None:
        shared = {**shared, "learning_commons_knowledge_graph": lc_bundle}
    d1_path = output / "generation" / case_name / "fixed_d1.json"
    if not d1_path.exists():
        save(d1_path, packet)
    return diagnostic.run_case_worker(
        case["id"],
        str(attempt_dir),
        "luna",
        2,
        str(d1_path),
        case_override=case,
        shared_context=shared,
    )


def evaluate_task(
    key: str,
    task_text: str,
    target: str,
    learner_context: dict,
    chats: dict,
    output: Path,
) -> dict:
    eval_path = output / "evaluations" / f"{key}.json"
    if eval_path.exists():
        return json.loads(eval_path.read_text())
    with ThreadPoolExecutor(max_workers=2) as pool:
        f29 = pool.submit(
            v29.evaluate_v29,
            task_text,
            target,
            copy.deepcopy(learner_context),
            solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
            judge_chat=chats["luna"],
        )
        f21 = pool.submit(
            v21.evaluate,
            task_text,
            target,
            copy.deepcopy(learner_context),
            solver_chat=chats["luna"],
            judge_chat=chats["luna"],
        )
        res_v29 = f29.result()
        res_v21 = f21.result()
    record = {
        "key": key,
        "evaluated_at": now(),
        "v29": res_v29,
        "v21": res_v21,
    }
    save(eval_path, record)
    return record


def summarize_evaluations(items: list[dict], version_key: str) -> dict:
    counts = {m: Counter() for m in MEASURES}
    all5_yes = 0
    for item in items:
        ms = item[version_key]["measures"]
        for m in MEASURES:
            val = ms[m]["value"]
            counts[m][str(val) if val is not None else ms[m]["status"]] += 1
        if all(ms[m]["value"] == "yes" for m in MEASURES):
            all5_yes += 1
    return {
        "tasks_evaluated": len(items),
        "all_5_yes": all5_yes,
        "measures": {m: dict(counts[m]) for m in MEASURES},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cases", nargs="+", default=list(CASES))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        for name in args.cases:
            case, _, _ = fresh.fixed_inputs(name)
            lc = graph_progression_bundle(case["id"])
            print(
                f"{name}: target_stds={len(lc['target_standards'])}, "
                f"prereq_stds={len(lc['prerequisite_standards_builds_towards'])}, "
                f"components={len(lc['supporting_learning_components'])}"
            )
        print(f"Total pipeline generations scheduled: {len(args.cases) * args.repeats}")
        return

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_hashes = diagnostic.compute_source_hashes()
    for p in (
        Path(__file__),
        ROOT / "scripts/learning_commons_local.py",
        ROOT / "src/evaluation/frozen/pf_three_role_v29.py",
    ):
        source_hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()

    jobs = [(name, r) for name in args.cases for r in range(1, args.repeats + 1)]
    gen_records = {}
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        futs = {pool.submit(generate_one, name, r, output): (name, r) for name, r in jobs}
        for fut in as_completed(futs):
            name, r = futs[fut]
            rec = fut.result()
            gen_records[(name, r)] = rec
            d2b_status = ((rec.get("stages") or {}).get("D2_D3") or {}).get("design_data", {})
            print(
                f"[GEN] {name} #{r:03d}: status={rec.get('status')} "
                f"d2b={d2b_status.get('status') if isinstance(d2b_status, dict) else None}",
                flush=True,
            )

    chats = build_chats()
    eval_jobs = []
    for name, r in jobs:
        rec = gen_records[(name, r)]
        task = ((rec.get("stages") or {}).get("D2_D3") or {}).get("task")
        if fresh.task_is_produced(task):
            case, _, shared = fresh.fixed_inputs(name)
            eval_jobs.append(
                (
                    f"{name}__{r:03d}",
                    student_task_text(task),
                    case["target_concept"],
                    shared["learner_context"],
                )
            )

    eval_records = []
    with ThreadPoolExecutor(max_workers=max(1, len(eval_jobs))) as pool:
        futs = {
            pool.submit(evaluate_task, key, text, target, ctx, chats, output): key
            for key, text, target, ctx in eval_jobs
        }
        for fut in as_completed(futs):
            key = futs[fut]
            er = fut.result()
            eval_records.append(er)
            ms29 = {k: v["value"] for k, v in er["v29"]["measures"].items()}
            ms21 = {k: v["value"] for k, v in er["v21"]["measures"].items()}
            print(f"[EVAL] {key}: v2.9={ms29} | v2.1={ms21}", flush=True)

    summary = {
        "generated_at": now(),
        "source_hashes": source_hashes,
        "scheduled": len(jobs),
        "produced": len(eval_jobs),
        "v29_summary": summarize_evaluations(eval_records, "v29"),
        "v21_summary": summarize_evaluations(eval_records, "v21"),
        "per_task": [
            {
                "key": er["key"],
                "v29_measures": {k: v["value"] for k, v in er["v29"]["measures"].items()},
                "v29_approach_counts": er["v29"].get("approach_counts"),
                "v21_measures": {k: v["value"] for k, v in er["v21"]["measures"].items()},
            }
            for er in sorted(eval_records, key=lambda x: x["key"])
        ],
    }
    save(output / "summary.json", summary)
    print(json.dumps({"v29": summary["v29_summary"], "v21": summary["v21_summary"]}, indent=2))


if __name__ == "__main__":
    main()
