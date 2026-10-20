import json
import re

import pytest
from pydantic import ValidationError

from src.evaluation import pf_rubric, pf_rubric_v2


def test_v2_retains_the_five_v1_anchors_and_discloses_adaptation():
    v1 = pf_rubric.load_prompt()
    v2 = pf_rubric_v2.load_prompt()
    assert v2["version"] == "rahimi-table1/v2"
    assert "explicitly adapted operational interpretation" in v2["source"]
    assert "not represented as the paper's exact wording" in v2["source"]

    def anchors(prompt):
        return [
            line.strip()
            for line in prompt["system"].splitlines()
            if line.strip().startswith(("1 (Low):", "2 (Moderate):", "3 (High):"))
        ]

    assert anchors(v2) == anchors(v1)
    assert len(anchors(v2)) == 15


def test_v2_guidance_is_method_blind_and_separates_route_from_format():
    system = re.sub(r"\s+", " ", pf_rubric_v2.load_prompt()["system"])
    for phrase in (
        "Do not infer or favor a generation method",
        "different display formats",
        "mathematical idea,",
        "Meaningful openness includes choices",
        "Keep mathematical concerns separate",
    ):
        assert phrase in system
    assert not any(label in system for label in ("V1", "V2", "V3", "PIPELINE"))


def test_v2_blind_input_includes_one_fixed_target_and_prior_context():
    user = pf_rubric_v2.judge_input(
        "Compare the two groups.",
        {
            "grade": 7,
            "subject": "mathematics",
            "jurisdiction": "USA",
            "target_concept": "SECRET_TARGET",
            "condition": "PIPELINE",
            "teacher_notes": "SECRET_TEACHER",
            "assumed_prior_knowledge": [
                {
                    "resource": "Unit rates",
                    "taught_as": "Compute rates.",
                    "student_move": "SECRET_MOVE",
                    "falls_short_because": "SECRET_ANALYSIS",
                }
            ],
        },
        "Recognize proportional relationships.",
    )
    payload = json.loads(user)
    assert payload["learner_context"] == {
        "grade": 7,
        "subject": "mathematics",
        "jurisdiction": "USA",
        "assumed_prior_knowledge": [
            {
                "resource": "Unit rates",
                "taught_as": "Compute rates.",
            }
        ],
        "learning_target": "Recognize proportional relationships.",
    }
    assert payload["student_task"] == "Compare the two groups."
    assert "SECRET" not in user
    assert "PIPELINE" not in user


def test_v2_reuses_same_strict_five_dimension_schema():
    raw = json.dumps(
        {
            **{key: {"evidence": "Task evidence.", "score": 2} for key in pf_rubric_v2.DIMENSIONS},
            "mathematical_concerns": [],
        }
    )
    assert pf_rubric_v2.parse_rating(raw)["scores"]["TOTAL"] == 10
    with pytest.raises(ValidationError):
        pf_rubric_v2.parse_rating(raw.replace('"score": 2', '"score": 4', 1))


def test_v2_rejects_missing_target_and_invalid_prior_context():
    with pytest.raises(ValueError, match="target_concept"):
        pf_rubric_v2.judge_input("Task", {"grade": 7}, "")
    with pytest.raises(ValueError, match="prior-knowledge resource"):
        pf_rubric_v2.judge_input("Task", {"assumed_prior_knowledge": ["invalid"]}, "Target")
