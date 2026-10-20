"""Three-role PF instrument v2.2: frozen October 15, 2026; mock-tested, not yet run.

Changes from v2.1: a shared, task-neutral basic toolkit for the solver (an arm switch),
explicit solver assumptions, checked versus unchecked trials, and an assumption
dependence that stops an unnamed reading from supporting a Yes. The v2 and v2.1 files
and their saved results are untouched. Nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Annotated, Callable, Literal

import yaml
from openai import OpenAIError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    ValidationError,
    model_validator,
)

from src.evaluation.pf_task_measures import MEASURES
from src.evaluation.pf_three_role import prepare_input
from src.generation.design_calculator import calculate_condition
from src.utils.llm_client import LLMResponse

logger = logging.getLogger(__name__)
VERSION = "pf-three-role/v2.2"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2_2.yaml"
FROZEN_PROMPT_SHA256 = "49ec603afd31f9dfd334733d8f33cc415ba79da28abbd58cce314eadcb5f0350"
FROZEN_TOOLKIT_SHA256 = "ce54ede3e15e9509e008a9aadfe10b999df21467fea59654b53058210bab56b0"
# Drafted from Polya's heuristics (How to Solve It, 1945): guess and test, work backwards,
# pattern, special cases, simpler related problem, table or diagram.
TOOLKIT = (
    {
        "id": "guess_and_test",
        "name": "Guess and test",
        "definition": (
            "Propose a candidate value, substitute it into the stated conditions, and check "
            "whether they hold. Count the candidates tested."
        ),
    },
    {
        "id": "work_backwards",
        "name": "Work backwards",
        "definition": (
            "Start from the required result and reverse the stated steps to find what the "
            "inputs must be."
        ),
    },
    {
        "id": "look_for_pattern",
        "name": "Look for a pattern",
        "definition": (
            "Compute the quantity for simple cases, look for a rule, then test that rule on "
            "the actual case."
        ),
    },
    {
        "id": "special_cases",
        "name": "Examine special cases",
        "definition": (
            "Try an extreme or simple value (zero, equal values, one unit) to see what the "
            "situation requires."
        ),
    },
    {
        "id": "simpler_problem",
        "name": "Solve a simpler related problem",
        "definition": (
            "Solve a version with fewer items or simpler numbers, then extend the same reasoning."
        ),
    },
    {
        "id": "table_or_diagram",
        "name": "Make a table or diagram",
        "definition": "Organise the givens in a table or sketch, then read off the relationships.",
    },
)
TOOLKIT_IDS = frozenset(item["id"] for item in TOOLKIT)
TOOLKIT_SHA256 = hashlib.sha256(json.dumps(TOOLKIT, sort_keys=True).encode()).hexdigest()
SUPPORTED = frozenset({"target_limit", "unrelated_shortfall", "meets_demands", "unresolved"})
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Chat = Callable[[list[dict[str, str]]], LLMResponse]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Attempt(Strict):
    idea: Text
    method_kind: Literal["structured", "checked_trial", "unchecked_trial"]
    trial_count: Annotated[int, Field(ge=0, le=500)] | None = None
    toolkit_used: list[str] = Field(default_factory=list, max_length=6)
    work: Text

    @model_validator(mode="after")
    def check_trial_fields(self) -> Attempt:
        if self.method_kind == "checked_trial" and not self.trial_count:
            raise ValueError("A checked trial must state how many candidates it tested")
        if any(item not in TOOLKIT_IDS for item in self.toolkit_used):
            raise ValueError("toolkit_used contains an unknown toolkit id")
        return self


class SolverReply(Strict):
    assumptions: list[Text] = Field(default_factory=list, max_length=6)
    attempts: list[Attempt] = Field(min_length=1, max_length=4)


class TextJudgment(Strict):
    verdict: Literal["yes", "partly", "no", "unclear"]
    quotes: list[Text]
    reason: Text


class Validity(Strict):
    verdict: Literal["yes", "no", "unclear"]
    assumptions: list[Text] = Field(default_factory=list, max_length=6)
    reading_dependence: Literal["none", "stated_choice", "unstated_choice"]
    reason: Text

    @model_validator(mode="after")
    def stated_choice_needs_assumption(self) -> Validity:
        if self.reading_dependence == "stated_choice" and not self.assumptions:
            raise ValueError("A stated choice must name the assumption used")
        return self


class Audit(Strict):
    status: Literal[
        "not_supported",
        "start_unresolved",
        "target_limit",
        "unrelated_shortfall",
        "meets_demands",
        "unresolved",
    ]
    reason: Text


class Check(Strict):
    purpose: Text
    values: dict[str, JsonValue] = Field(default_factory=dict)
    expressions: dict[str, Text]
    predicate: Text
    symbols: dict[str, Literal["real", "integer", "positive", "nonnegative"]] = Field(
        default_factory=dict
    )


def prompts() -> dict:
    source = PROMPT_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.2 prompt changed; use a new instrument version")
    if TOOLKIT_SHA256 != FROZEN_TOOLKIT_SHA256:
        raise ValueError("Frozen v2.2 toolkit changed; use a new instrument version")
    spec = yaml.safe_load(source)
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.2 prompt version")
    return spec


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def toolkit_block() -> str:
    lines = [f"- {item['name']} ({item['id']}): {item['definition']}" for item in TOOLKIT]
    return "Shared basic toolkit (applies to every task):\n" + "\n".join(lines)


def system(role: str, *, toolkit: bool = True) -> str:
    spec = prompts()
    if role not in {"solver", "task_judge", "attempt_judge"}:
        raise ValueError(f"Unknown role: {role}")
    if role == "solver":
        note = (
            spec["solver_toolkit_intro"] + "\n" + toolkit_block()
            if toolkit
            else spec["solver_control_note"]
        )
        return "\n\n".join(
            [
                spec["common"],
                spec["solver"],
                note,
                "Return JSON only, matching this schema:\n"
                + json.dumps(SolverReply.model_json_schema()),
            ]
        )
    if role == "task_judge":
        contract = (
            '{"action":"final","alignment":<TextJudgment>,"invention":<TextJudgment>,'
            '"validity":<Validity or null>}'
        )
        schemas = {
            "TextJudgment": TextJudgment.model_json_schema(),
            "Validity": Validity.model_json_schema(),
        }
    else:
        contract = (
            '{"action":"final","attempts":[<Audit per attempt, same order>],'
            '"inaccessible_because":<string or null>}'
        )
        schemas = {"Audit": Audit.model_json_schema()}
    return "\n\n".join(
        [
            spec["common"],
            spec[role],
            spec["calculator"],
            "Final contract:\n" + contract,
            json.dumps(schemas),
            'Calculator contract: {"action":"calculate","checks":[<Check>]}',
            json.dumps(Check.model_json_schema()),
        ]
    )


def role_input(role: str, prepared: dict, attempts: list[dict] | None = None) -> dict:
    payload = {
        "student_task": prepared["student_task"],
        "learner_context": prepared["learner_context"],
    }
    if role != "solver":
        payload["learning_target"] = prepared["learning_target"]
    if role == "attempt_judge":
        if attempts is None:
            raise ValueError("Attempt judge requires frozen attempts")
        payload["attempts"] = attempts
    return payload


def _row(value, status, evidence=None, error=None) -> dict:
    return {"value": value, "status": status, "evidence": evidence, "error": error}


def _text(raw, task: str) -> dict:
    judgment = TextJudgment.model_validate(raw)
    if judgment.verdict != "unclear" and not judgment.quotes:
        raise ValueError("A substantive text judgment requires an exact task quote")
    if any(quote not in task for quote in judgment.quotes):
        raise ValueError("A quotation is not an exact substring of the saved task")
    return _row(judgment.verdict, "assessed", judgment.model_dump())


def parse_task_v22(raw: dict, payload: dict) -> dict:
    rows = {}
    for field, measure in (("alignment", "target_alignment"), ("invention", "room_for_invention")):
        try:
            rows[measure] = _text(raw.get(field), payload["student_task"])
        except (ValidationError, ValueError) as exc:
            rows[measure] = _row(None, "invalid_response", raw.get(field), str(exc))
    if payload["learning_target"] is None:
        rows["target_alignment"] = _row(
            "unclear", "assessed", {"reason": "No saved intended target is available"}
        )
    alignment = rows["target_alignment"]
    if alignment["status"] != "assessed" or alignment["value"] != "yes":
        rows["mathematical_validity"] = _row(
            "not_assessed",
            "not_assessed",
            {
                "prerequisite_value": alignment["value"],
                "prerequisite_status": alignment["status"],
            },
        )
        return rows
    try:
        validity = Validity.model_validate(raw.get("validity"))
    except (ValidationError, ValueError) as exc:
        rows["mathematical_validity"] = _row(
            None, "invalid_response", raw.get("validity"), str(exc)
        )
        return rows
    value, evidence = validity.verdict, validity.model_dump()
    if validity.verdict == "yes" and validity.reading_dependence == "unstated_choice":
        value = "unclear"
        evidence = {**evidence, "raw_verdict": "yes", "rule": "unstated_choice_cannot_support_yes"}
    rows["mathematical_validity"] = _row(value, "assessed", evidence)
    return rows


def parse_attempts_v22(raw: dict, attempts: list[dict]) -> dict:
    reviews = raw.get("attempts")
    if not isinstance(reviews, list) or len(reviews) != len(attempts):
        raise ValueError("Judge must review every solver attempt, in the same order")
    audited, errors = [], []
    for index, (review, attempt) in enumerate(zip(reviews, attempts, strict=True)):
        try:
            item = Audit.model_validate(review).model_dump()
        except (ValidationError, ValueError) as exc:
            errors.append({"index": index, "error": str(exc)})
            item = {"status": "start_unresolved", "reason": f"Invalid audit: {exc}"}
        if attempt["method_kind"] == "unchecked_trial" and item["status"] in SUPPORTED:
            item = {
                "status": "not_supported",
                "reason": "Unchecked trial: no stated check, so it is not a method.",
                "raw_status": item["status"],
            }
        audited.append(item)
    obstruction = raw.get("inaccessible_because")
    if obstruction is not None and (not isinstance(obstruction, str) or not obstruction.strip()):
        errors.append({"field": "inaccessible_because", "error": "Requires nonempty text or null"})
        obstruction = None
    statuses = [item["status"] for item in audited]
    supported = sum(status in SUPPORTED for status in statuses)
    unknown_starts = statuses.count("start_unresolved")
    if supported:
        accessibility = "yes"
    elif obstruction and not unknown_starts:
        accessibility = "no"
    else:
        accessibility = "unclear"
    if accessibility != "yes":
        limits = "not_assessed"
    elif "target_limit" in statuses:
        limits = "yes"
    elif errors or unknown_starts or "unresolved" in statuses:
        limits = "unclear"
    else:
        limits = "no"
    counts = Counter(statuses)
    checked = [a for a in attempts if a["method_kind"] == "checked_trial"]
    evidence = {
        "attempts": audited,
        "inaccessible_because": obstruction,
        "validation_errors": errors,
    }
    return {
        "measures": {
            "prior_knowledge_accessibility": _row(accessibility, "assessed", evidence),
            "familiar_approach_limits": _row(
                limits, "not_assessed" if limits == "not_assessed" else "assessed", evidence
            ),
        },
        "counts": {
            "attempts_produced": len(attempts),
            "supported_starts": supported,
            "target_limits": counts["target_limit"],
            "meets_demands": counts["meets_demands"],
            "unrelated_shortfalls": counts["unrelated_shortfall"],
            "unresolved": counts["unresolved"] + unknown_starts,
            "not_supported": counts["not_supported"],
            "checked_trial_attempts": len(checked),
            "unchecked_trial_attempts": sum(
                a["method_kind"] == "unchecked_trial" for a in attempts
            ),
            "candidates_tested_in_checked_trials": sum(a.get("trial_count") or 0 for a in checked),
            "scope": "Model-identified methods, not student frequencies or exhaustive coverage.",
        },
    }


def _failure(record: dict, status: str, exc: Exception) -> dict:
    logger.error("%s %s: %s", record["role"], status, exc)
    record.update({"status": status, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return record


def run_role(
    role: str,
    payload: dict,
    chat: Chat,
    *,
    toolkit: bool = True,
    max_calls: int = 3,
    max_checks: int = 16,
    system_text: str | None = None,
) -> dict:
    expected = {"student_task", "learner_context"}
    if role != "solver":
        expected.add("learning_target")
    if role == "attempt_judge":
        expected.add("attempts")
    if set(payload) != expected:
        raise ValueError(f"{role} input contains unallowlisted fields")
    if not 1 <= max_calls <= 3 or not 1 <= max_checks <= 16:
        raise ValueError("Execution limits must be 1-3 calls and 1-16 calculator checks")
    budget = 1 if role == "solver" else max_calls
    messages = [
        {
            "role": "system",
            "content": system_text if system_text is not None else system(role, toolkit=toolkit),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": role,
        "version": VERSION,
        "prompt_sha256": fingerprint(),
        "toolkit_allowed": toolkit if role == "solver" else None,
        "input": payload,
        "status": "starting",
        "output": None,
        "calls": [],
        "calculations": [],
        "schema_repairs": [],
        "error": None,
    }
    frozen_text = None
    for number in range(budget):
        call = {"messages": [dict(item) for item in messages], "response": None}
        record["calls"].append(call)
        try:
            response = chat(messages)
        except (OpenAIError, ConnectionError, TimeoutError) as exc:
            return _failure(record, "api_error", exc)
        call["response"] = {
            "text": response.text,
            "model": response.model,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }
        if response.finish_reason == "length":
            return _failure(record, "truncated", ValueError("Completion budget exhausted"))
        if response.finish_reason not in {"", "stop"}:
            return _failure(record, "invalid_response", ValueError("Unusable finish reason"))
        try:
            raw = json.loads(response.text)
            if not isinstance(raw, dict):
                raise ValueError("Response must be a JSON object")
            if role == "solver":
                reply = SolverReply.model_validate(raw)
                if not toolkit and any(item.toolkit_used for item in reply.attempts):
                    raise ValueError("Toolkit use is not allowed in the control arm")
                record["output"] = reply.model_dump()
            elif raw.get("action") == "calculate":
                checks = raw.get("checks")
                if not isinstance(checks, list) or not checks:
                    raise ValueError("Calculator request requires nonempty checks")
                if len(record["calculations"]) + len(checks) > max_checks:
                    return _failure(record, "budget_exhausted", ValueError("Check budget exceeded"))
                results = []
                for item in checks:
                    check = Check.model_validate(item)
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
                                    "remaining_model_calls": budget - number - 1,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ]
                )
                continue
            elif raw.get("action") == "final":
                if (
                    role == "task_judge"
                    and raw.get("validity") is None
                    and payload["learning_target"] is not None
                    and number + 1 < budget
                ):
                    try:
                        alignment = _text(raw.get("alignment"), payload["student_task"])
                    except (ValidationError, ValueError):
                        alignment = None
                    if alignment is not None and alignment["value"] == "yes":
                        frozen_text = frozen_text or {
                            "alignment": raw["alignment"],
                            "invention": raw.get("invention"),
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
                                        "Complete the validity object only. Keep alignment and "
                                        "invention unchanged. You may request calculations first. "
                                        f"Remaining calls: {budget - number - 1}."
                                    ),
                                },
                            ]
                        )
                        continue
                if frozen_text is not None:
                    raw.update(frozen_text)
                record["output"] = raw
            else:
                raise ValueError("Judge requires action=calculate or action=final")
        except (ValueError, ValidationError) as exc:
            return _failure(record, "invalid_response", exc)
        record["status"] = "completed"
        return record
    return _failure(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def assemble_v22(
    prepared: dict, solver: dict, task: dict, attempt: dict | None, *, toolkit: bool
) -> dict:
    if task["status"] == "completed":
        rows = parse_task_v22(task["output"], prepared)
    else:
        rows = {
            name: _row(None, task["status"], error=task["error"])
            for name in ("target_alignment", "room_for_invention")
        }
        rows["mathematical_validity"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_status": task["status"]}
        )
    counts = None
    history = prepared["learner_context"].get("assumed_prior_knowledge")
    if not history:
        rows["prior_knowledge_accessibility"] = _row(
            "unclear", "assessed", {"reason": "No usable saved prerequisite history"}
        )
        rows["familiar_approach_limits"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_value": "unclear"}
        )
    elif solver["status"] != "completed":
        rows["prior_knowledge_accessibility"] = _row(
            None, solver["status"], error=solver.get("error")
        )
        rows["familiar_approach_limits"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_status": solver["status"]}
        )
    elif attempt is None or attempt["status"] != "completed":
        status = attempt["status"] if attempt else "not_run"
        rows["prior_knowledge_accessibility"] = _row(
            None, status, error=attempt["error"] if attempt else None
        )
        rows["familiar_approach_limits"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_status": status}
        )
    else:
        try:
            parsed = parse_attempts_v22(attempt["output"], solver["output"]["attempts"])
        except (ValueError, ValidationError) as exc:
            rows["prior_knowledge_accessibility"] = _row(None, "invalid_response", error=str(exc))
            rows["familiar_approach_limits"] = _row(
                "not_assessed", "not_assessed", {"prerequisite_status": "invalid_response"}
            )
        else:
            rows.update(parsed["measures"])
            counts = parsed["counts"]
    return {
        "version": VERSION,
        "arm": "toolkit" if toolkit else "no_toolkit",
        "toolkit_sha256": TOOLKIT_SHA256,
        "prompt_sha256": fingerprint(),
        "measures": {name: rows[name] for name in MEASURES},
        "approach_counts": counts,
        "solver": solver,
        "task_judge": task,
        "attempt_judge": attempt,
    }


def evaluate_v22(
    task: str | dict,
    target: str | None,
    context: dict,
    *,
    solver_chat: Chat,
    judge_chat: Chat,
    toolkit: bool = True,
) -> dict:
    prepared = prepare_input(task, target, context)
    task_result = run_role("task_judge", role_input("task_judge", prepared), judge_chat)
    history = prepared["learner_context"].get("assumed_prior_knowledge")
    if history:
        solver = run_role("solver", role_input("solver", prepared), solver_chat, toolkit=toolkit)
    else:
        solver = {"status": "input_unavailable", "error": None, "calls": [], "output": None}
    attempt = None
    if solver["status"] == "completed":
        attempt = run_role(
            "attempt_judge",
            role_input("attempt_judge", prepared, solver["output"]["attempts"]),
            judge_chat,
        )
    return assemble_v22(prepared, solver, task_result, attempt, toolkit=toolkit)
