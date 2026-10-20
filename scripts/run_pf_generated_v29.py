"""Evaluate saved generated PF task cohorts with the frozen v2.9 evaluator.

Runs v2.9 (Task Judge with accessibility gate + 2 resource-sweep Solvers + Attempt Judge)
on saved generated cohorts from catalog.json and comparison_groups.json, and aggregates
the five measures by cohort (Direct vs. Pipeline, Benchmark v4 V1/V2/V3/PIPELINE, and
Rahimi Main30 direct-generation cells).
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_pf_accessibility_sensitivity import build_chats
from scripts.run_pf_measure_campaign import case_inputs
from src.evaluation import pf_three_role_v29 as v29
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "experiments/results/pf_measure_campaign_20261014/catalog.json"
GROUPS = ROOT / "experiments/results/pf_measure_campaign_20261014/comparison_groups.json"
OUTPUT = ROOT / "experiments/results/pf_generated_tasks_v29_20261015"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def select_cohorts(limit_per_large_cohort: int = 4) -> tuple[list[dict], dict[str, dict]]:
    cat = json.loads(CATALOG.read_text())
    by_id = {c["case_id"]: c for c in cat["cases"]}
    cg = json.loads(GROUPS.read_text())
    selected_cohorts = []
    needed_ids: dict[str, dict] = {}
    for rc in cg["report_cohorts"]:
        label = rc["label"]
        if label.startswith("Latest fresh method comparison"):
            cids = list(rc["case_ids"])
        elif label.startswith("Benchmark v4 ") or label.startswith("Main30 "):
            cids = list(rc["case_ids"])[:limit_per_large_cohort]
        else:
            continue
        selected_cohorts.append({"label": label, "case_ids": cids})
        for cid in cids:
            needed_ids[cid] = by_id[cid]
    return selected_cohorts, needed_ids


def has_api_error(result: dict) -> bool:
    if (result.get("task_judge") or {}).get("status") == "api_error":
        return True
    if (result.get("attempt_judge") or {}).get("status") == "api_error":
        return True
    for s in (result.get("solvers") or {}).values():
        if s.get("status") == "api_error":
            return True
    return False


def run_one(case: dict, chats: dict, output: Path) -> dict:
    cid = case["case_id"]
    path = output / "jobs" / f"{cid}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("status") == "completed" and not has_api_error(saved.get("result") or {}):
            return saved
    prepared = case_inputs(copy.deepcopy(case))
    record = {"case_id": cid, "started_at": now()}
    for attempt in range(2):
        result = v29.evaluate_v29(
            prepared["student_task"],
            prepared["learning_target"],
            copy.deepcopy(prepared["learner_context"]),
            solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
            judge_chat=chats["luna"],
        )
        record.update({"status": "completed", "attempts_run": attempt + 1, "result": result})
        if not has_api_error(result):
            break
    record["finished_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def summarize(cohorts: list[dict], records: dict[str, dict]) -> dict:
    cohort_rows = []
    for cohort in cohorts:
        cids = cohort["case_ids"]
        measure_counts = {m: Counter() for m in MEASURES}
        approach_totals = []
        pf_pass_count = 0
        fancy_routine_count = 0
        giveaway_count = 0
        solved_by_prior_count = 0
        genuine_impasse_count = 0
        for cid in cids:
            res = records[cid]["result"]
            ms = res["measures"]
            for m in MEASURES:
                val = ms[m]["value"]
                measure_counts[m][str(val) if val is not None else ms[m]["status"]] += 1
            approach_totals.append(res.get("approach_items_judged", 0))
            inv = ms["room_for_invention"]["value"]
            lim = ms["familiar_approach_limits"]["value"]
            cnt = res.get("approach_counts") or {}
            md = cnt.get("meets_demands", 0)
            tl = cnt.get("target_limits", 0)
            if md > 0:
                solved_by_prior_count += 1
            elif tl > 0 and inv == "yes":
                genuine_impasse_count += 1
            if inv in {"no", "partly"}:
                giveaway_count += 1
            elif inv == "yes" and lim == "no":
                fancy_routine_count += 1
            elif inv == "yes" and lim == "yes":
                pf_pass_count += 1
        cohort_rows.append(
            {
                "label": cohort["label"],
                "cases": len(cids),
                "mean_pooled_approaches": round(sum(approach_totals) / len(approach_totals), 2)
                if approach_totals
                else 0.0,
                "solved_by_prior_knowledge_meets_demands_gt_0": solved_by_prior_count,
                "genuine_pf_impasse_inv_yes_md_0_tl_gt_0": genuine_impasse_count,
                "real_pf_opportunity_inv_yes_lim_yes": pf_pass_count,
                "fancy_wording_routine_inv_yes_lim_no": fancy_routine_count,
                "giveaway_or_guided_inv_no_or_partly": giveaway_count,
                "measures": {m: dict(measure_counts[m]) for m in MEASURES},
            }
        )
    return {
        "version": v29.VERSION,
        "generated_at": now(),
        "total_unique_cases": len(records),
        "cohorts": cohort_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-per-cohort", type=int, default=4)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    cohorts, needed = select_cohorts(args.limit_per_cohort)
    if args.dry_run:
        print(f"{len(cohorts)} cohorts selected; {len(needed)} unique cases to evaluate")
        for c in cohorts:
            print(f"  {c['label']:55s}: {len(c['case_ids'])} cases")
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    chats = build_chats()
    records = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, case, chats, output): cid for cid, case in needed.items()}
        for idx, fut in enumerate(as_completed(futs), 1):
            cid = futs[fut]
            records[cid] = fut.result()
            ms = records[cid]["result"]["measures"]
            print(
                f"[{idx}/{len(needed)}] {cid}: "
                f"align={ms['target_alignment']['value']} "
                f"access={ms['prior_knowledge_accessibility']['value']} "
                f"invent={ms['room_for_invention']['value']} "
                f"limits={ms['familiar_approach_limits']['value']} "
                f"(approaches={records[cid]['result']['approach_items_judged']})",
                flush=True,
            )
    summary = summarize(cohorts, records)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {output / 'summary.json'}")


if __name__ == "__main__":
    main()
