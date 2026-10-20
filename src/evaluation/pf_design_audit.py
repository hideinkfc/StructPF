"""Exploratory, qualitative PF task-design audit separate from Rahimi Table 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from src.evaluation.pf_rubric import judge_input

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pf_design_audit_v5.yaml"
FindingStatus = Literal["supported", "partial", "not_evidenced", "unknown"]
MathStatus = Literal["model_recomputed", "unknown", "concern"]
Evidence = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvidenceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FindingStatus
    evidence: Evidence


class Approach(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Evidence
    starting_resource: Evidence
    mathematical_difference: Evidence


class ApproachFinding(EvidenceFinding):
    approaches: list[Approach]

    @model_validator(mode="after")
    def supported_routes_are_distinct(self) -> "ApproachFinding":
        if self.status == "supported":
            if len(self.approaches) < 2:
                raise ValueError("supported approach diversity requires at least two routes")
            differences = {item.mathematical_difference.casefold() for item in self.approaches}
            if len(differences) < 2:
                raise ValueError("supported approaches must state distinct mathematical reasoning")
        return self


class MathematicsReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MathStatus
    evidence: Evidence
    concerns: list[Evidence]

    @model_validator(mode="after")
    def concern_status_has_evidence(self) -> "MathematicsReview":
        if self.status == "concern" and not self.concerns:
            raise ValueError("concern status requires at least one concrete concern")
        return self


class PFDesignAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_relevance: EvidenceFinding
    prior_resource_start: EvidenceFinding
    useful_contrast: EvidenceFinding
    approach_diversity: ApproachFinding
    task_openness: EvidenceFinding
    mathematics_review: MathematicsReview


def load_prompt() -> dict[str, str]:
    prompt = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
    if not isinstance(prompt, dict) or any(
        not isinstance(prompt.get(key), str) or not prompt[key].strip()
        for key in ("version", "source", "system")
    ):
        raise ValueError("PF design-audit prompt requires version, source, and system strings")
    return prompt


def design_audit_input(student_text: str, target: str, context: dict) -> str:
    """Reuse the Table 1 input allowlist, adding only the common lesson target."""
    target = target.strip() if isinstance(target, str) else ""
    if not target:
        raise ValueError("learning_target must be nonempty text")
    base = json.loads(judge_input(student_text, context))
    return json.dumps(
        {"learning_target": target, **base},
        ensure_ascii=False,
        indent=2,
    )


def parse_design_audit(raw: str) -> dict:
    audit = PFDesignAudit.model_validate_json(raw)
    findings = (
        audit.target_relevance,
        audit.prior_resource_start,
        audit.useful_contrast,
        audit.approach_diversity,
        audit.task_openness,
    )
    fully_unknown = all(item.status == "unknown" for item in findings)
    fully_unknown = fully_unknown and audit.mathematics_review.status == "unknown"
    return {
        "status": "unknown" if fully_unknown else "scored",
        "scope": "task_affordance_hypothesis",
        "observed_student_behavior": "not_provided",
        "mathematics_review_scope": (
            "Model task-text assessment only; not a deterministic proof or independent "
            "verification."
        ),
        "audit": audit.model_dump(),
    }
