"""Run the v2.5 solvers on saved task inputs and audit their attempts with the v2.7 judge.

Computational check only. The solvers receive student_task and learner_context, not the target.
The attempt judge is the strict-start judge; each attempt gets a status.
"""

from __future__ import annotations

import argparse
import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation.frozen import pf_three_role_v27 as v27

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "experiments/results/pf_measure_campaign_20261014/calibration_pack.json"
OUTPUT = ROOT / "experiments/results/pf_solver_check_v25_20261015"
CASE_IDS = [
    "expert_bicycle",
    "expert_consistency",
    "expert_country",
    "expert_land",
    "expert_time_sharing",
    "expert_ship",
    "garden_composite_area__gpt41__019",
    "sports_basketball_ratio__gpt41__021",
    "expert_pizza",
    "expert_braking_collision",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_cases() -> list[dict]:
    pack = json.loads(PACK.read_text())
    by_id = {case["case_id"]: case for case in pack["development"] + pack["transfer"]}
    missing = [case_id for case_id in CASE_IDS if case_id not in by_id]
    if missing:
        raise ValueError(f"Cases not found in the saved pack: {missing}")
    return [by_id[case_id] for case_id in CASE_IDS]


def run_case(case: dict, chats: dict, output: Path) -> dict:
    path = output / "jobs" / f"{case['case_id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    record = {"case_id": case["case_id"], "started_at": now()}
    try:
        prepared = v25.prepare_input(
            case["student_task"],
            case["learning_target"],
            copy.deepcopy(case["learner_context"]),
        )
        solver_input = v22.role_input("solver", prepared)
        if set(solver_input) != {"student_task", "learner_context"}:
            raise ValueError("Solver input is not target-blind")
        runs = {
            solver_id: v25.run_solver_v25(solver_input, chat, solver_id=solver_id, toolkit=True)
            for solver_id, chat in chats.items()
        }
        items = v25.combine_attempts(runs)
        attempt = None
        if items:
            attempt = v22.run_role(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                chats["luna"],
                system_text=v27.attempt_system(),
            )
        record.update(
            {
                "solver_runs": runs,
                "items": items,
                "attempt_judge": attempt,
                "status": "completed",
            }
        )
    except Exception as exc:  # keep the failure visible in the record
        record.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    record["finished_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    cases = load_cases()
    if args.dry_run:
        print(f"{len(cases)} cases load; solver calls: {2 * len(cases)}")
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    chats = build_chats()
    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(run_case, case, chats, output): case["case_id"] for case in cases}
        for future in as_completed(futures):
            record = future.result()
            results[record["case_id"]] = record
            print(f"{record['case_id']}: {record['status']}", flush=True)
    rows = []
    for case in cases:
        record = results[case["case_id"]]
        row = {"case_id": case["case_id"], "status": record["status"]}
        if record["status"] == "completed":
            row["solvers"] = {
                solver_id: v25._solver_summary(run)
                for solver_id, run in record["solver_runs"].items()
            }
            audit = record["attempt_judge"]
            row["attempt_statuses"] = (
                [item["status"] for item in audit["output"]["attempts"]]
                if audit and audit["status"] == "completed"
                else None
            )
            row["attempt_judge_status"] = audit["status"] if audit else "not_run"
        rows.append(row)
    summary = {"generated_at": now(), "cases": len(cases), "rows": rows}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {output / 'summary.json'}")


if __name__ == "__main__":
    main()
