from collections import Counter

import pytest

from scripts import export_pf_grounding_catalog as catalog
from scripts import run_pf_grounding_study as study


@pytest.fixture
def output(tmp_path):
    directory = tmp_path / "study"
    config = study.read_json(study.DEFAULT_CONFIG)
    schedule = study.schedule(config)
    hashes = {}
    for case in config["cases"] + config["calibration_cases"]:
        for arm in study.ARMS:
            path = directory / "inputs" / case["id"] / f"context_{arm}.json"
            study.save_json(path, {
                "learner_context": {
                    "grade": case["grade"],
                    "recently_taught": case["teacher_recently_taught"],
                },
            })
            hashes[str(path.relative_to(directory))] = study.digest(path)
    manifest = {
        "config": config,
        "schedule": schedule,
        "input_hashes": hashes,
        "source_hashes": {},
    }
    study.save_json(directory / "manifest.json", manifest)
    main = [item for item in schedule if item["phase"] == "main"]
    for item, failed in ((main[0], False), (main[1], True)):
        attempt = directory / item["attempt_path"]
        study.save_json(attempt / "result.json", {
            "status": "D2_D3_failed" if failed else "completed",
            "error": "Illustrative transport error" if failed else None,
            "stages": {"D2_D3": {"task": None if failed else {
                "status": "ready", "title": "Illustrative task",
                "body": "Illustrative body.", "question": "Illustrative question?",
            }}},
        })
        study.complete_receipt(attempt)
    (directory / main[2]["attempt_path"]).mkdir(parents=True)
    for name in ("all_tasks", "calibration_tasks", "evaluator_input"):
        study.save_json(directory / f"{name}.json", [{"student_task": "legacy example"}])
    return directory, manifest


def test_shared_catalog_keeps_all_slots_and_explicit_missing_statuses(output):
    directory, manifest = output
    original_manifest_hash = study.digest(directory / "manifest.json")
    interface = catalog.export_catalog(directory)
    records = study.read_json(directory / "all_tasks.json")
    assert set(records) == {"tasks"}
    assert len(records["tasks"]) == 60
    assert all(set(catalog.CATALOG_FIELDS) <= record.keys() for record in records["tasks"])
    assert Counter(record["status"] for record in records["tasks"]) == {
        "completed": 1, "D2_D3_failed": 1, "running": 1, "not_run": 57,
    }
    assert records["tasks"][0]["task"]["title"] == "Illustrative task"
    failed = records["tasks"][1]
    assert failed["task"] is None and not failed["produced"]
    assert failed["error"] == "Illustrative transport error"
    assert failed["source_sha256"]
    assert records["tasks"][2]["task"] is None
    assert records["tasks"][2]["source_sha256"] is None
    assert interface["main_produced_records"] == 1
    assert study.digest(directory / "manifest.json") == original_manifest_hash
    assert len(study.read_json(directory / "calibration_tasks.json")["tasks"]) == 3
    assert len(manifest["schedule"]) == 63


def test_evaluator_is_arm_free_and_legacy_lists_remain_identical(output):
    directory, _ = output
    originals = {
        name: study.digest(directory / f"{name}.json")
        for name in ("all_tasks", "calibration_tasks", "evaluator_input")
    }
    catalog.export_catalog(directory)
    evaluator = study.read_json(directory / "evaluator_input.json")
    assert len(evaluator["tasks"]) == 1
    assert set(evaluator["tasks"][0]) == set(catalog.EVALUATOR_FIELDS)
    assert "arm" not in evaluator["tasks"][0]
    for name, digest in originals.items():
        assert study.digest(directory / f"{name}_legacy_list.json") == digest
    catalog.export_catalog(directory)
    for name, digest in originals.items():
        assert study.digest(directory / f"{name}_legacy_list.json") == digest


def test_reporting_boundary_uses_targets_not_twenty_independent_pairs():
    boundary = catalog.REPORTING_BOUNDARY
    assert boundary["independent_blocks"] == 5
    assert boundary["matched_slots_per_arm"] == 20
    assert boundary["five_target_two_sided_sign_test_minimum_p"] == 2 / (2 ** 5)
    assert boundary["additional_generation_or_simulated_attempts"] is False
