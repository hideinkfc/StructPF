import json

import pytest

from src.evaluation.pf_evidence_audit import (
    ANCHORS,
    FINDINGS,
    aggregate_audits,
    check_witness,
    evidence_audit_input,
    exact_arithmetic,
    parse_evidence_audit,
)


def payload(status="supported"):
    finding = {
        "status": status, "task_quotes": ["6 km in 30 minutes"],
        "reason": "Concrete support.", "counterevidence": "",
    }
    value = {name: dict(finding) for name in FINDINGS}
    value["distinct_mathematical_ideas"] = {
        **finding, "status": "not_evidenced", "approaches": [],
    }
    value["mathematics"] = {
        "status": "model_recomputed", "task_quotes": ["6 km in 30 minutes"],
        "reason": "Segment rate.", "counterevidence": "", "concerns": [],
        "witnesses": [{
            "expression": "6 / 30", "claimed_value": "1/5",
            "task_quotes": ["6 km in 30 minutes"], "interpretation": "km per minute",
        }],
    }
    value["original_high_anchor_support"] = {name: dict(finding) for name in ANCHORS}
    return value


def entry():
    return {
        "task_id": "one",
        "task": {"title": "Trip", "body": "6 km in 30 minutes", "question": "Compare."},
        "learning_target": "Rates",
        "learner_context": {"grade": 7, "arm": "SECRET", "assumed_prior_knowledge": []},
        "arm": "SECRET", "original_rating": {"scores": {"TOTAL": 15, "MR": 3}},
    }


def parsed(judge, value=None):
    return {
        "task_id": "one", "judge": judge,
        **parse_evidence_audit(json.dumps(value or payload()), "6 km in 30 minutes"),
    }


def test_allowlist_hides_source_scores_and_design():
    data = json.loads(evidence_audit_input(entry()))
    assert set(data) == {"learning_target", "learner_context", "student_task"}
    assert "SECRET" not in str(data)
    assert "original_rating" not in str(data)


@pytest.mark.parametrize("expression", [
    "__import__('os').system('pwd')", "2 ** 100", "[1][0]", "True", "1e2", "2 // 1",
])
def test_arithmetic_rejects_code_and_unsupported_operations(expression):
    with pytest.raises(ValueError):
        exact_arithmetic(expression)


def test_exact_decimal_arithmetic_not_float_roundoff():
    assert str(exact_arithmetic("0.1 + 0.2")[0]) == "3/10"


def test_witness_grounds_numbers_and_flags_mismatch():
    witness = payload()["mathematics"]["witnesses"][0]
    assert check_witness(witness, "6 km in 30 minutes")["status"] == "verified_arithmetic"
    witness["claimed_value"] = "2"
    assert check_witness(witness, "6 km in 30 minutes")["status"] == "arithmetic_mismatch"
    witness["expression"] = "7 / 30"
    assert check_witness(witness, "6 km in 30 minutes")["status"] == "unknown"


def test_inexact_quote_cannot_be_agreed_issue():
    value = payload("not_evidenced")
    value["consequential_choice"]["task_quotes"] = ["invented quotation"]
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rates"]["consequential_choice"]["unknown"] == 1
    assert "consequential_choice" not in summary["rows"][0]["agreed_additional_concerns"]


def test_missing_and_partial_are_unknown_not_failure():
    value = payload("partial")
    summary = aggregate_audits([entry()], [parsed("a", value)], ["a", "b"])
    assert summary["missing_judgments"] == 1
    assert summary["rates"]["accessible_start"]["unknown"] == 1
    assert summary["rates"]["fixed_checklist"]["unknown"] == 1
    assert summary["rows"][0]["fixed_checklist_value"] is None
    assert summary["rows"][0]["availability"] == "audit_unavailable"
    assert summary["rows"][0]["availability_reason"] == "b: missing"


def test_distinct_ideas_separate_from_fixed_checklist_and_anchors():
    summary = aggregate_audits([entry()], [parsed("a"), parsed("b")], ["a", "b"])
    assert summary["rates"]["fixed_checklist"]["pass"] == 1
    assert summary["rows"][0]["fixed_checklist_value"] is True
    assert summary["rates"]["distinct_mathematical_ideas"]["concern"] == 1
    assert summary["rows"][0]["agreed_original_anchor_tensions"] == []
    assert summary["same_task_high_score_findings"]["additional_concern_without_anchor_tension"] == 1


def test_original_anchor_tension_requires_same_task_high_dimension():
    value = payload()
    value["original_high_anchor_support"]["MR"]["status"] = "not_evidenced"
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rows"][0]["agreed_original_anchor_tensions"] == ["MR"]


def test_math_concern_stays_unresolved_even_with_two_judges():
    value = payload()
    value["mathematics"]["status"] = "concern"
    value["mathematics"]["concerns"] = ["Task may contradict itself."]
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rates"]["mathematics"]["unknown"] == 1
    assert summary["rows"][0]["unresolved_mathematical_concern_judges"] == ["a", "b"]


def test_different_judge_failures_do_not_form_consensus_checklist_concern():
    a, b = payload(), payload()
    a["target_relevance"]["status"] = "not_evidenced"
    b["preserved_discovery"]["status"] = "not_evidenced"
    summary = aggregate_audits([entry()], [parsed("a", a), parsed("b", b)], ["a", "b"])
    assert summary["rates"]["fixed_checklist"]["unknown"] == 1
    assert summary["rows"][0]["fixed_checklist_value"] is None


def test_schema_rejects_representation_only_supported_idea_diversity():
    value = payload()
    value["distinct_mathematical_ideas"]["status"] = "supported"
    result = parse_evidence_audit(json.dumps(value), "6 km in 30 minutes")
    assert result["status"] == "partially_parsed"
    assert result["audit"]["distinct_mathematical_ideas"]["status"] == "unknown"
    assert "two explicit idea routes" in str(result["field_errors"])
    assert result["audit"]["target_relevance"]["status"] == "supported"


def test_partial_parse_preserves_valid_fields_and_invalid_raw_data():
    value = payload()
    value["accessible_start"]["task_quotes"] = []
    result = parsed("a", value)
    assert result["status"] == "partially_parsed"
    assert result["audit"]["target_relevance"]["status"] == "supported"
    assert result["audit"]["accessible_start"]["status"] == "unknown"
    assert result["field_errors"]["accessible_start"]["raw_data"] == value["accessible_start"]
    summary = aggregate_audits([entry()], [result, parsed("b", value)], ["a", "b"])
    assert summary["rates"]["target_relevance"]["pass"] == 1
    assert summary["rates"]["accessible_start"]["unknown"] == 1
    assert summary["rows"][0]["fixed_checklist_value"] is None
    assert summary["rows"][0]["availability"] == "audit_unavailable"


def test_strict_structured_math_concerns_are_preserved_not_stringified():
    value = payload()
    value["mathematics"]["status"] = "concern"
    concern = {
        "expression": "6 / 30", "claimed_value": "1/5",
        "task_quotes": ["6 km in 30 minutes"], "interpretation": "A specific concern.",
    }
    value["mathematics"]["concerns"] = [concern]
    result = parsed("a", value)
    assert result["status"] == "parsed"
    assert result["audit"]["mathematics"]["concerns"] == [concern]
    assert result["mathematical_concern_witness_checks"][0]["status"] == "verified_arithmetic"


@pytest.mark.parametrize("concern", [
    {"expression": "6 / 30", "claimed_value": "1/5", "task_quotes": []},
    {"unrelated": "cannot stringify this into evidence"},
    7,
])
def test_invalid_concern_object_affects_only_math_field(concern):
    value = payload()
    value["mathematics"]["concerns"] = [concern]
    result = parsed("a", value)
    assert result["status"] == "partially_parsed"
    assert result["audit"]["mathematics"]["status"] == "unknown"
    assert result["audit"]["target_relevance"]["status"] == "supported"
    assert result["field_errors"]["mathematics"]["raw_data"]["concerns"] == [concern]


def test_model_recomputed_with_concern_does_not_pass_mathematics():
    value = payload()
    value["mathematics"]["concerns"] = ["A recomputed relationship does not resolve this concern."]
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rates"]["mathematics"]["unknown"] == 1
    assert summary["rows"][0]["unresolved_mathematical_concern_judges"] == ["a", "b"]


def test_invalid_noncore_field_does_not_make_valid_checklist_unavailable():
    value = payload()
    value["distinct_mathematical_ideas"]["status"] = "supported"
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rows"][0]["fixed_checklist_value"] is True
    assert summary["rows"][0]["availability"] == "available"
    assert summary["rows"][0]["property_availability"]["distinct_mathematical_ideas"] == "audit_unavailable"
    assert summary["rates"]["distinct_mathematical_ideas"]["unknown_due_to_unavailability"] == 1


def test_missing_anchor_is_local_and_raw_status_is_unavailable_not_unknown():
    value = payload()
    del value["original_high_anchor_support"]["MR"]
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rows"][0]["judge_statuses"]["anchor_MR"] == [None, None]
    assert summary["rows"][0]["consensus"]["anchor_APK"] == "pass"
    assert summary["agreement"]["anchor_MR"]["raw_status_pair_denominator"] == 0


def test_no_valid_fields_is_not_success():
    result = parse_evidence_audit("{}", "6 km in 30 minutes")
    assert result["status"] == "field_validation_error"
    assert result["validated_fields"] == []
    assert result["field_errors"]["mathematics"]["raw_data"] is None


def test_mathematics_dependent_specification_concern_stays_unresolved():
    value = payload()
    value["task_specification"]["status"] = "not_evidenced"
    value["mathematics"]["status"] = "concern"
    value["mathematics"]["concerns"] = ["Possible inconsistent mathematical requirement."]
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rates"]["task_specification"]["unknown"] == 1
    assert "task_specification" not in summary["rows"][0]["agreed_additional_concerns"]


def test_arithmetic_witness_error_does_not_erase_separate_specification_support():
    value = payload()
    value["mathematics"]["witnesses"][0]["claimed_value"] = "2"
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rates"]["mathematics"]["unknown"] == 1
    assert summary["rates"]["task_specification"]["pass"] == 1


def test_aggregation_rejects_unmatched_results():
    with pytest.raises(ValueError, match="does not belong"):
        aggregate_audits([entry()], [parsed("other-judge")], ["a", "b"])


def test_agreed_concern_makes_composite_false_even_with_unknown_components():
    value = payload("partial")
    value["consequential_choice"]["status"] = "not_evidenced"
    summary = aggregate_audits([entry()], [parsed("a", value), parsed("b", value)], ["a", "b"])
    assert summary["rows"][0]["fixed_checklist_value"] is False
    assert summary["rows"][0]["availability"] == "available"
    assert summary["rows"][0]["consensus_values"]["accessible_start"] is None


def test_substantive_unknown_is_separate_from_unavailable_task():
    valid, missing = entry(), entry()
    missing.update(task_id="missing", task=None)
    summary = aggregate_audits(
        [valid, missing], [parsed("a", payload("partial")), parsed("b", payload("partial"))],
        ["a", "b"],
    )
    assert summary["availability_counts"] == {
        "available": 1, "task_unavailable": 1, "audit_unavailable": 0,
    }
    assert summary["delivered_denominators"]["student_tasks_supplied"] == 1
    assert summary["rates"]["fixed_checklist"]["unknown_due_to_unavailability"] == 1
    assert summary["rates"]["fixed_checklist"]["substantive_unknown_or_disputed_available"] == 1
