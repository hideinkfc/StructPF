"""Mock tests for v2.9 (resource-sweep solver + v2.8 task-judge gate). No model calls."""

import json

from src.evaluation import pf_three_role_v29 as v29
from src.utils.llm_client import LLMResponse

TASK = (
    "Jasmine rides at 0.15 km per minute and Hady rides at 0.2 km per minute. "
    "Hady lends Jasmine his bike after her tire goes flat. "
    "How far should Jasmine ride Hady's bike so that both arrive together?"
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


def test_pinned_hashes_match_v29_prompt_and_both_solver_systems():
    assert v29.fingerprint() == v29.FROZEN_PROMPT_SHA256
    assert v29.solver_system_sha256(toolkit=True) == v29.FROZEN_SOLVER_SYSTEM_SHA256["toolkit"]
    assert v29.solver_system_sha256(toolkit=False) == v29.FROZEN_SOLVER_SYSTEM_SHA256["no_toolkit"]
    assert "Single-resource or partial-constraint approaches" in v29.solver_system(toolkit=True)


def test_checked_trial_without_trial_count_downgrades_to_unchecked_instead_of_crashing():
    raw = {
        "action": "final",
        "assumptions": ["Assume constant speeds."],
        "attempts": [
            {
                "idea": "Ratio split",
                "principle": "Biking-speed ratio split",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "Split 5 km in 4:3 ratio -> 20/7 km.",
            },
            {
                "idea": "Guess a value without stating trial count",
                "principle": "Guess and test",
                "method_kind": "checked_trial",
                "trial_count": None,
                "toolkit_used": ["guess_and_test"],
                "work": "Try 3 km.",
            },
        ],
    }
    parsed = v29.FinalSolverReply.model_validate(raw)
    assert parsed.attempts[0].method_kind == "structured"
    assert parsed.attempts[1].method_kind == "unchecked_trial"


def test_evaluate_v29_runs_sweep_solvers_and_attempt_judge():
    task_out = {
        "action": "final",
        "alignment": {
            "verdict": "yes",
            "quotes": ["How far should Jasmine ride Hady's bike"],
            "reason": "Addresses coordinated arrival.",
        },
        "invention": {
            "verdict": "yes",
            "quotes": ["Hady lends Jasmine his bike"],
            "reason": "Leaves coordination open.",
        },
        "accessibility": {
            "verdict": "yes",
            "quotes": ["Jasmine rides at 0.15 km per minute"],
            "reason": "Speed relation allows a start.",
        },
        "validity": {
            "verdict": "yes",
            "assumptions": ["Jasmine rides at 0.2 km/min on Hady's bike."],
            "reading_dependence": "stated_choice",
            "reason": "Consistent under stated assumption.",
        },
    }

    def judge(messages):
        if '"attempts"' in messages[1]["content"]:
            return reply(
                {
                    "action": "final",
                    "attempts": [
                        {"status": "target_limit", "reason": "Ratio split ignores walking speeds."},
                        {"status": "meets_demands", "reason": "Equal-time equation works."},
                        {"status": "target_limit", "reason": "50-50 split leaves unequal times."},
                    ],
                }
            )
        return reply(task_out)

    luna_reply = {
        "action": "final",
        "assumptions": ["Jasmine rides at 0.2 km/min on Hady's bike."],
        "attempts": [
            {
                "idea": "Split 5 km by biking ratio",
                "principle": "4:3 biking-speed ratio split",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "20/7 km; times do not match.",
            },
            {
                "idea": "Equal total times",
                "principle": "Equal total travel times",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "85/26 km.",
            },
        ],
    }
    gpt_reply = {
        "action": "final",
        "assumptions": ["Jasmine keeps 0.15 km/min."],
        "attempts": [
            {
                "idea": "Equal 50-50 distance split",
                "principle": "Equal distance split",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": ["special_cases"],
                "work": "2.5 km each; times differ.",
            }
        ],
    }
    res = v29.evaluate_v29(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={"luna": scripted(luna_reply), "gpt41": scripted(gpt_reply)},
        judge_chat=judge,
    )
    assert res["version"] == v29.VERSION
    assert res["approach_items_judged"] == 3
    assert res["measures"]["familiar_approach_limits"]["value"] == "yes"
    assert res["principles"]["distinct_union"] == 3
