import json

import pytest
from openai import OpenAIError

from src.evaluation import pf_three_role as pf
from src.utils.llm_client import LLMResponse

TASK = "Invent a consistency measure for A=[4,5,6] and B=[0,5,10]."
CONTEXT = {
    "assumed_prior_knowledge": [
        {"resource": "Mean and arithmetic", "taught_as": "Add, subtract, divide and compute means."}
    ]
}
PREPARED = pf.prepare_input(TASK, "Variability", CONTEXT)


def chat(*outputs):
    replies = list(outputs)

    def call(messages):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return (
            reply
            if isinstance(reply, LLMResponse)
            else LLMResponse(text=json.dumps(reply), finish_reason="stop", model="test")
        )

    return call


def judgment(value="yes"):
    return {
        "verdict": value,
        "quotes": ["Invent a consistency measure"],
        "reason": "Worked evidence",
    }


def task_output(alignment="yes"):
    return {
        "action": "final",
        "alignment": judgment(alignment),
        "invention": judgment(),
        "validity": {"verdict": "yes", "reason": "Both lists are feasible"},
    }


@pytest.mark.parametrize("alignment", ["yes", "partly", "no", "unclear"])
def test_alignment_dependency(alignment):
    result = pf.parse_task(task_output(alignment), PREPARED)
    assert result["mathematical_validity"]["value"] == (
        "yes" if alignment == "yes" else "not_assessed"
    )
    assert result["room_for_invention"]["value"] == "yes"


def test_field_local_failures_do_not_discard_siblings():
    output = task_output()
    output["invention"]["quotes"] = ["invented quote"]
    result = pf.parse_task(output, PREPARED)
    assert result["room_for_invention"]["status"] == "invalid_response"
    assert result["target_alignment"]["value"] == result["mathematical_validity"]["value"] == "yes"


@pytest.mark.parametrize(
    "statuses,accessible,limits",
    [
        (["target_limit", "meets_demands"], "yes", "yes"),
        (["meets_demands"], "yes", "no"),
        (["unrelated_shortfall"], "yes", "no"),
        (["unresolved"], "yes", "unclear"),
        (["start_unresolved"], "unclear", "not_assessed"),
        (["not_supported"], "unclear", "not_assessed"),
        (["not_supported", "meets_demands"], "yes", "no"),
        (["start_unresolved", "meets_demands"], "yes", "unclear"),
    ],
)
def test_attempt_aggregation(statuses, accessible, limits):
    attempts = [{"idea": str(i), "work": "Concrete steps"} for i in range(len(statuses))]
    raw = {
        "attempts": [{"status": status, "reason": "Worked evidence"} for status in statuses],
        "inaccessible_because": None,
    }
    result = pf.parse_attempts(raw, attempts)
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == accessible
    assert result["measures"]["familiar_approach_limits"]["value"] == limits
    assert result["counts"]["attempts_produced"] == len(statuses)


def test_obstruction_needs_no_uncertain_start():
    raw = {
        "attempts": [{"status": "not_supported", "reason": "No start"}],
        "inaccessible_because": "All meaningful steps require unlisted integration",
    }
    assert (
        pf.parse_attempts(raw, [{}])["measures"]["prior_knowledge_accessibility"]["value"] == "no"
    )
    raw["attempts"][0]["status"] = "start_unresolved"
    assert (
        pf.parse_attempts(raw, [{}])["measures"]["prior_knowledge_accessibility"]["value"]
        == "unclear"
    )


def test_partial_invalid_attempt_retains_supported_sibling():
    raw = {
        "attempts": [{"status": "meets_demands", "reason": "Arithmetic works"}, {}],
        "inaccessible_because": None,
    }
    parsed = pf.parse_attempts(raw, [{}, {}])
    assert parsed["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert parsed["measures"]["familiar_approach_limits"]["value"] == "unclear"
    assert parsed["counts"]["supported_starts"] == 1


def test_solver_target_boundary():
    payload = pf.role_input("solver", PREPARED)
    assert "learning_target" not in payload
    assert "json" in pf.system("solver").lower()
    with pytest.raises(ValueError, match="unallowlisted"):
        pf.run_role("solver", payload | {"learning_target": "secret"}, chat({}))


def test_calculator_loop_returns_exact_results():
    check = {
        "action": "calculate",
        "checks": [
            {
                "purpose": "Mean",
                "values": {},
                "expressions": {"mean": "(4+5+6)/3"},
                "predicate": "mean == 5",
            }
        ],
    }
    result = pf.run_role(
        "task_judge", pf.role_input("task_judge", PREPARED), chat(check, task_output())
    )
    assert result["status"] == "completed"
    assert result["calculations"][0]["result"]["computed"]["mean"] == "5"
    assert len(result["calls"]) == 2


def test_truncation_is_not_educational_failure():
    result = pf.run_role(
        "solver",
        pf.role_input("solver", PREPARED),
        chat(LLMResponse(text='{"attempts":[]}', finish_reason="length")),
    )
    assert result["status"] == "truncated" and result["output"] is None


def test_budget_is_explicit():
    calc = {
        "action": "calculate",
        "checks": [
            {"purpose": "Check", "values": {}, "expressions": {"x": "1"}, "predicate": "x == 1"}
        ],
    }
    result = pf.run_role(
        "task_judge", pf.role_input("task_judge", PREPARED), chat(calc), max_calls=1
    )
    assert result["status"] == "budget_exhausted"


def test_api_failure_explicit():
    result = pf.run_role("solver", pf.role_input("solver", PREPARED), chat(OpenAIError("failed")))
    assert result["status"] == "api_error" and result["error"]["message"] == "failed"


def test_unknown_calculator_not_false():
    calc = {
        "action": "calculate",
        "checks": [
            {
                "purpose": "Missing",
                "values": {},
                "expressions": {"x": "missing"},
                "predicate": "x == 1",
            }
        ],
    }
    output = task_output()
    output["validity"] = {"verdict": "unclear", "reason": "Missing quantities"}
    result = pf.run_role("task_judge", pf.role_input("task_judge", PREPARED), chat(calc, output))
    assert result["calculations"][0]["result"]["status"] == "unknown"
    assert pf.parse_task(result["output"], PREPARED)["mathematical_validity"]["value"] == "unclear"


def test_missing_target_is_not_invented_and_skips_validity():
    inputs = pf.prepare_input(TASK, None, CONTEXT)
    assert inputs["learning_target"] is None
    result = pf.parse_task(task_output(), inputs)
    assert result["target_alignment"]["value"] == "unclear"
    assert result["mathematical_validity"]["value"] == "not_assessed"


def test_textual_history_adapter_preserves_exact_frozen_descriptions():
    original = {"assumed_prior_knowledge": ["Speed is distance divided by time"]}
    inputs = pf.prepare_input(TASK, "Variation", original)
    assert inputs["learner_context"]["assumed_prior_knowledge"] == [
        {
            "resource": "Speed is distance divided by time",
            "taught_as": "Speed is distance divided by time",
        }
    ]
    assert original["assumed_prior_knowledge"] == ["Speed is distance divided by time"]


def test_bounded_schema_completion_preserves_first_text_judgments():
    first = task_output()
    first["validity"] = None
    second = task_output()
    second["invention"] = judgment("no")
    result = pf.run_role("task_judge", pf.role_input("task_judge", PREPARED), chat(first, second))
    assert result["status"] == "completed"
    assert len(result["schema_repairs"]) == 1
    assert result["output"]["invention"] == first["invention"]
    assert result["output"]["validity"]["verdict"] == "yes"
    assert len(result["calls"]) == 2


def test_schema_completion_does_not_retry_no_or_partly_alignment():
    first = task_output("partly")
    first["validity"] = None
    result = pf.run_role("task_judge", pf.role_input("task_judge", PREPARED), chat(first))
    assert result["schema_repairs"] == [] and len(result["calls"]) == 1
