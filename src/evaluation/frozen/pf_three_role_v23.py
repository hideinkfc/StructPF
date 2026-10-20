"""Three-role PF instrument v2.3: solver with an iterative calculator (aid only).

Single change from v2.2: the solver may run one calculator step at a time, see each result,
and continue. Judges, parsers and assembly are reused unchanged from the frozen v2.2 module.
Calculator results are attached to the attempts as aids and never set a verdict by themselves.
Nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Callable, Literal

import yaml
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.pf_three_role import prepare_input
from src.generation.design_calculator import calculate_condition
from src.utils.llm_client import LLMResponse

logger = logging.getLogger(__name__)
VERSION = "pf-three-role/v2.3"
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "pf_three_role_v2_3.yaml"
FROZEN_PROMPT_SHA256 = "c51869f23a2c4c39378742b652257f42c24a9e87de4f7664c138b1288b41ce55"
CANDIDATE_CAP = 10
RUNTIME_CORRECTION = (
    "pf-three-role-v23-runtime/v1.1: a complete solver reply with exactly assumptions and "
    "attempts is accepted as final when the action key is omitted. The frozen prompt is "
    "unchanged and the omission is recorded in the run."
)
MAX_SOLVER_CALLS = 40
MAX_SOLVER_CHECKS = 120
Chat = Callable[[list[dict[str, str]]], LLMResponse]


class SolverCalc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["calculate"]
    purpose: str = Field(min_length=1)
    attempt: int = Field(ge=0, le=3)
    kind: Literal["arithmetic", "candidate_check"]
    values: dict[str, JsonValue] = Field(default_factory=dict)
    expressions: dict[str, str]
    predicate: str | None = None
    symbols: dict[str, Literal["real", "integer", "positive", "nonnegative"]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def one_step_and_predicates(self) -> SolverCalc:
        if len(self.expressions) != 1:
            raise ValueError("Each calculator request must contain exactly one expression")
        name, expression = next(iter(self.expressions.items()))
        if not name.isidentifier() or not expression.strip():
            raise ValueError("The expression needs an identifier name and a nonempty formula")
        if self.kind == "candidate_check" and not (self.predicate or "").strip():
            raise ValueError("A candidate_check must state the predicate it tests")
        return self


def prompts() -> dict:
    source = PROMPT_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.3 prompt changed; use a new instrument version")
    spec = yaml.safe_load(source)
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.3 prompt version")
    return spec


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def solver_system(*, toolkit: bool) -> str:
    spec = prompts()
    note = (
        spec["solver_toolkit_intro"] + "\n" + v22.toolkit_block()
        if toolkit
        else spec["solver_control_note"]
    )
    final = '{"action":"final","assumptions":[...],"attempts":[<up to 4 attempts>]}'
    return "\n\n".join(
        [
            spec["common"],
            spec["solver"],
            spec["solver_calculator"],
            note,
            "Final contract:\n" + final,
            "Final answer schema:\n" + json.dumps(v22.SolverReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(SolverCalc.model_json_schema()),
        ]
    )


def _execute(request: SolverCalc, counts: Counter) -> tuple[dict, bool]:
    refusal = None
    if request.kind == "candidate_check":
        if any(isinstance(v, list) and len(v) > 1 for v in request.values.values()):
            refusal = "Refused: candidate lists are not allowed; test one candidate per request."
        elif counts[request.attempt] >= CANDIDATE_CAP:
            refusal = (
                f"Refused: candidate limit of {CANDIDATE_CAP} reached for attempt "
                f"{request.attempt}; mark this approach unchecked."
            )
    entry = {
        "attempt": request.attempt,
        "kind": request.kind,
        "purpose": request.purpose,
        "request": request.model_dump(),
    }
    if refusal:
        return {**entry, "status": "refused", "reason": refusal, "computed": {}}, True
    if request.kind == "candidate_check":
        counts[request.attempt] += 1
    name, expression = next(iter(request.expressions.items()))
    predicate = request.predicate or f"{name} == {name}"
    calc = calculate_condition(
        {"expressions": {name: expression}, "predicate": predicate, "symbols": request.symbols},
        request.values,
    )
    return {
        **entry,
        "status": calc["status"],
        "reason": calc["reason"],
        "computed": calc["computed"],
    }, False


def _fail(record: dict, status: str, exc: Exception) -> dict:
    logger.error("solver %s: %s", status, exc)
    record.update({"status": status, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return record


def run_solver_v23(
    payload: dict,
    chat: Chat,
    *,
    toolkit: bool = True,
    max_calls: int = MAX_SOLVER_CALLS,
    max_checks: int = MAX_SOLVER_CHECKS,
) -> dict:
    if set(payload) != {"student_task", "learner_context"}:
        raise ValueError("solver input contains unallowlisted fields")
    if not 1 <= max_calls <= MAX_SOLVER_CALLS or not 1 <= max_checks <= MAX_SOLVER_CHECKS:
        raise ValueError("Solver limits must stay within the frozen ceilings")
    messages = [
        {"role": "system", "content": solver_system(toolkit=toolkit)},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": "solver",
        "version": VERSION,
        "toolkit_allowed": toolkit,
        "prompt_sha256": fingerprint(),
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
                entry, refused = _execute(SolverCalc.model_validate(raw), counts)
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
            missing_action = action is None and set(raw) == {"assumptions", "attempts"}
            if action == "final" or missing_action:
                body = {key: value for key, value in raw.items() if key != "action"}
                reply = v22.SolverReply.model_validate(body)
                if not toolkit and any(item.toolkit_used for item in reply.attempts):
                    raise ValueError("Toolkit use is not allowed in the control arm")
                record["output"] = reply.model_dump()
                record["candidate_checks_by_attempt"] = {
                    str(key): value for key, value in counts.items()
                }
                record["action_missing"] = missing_action
                record["runtime_correction"] = RUNTIME_CORRECTION if missing_action else None
                record["status"] = "completed"
                return record
            raise ValueError("Solver requires action=calculate or action=final")
        except (ValueError, ValidationError) as exc:
            return _fail(record, "invalid_response", exc)
    return _fail(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def attempts_with_aids(solver_output: dict, calculations: list[dict]) -> list[dict]:
    attempts = []
    for index, attempt in enumerate(solver_output["attempts"]):
        aids = [
            {
                "purpose": item["purpose"],
                "expression": next(iter(item["request"]["expressions"].values())),
                "status": item["status"],
                "computed": item["computed"],
            }
            for item in calculations
            if item["attempt"] == index
        ]
        attempts.append({**attempt, "calculator_aids": aids})
    return attempts


def evaluate_v23(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chat: Chat,
    judge_chat: Chat,
    toolkit: bool = True,
) -> dict:
    prepared = prepare_input(task, target, context)
    task_result = v22.run_role("task_judge", v22.role_input("task_judge", prepared), judge_chat)
    history = prepared["learner_context"].get("assumed_prior_knowledge")
    if history:
        solver = run_solver_v23(v22.role_input("solver", prepared), solver_chat, toolkit=toolkit)
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
                attempts_with_aids(solver["output"], solver["calculations"]),
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
