"""PF three-role v3.0: literature-grounded strict definitions across all three roles.

Combines the v2.8 task-judge accessibility gate with:
1. Typography-tolerant substring quote verification (requiring >=1 verbatim quote from
   student_task and recording any extra unmatched quotes without dropping the verdict),
   plus bounded quote-repair within max_calls when zero quotes match.
2. Restored v2.1 alignment, invention, and validity safeguards (open PF design choices
   and normal word-problem scope are stated_choice/yes; unstated_choice maps to unclear,
   never no; explicit geometric side/attachment contradictions are no).
3. Two-tier solver (1-2 direct prior-resource baselines + 1-3 coordinated/constructed
   approaches, capped at 4 per solver) and strict attempt-judge separation between
   target_limit, unrelated_shortfall, meets_demands, unresolved, and not_supported.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from openai import OpenAIError
from pydantic import Field, ValidationError, model_validator

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v23 as v23
from src.evaluation import pf_three_role_v25 as v25
from src.evaluation import pf_three_role_v28 as v28
from src.evaluation.pf_task_measures import MEASURES
from src.generation.design_calculator import calculate_condition

logger = logging.getLogger(__name__)

VERSION = "pf-three-role/v3.0"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v3_0.yaml"
FROZEN_PROMPT_SHA256 = "a8d751982a07e5f5ffb55ecde765da2fe741c4aba240e9e1f6ebb85bc52f1c02"
FROZEN_TASK_SYSTEM_SHA256 = "001929e8a7609966d78f36477c73864d3dce1942a456e3a26df671dbd8750218"
FROZEN_ATTEMPT_SYSTEM_SHA256 = "2602370d3719275a1723be86e4bb168c5767a28ec9b85966d585b0ba42d26fdc"
FROZEN_SOLVER_SYSTEM_SHA256 = {
    "toolkit": "ec774953b29c021abd61b2dcd2cf6bc4b731ed7b60fdae7b9bae32d881661738",
    "no_toolkit": "2658e246b6cee52472d076637006316796a13ce627d45b062a023b9605195887",
}
MAX_APPROACHES_PER_SOLVER = 4


def _norm_quote(text: str) -> str:
    trans = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2015": "-",
            "\u2212": "-",
            "\u00a0": " ",
        }
    )
    return re.sub(r"\s+", " ", text.translate(trans)).strip()


def _quote_in_task(quote: str, task: str) -> bool:
    if quote in task:
        return True
    nq = _norm_quote(quote)
    nt = _norm_quote(task)
    return bool(nq) and nq in nt


class Approach(v22.Strict):
    idea: v22.Text
    principle: v22.Text
    method_kind: Literal["structured", "checked_trial", "unchecked_trial"]
    trial_count: int | None = Field(default=None, ge=0, le=500)
    toolkit_used: list[str] = Field(default_factory=list)
    work: v22.Text

    @model_validator(mode="after")
    def check_fields(self) -> Approach:
        if self.method_kind == "checked_trial" and not self.trial_count:
            self.method_kind = "unchecked_trial"
        self.toolkit_used = [item for item in self.toolkit_used if item in v22.TOOLKIT_IDS]
        return self


class FinalSolverReply(v22.Strict):
    action: Literal["final"]
    assumptions: list[v22.Text] = Field(default_factory=list)
    attempts: list[Approach] = Field(min_length=1, max_length=MAX_APPROACHES_PER_SOLVER)

    @model_validator(mode="before")
    @classmethod
    def cap_attempts(cls, data):
        if isinstance(data, dict) and isinstance(data.get("attempts"), list):
            if len(data["attempts"]) > MAX_APPROACHES_PER_SOLVER:
                data = {**data, "attempts": data["attempts"][:MAX_APPROACHES_PER_SOLVER]}
        return data


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v3.0 prompt version")
    return spec


def prompts() -> dict:
    if FROZEN_PROMPT_SHA256 and hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v3.0 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def _compose_task_system(spec: dict) -> str:
    return "\n\n".join(
        [
            spec["common"],
            spec["task_judge"],
            spec["calculator"],
            "Final answer schema (reply with this exact shape, action included):\n"
            + json.dumps(v28.FinalTaskReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(v28.JudgeCalc.model_json_schema()),
        ]
    )


def _compose_attempt_system(spec: dict) -> str:
    return "\n\n".join(
        [
            spec["common"],
            spec["attempt_judge"],
            spec["calculator"],
            "Final answer schema (reply with this exact shape, action included):\n"
            + json.dumps(v28.FinalAttemptReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(v28.JudgeCalc.model_json_schema()),
        ]
    )


def _compose_solver_system(spec: dict, *, toolkit: bool) -> str:
    note = (
        spec["solver_toolkit_intro"] + "\n" + v22.toolkit_block()
        if toolkit
        else spec["solver_control_note"]
    )
    return "\n\n".join(
        [
            spec["common"],
            spec["solver"],
            spec["solver_calculator"],
            note,
            "Final answer schema (reply with exactly this shape, action included):\n"
            + json.dumps(FinalSolverReply.model_json_schema()),
            "Calculator request schema:\n" + json.dumps(v25.SolverCalc.model_json_schema()),
        ]
    )


def task_system() -> str:
    text = _compose_task_system(prompts())
    if FROZEN_TASK_SYSTEM_SHA256 and hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_TASK_SYSTEM_SHA256:
        raise ValueError("Frozen v3.0 task system changed; use a new instrument version")
    return text


def attempt_system() -> str:
    text = _compose_attempt_system(prompts())
    if FROZEN_ATTEMPT_SYSTEM_SHA256 and hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_ATTEMPT_SYSTEM_SHA256:
        raise ValueError("Frozen v3.0 attempt system changed; use a new instrument version")
    return text


def solver_system(*, toolkit: bool) -> str:
    text = _compose_solver_system(prompts(), toolkit=toolkit)
    key = "toolkit" if toolkit else "no_toolkit"
    expected = FROZEN_SOLVER_SYSTEM_SHA256[key]
    if expected and hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
        raise ValueError("Frozen v3.0 solver system changed; use a new instrument version")
    return text


def task_system_sha256() -> str:
    return hashlib.sha256(_compose_task_system(_spec()).encode("utf-8")).hexdigest()


def attempt_system_sha256() -> str:
    return hashlib.sha256(_compose_attempt_system(_spec()).encode("utf-8")).hexdigest()


def solver_system_sha256(*, toolkit: bool) -> str:
    return hashlib.sha256(_compose_solver_system(_spec(), toolkit=toolkit).encode("utf-8")).hexdigest()


def _text_v30(raw: object, task: str) -> dict:
    judgment = v22.TextJudgment.model_validate(raw)
    data = judgment.model_dump()
    matched = [q for q in judgment.quotes if _quote_in_task(q, task)]
    unmatched = [q for q in judgment.quotes if not _quote_in_task(q, task)]
    if judgment.verdict != "unclear" and not matched:
        if not judgment.quotes:
            raise ValueError("A substantive text judgment requires an exact task quote")
        raise ValueError("A quotation is not an exact substring of the saved task")
    if unmatched:
        data["unmatched_task_quotes"] = unmatched
        data["quotes"] = matched
    return v22._row(judgment.verdict, "assessed", data)


def _accessibility_v30(raw: object, task: str) -> dict:
    judgment = v28.AccessibilityJudgment.model_validate(raw)
    data = judgment.model_dump()
    unmatched = [q for q in judgment.quotes if not _quote_in_task(q, task)]
    if unmatched:
        data["unmatched_task_quotes"] = unmatched
    return v22._row(judgment.verdict, "assessed", data)


def parse_task_v30(raw: dict, payload: dict) -> dict:
    rows = {}
    for field, measure in (("alignment", "target_alignment"), ("invention", "room_for_invention")):
        try:
            rows[measure] = _text_v30(raw.get(field), payload["student_task"])
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
            rows["prior_knowledge_accessibility"] = _accessibility_v30(
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
    if validity.reading_dependence == "unstated_choice" and validity.verdict in {"yes", "no"}:
        value = "unclear"
        evidence = {
            **evidence,
            "raw_verdict": validity.verdict,
            "rule": "unstated_choice_maps_to_unclear",
        }
    rows["mathematical_validity"] = v22._row(value, "assessed", evidence)
    return rows


def run_solver_v30(
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
            raise ValueError('Solver requires action "calculate" or "final"')
        except (ValueError, ValidationError) as exc:
            return v25._fail(record, "invalid_response", exc)
    return v25._fail(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def run_judge_v30(
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
                            _text_v30(raw.get(field), payload["student_task"])
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
                            alignment = _text_v30(raw.get("alignment"), payload["student_task"])
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


def parse_attempts_v30(raw: dict, attempts: list[dict]) -> dict:
    parsed = v28.parse_attempts_v28(raw, attempts)
    counts = parsed["counts"]
    row = parsed["measures"]["familiar_approach_limits"]
    if (
        row["value"] == "unclear"
        and counts["target_limits"] == 0
        and counts["meets_demands"] >= 2
        and not row["evidence"]["validation_errors"]
    ):
        parsed["measures"]["familiar_approach_limits"] = v22._row(
            "no", "assessed", row["evidence"]
        )
    return parsed


def assemble_v30(
    prepared: dict, solver: dict, task: dict, attempt: dict | None, *, toolkit: bool
) -> dict:
    if task["status"] == "completed":
        rows = parse_task_v30(task["output"], prepared)
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
            parsed = parse_attempts_v30(attempt["output"], solver["output"]["attempts"])
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


def evaluate_v30(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict,
    judge_chat: v22.Chat,
    toolkit: bool = True,
) -> dict:
    prepared = v25.prepare_input(task, target, context)
    task_result = run_judge_v30(
        "task_judge", v22.role_input("task_judge", prepared), judge_chat
    )
    task_rows = (
        parse_task_v30(task_result["output"], prepared)
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
            solver_id: run_solver_v30(
                v22.role_input("solver", prepared), chat, solver_id=solver_id, toolkit=toolkit
            )
            for solver_id, chat in solver_chats.items()
        }
        items = v25.combine_attempts(solver_runs)
        solver = v25._combined_solver(solver_runs, items)
        attempt = None
        if items:
            attempt = run_judge_v30(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                judge_chat,
            )
        principles = v25.principle_counts(solver_runs)
    result = assemble_v30(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
