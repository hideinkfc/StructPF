import json

import pytest
from pydantic import ValidationError

from src.evaluation.pf_rubric import (
    DIMENSIONS,
    judge_input,
    legacy_student_text,
    load_prompt,
    parse_rating,
    student_task_text,
)


def payload():
    return {
        **{key: {"evidence": "Concrete evidence.", "score": 2} for key in DIMENSIONS},
        "mathematical_concerns": [],
    }


def test_paper_anchors_and_no_target_distribution():
    prompt = load_prompt()
    assert prompt["version"] == "rahimi-table1/v1"
    for anchor in (
        "Includes two or more prerequisite concepts",
        "Moderate challenge with some failures",
        "Highly engaging, presented in meaningful narrative or real-world scenario",
        "Wide range of representations and solution methods",
        "Highly complex, requiring integration of multiple variables and representations",
    ):
        assert anchor in prompt["system"]
    assert "most exercises score 2" not in prompt["system"]


def test_student_input_excludes_teacher_claims_and_condition():
    text = student_task_text({
        "status": "ready", "title": "Compare", "body": "A: 2, 8", "question": "Explain.",
        "consolidation": "SECRET_SOLUTION", "version": "V2",
    })
    result = json.loads(judge_input(text, {
        "grade": "10", "topic": "SECRET_TARGET",
        "assumed_prior_knowledge": [{
            "resource": "Mean", "taught_as": "Calculate an arithmetic mean.",
            "student_move": "SECRET_MOVE", "falls_short_because": "SECRET_FAILURE",
        }],
    }))
    assert "SECRET" not in json.dumps(result)
    assert "V2" not in json.dumps(result)
    assert result["learner_context"]["assumed_prior_knowledge"][0]["resource"] == "Mean"
    assert result["student_task"] == "Compare\n\nA: 2, 8\n\nExplain."


def test_legacy_sections_exclude_topic_and_teacher_notes_but_keep_data():
    assert legacy_student_text({
        "TOPIC": "SECRET_TARGET", "NARRATIVE": "Context.", "DATA": "A: 2, 8",
        "TASK": "Explain.", "CONSOLIDATION NOTE": "SECRET_SOLUTION",
    }) == "Context.\n\nA: 2, 8\n\nExplain."


@pytest.mark.parametrize("task", [
    {"status": "blocked", "title": "A", "body": "B", "question": "C"},
    {"status": "ready", "title": "A", "body": "", "question": "C"},
])
def test_invalid_student_task_rejected(task):
    with pytest.raises(ValueError):
        student_task_text(task)


def test_missing_priors_remain_unknown():
    context = json.loads(judge_input("Task", {"grade": "7"}))["learner_context"]
    assert context["assumed_prior_knowledge"] is None


def test_invalid_prior_resources_rejected():
    with pytest.raises(ValueError):
        judge_input("Task", {"assumed_prior_knowledge": ["Mean"]})


def test_scores_validated_and_total_computed():
    result = parse_rating(json.dumps(payload()))
    assert result["status"] == "scored"
    assert result["scores"] == {**dict.fromkeys(DIMENSIONS, 2), "TOTAL": 10}
    assert result["rating"]["MR"]["evidence"] == "Concrete evidence."


@pytest.mark.parametrize("invalid", [0, 4, 9, "2", 2.5, True])
def test_invalid_score_rejected(invalid):
    data = payload()
    data["MR"]["score"] = invalid
    with pytest.raises(ValidationError):
        parse_rating(json.dumps(data))


def test_unknown_score_does_not_become_zero_or_partial_total():
    data = payload()
    data["SSC"] = {"evidence": "Prior instruction is unknown.", "score": None}
    result = parse_rating(json.dumps(data))
    assert result["status"] == "insufficient_evidence"
    assert result["scores"]["SSC"] is None
    assert result["scores"]["TOTAL"] is None


@pytest.mark.parametrize("change", ["missing", "empty_evidence", "total"])
def test_incomplete_or_extra_output_rejected(change):
    data = payload()
    if change == "missing":
        del data["OE"]
    elif change == "empty_evidence":
        data["OE"]["evidence"] = "  "
    else:
        data["TOTAL"] = 15
    with pytest.raises(ValidationError):
        parse_rating(json.dumps(data))


def test_malformed_output_rejected():
    with pytest.raises(ValidationError):
        parse_rating("not JSON")
