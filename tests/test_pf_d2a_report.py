import json
from copy import deepcopy

import pytest

from scripts.report_pf_d2a_comparison import _counts, comparison, summarize


def item(status="ready", **kwargs):
    return {
        "status": status,
        "rating": {
            "disclosure": "absent",
            "mathematics": "valid",
            "accessible_start": "yes",
            "consequential_choice": "no",
            "target_preserved": "yes",
            **kwargs,
        },
    }


def test_stops_remain_in_denominator_and_unknowns_do_not_pass():
    counts = _counts(
        [
            item(),
            item(mathematics="unknown"),
            item(mathematics="missing_essential_data"),
            item(status="brief_not_selected"),
        ]
    )
    assert counts["attempts"] == 4
    assert counts["ready"] == 3
    assert counts["disclosure_free_ready"] == 3
    assert counts["disclosure_free_valid_accessible_ready"] == 1
    assert counts["invalid_or_missing_data_ready"] == 1
    assert counts["unknown_mathematics_ready"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("disclosure", "present"),
        ("mathematics", "unknown"),
        ("accessible_start", "unknown"),
        ("target_preserved", "unknown"),
    ],
)
def test_qualified_success_requires_all_checks(field, value):
    assert _counts([item(**{field: value})])["disclosure_free_valid_accessible_ready"] == 0


def test_choice_does_not_imply_disclosure_free_or_valid():
    counts = _counts(
        [
            item(consequential_choice="yes", disclosure="present"),
            item(consequential_choice="yes", mathematics="invalid"),
            item(consequential_choice="yes"),
        ]
    )
    assert counts["consequential_choice"] == {"yes": 3}
    assert counts["consequential_choice_valid_accessible_ready"] == 2
    assert counts["disclosure_free_valid_accessible_ready"] == 1


@pytest.fixture
def report_files(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    gallery = output / "gallery/development"
    gallery.mkdir(parents=True)
    source = tmp_path / "source.json"
    source.write_text("{}")
    digest = comparison._sha(source)
    snapshot = output / "snapshot.json"
    snapshot.write_bytes(source.read_bytes())
    schedule, mapping, cards, ratings = [], [], [], []
    for arm in comparison.ARMS:
        attempt = {
            "attempt_id": f"development--case--{arm}--1",
            "case_id": "case",
            "arm": arm,
            "repeat": 1,
            "phase": "development",
        }
        schedule.append(attempt)
        task_id = f"task-{arm}"
        task = {"title": "Task", "body": "A problem.", "question": "What follows?"}
        record = {
            **attempt,
            "status": "ready",
            "finished_at": "2026-10-11",
            "source_artifact_unchanged": True,
            "source_integrity_verified": True,
            "task": task,
        }
        directory = output / "attempts" / attempt["attempt_id"]
        directory.mkdir(parents=True)
        comparison._write_json(directory / "result.json", record)
        mapping.append({"task_id": task_id, **attempt, "status": "ready"})
        cards.append({"task_id": task_id, "task": task})
        ratings.append({"task_id": task_id, **item()["rating"]})
    manifest = {
        "schedule": schedule,
        "source_hashes": {str(source): digest},
        "snapshots": {str(source): snapshot.name},
        "inputs": {"case": {"source": str(source), "sha256": digest}},
        "limits": {"max_calls_total": 18},
        "usage": comparison.usage_summary([]),
        "phase_usage": {phase: comparison.usage_summary([]) for phase in comparison.PHASES},
        "config": {
            "cases": [{"id": "case"}],
            "protocol": {
                "gain_minimum_disclosure_free_ready_tasks": 6,
                "maximum_ready_task_loss": 1,
                "maximum_increase_invalid_or_missing_data": 0,
                "pricing_status": "unknown",
            },
        },
    }
    comparison._write_json(output / "manifest.json", manifest)
    comparison._write_json(output / "development_task_mapping.json", {"tasks": mapping})
    comparison._write_json(gallery / "review.json", {"tasks": cards})
    review_path = output / "assistant_review.json"
    review = {
        "schema_version": "pf-d2a-assistant-review/v1",
        "evidence_kind": "assistant_reading",
        "ratings": ratings,
    }
    comparison._write_json(review_path, review)
    return output, review_path, review


def test_complete_report_preserves_cost_unknown_and_stops_promotion(report_files):
    output, review_path, _ = report_files
    report = summarize(output, review_path)
    assert report["decision"]["result"] == "stop_no_promotion"
    assert report["arms"]["baseline"]["attempts"] == 1
    assert report["usage"]["monetary_cost"] is None
    assert report["provenance"]["sources_and_inputs_verified"]


@pytest.mark.parametrize("change", ["missing", "duplicate", "invalid"])
def test_report_rejects_unusable_review(report_files, change):
    output, path, original = report_files
    review = deepcopy(original)
    if change == "missing":
        review["ratings"].pop()
    elif change == "duplicate":
        review["ratings"].append(review["ratings"][0])
    else:
        review["ratings"][0]["mathematics"] = "probably"
    comparison._write_json(path, review)
    with pytest.raises(ValueError):
        summarize(output, path)


def test_report_rejects_stale_gallery(report_files):
    output, review_path, _ = report_files
    path = output / "gallery/development/review.json"
    cards = json.loads(path.read_text())
    cards["tasks"][0]["task"]["body"] = "Changed after reading."
    comparison._write_json(path, cards)
    with pytest.raises(ValueError, match="Gallery is stale"):
        summarize(output, review_path)


def test_report_rejects_changed_frozen_source(report_files):
    output, review_path, _ = report_files
    manifest = json.loads((output / "manifest.json").read_text())
    source = next(iter(manifest["source_hashes"]))
    from pathlib import Path

    Path(source).write_text('{"changed": true}')
    with pytest.raises(ValueError, match="Frozen source changed"):
        summarize(output, review_path)
