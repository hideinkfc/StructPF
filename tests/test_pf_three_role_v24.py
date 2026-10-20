"""Mock tests for v2.4. Scripted replies only; no model calls."""

import json

import pytest

from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v24 as v24
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
SOLVER_INPUT = v22.role_input("solver", prepare_input(TASK, TARGET, CONTEXT))


def reply(payload):
    return LLMResponse(
        text=json.dumps(payload),
        model="mock",
        finish_reason="stop",
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )


def scripted(*items):
    queue = list(items)

    def chat(messages):
        item = queue.pop(0)
        return item if isinstance(item, LLMResponse) else reply(item)

    return chat


def final_body(**overrides):
    body = {
        "action": "final",
        "assumptions": ["Jasmine keeps 0.15 km per minute on Hady's bike."],
        "attempts": [
            {
                "idea": "Equal travel times",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "Equate the two times and solve: 3.4 km.",
            }
        ],
    }
    body.update(overrides)
    return body


def test_pinned_hashes_match_the_live_prompt_and_both_solver_systems():
    assert v24.fingerprint() == v24.FROZEN_PROMPT_SHA256
    assert v24.solver_system_sha256(toolkit=True) == v24.FROZEN_SOLVER_SYSTEM_SHA256["toolkit"]
    assert v24.solver_system_sha256(toolkit=False) == v24.FROZEN_SOLVER_SYSTEM_SHA256["no_toolkit"]


def test_final_schema_shown_to_the_model_requires_action_final():
    system = v24.solver_system(toolkit=True)
    segment = system[system.find("Final answer schema") : system.find("Calculator request schema")]
    assert '"const": "final"' in segment
    assert '"action"' in segment and '"required"' in segment


def test_the_final_schema_and_the_parser_use_the_same_model():
    schema = v24.FinalSolverReply.model_json_schema()
    assert set(schema["properties"]) == {"action", "assumptions", "attempts"}
    assert schema["additionalProperties"] is False


def test_a_reply_with_action_final_is_accepted_without_any_correction_flag():
    result = v24.run_solver_v24(SOLVER_INPUT, scripted(final_body()))
    assert result["status"] == "completed"
    assert "action_missing" not in result
    assert result["output"]["assumptions"] == final_body()["assumptions"]
    assert "action" not in result["output"]


def test_a_reply_without_action_is_now_invalid_not_silently_accepted():
    body = final_body()
    del body["action"]
    result = v24.run_solver_v24(SOLVER_INPUT, scripted(body))
    assert result["status"] == "invalid_response"
    assert result["output"] is None


def test_an_unknown_action_is_invalid():
    result = v24.run_solver_v24(SOLVER_INPUT, scripted(final_body(action="done")))
    assert result["status"] == "invalid_response"


def test_extra_keys_are_still_rejected():
    result = v24.run_solver_v24(SOLVER_INPUT, scripted(final_body(notes="extra")))
    assert result["status"] == "invalid_response"


def test_calculator_loop_still_feeds_each_result_back_before_continuing():
    calc = {
        "action": "calculate",
        "purpose": "Compute 3.4/0.15",
        "attempt": 0,
        "kind": "arithmetic",
        "values": {},
        "expressions": {"value": "3.4/0.15"},
    }
    seen = []

    def chat(messages):
        seen.append(messages)
        return reply(calc) if len(seen) == 1 else reply(final_body())

    result = v24.run_solver_v24(SOLVER_INPUT, chat)
    assert result["status"] == "completed"
    assert result["calculations"][0]["computed"]["value"] == "68/3"
    assert '"calculator_result"' in seen[1][-1]["content"]


def test_control_arm_still_rejects_toolkit_use():
    body = final_body()
    body["attempts"][0]["toolkit_used"] = ["guess_and_test"]
    result = v24.run_solver_v24(SOLVER_INPUT, scripted(body), toolkit=False)
    assert result["status"] == "invalid_response"


def test_api_failure_is_an_execution_state():
    from openai import OpenAIError

    def chat(_messages):
        raise OpenAIError("down")

    result = v24.run_solver_v24(SOLVER_INPUT, chat)
    assert result["status"] == "api_error"


def test_the_runtime_guard_rejects_an_edited_prompt(tmp_path, monkeypatch):
    changed = tmp_path / "changed.yaml"
    changed.write_bytes(v24.PROMPT_PATH.read_bytes() + b"\n# edited\n")
    monkeypatch.setattr(v24, "PROMPT_PATH", changed)
    with pytest.raises(ValueError, match="new instrument version"):
        v24.prompts()


def test_the_solver_input_stays_target_blind():
    with pytest.raises(ValueError, match="unallowlisted"):
        v24.run_solver_v24(SOLVER_INPUT | {"learning_target": TARGET}, scripted(final_body()))
