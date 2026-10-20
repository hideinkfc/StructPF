import json

import pytest

from scripts import report_pf_student_diagnosis as diagnosis
from scripts import report_pf_student_probe as student_report
from scripts import run_pf_attempt_feedback as feedback
from scripts import run_pf_student_probe as probe
from src.evaluation.pf_attempt_feedback import FINDINGS, parse_panel_review, retain_panel_review


def panel():
    return {
        "student_task": "Invent a consistency measure. Values: 1, 2, 3.",
        "attempts": {
            "a1": {
                "attempt": {
                    "written_work": "The range is 3 - 1 = 2.",
                    "answer": "2", "unfinished": False,
                },
                "unparsed_raw_text": None,
            },
        },
    }


def review():
    return {
        "attempts": {
            "a1": {
                "approaches": ["range"], "mathematics_status": "supported",
                "named_advanced_procedure": False, "rationale": "Range is 2.",
            },
        },
        "findings": {
            name: {"status": "unknown", "evidence": [], "reason": "Not established."}
            for name in FINDINGS
        },
        "feedback": [],
        "summary": "No task defect established.",
    }


def test_exact_evidence_and_unknown_findings_are_preserved():
    payload = review()
    payload["findings"]["accessible_start"] = {
        "status": "observed",
        "evidence": [{"source": "a1", "quote": "The range is 3 - 1 = 2."}],
        "reason": "Initial mathematical work is visible.",
    }
    assert parse_panel_review(payload, panel()) == payload
    payload["findings"]["accessible_start"]["evidence"][0]["quote"] = "Invented quotation"
    with pytest.raises(ValueError, match="does not match"):
        parse_panel_review(payload, panel())


def test_task_revision_cannot_be_driven_by_simulator_slip():
    payload = review()
    payload["feedback"] = [{
        "attribution": "simulator_slip", "destination": "data",
        "evidence": [{"source": "a1", "quote": "range"}],
        "observation": "A calculation needs checking.", "suggestion": "Record only.",
    }]
    with pytest.raises(ValueError, match="cannot drive task revision"):
        parse_panel_review(payload, panel())
    payload["feedback"][0]["destination"] = "none"
    assert parse_panel_review(payload, panel()) == payload
    payload["feedback"][0].update(attribution="task_evidence", destination="design")
    with pytest.raises(ValueError, match="task-text evidence anchor"):
        parse_panel_review(payload, panel())


def test_all_attempts_must_be_reviewed_without_invented_categories():
    payload = review()
    payload["attempts"]["a1"]["approaches"] = ["new_format"]
    with pytest.raises(ValueError, match="approach coding"):
        parse_panel_review(payload, panel())
    payload = review()
    payload["attempts"] = {}
    with pytest.raises(ValueError, match="every attempted"):
        parse_panel_review(payload, panel())


def test_diagnosis_schedule_covers_all_eighteen_tasks_without_leaking_labels():
    config = json.loads(
        (probe.ROOT / "experiments/configs/pf_student_diagnosis_20261011.json").read_text()
    )
    requests = probe.build_requests(config)
    fresh = [item for item in requests if item["phase"] == "fresh"]
    assert len(requests) == 224
    assert len(fresh) == 216
    assert len({item["task_id"] for item in fresh}) == 18
    assert len({item["id"] for item in requests}) == 224
    for item in fresh:
        user = json.loads(item["prompt"]["user"])
        assert set(user) <= {"student_task", "learner_record"}
        assert item["task_id"] not in item["prompt"]["user"]
        assert "quality_findings" not in user


def test_panel_preparation_hides_profiles_models_and_source_methods(tmp_path, monkeypatch):
    requests = [
        {"id": "secret_model", "phase": "fresh", "task_id": "secret_source",
         "profile_id": "secret_profile", "prompt": {"user": json.dumps({
             "student_task": "Exercise", "learner_record": {"private": "secret_profile"},
         })}},
    ]
    records = {"secret_model": {
        "status": "invalid_response", "attempt": None, "raw_text": "Partial work retained.",
    }}
    monkeypatch.setattr(student_report, "load_results", lambda _: (
        {"requests": requests}, records,
    ))
    panels = feedback.prepare_panels(tmp_path, tmp_path / "panels")
    assert "secret" not in json.dumps(panels)
    assert panels["panel_01"]["attempts"]["a01"]["unparsed_raw_text"] == "Partial work retained."


def test_review_runner_creates_trace_directory_and_retains_rejected_review(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "prepare_panels", lambda *_: {
        f"panel_{index:02d}": panel() for index in range(1, 5)
    })
    probe_output = tmp_path / "input"
    probe_output.mkdir()
    (probe_output / "manifest.json").write_text("{}")

    class Client:
        def with_options(self, **kwargs):
            return self

    monkeypatch.setattr(feedback, "load_client", lambda _: (Client(), "test-model"))
    calls = []

    def call(*args, **kwargs):
        assert kwargs["trace_path"].parent.is_dir()
        calls.append(kwargs)
        return {}, "invalid original review", {"model": "test-model"}, None

    monkeypatch.setattr(feedback.benchmark, "_call_json", call)
    manifest = feedback.run(probe_output, tmp_path / "review", phase="calibration")
    assert len(calls) == 4
    assert manifest["status"] == "completed"
    assert all(row["status"] == "invalid_response" for row in manifest["results"])


def test_unmatched_quote_does_not_erase_usable_attempt_coding():
    payload = review()
    payload["findings"]["accessible_start"] = {
        "status": "observed", "evidence": [{"source": "a1", "quote": "invented text"}],
        "reason": "An unsupported quotation.",
    }
    result = retain_panel_review(payload, panel())
    assert result["attempts"] == payload["attempts"]
    assert result["findings"]["accessible_start"]["status"] == "unknown"
    assert result["unverified_evidence"]["accessible_start"] == (
        payload["findings"]["accessible_start"]
    )
    assert result["evidence_errors"]
    assert payload["findings"]["accessible_start"]["status"] == "observed"


def test_reader_agreement_reports_disagreements_not_a_new_ground_truth():
    first = review()["attempts"]
    second = review()["attempts"]
    second["a1"]["mathematics_status"] = "unknown"
    result = diagnosis.agreement(first, second)
    assert result["approaches"]["agreed"] == 1
    assert result["mathematics_status"]["agreed"] == 0
    assert result["mathematics_status"]["compared"] == 1
    assert len(result["mathematics_status"]["disagreements"]) == 1
    with pytest.raises(ValueError, match="same attempted responses"):
        diagnosis.agreement(first, {})


def test_task_feedback_requires_an_actual_attempt_as_well_as_task_text():
    payload = review()
    payload["feedback"] = [{
        "attribution": "task_evidence", "destination": "writer",
        "evidence": [{"source": "task", "quote": "Invent a consistency measure."}],
        "observation": "A task-only judgment.", "suggestion": "Consider clearer wording.",
    }]
    result = retain_panel_review(payload, panel())
    assert result["feedback"] == []
    assert "attempt evidence anchor" in result["evidence_errors"][0]
