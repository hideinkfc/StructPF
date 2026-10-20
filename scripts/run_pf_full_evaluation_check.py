"""Run the full v2.7 evaluation pipeline on a few saved task inputs and check every role's output.

Computational check only. Each task goes through the task judge, two solvers, the attempt judge
and the measure assembly, as in evaluate_v27. No human labels are involved.
"""

from __future__ import annotations

import argparse
import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_pf_accessibility_sensitivity import build_chats
from scripts.run_pf_solver_check import load_cases as load_pack_cases
from src.evaluation import pf_three_role_v27 as v27
from src.evaluation import pf_three_role_v28 as v28
from src.evaluation import pf_three_role_v29 as v29

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/pf_full_evaluation_check_v27_20261015"
CASE_IDS = ["expert_bicycle", "expert_ship", "garden_composite_area__gpt41__019"]
EVALUATORS = {"v27": v27.evaluate_v27, "v28": v28.evaluate_v28, "v29": v29.evaluate_v29}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_case(case: dict, chats: dict, output: Path, evaluate) -> dict:
    path = output / "jobs" / f"{case['case_id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    record = {"case_id": case["case_id"], "started_at": now()}
    try:
        result = evaluate(
            case["student_task"],
            case["learning_target"],
            copy.deepcopy(case["learner_context"]),
            solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
            judge_chat=chats["luna"],
        )
        record.update({"status": "completed", "result": result})
    except Exception as exc:  # keep the failure visible in the record
        record.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    record["finished_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def check(record: dict) -> dict:
    """Mechanical checks on one completed evaluation."""
    problems = []
    result = record.get("result") or {}
    measures = result.get("measures", {})
    expected = {
        "target_alignment",
        "mathematical_validity",
        "room_for_invention",
        "prior_knowledge_accessibility",
        "familiar_approach_limits",
    }
    if set(measures) != expected:
        problems.append(f"measure keys differ: {sorted(set(measures) ^ expected)}")
    task = result.get("task_judge") or {}
    if task.get("status") != "completed":
        problems.append(f"task judge {task.get('status')}")
    for solver_id, summary in (result.get("solvers") or {}).items():
        if summary.get("status") != "completed":
            problems.append(f"solver {solver_id} {summary.get('status')}")
    attempt = result.get("attempt_judge")
    if attempt is not None and attempt.get("status") != "completed":
        problems.append(f"attempt judge {attempt.get('status')}")
    align = measures.get("target_alignment", {}).get("value")
    if align != "yes" and measures.get("mathematical_validity", {}).get("status") != "not_assessed":
        problems.append("validity assessed although alignment is not yes")
    access = measures.get("prior_knowledge_accessibility", {}).get("value")
    if (
        access != "yes"
        and measures.get("familiar_approach_limits", {}).get("status") != "not_assessed"
    ):
        problems.append("limits assessed although accessibility is not yes")
    invalid = [name for name, row in measures.items() if row.get("status") == "invalid_response"]
    if invalid:
        problems.append(f"invalid measure rows: {invalid}")
    return {"problems": problems}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--evaluator", choices=sorted(EVALUATORS), default="v27")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--cases", nargs="+", default=CASE_IDS)
    args = parser.parse_args()
    pack = {case["case_id"]: case for case in load_pack_cases()}
    cases = [pack[case_id] for case_id in args.cases]
    if args.dry_run:
        print(f"{len(cases)} cases load; full pipeline runs: {len(cases)}")
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    chats = build_chats()
    evaluate = EVALUATORS[args.evaluator]
    records = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_case, case, chats, output, evaluate): case["case_id"] for case in cases
        }
        for future in as_completed(futures):
            record = future.result()
            records[record["case_id"]] = record
            print(f"{record['case_id']}: {record['status']}", flush=True)
    summary = {}
    for case_id in args.cases:
        record = records[case_id]
        summary[case_id] = {"status": record["status"], **check(record)}
        if record["status"] == "completed":
            result = record["result"]
            summary[case_id]["measures"] = {
                name: {"value": row["value"], "status": row["status"]}
                for name, row in result["measures"].items()
            }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
