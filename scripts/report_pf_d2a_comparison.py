#!/usr/bin/env python3
"""Aggregate recorded assistant readings without adding a model quality judge."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts import run_pf_d2a_comparison as comparison

FIELDS = {
    "disclosure": {"present", "absent", "unknown", "not_available"},
    "mathematics": {"valid", "invalid", "missing_essential_data", "unknown", "not_available"},
    "accessible_start": {"yes", "no", "unknown", "not_available"},
    "consequential_choice": {"yes", "no", "unknown", "not_available"},
    "target_preserved": {"yes", "no", "unknown", "not_available"},
}


def _counts(items: list[dict]) -> dict:
    ready = [item for item in items if item["status"] == "ready"]
    disclosure_free = [item for item in ready if item["rating"]["disclosure"] == "absent"]
    return {
        "attempts": len(items),
        "ready": len(ready),
        "statuses": dict(Counter(item["status"] for item in items)),
        "disclosure_free_ready": len(disclosure_free),
        "disclosure_free_valid_accessible_ready": sum(
            item["rating"]["mathematics"] == "valid"
            and item["rating"]["accessible_start"] == "yes"
            and item["rating"]["target_preserved"] == "yes"
            for item in disclosure_free
        ),
        **{field: dict(Counter(item["rating"][field] for item in ready)) for field in FIELDS},
        "invalid_or_missing_data_ready": sum(
            item["rating"]["mathematics"] in {"invalid", "missing_essential_data"} for item in ready
        ),
        "unknown_mathematics_ready": sum(
            item["rating"]["mathematics"] == "unknown" for item in ready
        ),
        "consequential_choice_valid_accessible_ready": sum(
            item["rating"]["mathematics"] == "valid"
            and item["rating"]["accessible_start"] == "yes"
            and item["rating"]["consequential_choice"] == "yes"
            for item in ready
        ),
    }


def summarize(output: Path, review_path: Path) -> dict:
    output = output.resolve()
    review_path = review_path.resolve()
    manifest = json.loads((output / "manifest.json").read_text())
    review = json.loads(review_path.read_text())
    if review.get("schema_version") != "pf-d2a-assistant-review/v1":
        raise ValueError("Unsupported review schema")
    mapping_path = output / "development_task_mapping.json"
    gallery_path = output / "gallery/development/review.json"
    mapping = json.loads(mapping_path.read_text())["tasks"]
    cards = json.loads(gallery_path.read_text())["tasks"]
    ratings = review["ratings"]
    for rows in (mapping, cards, ratings):
        ids = [row["task_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate review task IDs")
    by_id = {row["task_id"]: row for row in ratings}
    card_by_id = {row["task_id"]: row for row in cards}
    if set(by_id) != set(card_by_id) or set(by_id) != {row["task_id"] for row in mapping}:
        raise ValueError("Every scheduled task, including absent tasks, needs exactly one rating")
    expected = {row["attempt_id"] for row in manifest["schedule"] if row["phase"] == "development"}
    if len(mapping) != len(expected) or {row["attempt_id"] for row in mapping} != expected:
        raise ValueError("Mapping does not cover the frozen development schedule")
    for source, digest in manifest["source_hashes"].items():
        if comparison._sha(Path(source)) != digest:
            raise ValueError(f"Frozen source changed: {source}")
    for source, snapshot in manifest["snapshots"].items():
        if comparison._sha(output / snapshot) != manifest["source_hashes"][source]:
            raise ValueError(f"Frozen snapshot changed: {snapshot}")
    for item in manifest["inputs"].values():
        if comparison._sha(Path(item["source"])) != item["sha256"]:
            raise ValueError("Frozen D1 input changed")
    items = []
    for row in mapping:
        rating = by_id[row["task_id"]]
        for field, values in FIELDS.items():
            if rating.get(field) not in values:
                raise ValueError(f"Invalid {field} rating for {row['task_id']}")
        result_path = output / "attempts" / row["attempt_id"] / "result.json"
        record = json.loads(result_path.read_text())
        if not record.get("finished_at") or record["status"] in comparison.UNFINISHED:
            raise ValueError("Development contains unfinished attempts")
        if any(
            record.get(key) != row[key]
            for key in ("attempt_id", "case_id", "arm", "repeat", "phase", "status")
        ):
            raise ValueError("Mapping and attempt disagree")
        if not record["source_artifact_unchanged"] or not record["source_integrity_verified"]:
            raise ValueError("Attempt source integrity failed")
        text = (
            {key: record["task"][key] for key in ("title", "body", "question")}
            if isinstance(record.get("task"), dict)
            else None
        )
        if text != card_by_id[row["task_id"]]["task"]:
            raise ValueError("Gallery is stale relative to recorded task")
        has_text = bool(text and any(value.strip() for value in text.values()))
        if record["status"] == "ready":
            if not has_text or any(rating[field] == "not_available" for field in FIELDS):
                raise ValueError("Ready task needs text and substantive ratings")
        elif has_text or any(rating[field] != "not_available" for field in FIELDS):
            raise ValueError("Stopped attempt must remain unavailable, not a passed task")
        items.append({**row, "rating": rating, "result_sha256": comparison._sha(result_path)})
    arms = {arm: _counts([item for item in items if item["arm"] == arm]) for arm in comparison.ARMS}
    baseline, intervention = (arms[arm] for arm in comparison.ARMS)
    protocol = manifest["config"]["protocol"]
    gain = intervention["disclosure_free_ready"] - baseline["disclosure_free_ready"]
    ready_change = intervention["ready"] - baseline["ready"]
    invalid_change = (
        intervention["invalid_or_missing_data_ready"] - baseline["invalid_or_missing_data_ready"]
    )
    rules = {
        "disclosure_free_gain_met": gain >= protocol["gain_minimum_disclosure_free_ready_tasks"],
        "ready_loss_within_limit": ready_change >= -protocol["maximum_ready_task_loss"],
        "invalid_or_missing_increase_within_limit": invalid_change
        <= protocol["maximum_increase_invalid_or_missing_data"],
    }
    rows = comparison._rows(output / "ledger.jsonl")
    budget = comparison.RequestBudget(output, manifest["limits"])
    if budget.rows != rows or comparison.usage_summary(rows) != manifest["usage"]:
        raise ValueError("Manifest usage disagrees with ledger")
    return {
        "schema_version": "pf-d2a-comparison-report/v1",
        "evidence_kind": review["evidence_kind"],
        "arms": arms,
        "by_case": {
            case["id"]: {
                arm: _counts(
                    [item for item in items if item["arm"] == arm and item["case_id"] == case["id"]]
                )
                for arm in comparison.ARMS
            }
            for case in manifest["config"]["cases"]
        },
        "decision": {
            "result": "candidate_gain_requires_independent_check"
            if all(rules.values())
            else "stop_no_promotion",
            "disclosure_free_ready_gain": gain,
            "ready_task_change": ready_change,
            "invalid_or_missing_data_change": invalid_change,
            "rules": rules,
        },
        "usage": {
            "all": comparison.usage_summary(rows),
            "by_phase": manifest["phase_usage"],
            "development_by_arm": {
                arm: comparison.usage_summary(
                    [row for row in rows if row["phase"] == "development" and row["arm"] == arm]
                )
                for arm in comparison.ARMS
            },
            "reasoning_tokens_are_subset_of_output": True,
            "monetary_cost": None,
            "pricing_status": protocol["pricing_status"],
        },
        "provenance": {
            "manifest_sha256": comparison._sha(output / "manifest.json"),
            "review_sha256": comparison._sha(review_path),
            "gallery_sha256": comparison._sha(gallery_path),
            "mapping_sha256": comparison._sha(mapping_path),
            "report_script_sha256": comparison._sha(Path(__file__)),
            "sources_and_inputs_verified": True,
        },
        "reviewed_attempts": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.output_dir, args.review)
    comparison._write_json(args.output_dir / "comparison_report.json", report)
    print(json.dumps({"arms": report["arms"], "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
