"""Paper-aligned PF rating contract, separate from MCQ and in-pipeline judges."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pf_rubric.yaml"
DIMENSIONS = ("APK", "SSC", "AE", "MR", "OE")
Score = Annotated[int, Field(strict=True, ge=1, le=3)]
Evidence = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DimensionRating(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: Evidence
    score: Score | None


class PFRating(BaseModel):
    model_config = ConfigDict(extra="forbid")

    APK: DimensionRating
    SSC: DimensionRating
    AE: DimensionRating
    MR: DimensionRating
    OE: DimensionRating
    mathematical_concerns: list[Evidence]

    def scores(self) -> dict[str, int | None]:
        scores = {key: getattr(self, key).score for key in DIMENSIONS}
        known = [value for value in scores.values() if value is not None]
        scores["TOTAL"] = sum(known) if len(known) == len(DIMENSIONS) else None
        return scores


def load_prompt() -> dict[str, str]:
    prompt = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
    if not isinstance(prompt, dict) or any(
        not isinstance(prompt.get(key), str) or not prompt[key].strip()
        for key in ("version", "source", "system")
    ):
        raise ValueError("PF rubric prompt requires version, source, and system strings")
    return prompt


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def student_task_text(task: dict) -> str:
    """Allowlist only the three student-facing fields of a ready writer result."""
    if task.get("status") != "ready":
        raise ValueError("Only a ready student task can be rated")
    return "\n\n".join(_nonempty_text(task.get(key), key) for key in ("title", "body", "question"))


def legacy_student_text(sections: dict[str, str]) -> str:
    """Use parsed student sections rather than regex-filtering raw teacher output."""
    narrative = _nonempty_text(sections.get("NARRATIVE"), "NARRATIVE")
    task = _nonempty_text(sections.get("TASK"), "TASK")
    parts = [narrative]
    if "DATA" in sections:
        parts.append(_nonempty_text(sections["DATA"], "DATA"))
    return "\n\n".join([*parts, task])


def learner_context(context: dict) -> dict:
    """Exclude proposed student moves and claims about why those moves fail."""
    result = {key: context[key] for key in ("grade", "subject", "jurisdiction") if key in context}
    resources = context.get("assumed_prior_knowledge")
    if resources is not None:
        if not isinstance(resources, list):
            raise ValueError("assumed_prior_knowledge must be a list")
        result["assumed_prior_knowledge"] = [
            {key: _nonempty_text(resource.get(key), key) for key in ("resource", "taught_as")}
            for resource in resources
            if isinstance(resource, dict)
        ]
        if len(result["assumed_prior_knowledge"]) != len(resources):
            raise ValueError("Each prior-knowledge resource must be an object")
    else:
        result["assumed_prior_knowledge"] = None
    return result


def judge_input(student_text: str, context: dict) -> str:
    return json.dumps(
        {
            "learner_context": learner_context(context),
            "student_task": _nonempty_text(student_text, "student_task"),
        },
        ensure_ascii=False,
        indent=2,
    )


def parse_rating(raw: str) -> dict:
    rating = PFRating.model_validate_json(raw)
    scores = rating.scores()
    return {
        "status": "scored" if scores["TOTAL"] is not None else "insufficient_evidence",
        "scores": scores,
        "rating": rating.model_dump(),
    }
