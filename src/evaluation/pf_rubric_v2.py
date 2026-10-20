"""Versioned task-level adaptation of Rahimi et al.'s five-dimension PF rubric."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.evaluation.pf_rubric import (
    DIMENSIONS,
    PFRating,
    student_task_text,
)
from src.evaluation.pf_rubric import (
    learner_context as _learner_context,
)
from src.evaluation.pf_rubric import (
    parse_rating as _parse_rating,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pf_rubric_v2.yaml"


def load_prompt() -> dict[str, str]:
    prompt = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
    if not isinstance(prompt, dict) or any(
        not isinstance(prompt.get(key), str) or not prompt[key].strip()
        for key in ("version", "source", "system")
    ):
        raise ValueError("PF rubric v2 prompt requires version, source, and system strings")
    return prompt


def learner_context(context: dict, target_concept: str) -> dict:
    """Keep the common target and learner facts; omit condition and design metadata."""
    result = _learner_context(context)
    if not isinstance(target_concept, str) or not target_concept.strip():
        raise ValueError("target_concept must be nonempty text")
    result["learning_target"] = target_concept.strip()
    return result


def judge_input(student_text: str, context: dict, target_concept: str) -> str:
    return json.dumps(
        {
            "learner_context": learner_context(context, target_concept),
            "student_task": student_text.strip() if isinstance(student_text, str) else "",
        },
        ensure_ascii=False,
        indent=2,
    )


def parse_rating(raw: str) -> dict:
    """Use the unchanged v1 schema and score semantics for the same five fields."""
    return _parse_rating(raw)


__all__ = [
    "DIMENSIONS",
    "PFRating",
    "PROMPT_PATH",
    "judge_input",
    "learner_context",
    "load_prompt",
    "parse_rating",
    "student_task_text",
]
