"""PF three-role v3.1: systematic Tier (a) shortcut-first solver and matching attempt judge.

Extends pf-three-role/v3.0 so the solver's Tier (a) baseline always tests (1) any
character's conjectured shortcut in student_task and (2) the simplest single-step or
aggregate application of a listed prior skill whenever the task's numbers create a tie,
opposite ranking, or overlap on that baseline, before Tier (b) executes the full
multi-step resolution, while keeping routine tasks without such a trap at meets_demands
(limits = no). Task-judge prompts and rules are identical to v3.0.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from openai import OpenAIError
from pydantic import ValidationError

from src.evaluation import pf_three_role_v30 as v30
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v23 as v23
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation.frozen import pf_three_role_v28 as v28
from src.generation.design_calculator import calculate_condition

VERSION = "pf-three-role/v3.1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v3_1.yaml"
FROZEN_PROMPT_SHA256 = "4c10a0a4aa3f21f39e850e4ddf076de606ff5a945be3e58fa42a41fcf9a5521f"
FROZEN_TASK_SYSTEM_SHA256 = "001929e8a7609966d78f36477c73864d3dce1942a456e3a26df671dbd8750218"
FROZEN_ATTEMPT_SYSTEM_SHA256 = "4d16c5c87eff1195b6103f630a6e068a7d89a62958802c8c635b24cf810d3bc7"
FROZEN_SOLVER_SYSTEM_SHA256 = {
    "toolkit": "f6cd2822733aa2094a6334b841f12c27754ac27529266027f082d3f00888693e",
    "no_toolkit": "6399469c1e04201933110f242e323b65dac0671615f8d589755edb1b4a95b7f8",
}

parse_task_v31 = v30.parse_task_v30
parse_attempts_v31 = v30.parse_attempts_v30


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v3.1 prompt version")
    return spec


def prompts() -> dict:
    if (
        FROZEN_PROMPT_SHA256
        and hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256
    ):
        raise ValueError("Frozen v3.1 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def task_system() -> str:
    text = v30._compose_task_system(prompts())
    if (
        FROZEN_TASK_SYSTEM_SHA256
        and hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_TASK_SYSTEM_SHA256
    ):
        raise ValueError("Frozen v3.1 task system changed; use a new instrument version")
    return text


def attempt_system() -> str:
    text = v30._compose_attempt_system(prompts())
    if (
        FROZEN_ATTEMPT_SYSTEM_SHA256
        and hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_ATTEMPT_SYSTEM_SHA256
    ):
        raise ValueError("Frozen v3.1 attempt system changed; use a new instrument version")
    return text


def solver_system(*, toolkit: bool) -> str:
    text = v30._compose_solver_system(prompts(), toolkit=toolkit)
    key = "toolkit" if toolkit else "no_toolkit"
    expected = FROZEN_SOLVER_SYSTEM_SHA256[key]
    if expected and hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
        raise ValueError("Frozen v3.1 solver system changed; use a new instrument version")
    return text


def task_system_sha256() -> str:
    return hashlib.sha256(v30._compose_task_system(_spec()).encode("utf-8")).hexdigest()


def attempt_system_sha256() -> str:
    return hashlib.sha256(v30._compose_attempt_system(_spec()).encode("utf-8")).hexdigest()


def solver_system_sha256(*, toolkit: bool) -> str:
    return hashlib.sha256(
        v30._compose_solver_system(_spec(), toolkit=toolkit).encode("utf-8")
    ).hexdigest()


def run_solver_v31(
    payload: dict,
    chat: v25.Chat,
    *,
    solver_id: str,
    toolkit: bool = True,
    max_calls: int = v25.MAX_SOLVER_CALLS,
    max_checks: int = v25.MAX_SOLVER_CHECKS,
) -> dict:
    if set(payload) != {"student_task", "learner_context"}:
        raise ValueError("solver input contains unallowlisted fields")
    if not 1 <= max_calls <= v25.MAX_SOLVER_CALLS or not 1 <= max_checks <= v25.MAX_SOLVER_CHECKS:
        raise ValueError("Solver limits must stay within the frozen ceilings")
    messages = [
        {"role": "system", "content": solver_system(toolkit=toolkit)},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": "solver",
        "solver": solver_id,
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
            return v25._fail(record, "api_error", exc)
        call["response"] = {
            "text": response.text,
            "model": response.model,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }
        if response.finish_reason == "length":
            return v25._fail(record, "truncated", ValueError("Completion budget exhausted"))
        if response.finish_reason not in {"", "stop"}:
            return v25._fail(record, "invalid_response", ValueError("Unusable finish reason"))
        try:
            raw = json.loads(response.text)
            if not isinstance(raw, dict):
                raise ValueError("Response must be a JSON object")
            action = raw.get("action")
            if action == "calculate":
                if len(record["calculations"]) >= max_checks:
                    return v25._fail(
                        record, "budget_exhausted", ValueError("Calculator check budget exceeded")
                    )
                entry, refused = v23._execute(v25.SolverCalc.model_validate(raw), counts)
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
                reply = v30.FinalSolverReply.model_validate(raw)
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
            raise ValueError('Solver requires action "calculate" or "final"')
        except (ValueError, ValidationError) as exc:
            return v25._fail(record, "invalid_response", exc)
    return v25._fail(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def run_judge_v31(
    role: Literal["task_judge", "attempt_judge"],
    payload: dict,
    chat: v22.Chat,
    *,
    max_calls: int = 4,
    max_checks: int = 16,
) -> dict:
    expected = {"student_task", "learner_context", "learning_target"}
    if role == "attempt_judge":
        expected.add("attempts")
    if set(payload) != expected:
        raise ValueError(f"{role} input contains unallowlisted fields")
    if not 1 <= max_calls <= 5 or not 1 <= max_checks <= 16:
        raise ValueError("Execution limits must be 1-5 calls and 1-16 calculator checks")
    sys_text = task_system() if role == "task_judge" else attempt_system()
    sys_hash = task_system_sha256() if role == "task_judge" else attempt_system_sha256()
    messages = [
        {"role": "system", "content": sys_text},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": role,
        "version": VERSION,
        "prompt_sha256": fingerprint(),
        "system_sha256": sys_hash,
        "input": payload,
        "status": "starting",
        "output": None,
        "calls": [],
        "calculations": [],
        "schema_repairs": [],
        "error": None,
    }
    frozen_text = None
    for number in range(max_calls):
        call = {"messages": [dict(item) for item in messages], "response": None}
        record["calls"].append(call)
        try:
            response = chat(messages)
        except (OpenAIError, ConnectionError, TimeoutError) as exc:
            return v22._failure(record, "api_error", exc)
        call["response"] = {
            "text": response.text,
            "model": response.model,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }
        if response.finish_reason == "length":
            return v22._failure(record, "truncated", ValueError("Completion budget exhausted"))
        if response.finish_reason not in {"", "stop"}:
            return v22._failure(record, "invalid_response", ValueError("Unusable finish reason"))
        try:
            raw = json.loads(response.text)
            if not isinstance(raw, dict):
                raise ValueError("Response must be a JSON object")
            if raw.get("action") == "calculate":
                req = v28.JudgeCalc.model_validate(raw)
                if len(record["calculations"]) + len(req.checks) > max_checks:
                    return v22._failure(
                        record, "budget_exhausted", ValueError("Check budget exceeded")
                    )
                results = []
                for check in req.checks:
                    calc = calculate_condition(
                        {
                            "expressions": check.expressions,
                            "predicate": check.predicate,
                            "symbols": check.symbols,
                        },
                        check.values,
                    )
                    entry = {
                        "index": len(record["calculations"]),
                        "request": check.model_dump(),
                        "result": calc,
                    }
                    record["calculations"].append(entry)
                    results.append(entry)
                messages.extend(
                    [
                        {"role": "assistant", "content": response.text},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "calculator_results": results,
                                    "remaining_model_calls": max_calls - number - 1,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ]
                )
                continue
            if raw.get("action") == "final":
                if role == "task_judge" and number + 1 < max_calls:
                    bad_quote_fields = []
                    for field in ("alignment", "invention"):
                        try:
                            v30._text_v30(raw.get(field), payload["student_task"])
                        except (ValidationError, ValueError):
                            bad_quote_fields.append(field)
                    if bad_quote_fields:
                        record["schema_repairs"].append(
                            {"call": number, "reason": f"Unmatched quote in {bad_quote_fields}"}
                        )
                        messages.extend(
                            [
                                {"role": "assistant", "content": response.text},
                                {
                                    "role": "user",
                                    "content": (
                                        f"In {', '.join(bad_quote_fields)}, quotes must contain at "
                                        "least one exact verbatim substring copied character-for-"
                                        "character from student_task (not learning_target or "
                                        "learner_context). Return the complete final JSON with "
                                        "exact student_task quotes. "
                                        f"Remaining calls: {max_calls - number - 1}."
                                    ),
                                },
                            ]
                        )
                        continue
                    if raw.get("validity") is None and payload["learning_target"] is not None:
                        try:
                            alignment = v30._text_v30(raw.get("alignment"), payload["student_task"])
                        except (ValidationError, ValueError):
                            alignment = None
                        if alignment is not None and alignment["value"] == "yes":
                            frozen_text = frozen_text or {
                                "alignment": raw["alignment"],
                                "invention": raw.get("invention"),
                                "accessibility": raw.get("accessibility"),
                            }
                            record["schema_repairs"].append(
                                {"call": number, "reason": "Aligned final reply omitted validity"}
                            )
                            messages.extend(
                                [
                                    {"role": "assistant", "content": response.text},
                                    {
                                        "role": "user",
                                        "content": (
                                            "Your alignment is yes, so validity cannot be null. "
                                            "Complete the validity object only. Keep alignment, "
                                            "invention and accessibility unchanged. You may request "
                                            "calculations first. "
                                            f"Remaining calls: {max_calls - number - 1}."
                                        ),
                                    },
                                ]
                            )
                            continue
                if (
                    role == "attempt_judge"
                    and (
                        not isinstance(raw.get("attempts"), list)
                        or len(raw["attempts"]) != len(payload["attempts"])
                    )
                    and number + 1 < max_calls
                ):
                    got = (
                        len(raw["attempts"])
                        if isinstance(raw.get("attempts"), list)
                        else "non-list"
                    )
                    need = len(payload["attempts"])
                    record["schema_repairs"].append(
                        {"call": number, "reason": f"Attempt audit count {got} != {need}"}
                    )
                    messages.extend(
                        [
                            {"role": "assistant", "content": response.text},
                            {
                                "role": "user",
                                "content": (
                                    f"Your attempts list has {got} items, but the input has "
                                    f"{need} attempts. Return action='final' with exactly {need} "
                                    "Audit items in attempts, in the same order. "
                                    f"Remaining calls: {max_calls - number - 1}."
                                ),
                            },
                        ]
                    )
                    continue
                if frozen_text is not None:
                    raw.update(frozen_text)
                record["output"] = raw
                record["status"] = "completed"
                return record
            raise ValueError("Judge requires action=calculate or action=final")
        except (ValueError, ValidationError) as exc:
            return v22._failure(record, "invalid_response", exc)
    return v22._failure(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def assemble_v31(
    prepared: dict, solver: dict, task: dict, attempt: dict | None, *, toolkit: bool
) -> dict:
    res = v30.assemble_v30(prepared, solver, task, attempt, toolkit=toolkit)
    res["version"] = VERSION
    res["prompt_sha256"] = fingerprint()
    return res


def evaluate_v31(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict,
    judge_chat: v22.Chat,
    toolkit: bool = True,
) -> dict:
    prepared = v25.prepare_input(task, target, context)
    task_result = run_judge_v31("task_judge", v22.role_input("task_judge", prepared), judge_chat)
    task_rows = (
        parse_task_v31(task_result["output"], prepared)
        if task_result["status"] == "completed"
        else None
    )
    access_yes = (
        task_rows is not None
        and task_rows["prior_knowledge_accessibility"]["status"] == "assessed"
        and task_rows["prior_knowledge_accessibility"]["value"] == "yes"
    )
    if not access_yes:
        solver = {
            "status": "not_run_accessibility_gate",
            "error": None,
            "calls": [],
            "calculations": [],
            "output": None,
            "solvers": {},
        }
        attempt = None
        principles = v25.principle_counts({})
    else:
        solver_runs = {
            solver_id: run_solver_v31(
                v22.role_input("solver", prepared), chat, solver_id=solver_id, toolkit=toolkit
            )
            for solver_id, chat in solver_chats.items()
        }
        items = v25.combine_attempts(solver_runs)
        solver = v25._combined_solver(solver_runs, items)
        attempt = None
        if items:
            attempt = run_judge_v31(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                judge_chat,
            )
        principles = v25.principle_counts(solver_runs)
    result = assemble_v31(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
