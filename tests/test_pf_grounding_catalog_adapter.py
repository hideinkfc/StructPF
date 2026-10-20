import json

import pytest

from scripts.adapt_pf_grounding_catalog import adapt_catalog
from src.evaluation.pf_evidence_audit import evidence_audit_input


def catalog():
    return {"tasks": [
        {
            "task_id": arm, "arm": arm, "case_id": "one", "repeat": 1,
            "task": {"title": "Ratios", "body": "Compare two quantities.", "question": "Why?"},
            "learning_target": "Proportional relationships",
            "learner_context": {"grade": 8, "recently_taught": ["Unit rates", "Fractions"]},
        } for arm in ("A", "B", "C")
    ]}


def test_frozen_history_reaches_the_actual_auditor_input_in_all_arms():
    original = catalog()
    with pytest.raises(ValueError, match="would be lost"):
        evidence_audit_input(original["tasks"][0])
    adapted, receipt = adapt_catalog(original)
    for before, after in zip(original["tasks"], adapted["tasks"]):
        sent = json.loads(evidence_audit_input(after))
        assert [resource["resource"] for resource in sent["learner_context"][
            "assumed_prior_knowledge"
        ]] == before["learner_context"]["recently_taught"]
        assert after["task"] == before["task"]
        assert "assumed_prior_knowledge" not in before["learner_context"]
        assert "arm" not in sent
    assert receipt["new_generation_requests"] == 0


def test_different_histories_between_matched_arms_are_rejected():
    original = catalog()
    original["tasks"][1]["learner_context"]["recently_taught"] = ["Algebra"]
    with pytest.raises(ValueError, match="varies"):
        adapt_catalog(original)


@pytest.mark.parametrize("history", [[], None, [""]])
def test_invalid_frozen_history_is_not_invented(history):
    original = catalog()
    original["tasks"][0]["learner_context"]["recently_taught"] = history
    with pytest.raises(ValueError, match="Missing frozen"):
        adapt_catalog(original)


def test_conflicting_existing_prior_records_are_not_overwritten():
    original = catalog()
    original["tasks"][0]["learner_context"]["assumed_prior_knowledge"] = [
        {"resource": "Calculus", "taught_as": "Calculus"}
    ]
    with pytest.raises(ValueError, match="disagrees"):
        adapt_catalog(original)
