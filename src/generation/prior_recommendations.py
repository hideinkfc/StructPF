"""Shared data contract for prior-knowledge recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Mapping

RecommendationKind = Literal["builds_on", "tempting_mistake"]
ProvenanceType = Literal["paper", "curriculum", "model"]
Confidence = Literal["high", "medium", "low"]
Condition = Literal["grounded", "ungrounded"]


@dataclass(frozen=True)
class Provenance:
    """Evidence attached to a recommendation."""

    type: ProvenanceType
    source: str
    page: int | str | None = None
    document: str | None = None
    source_url: str | None = None
    evidence: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResourceCandidate:
    """A taught-skill candidate before it is expanded into a student move."""

    resource: str
    taught_as: str
    relevance: str
    provenance: Provenance
    confidence: Confidence
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PriorMethodRecommendation:
    """The comparable output record for both grounded and ungrounded runs."""

    resource: str
    kind: RecommendationKind
    taught_as: str
    student_move: str
    falls_short_because: str
    provenance: Provenance
    confidence: Confidence
    condition: Condition
    relevance: str = ""
    why_it_looks_applicable: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, object],
        *,
        provenance: Provenance,
        condition: Condition,
        default_resource: str | None = None,
        default_taught_as: str | None = None,
        default_relevance: str = "",
        default_confidence: Confidence = "medium",
    ) -> "PriorMethodRecommendation":
        """Validate one model expansion against the shared output contract."""
        resource = _string(payload, "resource") or default_resource
        taught_as = _string(payload, "taught_as") or default_taught_as
        if not resource:
            raise ValueError("recommendation is missing resource")
        if not taught_as:
            raise ValueError(f"recommendation {resource!r} is missing taught_as")

        kind = _choice(payload, "kind", {"builds_on", "tempting_mistake"}, "builds_on")
        confidence = _choice(
            payload,
            "confidence",
            {"high", "medium", "low"},
            default_confidence,
        )
        student_move = _string(payload, "student_move") or _string(payload, "what_student_does")
        if not student_move:
            raise ValueError(f"recommendation {resource!r} is missing student_move")
        falls_short = _string(payload, "falls_short_because")
        if not falls_short:
            raise ValueError(f"recommendation {resource!r} is missing falls_short_because")

        return cls(
            resource=resource,
            kind=kind,
            taught_as=taught_as,
            student_move=student_move,
            falls_short_because=falls_short,
            provenance=provenance,
            confidence=confidence,
            condition=condition,
            relevance=_string(payload, "relevance") or default_relevance,
            why_it_looks_applicable=_string(payload, "why_it_looks_applicable") or "",
        )


def _string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _choice(
    payload: Mapping[str, object],
    key: str,
    allowed: set[str],
    default: str,
) -> str:
    value = _string(payload, key)
    if value is None:
        return default
    if value not in allowed:
        raise ValueError(f"{key} must be one of {sorted(allowed)}, got {value!r}")
    return value
