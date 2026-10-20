"""Data contracts and validation for D2 situation design.

A skeleton contains quantities and a question before numbers or a story exist.
The mathematical plan is a separate, frozen contract. Historical v1 plans
may contain executable prior paths; new v2 plans contain the target, answer
rule, essential constraints, and optionally one selected prior contrast.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from src.generation.design_briefs import DesignBrief

ALLOWED_ROLES = {
    "rate",
    "amount",
    "whole",
    "part",
    "count",
    "list",
    "unknown",
    "other",
}
ALLOWED_VALUE_SOURCES = {"given", "derived", "unknown"}
ALLOWED_VALUE_DOMAINS = {"positive", "positive_integer"}
ALLOWED_ANSWER_KINDS = {"largest", "smallest", "equal", "scalar"}
ALLOWED_OPERATORS = {"==", "!=", ">", ">=", "<", "<="}


def skeleton_schema_contract() -> str:
    """Return the authoritative slot-only skeleton schema for generation prompts."""
    roles = "|".join(sorted(ALLOWED_ROLES))
    value_sources = "|".join(sorted(ALLOWED_VALUE_SOURCES))
    value_domains = "|".join(sorted(ALLOWED_VALUE_DOMAINS))
    return (
        "SKELETON SCHEMA (authoritative):\n"
        f'- quantities: a NON-EMPTY list of objects with required fields "name", "role", '
        f'"description", "value_source", "unit", "list_length", and "value_domain"; '
        f'role must be one of "{roles}", value_source one of "{value_sources}", '
        f'and value_domain one of "{value_domains}".\n'
        "- names are unique snake_case strings; descriptions contain no concrete "
        "numbers. Given list quantities require a fixed positive integer list_length; "
        "derived and unknown lists may use null. Scalar quantities must use null "
        "list_length. Keep derived and unknown quantities as descriptive skeleton "
        'slots: only value_source="given" quantities bind later checker inputs.\n'
        '- approaches: a NON-EMPTY list of objects with required fields "id", '
        '"resources", "procedure", and "why_plausible"; resources is a NON-EMPTY '
        "list of exact supplied prior-resource names. anticipated_limitation is optional.\n"
        "- number_constraints: a list of non-empty strings describing numerical "
        "conditions for later planning; question is a number-free slot-only question."
    )


def quantity_schema_contract() -> str:
    """Reuse quantity metadata without asking a translator to regenerate approaches."""
    return (
        skeleton_schema_contract()
        .split("- approaches:", 1)[0]
        .replace("SKELETON SCHEMA (authoritative)", "QUANTITY METADATA (authoritative)")
        .rstrip()
    )


@dataclass(frozen=True)
class Quantity:
    """One typed slot of a skeleton, with its source in the eventual task."""

    name: str
    role: str
    description: str = ""
    value_source: str = "given"
    unit: str = ""
    list_length: int | None = None
    value_domain: str = "positive"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposedApproach:
    """A concrete student procedure that may be activated by the situation."""

    id: str
    resources: tuple[str, ...]
    procedure: str
    why_plausible: str
    anticipated_limitation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Skeleton:
    """Quantities, question, and proposed approaches before numbers or a story."""

    quantities: tuple[Quantity, ...]
    question: str
    why_methods_start: str = ""
    why_target_needed: str = ""
    why_each_resource_can_activate: str = ""
    why_none_settles_the_question: str = ""
    why_the_target_is_needed: str = ""
    number_constraints: tuple[str, ...] = ()
    approaches: tuple[ProposedApproach, ...] = ()

    def to_dict(self) -> dict:
        return {
            "quantities": [q.to_dict() for q in self.quantities],
            "question": self.question,
            "why_methods_start": self.why_methods_start,
            "why_target_needed": self.why_target_needed,
            "why_each_resource_can_activate": self.why_each_resource_can_activate,
            "why_none_settles_the_question": self.why_none_settles_the_question,
            "why_the_target_is_needed": self.why_the_target_is_needed,
            "number_constraints": list(self.number_constraints),
            "approaches": [a.to_dict() for a in self.approaches],
        }


@dataclass(frozen=True)
class AnswerRule:
    """How a set of labelled results answers the situation's question."""

    kind: str
    labels: tuple[str, ...]
    unit: str = ""
    require_unique: bool = True

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "labels": list(self.labels),
            "unit": self.unit,
            "require_unique": self.require_unique,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AnswerRule":
        kind = str(payload.get("kind", "")).strip()
        if kind not in ALLOWED_ANSWER_KINDS:
            raise ValueError(f"answer_rule kind must be one of {sorted(ALLOWED_ANSWER_KINDS)}")
        raw_labels = payload.get("labels")
        if not isinstance(raw_labels, list) or not raw_labels:
            raise ValueError("answer_rule requires a non-empty labels list")
        labels = tuple(str(label).strip() for label in raw_labels)
        if any(not label for label in labels) or len(set(labels)) != len(labels):
            raise ValueError("answer_rule labels must be non-empty and unique")
        if kind == "scalar" and len(labels) != 1:
            raise ValueError("scalar answer_rule must have exactly one label")
        require_unique = payload.get("require_unique", kind in {"largest", "smallest"})
        if not isinstance(require_unique, bool):
            raise ValueError("answer_rule require_unique must be boolean")
        return cls(
            kind=kind,
            labels=labels,
            unit=str(payload.get("unit") or "").strip(),
            require_unique=require_unique,
        )


@dataclass(frozen=True)
class FormulaPath:
    """A labelled set of expressions for one target or prior approach."""

    name: str
    expressions: tuple[tuple[str, str], ...]
    approach_id: str | None = None
    unit: str = ""
    supported: bool = True
    checkability: str = "numerical"

    @property
    def expression_map(self) -> dict[str, str]:
        return dict(self.expressions)

    def to_dict(self) -> dict:
        output = {
            "name": self.name,
            "expressions": self.expression_map,
        }
        if self.approach_id is not None:
            output["approach_id"] = self.approach_id
        if self.unit:
            output["unit"] = self.unit
        if not self.supported:
            output["supported"] = False
        if self.checkability != "numerical":
            output["checkability"] = self.checkability
        return output


@dataclass(frozen=True)
class ConstraintSpec:
    """A restricted comparison that must hold for generated values."""

    left: str
    operator: str
    right: str
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "left": self.left,
            "operator": self.operator,
            "right": self.right,
            "description": self.description,
        }


@dataclass(frozen=True)
class MathPlan:
    """Frozen mathematical contract used by D2b and the deterministic checker."""

    quantities: tuple[Quantity, ...]
    target: FormulaPath
    answer_rule: AnswerRule
    priors: tuple[FormulaPath, ...] = ()
    prior_contrast: FormulaPath | None = None
    prior_contrast_expected_target_equal: bool | None = None
    prior_contrast_expected_prior_equal: bool | None = None
    constraints: tuple[ConstraintSpec, ...] = ()
    required_checks: tuple[str, ...] = ()
    schema_version: str = "math-plan/v1"

    def __post_init__(self) -> None:
        if self.schema_version == "math-plan/v2" and (self.priors or self.required_checks):
            raise ValueError("math-plan/v2 cannot contain priors or required_checks")
        if self.schema_version == "math-plan/v2":
            if self.prior_contrast is None and (
                self.prior_contrast_expected_target_equal is not None
                or self.prior_contrast_expected_prior_equal is not None
            ):
                raise ValueError("prior_contrast outcomes require a prior_contrast")
            if (
                self.prior_contrast_expected_target_equal is not None
                and self.prior_contrast_expected_target_equal
                == self.prior_contrast_expected_prior_equal
            ):
                raise ValueError("prior_contrast expected equality outcomes must differ")

    @property
    def given_quantities(self) -> tuple[Quantity, ...]:
        return tuple(q for q in self.quantities if q.value_source == "given")

    def to_dict(self) -> dict:
        output = {
            "schema_version": self.schema_version,
            "quantities": [q.to_dict() for q in self.quantities],
            "target": self.target.to_dict(),
            "answer_rule": self.answer_rule.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
        }
        if self.prior_contrast is not None:
            contrast = self.prior_contrast.to_dict()
            if self.prior_contrast_expected_target_equal is not None:
                contrast["expected_target_equal"] = self.prior_contrast_expected_target_equal
            if self.prior_contrast_expected_prior_equal is not None:
                contrast["expected_prior_equal"] = self.prior_contrast_expected_prior_equal
            output["prior_contrast"] = contrast
        if self.schema_version != "math-plan/v2":
            output["priors"] = [p.to_dict() for p in self.priors]
            output["required_checks"] = list(self.required_checks)
        return output

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        quantities: tuple[Quantity, ...],
        *,
        approach_ids: set[str] | None = None,
    ) -> "MathPlan":
        schema_version = str(payload.get("schema_version") or "math-plan/v1").strip()
        if schema_version not in {"math-plan/v1", "math-plan/v2", "math-plan/legacy-adapter"}:
            raise ValueError(f"unsupported math plan schema_version {schema_version!r}")
        if schema_version == "math-plan/v2":
            allowed_keys = {
                "schema_version",
                "quantities",
                "target",
                "answer_rule",
                "constraints",
                "prior_contrast",
            }
            unexpected = sorted(set(payload) - allowed_keys)
            if unexpected:
                legacy = next(
                    (field for field in ("priors", "required_checks") if field in unexpected),
                    None,
                )
                if legacy is not None:
                    raise ValueError(f"math-plan/v2 must not include {legacy}")
                raise ValueError(f"math-plan/v2 has unsupported fields: {unexpected}")
            if "quantities" in payload:
                _validate_supplied_quantities(payload["quantities"], quantities)
        target = _formula_path(payload.get("target"), "target", allow_approach=False)
        if not target.supported or target.checkability != "numerical":
            raise ValueError("target path must be numerically checkable")
        prior_contrast_expected_target_equal = None
        prior_contrast_expected_prior_equal = None
        if schema_version == "math-plan/v2":
            if "priors" in payload:
                raise ValueError("math-plan/v2 must not include priors")
            if "required_checks" in payload:
                raise ValueError("math-plan/v2 must not include required_checks")
            priors = ()
            raw_contrast = payload.get("prior_contrast")
            if raw_contrast is None:
                prior_contrast = None
            else:
                _validate_v2_object_keys(
                    raw_contrast,
                    {
                        "name",
                        "approach_id",
                        "expressions",
                        "unit",
                        "expected_target_equal",
                        "expected_prior_equal",
                    },
                    "prior_contrast",
                )
                prior_contrast = _formula_path(
                    raw_contrast,
                    "prior_contrast",
                    allow_approach=True,
                )
                if prior_contrast.checkability != "numerical":
                    raise ValueError("math-plan/v2 prior_contrast must be numerically checkable")
                if prior_contrast.approach_id is None:
                    raise ValueError("math-plan/v2 prior_contrast requires approach_id")
                prior_contrast_expected_target_equal = raw_contrast.get("expected_target_equal")
                prior_contrast_expected_prior_equal = raw_contrast.get("expected_prior_equal")
                for field_name, value in (
                    ("expected_target_equal", prior_contrast_expected_target_equal),
                    ("expected_prior_equal", prior_contrast_expected_prior_equal),
                ):
                    if value is not None and not isinstance(value, bool):
                        raise ValueError(f"prior_contrast {field_name} must be boolean or null")
        else:
            prior_contrast = None
            raw_priors = payload.get("priors")
            if not isinstance(raw_priors, list) or not raw_priors:
                raise ValueError("math plan requires a non-empty priors list")
            priors = tuple(
                _formula_path(item, f"prior {index}", allow_approach=True)
                for index, item in enumerate(raw_priors)
            )
        raw_rule = payload.get("answer_rule")
        if not isinstance(raw_rule, Mapping):
            raise ValueError("math plan is missing answer_rule")
        answer_rule = AnswerRule.from_payload(raw_rule)
        if schema_version == "math-plan/v2":
            _validate_v2_object_keys(
                payload.get("target"),
                {"name", "unit", "expressions"},
                "target",
            )
            _validate_v2_object_keys(
                raw_rule,
                {"kind", "labels", "unit", "require_unique"},
                "answer_rule",
            )
        target_labels = set(target.expression_map)
        if target_labels != set(answer_rule.labels):
            raise ValueError("target expression labels must match answer_rule labels")
        if prior_contrast is not None:
            if answer_rule.kind in {"largest", "smallest"}:
                if not answer_rule.require_unique:
                    raise ValueError(
                        "prior_contrast requires a unique largest or smallest target answer"
                    )
                if set(prior_contrast.expression_map) != target_labels:
                    raise ValueError(
                        "prior_contrast labels must match target labels for largest/smallest"
                    )
                if (
                    prior_contrast_expected_target_equal is not None
                    or prior_contrast_expected_prior_equal is not None
                ):
                    raise ValueError(
                        "prior_contrast equality outcomes are only valid for an equal answer rule"
                    )
            elif answer_rule.kind == "equal":
                if len(target_labels) < 2:
                    raise ValueError(
                        "equal prior_contrast requires at least two target comparisons"
                    )
                if len(prior_contrast.expression_map) < 2:
                    raise ValueError("equal prior_contrast requires at least two prior comparisons")
                if (
                    prior_contrast_expected_target_equal is None
                    or prior_contrast_expected_prior_equal is None
                ):
                    raise ValueError(
                        "equal prior_contrast requires selected expected_target_equal "
                        "and expected_prior_equal outcomes"
                    )
                if prior_contrast_expected_target_equal == prior_contrast_expected_prior_equal:
                    raise ValueError(
                        "equal prior_contrast expected outcomes must differ as selected"
                    )
            else:
                raise ValueError("prior_contrast supports largest, smallest, or equal answer rules")
            if approach_ids is not None and prior_contrast.approach_id not in approach_ids:
                raise ValueError(
                    f"prior_contrast references unknown approach {prior_contrast.approach_id!r}"
                )
        declared_units = {
            path.unit
            for path in (target, *priors)
            if path.unit and path.checkability == "numerical"
        }
        if schema_version != "math-plan/v2" and len(declared_units) > 1:
            raise ValueError("target and prior path units must be compatible")
        if answer_rule.unit and declared_units and answer_rule.unit not in declared_units:
            raise ValueError("answer_rule unit does not match the path units")
        for prior in priors:
            if prior.approach_id is None and approach_ids is not None:
                raise ValueError(f"prior {prior.name!r} still needs approach_id")
            if prior.checkability != "numerical":
                continue
            if set(prior.expression_map) != target_labels:
                raise ValueError(f"prior {prior.name!r} labels must match target labels exactly")
            if approach_ids is not None and prior.approach_id not in approach_ids:
                raise ValueError(
                    f"prior {prior.name!r} references unknown approach {prior.approach_id!r}"
                )
        raw_constraints = (
            payload.get("constraints", [])
            if schema_version == "math-plan/v2"
            else payload.get("constraints") or []
        )
        if not isinstance(raw_constraints, list):
            raise ValueError("math plan constraints must be a list")
        if schema_version == "math-plan/v2":
            for index, item in enumerate(raw_constraints):
                _validate_v2_object_keys(
                    item,
                    {"left", "operator", "right", "description"},
                    f"constraint {index}",
                )
        constraints = tuple(_constraint_from_payload(item) for item in raw_constraints)
        if schema_version == "math-plan/v2":
            required_checks = ()
        else:
            raw_checks = payload.get("required_checks")
            if raw_checks is None:
                required_checks = ()
            elif isinstance(raw_checks, list) and all(
                isinstance(item, str) and item.strip() for item in raw_checks
            ):
                required_checks = tuple(item.strip() for item in raw_checks)
            else:
                raise ValueError("required_checks must be a list of non-empty strings")
        return cls(
            quantities=quantities,
            target=target,
            priors=priors,
            prior_contrast=prior_contrast,
            prior_contrast_expected_target_equal=prior_contrast_expected_target_equal,
            prior_contrast_expected_prior_equal=prior_contrast_expected_prior_equal,
            answer_rule=answer_rule,
            constraints=constraints,
            required_checks=required_checks,
            schema_version=schema_version,
        )


@dataclass(frozen=True)
class MethodVerdict:
    """Judge verdict for one prior method on one candidate."""

    method: str
    can_start: bool
    settles_question: bool
    direct_routine: bool = False
    approach_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NumberRequirement:
    """A judge-proposed numerical condition and its educational purpose."""

    condition: str
    purpose: str

    def to_dict(self) -> dict:
        return asdict(self)


def _number_requirements_from_raw(
    raw: object,
    candidate_id: int,
) -> tuple[NumberRequirement, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"judge candidate {candidate_id} number_requirements must be a list")
    requirements = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(
                f"judge candidate {candidate_id} number requirement {index} must be an object"
            )
        condition = item.get("condition")
        purpose = item.get("purpose")
        if (
            not isinstance(condition, str)
            or not condition.strip()
            or not isinstance(purpose, str)
            or not purpose.strip()
        ):
            raise ValueError(
                f"judge candidate {candidate_id} number requirement {index} "
                "needs non-empty condition and purpose"
            )
        requirements.append(NumberRequirement(condition=condition.strip(), purpose=purpose.strip()))
    return tuple(requirements)


def number_requirements_from_payload(
    payload: Mapping[str, object],
) -> dict[int, tuple[NumberRequirement, ...]]:
    """Validate and extract optional judge-proposed numerical requirements."""
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise ValueError("judge payload is missing a non-empty candidates list")
    out: dict[int, tuple[NumberRequirement, ...]] = {}
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError(f"judge candidate must be an object, got {entry!r}")
        try:
            cid = int(entry.get("id"))
        except (TypeError, ValueError):
            raise ValueError(f"judge candidate is missing integer id: {entry!r}") from None
        out[cid] = _number_requirements_from_raw(entry.get("number_requirements"), cid)
    return out


@dataclass(frozen=True)
class PriorContrastIntent:
    """One selected, operational prior move and how far it can be checked."""

    approach_id: str
    operational_move: str
    checkability: str
    reason: str
    expected_target_equal: bool | None = None
    expected_prior_equal: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def prior_contrast_intent_from_payload(raw: object) -> PriorContrastIntent | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("judge prior_contrast must be an object or null")
    approach_id = raw.get("approach_id")
    operational_move = raw.get("operational_move")
    checkability = raw.get("checkability")
    reason = raw.get("reason")
    expected_target_equal = raw.get("expected_target_equal")
    expected_prior_equal = raw.get("expected_prior_equal")
    if not isinstance(approach_id, str) or not approach_id.strip():
        raise ValueError("judge prior_contrast requires a non-empty approach_id")
    if not isinstance(operational_move, str) or not operational_move.strip():
        raise ValueError("judge prior_contrast requires a concrete operational_move")
    if not isinstance(checkability, str) or checkability not in {
        "numerical",
        "qualitative",
        "unsupported",
    }:
        raise ValueError(
            "judge prior_contrast checkability must be numerical, qualitative, or unsupported"
        )
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("judge prior_contrast requires a non-empty reason")
    if expected_target_equal is not None and not isinstance(expected_target_equal, bool):
        raise ValueError("judge prior_contrast expected_target_equal must be boolean or null")
    if expected_prior_equal is not None and not isinstance(expected_prior_equal, bool):
        raise ValueError("judge prior_contrast expected_prior_equal must be boolean or null")
    if (expected_target_equal is None) != (expected_prior_equal is None):
        raise ValueError("judge prior_contrast equality outcomes must both be set or both be null")
    if expected_target_equal is not None and expected_target_equal == expected_prior_equal:
        raise ValueError("judge prior_contrast equality outcomes must differ")
    return PriorContrastIntent(
        approach_id=approach_id.strip(),
        operational_move=operational_move.strip(),
        checkability=checkability,
        reason=reason.strip(),
        expected_target_equal=expected_target_equal,
        expected_prior_equal=expected_prior_equal,
    )


@dataclass(frozen=True)
class JudgeSelection:
    """The judge's compact recommendation for the candidate set."""

    recommended_id: int | None
    approaches: tuple[str, ...]
    reason: str
    main_concern: str | None
    number_requirements: tuple[NumberRequirement, ...] = ()
    prior_contrast: PriorContrastIntent | None = None


def judge_selection_from_payload(
    payload: Mapping[str, object],
    candidate_ids: set[int],
    *,
    require_prior_contrast: bool = False,
) -> JudgeSelection | None:
    """Validate the current compact judge response.

    ``None`` indicates the legacy per-candidate response shape.
    """
    if "recommended_id" not in payload:
        if require_prior_contrast:
            raise ValueError("judge response is missing compact-selection recommended_id")
        return None
    if require_prior_contrast and "prior_contrast" not in payload:
        raise ValueError("judge payload is missing prior_contrast (use null when none applies)")
    raw_id = payload.get("recommended_id")
    if raw_id is not None and (isinstance(raw_id, bool) or not isinstance(raw_id, int)):
        raise ValueError("judge recommended_id must be an integer or null")
    recommended_id = raw_id
    if recommended_id is not None and recommended_id not in candidate_ids:
        raise ValueError(f"judge recommended_id {recommended_id} is not a candidate")

    raw_approaches = payload.get("approaches")
    if not isinstance(raw_approaches, list) or any(
        not isinstance(item, str) or not item.strip() for item in raw_approaches
    ):
        raise ValueError("judge approaches must be a list of non-empty strings")
    approaches = tuple(item.strip() for item in raw_approaches)
    if recommended_id is not None and not approaches:
        raise ValueError("judge approaches must not be empty when a candidate is recommended")
    if recommended_id is None and approaches:
        raise ValueError("judge approaches must be empty when no candidate is recommended")

    reason = str(payload.get("reason", "")).strip()
    if not reason:
        raise ValueError("judge reason must be non-empty")
    raw_concern = payload.get("main_concern")
    if raw_concern is not None and (not isinstance(raw_concern, str) or not raw_concern.strip()):
        raise ValueError("judge main_concern must be a non-empty string or null")
    main_concern = raw_concern.strip() if isinstance(raw_concern, str) else None
    requirements = _number_requirements_from_raw(
        payload.get("number_requirements"),
        recommended_id if recommended_id is not None else -1,
    )
    prior_contrast = prior_contrast_intent_from_payload(payload.get("prior_contrast"))
    if recommended_id is None and prior_contrast is not None:
        raise ValueError("judge prior_contrast must be null when no candidate is recommended")
    return JudgeSelection(
        recommended_id=recommended_id,
        approaches=approaches,
        reason=reason,
        main_concern=main_concern,
        number_requirements=requirements,
        prior_contrast=prior_contrast,
    )


@dataclass(frozen=True)
class JudgedCandidate:
    """A skeleton plus the judge's verdicts and code-derived acceptance/rank."""

    candidate_id: int
    skeleton: Skeleton
    verdicts: tuple[MethodVerdict, ...]
    practice_item: bool = field(compare=False)
    target_named: bool = field(compare=False)
    activation_count: int = field(compare=False)
    number_requirements: tuple[NumberRequirement, ...] = field(default_factory=tuple, compare=False)
    selection_reason: str = field(default="", compare=False)
    main_concern: str | None = field(default=None, compare=False)
    selection_approaches: tuple[str, ...] = field(default=(), compare=False)
    prior_contrast: PriorContrastIntent | None = field(default=None, compare=False)
    design_brief: DesignBrief | None = field(default=None, compare=False)

    @property
    def accepted(self) -> bool:
        return not self.practice_item and not self.target_named and self.activation_count >= 1

    def to_dict(self) -> dict:
        payload = {
            "candidate_id": self.candidate_id,
            "skeleton": self.skeleton.to_dict(),
            "verdicts": [v.to_dict() for v in self.verdicts],
            "practice_item": self.practice_item,
            "target_named": self.target_named,
            "activation_count": self.activation_count,
            "approach_count": self.activation_count,
            "number_requirements": [r.to_dict() for r in self.number_requirements],
            "selection_reason": self.selection_reason,
            "main_concern": self.main_concern,
            "selection_approaches": list(self.selection_approaches),
            "prior_contrast": (
                None if self.prior_contrast is None else self.prior_contrast.to_dict()
            ),
            "accepted": self.accepted,
        }
        if self.design_brief is not None:
            payload["design_brief"] = self.design_brief.to_dict()
        return payload


_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MISSING = object()


def _safe_id(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip()).strip("_").lower()
    return value or "approach"


def _approach_from_payload(item: object, index: int) -> ProposedApproach:
    if not isinstance(item, Mapping):
        raise ValueError(f"approach {index} must be an object")
    approach_id = str(item.get("id") or f"approach_{index}").strip()
    if not approach_id:
        raise ValueError(f"approach {index} is missing id")
    raw_resources = item.get("resources")
    if isinstance(raw_resources, str):
        resources = (raw_resources.strip(),)
    elif isinstance(raw_resources, list) and all(
        isinstance(resource, str) and resource.strip() for resource in raw_resources
    ):
        resources = tuple(resource.strip() for resource in raw_resources)
    else:
        resource = str(item.get("resource") or "").strip()
        resources = (resource,) if resource else ()
    if not resources:
        raise ValueError(f"approach {approach_id!r} needs at least one resource")
    procedure = str(item.get("procedure") or "").strip()
    why_plausible = str(item.get("why_plausible") or "").strip()
    limitation = str(item.get("anticipated_limitation") or "").strip()
    if not procedure or not why_plausible:
        raise ValueError(f"approach {approach_id!r} needs procedure and why_plausible")
    return ProposedApproach(
        id=approach_id,
        resources=resources,
        procedure=procedure,
        why_plausible=why_plausible,
        anticipated_limitation=limitation,
    )


def _formula_path(
    payload: object,
    fallback_name: str,
    *,
    allow_approach: bool,
) -> FormulaPath:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{fallback_name} path must be an object")
    name = str(payload.get("name") or payload.get("resource") or fallback_name).strip()
    if not name:
        raise ValueError(f"{fallback_name} path is missing a name")
    supported = payload.get("supported", True)
    if not isinstance(supported, bool):
        raise ValueError(f"{name!r} supported must be boolean")
    raw_checkability = payload.get("checkability")
    if raw_checkability is None:
        checkability = "numerical" if supported else "unsupported"
    else:
        checkability = str(raw_checkability).strip()
    if checkability not in {"numerical", "qualitative", "unsupported"}:
        raise ValueError(f"{name!r} checkability must be numerical, qualitative, or unsupported")
    if checkability == "numerical" and not supported:
        raise ValueError(f"{name!r} numerical path cannot set supported=false")
    raw_expressions = payload.get("expressions")
    if checkability != "numerical":
        if raw_expressions not in (None, {}):
            raise ValueError(f"{name!r} non-numerical paths must have empty expressions")
        raw_expressions = {}
    if not isinstance(raw_expressions, Mapping) or (
        checkability == "numerical" and not raw_expressions
    ):
        raise ValueError(f"{name!r} path needs non-empty expressions")
    expressions: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_label, raw_formula in raw_expressions.items():
        label = str(raw_label).strip()
        if not label or label in seen:
            raise ValueError(f"{name!r} path has duplicate or empty expression label")
        if not isinstance(raw_formula, str) or not raw_formula.strip():
            raise ValueError(f"{name!r} expression {label!r} must be a non-empty string")
        seen.add(label)
        expressions.append((label, raw_formula.strip()))
    approach_id = payload.get("approach_id")
    if approach_id is not None:
        if not allow_approach:
            raise ValueError("target path cannot reference a prior approach")
        if not isinstance(approach_id, str) or not approach_id.strip():
            raise ValueError(f"{name!r} approach_id must be a non-empty string")
        approach_id = approach_id.strip()
    return FormulaPath(
        name=name,
        expressions=tuple(expressions),
        approach_id=approach_id,
        unit=str(payload.get("unit") or "").strip(),
        supported=checkability == "numerical",
        checkability=checkability,
    )


def _constraint_from_payload(item: object) -> ConstraintSpec:
    if not isinstance(item, Mapping):
        raise ValueError("each math plan constraint must be an object")
    left = item.get("left")
    right = item.get("right")
    operator = str(item.get("operator") or "").strip()
    if not isinstance(left, str) or not left.strip():
        raise ValueError("constraint left must be a non-empty expression")
    if not isinstance(right, str) or not right.strip():
        raise ValueError("constraint right must be a non-empty expression")
    if operator not in ALLOWED_OPERATORS:
        raise ValueError(f"constraint operator must be one of {sorted(ALLOWED_OPERATORS)}")
    return ConstraintSpec(
        left=left.strip(),
        operator=operator,
        right=right.strip(),
        description=str(item.get("description") or "").strip(),
    )


def _validate_v2_object_keys(
    payload: object,
    allowed: set[str],
    name: str,
) -> None:
    if not isinstance(payload, Mapping):
        return
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise ValueError(f"math-plan/v2 {name} has unsupported fields: {unexpected}")


def _validate_supplied_quantities(
    raw_quantities: object,
    quantities: tuple[Quantity, ...],
) -> None:
    if not isinstance(raw_quantities, list):
        raise ValueError("math-plan/v2 quantities must be a list")
    expected = [quantity.to_dict() for quantity in quantities]
    normalized = []
    for item in raw_quantities:
        if isinstance(item, Mapping) and "value_domain" not in item:
            normalized.append({**item, "value_domain": "positive"})
        else:
            normalized.append(item)
    if normalized != expected:
        raise ValueError("math-plan/v2 quantities do not match the selected skeleton")


def skeleton_from_payload(
    payload: Mapping[str, object],
    *,
    require_complete_metadata: bool = False,
) -> Skeleton:
    """Validate one proposer payload against the slot-only contract.

    Historical payloads may omit list lengths. Fresh proposals should pass
    ``require_complete_metadata=True`` so every given list has a fixed length
    before it can be judged or selected.
    """
    return _skeleton_from_payload(
        payload,
        require_complete_metadata=require_complete_metadata,
    )


def _skeleton_from_payload(
    payload: Mapping[str, object],
    *,
    require_complete_metadata: bool,
) -> Skeleton:
    raw_quantities = payload.get("quantities")
    if not isinstance(raw_quantities, list) or not raw_quantities:
        raise ValueError("skeleton is missing a non-empty quantities list")
    quantities = []
    names: set[str] = set()
    for item in raw_quantities:
        if not isinstance(item, Mapping):
            raise ValueError(f"quantity must be an object, got {item!r}")
        name = str(item.get("name", "")).strip()
        role = str(item.get("role", "")).strip()
        description = str(item.get("description", "")).strip()
        if not name or not _NAME_RE.match(name):
            raise ValueError(f"quantity name must be snake_case, got {name!r}")
        if name in names:
            raise ValueError(f"duplicate quantity name {name!r}")
        if role not in ALLOWED_ROLES:
            raise ValueError(f"quantity {name!r} role must be one of {sorted(ALLOWED_ROLES)}")
        if any(ch.isdigit() for ch in description):
            raise ValueError(f"quantity {name!r} description contains a number")
        value_source = str(
            item.get("value_source") or ("unknown" if role == "unknown" else "given")
        ).strip()
        if value_source not in ALLOWED_VALUE_SOURCES:
            raise ValueError(
                f"quantity {name!r} value_source must be one of {sorted(ALLOWED_VALUE_SOURCES)}"
            )
        unit = str(item.get("unit") or "").strip()
        list_length = item.get("list_length")
        if list_length is not None:
            if isinstance(list_length, bool) or not isinstance(list_length, int) or list_length < 1:
                raise ValueError(f"quantity {name!r} list_length must be a positive integer")
            if require_complete_metadata and role != "list":
                raise ValueError(f"quantity {name!r} list_length is only valid for role='list'")
        raw_value_domain = item.get("value_domain", _MISSING)
        if raw_value_domain is _MISSING:
            value_domain = "positive"
        elif isinstance(raw_value_domain, str):
            value_domain = raw_value_domain.strip()
        elif require_complete_metadata and value_source == "given":
            raise ValueError(
                f"given quantity {name!r} value_domain must be one of "
                f"{sorted(ALLOWED_VALUE_DOMAINS)}"
            )
        else:
            value_domain = "positive"
        if value_domain not in ALLOWED_VALUE_DOMAINS:
            raise ValueError(
                f"quantity {name!r} value_domain must be one of {sorted(ALLOWED_VALUE_DOMAINS)}"
            )
        if require_complete_metadata and role == "list" and value_source == "given":
            if list_length is None:
                raise ValueError(
                    f"given list quantity {name!r} must declare fixed positive list_length metadata"
                )
        if require_complete_metadata and value_source == "given" and "value_domain" not in item:
            raise ValueError(f"given quantity {name!r} must declare value_domain metadata")
        names.add(name)
        quantities.append(
            Quantity(
                name=name,
                role=role,
                description=description,
                value_source=value_source,
                unit=unit,
                list_length=list_length,
                value_domain=value_domain,
            )
        )
    question = str(payload.get("question", "")).strip()
    if not question:
        raise ValueError("skeleton is missing question")
    if any(ch.isdigit() for ch in question):
        raise ValueError("question contains a number")
    why_activate = str(
        payload.get("why_each_resource_can_activate") or payload.get("why_methods_start") or ""
    ).strip()
    why_target = str(
        payload.get("why_the_target_is_needed") or payload.get("why_target_needed") or ""
    ).strip()
    why_none = str(payload.get("why_none_settles_the_question") or "").strip()
    raw_constraints = payload.get("number_constraints", _MISSING)
    if raw_constraints is _MISSING:
        raw_constraints = []
    elif require_complete_metadata and not isinstance(raw_constraints, list):
        raise ValueError("number_constraints must be a list in a fresh proposal")
    constraints: list[str] = []
    if isinstance(raw_constraints, list):
        for index, item in enumerate(raw_constraints):
            if isinstance(item, str) and item.strip():
                constraints.append(item.strip())
            elif require_complete_metadata:
                raise ValueError(f"number_constraints entry {index} must be a non-empty string")
    raw_approaches = payload.get("approaches")
    if require_complete_metadata:
        if not isinstance(raw_approaches, list) or not raw_approaches:
            raise ValueError("fresh proposal requires a non-empty approaches list")
        approaches = tuple(
            _approach_from_payload(item, index) for index, item in enumerate(raw_approaches)
        )
    elif raw_approaches is None:
        approaches = tuple(
            ProposedApproach(
                id=_safe_id(f"approach_{index}_{name}"),
                resources=(name,),
                procedure=f"Apply {name}.",
                why_plausible="The listed prior resource appears applicable to the quantities.",
                anticipated_limitation="Its limitation is not specified in this legacy payload.",
            )
            for index, name in enumerate(
                str(item.get("resource") or "").strip()
                for item in (payload.get("prior_resources") or [])
                if isinstance(item, Mapping) and str(item.get("resource") or "").strip()
            )
        )
    else:
        if not isinstance(raw_approaches, list) or not raw_approaches:
            raise ValueError("approaches must be a non-empty list when provided")
        approaches = tuple(
            _approach_from_payload(item, index) for index, item in enumerate(raw_approaches)
        )
    return Skeleton(
        quantities=tuple(quantities),
        question=question,
        why_methods_start=why_activate,
        why_target_needed=why_target,
        why_each_resource_can_activate=why_activate,
        why_none_settles_the_question=why_none,
        why_the_target_is_needed=why_target,
        number_constraints=tuple(constraints),
        approaches=approaches,
    )


def skeleton_from_proposal_payload(payload: Mapping[str, object]) -> Skeleton:
    """Validate a new proposal, including metadata needed for deterministic filling."""
    return skeleton_from_payload(payload, require_complete_metadata=True)


def skeleton_metadata_errors(skeleton: Skeleton) -> tuple[str, ...]:
    """Return missing metadata errors without changing historical skeletons."""
    errors = []
    for quantity in skeleton.quantities:
        if quantity.role == "list" and quantity.value_source == "given":
            if quantity.list_length is None:
                errors.append(f"given list quantity {quantity.name!r} has no fixed list_length")
    return tuple(errors)


def verdicts_from_payload(
    payload: Mapping[str, object],
    prior_methods: list[str],
    approach_ids_by_candidate: Mapping[int, set[str]] | None = None,
) -> dict[int, tuple[bool, tuple[MethodVerdict, ...]]]:
    """Validate the batched judge payload.

    Returns a map of candidate id -> (target_named, method verdicts).
    """
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise ValueError("judge payload is missing a non-empty candidates list")
    allowed = set(prior_methods)
    out: dict[int, tuple[bool, tuple[MethodVerdict, ...]]] = {}
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError(f"judge candidate must be an object, got {entry!r}")
        try:
            cid = int(entry.get("id"))
        except (TypeError, ValueError):
            raise ValueError(f"judge candidate is missing integer id: {entry!r}") from None
        target_named = entry.get("target_named")
        if not isinstance(target_named, bool):
            raise ValueError(f"judge candidate {cid} is missing boolean target_named")
        methods = entry.get("methods")
        if not isinstance(methods, list):
            raise ValueError(f"judge candidate {cid} is missing methods list")
        verdicts = []
        seen: set[str] = set()
        for m in methods:
            if not isinstance(m, Mapping):
                raise ValueError(f"method verdict must be an object: {m!r}")
            method = str(m.get("method", "")).strip()
            if method not in allowed:
                raise ValueError(f"judge returned unknown method {method!r}")
            if method in seen:
                raise ValueError(f"judge returned duplicate method {method!r}")
            can_start = m.get("can_start")
            settles = m.get("settles_question")
            if not isinstance(can_start, bool) or not isinstance(settles, bool):
                raise ValueError(f"method {method!r} verdicts must be booleans")
            direct_routine = m.get("direct_routine", settles)
            if not isinstance(direct_routine, bool):
                raise ValueError(f"method {method!r} direct_routine must be boolean")
            raw_approach_ids = m.get("approach_ids")
            if raw_approach_ids is None:
                approach_ids = (method,)
            elif isinstance(raw_approach_ids, list) and all(
                isinstance(item, str) and item.strip() for item in raw_approach_ids
            ):
                approach_ids = tuple(item.strip() for item in raw_approach_ids)
            else:
                raise ValueError(f"method {method!r} approach_ids must be a list of strings")
            if approach_ids_by_candidate is not None:
                allowed_approaches = approach_ids_by_candidate.get(cid, set())
                unknown_approaches = set(approach_ids) - allowed_approaches
                if unknown_approaches:
                    raise ValueError(
                        f"candidate {cid} method {method!r} returned unknown "
                        f"approaches {sorted(unknown_approaches)}"
                    )
            seen.add(method)
            verdicts.append(
                MethodVerdict(
                    method=method,
                    can_start=can_start,
                    settles_question=settles,
                    direct_routine=direct_routine,
                    approach_ids=approach_ids,
                )
            )
        if seen != allowed:
            raise ValueError(
                f"judge candidate {cid} covers {sorted(seen)}, expected {sorted(allowed)}"
            )
        out[cid] = (target_named, tuple(verdicts))
    return out


def rank_candidates(
    skeletons: list[Skeleton],
    verdicts: dict[int, tuple[bool, tuple[MethodVerdict, ...]]],
    number_requirements_by_candidate: Mapping[int, tuple[NumberRequirement, ...]] | None = None,
) -> list[JudgedCandidate]:
    """Attach verdicts and compute acceptance.

    Reject candidates that name the target directly or are direct routine drills.
    Rank the rest by how many distinct proposed approaches can activate.
    Candidates the judge did not cover are dropped. All judged candidates are
    returned, sorted accepted-first then by activation count, so callers can see what died.
    """
    judged = []
    number_requirements_by_candidate = number_requirements_by_candidate or {}
    for cid, skeleton in enumerate(skeletons):
        entry = verdicts.get(cid)
        if entry is None:
            continue
        target_named, v = entry
        practice_item = any(verd.direct_routine for verd in v)
        approach_ids = {
            approach_id
            for verd in v
            if verd.can_start and not verd.direct_routine
            for approach_id in (verd.approach_ids or (verd.method,))
        }
        activation_count = len(approach_ids)
        judged.append(
            JudgedCandidate(
                candidate_id=cid,
                skeleton=skeleton,
                verdicts=v,
                practice_item=practice_item,
                target_named=target_named,
                activation_count=activation_count,
                number_requirements=number_requirements_by_candidate.get(cid, ()),
            )
        )
    judged.sort(key=lambda c: (c.accepted, c.activation_count), reverse=True)
    return judged


def selected_candidate(
    skeletons: list[Skeleton],
    selection: JudgeSelection,
) -> list[JudgedCandidate]:
    """Convert a compact judge recommendation into the existing winner shape."""
    if selection.recommended_id is None:
        return []
    skeleton = skeletons[selection.recommended_id]
    if selection.prior_contrast is not None and selection.prior_contrast.approach_id not in {
        approach.id for approach in skeleton.approaches
    }:
        raise ValueError(
            "judge prior_contrast references unknown approach "
            f"{selection.prior_contrast.approach_id!r}"
        )
    return [
        JudgedCandidate(
            candidate_id=selection.recommended_id,
            skeleton=skeleton,
            verdicts=(),
            practice_item=False,
            target_named=False,
            activation_count=len(selection.approaches),
            number_requirements=selection.number_requirements,
            selection_reason=selection.reason,
            main_concern=selection.main_concern,
            selection_approaches=selection.approaches,
            prior_contrast=selection.prior_contrast,
        )
    ]


def best_candidates(judged: list[JudgedCandidate]) -> list[JudgedCandidate]:
    """The winning tier: accepted candidates tied at the max activation count."""
    viable = [c for c in judged if c.accepted]
    if not viable:
        return []
    top = max(c.activation_count for c in viable)
    return [c for c in viable if c.activation_count == top]
