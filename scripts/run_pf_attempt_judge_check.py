"""Re-judge the saved solver attempts from the solver check to measure attempt-judge consistency.

Computational check only. Attempts are frozen from the solver check; only the judge repeats.
Luna is run twice more (the saved run is a third Luna run); GPT-4.1 is run once.
"""

from __future__ import annotations

import argparse
import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_pf_accessibility_sensitivity import build_chats
from scripts.run_pf_solver_check import load_cases
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation.frozen import pf_three_role_v27 as v27

ROOT = Path(__file__).resolve().parents[1]
SOLVER_CHECK = ROOT / "experiments/results/pf_solver_check_v25_20261015/jobs"
OUTPUT = ROOT / "experiments/results/pf_attempt_judge_check_20261015"
RUNS = [("luna", "luna_repeat_2"), ("luna", "luna_repeat_3"), ("gpt41", "gpt41_repeat_1")]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def judge_once(case: dict, items: list[dict], chat, output: Path, label: str) -> dict:
    path = output / "jobs" / f"{case['case_id']}__{label}.json"
    if path.exists():
        return json.loads(path.read_text())
    prepared = v25.prepare_input(
        case["student_task"], case["learning_target"], copy.deepcopy(case["learner_context"])
    )
    run = v22.run_role(
        "attempt_judge",
        v22.role_input("attempt_judge", prepared, items),
        chat,
        system_text=v27.attempt_system(),
    )
    record = {"case_id": case["case_id"], "judge": label, "finished_at": now(), "run": run}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cases = load_cases()
    saved = {}
    for case in cases:
        record = json.loads((SOLVER_CHECK / f"{case['case_id']}.json").read_text())
        saved[case["case_id"]] = record["items"]
    if args.dry_run:
        print(f"{len(cases)} cases; judge calls: {len(cases) * len(RUNS)}")
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    chats = build_chats()
    jobs = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for case in cases:
            items = saved[case["case_id"]]
            if not items:
                continue
            for model, label in RUNS:
                jobs.append(pool.submit(judge_once, case, items, chats[model], OUTPUT, label))
        done = 0
        for future in as_completed(jobs):
            future.result()
            done += 1
            print(f"{done}/{len(jobs)}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
