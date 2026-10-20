"""Evaluate the newest PF pipeline against the Rahimi Table 1 rubric and pf-three-role/v3.0.

Executes two complementary phases (all per-task jobs cached to disk):
  Phase 1 (--phase saved_cohorts):
    Rates all already-saved newest pipeline cohorts with the frozen Rahimi Table 1
    5-dimension rubric (APK, SSC, AE, MR, OE; 1-3 each, max 15; two passes of Luna):
      - Improved Pipeline Round 2 (pf_pipeline_lc_impasse_v3_20261015, n = 9)
      - Improved Pipeline Round 1 (pf_pipeline_lc_impasse_v2_20261015, n = 9)
      - Generalized Pipeline Check (pf_pipeline_generalized_check_20261016, n = 3)
      - 20-Topic Progression Bridge Study (pf_progression_bridge_20cases_20261016:
        Direct n = 20, Pipeline Ungrounded n = 20, Pipeline LC-Grounded n = 20)

  Phase 2 (--phase rahimi_cells):
    Runs the newest generalized Learning Commons + Impasse pipeline on the 4 Grade-7
    cells of the Rahimi Multi-Theme Benchmark (sports_basketball_ratio,
    shopping_percent, music_compare_distributions, garden_composite_area; R repeats per
    cell), and evaluates every generated task with BOTH:
      1. The exact two-pass blinded Rahimi Table 1 setting judge (pf_rubric_setting.py)
      2. The frozen pf-three-role/v3.0 strict 5-measure evaluator (pf_three_role_v30.py)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts import run_pf_diagnostic as diagnostic
from scripts.learning_commons_local import load_snapshot, summarize_node
from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation import pf_rubric, pf_rubric_setting
from src.evaluation import pf_three_role_v30 as v30
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
SETTING_PATH = ROOT / "experiments/configs/pf_rahimi_multi_theme_setting.json"
MAIN30_SUMMARY_PATH = ROOT / "experiments/results/pf_rahimi_multi_theme_20261013/main_30/summary.json"
LC_BRIDGE_SNAP = ROOT / "data/learning_commons/progression_bridge_v1"
DEFAULT_OUTPUT = ROOT / "experiments/results/pf_newest_pipeline_rahimi_eval_20261016"
DIMENSIONS = pf_rubric.DIMENSIONS


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clean_learner_context(ctx: dict[str, Any]) -> dict[str, Any]:
    priors = []
    for item in ctx.get("assumed_prior_knowledge") or []:
        if isinstance(item, str):
            r = item.strip()
            priors.append({"resource": r, "taught_as": r})
        elif isinstance(item, dict) and isinstance(item.get("resource"), str):
            r = item["resource"].strip()
            ta = item.get("taught_as")
            ta_str = ta.strip() if isinstance(ta, str) and ta.strip() else r
            priors.append({"resource": r, "taught_as": ta_str})
    return {
        "grade": str(ctx.get("grade", "7")),
        "subject": str(ctx.get("subject", "mathematics")),
        "jurisdiction": str(ctx.get("jurisdiction") or ctx.get("country") or "USA"),
        "assumed_prior_knowledge": priors,
    }


def rate_one_table1(
    task_id: str,
    cohort: str,
    student_task: str,
    learner_ctx: dict[str, Any],
    chat,
    out_dir: Path,
    *,
    case_setting: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out_path = out_dir / "table1_ratings" / f"{task_id}.json"
    if out_path.exists():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed" and saved.get("mean_scores"):
            return saved

    clean_ctx = _clean_learner_context(learner_ctx)
    if case_setting is not None:
        sys_prompt = pf_rubric_setting.load_prompt()["system"]
        user_prompt = pf_rubric_setting.judge_input(student_task, case_setting, clean_ctx)
        prompt_ver = "rahimi-table1/v1-setting"
    else:
        sys_prompt = pf_rubric.load_prompt()["system"]
        user_prompt = pf_rubric.judge_input(student_task, clean_ctx)
        prompt_ver = "rahimi-table1/v1"

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    passes = []
    for pass_idx in (1, 2):
        for attempt in range(2):
            try:
                resp = chat(messages)
                parsed = pf_rubric.parse_rating(resp.text)
                passes.append(
                    {
                        "pass": pass_idx,
                        "status": parsed["status"],
                        "scores": parsed["scores"],
                        "rating": parsed["rating"],
                        "model": resp.model,
                    }
                )
                break
            except Exception as exc:
                if attempt == 1:
                    passes.append(
                        {
                            "pass": pass_idx,
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                            "scores": None,
                        }
                    )

    valid_passes = [p["scores"] for p in passes if p.get("scores") and p["scores"].get("TOTAL") is not None]
    mean_scores = None
    if valid_passes:
        mean_scores = {
            k: round(sum(s[k] for s in valid_passes) / len(valid_passes), 2)
            for k in (*DIMENSIONS, "TOTAL")
        }

    rec = {
        "task_id": task_id,
        "cohort": cohort,
        "prompt_version": prompt_ver,
        "status": "completed" if mean_scores is not None else "error",
        "mean_scores": mean_scores,
        "passes": passes,
        "finished_at": now(),
    }
    save_json(out_path, rec)
    return rec


def collect_saved_newest_pipeline_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    # 1. Improved Pipeline Round 2 (pf_pipeline_lc_impasse_v3_20261015, n = 9)
    r2_dir = ROOT / "experiments/results/pf_pipeline_lc_impasse_v3_20261015/evaluations"
    for p in sorted(r2_dir.glob("*.json")):
        ev = json.loads(p.read_text(encoding="utf-8"))
        inp = ev["v29"]["task_judge"]["input"]
        tasks.append(
            {
                "task_id": f"r2_lc__{ev['key']}",
                "cohort": "improved_pipeline_round2",
                "student_task": inp["student_task"],
                "learner_context": inp["learner_context"],
                "case_setting": None,
            }
        )

    # 2. Improved Pipeline Round 1 (pf_pipeline_lc_impasse_v2_20261015, n = 9)
    r1_dir = ROOT / "experiments/results/pf_pipeline_lc_impasse_v2_20261015/evaluations"
    for p in sorted(r1_dir.glob("*.json")):
        ev = json.loads(p.read_text(encoding="utf-8"))
        inp = ev["v29"]["task_judge"]["input"]
        tasks.append(
            {
                "task_id": f"r1_lc__{ev['key']}",
                "cohort": "improved_pipeline_round1",
                "student_task": inp["student_task"],
                "learner_context": inp["learner_context"],
                "case_setting": None,
            }
        )

    # 3. Generalized Pipeline Check (pf_pipeline_generalized_check_20261016, n = 3)
    gen_dir = ROOT / "experiments/results/pf_pipeline_generalized_check_20261016/evaluations"
    for p in sorted(gen_dir.glob("*.json")):
        ev = json.loads(p.read_text(encoding="utf-8"))
        inp = ev["v29"]["task_judge"]["input"]
        tasks.append(
            {
                "task_id": f"gen_check__{ev['key']}",
                "cohort": "generalized_pipeline_check",
                "student_task": inp["student_task"],
                "learner_context": inp["learner_context"],
                "case_setting": None,
            }
        )

    # 4. 20-Topic Progression Bridge Study (Direct vs Pipeline Ungrounded vs Pipeline LC-Grounded)
    pb_summary = json.loads(
        (ROOT / "experiments/results/pf_progression_bridge_20cases_20261016/summary.json").read_text(
            encoding="utf-8"
        )
    )
    pb_dataset = json.loads(
        (ROOT / "data/learning_commons/progression_bridge_dataset_v1.json").read_text(
            encoding="utf-8"
        )
    )
    pb_cases_by_id = {c["id"]: c for c in pb_dataset["cases"]}
    pb_gen_root = ROOT / "experiments/results/pf_progression_bridge_20cases_20261016/generation"
    for case_id, case_obj in sorted(pb_cases_by_id.items()):
        priors = [
            {
                "resource": f"{s['statementCode']}: {s['description'][:80]}",
                "taught_as": s["description"],
            }
            for s in case_obj["progression_bridge"]["prerequisite_standards_builds_towards"]
        ]
        l_ctx = {
            "grade": str(case_obj["grade"]),
            "subject": case_obj["subject"],
            "jurisdiction": "USA",
            "assumed_prior_knowledge": priors,
        }
        for arm in ("ungrounded", "lc_grounded"):
            res_p = pb_gen_root / arm / case_id / "result.json"
            if not res_p.exists():
                continue
            res_d = json.loads(res_p.read_text(encoding="utf-8"))
            if arm == "direct":
                t_obj = res_d.get("task") or {}
            else:
                t_obj = ((res_d.get("stages") or {}).get("D2_D3") or {}).get("task") or {}
            st_text = "\n\n".join(
                str(t_obj.get(k, "")).strip() for k in ("title", "body", "question") if t_obj.get(k)
            )
            if not st_text:
                continue
            tasks.append(
                {
                    "task_id": f"bridge20__{arm}__{case_id}",
                    "cohort": f"bridge20_{arm}",
                    "student_task": st_text,
                    "learner_context": l_ctx,
                    "case_setting": None,
                }
            )

    return tasks


def _lc_bundle_for_rahimi_cell(cell_id: str) -> dict[str, Any]:
    """Extract Learning Commons progression bundle for each of the 4 Rahimi Grade-7 cells."""
    nodes, _, rels = load_snapshot(LC_BRIDGE_SNAP)
    target_code_map = {
        "sports_basketball_ratio": ("7.RP.A.2", ["7.RP.A.1", "7.NS.A.1"]),
        "shopping_percent": ("7.RP.A.3", ["7.RP.A.2", "7.NS.A.3"]),
        "music_compare_distributions": ("7.SP.B.4", ["6.SP.B.5c", "6.NS.B.3"]),
        "garden_composite_area": ("7.G.B.6", ["6.G.A.1", "7.NS.A.3"]),
    }
    t_code, p_codes = target_code_map[cell_id]
    t_nodes = [
        n for n in nodes.values() if (n.get("properties", {}).get("statementCode") or "") == t_code
    ]
    p_nodes = [
        n
        for n in nodes.values()
        if (n.get("properties", {}).get("statementCode") or "") in p_codes
    ]
    t_ids = {n["identifier"] for n in t_nodes}
    p_ids = {n["identifier"] for n in p_nodes}

    comp_descs: list[str] = []
    for edge in rels:
        if edge.get("label") == "supports" and (
            edge.get("target_identifier") in t_ids or edge.get("target_identifier") in p_ids
        ):
            src = nodes.get(edge.get("source_identifier", ""))
            if src:
                desc = summarize_node(src).get("description")
                if desc and desc not in comp_descs:
                    comp_descs.append(desc)

    return {
        "source_version": "v1.14.0",
        "target_id": cell_id,
        "target_standards": [
            {
                "statementCode": n["properties"].get("statementCode"),
                "description": n["properties"].get("description"),
                "jurisdiction": n["properties"].get("jurisdiction"),
            }
            for n in t_nodes
        ],
        "prerequisite_standards_builds_towards": [
            {
                "statementCode": n["properties"].get("statementCode"),
                "description": n["properties"].get("description"),
                "jurisdiction": n["properties"].get("jurisdiction"),
            }
            for n in p_nodes
        ],
        "supporting_learning_components": comp_descs[:10],
    }


def _build_cell_inputs(cell: dict[str, Any], key: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    case = copy.deepcopy(cell["case"])
    case["id"] = key
    case["teacher_skills"] = list(case.get("teacher_recently_taught") or [])

    grounding_evidence = [
        {
            "source_url": "https://www.thecorestandards.org/Math/",
            "standard_id": f"std:{p['resource']}",
            "label": p["resource"],
            "text": p["taught_as"],
        }
        for p in cell["learner_context"]["assumed_prior_knowledge"]
    ]
    lc_bundle = _lc_bundle_for_rahimi_cell(cell["cell_id"])
    for comp_idx, comp_text in enumerate(
        lc_bundle.get("supporting_learning_components", [])[:6], start=1
    ):
        grounding_evidence.append(
            {
                "source_url": "https://cdn.learningcommons.org/knowledge-graph/v1.14.0/exports/nodes.jsonl",
                "standard_id": f"lc_comp:{cell['cell_id']}:{comp_idx}",
                "label": f"Learning Commons v1.14.0 Supporting Learning Component {comp_idx}",
                "text": comp_text,
            }
        )

    shared_context = {
        "learner_context": cell["learner_context"],
        "benchmark_context": case.get("benchmark_context"),
        "learning_commons_knowledge_graph": lc_bundle,
        "grounding_evidence": grounding_evidence,
    }
    return case, grounding_evidence, shared_context


def ensure_cell_fixed_d1(cell: dict[str, Any], out_dir: Path) -> Path:
    """Generate and freeze Stage D1 once per cell in an isolated process."""
    cell_id = cell["cell_id"]
    d1_file = out_dir / "rahimi_cells_generation" / cell_id / "fixed_d1.json"
    if d1_file.exists():
        return d1_file
    seed_dir = out_dir / "rahimi_cells_generation" / cell_id / "_d1_seed"
    if seed_dir.exists():
        shutil.rmtree(seed_dir)
    seed_dir.mkdir(parents=True, exist_ok=True)
    case, grounding_evidence, shared_context = _build_cell_inputs(cell, f"{cell_id}__d1_seed")
    client, model = diagnostic.load_client("luna")
    import scripts.run_prior_recommendations as d1_runner

    frozen_records = diagnostic._frozen_grounding_records(grounding_evidence)
    orig_curr = d1_runner._curriculum_evidence
    orig_cur = d1_runner._curated_evidence
    try:
        d1_runner._curriculum_evidence = lambda _c, _k: frozen_records
        d1_runner._curated_evidence = lambda _c: []
        d1_res = diagnostic._run_d1_condition(
            client,
            model,
            diagnostic._d1_prompts(),
            case,
            "grounded",
            evidence_k=6,
            max_resources=4,
        )
    finally:
        d1_runner._curriculum_evidence = orig_curr
        d1_runner._curated_evidence = orig_cur

    payload = {
        "schema_version": d1_res["schema_version"],
        "created_at": now(),
        "model": model,
        "origin": "fresh",
        "records": [{"case_id": cell_id, "condition": "grounded", "result": d1_res}],
    }
    save_json(d1_file, payload)
    shutil.rmtree(seed_dir, ignore_errors=True)
    return d1_file


def generate_rahimi_cell_pipeline_task(
    cell: dict[str, Any], repeat: int, out_dir: Path
) -> dict[str, Any]:
    cell_id = cell["cell_id"]
    key = f"{cell_id}__pipeline_lc__{repeat:03d}"
    attempt_dir = out_dir / "rahimi_cells_generation" / cell_id / f"{repeat:03d}"
    res_path = attempt_dir / "result.json"
    if res_path.exists():
        saved = json.loads(res_path.read_text(encoding="utf-8"))
        if saved.get("status") != "running" and (
            (saved.get("stages") or {}).get("D2_D3") or {}
        ).get("task"):
            return {"key": key, "cell_id": cell_id, "repeat": repeat, "result": saved}
        shutil.rmtree(attempt_dir)

    case, grounding_evidence, shared_context = _build_cell_inputs(cell, key)
    fixed_d1_path = out_dir / "rahimi_cells_generation" / cell_id / "fixed_d1.json"
    reused_d1_for_key = attempt_dir.parent / f"_d1_reused_{repeat:03d}.json"
    if fixed_d1_path.exists():
        d1_data = json.loads(fixed_d1_path.read_text(encoding="utf-8"))
        d1_data["records"][0]["case_id"] = key
        save_json(reused_d1_for_key, d1_data)

    try:
        res = diagnostic.run_case_worker(
            key,
            str(attempt_dir),
            "luna",
            2,
            str(reused_d1_for_key) if reused_d1_for_key.exists() else None,
            case_override=case,
            shared_context=shared_context,
            evidence_k=6,
            max_resources=4,
            d1_condition="grounded",
            grounding_evidence=grounding_evidence if not reused_d1_for_key.exists() else None,
        )
    finally:
        if reused_d1_for_key.exists():
            reused_d1_for_key.unlink()
    return {"key": key, "cell_id": cell_id, "repeat": repeat, "result": res}


def _has_v30_api_error(res: dict[str, Any]) -> bool:
    if (res.get("task_judge") or {}).get("status") == "api_error":
        return True
    if (res.get("attempt_judge") or {}).get("status") == "api_error":
        return True
    for s in (res.get("solvers") or {}).values():
        if s.get("status") == "api_error":
            return True
    return False


def evaluate_rahimi_cell_v30(
    key: str,
    cell: dict[str, Any],
    student_task: str,
    chats: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    out_path = out_dir / "rahimi_cells_v30" / f"{key}.json"
    if out_path.exists():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed" and not _has_v30_api_error(saved.get("result") or {}):
            return saved
    res = None
    for attempt in range(3):
        res = v30.evaluate_v30(
            student_task,
            cell["case"]["target_concept"],
            copy.deepcopy(cell["learner_context"]),
            solver_chats={"luna": chats["luna"]},
            judge_chat=chats["luna"],
        )
        if not _has_v30_api_error(res):
            break
    rec = {
        "key": key,
        "cell_id": cell["cell_id"],
        "status": "completed",
        "result": res,
        "finished_at": now(),
    }
    save_json(out_path, rec)
    return rec


def summarize_cohort_table1(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [r["mean_scores"] for r in records if r.get("mean_scores")]
    if not valid:
        return {"n_scored": 0}
    means = {
        k: round(sum(s[k] for s in valid) / len(valid), 2)
        for k in (*DIMENSIONS, "TOTAL")
    }
    return {"n_scored": len(valid), "mean_scores": means}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=["saved_cohorts", "rahimi_cells", "all"],
        default="all",
    )
    parser.add_argument("--repeats-per-cell", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    chats = build_chats()

    summary_out: dict[str, Any] = {}
    if (out_dir / "summary.json").exists():
        summary_out = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    summary_out.update(
        {
            "generated_at": now(),
            "v30_prompt_sha256": v30.fingerprint(),
        }
    )

    if args.phase in ("saved_cohorts", "all"):
        saved_tasks = collect_saved_newest_pipeline_tasks()
        rated_by_cohort: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(
                    rate_one_table1,
                    t["task_id"],
                    t["cohort"],
                    t["student_task"],
                    t["learner_context"],
                    chats["luna"],
                    out_dir,
                    case_setting=t["case_setting"],
                ): t
                for t in saved_tasks
            }
            for fut in as_completed(futs):
                rec = fut.result()
                rated_by_cohort[rec["cohort"]].append(rec)
                print(
                    f"[table1-saved] {rec['task_id']}: TOTAL={rec.get('mean_scores', {}).get('TOTAL')}",
                    flush=True,
                )

        existing_saved = summary_out.get("saved_cohorts_table1") or {}
        summary_out["saved_cohorts_table1"] = {
            **existing_saved,
            **{
                coh: summarize_cohort_table1(recs)
                for coh, recs in sorted(rated_by_cohort.items())
            },
        }
        save_json(out_dir / "summary.json", summary_out)

    if args.phase in ("rahimi_cells", "all"):
        setting = json.loads(SETTING_PATH.read_text(encoding="utf-8"))
        cells = setting["cells"]
        cells_by_id = {c["cell_id"]: c for c in cells}

        # Step 1: Ensure fixed_d1.json per cell in isolated processes
        with ProcessPoolExecutor(max_workers=4) as pool:
            d1_futs = {pool.submit(ensure_cell_fixed_d1, cell, out_dir): cell["cell_id"] for cell in cells}
            for fut in as_completed(d1_futs):
                d1_p = fut.result()
                print(f"[d1-cell] {d1_futs[fut]} -> {d1_p.name}", flush=True)

        # Step 2: Run all 120 D2a-D2b-D3 generations in isolated processes
        gen_jobs = [
            (cell, rep)
            for cell in cells
            for rep in range(1, args.repeats_per_cell + 1)
        ]
        gen_records: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(generate_rahimi_cell_pipeline_task, cell, rep, out_dir): (
                    cell["cell_id"],
                    rep,
                )
                for cell, rep in gen_jobs
            }
            for fut in as_completed(futs):
                grec = fut.result()
                gen_records.append(grec)
                print(f"[gen-rahimi-cell] {grec['key']} done ({len(gen_records)}/{len(gen_jobs)})", flush=True)

        # Evaluate each ready task on BOTH Rahimi Table 1 (setting prompt) and v3.0
        cell_table1_recs: list[dict[str, Any]] = []
        cell_v30_recs: list[dict[str, Any]] = []
        ready_items = []
        for grec in sorted(gen_records, key=lambda x: x["key"]):
            task_obj = (
                ((grec["result"].get("stages") or {}).get("D2_D3") or {}).get("task") or {}
            )
            st_text = "\n\n".join(
                str(task_obj.get(k, "")).strip()
                for k in ("title", "body", "question")
                if task_obj.get(k)
            )
            if st_text:
                ready_items.append((grec["key"], cells_by_id[grec["cell_id"]], st_text))

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            t1_futs = {
                pool.submit(
                    rate_one_table1,
                    key,
                    f"rahimi_cell__{cell['cell_id']}",
                    st_text,
                    cell["learner_context"],
                    chats["luna"],
                    out_dir,
                    case_setting=cell["case"],
                ): key
                for key, cell, st_text in ready_items
            }
            v30_futs = {
                pool.submit(
                    evaluate_rahimi_cell_v30,
                    key,
                    cell,
                    st_text,
                    chats,
                    out_dir,
                ): key
                for key, cell, st_text in ready_items
            }
            for fut in as_completed(t1_futs):
                r = fut.result()
                cell_table1_recs.append(r)
                print(
                    f"[rahimi-cell-table1] {r['task_id']}: TOTAL={r.get('mean_scores', {}).get('TOTAL')}",
                    flush=True,
                )
            for fut in as_completed(v30_futs):
                r = fut.result()
                cell_v30_recs.append(r)
                ms = r["result"]["measures"]
                all5 = all(ms[m]["value"] == "yes" for m in MEASURES)
                print(
                    f"[rahimi-cell-v30] {r['key']}: all5={all5} limits={ms['familiar_approach_limits']['value']}",
                    flush=True,
                )

        by_cell_t1: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in cell_table1_recs:
            cid = r["cohort"].replace("rahimi_cell__", "")
            by_cell_t1[cid].append(r)

        v30_counts = {m: Counter() for m in MEASURES}
        v30_all5 = 0
        by_cell_v30: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"n": 0, "all_5_yes": 0, "limits_yes": 0}
        )
        for r in cell_v30_recs:
            cid = r["cell_id"]
            ms = r["result"]["measures"]
            by_cell_v30[cid]["n"] += 1
            for m in MEASURES:
                val = ms[m]["value"] if ms[m]["status"] == "assessed" else ms[m]["status"]
                v30_counts[m][str(val)] += 1
            if ms["familiar_approach_limits"]["value"] == "yes":
                by_cell_v30[cid]["limits_yes"] += 1
            if all(ms[m]["value"] == "yes" for m in MEASURES):
                v30_all5 += 1
                by_cell_v30[cid]["all_5_yes"] += 1

        main30_ref = json.loads(MAIN30_SUMMARY_PATH.read_text(encoding="utf-8"))["by_cell_model"]
        summary_out["rahimi_4cells_newest_pipeline"] = {
            "scheduled": len(gen_jobs),
            "ready": len(ready_items),
            "overall_table1": summarize_cohort_table1(cell_table1_recs),
            "by_cell_table1": {
                cid: summarize_cohort_table1(recs) for cid, recs in sorted(by_cell_t1.items())
            },
            "overall_v30": {
                "n_evaluated": len(cell_v30_recs),
                "all_5_yes": v30_all5,
                "all_5_yes_pct": round(100.0 * v30_all5 / max(1, len(cell_v30_recs)), 1),
                "measures": {m: dict(c) for m, c in v30_counts.items()},
            },
            "by_cell_v30": dict(by_cell_v30),
            "main30_direct_reference_mean_total": {
                k: v["mean_final"] for k, v in main30_ref.items()
            },
        }
        save_json(out_dir / "summary.json", summary_out)

    print(json.dumps(summary_out, indent=2))


if __name__ == "__main__":
    main()
