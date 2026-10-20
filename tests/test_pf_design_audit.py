import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.evaluation.pf_design_audit import (
    PROMPT_PATH,
    design_audit_input,
    load_prompt,
    parse_design_audit,
)

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "experiments/configs/pf_design_audit_controls.json"


def finding(status="unknown"):
    return {"status": status, "evidence": f"Synthetic {status} evidence."}


def audit_payload(profile="unknown"):
    supported = profile == "positive"
    negative = profile == "negative"
    intentional_open = profile == "intentional_open"
    display_only = profile == "display_only"
    status = (
        "supported"
        if supported
        else "not_evidenced"
        if negative or display_only
        else "partial"
        if intentional_open
        else "unknown"
    )
    approaches = (
        [
            {
                "route": "Use total distance divided by total time.",
                "starting_resource": "Unit rates.",
                "mathematical_difference": (
                    "Combines total distance and total time before finding one rate."
                ),
            },
            {
                "route": (
                    "Find each segment's rate, then compare their time-weighted contributions."
                ),
                "starting_resource": "Unit rates and ratio reasoning.",
                "mathematical_difference": (
                    "Combines segment rates according to their durations rather than first "
                    "summing distance and time."
                ),
            },
        ]
        if supported
        else []
    )
    return {
        "target_relevance": finding(
            "supported" if supported or intentional_open or display_only else status
        ),
        "prior_resource_start": finding(
            "supported"
            if supported or negative or intentional_open or display_only
            else "unknown"
        ),
        "useful_contrast": finding(
            "supported"
            if supported
            else "not_evidenced"
            if negative or display_only
            else "partial"
            if intentional_open
            else "unknown"
        ),
        "approach_diversity": {
            **finding(status),
            "approaches": approaches,
        },
        "task_openness": finding(
            "supported"
            if intentional_open
            else "not_evidenced"
            if negative or display_only
            else status
        ),
        "mathematics_review": {
            "status": "unknown",
            "evidence": "Synthetic control does not request an external validation.",
            "concerns": [],
        },
    }


def test_prompt_is_exploratory_paper_informed_and_not_a_weighted_ranking():
    prompt = load_prompt()
    assert PROMPT_PATH.exists()
    assert prompt["version"] == "pf-design-audit/exploratory-v5"
    assert "Rahimi et al. (2025), Table 1, p. 2" in prompt["source"]
    assert "Kapur and Bielaczyc (2012), pp. 49-50" in prompt["source"]
    assert "Do not sum, average, rank, or" in prompt["system"]
    assert "weight findings" in prompt["system"]
    assert "different displays of the same calculation" in prompt["system"]
    assert "not predictions of student behavior" in prompt["system"]
    assert "Do not infer or favor a generation method" in prompt["system"]
    assert "not a proof" in prompt["system"]
    assert "prior judge's claim" in prompt["system"]
    assert "model_recomputed" in prompt["system"]
    assert "status checked" not in prompt["system"]
    assert "define a measure" in prompt["system"]
    archived_v1 = yaml.safe_load((PROMPT_PATH.parent / "pf_design_audit.yaml").read_text())
    assert archived_v1["version"] == "pf-design-audit/exploratory-v1"
    archived_v2 = yaml.safe_load((PROMPT_PATH.parent / "pf_design_audit_v2.yaml").read_text())
    assert archived_v2["version"] == "pf-design-audit/exploratory-v2"
    archived_v3 = yaml.safe_load((PROMPT_PATH.parent / "pf_design_audit_v3.yaml").read_text())
    assert archived_v3["version"] == "pf-design-audit/exploratory-v3"
    archived_v4 = yaml.safe_load((PROMPT_PATH.parent / "pf_design_audit_v4.yaml").read_text())
    assert archived_v4["version"] == "pf-design-audit/exploratory-v4"
    assert "PIPELINE" not in prompt["system"]
    assert "cosmetic freedom" in prompt["system"]
    assert "single determinate numerical answer is not" in prompt["system"]
    assert "speculate generically" in prompt["system"]
    assert "if assumed_prior_knowledge is absent or empty" in prompt["system"]
    assert "Missing history does not establish that" in prompt["system"]
    assert "learners were taught nothing" in prompt["system"]
    assert "concrete difference in mathematical idea" in prompt["system"]
    assert "same constant-ratio property" in prompt["system"]
    assert "use partial or unknown rather than supported" in prompt["system"]
    assert "Two distinct routes" in prompt["system"]
    assert "may both be mathematically valid" in prompt["system"]
    assert "multiple valid approaches as a defect" in prompt["system"]


def test_audit_input_uses_only_student_text_and_common_target_context():
    context = {
        "grade": 7,
        "subject": "mathematics",
        "assumed_prior_knowledge": [{"resource": "Unit rates", "taught_as": "Compute unit rates."}],
        "target_concept": "SECRET_TEACHER_TARGET",
        "condition": "PIPELINE",
        "teacher_claim": "SECRET_TEACHER_CLAIM",
    }
    result = json.loads(design_audit_input("Student task.", "Shared target.", context))
    rendered = json.dumps(result)
    assert result["learning_target"] == "Shared target."
    assert result["student_task"] == "Student task."
    assert result["learner_context"]["assumed_prior_knowledge"][0]["resource"] == "Unit rates"
    assert "SECRET" not in rendered
    assert "PIPELINE" not in rendered


@pytest.mark.parametrize(
    ("case_id", "profile"),
    [
        ("synthetic_positive_average_speed", "positive"),
        ("synthetic_negative_fair_share", "negative"),
        ("synthetic_unknown_percentages", "unknown"),
        ("synthetic_negative_consistency_procedure", "negative"),
        ("synthetic_intentional_open_consistency", "intentional_open"),
        ("synthetic_narrow_yes_no_display", "display_only"),
    ],
)
def test_synthetic_topic_diverse_controls_are_explicitly_not_human_rated(case_id, profile):
    controls = json.loads(CONTROLS.read_text(encoding="utf-8"))
    control = next(entry for entry in controls if entry["case_id"] == case_id)
    assert control["kind"] == "synthetic_control_not_human_rated"
    assert "Not a gold rating" in control["control_purpose"]
    user = design_audit_input(
        control["student_task"], control["learning_target"], control["learner_context"]
    )
    assert case_id not in user
    assert control["control_purpose"] not in user
    assert control["illustrative_signals"].get("prior_resource_start", "unspecified") in {
        "supported",
        "unknown",
        "unspecified",
    }
    parsed = parse_design_audit(json.dumps(audit_payload(profile)))
    if profile == "positive":
        assert control["illustrative_signals"]["task_openness"] == "partial"
    assert parsed["status"] == ("unknown" if profile == "unknown" else "scored")
    assert parsed["scope"] == "task_affordance_hypothesis"
    assert parsed["observed_student_behavior"] == "not_provided"
    assert parsed["mathematics_review_scope"] == (
        "Model task-text assessment only; not a deterministic proof or independent verification."
    )
    assert "TOTAL" not in parsed
    if profile == "unknown":
        assert parsed["audit"]["mathematics_review"]["status"] == "unknown"
        assert "assumed_prior_knowledge" not in control["learner_context"]
        assert control["illustrative_signals"]["prior_resource_start"] == "unknown"
        assert all(
            parsed["audit"][key]["status"] == "unknown"
            for key in (
                "target_relevance",
                "prior_resource_start",
                "useful_contrast",
                "approach_diversity",
                "task_openness",
            )
        )
    if profile == "intentional_open":
        assert parsed["audit"]["task_openness"]["status"] == "supported"
        assert parsed["audit"]["mathematics_review"]["status"] == "unknown"
        assert parsed["audit"]["mathematics_review"]["concerns"] == []
    if profile == "display_only":
        assert parsed["audit"]["approach_diversity"]["status"] == "not_evidenced"
        assert parsed["audit"]["task_openness"]["status"] == "not_evidenced"


def test_openness_does_not_require_multiple_numeric_answers():
    controls = json.loads(CONTROLS.read_text(encoding="utf-8"))
    average = next(
        item for item in controls if item["case_id"] == "synthetic_positive_average_speed"
    )
    narrow = next(
        item for item in controls if item["case_id"] == "synthetic_narrow_yes_no_display"
    )
    assert average["illustrative_signals"]["task_openness"] == "partial"
    assert "Choose a table, graph, or equation" in narrow["student_task"]
    assert "speculate about what might make using this pace unsafe" in narrow["student_task"]

    data = audit_payload("positive")
    data["task_openness"] = {
        "status": "partial",
        "evidence": (
            "The average is determinate, but learners choose how to compare the segment rates "
            "with whole-trip distance and time."
        ),
    }
    assert parse_design_audit(json.dumps(data))["audit"]["task_openness"]["status"] == "partial"


def test_negative_controls_cover_topics_beyond_average_speed():
    controls = json.loads(CONTROLS.read_text(encoding="utf-8"))
    negative_topics = {
        item["topic"]
        for item in controls
        if item["illustrative_signals"].get("approach_diversity") == "not_evidenced"
    }
    assert {"equal sharing", "spread of scores", "water use"} <= negative_topics
    assert "average speed" not in negative_topics


def test_supported_approach_diversity_requires_distinct_mathematical_routes():
    data = audit_payload("positive")
    data["approach_diversity"]["approaches"].pop()
    with pytest.raises(ValidationError, match="at least two routes"):
        parse_design_audit(json.dumps(data))
    data = audit_payload("positive")
    data["approach_diversity"]["approaches"][1]["mathematical_difference"] = data[
        "approach_diversity"
    ]["approaches"][0]["mathematical_difference"]
    with pytest.raises(ValidationError, match="distinct mathematical reasoning"):
        parse_design_audit(json.dumps(data))


def test_approach_diversity_can_remain_partial_when_routes_restate_one_test():
    data = audit_payload()
    data["approach_diversity"] = {
        "status": "partial",
        "evidence": (
            "Both proposed routes test a constant-ratio property; the task/context does not "
            "establish a different mathematical idea beyond division versus multiplication."
        ),
        "approaches": [
            {
                "route": "Compare output-to-input unit rates using division.",
                "starting_resource": "Unit rates.",
                "mathematical_difference": "Divide the output by the input.",
            },
            {
                "route": "Check equivalent scaling using multiplication.",
                "starting_resource": "Ratio reasoning.",
                "mathematical_difference": "Multiply both quantities by a common factor.",
            },
        ],
    }
    parsed = parse_design_audit(json.dumps(data))
    assert parsed["audit"]["approach_diversity"]["status"] == "partial"
    assert len(parsed["audit"]["approach_diversity"]["approaches"]) == 2

    data["approach_diversity"] = {
        "status": "unknown",
        "evidence": "The supplied task does not clarify whether the routes use different ideas.",
        "approaches": [],
    }
    assert (
        parse_design_audit(json.dumps(data))["audit"]["approach_diversity"]["status"] == "unknown"
    )


def test_math_concern_requires_concrete_evidence_and_unknown_is_preserved():
    data = audit_payload("negative")
    data["mathematics_review"]["status"] = "model_recomputed"
    data["mathematics_review"]["evidence"] = (
        "Set A's range is 8 - 2 = 6; Set B's range is 9 - 1 = 8."
    )
    parsed = parse_design_audit(json.dumps(data))
    assert parsed["audit"]["mathematics_review"]["status"] == "model_recomputed"
    assert "not a deterministic proof" in parsed["mathematics_review_scope"]
    data["mathematics_review"]["status"] = "concern"
    with pytest.raises(ValidationError, match="at least one concrete concern"):
        parse_design_audit(json.dumps(data))
    data = audit_payload()
    data["mathematics_review"] = {
        "status": "unknown",
        "evidence": "The source omits the units and comparison rule.",
        "concerns": [],
    }
    assert parse_design_audit(json.dumps(data))["status"] == "unknown"


def test_extra_total_and_invalid_status_are_rejected():
    data = audit_payload()
    data["TOTAL"] = 12
    with pytest.raises(ValidationError):
        parse_design_audit(json.dumps(data))
    data = audit_payload()
    data["task_openness"]["status"] = "excellent"
    with pytest.raises(ValidationError):
        parse_design_audit(json.dumps(data))
    data = audit_payload()
    data["mathematics_review"]["status"] = "checked"
    with pytest.raises(ValidationError):
        parse_design_audit(json.dumps(data))
