"""Run the PF Solver Approach-Recall & Objectivity Benchmark across all 76 tasks.

Stages (cached per case so interrupted runs resume cleanly):
  1. solver: loads cached pf-three-role/v3.0 solver attempts (Luna + GPT-4.1) for the 44
     tasks already evaluated in pf_v30_calibration_20261015, and runs the frozen v3.0
     solver (Luna + GPT-4.1) on the remaining 32 tasks.
  2. judge: runs the frozen pf-solver-recall-match/v1.0 judge to score whether Luna's
     attempts and GPT-4.1's attempts cover each pre-specified reference approach
     (baseline_trap, resolving_route, routine_solution, diagnostic_control_check).
  3. summary: aggregates approach-level recall by role and cohort, plus task-level
     evaluator objectivity rates (baseline-trap coverage, resolving-route coverage,
     dual coverage on PF tasks, and routine-solve sensitivity on routine tasks).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation import pf_three_role_v30 as v30

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "experiments/configs/pf_solver_recall_benchmark_20261016.json"
JUDGE_PROMPT_PATH = ROOT / "src/evaluation/prompts/pf_solver_recall_match_v1.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/results/pf_solver_recall_20261016"
PRIMARY_COMPLETE_ROLES = (
    "baseline_trap",
    "resolving_route",
    "routine_solution",
    "diagnostic_control_check",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_json_text(text: str) -> dict[str, Any]:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*```$", "", s)
    return json.loads(s)


def run_or_load_solver_case(case: dict[str, Any], chats: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    cid = case["case_id"]
    out_path = out_dir / "solver" / f"{cid}.json"
    if out_path.exists():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed" and saved.get("luna_attempts") and saved.get("gpt41_attempts"):
            return saved

    # Check if cached v3.0 evaluation exists
    cached_rel = case.get("cached_v30_eval_path")
    if cached_rel:
        cached_file = ROOT / cached_rel
        if cached_file.exists():
            d = json.loads(cached_file.read_text(encoding="utf-8"))
            atts = ((d.get("result") or {}).get("attempt_judge") or {}).get("input", {}).get("attempts") or []
            luna_atts = [a for a in atts if a.get("solver") == "luna"]
            gpt41_atts = [a for a in atts if a.get("solver") == "gpt41"]
            if luna_atts and gpt41_atts:
                rec = {
                    "case_id": cid,
                    "status": "completed",
                    "source": "cached_v30_calibration",
                    "cached_v30_eval_path": cached_rel,
                    "luna_attempts": luna_atts,
                    "gpt41_attempts": gpt41_atts,
                    "finished_at": now(),
                }
                save_json(out_path, rec)
                return rec

    # Run fresh v3.0 solvers (Luna and GPT-4.1) on target-blind solver_input
    prepared = v25.prepare_input(
        case["student_task"],
        case["learning_target"],
        copy.deepcopy(case["learner_context"]),
    )
    payload = v22.role_input("solver", prepared)
    if set(payload.keys()) != {"student_task", "learner_context"}:
        raise ValueError(f"Non-blind solver payload keys: {list(payload.keys())}")

    runs = {}
    for solver_id in ("luna", "gpt41"):
        runs[solver_id] = v30.run_solver_v30(payload, chats[solver_id], solver_id=solver_id, toolkit=True)

    combined = v25.combine_attempts(runs)
    luna_atts = [a for a in combined if a.get("solver") == "luna"]
    gpt41_atts = [a for a in combined if a.get("solver") == "gpt41"]
    status = "completed" if (luna_atts and gpt41_atts) else "incomplete_solver"
    rec = {
        "case_id": cid,
        "status": status,
        "source": "fresh_v30_solver",
        "solver_meta": {
            s: {k: v for k, v in r.items() if k != "calls"} for s, r in runs.items()
        },
        "luna_attempts": luna_atts,
        "gpt41_attempts": gpt41_atts,
        "finished_at": now(),
    }
    save_json(out_path, rec)
    return rec


def _compact_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "attempt_index": idx,
            "idea": a.get("idea"),
            "principle": a.get("principle"),
            "method_kind": a.get("method_kind"),
            "trial_count": a.get("trial_count"),
            "toolkit_used": a.get("toolkit_used"),
            "work": a.get("work"),
        }
        for idx, a in enumerate(attempts)
    ]


def run_judge_case(
    case: dict[str, Any],
    solver_rec: dict[str, Any],
    judge_system: str,
    chat,
    out_dir: Path,
) -> dict[str, Any]:
    cid = case["case_id"]
    out_path = out_dir / "judge" / f"{cid}.json"
    expected_ids = [a["approach_id"] for a in case["reference_approaches"]]
    if out_path.exists():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed":
            got_ids = [m.get("approach_id") for m in (saved.get("parsed") or {}).get("matches", [])]
            if got_ids == expected_ids:
                return saved

    user_payload = {
        "student_task": case["student_task"],
        "reference_approaches": [
            {
                "approach_id": a["approach_id"],
                "name": a["name"],
                "role": a["role"],
                "action_definition": a["action_definition"],
                "expected_limitation": a["expected_limitation"],
            }
            for a in case["reference_approaches"]
        ],
        "luna_attempts": _compact_attempts(solver_rec.get("luna_attempts") or []),
        "gpt41_attempts": _compact_attempts(solver_rec.get("gpt41_attempts") or []),
    }
    messages = [
        {"role": "system", "content": judge_system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

    calls = []
    parsed = None
    last_error = None
    for attempt in range(3):
        try:
            resp = chat(messages)
            calls.append(
                {
                    "attempt": attempt + 1,
                    "response_text": resp.text,
                    "model": resp.model,
                    "usage": resp.usage,
                }
            )
            cand = parse_json_text(resp.text)
            matches = cand.get("matches")
            if not isinstance(matches, list):
                raise ValueError("matches must be a list")
            by_id = {m.get("approach_id"): m for m in matches if isinstance(m, dict)}
            norm_matches = []
            for aid in expected_ids:
                if aid not in by_id:
                    raise ValueError(f"Missing approach_id in matches: {aid}")
                m = by_id[aid]
                lc = m.get("luna_coverage")
                gc = m.get("gpt41_coverage")
                if lc not in ("yes", "partly", "no") or gc not in ("yes", "partly", "no"):
                    raise ValueError(f"Invalid coverage value for {aid}: luna={lc}, gpt41={gc}")
                norm_matches.append(
                    {
                        "approach_id": aid,
                        "luna_coverage": lc,
                        "luna_attempt_indices": [
                            int(i) for i in (m.get("luna_attempt_indices") or []) if isinstance(i, int)
                        ],
                        "gpt41_coverage": gc,
                        "gpt41_attempt_indices": [
                            int(i) for i in (m.get("gpt41_attempt_indices") or []) if isinstance(i, int)
                        ],
                        "combined_coverage": (
                            "yes"
                            if "yes" in (lc, gc)
                            else ("partly" if "partly" in (lc, gc) else "no")
                        ),
                        "reason": str(m.get("reason", "")).strip(),
                    }
                )
            parsed = {
                "matches": norm_matches,
                "extra_valid_approaches": cand.get("extra_valid_approaches") or [],
            }
            last_error = None
            break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            messages.append({"role": "assistant", "content": calls[-1]["response_text"] if calls else ""})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your response had a schema error ({last_error}). Return valid JSON only "
                        f"with matches for exact approach_ids: {expected_ids}."
                    ),
                }
            )

    rec = {
        "case_id": cid,
        "status": "completed" if parsed is not None else "error",
        "error": last_error,
        "parsed": parsed,
        "calls": calls,
        "finished_at": now(),
    }
    save_json(out_path, rec)
    return rec


def summarize_results(
    dataset: dict[str, Any],
    solver_records: dict[str, dict[str, Any]],
    judge_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    systems = ("luna", "gpt41", "combined")
    cov_key = {
        "luna": "luna_coverage",
        "gpt41": "gpt41_coverage",
        "combined": "combined_coverage",
    }

    # Approach-level tallies by role and by cohort
    by_role: dict[str, dict[str, Counter]] = {
        sys: defaultdict(Counter) for sys in systems
    }
    by_cohort: dict[str, dict[str, Counter]] = {
        sys: defaultdict(Counter) for sys in systems
    }

    # Task-level objectivity tallies
    pf_task_counts = {
        sys: {
            "total_pf_tasks": 0,
            "has_baseline_trap_strict": 0,
            "has_baseline_trap_partly": 0,
            "has_resolving_route_strict": 0,
            "has_resolving_route_partly": 0,
            "dual_coverage_strict": 0,
            "dual_coverage_partly": 0,
        }
        for sys in systems
    }
    routine_task_counts = {
        sys: {
            "total_routine_tasks": 0,
            "has_routine_solution_strict": 0,
            "has_routine_solution_partly": 0,
        }
        for sys in systems
    }
    control_task_counts = {
        sys: {
            "total_diagnostic_control_tasks": 0,
            "has_diagnostic_check_strict": 0,
            "has_diagnostic_check_partly": 0,
        }
        for sys in systems
    }

    per_case_rows = []
    approach_counts_per_solver = {"luna": [], "gpt41": [], "combined": []}

    for case in dataset["cases"]:
        cid = case["case_id"]
        cohort = case["cohort"]
        srec = solver_records[cid]
        jrec = judge_records[cid]
        n_luna = len(srec.get("luna_attempts") or [])
        n_gpt41 = len(srec.get("gpt41_attempts") or [])
        approach_counts_per_solver["luna"].append(n_luna)
        approach_counts_per_solver["gpt41"].append(n_gpt41)
        approach_counts_per_solver["combined"].append(n_luna + n_gpt41)

        matches_by_id = {
            m["approach_id"]: m
            for m in ((jrec.get("parsed") or {}).get("matches") or [])
        }

        for ref in case["reference_approaches"]:
            aid = ref["approach_id"]
            role = ref["role"]
            m = matches_by_id.get(aid, {})
            for sys in systems:
                val = m.get(cov_key[sys], "no")
                by_role[sys][role][val] += 1
                if role in PRIMARY_COMPLETE_ROLES:
                    by_role[sys]["primary_complete"][val] += 1
                    by_cohort[sys][cohort][val] += 1

        # Task-level aggregation
        roles_in_case = {r["role"] for r in case["reference_approaches"]}
        if "baseline_trap" in roles_in_case and "resolving_route" in roles_in_case:
            for sys in systems:
                pf_task_counts[sys]["total_pf_tasks"] += 1
                trap_vals = [
                    matches_by_id.get(r["approach_id"], {}).get(cov_key[sys], "no")
                    for r in case["reference_approaches"]
                    if r["role"] == "baseline_trap"
                ]
                res_vals = [
                    matches_by_id.get(r["approach_id"], {}).get(cov_key[sys], "no")
                    for r in case["reference_approaches"]
                    if r["role"] == "resolving_route"
                ]
                trap_s = "yes" in trap_vals
                trap_p = any(v in ("yes", "partly") for v in trap_vals)
                res_s = "yes" in res_vals
                res_p = any(v in ("yes", "partly") for v in res_vals)
                if trap_s:
                    pf_task_counts[sys]["has_baseline_trap_strict"] += 1
                if trap_p:
                    pf_task_counts[sys]["has_baseline_trap_partly"] += 1
                if res_s:
                    pf_task_counts[sys]["has_resolving_route_strict"] += 1
                if res_p:
                    pf_task_counts[sys]["has_resolving_route_partly"] += 1
                if trap_s and res_s:
                    pf_task_counts[sys]["dual_coverage_strict"] += 1
                if trap_p and res_p:
                    pf_task_counts[sys]["dual_coverage_partly"] += 1

        if "routine_solution" in roles_in_case:
            for sys in systems:
                routine_task_counts[sys]["total_routine_tasks"] += 1
                r_vals = [
                    matches_by_id.get(r["approach_id"], {}).get(cov_key[sys], "no")
                    for r in case["reference_approaches"]
                    if r["role"] == "routine_solution"
                ]
                if "yes" in r_vals:
                    routine_task_counts[sys]["has_routine_solution_strict"] += 1
                if any(v in ("yes", "partly") for v in r_vals):
                    routine_task_counts[sys]["has_routine_solution_partly"] += 1

        if "diagnostic_control_check" in roles_in_case:
            for sys in systems:
                control_task_counts[sys]["total_diagnostic_control_tasks"] += 1
                d_vals = [
                    matches_by_id.get(r["approach_id"], {}).get(cov_key[sys], "no")
                    for r in case["reference_approaches"]
                    if r["role"] == "diagnostic_control_check"
                ]
                if "yes" in d_vals:
                    control_task_counts[sys]["has_diagnostic_check_strict"] += 1
                if any(v in ("yes", "partly") for v in d_vals):
                    control_task_counts[sys]["has_diagnostic_check_partly"] += 1

        per_case_rows.append(
            {
                "case_id": cid,
                "cohort": cohort,
                "topic": case["topic"],
                "n_luna_attempts": n_luna,
                "n_gpt41_attempts": n_gpt41,
                "matches": (jrec.get("parsed") or {}).get("matches") or [],
                "extra_valid_approaches_count": len(
                    (jrec.get("parsed") or {}).get("extra_valid_approaches") or []
                ),
            }
        )

    def _fmt_counter(c: Counter) -> dict[str, Any]:
        tot = sum(c.values())
        yes = c.get("yes", 0)
        partly = c.get("partly", 0)
        no = c.get("no", 0)
        return {
            "total": tot,
            "yes": yes,
            "partly": partly,
            "no": no,
            "recall_strict_pct": round(100.0 * yes / tot, 1) if tot else 0.0,
            "recall_partly_pct": round(100.0 * (yes + partly) / tot, 1) if tot else 0.0,
        }

    return {
        "benchmark_sha256": file_sha256(BENCHMARK_PATH),
        "judge_prompt_sha256": file_sha256(JUDGE_PROMPT_PATH),
        "v30_prompt_sha256": v30.fingerprint(),
        "tasks_evaluated": len(dataset["cases"]),
        "mean_approaches_per_task": {
            sys: round(
                sum(approach_counts_per_solver[sys]) / len(approach_counts_per_solver[sys]), 2
            )
            for sys in systems
        },
        "recall_by_role": {
            sys: {role: _fmt_counter(cnt) for role, cnt in by_role[sys].items()}
            for sys in systems
        },
        "recall_by_cohort_primary_complete": {
            sys: {coh: _fmt_counter(cnt) for coh, cnt in by_cohort[sys].items()}
            for sys in systems
        },
        "task_level_pf_coverage": {
            sys: {
                **pf_task_counts[sys],
                "baseline_trap_strict_pct": round(
                    100.0
                    * pf_task_counts[sys]["has_baseline_trap_strict"]
                    / max(1, pf_task_counts[sys]["total_pf_tasks"]),
                    1,
                ),
                "resolving_route_strict_pct": round(
                    100.0
                    * pf_task_counts[sys]["has_resolving_route_strict"]
                    / max(1, pf_task_counts[sys]["total_pf_tasks"]),
                    1,
                ),
                "dual_coverage_strict_pct": round(
                    100.0
                    * pf_task_counts[sys]["dual_coverage_strict"]
                    / max(1, pf_task_counts[sys]["total_pf_tasks"]),
                    1,
                ),
                "dual_coverage_partly_pct": round(
                    100.0
                    * pf_task_counts[sys]["dual_coverage_partly"]
                    / max(1, pf_task_counts[sys]["total_pf_tasks"]),
                    1,
                ),
            }
            for sys in systems
        },
        "task_level_routine_solve_sensitivity": {
            sys: {
                **routine_task_counts[sys],
                "routine_solution_strict_pct": round(
                    100.0
                    * routine_task_counts[sys]["has_routine_solution_strict"]
                    / max(1, routine_task_counts[sys]["total_routine_tasks"]),
                    1,
                ),
            }
            for sys in systems
        },
        "task_level_diagnostic_control_sensitivity": {
            sys: {
                **control_task_counts[sys],
                "diagnostic_check_strict_pct": round(
                    100.0
                    * control_task_counts[sys]["has_diagnostic_check_strict"]
                    / max(1, control_task_counts[sys]["total_diagnostic_control_tasks"]),
                    1,
                ),
            }
            for sys in systems
        },
        "per_case": per_case_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cases (0 = all 76)")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    dataset = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    judge_spec = yaml.safe_load(JUDGE_PROMPT_PATH.read_text(encoding="utf-8"))
    judge_system = judge_spec["system"]

    cases = dataset["cases"]
    if args.limit > 0:
        cases = cases[: args.limit]
        dataset = {**dataset, "cases": cases}

    chats = build_chats()
    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Solver (reusing cached v3.0 runs for 44 tasks, executing fresh for 32 tasks)
    solver_records: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(run_or_load_solver_case, c, chats, out_dir): c["case_id"]
            for c in cases
        }
        for fut in as_completed(futs):
            rec = fut.result()
            solver_records[rec["case_id"]] = rec
            print(f"[solver] {rec['case_id']} ({rec['source']}): status={rec['status']}", flush=True)

    # Stage 2: Matching Judge
    judge_records: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(
                run_judge_case,
                c,
                solver_records[c["case_id"]],
                judge_system,
                chats["luna"],
                out_dir,
            ): c["case_id"]
            for c in cases
        }
        for fut in as_completed(futs):
            rec = fut.result()
            judge_records[rec["case_id"]] = rec
            print(f"[judge] {rec['case_id']}: status={rec['status']}", flush=True)

    summary = summarize_results(dataset, solver_records, judge_records)
    save_json(out_dir / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "per_case"}, indent=2))


if __name__ == "__main__":
    main()
