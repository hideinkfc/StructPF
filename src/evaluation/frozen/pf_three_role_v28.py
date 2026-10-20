"""PF three-role v2.8: accessibility moved to the task judge as a task-level gate.

The task judge assesses target_alignment, room_for_invention, prior_knowledge_accessibility,
and (when target_alignment is yes) mathematical_validity, using a top-level FinalTaskReply
schema that requires action="final". Solvers and the attempt judge run only when
prior_knowledge_accessibility is yes, to assess familiar_approach_limits.
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
from pydantic import Field, ValidationError

from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.evaluation.pf_task_measures import MEASURES
from src.generation.design_calculator import calculate_condition

logger = logging.getLogger(__name__)

VERSION = "pf-three-role/v2.8"
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "pf_three_role_v2_8.yaml"
FROZEN_PROMPT_SHA256 = "6c771460d2fbe82df65f1652e966640a1db896e5486bc8cae3a39a783acec44e"
FROZEN_TASK_SYSTEM_SHA256 = "2913ac8cfe8f9d617ed068fc882a217662d6c8463aa1cbe83e608aef60951f21"
FROZEN_ATTEMPT_SYSTEM_SHA256 = "b73dbb076bec2c21fb460e06804d2d45c81dbd07e2c42aaafb2e555eb629f976"


class AccessibilityJudgment(v22.Strict):
    verdict: Literal["yes", "no", "unclear"]
    quotes: list[v22.Text]
    reason: v22.Text


class FinalTaskReply(v22.Strict):
    action: Literal["final"]
    alignment: v22.TextJudgment
    invention: v22.TextJudgment
    accessibility: AccessibilityJudgment
    validity: v22.Validity | None = None


class FinalAttemptReply(v22.Strict):
    action: Literal["final"]
    attempts: list[v22.Audit]


class JudgeCalc(v22.Strict):
    action: Literal["calculate"]
    checks: list[v22.Check] = Field(min_length=1)


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.8 prompt version")
    return spec


def prompts() -> dict:
    if hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.8 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def _compose_task_system(spec: dict) -> str:
    base = v22.prompts()
    return "\n\n".join(
        [
            base["common"],
            spec["task_judge"],
            base["calculator"],
            "Final answer schema (reply with this exact shape, action included):\n"
            + json.dumps(FinalTaskReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(JudgeCalc.model_json_schema()),
        ]
    )


def _compose_attempt_system(spec: dict) -> str:
    base = v22.prompts()
    return "\n\n".join(
        [
            base["common"],
            spec["attempt_judge"],
            base["calculator"],
            "Final answer schema (reply with this exact shape, action included):\n"
            + json.dumps(FinalAttemptReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(JudgeCalc.model_json_schema()),
        ]
    )


def task_system() -> str:
    text = _compose_task_system(prompts())
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_TASK_SYSTEM_SHA256:
        raise ValueError("Frozen v2.8 task system changed; use a new instrument version")
    return text


def attempt_system() -> str:
    text = _compose_attempt_system(prompts())
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_ATTEMPT_SYSTEM_SHA256:
        raise ValueError("Frozen v2.8 attempt system changed; use a new instrument version")
    return text


def task_system_sha256() -> str:
    return hashlib.sha256(_compose_task_system(_spec()).encode("utf-8")).hexdigest()


def attempt_system_sha256() -> str:
    return hashlib.sha256(_compose_attempt_system(_spec()).encode("utf-8")).hexdigest()


def _text_v28(raw, task: str) -> dict:
    judgment = v22.TextJudgment.model_validate(raw)
    matched = [quote for quote in judgment.quotes if quote in task]
    if judgment.verdict != "unclear" and not matched:
        raise ValueError("A substantive text judgment requires an exact task quote")
    data = judgment.model_dump()
    unmatched = [quote for quote in judgment.quotes if quote not in task]
    if unmatched:
        data["quotes"] = matched
        data["unmatched_task_quotes"] = unmatched
    return v22._row(judgment.verdict, "assessed", data)


def _accessibility(raw, task: str) -> dict:
    judgment = AccessibilityJudgment.model_validate(raw)
    data = judgment.model_dump()
    unmatched = [quote for quote in judgment.quotes if quote not in task]
    if unmatched:
        data["unmatched_task_quotes"] = unmatched
    return v22._row(judgment.verdict, "assessed", data)


def parse_task_v28(raw: dict, payload: dict) -> dict:
    rows = {}
    for field, measure in (("alignment", "target_alignment"), ("invention", "room_for_invention")):
        try:
            rows[measure] = _text_v28(raw.get(field), payload["student_task"])
        except (ValidationError, ValueError) as exc:
            rows[measure] = v22._row(None, "invalid_response", raw.get(field), str(exc))
    if payload["learning_target"] is None:
        rows["target_alignment"] = v22._row(
            "unclear", "assessed", {"reason": "No saved intended target is available"}
        )
    history = payload["learner_context"].get("assumed_prior_knowledge")
    if not history:
        rows["prior_knowledge_accessibility"] = v22._row(
            "unclear", "assessed", {"reason": "No usable saved prerequisite history"}
        )
    else:
        try:
            rows["prior_knowledge_accessibility"] = _accessibility(
                raw.get("accessibility"), payload["student_task"]
            )
        except (ValidationError, ValueError) as exc:
            rows["prior_knowledge_accessibility"] = v22._row(
                None, "invalid_response", raw.get("accessibility"), str(exc)
            )
    alignment = rows["target_alignment"]
    if alignment["status"] != "assessed" or alignment["value"] != "yes":
        rows["mathematical_validity"] = v22._row(
            "not_assessed",
            "not_assessed",
            {
                "prerequisite_value": alignment["value"],
                "prerequisite_status": alignment["status"],
            },
        )
        return rows
    try:
        validity = v22.Validity.model_validate(raw.get("validity"))
    except (ValidationError, ValueError) as exc:
        rows["mathematical_validity"] = v22._row(
            None, "invalid_response", raw.get("validity"), str(exc)
        )
        return rows
    value, evidence = validity.verdict, validity.model_dump()
    if validity.verdict == "yes" and validity.reading_dependence == "unstated_choice":
        value = "unclear"
        evidence = {**evidence, "raw_verdict": "yes", "rule": "unstated_choice_cannot_support_yes"}
    rows["mathematical_validity"] = v22._row(value, "assessed", evidence)
    return rows


def parse_attempts_v28(raw: dict, attempts: list[dict]) -> dict:
    reviews = raw.get("attempts")
    if not isinstance(reviews, list) or len(reviews) != len(attempts):
        raise ValueError("Judge must review every solver attempt, in the same order")
    audited, errors = [], []
    for index, (review, attempt) in enumerate(zip(reviews, attempts, strict=True)):
        try:
            item = v22.Audit.model_validate(review).model_dump()
        except (ValidationError, ValueError) as exc:
            errors.append({"index": index, "error": str(exc)})
            item = {"status": "start_unresolved", "reason": f"Invalid audit: {exc}"}
        if attempt["method_kind"] == "unchecked_trial" and item["status"] in v22.SUPPORTED:
            item = {
                "status": "not_supported",
                "reason": "Unchecked trial: no stated check, so it is not a method.",
                "raw_status": item["status"],
            }
        audited.append(item)
    statuses = [item["status"] for item in audited]
    supported = sum(status in v22.SUPPORTED for status in statuses)
    unknown_starts = statuses.count("start_unresolved")
    if "target_limit" in statuses:
        limits = "yes"
    elif errors or unknown_starts or "unresolved" in statuses:
        limits = "unclear"
    else:
        limits = "no"
    counts = Counter(statuses)
    checked = [a for a in attempts if a["method_kind"] == "checked_trial"]
    evidence = {"attempts": audited, "validation_errors": errors}
    return {
        "measures": {
            "familiar_approach_limits": v22._row(limits, "assessed", evidence),
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


def run_judge_v28(
    role: Literal["task_judge", "attempt_judge"],
    payload: dict,
    chat: v22.Chat,
    *,
    max_calls: int = 3,
    max_checks: int = 16,
) -> dict:
    expected = {"student_task", "learner_context", "learning_target"}
    if role == "attempt_judge":
        expected.add("attempts")
    if set(payload) != expected:
        raise ValueError(f"{role} input contains unallowlisted fields")
    if not 1 <= max_calls <= 3 or not 1 <= max_checks <= 16:
        raise ValueError("Execution limits must be 1-3 calls and 1-16 calculator checks")
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
                req = JudgeCalc.model_validate(raw)
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
                if (
                    role == "task_judge"
                    and raw.get("validity") is None
                    and payload["learning_target"] is not None
                    and number + 1 < max_calls
                ):
                    try:
                        alignment = _text_v28(raw.get("alignment"), payload["student_task"])
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


def assemble_v28(
    prepared: dict, solver: dict, task: dict, attempt: dict | None, *, toolkit: bool
) -> dict:
    if task["status"] == "completed":
        rows = parse_task_v28(task["output"], prepared)
    else:
        rows = {
            name: v22._row(None, task["status"], error=task["error"])
            for name in (
                "target_alignment",
                "room_for_invention",
                "prior_knowledge_accessibility",
            )
        }
        rows["mathematical_validity"] = v22._row(
            "not_assessed", "not_assessed", {"prerequisite_status": task["status"]}
        )
    counts = None
    access = rows["prior_knowledge_accessibility"]
    if access["status"] != "assessed" or access["value"] != "yes":
        rows["familiar_approach_limits"] = v22._row(
            "not_assessed",
            "not_assessed",
            {
                "prerequisite_value": access["value"],
                "prerequisite_status": access["status"],
            },
        )
    elif solver["status"] != "completed":
        rows["familiar_approach_limits"] = v22._row(
            None, solver["status"], error=solver.get("error")
        )
    elif attempt is None or attempt["status"] != "completed":
        status = attempt["status"] if attempt else "not_run"
        rows["familiar_approach_limits"] = v22._row(
            None, status, error=attempt["error"] if attempt else None
        )
    else:
        try:
            parsed = parse_attempts_v28(attempt["output"], solver["output"]["attempts"])
        except (ValueError, ValidationError) as exc:
            rows["familiar_approach_limits"] = v22._row(None, "invalid_response", error=str(exc))
        else:
            rows.update(parsed["measures"])
            counts = parsed["counts"]
    return {
        "version": VERSION,
        "arm": "toolkit" if toolkit else "no_toolkit",
        "toolkit_sha256": v22.TOOLKIT_SHA256,
        "prompt_sha256": fingerprint(),
        "measures": {name: rows[name] for name in MEASURES},
        "approach_counts": counts,
        "solver": solver,
        "task_judge": task,
        "attempt_judge": attempt,
    }


def evaluate_v28(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict,
    judge_chat: v22.Chat,
    toolkit: bool = True,
) -> dict:
    prepared = v25.prepare_input(task, target, context)
    task_result = run_judge_v28("task_judge", v22.role_input("task_judge", prepared), judge_chat)
    task_rows = (
        parse_task_v28(task_result["output"], prepared)
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
            solver_id: v25.run_solver_v25(
                v22.role_input("solver", prepared), chat, solver_id=solver_id, toolkit=toolkit
            )
            for solver_id, chat in solver_chats.items()
        }
        items = v25.combine_attempts(solver_runs)
        solver = v25._combined_solver(solver_runs, items)
        attempt = None
        if items:
            attempt = run_judge_v28(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                judge_chat,
            )
        principles = v25.principle_counts(solver_runs)
    result = assemble_v28(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
