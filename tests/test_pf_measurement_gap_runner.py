import json
import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts.report_pf_measurement_gap_study import review_pack
from scripts.run_pf_measurement_gap_study import (
    DEFAULT_BENCHMARK, DEFAULT_CONFIG, _stratified, catalog_source_provenance,
    control_performance, judge_one, prepare_run, read_catalog, run_prepared,
)
from scripts.reparse_pf_measurement_gap_study import reparse_record
from src.evaluation.pf_evidence_audit import ANCHORS, FINDINGS


@pytest.fixture
def artifact_directory():
    path = Path(".cache") / f"pf-measurement-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def entry():
    return {
        "task_id": "source-V1-001",
        "task": {"title": "Trip", "body": "6 km in 30 minutes", "question": "Compare speeds."},
        "learning_target": "Compare rates",
        "learner_context": {"grade": 7, "subject": "math", "assumed_prior_knowledge": []},
        "source_path": "task.json",
        "source_sha256": "a" * 64,
        "arm": "SECRET_ARM",
        "original_rating": {"scores": {"TOTAL": 15}},
    }


def manifest():
    return {
        "system_prompt": "Independent task audit",
        "settings": {
            "timeout_seconds": 240, "max_completion_tokens": 9000,
            "gpt54_reasoning_effort": "low", "gpt41_temperature": 0,
        },
    }


def unknown_response():
    finding = {"status": "unknown", "task_quotes": [], "reason": "Not enough evidence.", "counterevidence": ""}
    value = {name: dict(finding) for name in FINDINGS}
    value["distinct_mathematical_ideas"]["approaches"] = []
    value["mathematics"] = {
        **finding, "witnesses": [], "concerns": [],
    }
    value["original_high_anchor_support"] = {name: dict(finding) for name in ANCHORS}
    return json.dumps(value)


class FakeClient:
    def __init__(self, raw):
        self.raw = raw
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(
            id="saved-response-id", model="gpt-4.1",
            usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 20, "completion_tokens": 40}),
            choices=[SimpleNamespace(
                finish_reason="stop", message=SimpleNamespace(content=self.raw),
            )],
        )

    def with_options(self, **options):
        assert options["max_retries"] == 0
        return self


def test_strata_selection_is_seeded_and_has_no_score_dependency():
    import random
    records = [{"number": index, "task_id": str(index)} for index in range(1, 31)]
    a = _stratified(records, 2, random.Random(20261013))
    b = _stratified(records, 2, random.Random(20261013))
    assert a == b
    assert len(a) == 6
    assert [sum(lower <= item["number"] < lower + 10 for item in a) for lower in (1, 11, 21)] == [2, 2, 2]


def test_generic_catalog_array_and_object(artifact_directory):
    path = artifact_directory / "catalog.json"
    path.write_text(json.dumps([entry()]))
    assert read_catalog(path)[0]["task_id"] == entry()["task_id"]
    path.write_text(json.dumps({"tasks": [entry()]}))
    assert read_catalog(path)[0]["task_id"] == entry()["task_id"]


def test_generic_catalog_rejects_duplicate_ids(artifact_directory):
    path = artifact_directory / "catalog.json"
    path.write_text(json.dumps([entry(), entry()]))
    with pytest.raises(ValueError, match="unique"):
        read_catalog(path)


def test_failed_catalog_entry_without_task_remains_scheduled(artifact_directory):
    failed = entry()
    failed.pop("task")
    failed["status"] = "failed"
    path = artifact_directory / "catalog.json"
    path.write_text(json.dumps({"tasks": [failed]}))
    loaded = read_catalog(path)
    assert len(loaded) == 1
    assert loaded[0]["task"] is None
    assert loaded[0]["status"] == "failed"


def test_saves_response_usage_latency_and_only_blind_input(artifact_directory):
    client = FakeClient(unknown_response())
    result = judge_one(entry(), "gpt41", "blind-1", manifest(), artifact_directory, client, "gpt-4.1")
    assert result["status"] == "parsed"
    assert result["response_id"] == "saved-response-id"
    assert result["usage"]["prompt_tokens"] == 20
    assert result["latency_seconds"] >= 0
    assert "SECRET_ARM" not in result["user_input"]
    assert "source-V1-001" not in result["user_input"]
    assert len(result["input_sha256"]) == 64
    saved = json.loads((artifact_directory / "judgments/gpt41/blind-1.json").read_text())
    assert saved["raw_response"] == unknown_response()


def test_parse_failure_preserves_raw_and_never_retries(artifact_directory):
    client = FakeClient("{bad json")
    result = judge_one(entry(), "gpt54", "blind-2", manifest(), artifact_directory, client, "gpt-5.4")
    assert result["status"] == "parse_error"
    assert result["raw_response"] == "{bad json"
    assert len(client.requests) == 1
    assert client.requests[0]["reasoning_effort"] == "low"
    assert "temperature" not in client.requests[0]


def test_input_error_is_explicit_with_zero_calls(artifact_directory):
    invalid = entry()
    invalid["task"]["body"] = None
    client = FakeClient(unknown_response())
    result = judge_one(invalid, "gpt41", "blind-3", manifest(), artifact_directory, client, "gpt-4.1")
    assert result["status"] == "input_error"
    assert result["model_calls"] == 0
    assert client.requests == []


def test_absent_task_is_explicit_unknown_input_with_zero_calls(artifact_directory):
    invalid = entry()
    invalid["task"] = None
    client = FakeClient(unknown_response())
    result = judge_one(invalid, "gpt41", "blind-null", manifest(), artifact_directory, client, "gpt-4.1")
    assert result["status"] == "input_error"
    assert result["model_calls"] == 0
    assert client.requests == []


def test_missing_source_path_is_recorded_not_a_task_quality_failure(artifact_directory):
    records = catalog_source_provenance([entry()], artifact_directory)
    assert records[0]["status"] == "unknown_missing_source_path"


def test_review_pack_hides_source_arm_ratings_and_source_id(artifact_directory):
    value = entry()
    value["learner_context"]["arm"] = "HIDDEN_CONTEXT_ARM"
    review_pack(artifact_directory, [value])
    public = (artifact_directory / "review_pack_labels_hidden.html").read_text()
    assert "SECRET_ARM" not in public
    assert "HIDDEN_CONTEXT_ARM" not in public
    assert "source-V1-001" not in public
    assert "TOTAL" not in public
    assert "6 km in 30 minutes" in public
    assert "review-001" in public


def test_generic_catalog_end_to_end_retains_absent_task(monkeypatch, artifact_directory):
    valid, absent = entry(), entry()
    absent.update(task_id="absent", status="failed")
    absent.pop("task")
    catalog_path = artifact_directory / "catalog.json"
    catalog_path.write_text(json.dumps({"tasks": [valid, absent]}))
    output = artifact_directory / "frozen-run"
    prepare_run(output, DEFAULT_CONFIG, catalog_path, DEFAULT_BENCHMARK, ["gpt41", "gpt54"], 4)
    clients = {}

    def loader(judge):
        clients[judge] = FakeClient(unknown_response())
        return clients[judge], "gpt-4.1" if judge == "gpt41" else "gpt-5.4"

    monkeypatch.setattr("scripts.run_pf_measurement_gap_study.load_client", loader)
    summary = run_prepared(output, "all", 2)
    assert summary["catalog_tasks"] == 2
    assert summary["parsed_judgments"] == 2
    assert summary["error_status_counts"]["input_error"] == 2
    assert summary["execution"]["actual_model_requests"] == 2
    assert summary["rates"]["fixed_checklist"]["unknown"] == 2
    assert (output / "report.html").is_file()
    assert (output / "review_pack_labels_hidden.html").is_file()
    assert not (output / "calibration_summary.json").exists()
    assert len(clients["gpt41"].requests) == len(clients["gpt54"].requests) == 1


def test_reparse_preserves_raw_and_transport_without_loading_client(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Mechanical reparse must not load a client")

    monkeypatch.setattr("scripts.run_pf_measurement_gap_study.load_client", forbidden)
    value = json.loads(unknown_response())
    value["accessible_start"] = {
        "status": "supported", "task_quotes": [],
        "reason": "Missing quote in this field only.", "counterevidence": "",
    }
    raw = json.dumps(value)
    record = {
        "status": "parse_error", "raw_response": raw, "response_id": "immutable-id",
        "usage": {"prompt_tokens": 5}, "error": {"type": "ValidationError"},
    }
    result = reparse_record(record, entry())
    assert result["status"] == "partially_parsed"
    assert result["raw_response"] == raw
    assert result["response_id"] == "immutable-id"
    assert result["previous_parse_error"] == {"type": "ValidationError"}
    assert record["status"] == "parse_error"
    assert result["audit"]["target_relevance"]["status"] == "unknown"
    assert result["field_errors"]["accessible_start"]["raw_data"] == value["accessible_start"]


def test_control_invalid_field_is_not_a_substantive_unknown_match():
    value = json.loads(unknown_response())
    del value["accessible_start"]
    from src.evaluation.pf_evidence_audit import parse_evidence_audit
    result = {
        "task_id": entry()["task_id"], "judge": "gpt41",
        **parse_evidence_audit(json.dumps(value), "6 km in 30 minutes"),
    }
    control = {**entry(), "role": "development_control", "expected": {"accessible_start": ["unknown"]}}
    performance = control_performance([control], [result], ["gpt41", "gpt54"])
    row = performance["rows"][0]
    assert row["observed"] is None
    assert row["field_validation_error"] is not None
    assert row["matches"] is False
