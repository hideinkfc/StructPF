import json
import shutil
import uuid
from pathlib import Path

import pytest

from scripts import build_pf_measure_catalog as catalog

TASK = {
    "status": "ready",
    "title": "Compare the records",
    "body": "A has 2, 4, 6. B has 1, 4, 7.",
    "question": "Invent and justify a consistency comparison.",
    "solution": "Do not send this solution to students.",
    "withheld": [{"quote": "Do not send internal notes."}],
}
TARGET = "Comparing variability before instruction."
HISTORY = {
    "grade": 7,
    "recently_taught": [{"resource": "Mean", "taught_as": "Add and divide by the count."}],
}


@pytest.fixture
def tree():
    # Keep all fixture writes inside the repository, not system temporary paths.
    root = Path(__file__).parent / (".pf_catalog_test_" + uuid.uuid4().hex)
    root.mkdir()
    (root / "experiments/results").mkdir(parents=True)
    try:
        yield root.resolve()
    finally:
        shutil.rmtree(root)


def save(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def result(root, run="run", **fields):
    return save(
        root,
        f"experiments/results/{run}/result.json",
        {
            "status": "ready",
            "task": TASK,
            "learning_target": TARGET,
            "learner_context": HISTORY,
            **fields,
        },
    )


def build(root):
    return catalog.build_catalog(root)


def test_extracts_only_explicit_student_fields():
    text, method = catalog.student_text(TASK)
    assert text == "\n\n".join(TASK[key] for key in ("title", "body", "question"))
    assert "Do not send" not in text
    assert method == "title_body_question"


def test_legacy_sections_exclude_consolidation():
    text, _ = catalog.student_text(
        {
            "sections": {
                "TOPIC": "Metadata",
                "NARRATIVE": "Student situation.",
                "TASK": "Choose a comparison.\n\n## CONSOLIDATION NOTE\nHidden answer",
                "CONSOLIDATION NOTE": "Another hidden answer",
            }
        }
    )
    assert text == "Student situation.\n\nChoose a comparison."


def test_invalid_complete_envelope_and_flagged_draft_are_not_dropped(tree):
    result(tree, "invalid", status="invalid_response", error="unexpected extra key")
    result(
        tree,
        "flagged",
        task={
            **TASK,
            "body": "Different data.",
            "quality_status": "needs_review",
            "quality_findings": ["Unresolved."],
        },
    )
    value = build(tree)
    assert len(value["cases"]) == 2
    assert {case["occurrences"][0]["envelope_status"] for case in value["cases"]} == {
        "invalid",
        "flagged_usable_draft",
    }
    assert not value["unassessable"]


def test_exact_dedup_preserves_all_occurrences_but_not_semantic_variants(tree):
    result(tree, "one")
    result(
        tree,
        "two",
        learner_context={
            "grade": 7,
            "assumed_prior_knowledge": HISTORY["recently_taught"],
        },
    )
    result(tree, "different_target", learning_target="A distinct recorded target.")
    result(
        tree,
        "different_history",
        learner_context={
            "grade": 7,
            "recently_taught": [{"resource": "Range", "taught_as": "Subtract extremes."}],
        },
    )
    result(tree, "similar", task={**TASK, "question": TASK["question"] + " Explain."})
    result(tree, "whitespace", task={**TASK, "body": TASK["body"] + " "})
    value = build(tree)
    assert len(value["cases"]) == 5
    assert sorted(len(case["occurrences"]) for case in value["cases"]) == [1, 1, 1, 1, 2]


def test_missing_inputs_and_blocked_attempts_remain_explicit(tree):
    result(tree, "missing", learning_target=None, learner_context=None)
    result(tree, "blocked", status="data_review_needed", task=None, error="No usable output.")
    value = build(tree)
    assert value["cases"][0]["learning_target"] is None
    assert value["cases"][0]["learner_context"] is None
    assert value["cases"][0]["input_status"]["learner_prerequisites"] == "unavailable"
    assert value["unassessable"][0]["occurrences"][0]["saved_status"] == "data_review_needed"
    assert value["unassessable"][0]["occurrences"][0]["error"] == "No usable output."


def test_recently_taught_strings_never_invent_teaching_details():
    context = catalog.normalize_context({"recently_taught": ["Unit rates"]})
    assert context["assumed_prior_knowledge"] == [{"resource": "Unit rates", "taught_as": None}]
    assert catalog.has_history(context)
    assert catalog.has_history(catalog.normalize_context({"recently_taught": []}))
    assert not catalog.has_history(
        catalog.normalize_context({"recently_taught": [{"unknown": "value"}]})
    )
    assert not catalog.has_history(catalog.normalize_context({"grade": 7}))


def test_pipeline_uses_saved_case_and_recorded_d1_not_current_defaults(tree):
    path = save(
        tree,
        "experiments/results/pf_old/run/result.json",
        {
            "case_id": "saved",
            "status": "ready",
            "case_input": {"id": "saved", "target_concept": TARGET, "grade": 7},
            "prior_context": {
                "source": "d1_recommendations",
                "condition": "grounded",
                "recommendations": [
                    {
                        "resource": "Old supplied expert resource",
                        "taught_as": "Recorded teaching.",
                        "student_move": "Internal expected move",
                        "falls_short_because": "Internal limit",
                    },
                ],
            },
            "stages": {"D2_D3": {"task": TASK}},
        },
    )
    value = build(tree)
    case = value["cases"][0]
    assert case["learning_target"] == TARGET
    assert case["learner_context"]["assumed_prior_knowledge"] == [
        {"resource": "Old supplied expert resource", "taught_as": "Recorded teaching."},
    ]
    occurrence = case["occurrences"][0]
    assert occurrence["method"] == "pipeline"
    assert occurrence["source"]["sha256"] == catalog.digest(path.read_bytes())
    assert occurrence["historical_condition_evidence"]["prior_context"]


def test_hash_verified_configuration_supplies_original_context(tree):
    config = save(
        tree,
        "experiments/configs/frozen.json",
        {
            "cells": [
                {"cell_id": "music", "case": {"target_concept": TARGET}, "learner_context": HISTORY}
            ],
        },
    )
    save(
        tree,
        "experiments/results/pf_multi/manifest.json",
        {
            "config_sha256": catalog.digest(config.read_bytes()),
        },
    )
    save(
        tree,
        "experiments/results/pf_multi/attempts/music.json",
        {
            "cell_id": "music",
            "status": "ready",
            "task": TASK,
        },
    )
    value = build(tree)
    case = value["cases"][0]
    assert case["learning_target"] == TARGET
    assert case["input_status"]["learner_prerequisites"] == "available"
    assert any(
        item["path"] == "experiments/configs/frozen.json"
        for item in case["occurrences"][0]["input_sources"]
    )


def test_unverified_changed_configuration_is_not_historical_evidence(tree):
    save(
        tree,
        "experiments/configs/changed.json",
        {
            "learning_target": "Not the historical target",
            "learner_context": HISTORY,
        },
    )
    save(
        tree,
        "experiments/results/pf_multi/manifest.json",
        {
            "config_path": "experiments/configs/changed.json",
            "config_sha256": "0" * 64,
        },
    )
    save(
        tree,
        "experiments/results/pf_multi/attempts/music.json",
        {
            "cell_id": "music",
            "status": "ready",
            "task": TASK,
        },
    )
    case = build(tree)["cases"][0]
    assert case["learning_target"] is None
    assert case["learner_context"] is None


def test_writer_trace_recovers_original_prompt_and_failed_attempt(tree):
    path = tree / "experiments/results/pf_replay/model_calls.jsonl"
    path.parent.mkdir(parents=True)
    rows = [
        {"stage": "D3.writer", "event": "model_call_started", "user_prompt": "Unused start"},
        {
            "stage": "D3.writer",
            "event": "model_call_finished",
            "payload": TASK,
            "user_prompt": "STUDENT CONTEXT:\n"
            + json.dumps(HISTORY)
            + "\nTARGET CONCEPT: "
            + TARGET,
        },
        {"stage": "V1.generate", "event": "model_call_finished", "error": "Original API error."},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows))
    value = build(tree)
    assert len(value["cases"]) == 1
    assert value["cases"][0]["learning_target"] == TARGET
    assert len(value["unassessable"]) == 1
    assert value["unassessable"][0]["occurrences"][0]["error"] == "Original API error."


def test_revision_json_prompt_target_is_recovered_without_learner_attempts(tree):
    path = tree / "experiments/results/pf_revision/model_calls.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "stage": "task.revision",
                "raw_text": json.dumps(TASK),
                "user": json.dumps(
                    {
                        "internal_learning_target": TARGET,
                        "learner_context": HISTORY,
                        "learner_attempts": [{"answer": "Must not become learner context"}],
                    }
                ),
            }
        )
    )
    case = build(tree)["cases"][0]
    assert case["learning_target"] == TARGET
    assert "learner_attempts" not in case["learner_context"]


def test_finished_trace_uses_matching_start_event_not_another_attempt(tree):
    path = tree / "experiments/results/pf_revision/model_calls.jsonl"
    path.parent.mkdir(parents=True)
    rows = []
    for call_id, target in [("one", TARGET), ("two", "Another recorded target.")]:
        rows.extend(
            [
                {
                    "stage": "task.revision",
                    "call_id": call_id,
                    "event": "model_call_started",
                    "user_prompt": json.dumps(
                        {
                            "internal_learning_target": target,
                            "learner_context": HISTORY,
                        }
                    ),
                },
                {
                    "stage": "task.revision",
                    "call_id": call_id,
                    "event": "model_call_finished",
                    "payload": TASK,
                },
            ]
        )
    path.write_text("\n".join(json.dumps(row) for row in rows))
    value = build(tree)
    assert len(value["cases"]) == 2
    assert {case["learning_target"] for case in value["cases"]} == {
        TARGET,
        "Another recorded target.",
    }
    assert all(
        case["input_status"]["learner_prerequisites"] == "available" for case in value["cases"]
    )


def test_writer_attempts_preserve_rejected_and_latest_usable_drafts(tree):
    first = {**TASK, "body": "An earlier complete draft.", "status": "blocked"}
    result(
        tree,
        task={
            **TASK,
            "writer_attempts": [
                {"payload": first, "status": "blocked"},
                {"payload": TASK, "status": "ready"},
            ],
        },
    )
    value = build(tree)
    assert len(value["cases"]) == 2
    assert sum(len(case["occurrences"]) for case in value["cases"]) == 3
    assert any(
        item["envelope_status"] == "invalid"
        for case in value["cases"]
        for item in case["occurrences"]
    )


def test_judgment_and_snapshot_copies_link_without_new_generations(tree):
    original = result(tree)
    save(
        tree,
        "experiments/results/pf_review/catalog.json",
        {
            "tasks": [
                {
                    "task": TASK,
                    "source_path": original.relative_to(tree).as_posix(),
                    "source_sha256": catalog.digest(original.read_bytes()),
                    "learning_target": "A later judge's different target.",
                }
            ]
        },
    )
    save(
        tree,
        "experiments/results/pf_review/source_snapshot/result.json",
        {
            "task": TASK,
            "status": "ready",
        },
    )
    value = build(tree)
    assert len(value["cases"]) == 1
    case = value["cases"][0]
    assert len(case["occurrences"]) == 1
    assert len(case["origin_references"]) == 2
    assert case["learning_target"] == TARGET


def test_parse_errors_are_logged_and_campaign_is_not_reimported(tree):
    broken = tree / "experiments/results/broken.json"
    broken.write_text('{"unfinished":')
    save(
        tree,
        "experiments/results/pf_measure_campaign_20261014/calibration.json",
        {
            "status": "ready",
            "task": TASK,
        },
    )
    result(tree)
    value = build(tree)
    assert len(value["cases"]) == 1
    assert value["inventory_summary"]["parse_error_count"] == 1
    assert value["inventory_summary"]["inspected_file_count"] == 2


def test_frozen_output_never_overwrites(tree):
    path = tree / "catalog.json"
    catalog.write_frozen_catalog({"original": True}, path)
    with pytest.raises(FileExistsError):
        catalog.write_frozen_catalog({"original": False}, path)
    assert json.loads(path.read_text()) == {"original": True}


def test_incomplete_structured_task_is_unavailable_not_literal_json():
    text, reason = catalog.student_text('{"body": "unfinished"')
    assert text is None
    assert reason == "unparseable_structured_task"


def test_repository_known_run_inventory():
    value = catalog.build_catalog()
    checks = {check["name"]: check for check in value["inventory_summary"]["known_run_checks"]}
    assert len(checks) == 7
    assert all(check["pass"] for check in checks.values())
    assert checks["multi_theme_main"]["observed_ready"] == 238
    assert checks["multi_theme_main"]["observed_with_student_task"] == 240
    assert checks["latest_method_comparison_fresh"]["by_method"] == {"direct": 9, "pipeline": 9}
    assert checks["grounding_main"]["observed_with_student_task"] == 60
    assert checks["benchmark_v2"]["pending_unexecuted_slots"] == 108
    assert checks["benchmark_v3"]["pending_unexecuted_slots"] == 108
    invalid = [
        item
        for case in value["cases"]
        for item in case["occurrences"]
        if "pf_rahimi_multi_theme_20261013/main_30/attempts/" in item["source"]["path"]
        and item["envelope_status"] == "invalid"
    ]
    assert len(invalid) == 2
