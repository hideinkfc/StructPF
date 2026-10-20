"""Pf three-role v2.6: v2.5 solvers and task judge, with a strict start rule for the attempt judge.

Only the attempt-judge text changes. Its composition follows v2.2 exactly, so the
composition can be checked against the frozen v2.2 attempt judge.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import yaml

from src.evaluation import pf_three_role_v22 as v22
from src.evaluation import pf_three_role_v25 as v25

logger = logging.getLogger(__name__)

VERSION = "pf-three-role/v2.6"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_three_role_v2_6.yaml"
FROZEN_PROMPT_SHA256 = "1fd239be21126c9835384ba0b0b9e28c2c2cab05f88b161c6adbe1375cb2ec7d"
FROZEN_ATTEMPT_SYSTEM_SHA256 = "e5215a04b544c01b9c439af5f6cd23d6a69027465fc81372009d9b7c77b65a24"


def _spec() -> dict:
    spec = yaml.safe_load(PROMPT_PATH.read_bytes())
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError("Unexpected three-role v2.6 prompt version")
    return spec


def prompts() -> dict:
    if hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() != FROZEN_PROMPT_SHA256:
        raise ValueError("Frozen v2.6 prompt changed; use a new instrument version")
    return _spec()


def fingerprint() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def compose_attempt_system(attempt_text: str) -> str:
    """Same parts and order as v22.system('attempt_judge'), with the given judge text."""
    contract = (
        '{"action":"final","attempts":[<Audit per attempt, same order>],'
        '"inaccessible_because":<string or null>}'
    )
    base = v22.prompts()
    return "\n\n".join(
        [
            base["common"],
            attempt_text,
            base["calculator"],
            "Final contract:\n" + contract,
            json.dumps({"Audit": v22.Audit.model_json_schema()}),
            'Calculator contract: {"action":"calculate","checks":[<Check>]}',
            json.dumps(v22.Check.model_json_schema()),
        ]
    )


def attempt_system() -> str:
    text = compose_attempt_system(prompts()["attempt_judge"])
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != FROZEN_ATTEMPT_SYSTEM_SHA256:
        raise ValueError("Frozen v2.6 attempt system changed; use a new instrument version")
    return text


def attempt_system_sha256() -> str:
    """Hash of the exact attempt-judge system prompt. Unguarded so it can be pinned."""
    return hashlib.sha256(
        compose_attempt_system(_spec()["attempt_judge"]).encode("utf-8")
    ).hexdigest()


def evaluate_v26(
    task,
    target: str | None,
    context: dict,
    *,
    solver_chats: dict,
    judge_chat,
    toolkit: bool = True,
) -> dict:
    prepared = v25.prepare_input(task, target, context)
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
            attempt = v22.run_role(
                "attempt_judge",
                v22.role_input("attempt_judge", prepared, items),
                judge_chat,
                system_text=attempt_system(),
            )
            attempt["system_sha256"] = attempt_system_sha256()
        principles = v25.principle_counts(solver_runs)
    result = v22.assemble_v22(prepared, solver, task_result, attempt, toolkit=toolkit)
    return {
        **result,
        "version": VERSION,
        "solvers": solver["solvers"],
        "principles": principles,
        "approach_items_judged": len(solver["output"]["attempts"]) if solver["output"] else 0,
    }
