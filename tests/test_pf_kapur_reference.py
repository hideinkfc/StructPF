import json

import pytest

from scripts import report_pf_kapur_reference as report
from scripts import run_pf_kapur_reference as reference


def test_reference_schedule_is_solution_blind_and_has_fixed34_call_budget():
    config = json.loads(reference.CONFIG.read_text())
    rows = reference.schedule(config)
    assert len(rows) == 34 and len({row["id"] for row in rows}) == 34
    fresh = [row for row in rows if row["phase"] == "fresh"]
    assert sum(row["kind"] == "learner" for row in fresh) == 24
    assert sum(row["kind"] == "solver" for row in fresh) == 4
    assert sum(row["kind"] == "prediction" for row in fresh) == 2
    for row in fresh:
        text = row["prompt"]["user"]
        assert "codebook" not in text and "expected_student" not in text
        assert "Kapur" not in text
        if row["kind"] != "prediction":
            assert set(json.loads(text)) <= {"student_task", "learner_record"}


def test_calibration_keeps_invalid_outputs_without_substitution(tmp_path, monkeypatch):
    class Client:
        def with_options(self, **kwargs):
            return self

    monkeypatch.setattr(reference, "load_client", lambda _: (Client(), "test-model"))

    def fake(*args, **kwargs):
        assert kwargs["trace_path"].parent.is_dir()
        return {}, "invalid original response", None, None

    monkeypatch.setattr(reference.benchmark, "_call_json", fake)
    output = tmp_path / "reference"
    result = reference.run(output, "calibration")
    assert len(result["results"]) == 4
    assert all(item["status"] == "invalid_response" for item in result["results"])
    with pytest.raises(FileExistsError):
        reference.run(output, "calibration")


def test_reference_exact_math_and_evidence_do_not_force_human_failure():
    assert report.exact_check()["handover_metres"] == "3400"
    assert report.exact_check()["mira_minutes"] == report.exact_check()["leon_minutes"] == "76"
    packet = {
        "response_01": {
            "response_type": "attempt",
            "output": {
                "written_work": "Let x be the riding distance. Solving gives x = 3400.",
                "answer": "3400 m",
                "unfinished": False,
            },
            "raw_text": "",
        }
    }
    row = {
        "categories": ["algebra_single_variable"],
        "mentioned_only": [],
        "evidence": {"algebra_single_variable": ["Solving gives x = 3400."]},
        "unsuccessful_work": "no",
        "unsuccessful_evidence": [],
        "final_result": "correct",
        "rationale": "Correct algebra is not forced into failure.",
    }
    payload = {"provenance": "Illustrative software test", "responses": {"response_01": row}}
    assert report.validate_coding(payload, packet) == payload
    row["evidence"]["algebra_single_variable"] = ["Invented quote"]
    with pytest.raises(ValueError, match="does not match"):
        report.validate_coding(payload, packet)


def test_prediction_categories_are_not_scored_as_completed_attempts():
    packet = {
        "response_01": {
            "response_type": "prediction",
            "output": {
                "approaches": [
                    {
                        "description": "A learner may try ratios.",
                        "possible_limitation": "May not suffice.",
                    }
                ]
            },
            "raw_text": '{"description": "A learner may try ratios."}',
        }
    }
    payload = {
        "provenance": "Illustrative prediction",
        "responses": {
            "response_01": {
                "categories": ["ratios"],
                "mentioned_only": [],
                "evidence": {"ratios": ["A learner may try ratios."]},
                "unsuccessful_work": "unknown",
                "unsuccessful_evidence": [],
                "final_result": "not_applicable",
                "rationale": "A prediction is not an enactment.",
            }
        },
    }
    assert report.validate_coding(payload, packet) == payload
    payload["responses"]["response_01"]["final_result"] = "correct"
    with pytest.raises(ValueError, match="not a completed learner"):
        report.validate_coding(payload, packet)


def test_representation_coverage_is_not_algorithm_coverage():
    assert "diagram" in report.CATEGORY_LABELS
    assert "diagram" not in report.ALGORITHMS
    assert "hady_walks_more" not in report.ALGORITHMS
    assert "algebra_single_variable" in report.ALGORITHMS


def test_reference_gallery_preserves_count_meaning_and_escaped_output(tmp_path):
    config = json.loads(reference.CONFIG.read_text())
    reference.benchmark._write_json(tmp_path / "manifest.json", {"protocol": config})
    packet = {
        "response_01": {
            "response_type": "attempt",
            "output": {"written_work": "Trial <test>", "answer": "3400", "unfinished": False},
            "raw_text": "",
        }
    }
    key = {"response_01": "test"}
    groups = {
        "learner": {
            "responses": 24,
            "category/algebra_single_variable": 19,
            "category/trial_bruteforce": 6,
            "final/correct": 21,
            "final/unfinished": 2,
            "final/incorrect": 1,
        },
        "solver": {"responses": 4, "final/correct": 4},
        "prediction": {"responses": 2},
    }
    summary = {
        "groups": groups,
        "responses": {
            "test": {
                "kind": "learner",
                "final_result": "correct",
                "categories": ["trial_bruteforce"],
                "rationale": "Illustrative <coding>",
            }
        },
    }
    report.render(tmp_path, summary, packet, key)
    page = (tmp_path / "reference.html").read_text()
    assert "19/24 attempts" in page and "6/24 attempts" in page
    assert "Trial &lt;test&gt;" in page
    assert "not observed human-student frequencies" in page
