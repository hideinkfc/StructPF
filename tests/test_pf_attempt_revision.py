import json

import pytest

from scripts import report_pf_attempt_revision as report
from scripts import run_pf_attempt_revision as revision
from scripts import run_pf_student_probe as students


def test_revision_conditions_share_everything_except_saved_attempts(tmp_path):
    config = json.loads(revision.CONFIG.read_text())
    requests = revision.prepare(config, tmp_path, "fresh")
    assert len(requests) == 12
    for case in config["cases"]:
        arms = {row["arm"]: row for row in requests if row["id"] == case["id"]}
        assert arms["ordinary_revision"]["system"] == arms["attempt_revision"]["system"]
        basic = json.loads(arms["ordinary_revision"]["user"])
        attempt = json.loads(arms["attempt_revision"]["user"])
        evidence = attempt.pop("learner_attempts")
        assert attempt == basic
        assert len(evidence) == 8
        assert all(
            set(row) == {"written_work", "answer", "execution_status", "unfinished"}
            for row in evidence
        )
        assert "quality_findings" not in basic


def test_revision_run_preserves_no_output_and_does_not_substitute_original(tmp_path, monkeypatch):
    class Client:
        def with_options(self, **kwargs):
            return self

    monkeypatch.setattr(revision, "load_client", lambda _: (Client(), "test-model"))
    calls = []

    def fake(*args, **kwargs):
        assert kwargs["trace_path"].parent.is_dir()
        calls.append(kwargs)
        return {}, "invalid original reply", None, None

    monkeypatch.setattr(revision.benchmark, "_call_json", fake)
    manifest = revision.run(tmp_path, "calibration")
    assert len(calls) == 4
    assert manifest["status"] == "completed"
    for row in manifest["results"]:
        result = json.loads((tmp_path / "calibration" / row["result_path"]).read_text())
        assert result["task"] is None
        assert result["raw_text"] == "invalid original reply"
    with pytest.raises(FileExistsError):
        revision.run(tmp_path, "calibration")


def test_evaluation_has_identical_frozen_panel_across_all_versions(tmp_path, monkeypatch):
    config = json.loads(revision.CONFIG.read_text())
    task, prior, case, _ = revision.inputs(config, config["cases"][0])
    local_config = tmp_path / "config.json"
    revision.save(local_config, config)
    monkeypatch.setattr(revision, "ROOT", tmp_path)
    monkeypatch.setattr(revision, "CONFIG", local_config)
    monkeypatch.setattr(revision, "inputs", lambda *_: (task, prior, case, []))
    output = tmp_path / "pilot"
    revision.save(output / "fresh/manifest.json", {"status": "completed"})
    for spec in config["cases"]:
        for arm in config["arms"][1:]:
            revision.save(
                output / "fresh" / spec["id"] / arm / "result.json",
                {
                    "task": task,
                    "status": "ready",
                },
            )
    evaluation = revision.prepare_evaluation(output)
    assert len(evaluation["tasks"]) == 18
    assert evaluation["budget"]["fresh_calls"] == 216
    assert evaluation["profiles"] == config["attempt_evaluation"]["profiles"]
    assert len(json.loads((output / "task_review_packet.json").read_text())) == 18
    for profile in config["attempt_evaluation"]["profiles"]:
        effective = dict(profile)
        if profile.get("omit_resources"):
            effective["omit_resource"] = profile["omit_resources"]["kapur_average_speed"]
        prompt = students.attempt_prompt(task, prior, effective)
        user = json.loads(prompt["user"])
        assert set(user) <= {"student_task", "learner_record"}
        assert "ordinary_revision" not in prompt["user"]


def test_predefined_design_requirements_keep_unknown_and_disclosure_separate():
    row = {
        "mathematics": "supported",
        "target": "preserved",
        "accessible_start": "yes",
        "disclosure": "none",
        "consequential_choice": "yes",
        "input_clarity": "yes",
    }
    assert report.qualified(row)
    assert not report.qualified({**row, "mathematics": "unknown"})
    assert not report.qualified({**row, "disclosure": "method"})
    with pytest.raises(ValueError, match="Unknown task rating"):
        report.qualified({**row, "target": "accepted"})


def test_attempt_coding_requires_actual_source_evidence_and_keeps_unknown():
    panels = {
        "task_01": {
            "student_task": "Illustrative task",
            "attempts": {
                "task_01_a01": {
                    "attempt": None,
                    "unparsed_raw_text": "I tried the range",
                    "execution_status": "invalid",
                }
            },
        }
    }
    coding = {
        "provenance": "Illustrative software test",
        "attempts": {
            "task_01_a01": {
                "approaches": ["range"],
                "mathematics": "unknown",
                "initial_access": "yes",
                "recognised_limit": "unknown",
                "unsupported_assumption": "unknown",
                "timing_interpretation": "not_applicable",
                "evidence": ["I tried the range"],
                "rationale": "Visible partial work only.",
            },
        },
    }
    assert report.validate_attempts(coding, panels) == coding
    coding["attempts"]["task_01_a01"]["evidence"] = ["Invented quote"]
    with pytest.raises(ValueError, match="does not match"):
        report.validate_attempts(coding, panels)


def test_comparison_page_shows_all_arms_and_escapes_task_text(tmp_path):
    packet = {}
    reviews = {}
    for number, arm in enumerate(("original", "ordinary_revision", "attempt_revision"), 1):
        label = f"task_{number:02d}"
        packet[label] = {
            "student_task": {
                "title": "Illustrative <task>",
                "body": "Data & assumptions",
                "question": "Explore.",
            }
        }
        reviews[arm] = {
            "label": label,
            "task_review": {"rationale": "Illustrative <review>"},
            "learner_attempts": {"method/range": 3},
        }
    revision.save(tmp_path / "task_review_packet.json", packet)
    summary = {
        "cases": {"illustrative": reviews},
        "arms": {arm: {"tasks": 6} for arm in reviews},
        "decision": "No <automatic> promotion.",
    }
    report.render(tmp_path, summary)
    page = (tmp_path / "comparison.html").read_text()
    assert page.count("<article>") == 3
    assert "Illustrative &lt;task&gt;" in page
    assert "Illustrative &lt;review&gt;" in page
    assert "range (3/8)" in page
    assert "Attempt-informed revision" in page
