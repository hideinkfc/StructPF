"""Mock tests for v2.6. Scripted replies only; no model calls."""

import json

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v25 as v25
from src.evaluation import pf_three_role_v26 as v26
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


def test_pinned_hashes_match_the_live_prompt_and_attempt_system():
    assert v26.fingerprint() == v26.FROZEN_PROMPT_SHA256
    assert v26.attempt_system_sha256() == v26.FROZEN_ATTEMPT_SYSTEM_SHA256
    assert v26.attempt_system() == v26.compose_attempt_system(v26.prompts()["attempt_judge"])


def test_composition_reproduces_the_frozen_v22_attempt_judge_with_its_own_text():
    assert v26.compose_attempt_system(v22.prompts()["attempt_judge"]) == v22.system("attempt_judge")


def test_strict_start_rule_is_in_the_attempt_judge_and_the_witness_rule_is_kept():
    text = v26.attempt_system()
    assert "Strict start rule" in text
    assert "taught_as" in text
    assert "A supplied formula does not make its use available" in text
    assert "Absence of a witness is not that argument" in text


def test_run_role_uses_the_supplied_system_text_and_default_is_unchanged():
    seen = []

    def chat(messages):
        seen.append(messages)
        return reply({"action": "final", "attempts": [], "inaccessible_because": None})

    payload = {
        "student_task": TASK,
        "learner_context": CONTEXT,
        "learning_target": TARGET,
        "attempts": [],
    }
    v22.run_role("attempt_judge", payload, chat, system_text="SENTINEL SYSTEM")
    assert seen[-1][0]["content"] == "SENTINEL SYSTEM"
    v22.run_role("attempt_judge", payload, chat)
    assert seen[-1][0]["content"] == v22.system("attempt_judge")


def test_no_history_gives_unclear_accessibility_and_no_attempt_judge():
    judge_calls = []

    def judge(messages):
        judge_calls.append(messages)
        return reply(TASK_REPLY)

    result = v26.evaluate_v26(
        TASK, TARGET, {"grade": 7}, solver_chats={"luna": scripted()}, judge_chat=judge
    )
    assert result["version"] == v26.VERSION
    assert result["attempt_judge"] is None
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "unclear"
    assert len(judge_calls) == 1


def test_attempt_judge_receives_the_strict_system_and_its_hash_is_recorded():
    attempt_calls = []

    def judge(messages):
        if '"attempts"' in messages[1]["content"]:
            attempt_calls.append(messages)
            return reply(
                {
                    "action": "final",
                    "attempts": [
                        {"status": "meets_demands", "reason": "mock"},
                        {"status": "meets_demands", "reason": "mock"},
                    ],
                    "inaccessible_because": None,
                }
            )
        return reply(TASK_REPLY)

    result = v26.evaluate_v26(
        TASK,
        TARGET,
        CONTEXT,
        solver_chats={
            "luna": scripted(final_body(approach("total distance divided by total time"))),
            "gpt41": scripted(final_body(approach("equal-time comparison"))),
        },
        judge_chat=judge,
    )
    assert attempt_calls[-1][0]["content"] == v26.attempt_system()
    attempt = result["attempt_judge"]
    assert attempt["system_sha256"] == v26.attempt_system_sha256()
    assert result["measures"]["prior_knowledge_accessibility"]["value"] == "yes"
    assert result["approach_items_judged"] == 2
    assert set(result["solvers"]) == {"luna", "gpt41"}
    assert v25.VERSION != result["version"]
