"""Three-role PF instrument v2.5: uncapped approaches, principle labels, two solvers, one judge.

Changes over v2.4, all on the solver side:
1. No cap on how many approaches a solver lists (the assumption cap is removed too).
2. Each approach carries a principle label; the solver prompt defines same versus different
   approaches by underlying mathematical principle. Code does not judge similarity.
3. The solver runs once per model in solver_chats; both attempt lists go to one attempt judge.

Judges, the task judge and assembly are reused from the frozen v2.2 module; calculator
execution is reused from v2.3. Calculator attempt numbers are per solver. Nothing here calls
a model.
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

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v23 as v23
from src.evaluation.pf_three_role import prepare_input
from src.utils.llm_client import LLMResponse

logger = logging.getLogger(__name__)
VERSION = "pf-three-role/v2.5"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2_5.yaml"
FROZEN_PROMPT_SHA256 = "59caddc8d48df0e09e73b4e5ba26a143d689157c9f3c7b459185f0f92714e832"
FROZEN_SOLVER_SYSTEM_SHA256 = {
    "toolkit": "108c03e63aae02d68f38e0db142ae7e3d865528ca9853db7ca42cd550647ffbd",
    "no_toolkit": "9cd5b7c61a798473f482ae8a9c922e3ae959a8ccf1632c827d7a2cf9e31fe590",
}
MAX_SOLVER_CALLS = v23.MAX_SOLVER_CALLS
MAX_SOLVER_CHECKS = v23.MAX_SOLVER_CHECKS
CANDIDATE_CAP = v23.CANDIDATE_CAP
Chat = Callable[[list[dict[str, str]]], LLMResponse]


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
            raise ValueError("A checked trial must state how many candidates it tested")
        if any(item not in v22.TOOLKIT_IDS for item in self.toolkit_used):
            raise ValueError("toolkit_used contains an unknown toolkit id")
        return self


class FinalSolverReply(v22.Strict):
    action: Literal["final"]
    assumptions: list[v22.Text] = Field(default_factory=list)
    attempts: list[Approach] = Field(min_length=1)


class SolverCalc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["calculate"]
    purpose: v22.Text
    attempt: int = Field(ge=0)
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


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.5 prompt version")
    return spec


def prompts() -> dict:
    if hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.5 prompt changed; use a new instrument version")
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
            "Calculator request schema:\n" + json.dumps(SolverCalc.model_json_schema()),
        ]
    )


def solver_system(*, toolkit: bool) -> str:
    text = _render(prompts(), toolkit=toolkit)
    key = "toolkit" if toolkit else "no_toolkit"
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_SOLVER_SYSTEM_SHA256[key]:
        raise ValueError("Frozen v2.5 solver system prompt changed; use a new instrument version")
    return text


def solver_system_sha256(*, toolkit: bool) -> str:
    """Hash of the exact solver system prompt. Unguarded so it can be pinned."""
    return hashlib.sha256(_render(_spec(), toolkit=toolkit).encode("utf-8")).hexdigest()


def _fail(record: dict, status: str, exc: Exception) -> dict:
    logger.error("solver %s: %s", status, exc)
    record.update({"status": status, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return record


def run_solver_v25(
    payload: dict,
    chat: Chat,
    *,
    solver_id: str,
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
                entry, refused = v23._execute(SolverCalc.model_validate(raw), counts)
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
            return _fail(record, "invalid_response", exc)
    return _fail(record, "budget_exhausted", ValueError("Model-call budget exceeded"))


def _principle_key(label: str) -> str:
    return " ".join(label.casefold().split())


def combine_attempts(solver_runs: dict[str, dict]) -> list[dict]:
    """One flat list for the attempt judge, labelled by solver, with that solver's own aids."""
    items = []
    for solver_id, run in solver_runs.items():
        if run["status"] != "completed":
            continue
        assumptions = run["output"]["assumptions"]
        for index, attempt in enumerate(run["output"]["attempts"]):
            aids = [
                {
                    "purpose": item["purpose"],
                    "expression": next(iter(item["request"]["expressions"].values())),
                    "status": item["status"],
                    "computed": item["computed"],
                }
                for item in run["calculations"]
                if item["attempt"] == index
            ]
            items.append(
                {
                    "solver": solver_id,
                    "attempt_number": index,
                    **attempt,
                    "solver_assumptions": assumptions,
                    "calculator_aids": aids,
                }
            )
    return items


def principle_counts(solver_runs: dict[str, dict]) -> dict:
    by_solver, union = {}, set()
    for solver_id, run in solver_runs.items():
        if run["status"] != "completed":
            continue
        keys = {_principle_key(item["principle"]) for item in run["output"]["attempts"]}
        by_solver[solver_id] = len(keys)
        union |= keys
    return {
        "distinct_by_solver": by_solver,
        "distinct_union": len(union),
        "scope": (
            "Exact match of solver-written principle labels after case and spacing "
            "normalisation. Not a semantic judgement; the solver prompt defines distinctness."
        ),
    }


def _solver_summary(run: dict) -> dict:
    refused = sum(item.get("refused", False) for item in run["calculations"])
    listed = len(run["output"]["attempts"]) if run["output"] else 0
    unmatched = sum(item["attempt"] >= listed for item in run["calculations"])
    return {
        "status": run["status"],
        "error": run["error"],
        "attempts": len(run["output"]["attempts"]) if run["output"] else None,
        "calculator_requests": len(run["calculations"]),
        "refused": refused,
        "calculator_requests_without_listed_attempt": unmatched,
        "candidate_checks_by_attempt": run["candidate_checks_by_attempt"],
    }


def _combined_solver(solver_runs: dict[str, dict], items: list[dict]) -> dict:
    failed = [run for run in solver_runs.values() if run["status"] != "completed"]
    status = "completed" if items else failed[0]["status"]
    error = None if items else failed[0]["error"]
    return {
        "status": status,
        "error": error,
        "calls": [call for run in solver_runs.values() for call in run["calls"]],
        "calculations": [item for run in solver_runs.values() for item in run["calculations"]],
        "output": {"assumptions": [], "attempts": items},
        "solvers": {sid: _solver_summary(run) for sid, run in solver_runs.items()},
    }


def evaluate_v25(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict[str, Chat],
    judge_chat: Chat,
    toolkit: bool = True,
) -> dict:
    prepared = prepare_input(task, target, context)
    task_result = v22.run_role("task_judge", v22.role_input("task_judge", prepared), judge_chat)
    history = prepared["learner_context"].get("assumed_prior_knowledge")
    if not history:
        solver = {
            "status": "input_unavailable",
            "error": None,
            "calls": [],
            "calculations": [],
            "output": None,
            "solvers": {},
        }
        attempt = None
        principles = principle_counts({})
    else:
        solver_runs = {
            solver_id: run_solver_v25(
                v22.role_input("solver", prepared), chat, solver_id=solver_id, toolkit=toolkit
            )
            for solver_id, chat in solver_chats.items()
        }
        items = combine_attempts(solver_runs)
        solver = _combined_solver(solver_runs, items)
        attempt = None
        if items:
            attempt = v22.run_role(
                "attempt_judge", v22.role_input("attempt_judge", prepared, items), judge_chat
            )
        principles = principle_counts(solver_runs)
    result = v22.assemble_v22(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
