"""Internal design briefs, before executable quantities are declared."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.generation.situation_skeletons import ProposedApproach, Quantity, Skeleton


@dataclass(frozen=True)
class BriefApproach:
    resources: tuple[str, ...]
    first_action: str
    what_it_establishes: str
    limitation: str = ""

    def to_dict(self) -> dict:
        return {
            "resources": list(self.resources),
            "first_action": self.first_action,
            "what_it_establishes": self.what_it_establishes,
            "limitation": self.limitation,
        }


@dataclass(frozen=True)
class DesignBrief:
    goal: str
    situation_and_rules: str
    student_question: str
    approaches: tuple[BriefApproach, ...]
    successful_route: str
    learning_opportunity: str
    number_requirements: tuple[str, ...]
    key_idea: str = ""
    naive_answer: str = ""
    schema_version: str = "design-brief/v1"

    def to_dict(self) -> dict:
        payload = {
            "schema_version": self.schema_version,
            "goal": self.goal,
            "situation_and_rules": self.situation_and_rules,
            "student_question": self.student_question,
            "approaches": [approach.to_dict() for approach in self.approaches],
            "successful_route": self.successful_route,
            "learning_opportunity": self.learning_opportunity,
            "number_requirements": list(self.number_requirements),
        }
        if self.schema_version == "design-brief/v2":
            payload.update(key_idea=self.key_idea, naive_answer=self.naive_answer)
        return payload

    def skeleton(self, quantities: tuple[Quantity, ...]) -> Skeleton:
        """Project immutable pedagogical fields; translation supplies only quantities."""
        return Skeleton(
            quantities=quantities,
            question=self.student_question,
            approaches=tuple(
                ProposedApproach(
                    id=f"brief_{index}",
                    resources=approach.resources,
                    procedure=approach.first_action,
                    why_plausible=approach.what_it_establishes,
                    anticipated_limitation=approach.limitation,
                )
                for index, approach in enumerate(self.approaches)
            ),
            why_each_resource_can_activate="\n".join(
                f"{', '.join(approach.resources)}: {approach.first_action}"
                for approach in self.approaches
            ),
            why_none_settles_the_question=self.learning_opportunity,
            why_the_target_is_needed=self.learning_opportunity,
            number_constraints=self.number_requirements,
        )


def _text(payload: Mapping, key: str, *, optional: bool = False) -> str:
    value = payload.get(key, "" if optional else None)
    if not isinstance(value, str) or (not optional and not value.strip()):
        requirement = "possibly empty" if optional else "non-empty"
        raise ValueError(f"design brief {key} must be a {requirement} string")
    return value.strip()


def design_brief_from_payload(
    payload: object, supplied_resources: list[str] | None = None
) -> DesignBrief:
    if not isinstance(payload, Mapping):
        raise ValueError("design brief must be a JSON object")
    version = payload.get("schema_version", "design-brief/v1")
    if version not in ("design-brief/v1", "design-brief/v2"):
        raise ValueError("design brief schema_version must be design-brief/v1 or design-brief/v2")
    allowed = {
        "schema_version",
        "goal",
        "situation_and_rules",
        "student_question",
        "approaches",
        "successful_route",
        "learning_opportunity",
        "number_requirements",
    }
    if version == "design-brief/v2":
        allowed.update(("key_idea", "naive_answer"))
    if set(payload) - allowed:
        raise ValueError(f"design brief has unsupported fields: {sorted(set(payload) - allowed)}")
    raw_approaches = payload.get("approaches")
    if not isinstance(raw_approaches, list) or not raw_approaches:
        raise ValueError("design brief approaches must be a non-empty list")
    approaches = []
    for item in raw_approaches:
        if not isinstance(item, Mapping):
            raise ValueError("design brief approach must be an object")
        if set(item) - {"resources", "first_action", "what_it_establishes", "limitation"}:
            raise ValueError("design brief approach has unsupported fields")
        resources = item.get("resources")
        if (
            not isinstance(resources, list)
            or not resources
            or any(not isinstance(resource, str) or not resource.strip() for resource in resources)
        ):
            raise ValueError("design brief approach resources must be non-empty strings")
        resources = tuple(resource.strip() for resource in resources)
        if len(set(resources)) != len(resources):
            raise ValueError("design brief approach has duplicate resources")
        if supplied_resources is not None and set(resources) - set(supplied_resources):
            raise ValueError(
                f"design brief references unsupported prior resources: "
                f"{sorted(set(resources) - set(supplied_resources))}"
            )
        approaches.append(
            BriefApproach(
                resources=resources,
                first_action=_text(item, "first_action"),
                what_it_establishes=_text(item, "what_it_establishes"),
                limitation=_text(item, "limitation", optional=True),
            )
        )
    requirements = payload.get("number_requirements")
    if not isinstance(requirements, list) or any(
        not isinstance(condition, str) or not condition.strip() for condition in requirements
    ):
        raise ValueError("design brief number_requirements must be a list of non-empty strings")
    question = _text(payload, "student_question")
    if any(character.isdigit() for character in question):
        raise ValueError("design brief student_question contains concrete numbers")
    return DesignBrief(
        goal=_text(payload, "goal"),
        situation_and_rules=_text(payload, "situation_and_rules"),
        student_question=question,
        approaches=tuple(approaches),
        successful_route=_text(payload, "successful_route"),
        learning_opportunity=_text(payload, "learning_opportunity"),
        number_requirements=tuple(condition.strip() for condition in requirements),
        key_idea=_text(payload, "key_idea") if version == "design-brief/v2" else "",
        naive_answer=_text(payload, "naive_answer") if version == "design-brief/v2" else "",
        schema_version=version,
    )
