"""Three-role PF instrument v2.4: solver final-answer schema fixed.

Single fix over v2.3: the final-answer schema shown to the solver includes action "final",
generated from the same model the parser validates, and a reply without the action is
invalid. The calculator loop and judges are reused from the frozen v2.2 and v2.3 modules.
Nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from openai import OpenAIError
from pydantic import ValidationError

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v23 as v23
from src.evaluation.pf_three_role import prepare_input

logger = logging.getLogger(__name__)
VERSION = "pf-three-role/v2.4"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2_4.yaml"
FROZEN_PROMPT_SHA256 = "8fda9c77fb003c8018baebb76e919df75bcbb903450ea86e607cd8b66d7fad45"
FROZEN_SOLVER_SYSTEM_SHA256 = {
    "toolkit": "16b054d55e0850d7862a23f674a8b1a678f332dc220ae048eae8fb739f92ad02",
    "no_toolkit": "c3dc55cc5d56ea3406506d89d3a8a1dd87b96090c670d2f0c98fe79a2cf3f5fc",
}
MAX_SOLVER_CALLS = v23.MAX_SOLVER_CALLS
MAX_SOLVER_CHECKS = v23.MAX_SOLVER_CHECKS


class FinalSolverReply(v22.SolverReply):
    action: Literal["final"]


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.4 prompt version")
    return spec


def prompts() -> dict:
    if hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.4 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def solver_system(*, toolkit: bool) -> str:
    return _render(prompts(), toolkit=toolkit)


def _render(spec: dict, *, toolkit: bool) -> str:
    note = (
        spec["solver_toolkit_intro"] + "\n" + v22.toolkit_block()
        if toolkit
        else spec["solver_control_note"]
    )
    final_schema = json.dumps(FinalSolverReply.model_json_schema())
    return "\n\n".join(
        [
            spec["common"],
            spec["solver"],
            spec["solver_calculator"],
            note,
            "Final answer schema (reply with exactly this shape, action included):\n"
            + final_schema,
            "Calculator request schema:\n" + json.dumps(v23.SolverCalc.model_json_schema()),
        ]
    )


def solver_system_sha256(*, toolkit: bool) -> str:
    """Hash of the exact solver system prompt. Unguarded so it can be pinned."""
    return hashlib.sha256(_render(_spec(), toolkit=toolkit).encode("utf-8")).hexdigest()


def _fail(record: dict, status: str, exc: Exception) -> dict:
    logger.error("solver %s: %s", status, exc)
    record.update({"status": status, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return record


def run_solver_v24(
    payload: dict,
    chat,
    *,
    toolkit: bool = True,
    max_calls: int = MAX_SOLVER_CALLS,
    max_checks: int = MAX_SOLVER_CHECKS,
) -> dict:
    if set(payload) != {"student_task", "learner_context"}:
        raise ValueError("solver input contains unallowlisted fields")
    if not 1 <= max_calls <= MAX_SOLVER_CALLS or not 1 <= max_checks <= MAX_SOLVER_CHECKS:
        raise ValueError("Solver limits must stay within the frozen ceilings")
    system = solver_system(toolkit=toolkit)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": "solver",
        "version": VERSION,
        "toolkit_allowed": toolkit,
        "prompt_sha256": fingerprint(),
        "system_sha256": solver_system_sha256(toolkit=toolkit),
        "input": payload,
        "status": "starting",
        "output": None,
        "calls": [],
        "calculations": [],
        "candidate_checks_by_attempt": {},
        "error": None,
    }
    counts: Counter = Counter()
    for number in range(max_calls):
        call = {"messages": [dict(item) for item in messages], "response": None}
        record["calls"].append(call)
        try:
            response = chat(messages)
        except (OpenAIError, ConnectionError, TimeoutError) as exc:
            return _fail(record, "api_error", exc)
        call["response"] = {
            "text": response.text,
            "model": response.model,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }
        if response.finish_reason == "length":
            return _fail(record, "truncated", ValueError("Completion budget exhausted"))
        if response.finish_reason not in {"", "stop"}:
            return _fail(record, "invalid_response", ValueError("Unusable finish reason"))
        try:
            raw = json.loads(response.text)
            if not isinstance(raw, dict):
                raise ValueError("Response must be a JSON object")
            action = raw.get("action")
            if action == "calculate":
                if len(record["calculations"]) >= max_checks:
                    return _fail(
                        record, "budget_exhausted", ValueError("Calculator check budget exceeded")
                    )
                entry, refused = v23._execute(v23.SolverCalc.model_validate(raw), counts)
                record["calculations"].append({**entry, "refused": refused})
                messages.extend(
                    [
                        {"role": "assistant", "content": response.text},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "calculator_result": entry,
                                    "remaining_model_calls": max_calls - number - 1,
                                    "remaining_checks": max_checks - len(record["calculations"]),
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ]
                )
                continue
            if action == "final":
                reply = FinalSolverReply.model_validate(raw)
                if not toolkit and any(item.toolkit_used for item in reply.attempts):
                    raise ValueError("Toolkit use is not allowed in the control arm")
                record["output"] = {
                    "assumptions": reply.assumptions,
                    "attempts": [item.model_dump() for item in reply.attempts],
                }
                record["candidate_checks_by_attempt"] = {
                    str(key): value for key, value in counts.items()
                }
                record["status"] = "completed"
                return record
            raise ValueError(
                'Solver requires action "calculate" or "final"; action was missing or unknown'
            )
        except (ValueError, ValidationError) as exc:
            return _fail(record, "invalid_response", exc)
    return _fail(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def evaluate_v24(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chat,
    judge_chat,
    toolkit: bool = True,
) -> dict:
    prepared = prepare_input(task, target, context)
    task_result = v22.run_role("task_judge", v22.role_input("task_judge", prepared), judge_chat)
    history = prepared["learner_context"].get("assumed_prior_knowledge")
    if history:
        solver = run_solver_v24(v22.role_input("solver", prepared), solver_chat, toolkit=toolkit)
    else:
        solver = {
            "status": "input_unavailable",
            "error": None,
            "calls": [],
            "calculations": [],
            "output": None,
        }
    attempt = None
    if solver["status"] == "completed":
        attempt = v22.run_role(
            "attempt_judge",
            v22.role_input(
                "attempt_judge",
                prepared,
                v23.attempts_with_aids(solver["output"], solver["calculations"]),
            ),
            judge_chat,
        )
    result = v22.assemble_v22(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solver_calculator": {
            "requests": len(solver["calculations"]),
            "refused": sum(item.get("refused", False) for item in solver["calculations"]),
            "candidate_checks_by_attempt": solver.get("candidate_checks_by_attempt", {}),
        },
    }
