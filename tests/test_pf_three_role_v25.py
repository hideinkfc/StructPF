"""Mock tests for v2.5. Scripted replies only; no model calls."""

import json

import pytest
from pydantic import ValidationError

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v25 as v25
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


def reply(payload, finish_reason="stop"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMResponse(
        text=text,
        model="mock",
        finish_reason=finish_reason,
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )


def scripted(*items):
    queue = list(items)
    seen = []

    def chat(messages):
        seen.append([dict(item) for item in messages])
        item = queue.pop(0)
        return item if isinstance(item, LLMResponse) else reply(item)

    chat.seen = seen
    return chat


def approach(principle, **overrides):
    body = {
        "idea": f"Idea using {principle}",
        "principle": principle,
        "method_kind": "structured",
        "trial_count": None,
        "toolkit_used": [],
        "work": f"Work for {principle}; answer 3.4 km.",
    }
    body.update(overrides)
    return body


def final_body(*approaches, assumptions=None):
    return {
        "action": "final",
        "assumptions": assumptions or ["Jasmine keeps 0.15 km per minute on Hady's bike."],
        "attempts": list(approaches) or [approach("total distance divided by total time")],
    }


TASK_REPLY = {
    "action": "final",
    "alignment": {
        "verdict": "yes",
        "quotes": ["How far should Jasmine ride Hady's bike"],
        "reason": "The task asks for the coordinated distance.",
    },
    "invention": {
        "verdict": "partly",
        "quotes": ["Hady lends Jasmine his bike"],
        "reason": "The bike swap is given.",
    },
    "validity": {
        "verdict": "yes",
        "assumptions": [],
        "reading_dependence": "none",
        "reason": "The numbers determine one answer.",
    },
}


def attempt_reply(*statuses):
    return {
        "action": "final",
        "attempts": [{"status": status, "reason": "mock"} for status in statuses],
        "inaccessible_because": None,
    }


def judge(messages):
    """Task judge first; attempt judge when the user payload carries attempts."""
    if '"attempts"' in messages[1]["content"]:
        return reply(judge.attempt)
    return reply(TASK_REPLY)


judge.attempt = attempt_reply("meets_demands")


def test_pinned_hashes_match_the_live_prompt_and_both_solver_systems():
    assert v25.fingerprint() == v25.FROZEN_PROMPT_SHA256
    assert v25.solver_system_sha256(toolkit=True) == v25.FROZEN_SOLVER_SYSTEM_SHA256["toolkit"]
    assert v25.solver_system_sha256(toolkit=False) == v25.FROZEN_SOLVER_SYSTEM_SHA256["no_toolkit"]


def test_freeze_guard_refuses_a_changed_prompt(monkeypatch):
    monkeypatch.setattr(v25, "FROZEN_PROMPT_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="changed"):
        v25.prompts()


def test_freeze_guard_refuses_a_changed_rendered_solver(monkeypatch):
    monkeypatch.setitem(v25.FROZEN_SOLVER_SYSTEM_SHA256, "toolkit", "0" * 64)
    with pytest.raises(ValueError, match="solver system prompt changed"):
        v25.solver_system(toolkit=True)


def test_solver_prompt_has_no_approach_cap_and_defines_same_and_different():
    system = v25.solver_system(toolkit=True)
    assert "up to four" not in system
    assert "no maximum number of approaches" in system
    assert "SAME" in system and "DIFFERENT" in system
    assert "principle" in system


def test_final_schema_has_no_approach_or_assumption_cap():
    schema = v25.FinalSolverReply.model_json_schema()
    attempts = schema["properties"]["attempts"]
    assumptions = schema["properties"]["assumptions"]
    assert "maxItems" not in attempts and attempts.get("minItems") == 1
    assert "maxItems" not in assumptions
    assert schema["properties"]["action"]["const"] == "final"


def test_many_approaches_and_assumptions_are_accepted():
    many = [approach(f"principle {number}") for number in range(9)]
    reply_model = v25.FinalSolverReply.model_validate(
        final_body(*many, assumptions=[f"assumption {n}" for n in range(12)])
    )
    assert len(reply_model.attempts) == 9
    assert len(reply_model.assumptions) == 12


def test_approach_without_principle_is_invalid():
    body = final_body(approach("x"))
    del body["attempts"][0]["principle"]
    with pytest.raises(ValidationError):
        v25.FinalSolverReply.model_validate(body)


def test_checked_trial_must_state_candidate_count():
    body = final_body(approach("guess and test", method_kind="checked_trial", trial_count=None))
    with pytest.raises(ValidationError):
        v25.FinalSolverReply.model_validate(body)


def test_calculator_attempt_number_is_unbounded_above_but_not_negative():
    base = {
        "action": "calculate",
        "purpose": "Divide",
        "kind": "arithmetic",
        "expressions": {"x": "3.4/0.15"},
    }
    assert v25.SolverCalc.model_validate({**base, "attempt": 7}).attempt == 7
    with pytest.raises(ValidationError):
        v25.SolverCalc.model_validate({**base, "attempt": -1})


def test_solver_input_is_target_blind_and_allowlisted():
    solver_input = v22.role_input("solver", PREPARED)
    assert set(solver_input) == {"student_task", "learner_context"}
    with pytest.raises(ValueError, match="unallowlisted"):
        v25.run_solver_v25(
            {**solver_input, "learning_target": TARGET}, scripted(), solver_id="luna"
        )


def test_solver_calculator_round_trip_passes_result_back_before_final():
    chat = scripted(
        {
            "action": "calculate",
            "purpose": "Divide the distance by the speed",
            "attempt": 0,
            "kind": "arithmetic",
            "expressions": {"t": "3.4/0.15"},
        },
        final_body(approach("total distance divided by total time")),
    )
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), chat, solver_id="luna")
    assert run["status"] == "completed"
    assert len(run["calculations"]) == 1
    second_call_user = chat.seen[1][-1]["content"]
    assert "calculator_result" in second_call_user and "remaining_checks" in second_call_user


def test_candidate_cap_applies_per_approach_and_refuses_the_eleventh():
    calls = []
    for _ in range(11):
        calls.append(
            {
                "action": "calculate",
                "purpose": "Test a candidate",
                "attempt": 0,
                "kind": "candidate_check",
                "values": {"t": 76},
                "expressions": {"d": "0.15*t"},
                "predicate": "d == 11.4",
            }
        )
    calls.append(
        {
            "action": "calculate",
            "purpose": "Test on another approach",
            "attempt": 1,
            "kind": "candidate_check",
            "values": {"t": 76},
            "expressions": {"d": "0.15*t"},
            "predicate": "d == 11.4",
        }
    )
    chat = scripted(*calls, final_body(approach("a"), approach("b")))
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), chat, solver_id="luna")
    assert run["status"] == "completed"
    assert run["calculations"][9]["refused"] is False
    assert run["calculations"][10]["refused"] is True
    assert run["calculations"][11]["refused"] is False
    assert run["candidate_checks_by_attempt"] == {"0": 10, "1": 1}


def test_list_of_candidates_is_refused():
    chat = scripted(
        {
            "action": "calculate",
            "purpose": "Search",
            "attempt": 0,
            "kind": "candidate_check",
            "values": {"t": [1, 2, 3]},
            "expressions": {"d": "0.15*t"},
            "predicate": "d == 11.4",
        },
        final_body(approach("a")),
    )
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), chat, solver_id="luna")
    assert run["calculations"][0]["refused"] is True


def test_control_arm_refuses_toolkit_use():
    chat = scripted(final_body(approach("a", toolkit_used=["guess_and_test"])))
    run = v25.run_solver_v25(
        v22.role_input("solver", PREPARED), chat, solver_id="luna", toolkit=False
    )
    assert run["status"] == "invalid_response"


def test_missing_action_is_invalid():
    body = final_body(approach("a"))
    del body["action"]
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), scripted(body), solver_id="luna")
    assert run["status"] == "invalid_response"


def test_api_error_is_recorded_not_raised():
    def failing(messages):
        raise ConnectionError("network down")

    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), failing, solver_id="luna")
    assert run["status"] == "api_error"


def test_truncated_reply_is_not_treated_as_failure_to_solve():
    chat = scripted(reply("{", finish_reason="length"))
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), chat, solver_id="luna")
    assert run["status"] == "truncated"


def test_principle_counts_per_solver_and_union_with_normalisation():
    runs = {
        "luna": {
            "status": "completed",
            "output": {
                "assumptions": [],
                "attempts": [
                    approach("Total distance divided by total time"),
                    approach("total distance  divided by total time"),
                    approach("average of two speeds"),
                ],
            },
        },
        "gpt41": {
            "status": "completed",
            "output": {"assumptions": [], "attempts": [approach("equal travel times")]},
        },
        "broken": {"status": "invalid_response", "output": None},
    }
    counts = v25.principle_counts(runs)
    assert counts["distinct_by_solver"] == {"luna": 2, "gpt41": 1}
    assert counts["distinct_union"] == 3


def test_combined_list_labels_each_attempt_with_its_solver_and_aids():
    runs = {
        "luna": {
            "status": "completed",
            "output": {"assumptions": ["A1"], "attempts": [approach("p1")]},
            "calculations": [
                {
                    "attempt": 0,
                    "purpose": "Divide",
                    "status": "holds",
                    "computed": {"t": 22.67},
                    "request": {"expressions": {"t": "3.4/0.15"}},
                }
            ],
        },
        "gpt41": {
            "status": "completed",
            "output": {"assumptions": ["A2"], "attempts": [approach("p2")]},
            "calculations": [],
        },
    }
    items = v25.combine_attempts(runs)
    assert [item["solver"] for item in items] == ["luna", "gpt41"]
    assert items[0]["solver_assumptions"] == ["A1"]
    assert items[0]["calculator_aids"][0]["expression"] == "3.4/0.15"
    assert items[1]["calculator_aids"] == []


def test_evaluate_runs_two_solvers_and_one_attempt_judge():
    judge_chat = judge
    judge.attempt = attempt_reply("meets_demands", "unrelated_shortfall")
    luna = scripted(final_body(approach("p1")))
    gpt41 = scripted(final_body(approach("p2")))
    seen_judge = []

    def recording_judge(messages):
        seen_judge.append(messages)
        return judge_chat(messages)

    result = v25.evaluate_v25(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={"luna": luna, "gpt41": gpt41},
        judge_chat=recording_judge,
    )
    attempt_payload = json.loads(seen_judge[-1][1]["content"])
    labels = [item["solver"] for item in attempt_payload["attempts"]]
    assert labels == ["luna", "gpt41"]
    assert len(seen_judge) == 2
    assert result["approach_items_judged"] == 2
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["principles"]["distinct_union"] == 2
    assert set(result["solvers"]) == {"luna", "gpt41"}


def test_one_failed_solver_is_excluded_and_recorded():
    judge.attempt = attempt_reply("meets_demands")
    result = v25.evaluate_v25(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={
            "luna": scripted(reply("not json")),
            "gpt41": scripted(final_body(approach("p2"))),
        },
        judge_chat=judge,
    )
    assert result["solvers"]["luna"]["status"] == "invalid_response"
    assert result["solvers"]["gpt41"]["status"] == "completed"
    assert result["approach_items_judged"] == 1
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"


def test_both_solvers_failing_gives_no_verdict_and_no_attempt_judge():
    calls = []

    def counting_judge(messages):
        calls.append(messages)
        return judge(messages)

    result = v25.evaluate_v25(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={"luna": scripted(reply("x")), "gpt41": scripted(reply("y"))},
        judge_chat=counting_judge,
    )
    assert result["measures"]["prior_knowledge_accessibility"]["status"] == "invalid_response"
    assert result["attempt_judge"] is None
    assert len(calls) == 1


def test_unlisted_calculator_attempt_is_counted_not_dropped():
    chat = scripted(
        {
            "action": "calculate",
            "purpose": "Divide",
            "attempt": 3,
            "kind": "arithmetic",
            "expressions": {"t": "3.4/0.15"},
        },
        final_body(approach("p1")),
    )
    run = v25.run_solver_v25(v22.role_input("solver", PREPARED), chat, solver_id="luna")
    summary = v25._solver_summary(run)
    assert summary["calculator_requests_without_listed_attempt"] == 1
