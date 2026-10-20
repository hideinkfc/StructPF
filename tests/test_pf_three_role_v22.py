"""Mock tests for the v2.2 draft. Every model reply is scripted; no network calls are made."""

import hashlib
import json

import pytest
from openai import OpenAIError

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation.pf_three_role import prepare_input
from src.utils.llm_client import LLMResponse

# Synthetic development fixture, not a saved campaign task.
TASK = (
    "Jasmine rides at 0.15 km per minute and Hady rides at 0.2 km per minute. "
    "Hady lends Jasmine his bike after her tire goes flat. "
    "How far should Jasmine ride Hady's bike so that both arrive together?"
)
QUOTE = "How far should Jasmine ride Hady's bike so that both arrive together?"
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


def reply(payload, finish="stop"):
    return LLMResponse(
        text=json.dumps(payload),
        model="mock",
        finish_reason=finish,
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )


def scripted(*items):
    queue = list(items)
    seen = []

    def chat(messages):
        seen.append([dict(message) for message in messages])
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, LLMResponse) else reply(item)

    chat.seen = seen
    return chat


def solver_output(toolkit_on=True):
    return {
        "assumptions": ["Jasmine keeps her own speed of 0.15 km per minute on Hady's bike."],
        "attempts": [
            {
                "idea": "Equal travel times",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "Set Jasmine's time equal to Hady's time and solve for the distance.",
            },
            {
                "idea": "Try 3.4 km and check both times",
                "method_kind": "checked_trial",
                "trial_count": 3,
                "toolkit_used": ["guess_and_test"] if toolkit_on else [],
                "work": "3.4/0.15 + 1.6/0.03 = 76 and 3.4/0.05 + 1.6/0.2 = 76.",
            },
        ],
    }


def judgment_text(verdict="yes", quotes=(QUOTE,), reason="Worked evidence."):
    return {"verdict": verdict, "quotes": list(quotes), "reason": reason}


def task_output(dependence="none", validity_verdict="yes", assumptions=None):
    return {
        "action": "final",
        "alignment": judgment_text(),
        "invention": judgment_text(),
        "validity": {
            "verdict": validity_verdict,
            "assumptions": assumptions if assumptions is not None else [],
            "reading_dependence": dependence,
            "reason": "Consistent arithmetic under the stated reading.",
        },
    }


def audit_output(statuses):
    return {
        "action": "final",
        "attempts": [{"status": status, "reason": "Worked evidence."} for status in statuses],
        "inaccessible_because": None,
    }


def test_toolkit_is_fixed_and_task_neutral():
    ids = [item["id"] for item in v22.TOOLKIT]
    assert len(ids) == len(set(ids)) == 6
    blob = json.dumps(v22.TOOLKIT).lower()
    assert "bike" not in blob and "jasmine" not in blob and "target" not in blob
    expected = hashlib.sha256(json.dumps(v22.TOOLKIT, sort_keys=True).encode()).hexdigest()
    assert v22.TOOLKIT_SHA256 == expected


def test_toolkit_appears_only_in_the_solver_toolkit_arm():
    assert "Guess and test" in v22.system("solver", toolkit=True)
    assert "Guess and test" not in v22.system("solver", toolkit=False)
    for role in ("task_judge", "attempt_judge"):
        assert "Guess and test" not in v22.system(role)


def test_solver_payload_is_identical_across_arms_and_hides_target():
    payload = v22.role_input("solver", PREPARED)
    assert set(payload) == {"student_task", "learner_context"}
    assert TARGET not in json.dumps(payload)
    on, off = scripted(solver_output(True)), scripted(solver_output(False))
    v22.run_role("solver", payload, on, toolkit=True)
    v22.run_role("solver", payload, off, toolkit=False)
    assert on.seen[0][1]["content"] == off.seen[0][1]["content"]
    assert on.seen[0][0]["content"] != off.seen[0][0]["content"]


def test_control_arm_rejects_toolkit_use():
    result = v22.run_role(
        "solver", v22.role_input("solver", PREPARED), scripted(solver_output(True)), toolkit=False
    )
    assert result["status"] == "invalid_response"
    assert result["output"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda o: o["attempts"][1].update(method_kind="guessed"),
        lambda o: o["attempts"][1].update(trial_count=0),
        lambda o: o["attempts"][1].update(toolkit_used=["mind_reading"]),
        lambda o: o.update(attempts=o["attempts"] * 3),
    ],
)
def test_solver_schema_rejects_invalid_outputs(mutate):
    output = solver_output(True)
    mutate(output)
    result = v22.run_role("solver", v22.role_input("solver", PREPARED), scripted(output))
    assert result["status"] == "invalid_response"


def test_unchecked_trial_needs_no_count_but_is_still_valid_output():
    output = solver_output(True)
    output["attempts"][1] = {
        "idea": "Insert numbers",
        "method_kind": "unchecked_trial",
        "work": "Try 2, then 7, then 5.",
    }
    result = v22.run_role("solver", v22.role_input("solver", PREPARED), scripted(output))
    assert result["status"] == "completed"


def test_unstated_choice_cannot_support_yes_and_raw_verdict_is_kept():
    raw = task_output(dependence="unstated_choice", validity_verdict="yes")
    validity = v22.parse_task_v22(raw, PREPARED)["mathematical_validity"]
    assert validity["value"] == "unclear"
    assert validity["evidence"]["raw_verdict"] == "yes"
    assert validity["evidence"]["rule"] == "unstated_choice_cannot_support_yes"


def test_stated_choice_keeps_yes_when_the_assumption_is_named():
    raw = task_output(
        dependence="stated_choice",
        validity_verdict="yes",
        assumptions=["Jasmine keeps 0.15 km per minute on Hady's bike."],
    )
    assert v22.parse_task_v22(raw, PREPARED)["mathematical_validity"]["value"] == "yes"


def test_stated_choice_without_an_assumption_is_invalid():
    raw = task_output(dependence="stated_choice", validity_verdict="yes", assumptions=[])
    row = v22.parse_task_v22(raw, PREPARED)["mathematical_validity"]
    assert row["status"] == "invalid_response"


def test_no_dependence_yes_stays_yes():
    raw = task_output(dependence="none", validity_verdict="yes")
    assert v22.parse_task_v22(raw, PREPARED)["mathematical_validity"]["value"] == "yes"


def test_validity_is_not_assessed_unless_alignment_is_yes():
    raw = task_output(dependence="none", validity_verdict="yes")
    raw["alignment"] = judgment_text("partly", reason="Only one element is addressed.")
    row = v22.parse_task_v22(raw, PREPARED)["mathematical_validity"]
    assert row["value"] == "not_assessed"


def test_unchecked_trial_cannot_count_as_a_supported_start():
    attempts = [
        solver_output(True)["attempts"][0],
        {
            "idea": "Insert numbers",
            "method_kind": "unchecked_trial",
            "trial_count": None,
            "toolkit_used": [],
            "work": "Try 2 and 7.",
        },
    ]
    parsed = v22.parse_attempts_v22(audit_output(["meets_demands", "meets_demands"]), attempts)
    evidence = parsed["measures"]["prior_knowledge_accessibility"]["evidence"]["attempts"]
    assert evidence[1]["status"] == "not_supported"
    assert evidence[1]["raw_status"] == "meets_demands"
    assert parsed["measures"]["prior_knowledge_accessibility"]["value"] == "yes"


def test_checked_trial_status_is_kept_and_counts_are_separate():
    attempts = solver_output(True)["attempts"]
    parsed = v22.parse_attempts_v22(audit_output(["meets_demands", "target_limit"]), attempts)
    counts = parsed["counts"]
    assert counts["checked_trial_attempts"] == 1
    assert counts["unchecked_trial_attempts"] == 0
    assert counts["candidates_tested_in_checked_trials"] == 3
    assert parsed["measures"]["familiar_approach_limits"]["value"] == "yes"


def test_unstated_reading_end_to_end_is_unclear_not_yes():
    result = v22.evaluate_v22(
        TASK,
        TARGET,
        CONTEXT,
        solver_chat=scripted(solver_output(True)),
        judge_chat=scripted(
            task_output(dependence="unstated_choice", validity_verdict="yes"),
            audit_output(["meets_demands", "meets_demands"]),
        ),
        toolkit=True,
    )
    assert result["measures"]["mathematical_validity"]["value"] == "unclear"
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["measures"]["familiar_approach_limits"]["value"] == "no"
    assert result["arm"] == "toolkit"
    assert result["toolkit_sha256"] == v22.TOOLKIT_SHA256


def test_stated_reading_end_to_end_keeps_yes_and_control_arm_hides_toolkit():
    solver_chat = scripted(solver_output(False))
    result = v22.evaluate_v22(
        TASK,
        TARGET,
        CONTEXT,
        solver_chat=solver_chat,
        judge_chat=scripted(
            task_output(
                dependence="stated_choice",
                validity_verdict="yes",
                assumptions=["Jasmine keeps 0.15 km per minute on Hady's bike."],
            ),
            audit_output(["meets_demands", "meets_demands"]),
        ),
        toolkit=False,
    )
    assert result["measures"]["mathematical_validity"]["value"] == "yes"
    assert result["arm"] == "no_toolkit"
    assert "Guess and test" not in solver_chat.seen[0][0]["content"]


def test_calculator_loop_returns_exact_result_and_respects_budget():
    calc = {
        "action": "calculate",
        "checks": [
            {
                "purpose": "Mean",
                "values": {},
                "expressions": {"m": "(4+5+6)/3"},
                "predicate": "m == 5",
            }
        ],
    }
    result = v22.run_role(
        "task_judge", v22.role_input("task_judge", PREPARED), scripted(calc, task_output())
    )
    assert result["status"] == "completed"
    assert result["calculations"][0]["result"]["status"] == "holds"
    tight = v22.run_role(
        "task_judge", v22.role_input("task_judge", PREPARED), scripted(calc), max_calls=1
    )
    assert tight["status"] == "budget_exhausted"


def test_single_equals_predicate_is_not_accepted_as_a_holding_check():
    calc = {
        "action": "calculate",
        "checks": [
            {
                "purpose": "Mean",
                "values": {},
                "expressions": {"m": "(4+5+6)/3"},
                "predicate": "m = 5",
            }
        ],
    }
    result = v22.run_role(
        "task_judge",
        v22.role_input("task_judge", PREPARED),
        scripted(calc, task_output()),
        max_calls=2,
    )
    assert result["calculations"][0]["result"]["status"] != "holds"


def test_missing_validity_is_completed_once_and_first_text_findings_are_kept():
    first = task_output()
    first["validity"] = None
    first["invention"] = judgment_text("no", reason="First reply: routine execution remains.")
    second = task_output(validity_verdict="yes")
    second["invention"] = judgment_text("yes", reason="Second reply should be ignored.")
    result = v22.run_role(
        "task_judge", v22.role_input("task_judge", PREPARED), scripted(first, second)
    )
    assert result["status"] == "completed"
    assert len(result["schema_repairs"]) == 1
    assert result["output"]["invention"]["verdict"] == "no"
    assert result["output"]["validity"]["verdict"] == "yes"
    assert len(result["calls"]) == 2


def test_api_error_and_truncation_are_execution_states_not_verdicts():
    api = v22.run_role(
        "solver", v22.role_input("solver", PREPARED), scripted(OpenAIError("unavailable"))
    )
    assert api["status"] == "api_error"
    assert api["output"] is None
    cut = v22.run_role(
        "solver", v22.role_input("solver", PREPARED), scripted(reply(solver_output(True), "length"))
    )
    assert cut["status"] == "truncated"


def test_inputs_are_allowlisted_per_role():
    with pytest.raises(ValueError, match="unallowlisted"):
        v22.run_role(
            "solver",
            v22.role_input("solver", PREPARED) | {"learning_target": TARGET},
            scripted(solver_output(True)),
        )
    with pytest.raises(ValueError):
        v22.role_input("attempt_judge", PREPARED)


def test_prompt_is_frozen_with_pinned_hashes():
    spec = v22.prompts()
    assert spec["version"] == v22.VERSION == "pf-three-role/v2.2"
    assert spec["status"] == "frozen-mock-tested-not-run"
    assert v22.fingerprint() == v22.FROZEN_PROMPT_SHA256
    assert v22.TOOLKIT_SHA256 == v22.FROZEN_TOOLKIT_SHA256


def test_in_place_prompt_edit_is_rejected(tmp_path, monkeypatch):
    changed = tmp_path / "changed.yaml"
    changed.write_bytes(v22.PROMPT_PATH.read_bytes() + b"\n# edited\n")
    monkeypatch.setattr(v22, "PROMPT_PATH", changed)
    with pytest.raises(ValueError, match="new instrument version"):
        v22.prompts()


def test_toolkit_edit_is_rejected(monkeypatch):
    monkeypatch.setattr(v22, "TOOLKIT_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="toolkit changed"):
        v22.system("solver")
