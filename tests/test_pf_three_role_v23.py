"""Mock tests for v2.3 solver calculator loop. Scripted replies only; no model calls."""

import hashlib
import json

import pytest
from openai import OpenAIError

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v23 as v23
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
SOLVER_INPUT = v22.role_input("solver", PREPARED)


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


def arithmetic(expression, attempt=0, purpose="Compute a step"):
    return {
        "action": "calculate",
        "purpose": purpose,
        "attempt": attempt,
        "kind": "arithmetic",
        "values": {},
        "expressions": {"value": expression},
    }


def candidate(value, attempt=0, predicate="gap == 0"):
    return {
        "action": "calculate",
        "purpose": f"Test candidate {value}",
        "attempt": attempt,
        "kind": "candidate_check",
        "values": {"x": value},
        "expressions": {
            "gap": "x/0.15 + (5-x)/0.03 - (x/0.05 + (5-x)/0.2)",
        },
        "predicate": predicate,
    }


def final(attempts=None, assumptions=None):
    if attempts is None:
        attempts = [
            {
                "idea": "Equal travel times",
                "method_kind": "structured",
                "trial_count": None,
                "toolkit_used": [],
                "work": "Equate the two times and solve for the distance: 3.4 km.",
            }
        ]
    return {
        "action": "final",
        "assumptions": assumptions
        if assumptions is not None
        else ["Jasmine keeps 0.15 km per minute on Hady's bike."],
        "attempts": attempts,
    }


def test_frozen_ceilings_and_hashes():
    assert v23.CANDIDATE_CAP == 10
    assert v23.MAX_SOLVER_CALLS == 40
    assert v23.MAX_SOLVER_CHECKS == 120
    assert v23.fingerprint() == v23.FROZEN_PROMPT_SHA256
    assert v23.prompts()["version"] == v23.VERSION == "pf-three-role/v2.3"


def test_v22_judges_and_prompt_are_untouched():
    assert v22.fingerprint() == v22.FROZEN_PROMPT_SHA256
    assert v22.TOOLKIT_SHA256 == v22.FROZEN_TOOLKIT_SHA256
    assert hashlib.sha256(v22.PROMPT_PATH.read_bytes()).hexdigest() == v22.FROZEN_PROMPT_SHA256


def test_solver_input_stays_target_blind():
    assert set(SOLVER_INPUT) == {"student_task", "learner_context"}
    assert TARGET not in json.dumps(SOLVER_INPUT)
    with pytest.raises(ValueError, match="unallowlisted"):
        v23.run_solver_v23(SOLVER_INPUT | {"learning_target": TARGET}, scripted(final()))


def test_calculator_is_iterative_and_each_result_reaches_the_solver():
    chat = scripted(arithmetic("3.4/0.15"), arithmetic("22.6666 + 53.3333"), final())
    result = v23.run_solver_v23(SOLVER_INPUT, chat)
    assert result["status"] == "completed"
    assert len(result["calls"]) == 3
    assert len(result["calculations"]) == 2
    # The second request must see the result of the first step before it continues.
    second_prompt = chat.seen[1][-1]["content"]
    assert '"calculator_result"' in second_prompt
    assert '"computed"' in second_prompt


def test_arithmetic_result_is_exact_not_a_float_guess():
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(arithmetic("3.4/0.15"), final()))
    assert result["calculations"][0]["status"] == "holds"
    assert result["calculations"][0]["computed"]["value"] == "68/3"


def test_candidate_checks_are_capped_at_ten_per_attempt():
    script = [candidate(round(3 + i / 10, 1)) for i in range(10)] + [candidate(4.5)] + [final()]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(*script), max_calls=40)
    accepted = [c for c in result["calculations"] if not c["refused"]]
    refused = [c for c in result["calculations"] if c["refused"]]
    assert len(accepted) == 10
    assert len(refused) == 1
    assert refused[0]["status"] == "refused"
    assert "candidate limit" in refused[0]["reason"]
    assert result["candidate_checks_by_attempt"] == {"0": 10}


def test_candidate_cap_is_per_attempt_not_global():
    script = [candidate(3.4, attempt=0)] * 10 + [candidate(3.4, attempt=1)] + [final()]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(*script), max_calls=40)
    assert not any(c["refused"] for c in result["calculations"][-1:])
    assert result["candidate_checks_by_attempt"] == {"0": 10, "1": 1}


def test_arithmetic_steps_are_not_limited_by_the_candidate_cap():
    script = [arithmetic(f"{i}+1") for i in range(15)] + [final()]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(*script), max_calls=40)
    assert not any(c["refused"] for c in result["calculations"])
    assert len(result["calculations"]) == 15


def test_candidate_lists_are_refused_as_search():
    bad = candidate(3.4)
    bad["values"] = {"x": [3.0, 3.1, 3.2, 3.3, 3.4]}
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(bad, final()), max_calls=3)
    assert result["calculations"][0]["refused"] is True
    assert "candidate lists" in result["calculations"][0]["reason"]
    assert result["candidate_checks_by_attempt"] == {}


def test_candidate_check_without_predicate_is_invalid():
    bad = candidate(3.4)
    del bad["predicate"]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(bad))
    assert result["status"] == "invalid_response"


def test_one_expression_per_request_is_enforced():
    bad = arithmetic("1+1")
    bad["expressions"] = {"a": "1+1", "b": "2+2"}
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(bad))
    assert result["status"] == "invalid_response"


def test_refusal_is_returned_to_the_solver_as_a_result():
    script = [candidate(3.4)] * 11 + [final()]
    chat = scripted(*script)
    v23.run_solver_v23(SOLVER_INPUT, chat, max_calls=40)
    assert "refused" in chat.seen[-1][-1]["content"]


def test_total_check_budget_is_enforced():
    script = [arithmetic(f"{i}") for i in range(10)]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(*script), max_calls=40, max_checks=3)
    assert result["status"] == "budget_exhausted"
    assert len(result["calculations"]) == 3


def test_model_call_budget_is_enforced():
    result = v23.run_solver_v23(
        SOLVER_INPUT, scripted(arithmetic("1+1"), arithmetic("2+2")), max_calls=2
    )
    assert result["status"] == "budget_exhausted"


def test_control_arm_rejects_toolkit_but_keeps_calculator():
    calc_chat = scripted(arithmetic("3.4/0.15"), final())
    ok = v23.run_solver_v23(SOLVER_INPUT, calc_chat, toolkit=False)
    assert ok["status"] == "completed"
    assert "Guess and test" not in calc_chat.seen[0][0]["content"]
    toolkit_use = final()
    toolkit_use["attempts"][0]["toolkit_used"] = ["guess_and_test"]
    bad = v23.run_solver_v23(SOLVER_INPUT, scripted(toolkit_use), toolkit=False)
    assert bad["status"] == "invalid_response"


def test_toolkit_arm_shows_the_toolkit_and_calculator_together():
    chat = scripted(final())
    v23.run_solver_v23(SOLVER_INPUT, chat, toolkit=True)
    system = chat.seen[0][0]["content"]
    assert "Guess and test" in system and "calculate" in system


def test_api_error_and_truncation_are_not_verdicts():
    api = v23.run_solver_v23(SOLVER_INPUT, scripted(OpenAIError("down")))
    assert api["status"] == "api_error" and api["output"] is None
    cut = v23.run_solver_v23(SOLVER_INPUT, scripted(reply(final(), "length")))
    assert cut["status"] == "truncated"


def test_checked_trial_still_needs_its_trial_count():
    attempts = [
        {
            "idea": "Guess and test",
            "method_kind": "checked_trial",
            "trial_count": None,
            "toolkit_used": [],
            "work": "Try 3.4 km.",
        }
    ]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(final(attempts)))
    assert result["status"] == "invalid_response"


def _judge_task():
    return {
        "action": "final",
        "alignment": {"verdict": "yes", "quotes": [QUOTE], "reason": "Matches the target."},
        "invention": {"verdict": "yes", "quotes": [QUOTE], "reason": "The distance is open."},
        "validity": {
            "verdict": "yes",
            "assumptions": ["Jasmine keeps 0.15 km per minute on Hady's bike."],
            "reading_dependence": "stated_choice",
            "reason": "Consistent under the named reading.",
        },
    }


def _audit(statuses):
    return {
        "action": "final",
        "attempts": [{"status": status, "reason": "Worked evidence."} for status in statuses],
        "inaccessible_because": None,
    }


def test_aids_reach_the_attempt_judge_and_never_change_its_verdicts():
    calc = arithmetic("3.4/0.15", attempt=0)
    solver = scripted(calc, final())
    judge = scripted(_judge_task(), _audit(["meets_demands"]))
    result = v23.evaluate_v23(TASK, TARGET, CONTEXT, solver_chat=solver, judge_chat=judge)
    attempt_prompt = json.loads(judge.seen[1][1]["content"])
    aids = attempt_prompt["attempts"][0]["calculator_aids"]
    assert aids and aids[0]["status"] == "holds"
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["measures"]["familiar_approach_limits"]["value"] == "no"


def test_refused_aid_does_not_change_the_verdict_either():
    script = [candidate(3.4)] * 11 + [final()]
    judge = scripted(_judge_task(), _audit(["meets_demands"]))
    result = v23.evaluate_v23(
        TASK, TARGET, CONTEXT, solver_chat=scripted(*script), judge_chat=judge
    )
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["solver_calculator"]["refused"] == 1
    assert result["version"] == "pf-three-role/v2.3"


def test_solver_calculator_summary_is_recorded():
    script = [arithmetic("1+1"), candidate(3.4), final()]
    result = v23.evaluate_v23(
        TASK,
        TARGET,
        CONTEXT,
        solver_chat=scripted(*script),
        judge_chat=scripted(_judge_task(), _audit(["meets_demands"])),
    )
    assert result["solver_calculator"]["requests"] == 2
    assert result["solver_calculator"]["refused"] == 0
    assert result["solver_calculator"]["candidate_checks_by_attempt"] == {"0": 1}


def test_no_history_skips_the_solver_without_calculator_use():
    no_history = {"grade": 7, "subject": "mathematics"}
    result = v23.evaluate_v23(
        TASK,
        TARGET,
        no_history,
        solver_chat=scripted(),
        judge_chat=scripted(_judge_task()),
    )
    assert result["solver"]["status"] == "input_unavailable"
    assert result["solver_calculator"]["requests"] == 0
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "unclear"


def test_missing_action_on_a_complete_solver_reply_is_accepted_and_flagged():
    body = {"assumptions": final()["assumptions"], "attempts": final()["attempts"]}
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(body))
    assert result["status"] == "completed"
    assert result["action_missing"] is True
    assert result["runtime_correction"].startswith("pf-three-role-v23-runtime/v1.1")
    assert len(result["output"]["attempts"]) == 1


def test_explicit_final_is_not_flagged_as_a_correction():
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(final()))
    assert result["status"] == "completed"
    assert result["action_missing"] is False
    assert result["runtime_correction"] is None


def test_missing_action_with_extra_keys_is_still_rejected():
    body = {"assumptions": [], "attempts": final()["attempts"], "notes": "extra"}
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(body))
    assert result["status"] == "invalid_response"


def test_missing_action_does_not_bypass_the_control_arm_toolkit_rule():
    attempts = final()["attempts"]
    attempts[0]["toolkit_used"] = ["guess_and_test"]
    body = {"assumptions": final()["assumptions"], "attempts": attempts}
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(body), toolkit=False)
    assert result["status"] == "invalid_response"


def test_a_calculation_without_its_action_is_still_rejected():
    request = arithmetic("1+1")
    del request["action"]
    result = v23.run_solver_v23(SOLVER_INPUT, scripted(request))
    assert result["status"] == "invalid_response"
