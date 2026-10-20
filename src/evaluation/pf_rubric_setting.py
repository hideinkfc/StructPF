"""Table 1 rating with the fixed task setting a trained rater would know.

Anchors are identical to rahimi-table1/v1. The judge additionally sees the
shared design brief of the task's group (intended use, untaught target, theme
and interest), never the generating model, prompt examples or design notes.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.evaluation.pf_rubric import (
    DIMENSIONS,
    PFRating,
    _nonempty_text,
    learner_context,
    parse_rating,
    student_task_text,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pf_rubric_setting.yaml"
INTENDED_USE = (
    "Productive Failure exploration phase: students attempt this problem before "
    "any instruction on the learning target."
)


def load_prompt() -> dict[str, str]:
    prompt = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
    if not isinstance(prompt, dict) or any(
        not isinstance(prompt.get(key), str) or not prompt[key].strip()
        for key in ("version", "source", "system")
    ):
        raise ValueError("PF rubric setting prompt requires version, source, and system strings")
    return prompt


def task_setting(case: dict) -> dict[str, str]:
    """Allowlist the group-level brief; drop ids, standards lists and generation rules."""
    context = case.get("benchmark_context") or {}
    return {
        "intended_use": INTENDED_USE,
        "learning_target": _nonempty_text(case.get("target_concept"), "target_concept"),
        "theme": _nonempty_text(context.get("theme"), "theme"),
        "student_interest": _nonempty_text(context.get("interest"), "interest"),
    }


def judge_input(student_text: str, case: dict, context: dict) -> str:
    return json.dumps(
        {
            "task_setting": task_setting(case),
            "learner_context": learner_context(context),
            "student_task": _nonempty_text(student_text, "student_task"),
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = [
    "DIMENSIONS",
    "INTENDED_USE",
    "PFRating",
    "PROMPT_PATH",
    "judge_input",
    "learner_context",
    "load_prompt",
    "parse_rating",
    "student_task_text",
    "task_setting",
]
