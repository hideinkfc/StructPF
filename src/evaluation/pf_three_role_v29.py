"""PF three-role v2.9: resource-and-toolkit sweep solver with the v2.8 accessibility gate.

The solver systematically sweeps (a) single-resource / partial-constraint student starts,
(b) toolkit heuristic explorations, and (c) combined solutions as independent parallel
approaches. If an approach is labelled checked_trial without a positive trial_count, that
approach is downgraded to unchecked_trial rather than discarding the whole solver reply.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import yaml
from openai import OpenAIError
from pydantic import Field, ValidationError, model_validator

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v23 as v23
from src.evaluation import pf_three_role_v25 as v25
from src.evaluation import pf_three_role_v28 as v28

logger = logging.getLogger(__name__)

VERSION = "pf-three-role/v2.9"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2_9.yaml"
FROZEN_PROMPT_SHA256 = "91fa3e79f50c74289b87a6c7c93dc88fef8805eb6a6050148ccadf1e9362323f"
FROZEN_SOLVER_SYSTEM_SHA256 = {
    "toolkit": "4d39ac1dafe20bfa4faaa7eba59a9c215a3ae8c22b5cb589a693987dbd138ab1",
    "no_toolkit": "c7f7aadf719c91bd0be866b575d9db55cf5f06677330ce5d4922ca3cb26b286f",
}


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
    attempts: list[Approach] = Field(min_length=1)


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.9 prompt version")
    return spec


def prompts() -> dict:
    if hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.9 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def _render(spec: dict, *, toolkit: bool) -> str:
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


def solver_system(*, toolkit: bool) -> str:
    text = _render(prompts(), toolkit=toolkit)
    key = "toolkit" if toolkit else "no_toolkit"
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_SOLVER_SYSTEM_SHA256[key]:
        raise ValueError("Frozen v2.9 solver system prompt changed; use a new instrument version")
    return text


def solver_system_sha256(*, toolkit: bool) -> str:
    return hashlib.sha256(_render(_spec(), toolkit=toolkit).encode("utf-8")).hexdigest()


def run_solver_v29(
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


def evaluate_v29(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict,
    judge_chat: v22.Chat,
    toolkit: bool = True,
) -> dict:
    prepared = v25.prepare_input(task, target, context)
    task_result = v28.run_judge_v28(
        "task_judge", v22.role_input("task_judge", prepared), judge_chat
    )
    task_rows = (
        v28.parse_task_v28(task_result["output"], prepared)
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
        solver_payload = v22.role_input("solver", prepared)
        with ThreadPoolExecutor(max_workers=max(1, len(solver_chats))) as pool:
            futs = {
                solver_id: pool.submit(
                    run_solver_v29, solver_payload, chat, solver_id=solver_id, toolkit=toolkit
                )
                for solver_id, chat in solver_chats.items()
            }
            solver_runs = {solver_id: fut.result() for solver_id, fut in futs.items()}
        items = v25.combine_attempts(solver_runs)
        solver = v25._combined_solver(solver_runs, items)
        attempt = None
        if items:
            attempt = v28.run_judge_v28(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                judge_chat,
            )
        principles = v25.principle_counts(solver_runs)
    result = v28.assemble_v28(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
