"""Mock tests for pf-three-role/v3.0. No model calls."""

import json

from src.evaluation import pf_three_role_v30 as v30
from src.utils.llm_client import LLMResponse

TASK = (
    "Jasmine rides at 0.15 km per minute and Hady rides at 0.2 km per minute. "
    "Hady lends Jasmine his bike after her tire goes flat. "
    "How far should Jasmine ride Hady\u2019s bike so that both arrive together?"
)
TARGET = "Coordinate travel times for simultaneous arrival."
CONTEXT = {
    "grade": 7,
    "subject": "mathematics",
    "assumed_prior_knowledge": [
        {"resource": "Speed", "taught_as": "Speed is distance divided by time."},
        {"resource": "Arithmetic", "taught_as": "Add, subtract, multiply and divide decimals."},
    ],
}


def reply(payload):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMResponse(
        text=text,
        model="mock",
        finish_reason="stop",
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )


def scripted(*items):
    queue = list(items)

    def chat(messages):
        return reply(queue.pop(0))

    return chat


def test_pinned_hashes_match_v30_prompt_and_systems():
    assert v30.fingerprint() == v30.FROZEN_PROMPT_SHA256
    assert v30.task_system_sha256() == v30.FROZEN_TASK_SYSTEM_SHA256
    assert v30.attempt_system_sha256() == v30.FROZEN_ATTEMPT_SYSTEM_SHA256
    assert v30.solver_system_sha256(toolkit=True) == v30.FROZEN_SOLVER_SYSTEM_SHA256["toolkit"]
    assert v30.solver_system_sha256(toolkit=False) == v30.FROZEN_SOLVER_SYSTEM_SHA256["no_toolkit"]
    assert "Direct prior-resource baseline" in v30.solver_system(toolkit=True)


def test_typography_tolerant_quote_matching_and_unmatched_recording():
    raw = {
        "verdict": "yes",
        "quotes": [
            "How far should Jasmine ride Hady's bike",
            "Coordinate travel times for simultaneous arrival.",
        ],
        "reason": "Matches target.",
    }
    row = v30._text_v30(raw, TASK)
    assert row["status"] == "assessed"
    assert row["value"] == "yes"
    assert row["evidence"]["quotes"] == ["How far should Jasmine ride Hady's bike"]
    assert row["evidence"]["unmatched_task_quotes"] == [
        "Coordinate travel times for simultaneous arrival."
    ]


def test_unstated_choice_maps_no_and_yes_to_unclear():
    raw = {
        "action": "final",
        "alignment": {
            "verdict": "yes",
            "quotes": ["How far should Jasmine ride Hady's bike"],
            "reason": "Aligned.",
        },
        "invention": {
            "verdict": "yes",
            "quotes": ["Hady lends Jasmine his bike"],
            "reason": "Open.",
        },
        "accessibility": {
            "verdict": "yes",
            "quotes": ["Jasmine rides at 0.15 km per minute"],
            "reason": "Accessible.",
        },
        "validity": {
            "verdict": "no",
            "assumptions": ["Depends on unstated rule."],
            "reading_dependence": "unstated_choice",
            "reason": "Ambiguous scope.",
        },
    }
    rows = v30.parse_task_v30(
        raw, {"student_task": TASK, "learning_target": TARGET, "learner_context": CONTEXT}
    )
    assert rows["mathematical_validity"]["value"] == "unclear"
    assert rows["mathematical_validity"]["evidence"]["raw_verdict"] == "no"


def test_solver_caps_attempts_at_four_and_downgrades_unchecked_trials():
    item = {
        "idea": "Approach",
        "principle": "Principle",
        "method_kind": "checked_trial",
        "trial_count": None,
        "toolkit_used": [],
        "work": "Work.",
    }
    parsed = v30.FinalSolverReply.model_validate(
        {"action": "final", "assumptions": [], "attempts": [item] * 6}
    )
    assert len(parsed.attempts) == 4
    assert parsed.attempts[0].method_kind == "unchecked_trial"


def test_quote_repair_in_run_judge_v30():
    bad = {
        "action": "final",
        "alignment": {
            "verdict": "yes",
            "quotes": ["Nonexistent quote from nowhere"],
            "reason": "Aligned.",
        },
        "invention": {
            "verdict": "yes",
            "quotes": ["Hady lends Jasmine his bike"],
            "reason": "Open.",
        },
        "accessibility": {
            "verdict": "yes",
            "quotes": ["Jasmine rides at 0.15 km per minute"],
            "reason": "Accessible.",
        },
        "validity": {
            "verdict": "yes",
            "assumptions": [],
            "reading_dependence": "none",
            "reason": "Valid.",
        },
    }
    good = {
        **bad,
        "alignment": {
            "verdict": "yes",
            "quotes": ["How far should Jasmine ride Hady's bike"],
            "reason": "Aligned.",
        },
    }
    payload = {"student_task": TASK, "learning_target": TARGET, "learner_context": CONTEXT}
    rec = v30.run_judge_v30("task_judge", payload, scripted(bad, good))
    assert rec["status"] == "completed"
    assert len(rec["schema_repairs"]) == 1
    rows = v30.parse_task_v30(rec["output"], payload)
    assert rows["target_alignment"]["value"] == "yes"
