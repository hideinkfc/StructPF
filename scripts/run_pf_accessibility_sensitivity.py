"""Run a labelled accessibility sensitivity set through a pinned PF evaluator.

Computational check only. The cases are synthetic and assistant-written; their
labels are provisional and not human-reviewed. Each case goes through the same
path as the saved campaign: two solvers, one attempt judge, and the task judge.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.prior_methods.common import load_client
from scripts.run_pf_task_measures import make_chat
from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v25 as v25
from src.evaluation import pf_three_role_v26 as v26
from src.evaluation import pf_three_role_v27 as v27
from src.evaluation import pf_three_role_v28 as v28

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/configs/pf_accessibility_sensitivity_20261015.json"
OUTPUT = ROOT / "experiments/results/pf_accessibility_sensitivity_20261015"
EVALUATORS = {
    "v25": v25.evaluate_v25,
    "v26": v26.evaluate_v26,
    "v27": v27.evaluate_v27,
    "v28": v28.evaluate_v28,
}
MODULES = {"v25": v25, "v26": v26, "v27": v27, "v28": v28}
GATE_LABELS = {
    "inaccessible": "inaccessible",
    "no": "inaccessible",
    "accessible": "accessible",
    "yes": "accessible",
}
MODELS = {"luna": "gpt-5.6-luna", "gpt41": "gpt-4.1"}
TOKENS = 12000
REPEATS = 2


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def settings(model: str) -> dict:
    if model.startswith("gpt-5"):
        return {"max_completion_tokens": TOKENS, "reasoning_effort": "high"}
    return {"max_tokens": TOKENS, "temperature": 0}


def build_chats() -> dict:
    chats = {}
    for label, model in MODELS.items():
        client, _ = load_client("luna" if label == "luna" else "gpt41")
        chats[label] = make_chat(client, model, settings(model))
    return chats


def load_cases(config: Path) -> list[dict]:
    cases = json.loads(config.read_text())["cases"]
    for case in cases:
        v25.prepare_input(case["student_task"], case["learning_target"], case["learner_context"])
        # Strict-label files use strict_label (no/yes/unclear); the first file uses label.
        raw = case.get("strict_label", case.get("label"))
        case["recorded_label"] = raw
        case["gate_label"] = GATE_LABELS.get(raw, "unscored")
    return cases


def run_job(case: dict, repeat: int, chats: dict, output: Path, evaluate) -> dict:
    path = output / "jobs" / f"{case['case_id']}__r{repeat}.json"
    if path.exists():
        return json.loads(path.read_text())
    record = {"case_id": case["case_id"], "repeat": repeat, "started_at": now()}
    try:
        result = evaluate(
            case["student_task"],
            case["learning_target"],
            copy.deepcopy(case["learner_context"]),
            solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
            judge_chat=chats["luna"],
        )
        record["result"] = result
        record["accessibility"] = result["measures"]["prior_knowledge_accessibility"]["value"]
        record["status"] = "completed"
    except Exception as exc:  # keep the failure visible in the record
        record.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    record["finished_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def manifest(cases: list[dict], status: str, config: Path, evaluator_name: str) -> dict:
    module = MODULES[evaluator_name]
    if evaluator_name in {"v26", "v27", "v28"}:
        attempt_system = module.attempt_system_sha256()
    else:
        attempt_system = hashlib.sha256(v22.system("attempt_judge").encode("utf-8")).hexdigest()
    sources = [
        ROOT / "src/evaluation/pf_three_role_v22.py",
        ROOT / "src/evaluation/pf_three_role_v23.py",
        ROOT / "src/evaluation/pf_three_role_v25.py",
        Path(__file__),
    ]
    if evaluator_name in {"v26", "v27", "v28"}:
        sources.append(Path(module.__file__))
    return {
        "version": module.VERSION,
        "evaluator": evaluator_name,
        "status": status,
        "created_at": now(),
        "computational_only": True,
        "human_validated": False,
        "models": MODELS,
        "tokens_per_call": TOKENS,
        "repeats": REPEATS,
        "case_count": len(cases),
        "config": str(config.relative_to(ROOT)),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "prompt_sha256": module.fingerprint(),
        "solver_system_sha256": v25.solver_system_sha256(toolkit=True),
        "attempt_system_sha256": attempt_system,
        "source_hashes": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources
        },
    }


def summarize(cases: list[dict], records: dict) -> dict:
    rows = []
    for case in cases:
        values = [
            records[(case["case_id"], repeat)].get("accessibility")
            for repeat in range(1, REPEATS + 1)
        ]
        rows.append(
            {
                "case_id": case["case_id"],
                "recorded_label": case["recorded_label"],
                "gate_label": case["gate_label"],
                "accessibility_by_repeat": values,
                "any_yes": "yes" in values,
            }
        )
    inaccessible = [row for row in rows if row["gate_label"] == "inaccessible"]
    errors = [
        f"{case_id} r{repeat}: {records[(case_id, repeat)]['status']}, "
        f"accessibility={records[(case_id, repeat)].get('accessibility')}"
        for case_id, repeat in records
        if records[(case_id, repeat)]["status"] != "completed"
        or records[(case_id, repeat)].get("accessibility") not in {"yes", "no", "unclear"}
    ]
    gate_passes = not errors and all(not row["any_yes"] for row in inaccessible)
    return {
        "gate_passes": gate_passes,
        "rule": (
            "Every repeat completes and no inaccessible case is judged yes; "
            "unscored cases are reported only"
        ),
        "inaccessible_yes_cases": [row["case_id"] for row in inaccessible if row["any_yes"]],
        "errors": sorted(errors),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs; no model calls")
    parser.add_argument("--evaluator", choices=sorted(EVALUATORS), default="v25")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.config = args.config.resolve()
    args.output = args.output.resolve()
    logging.basicConfig(level=logging.WARNING)
    cases = load_cases(args.config)
    if args.dry_run:
        module = MODULES[args.evaluator]
        print(f"{len(cases)} cases validate; {len(cases) * REPEATS} evaluations would run")
        print("prompt_sha256", module.fingerprint())
        return
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    started = manifest(cases, "started", args.config, args.evaluator)
    (output / "manifest.json").write_text(json.dumps(started, indent=2) + "\n")
    chats = build_chats()
    evaluate = EVALUATORS[args.evaluator]
    jobs = [(case, repeat) for case in cases for repeat in range(1, REPEATS + 1)]
    records = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(run_job, case, repeat, chats, output, evaluate): (case["case_id"], repeat)
            for case, repeat in jobs
        }
        for future in as_completed(futures):
            key = futures[future]
            records[key] = future.result()
            shown = records[key].get("accessibility", records[key]["status"])
            print(f"{key[0]} r{key[1]}: {shown}", flush=True)
    summary = summarize(cases, records)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    done = manifest(cases, "completed", args.config, args.evaluator)
    (output / "manifest.json").write_text(json.dumps(done, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("gate_passes", "inaccessible_yes_cases")}, indent=2))


if __name__ == "__main__":
    main()
