import copy
import json
import threading
from types import SimpleNamespace

import pytest

from scripts import run_pf_grounding_study as study


def fake_lc_context(case, **kwargs):
    response = [
        {
            "caseIdentifierUUID": f"standard-{number}",
            "description": f"Illustrative mathematical reference {number}; not real evidence.",
            "author": "Illustrative author",
            "provider": "Illustrative provider",
            "license": "Illustrative license",
            "attributionStatement": "Illustrative attribution",
            "jurisdiction": "Illustrative jurisdiction",
            "statementCode": f"TEST.{number}",
        }
        for number in range(1, 4)
    ]
    return {
        "schema_version": study.lc.SCHEMA_VERSION,
        "api_base_url": study.lc.BASE_URL,
        "request": {
            "query": kwargs["query"],
            "academic_subject": "Mathematics",
            "grade_levels": [],
            "jurisdiction": None,
            "limit": study.lc.SEARCH_LIMIT,
        },
        "retrieved_at_utc": "2026-10-12T22:00:00+00:00",
        "response": response,
        "cache_hit": False,
    }


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setattr(study.lc, "retrieve_context", fake_lc_context)
    monkeypatch.setattr(
        study, "load_client", lambda which: (SimpleNamespace(close=lambda: None), "gpt-5.6-luna")
    )
    output = tmp_path / "study"
    manifest = study.prepare(study.DEFAULT_CONFIG, output)
    return output, manifest


def test_schedule_and_current_caps():
    config = study.read_json(study.DEFAULT_CONFIG)
    study.validate_config(config)
    schedule = study.schedule(config)
    assert schedule == study.schedule(config)
    assert len(schedule) == len({item["task_id"] for item in schedule}) == 63
    assert sum(item["phase"] == "main" for item in schedule) == 60
    for case in config["cases"]:
        assert sum(item["case_id"] == case["id"] for item in schedule) == 12
    assert study.max_calls_per_attempt() == 15
    assert config["request_cap"] == 800
    assert all("A" not in item["task_id"] for item in schedule)


def test_prepare_freezes_only_evidence_difference(frozen, monkeypatch):
    output, manifest = frozen
    assert manifest["protocol"]["worst_case_scheduled_requests"] == 945
    for case in manifest["config"]["cases"]:
        inputs = output / "inputs" / case["id"]
        contexts = {arm: study.read_json(inputs / f"context_{arm}.json") for arm in study.ARMS}
        non_evidence = [
            {key: value for key, value in context.items() if key != study.INVENTORY_KEY}
            for context in contexts.values()
        ]
        assert non_evidence[0] == non_evidence[1] == non_evidence[2]
        inventories = [context[study.INVENTORY_KEY] for context in contexts.values()]
        assert {value["instruction"] for value in inventories} == {study.REFERENCE_INSTRUCTION}
        assert not inventories[0]["local_curriculum"]
        assert not inventories[0]["learning_commons_standard_descriptions"]
        assert inventories[1]["local_curriculum"] == inventories[2]["local_curriculum"]
        assert not inventories[1]["learning_commons_standard_descriptions"]
        assert len(inventories[2]["learning_commons_standard_descriptions"]) == 3
        assert all(
            record["license"] for record in inventories[2]["learning_commons_standard_descriptions"]
        )
        context = study.stages._prior_context_from_d1(inputs / "fixed_d1.json", case["id"])
        assert [row["resource"] for row in context["recommendations"]] == case[
            "teacher_recently_taught"
        ]
        assert "learning_commons" not in context
    monkeypatch.setattr(
        study.lc,
        "retrieve_context",
        lambda *args, **kwargs: pytest.fail("Resume must not retrieve again"),
    )
    assert study.prepare(study.DEFAULT_CONFIG, output) == manifest


def test_input_mutation_is_rejected(frozen):
    output, manifest = frozen
    item = manifest["schedule"][0]
    path = output / "inputs" / item["case_id"] / "context_A.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="Frozen study input changed"):
        study.verify_inputs(output, manifest)


def test_text_budget_preserves_source_hash():
    records = [{"text": "abcde", "source": 1}, {"text": "fghij", "source": 2}]
    result = study.limited_records(records, "text", 7)
    assert [row["text"] for row in result] == ["abcde", "fg"]
    assert result[1]["text_truncated"]
    assert result[1]["source_characters"] == 5
    assert result[1]["presented_characters"] == 2
    assert records[1]["text"] == "fghij"


def test_request_boundary_has_hard_cap_and_usage(tmp_path):
    calls = []
    usage = SimpleNamespace(
        model_dump=lambda **kwargs: {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    )

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id="fake-response",
            model="fake-model",
            usage=usage,
            choices=[SimpleNamespace(finish_reason="stop")],
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    client.with_options = lambda **kwargs: client
    counter = SimpleNamespace(value=0)
    path = tmp_path / "request_usage.jsonl"
    observed = study.ObservedClient(client, path, counter, threading.Lock(), 1, 15)
    assert observed.with_options(max_retries=0) is observed
    observed.chat.completions.create(model="fake", messages=[])
    with pytest.raises(study.RequestBudgetExceededError):
        observed.chat.completions.create(model="fake", messages=[])
    assert len(calls) == counter.value == 1
    records = study.usage_records(tmp_path)
    assert records[1]["usage"]["total_tokens"] == 18
    assert records[-1]["event"] == "budget_exhausted"


def test_terminal_receipts_preserve_errors_and_reject_changes(tmp_path):
    directory = tmp_path / "attempt"
    directory.mkdir()
    study.save_json(directory / "result.json", {"status": "D2_D3_failed", "error": "API"})
    study.complete_receipt(directory)
    assert study.existing_result(directory)["error"] == "API"
    study.save_json(directory / "result.json", {"status": "completed"})
    with pytest.raises(ValueError, match="immutable attempt was changed"):
        study.existing_result(directory)


def test_resume_refuses_incomplete_attempt(tmp_path):
    directory = tmp_path / "attempt"
    directory.mkdir()
    study.save_json(directory / "result.json", {"status": "running"})
    with pytest.raises(ValueError, match="never regenerate"):
        study.existing_result(directory)


def save_fake_completed(output, item, *, failed=False):
    inputs = output / "inputs" / item["case_id"]
    directory = output / item["attempt_path"]
    directory.mkdir(parents=True)
    task = {
        "status": "ready",
        "title": "Illustrative test task",
        "body": "Illustrative task body, not measured student evidence.",
        "question": "Illustrative question?",
    }
    packet = study.read_json(inputs / "fixed_d1.json")
    packet["origin"] = "diagnostic_reused_d1"
    study.save_json(directory / "d1.json", packet)
    study.save_json(
        directory / "result.json",
        {
            "status": "D2_D3_failed" if failed else "completed",
            "error": "Illustrative API error" if failed else None,
            "case_input": study.read_json(inputs / "case.json"),
            "stages": {"D2_D3": {"task": None if failed else task}},
            "model_call_count": 1,
        },
    )
    shared = study.read_json(inputs / f"context_{item['arm']}.json")
    record = {
        "call_id": "test:1",
        "user_prompt": (
            "Illustrative task request"
            "\n\nSHARED BENCHMARK CONTEXT (use throughout this design stage):\n"
            + json.dumps(shared)
        ),
    }
    (directory / "model_calls.jsonl").write_text(
        json.dumps({**record, "event": "model_call_started"})
        + "\n"
        + json.dumps({**record, "event": "model_call_finished"})
        + "\n"
    )
    (directory / "request_usage.jsonl").write_text(
        json.dumps({"event": "request_started", "request_number": 1})
        + "\n"
        + json.dumps(
            {
                "event": "request_finished",
                "request_number": 1,
                "usage": {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9},
            }
        )
        + "\n"
    )
    study.complete_receipt(directory)
    return directory


def test_calibration_gate_checks_wiring_not_quality(frozen):
    output, manifest = frozen
    item = manifest["schedule"][0]
    save_fake_completed(output, item)
    check = study.wiring_check(output, manifest, item)
    assert check["passed"]
    assert check["fixed_D1_records_unchanged"]
    assert check["shared_context_exact_in_all_requests"]
    assert check["quality_findings_not_used_for_gate"]


def test_export_separates_arms_sources_and_calibration(frozen):
    output, manifest = frozen
    main = [item for item in manifest["schedule"] if item["phase"] == "main"]
    save_fake_completed(output, main[0])
    save_fake_completed(output, main[1], failed=True)
    # An in-flight directory must not break live exports or become usable output.
    (output / main[2]["attempt_path"]).mkdir(parents=True)
    summary = study.export(output)
    assert summary["produced_main"] == 1
    assert summary["scheduled_main"] == 60
    assert summary["statuses"]["main"]["D2_D3_failed"] == 1
    assert summary["statuses"]["main"]["running"] == 1
    assert summary["usage_including_calibration"]["generation_requests"] == 2
    tasks = study.read_json(output / "all_tasks.json")
    assert tasks[0]["arm"] == main[0]["arm"]
    assert tasks[0]["source_sha256"]
    evaluator = study.read_json(output / "evaluator_input.json")
    assert set(evaluator[0]) == {
        "task_id",
        "student_task",
        "learner_context",
        "learning_target",
    }
    assert "arm" not in json.dumps(evaluator)
    assert len(study.read_json(output / "all_attempts.json")) == 63
    assert "Illustrative API error" in (output / "tasks.html").read_text()


def test_config_rejects_changed_schedule_or_worker_budget():
    original = study.read_json(study.DEFAULT_CONFIG)
    for key, value in (("repeats", 5), ("request_cap", 801), ("max_workers", 4)):
        config = copy.deepcopy(original)
        config[key] = value
        with pytest.raises(ValueError):
            study.validate_config(config)
