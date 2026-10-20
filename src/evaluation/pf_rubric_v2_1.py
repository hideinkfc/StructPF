"""Anchor-preserving v2.1 operational interpretation of the PF rating rubric."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.evaluation.pf_rubric_v2 import (
    DIMENSIONS,
    PFRating,
    judge_input,
    learner_context,
    parse_rating,
    student_task_text,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pf_rubric_v2_1.yaml"


def load_prompt() -> dict[str, str]:
    prompt = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
    if not isinstance(prompt, dict) or any(
        not isinstance(prompt.get(key), str) or not prompt[key].strip()
        for key in ("version", "source", "system")
    ):
        raise ValueError("PF rubric v2.1 prompt requires version, source, and system strings")
    return prompt


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
