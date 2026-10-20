"""Preserve frozen learner history when adapting grounding tasks for an evidence audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.pf_evidence_audit import evidence_audit_input  # noqa: E402


def adapt_catalog(catalog: dict) -> tuple[dict, dict]:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("tasks"), list):
        raise ValueError("The grounding catalog must contain tasks")
    tasks, receipts, case_histories = [], [], {}
    for entry in catalog["tasks"]:
        context = entry.get("learner_context")
        if not isinstance(context, dict):
            raise ValueError(f"Missing learner context: {entry.get('task_id')}")
        taught = context.get("recently_taught")
        if not isinstance(taught, list) or not taught or any(
            not isinstance(value, str) or not value.strip() for value in taught
        ):
            raise ValueError(f"Missing frozen prior-learning descriptions: {entry['task_id']}")
        case = entry["case_id"]
        if case in case_histories and case_histories[case] != context:
            raise ValueError(f"Learner context varies within the matched case: {case}")
        case_histories[case] = context
        resources = [{"resource": value, "taught_as": value} for value in taught]
        existing = context.get("assumed_prior_knowledge")
        if existing is not None and existing != resources:
            raise ValueError(
                "Existing assumed prior knowledge disagrees with frozen taught history"
            )
        adapted = {**entry, "learner_context": {**context, "assumed_prior_knowledge": resources}}
        sent = json.loads(evidence_audit_input(adapted))
        if sent["learner_context"]["assumed_prior_knowledge"] != resources:
            raise ValueError("The evaluator allowlist still loses prior-learning descriptions")
        if adapted["task"] != entry["task"]:
            raise ValueError("An adapter must not alter the student task")
        tasks.append(adapted)
        receipts.append({
            "task_id": entry["task_id"],
            "case_id": case,
            "arm": entry["arm"],
            "frozen_recently_taught": taught,
            "sent_assumed_prior_knowledge": resources,
            "student_task_unchanged": True,
        })
    if not tasks:
        raise ValueError("No grounding tasks supplied")
    return {"tasks": tasks}, {
        "version": "pf-grounding-history-adapter/v1",
        "reason": (
            "The prior audit's allowlist discarded recently_taught. Preserve that run; "
            "this translates the same stipulated learning history into the required "
            "assumed_prior_knowledge shape without adding skills or source evidence."
        ),
        "learner_history_is_stipulated_not_observed": True,
        "new_generation_requests": 0,
        "tasks": receipts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.catalog.read_bytes()
    catalog, receipt = adapt_catalog(json.loads(data))
    receipt["original_catalog_sha256"] = hashlib.sha256(data).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    (args.output / "adapter_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Validated {len(catalog['tasks'])} unchanged tasks and learner histories")


if __name__ == "__main__":
    main()
