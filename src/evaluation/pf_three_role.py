"""Minimal three-role PF instrument with preserved field-local execution failures."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Annotated, Callable, Literal

import yaml
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, ValidationError

from src.evaluation.pf_evidence_audit import student_text
from src.evaluation.pf_task_measures import MEASURES, _prepare_context
from src.evaluation.pf_task_measures import prepare_input as _v1_prepare
from src.generation.design_calculator import calculate_condition
from src.utils.llm_client import LLMResponse

logger = logging.getLogger(__name__)
VERSION = "pf-three-role/v2.1"
EXECUTION_VERSION = "pf-three-role-runtime/v1.1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2.yaml"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Chat = Callable[[list[dict[str, str]]], LLMResponse]
SUPPORTED = {"target_limit", "unrelated_shortfall", "meets_demands", "unresolved"}


def prepare_input(task: str | dict, target: str | None, context: dict) -> dict:
    if not isinstance(context, dict):
        raise ValueError("Learner context must be an object")
    resources = context.get("assumed_prior_knowledge")
    if isinstance(resources, list) and any(isinstance(item, str) for item in resources):
        if not all(isinstance(item, (str, dict)) for item in resources):
            raise ValueError("Prior resources must be text descriptions or objects")
        context = {
            **context,
            "assumed_prior_knowledge": [
                {"resource": item, "taught_as": item} if isinstance(item, str) else item
                for item in resources
            ],
        }
        logger.info("Preserved frozen textual prior resources as resource/taught_as objects")
    if target is not None:
        return _v1_prepare(task, target, context)
    if isinstance(task, str):
        if not task.strip():
            raise ValueError("student_task must be nonempty text")
        text = task
    else:
        text = student_text(task)
    return {
        "student_task": text,
        "learning_target": None,
        "learner_context": _prepare_context(context),
    }


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Attempt(Strict):
    idea: Text
    work: Text


class SolverReply(Strict):
    attempts: Annotated[list[Attempt], Field(max_length=4)]


class TextJudgment(Strict):
    verdict: Literal["yes", "partly", "no", "unclear"]
    quotes: list[Text]
    reason: Text


class Validity(Strict):
    verdict: Literal["yes", "no", "unclear"]
    reason: Text


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
    values: dict[str, JsonValue]
    expressions: dict[str, Text]
    predicate: Text
    symbols: dict[str, Literal["real", "integer", "positive", "nonnegative"]] = Field(
        default_factory=dict
    )


def prompts() -> dict:
    source = yaml.safe_load(PROMPT_PATH.read_text())
    if source.get("version") != "pf-three-role/v2":
        raise ValueError("Unexpected three-role instrument version")
    return source


def fingerprint() -> str:
    clarification = Path(__file__).parent / "prompts" / "pf_three_role_v2_1.yaml"
    return hashlib.sha256(PROMPT_PATH.read_bytes() + clarification.read_bytes()).hexdigest()


def system(role: str) -> str:
    spec = prompts()
    revision = yaml.safe_load(
        (Path(__file__).parent / "prompts" / "pf_three_role_v2_1.yaml").read_text()
    )
    if role not in {"solver", "task_judge", "attempt_judge"}:
        raise ValueError(f"Unknown role: {role}")
    if role == "solver":
        return (
            spec[role]
            + "\n"
            + revision[role]
            + "\nReturn JSON only, matching this schema:\n"
            + json.dumps(SolverReply.model_json_schema())
        )
    if role == "task_judge":
        contract = (
            '{"action":"final","alignment":<TextJudgment>,'
            '"invention":<TextJudgment>,"validity":<Validity or null>}'
        )
        schemas = {
            "TextJudgment": TextJudgment.model_json_schema(),
            "Validity": Validity.model_json_schema(),
        }
    else:
        contract = (
            '{"action":"final","attempts":[<Audit for each supplied attempt>],'
            '"inaccessible_because":<string or null>}'
        )
        schemas = {"Audit": Audit.model_json_schema()}
    return "\n\n".join(
        [
            spec["common"],
            spec[role],
            revision[role],
            spec["calculator"],
            revision["calculator"],
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


def _row(value: str | None, status: str, evidence=None, error=None) -> dict:
    return {"value": value, "status": status, "evidence": evidence, "error": error}


def _parse_text(raw: object, task: str) -> dict:
    judgment = TextJudgment.model_validate(raw)
    if judgment.verdict != "unclear" and not judgment.quotes:
        raise ValueError("A substantive text judgment requires an exact task quote")
    if any(quote not in task for quote in judgment.quotes):
        raise ValueError("A quotation is not an exact substring of the saved task")
    return _row(judgment.verdict, "assessed", judgment.model_dump())


def parse_task(raw: dict, payload: dict) -> dict:
    result = {}
    for field, measure in [("alignment", "target_alignment"), ("invention", "room_for_invention")]:
        try:
            result[measure] = _parse_text(raw.get(field), payload["student_task"])
        except (ValidationError, ValueError) as exc:
            logger.error("Task-judge %s invalid: %s", field, exc)
            result[measure] = _row(None, "invalid_response", raw.get(field), str(exc))
    if payload["learning_target"] is None:
        result["target_alignment"] = _row(
            "unclear", "assessed", {"reason": "No saved intended target is available"}
        )
    alignment = result["target_alignment"]
    if alignment["status"] != "assessed" or alignment["value"] != "yes":
        result["mathematical_validity"] = _row(
            "not_assessed",
            "not_assessed",
            {"prerequisite_value": alignment["value"], "prerequisite_status": alignment["status"]},
        )
    else:
        try:
            valid = Validity.model_validate(raw.get("validity"))
            result["mathematical_validity"] = _row(valid.verdict, "assessed", valid.model_dump())
        except (ValidationError, ValueError) as exc:
            logger.error("Task-judge validity invalid: %s", exc)
            result["mathematical_validity"] = _row(
                None, "invalid_response", raw.get("validity"), str(exc)
            )
    return result


def parse_attempts(raw: dict, attempts: list[dict]) -> dict:
    reviews = raw.get("attempts")
    if not isinstance(reviews, list) or len(reviews) != len(attempts):
        raise ValueError("Judge must review every solver attempt, in the same order")
    audited, errors = [], []
    for index, review in enumerate(reviews):
        try:
            audited.append(Audit.model_validate(review).model_dump())
        except (ValidationError, ValueError) as exc:
            errors.append({"index": index, "error": str(exc), "raw": review})
            audited.append({"status": "start_unresolved", "reason": f"Invalid audit: {exc}"})
    obstruction = raw.get("inaccessible_because")
    if obstruction is not None and (not isinstance(obstruction, str) or not obstruction.strip()):
        errors.append({"field": "inaccessible_because", "error": "Requires nonempty text or null"})
        obstruction = None
    supported = sum(item["status"] in SUPPORTED for item in audited)
    unknown_starts = sum(item["status"] == "start_unresolved" for item in audited)
    accessibility = (
        "yes" if supported else "no" if obstruction and not unknown_starts else "unclear"
    )
    limits = (
        "not_assessed"
        if accessibility != "yes"
        else "yes"
        if any(item["status"] == "target_limit" for item in audited)
        else "unclear"
        if errors or unknown_starts or any(item["status"] == "unresolved" for item in audited)
        else "no"
    )
    counts = dict(Counter(item["status"] for item in audited))
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
            "reviewed_supported": supported,
            "target_limits": counts.get("target_limit", 0),
            "meets_demands": counts.get("meets_demands", 0),
            "unrelated_shortfalls": counts.get("unrelated_shortfall", 0),
            "unresolved": counts.get("unresolved", 0) + unknown_starts,
            "not_supported": counts.get("not_supported", 0),
            "scope": "Model-identified methods, not student frequencies or exhaustive coverage.",
        },
    }


def run_role(role: str, payload: dict, chat: Chat, *, max_calls=3, max_checks=16) -> dict:
    expected = {"student_task", "learner_context"}
    if role != "solver":
        expected.add("learning_target")
    if role == "attempt_judge":
        expected.add("attempts")
    if set(payload) != expected:
        raise ValueError(f"{role} input contains unallowlisted fields")
    if not 1 <= max_calls <= 3 or not 1 <= max_checks <= 16:
        raise ValueError("Execution limits must be 1-3 calls and 1-16 calculator checks")
    messages = [
        {"role": "system", "content": system(role)},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    record = {
        "role": role,
        "version": VERSION,
        "prompt_sha256": fingerprint(),
        "input": payload,
        "status": "starting",
        "output": None,
        "calls": [],
        "calculations": [],
        "error": None,
        "execution_version": EXECUTION_VERSION,
        "schema_repairs": [],
    }
    frozen_text_findings = None
    budget = 1 if role == "solver" else max_calls
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
                record["output"] = SolverReply.model_validate(raw).model_dump()
            elif raw.get("action") == "calculate":
                checks = raw.get("checks")
                if not isinstance(checks, list) or not checks:
                    raise ValueError("Calculator request requires nonempty checks")
                if len(record["calculations"]) + len(checks) > max_checks:
                    return _failure(record, "budget_exhausted", ValueError("Check budget exceeded"))
                checked = [Check.model_validate(item) for item in checks]
                results = []
                for check in checked:
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
                    if calc["status"] in {"unsupported", "unknown"}:
                        logger.warning("%s calculator: %s", role, calc["reason"])
                messages.extend(
                    [
                        {"role": "assistant", "content": response.text},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "calculator_results": results,
                                    "remaining_model_calls": budget - number - 1,
                                    "instruction": "Finalize if only one model call remains.",
                                }
                            ),
                        },
                    ]
                )
                continue
            elif raw.get("action") == "final":
                if role == "task_judge" and raw.get("validity") is None:
                    try:
                        alignment = _parse_text(raw.get("alignment"), payload["student_task"])
                    except (ValueError, ValidationError):
                        alignment = None
                    if (
                        payload["learning_target"] is not None
                        and alignment is not None
                        and alignment["value"] == "yes"
                        and number + 1 < budget
                    ):
                        if frozen_text_findings is None:
                            frozen_text_findings = {
                                "alignment": raw["alignment"],
                                "invention": raw.get("invention"),
                            }
                        record["schema_repairs"].append(
                            {
                                "call": number,
                                "reason": "Aligned final reply omitted required validity",
                            }
                        )
                        messages.extend(
                            [
                                {"role": "assistant", "content": response.text},
                                {
                                    "role": "user",
                                    "content": (
                                        "Your alignment is yes, so validity cannot be null. "
                                        "Complete the required validity object "
                                        "(yes/no/unclear plus mathematical reason). "
                                        "Keep alignment and invention unchanged; "
                                        "this is schema completion, not a request for a "
                                        "positive verdict. You may request calculations "
                                        f"first. Remaining calls: {budget - number - 1}."
                                    ),
                                },
                            ]
                        )
                        continue
                if frozen_text_findings is not None:
                    raw.update(frozen_text_findings)
                record["output"] = raw
            else:
                raise ValueError("Judge requires action=calculate or action=final")
        except (ValueError, ValidationError) as exc:
            return _failure(record, "invalid_response", exc)
        record["status"] = "completed"
        return record
    return _failure(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def _failure(record: dict, status: str, exc: Exception) -> dict:
    logger.error("%s %s: %s", record["role"], status, exc)
    record.update({"status": status, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return record


def assemble(prepared: dict, solver: dict, task: dict, attempt: dict | None) -> dict:
    if task["status"] == "completed":
        rows = parse_task(task["output"], prepared)
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
    elif solver["status"] != "completed" or attempt is None:
        rows["prior_knowledge_accessibility"] = _row(
            None, solver["status"], error=solver.get("error")
        )
        rows["familiar_approach_limits"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_status": solver["status"]}
        )
    elif attempt["status"] != "completed":
        rows["prior_knowledge_accessibility"] = _row(
            None, attempt["status"], error=attempt["error"]
        )
        rows["familiar_approach_limits"] = _row(
            "not_assessed", "not_assessed", {"prerequisite_status": attempt["status"]}
        )
    else:
        try:
            parsed = parse_attempts(attempt["output"], solver["output"]["attempts"])
            rows.update(parsed["measures"])
            counts = parsed["counts"]
        except (ValueError, ValidationError) as exc:
            logger.error("Attempt-review parse error: %s", exc)
            rows["prior_knowledge_accessibility"] = _row(None, "invalid_response", error=str(exc))
            rows["familiar_approach_limits"] = _row(
                "not_assessed", "not_assessed", {"prerequisite_status": "invalid_response"}
            )
    return {
        "version": VERSION,
        "execution_version": EXECUTION_VERSION,
        "prompt_sha256": fingerprint(),
        "measures": {name: rows[name] for name in MEASURES},
        "approach_counts": counts,
        "solver": solver,
        "task_judge": task,
        "attempt_judge": attempt,
    }


def evaluate(task: str, target: str, context: dict, solver_chat: Chat, judge_chat: Chat) -> dict:
    prepared = prepare_input(task, target, context)
    task_result = run_role("task_judge", role_input("task_judge", prepared), judge_chat)
    if prepared["learner_context"].get("assumed_prior_knowledge"):
        solver = run_role("solver", role_input("solver", prepared), solver_chat)
    else:
        solver = {"status": "input_unavailable", "error": None, "calls": [], "output": None}
    attempt = None
    if solver["status"] == "completed":
        attempt = run_role(
            "attempt_judge",
            role_input("attempt_judge", prepared, solver["output"]["attempts"]),
            judge_chat,
        )
    return assemble(prepared, solver, task_result, attempt)
