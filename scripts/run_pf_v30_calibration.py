"""Calibrate and evaluate pf-three-role/v3.0 across development, control, fixture, sensitivity, transfer, and generated cohorts."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation import pf_three_role_v30 as v30
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation.frozen import pf_three_role_v28 as v28
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "experiments/results/pf_measure_campaign_20261014/calibration_pack.json"
SENS_PATH = ROOT / "experiments/configs/pf_accessibility_sensitivity_strict_labels_20261015.json"
OUTPUT_BASE = ROOT / "experiments/results/pf_v30_calibration_20261015"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_task_judge_case(case: dict, chat, out_dir: Path) -> dict:
    cid = case["case_id"]
    path = out_dir / "task_judge_jobs" / f"{cid}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("job", {}).get("status") == "completed":
            return saved
    prepared = v25.prepare_input(
        case["student_task"], case["learning_target"], copy.deepcopy(case["learner_context"])
    )
    payload = v22.role_input("task_judge", prepared)
    job = v30.run_judge_v30("task_judge", payload, chat)
    if job["status"] == "completed":
        measures = v30.parse_task_v30(job["output"], prepared)
    else:
        measures = {
            m: v22._row(None, job["status"], error=job["error"])
            for m in ("target_alignment", "room_for_invention", "prior_knowledge_accessibility")
        }
        measures["mathematical_validity"] = v22._row(
            "not_assessed", "not_assessed", {"prerequisite_status": job["status"]}
        )
    rec = {"case_id": cid, "status": job["status"], "measures": measures, "job": job}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return rec


def run_attempt_fixture(group: dict, case_map: dict[str, dict], chat, out_dir: Path) -> dict:
    gid = group["id"]
    path = out_dir / "fixture_jobs" / f"{gid}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("job", {}).get("status") == "completed":
            return saved
    case = case_map[group["case_id"]]
    prepared = v25.prepare_input(
        case["student_task"], case["learning_target"], copy.deepcopy(case["learner_context"])
    )
    attempts = [
        {
            "solver": "fixture",
            "solver_attempt_index": idx,
            "idea": item["idea"],
            "principle": item["idea"],
            "method_kind": "structured",
            "trial_count": None,
            "toolkit_used": [],
            "work": item["work"],
        }
        for idx, item in enumerate(group["attempts"])
    ]
    payload = v22.role_input("attempt_judge", prepared, attempts)
    job = v30.run_judge_v30("attempt_judge", payload, chat)
    parsed = (
        v28.parse_attempts_v28(job["output"], attempts) if job["status"] == "completed" else None
    )
    rec = {
        "group_id": gid,
        "case_id": group["case_id"],
        "status": job["status"],
        "parsed": parsed,
        "job": job,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return rec


def run_full_case(case: dict, chats: dict, out_dir: Path, subdir: str = "full_jobs") -> dict:
    cid = case["case_id"]
    path = out_dir / subdir / f"{cid}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        res = saved.get("result") or {}
        if (
            saved.get("status") == "completed"
            and (res.get("task_judge") or {}).get("status") == "completed"
        ):
            return saved
    record = {"case_id": cid, "started_at": now()}
    tj_cache = out_dir / "task_judge_jobs" / f"{cid}.json"
    cached_tj = None
    if tj_cache.exists():
        tj_rec = json.loads(tj_cache.read_text())
        if tj_rec.get("status") == "completed":
            cached_tj = tj_rec["job"]

    def judge_chat_with_cache(messages):
        if cached_tj is not None and '"attempts"' not in messages[1]["content"]:
            from src.utils.llm_client import LLMResponse

            last_resp = cached_tj["calls"][-1]["response"]
            return LLMResponse(
                text=json.dumps(cached_tj["output"], ensure_ascii=False),
                model=last_resp["model"],
                finish_reason=last_resp["finish_reason"],
                usage=last_resp["usage"],
            )
        return chats["luna"](messages)

    result = v30.evaluate_v30(
        case["student_task"],
        case["learning_target"],
        copy.deepcopy(case["learner_context"]),
        solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
        judge_chat=judge_chat_with_cache,
    )
    record.update({"status": "completed", "result": result, "finished_at": now()})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=["judges_only", "full_dev", "transfer", "generated", "lc_pipeline"],
        default="judges_only",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_BASE)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    pack = json.loads(PACK_PATH.read_text())
    dev_cases = pack["development"] + pack["controls"]
    transfer_cases = pack["transfer"]
    all_case_map = {c["case_id"]: c for c in dev_cases + transfer_cases}
    sens_cases = json.loads(SENS_PATH.read_text())["cases"]
    chats = build_chats()
    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.phase == "judges_only":
        tj_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_task_judge_case, c, chats["luna"], out_dir): c["case_id"]
                for c in dev_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                tj_results[rec["case_id"]] = rec
        # Compare against calibration_pack references
        tj_matches = Counter()
        tj_diffs = []
        for c in dev_cases:
            cid = c["case_id"]
            ms = tj_results[cid]["measures"]
            for m in (
                "target_alignment",
                "mathematical_validity",
                "prior_knowledge_accessibility",
                "room_for_invention",
            ):
                obs = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                exp = c["references"][m]["acceptable_values"]
                if obs in exp:
                    tj_matches[m] += 1
                else:
                    tj_diffs.append(
                        {
                            "case_id": cid,
                            "measure": m,
                            "observed": obs,
                            "expected": exp,
                            "evidence": ms[m]["evidence"],
                        }
                    )

        # Sensitivity cases
        sens_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_task_judge_case, c, chats["luna"], out_dir): c["case_id"]
                for c in sens_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                sens_results[rec["case_id"]] = rec
        sens_matches = 0
        sens_scored = 0
        sens_diffs = []
        for c in sens_cases:
            cid = c["case_id"]
            exp = c["strict_label"]
            obs = sens_results[cid]["measures"]["prior_knowledge_accessibility"]["value"]
            if exp in {"yes", "no"}:
                sens_scored += 1
                if obs == exp:
                    sens_matches += 1
                else:
                    sens_diffs.append({"case_id": cid, "observed": obs, "expected": exp})

        # Attempt fixtures
        fix_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_attempt_fixture, g, all_case_map, chats["luna"], out_dir): g["id"]
                for g in pack["attempt_fixture_groups"]
            }
            for fut in as_completed(futs):
                rec = fut.result()
                fix_results[rec["group_id"]] = rec
        fix_matches = 0
        fix_total = 0
        fix_diffs = []
        for g in pack["attempt_fixture_groups"]:
            gid = g["id"]
            if gid == "concrete_no_start":
                continue
            rec = fix_results[gid]
            audits = (
                (rec.get("parsed") or {})
                .get("measures", {})
                .get("familiar_approach_limits", {})
                .get("evidence", {})
                .get("attempts", [])
            )
            for exp_rev in g["expected_reviews"]:
                idx = exp_rev["attempt_index"]
                exp_st = exp_rev["status"]
                obs_st = audits[idx]["status"] if idx < len(audits) else None
                fix_total += 1
                if obs_st == exp_st:
                    fix_matches += 1
                else:
                    fix_diffs.append(
                        {
                            "group_id": gid,
                            "index": idx,
                            "observed": obs_st,
                            "expected": exp_st,
                            "reason": audits[idx]["reason"] if idx < len(audits) else None,
                        }
                    )

        summary = {
            "version": v30.VERSION,
            "prompt_sha256": v30.fingerprint(),
            "dev_task_judge_matches_of_20": dict(tj_matches),
            "dev_task_judge_diffs": tj_diffs,
            "strict_sensitivity_matches": f"{sens_matches}/{sens_scored}",
            "strict_sensitivity_diffs": sens_diffs,
            "attempt_fixture_matches": f"{fix_matches}/{fix_total}",
            "attempt_fixture_diffs": fix_diffs,
        }
        (out_dir / "judges_only_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return

    if args.phase == "full_dev":
        full_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_full_case, c, chats, out_dir, "full_dev_jobs"): c["case_id"]
                for c in dev_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                full_results[rec["case_id"]] = rec
                print(f"done {rec['case_id']}", flush=True)
        matches = Counter()
        diffs = []
        for c in dev_cases:
            cid = c["case_id"]
            ms = full_results[cid]["result"]["measures"]
            for m in MEASURES:
                obs = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                exp = c["references"][m]["acceptable_values"]
                if obs in exp:
                    matches[m] += 1
                else:
                    diffs.append({"case_id": cid, "measure": m, "observed": obs, "expected": exp})
        summary = {
            "version": v30.VERSION,
            "full_dev_matches_of_20": dict(matches),
            "full_dev_diffs": diffs,
        }
        (out_dir / "full_dev_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return

    if args.phase == "transfer":
        trans_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_full_case, c, chats, out_dir, "transfer_jobs"): c["case_id"]
                for c in transfer_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                trans_results[rec["case_id"]] = rec
                print(f"done {rec['case_id']}", flush=True)
        matches = Counter()
        diffs = []
        for c in transfer_cases:
            cid = c["case_id"]
            ms = trans_results[cid]["result"]["measures"]
            for m in MEASURES:
                obs = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                exp = c["references"][m]["acceptable_values"]
                if obs in exp:
                    matches[m] += 1
                else:
                    diffs.append({"case_id": cid, "measure": m, "observed": obs, "expected": exp})
        summary = {
            "version": v30.VERSION,
            "transfer_matches_of_9": dict(matches),
            "transfer_diffs": diffs,
        }
        (out_dir / "transfer_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return

    if args.phase == "generated":
        from scripts.run_pf_generated_v29 import select_cohorts
        from scripts.run_pf_measure_campaign import case_inputs

        cohorts, needed_ids = select_cohorts(limit_per_large_cohort=2)
        gen_cases = []
        for cid, raw_case in needed_ids.items():
            prep = case_inputs(copy.deepcopy(raw_case))
            gen_cases.append(
                {
                    "case_id": cid,
                    "student_task": prep["student_task"],
                    "learning_target": prep["learning_target"],
                    "learner_context": prep["learner_context"],
                }
            )
        gen_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_full_case, c, chats, out_dir, "generated_jobs"): c["case_id"]
                for c in gen_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                gen_results[rec["case_id"]] = rec
                print(f"done {rec['case_id']}", flush=True)

        overall = {m: Counter() for m in MEASURES}
        all_five_yes_and_no_prior_solve = 0
        all_five_yes_total = 0
        solved_by_prior = 0
        for cid, rec in gen_results.items():
            res = rec["result"]
            ms = res["measures"]
            for m in MEASURES:
                val = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                overall[m][str(val)] += 1
            cnt = res.get("approach_counts") or {}
            md = cnt.get("meets_demands", 0)
            tl = cnt.get("target_limits", 0)
            if md > 0:
                solved_by_prior += 1
            if all(ms[m]["value"] == "yes" for m in MEASURES):
                all_five_yes_total += 1
                if md == 0 and tl > 0:
                    all_five_yes_and_no_prior_solve += 1

        summary = {
            "version": v30.VERSION,
            "prompt_sha256": v30.fingerprint(),
            "total_generated_cases": len(gen_results),
            "overall_measures": {m: dict(c) for m, c in overall.items()},
            "solved_by_prior_meets_demands_gt_0": solved_by_prior,
            "all_five_yes_total": all_five_yes_total,
            "genuine_pf_impasse_all_five_yes_and_md_0": all_five_yes_and_no_prior_solve,
        }
        (out_dir / "generated_v30_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return

    if args.phase == "lc_pipeline":
        lc_dir = ROOT / "experiments/results/pf_pipeline_lc_impasse_v3_20261015/evaluations"
        lc_cases = []
        for p in sorted(lc_dir.glob("*.json")):
            ev = json.loads(p.read_text())
            inp = ev["v29"]["task_judge"]["input"]
            lc_cases.append(
                {
                    "case_id": ev["key"],
                    "student_task": inp["student_task"],
                    "learning_target": inp["learning_target"],
                    "learner_context": inp["learner_context"],
                }
            )
        lc_results = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(run_full_case, c, chats, out_dir, "lc_pipeline_jobs"): c["case_id"]
                for c in lc_cases
            }
            for fut in as_completed(futs):
                rec = fut.result()
                lc_results[rec["case_id"]] = rec
                print(f"done {rec['case_id']}", flush=True)
        overall = {m: Counter() for m in MEASURES}
        all5 = 0
        for cid, rec in sorted(lc_results.items()):
            ms = rec["result"]["measures"]
            for m in MEASURES:
                val = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                overall[m][str(val)] += 1
            if all(ms[m]["value"] == "yes" for m in MEASURES):
                all5 += 1
        summary = {
            "version": v30.VERSION,
            "prompt_sha256": v30.fingerprint(),
            "tasks": len(lc_results),
            "all_five_yes": all5,
            "measures": {m: dict(c) for m, c in overall.items()},
        }
        (out_dir / "lc_pipeline_v30_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
