import json

import pytest

from scripts import report_pf_path_coverage_final as reporting
from scripts import run_pf_path_coverage_final as campaign
from src.evaluation.pf_path_coverage import path_counts, validate_path, weighted_path_rate


def path():
    return {
        "id": "range",
        "kind": "algorithm",
        "design_quote": "Compare range.",
        "operational_definition": "Actually subtract maximum and minimum.",
        "attempts": {
            "a1": {"status": "reached", "evidence": ["10 - 6 = 4"]},
            "a2": {"status": "unknown", "evidence": []},
        },
    }


def test_path_count_keeps_unknown_and_requires_actual_quote():
    attempts = {
        "a1": {"attempt": {"written_work": "10 - 6 = 4", "answer": "Tie"}},
        "a2": {"attempt": None, "unparsed_raw_text": "I would compare"},
    }
    payload = path()
    validate_path(payload, attempts, "Compare range.")
    assert path_counts(payload)["attempted"] == 2
    assert path_counts(payload)["unknown"] == 1
    payload["attempts"]["a1"]["evidence"] = ["Invented quote"]
    with pytest.raises(ValueError, match="does not match"):
        validate_path(payload, attempts, "Compare range.")


def test_hypothetical_class_mix_is_sensitivity_not_an_empirical_distribution():
    rows = path()["attempts"]
    profiles = {"a1": "full", "a2": "gap"}
    result = weighted_path_rate(rows, profiles, {"full": 0.25, "gap": 0.75})
    assert result["weighted_observed_reach"] == 0.25
    assert result["weighted_reach_if_unknowns_reach"] == 1
    assert "not fitted" in result["interpretation"]
    with pytest.raises(ValueError, match="sum to one"):
        weighted_path_rate(rows, profiles, {"full": 0.3, "gap": 0.3})
    with pytest.raises(ValueError, match="nonnegative numbers"):
        weighted_path_rate(rows, profiles, {"full": float("nan"), "gap": 0.75})


def test_coverage_feedback_has_same_source_design_and_no_extra_output_instructions(
    monkeypatch,
    tmp_path,
):
    task = {"title": "Task", "body": "Data", "question": "Explore"}
    monkeypatch.setattr(
        campaign,
        "source_input",
        lambda *_: (
            {},
            {"stages": {"D2_D3": {"task": task}}},
            {"goal": "Same original goal"},
        ),
    )
    config = {
        "design_instruction": "Restructure only when needed.",
        "coverage_instruction": "Not-observed does not prove inability.",
        "source_root": str(tmp_path),
    }
    campaign.benchmark._write_json(
        tmp_path / "assessment.json",
        {
            "tasks": {
                "speed/002/pipeline": {"impression": "Specific original task-only assessment"}
            },
        },
    )
    spec = {"family": "speed", "number": "002"}
    audit = {
        "tasks": {
            "one": {
                "source": "speed/002/pipeline/result.json",
                "denominator": 8,
                "diagnosis": "No construction observed.",
                "paths": [
                    {
                        "design_quote": "Try a guess.",
                        "kind": "algorithm",
                        "operational_definition": "Actual numerical trial.",
                        "reached_count": 0,
                        "not_observed_count": 8,
                        "unknown_count": 0,
                        "attempts": {
                            "a1": {
                                "status": "not_observed",
                                "evidence": [],
                                "reasons": "Not attempted.",
                            }
                        },
                    }
                ],
            }
        }
    }
    plain = json.loads(campaign.feedback_text(config, spec, "design_review", audit))
    extra = json.loads(campaign.feedback_text(config, spec, "coverage_feedback", audit))
    extra.pop("coverage_instruction")
    evidence = extra.pop("path_diagnosis")
    assert extra == plain
    assert plain["shared_task_only_review"]["impression"].startswith("Specific")
    assert evidence["paths"][0]["not_observed_count"] == 8


def test_codebook_freeze_records_hash_before_student_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    campaign.benchmark._write_json(
        tmp_path / "design_codebook_packet.json",
        {
            "task_01": {
                "design_brief": {
                    "approaches": [{"first_action": "Compare range."}],
                    "successful_route": "Invent a score.",
                }
            },
        },
    )
    campaign.benchmark._write_json(
        tmp_path / "path_codebook.json",
        {
            "provenance": "Illustrative prospective codebook",
            "tasks": {
                "task_01": {
                    "paths": [
                        {
                            "id": "range",
                            "design_quote": "Compare range.",
                            "operational_definition": "Subtract maximum and minimum.",
                            "kind": "algorithm",
                        }
                    ]
                }
            },
        },
    )
    campaign.benchmark._write_json(tmp_path / "evaluation_config.json", {"models": ["test"]})
    config = campaign.freeze_codebook(tmp_path)
    assert config["path_codebook"]["path"] == "path_codebook.json"
    assert len(config["path_codebook"]["sha256"]) == 64
    freeze = json.loads((tmp_path / "codebook_freeze.json").read_text())
    assert freeze["phase"] == "before_student_requests"


def test_prospective_paths_cannot_be_modified_to_fit_new_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    campaign.benchmark._write_json(
        tmp_path / "design_codebook_packet.json",
        {
            "task_01": {
                "design_brief": {
                    "approaches": [{"first_action": "Compare range."}],
                    "successful_route": "Invent a score.",
                }
            },
        },
    )
    campaign.benchmark._write_json(
        tmp_path / "path_codebook.json",
        {
            "tasks": {
                "task_01": {
                    "paths": [
                        {
                            "design_quote": "Compare range.",
                            "attempts": {"a1": {"status": "reached"}},
                        }
                    ]
                }
            },
        },
    )
    with pytest.raises(ValueError, match="cannot contain evaluated attempts"):
        campaign.freeze_codebook(tmp_path)


def test_final_report_keeps_other_model_series_separate():
    assert reporting.request_group({"profile_id": "ordinary_solver", "model": "gpt54"}) == "solver"
    assert reporting.request_group({"profile_id": "recent_prerequisites", "model": "gpt54"}) == (
        "learner_gpt54"
    )
    assert reporting.request_group({"profile_id": "one_prerequisite_gap", "model": "gpt41"}) == (
        "learner_gpt41"
    )


def test_reached_unsuccessful_path_is_not_an_unreached_path():
    row = path()
    row["attempts"]["a1"]["phase"] = "unsuccessful"
    counts = path_counts(row)
    assert counts["reached"] == counts["reached_unsuccessful"] == 1
    assert counts["unknown"] == 1


def test_final_panel_validation_preserves_missing_execution_as_unknown():
    packet = {
        "task_01": {
            "student_task": "Compare readings.",
            "paths": [{key: value for key, value in path().items() if key != "attempts"}],
            "attempts": {
                "a1": {"attempt": {"written_work": "10 - 6 = 4", "answer": "Tie"}},
                "a2": {"attempt": None, "unparsed_raw_text": "I would compare"},
            },
        }
    }
    coding = {
        "tasks": {
            "task_01": {
                "paths": {"range": {"attempts": path()["attempts"]}},
                "attempts": {
                    "a1": {
                        "mathematics": "supported",
                        "initial_access": "yes",
                        "evidence": ["10 - 6 = 4"],
                        "summary": "Uses range.",
                    },
                    "a2": {
                        "mathematics": "unknown",
                        "initial_access": "unknown",
                        "evidence": ["I would compare"],
                        "summary": "Cut off.",
                    },
                },
                "unexpected_paths": [],
                "diagnosis": "One usable range attempt.",
            }
        }
    }
    assert reporting.validate_panel_coding(coding, packet) == coding
    coding["tasks"]["task_01"]["paths"]["range"]["attempts"].pop("a2")
    with pytest.raises(ValueError, match="every scheduled"):
        reporting.validate_panel_coding(coding, packet)


def test_final_report_displays_original_model_dependence_without_claiming_fidelity(tmp_path):
    review = {
        "rationale": "Illustrative task review.",
        "mathematics": "supported",
        "target": "preserved",
        "accessible_start": "yes",
        "disclosure": "none",
        "consequential_choice": "yes",
        "input_clarity": "yes",
    }
    campaign.benchmark._write_json(
        tmp_path / "task_review_packet.json",
        {
            "task_01": {
                "student_task": {
                    "title": "Illustrative <task>",
                    "body": "Data",
                    "question": "Explore this.",
                }
            },
        },
    )
    result = {
        "actual_total_requests": 238,
        "maximum_requests": 294,
        "tasks": {
            "division_original": {
                "task_review": review,
                "diagnosis": "Illustrative source-quoted path diagnosis.",
                "label": "task_01",
                "paths": [
                    {
                        "id": "p03",
                        "kind": "algorithm",
                        "operational_definition": "Actually trim a claim.",
                        "groups": {
                            "learner_gpt41": {"attempted": 8, "reached": 0, "unknown": 0},
                            "learner_gpt54": {"attempted": 4, "reached": 4, "unknown": 0},
                        },
                    }
                ],
            }
        },
        "arms": {
            arm: {"design_requirements": 2}
            for arm in ("original", "design_review", "coverage_feedback")
        },
    }
    reporting.render(tmp_path, result)
    page = (tmp_path / "final_report.html").read_text()
    assert "0/8 attempts" in page and "4/4 attempts" in page
    assert "Global generator" in page and "promotion: no" in page
    assert "Neither count is a real student probability" in page
    assert "Illustrative &lt;task&gt;" in page
