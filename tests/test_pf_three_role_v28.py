"""Mock tests for v2.8 (accessibility in the task judge as a gate). No model calls."""

import json

from src.evaluation import pf_three_role_v28 as v28
from src.evaluation.pf_three_role import prepare_input
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
PREPARED = prepare_input(TASK, TARGET, CONTEXT)


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


def approach(principle):
    return {
        "idea": f"Idea using {principle}",
        "principle": principle,
        "method_kind": "structured",
        "trial_count": None,
        "toolkit_used": [],
        "work": f"Work for {principle}; answer 3.4 km.",
    }


def final_body(*approaches):
    return {
        "action": "final",
        "assumptions": ["Jasmine keeps 0.15 km per minute on Hady's bike."],
        "attempts": list(approaches),
    }


def task_reply(*, accessibility="yes", alignment="yes"):
    return {
        "action": "final",
        "alignment": {
            "verdict": alignment,
            "quotes": ["How far should Jasmine ride Hady's bike"],
            "reason": "The task asks for the coordinated distance.",
        },
        "invention": {
            "verdict": "partly",
            "quotes": ["Hady lends Jasmine his bike"],
            "reason": "The bike swap is given.",
        },
        "accessibility": {
            "verdict": accessibility,
            "quotes": ["Jasmine rides at 0.15 km per minute"],
            "reason": "Speed and decimal operations allow a direct start."
            if accessibility == "yes"
            else "No listed skill allows a first step.",
        },
        "validity": (
            {
                "verdict": "yes",
                "assumptions": [],
                "reading_dependence": "none",
                "reason": "The numbers determine one answer.",
            }
            if alignment == "yes"
            else None
        ),
    }


def test_pinned_hashes_match_the_live_prompt_and_systems():
    assert v28.fingerprint() == v28.FROZEN_PROMPT_SHA256
    assert v28.task_system_sha256() == v28.FROZEN_TASK_SYSTEM_SHA256
    assert v28.attempt_system_sha256() == v28.FROZEN_ATTEMPT_SYSTEM_SHA256
    assert v28.task_system()
    assert v28.attempt_system()


def test_task_judge_schema_requires_action_final_and_accessibility():
    schema = v28.FinalTaskReply.model_json_schema()
    assert set(schema["required"]) >= {"action", "alignment", "invention", "accessibility"}
    assert schema["properties"]["action"].get("const") == "final"


def test_accessibility_gate_no_skips_solvers_and_attempt_judge():
    solver_called = []

    def never_called(messages):
        solver_called.append(messages)
        return reply(final_body(approach("p1")))

    result = v28.evaluate_v28(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={"luna": never_called, "gpt41": never_called},
        judge_chat=scripted(task_reply(accessibility="no")),
    )
    assert not solver_called
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "no"
    assert result["measures"]["familiar_approach_limits"]["value"] == "not_assessed"
    assert result["solver"]["status"] == "not_run_accessibility_gate"
    assert result["attempt_judge"] is None


def test_accessibility_gate_yes_runs_solvers_and_attempt_judge():
    def judge(messages):
        if '"attempts"' in messages[1]["content"]:
            return reply(
                {
                    "action": "final",
                    "attempts": [
                        {"status": "target_limit", "reason": "Stops before coordinating times."},
                        {"status": "meets_demands", "reason": "Reaches coordinated distance."},
                    ],
                }
            )
        return reply(task_reply(accessibility="yes"))

    result = v28.evaluate_v28(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={
            "luna": scripted(final_body(approach("equal-time equations"))),
            "gpt41": scripted(final_body(approach("trial distances"))),
        },
        judge_chat=judge,
    )
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["measures"]["familiar_approach_limits"]["value"] == "yes"
    assert result["approach_items_judged"] == 2


def test_missing_history_overrides_accessibility_to_unclear_and_skips_solvers():
    solver_called = []

    def never_called(messages):
        solver_called.append(messages)
        return reply(final_body(approach("p1")))

    result = v28.evaluate_v28(
        TASK,
        TARGET,
        {"grade": 7},
        solver_chats={"luna": never_called},
        judge_chat=scripted(task_reply(accessibility="yes")),
    )
    assert not solver_called
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "unclear"
    assert result["measures"]["familiar_approach_limits"]["value"] == "not_assessed"
