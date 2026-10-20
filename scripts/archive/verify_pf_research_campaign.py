"""Offline checks that corrected grounding audits preserve tasks and stated learning."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.pf_evidence_audit import evidence_audit_input  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(generation: Path, audit: Path) -> dict:
    original = json.loads((generation / "all_tasks.json").read_text())["tasks"]
    frozen = json.loads((audit / "catalog.json").read_text())
    frozen = frozen["tasks"] if isinstance(frozen, dict) else frozen
    tasks = {entry["task_id"]: entry for entry in original}
    inputs = {entry["task_id"]: entry for entry in frozen}
    if len(tasks) != len(original) or tasks.keys() != inputs.keys():
        raise ValueError("Corrected audit must retain exactly the original scheduled tasks")
    history_per_case = {}
    for task_id, task in tasks.items():
        path = Path(task["source_path"])
        path = path if path.is_absolute() else ROOT / path
        if sha256(path.read_bytes()) != task["source_sha256"]:
            raise ValueError(f"Generated task source changed: {task_id}")
        adapted = inputs[task_id]
        if adapted["task"] != task["task"]:
            raise ValueError(f"Student text changed in evaluator adaptation: {task_id}")
        sent = json.loads(evidence_audit_input(adapted))
        taught = task["learner_context"]["recently_taught"]
        actual = sent["learner_context"]["assumed_prior_knowledge"]
        if [item["resource"] for item in actual] != taught:
            raise ValueError(f"Learning history changed: {task_id}")
        if [item["taught_as"] for item in actual] != taught:
            raise ValueError(f"Additional teaching details were invented: {task_id}")
        case = task["case_id"]
        if case in history_per_case and history_per_case[case] != actual:
            raise ValueError(f"Learning history differs between matched arms: {case}")
        history_per_case[case] = actual
        if set(sent) != {"learning_target", "learner_context", "student_task"}:
            raise ValueError("Private condition metadata reached the auditor")
    judgments = [json.loads(path.read_text()) for path in (audit / "judgments").glob("*/*.json")]
    pairs = [(record["task_id"], record["judge"]) for record in judgments]
    if len(pairs) != len(set(pairs)) or len(pairs) != 2 * len(tasks):
        raise ValueError("Every original task needs two recorded, nonduplicate judge attempts")
    for record in judgments:
        expected = evidence_audit_input(inputs[record["task_id"]])
        if record["user_input"] != expected:
            raise ValueError("The recorded model request differs from the repaired input")
        if record["input_sha256"] != sha256(expected.encode()):
            raise ValueError("A recorded auditor input hash differs")
    return {
        "schema_version": "pf-campaign-verification/v1",
        "scheduled_main_tasks": len(tasks),
        "task_specifications": len(history_per_case),
        "recorded_main_audits": len(judgments),
        "task_source_hashes_unchanged": True,
        "student_text_unchanged_by_history_adapter": True,
        "same_stipulated_prior_learning_in_all_arms": True,
        "actual_model_inputs_contain_that_history": True,
        "actual_model_inputs_exclude_condition_labels": True,
        "actual_model_input_hashes_verified": True,
        "judge_statuses": dict(Counter(record["status"] for record in judgments)),
        "new_model_calls_for_verification": 0,
        "verification_boundary": "Request fidelity and provenance, not pedagogical validity",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Verification records are immutable; choose a fresh output")
    result = verify(args.generation, args.audit)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
