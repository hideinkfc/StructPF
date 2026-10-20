"""Frozen, evidence-backed PF task measures; no generator or learner-quality gates."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Annotated, Callable, Generic, Literal, TypeVar

import yaml
from openai import OpenAIError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    StringConstraints,
    ValidationError,
    model_validator,
)

from src.evaluation.pf_evidence_audit import quote_anchor, student_text
from src.evaluation.pf_rubric import _nonempty_text, learner_context
from src.generation.design_calculator import calculate_condition
from src.utils.llm_client import LLMResponse

logger = logging.getLogger(__name__)
VERSION = "pf-task-measures/v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_task_measures_v1.yaml"
FROZEN_RUBRIC_SHA256 = "dced22cbab1a9659f7966dac1a5ca12d9d1b7c57d511cefe3e8f5682825d8c61"
MEASURES = (
    "target_alignment",
    "mathematical_validity",
    "prior_knowledge_accessibility",
    "familiar_approach_limits",
    "room_for_invention",
)
CALCULATOR_ROLES = {"mathematical_validity", "familiar_approach_limits"}
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Verdict = Literal["yes", "partly", "no", "unclear"]
BinaryVerdict = Literal["yes", "no", "unclear"]
Chat = Callable[[list[dict[str, str]]], LLMResponse]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Judgment(StrictModel):
    verdict: Verdict
    task_quotes: list[Text]
    reasoning: Text

    @model_validator(mode="after")
    def require_quotes(self) -> Judgment:
        if self.verdict != "unclear" and not self.task_quotes:
            raise ValueError("A substantive verdict requires exact task quotes")
        return self


class Alignment(Judgment):
    target_quotes: list[Text]
    addressed_elements: list[Text]
    missing_elements: list[Text]

    @model_validator(mode="after")
    def require_mapping(self) -> Alignment:
        if self.verdict != "unclear" and not self.target_quotes:
            raise ValueError("Alignment requires an exact target quote")
        if self.verdict in {"yes", "partly"} and not self.addressed_elements:
            raise ValueError("Aligned and partly aligned judgments require addressed elements")
        if self.verdict == "partly" and not self.missing_elements:
            raise ValueError("Partly aligned requires an explicit missing target element")
        return self


class MathematicalFinding(StrictModel):
    status: Literal["supported", "concern", "unresolved"]
    argument: Text
    verification: Literal["argument", "calculator", "both"]
    calculator_ids: list[Text]


class Mathematics(Judgment):
    verdict: BinaryVerdict
    interpretation: Text
    assumptions: list[Text]
    calculator_coverage: Text
    consistency: MathematicalFinding
    feasibility: MathematicalFinding
    justification: MathematicalFinding

    @model_validator(mode="after")
    def require_consistent_findings(self) -> Mathematics:
        statuses = {self.consistency.status, self.feasibility.status, self.justification.status}
        expected = (
            "no" if "concern" in statuses else "unclear" if "unresolved" in statuses else "yes"
        )
        if self.verdict != expected:
            raise ValueError("Mathematical verdict contradicts its essential findings")
        return self


class Approach(StrictModel):
    id: Text
    method: Text
    mathematical_idea: Text
    worked_start: Text
    resource_indices: list[Annotated[StrictInt, Field(ge=0)]]
    support_argument: Text
    distinction_argument: Text
    task_quotes: list[Text]

    @model_validator(mode="after")
    def require_start_evidence(self) -> Approach:
        if not self.resource_indices or not self.task_quotes:
            raise ValueError("An approach requires prerequisite references and exact task quotes")
        if len(set(self.resource_indices)) != len(self.resource_indices):
            raise ValueError("An approach repeats a prerequisite reference")
        return self


class Accessibility(Judgment):
    verdict: BinaryVerdict
    approaches: list[Approach]
    missing_knowledge: list[Text]
    inaccessibility_argument: str

    @model_validator(mode="after")
    def require_start_or_obstruction(self) -> Accessibility:
        if (self.verdict == "yes") != bool(self.approaches):
            raise ValueError("Yes requires a supported start; No/Unclear cannot contain one")
        if self.verdict == "no" and (
            not self.missing_knowledge or not self.inaccessibility_argument.strip()
        ):
            raise ValueError(
                "Inaccessibility requires missing knowledge and an obstruction argument"
            )
        ids = [approach.id for approach in self.approaches]
        ideas = [approach.mathematical_idea.casefold() for approach in self.approaches]
        if len(set(ids)) != len(ids) or len(set(ideas)) != len(ideas):
            raise ValueError("Approach ids and underlying ideas must not be exact duplicates")
        return self


class ApproachReview(StrictModel):
    approach_id: Text
    outcome: Literal["limit", "meets_demands", "unresolved"]
    worked_attempt: Text
    reasoning: Text
    limitation: str
    target_resolution: str
    task_quotes: list[Text]
    calculator_ids: list[Text]

    @model_validator(mode="after")
    def require_limit_evidence(self) -> ApproachReview:
        if self.outcome != "unresolved" and not self.task_quotes:
            raise ValueError("A substantive approach outcome requires exact task quotes")
        if self.outcome == "limit" and (
            not self.limitation.strip() or not self.target_resolution.strip()
        ):
            raise ValueError("A limit requires its explanation and a target-related resolution")
        return self


class ApproachLimits(Judgment):
    verdict: BinaryVerdict
    approach_reviews: list[ApproachReview]

    @model_validator(mode="after")
    def require_consistent_outcomes(self) -> ApproachLimits:
        outcomes = [review.outcome for review in self.approach_reviews]
        if not outcomes:
            raise ValueError("Approach-limit review cannot be empty")
        expected = "yes" if "limit" in outcomes else "unclear" if "unresolved" in outcomes else "no"
        if self.verdict != expected:
            raise ValueError("Approach-limit verdict contradicts the reviewed outcomes")
        return self


class Invention(Judgment):
    supplied_construction: list[Text]
    remaining_construction: str
    consequence_argument: Text

    @model_validator(mode="after")
    def require_construction_evidence(self) -> Invention:
        if self.verdict in {"yes", "partly"} and not self.remaining_construction.strip():
            raise ValueError("Yes/Partly requires remaining consequential construction")
        if self.verdict in {"partly", "no"} and not self.supplied_construction:
            raise ValueError("Partly/No requires supplied central mathematical construction")
        return self


class Calculation(StrictModel):
    expressions: dict[str, Text]
    predicate: Text
    symbols: dict[str, Literal["positive", "nonnegative", "real", "integer"]] = Field(
        default_factory=dict
    )


class CalculatorRequest(StrictModel):
    id: Text
    statement: Text
    interpretation: Text
    task_quotes: Annotated[list[Text], Field(min_length=1)]
    values: dict[str, JsonValue]
    units: dict[str, str] = Field(default_factory=dict)
    calculation: Calculation


class CalculateResponse(StrictModel):
    action: Literal["calculate"]
    checks: Annotated[list[CalculatorRequest], Field(min_length=1, max_length=16)]


J = TypeVar("J", bound=Judgment)


class FinalResponse(StrictModel, Generic[J]):
    action: Literal["final"]
    judgment: J


SCHEMAS = {
    "target_alignment": Alignment,
    "mathematical_validity": Mathematics,
    "prior_knowledge_accessibility": Accessibility,
    "familiar_approach_limits": ApproachLimits,
    "room_for_invention": Invention,
}


class EvaluationLimits(StrictModel):
    max_calls: Annotated[StrictInt, Field(ge=1, le=3)] = 3
    max_calculations: Annotated[StrictInt, Field(ge=1, le=16)] = 16


def load_rubric() -> dict:
    source = PROMPT_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != FROZEN_RUBRIC_SHA256:
        raise ValueError("Frozen PF rubric changed; use a new instrument version")
    rubric = yaml.safe_load(source)
    if not isinstance(rubric, dict) or rubric.get("version") != VERSION:
        raise ValueError("Unexpected PF task-measure rubric version")
    if tuple(rubric.get("measures", {})) != MEASURES:
        raise ValueError("PF task-measure rubric must contain the five ordered measures")
    return rubric


def _prepare_context(context: dict) -> dict:
    if not isinstance(context, dict):
        raise ValueError("learner_context must be an object")
    if context.get("recently_taught") and context.get("assumed_prior_knowledge") is None:
        raise ValueError(
            "recently_taught would be discarded; adapt the frozen history to "
            "assumed_prior_knowledge first"
        )
    return learner_context(context)


def prepare_input(task: str | dict, target: str, context: dict) -> dict:
    return {
        "student_task": _nonempty_text(task, "student_task")
        if isinstance(task, str)
        else student_text(task),
        "learning_target": _nonempty_text(target, "learning_target"),
        "learner_context": _prepare_context(context),
    }


def role_input(measure: str, prepared: dict, approaches: list[dict] | None = None) -> dict:
    if measure not in MEASURES:
        raise ValueError(f"Unknown task measure: {measure}")
    payload = {
        "student_task": prepared["student_task"],
        "learner_context": prepared["learner_context"],
    }
    if measure != "prior_knowledge_accessibility":
        payload["learning_target"] = prepared["learning_target"]
    if measure == "familiar_approach_limits":
        if not approaches:
            raise ValueError("Approach-limit input requires the frozen supported starts")
        payload["approaches"] = approaches
    return payload


def system_prompt(measure: str, *, max_calls: int = 3, max_calculations: int = 16) -> str:
    rubric = load_rubric()
    contract = rubric["measures"][measure]
    parts = [
        f"Measure: {contract['name']}. Instrument: {VERSION}.",
        rubric["common"],
        json.dumps(contract["definitions"], ensure_ascii=False),
        contract["instruction"],
        "Return ONLY JSON matching the following final-response schema:\n"
        + json.dumps(FinalResponse[SCHEMAS[measure]].model_json_schema()),
    ]
    if measure in CALCULATOR_ROLES:
        parts.extend(
            [
                rubric["calculator_protocol"],
                f"Execution limits: {max_calls} model calls and {max_calculations} "
                "calculator checks total for this role.",
                "Alternatively request checks using this JSON schema:\n"
                + json.dumps(CalculateResponse.model_json_schema()),
            ]
        )
    return "\n\n".join(parts)


def _verify_quotes(quotes: list[str], text: str) -> None:
    for quote in quotes:
        if not quote_anchor(quote, text)["verified"]:
            raise ValueError(f"Evidence quote is absent from its source: {quote!r}")


def _verify_approach(approach: Approach, payload: dict) -> None:
    _verify_quotes(approach.task_quotes, payload["student_task"])
    resources = payload["learner_context"]["assumed_prior_knowledge"] or []
    if any(index >= len(resources) for index in approach.resource_indices):
        raise ValueError("An approach references an unavailable prerequisite")


def _validate_judgment(judgment: Judgment, payload: dict, calculations: list[dict]) -> None:
    _verify_quotes(judgment.task_quotes, payload["student_task"])
    checks = {entry["request"]["id"]: entry["result"] for entry in calculations}
    if isinstance(judgment, Alignment):
        _verify_quotes(judgment.target_quotes, payload["learning_target"])
    if isinstance(judgment, Accessibility):
        resources = payload["learner_context"]["assumed_prior_knowledge"] or []
        if not resources and judgment.verdict != "unclear":
            raise ValueError(
                "Absent prior history cannot establish accessibility or inaccessibility"
            )
        for approach in judgment.approaches:
            _verify_approach(approach, payload)
    if isinstance(judgment, Mathematics):
        findings = [judgment.consistency, judgment.feasibility, judgment.justification]
        for finding in findings:
            if any(identifier not in checks for identifier in finding.calculator_ids):
                raise ValueError("A mathematical finding references an unexecuted calculation")
            if finding.verification in {"calculator", "both"} and not finding.calculator_ids:
                raise ValueError("Calculator verification requires executed check ids")
            if finding.verification == "calculator" and finding.status != "unresolved":
                if any(
                    checks[identifier]["status"] in {"unknown", "unsupported"}
                    for identifier in finding.calculator_ids
                ):
                    raise ValueError("Unknown/unsupported checks cannot establish a finding alone")
    if isinstance(judgment, ApproachLimits):
        expected = {approach["id"] for approach in payload["approaches"]}
        reviewed = [review.approach_id for review in judgment.approach_reviews]
        if set(reviewed) != expected or len(reviewed) != len(expected):
            raise ValueError("Every frozen approach must be reviewed exactly once")
        for review in judgment.approach_reviews:
            _verify_quotes(review.task_quotes, payload["student_task"])
            if any(identifier not in checks for identifier in review.calculator_ids):
                raise ValueError("An approach review references an unexecuted calculation")


class PFTaskMeasuresEvaluator:
    def __init__(self, chat: Chat, *, max_calls: int = 3, max_calculations: int = 16):
        limits = EvaluationLimits(max_calls=max_calls, max_calculations=max_calculations)
        self.chat = chat
        self.max_calls = limits.max_calls
        self.max_calculations = limits.max_calculations

    def evaluate_role(self, measure: str, payload: dict) -> dict:
        if measure not in MEASURES:
            raise ValueError(f"Unknown task measure: {measure}")
        allowed = {"student_task", "learner_context"}
        if measure != "prior_knowledge_accessibility":
            allowed.add("learning_target")
        if measure == "familiar_approach_limits":
            allowed.add("approaches")
        if set(payload) != allowed:
            raise ValueError(f"{measure} input must contain exactly {sorted(allowed)}")
        payload = {
            **payload,
            "student_task": _nonempty_text(payload["student_task"], "student_task"),
            "learner_context": _prepare_context(payload["learner_context"]),
        }
        if "learning_target" in payload:
            _nonempty_text(payload["learning_target"], "learning_target")
        if "approaches" in payload:
            approaches = [Approach.model_validate(item) for item in payload["approaches"]]
            if not approaches:
                raise ValueError("Approach-limit review requires supported starts")
            for approach in approaches:
                _verify_approach(approach, payload)
            payload["approaches"] = [approach.model_dump() for approach in approaches]
        messages = [
            {
                "role": "system",
                "content": system_prompt(
                    measure, max_calls=self.max_calls, max_calculations=self.max_calculations
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        record = {
            "measure": measure,
            "status": "starting",
            "value": None,
            "judgment": None,
            "input": payload,
            "calls": [],
            "calculations": [],
            "error": None,
        }
        limit = self.max_calls if measure in CALCULATOR_ROLES else 1
        for _ in range(limit):
            call = {"messages": [dict(message) for message in messages], "response": None}
            record["calls"].append(call)
            try:
                response = self.chat(messages)
            except (OpenAIError, ConnectionError, TimeoutError) as exc:
                return self._failure(record, "api_error", exc)
            call["response"] = {
                "text": response.text,
                "model": response.model,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            }
            if response.finish_reason == "length":
                return self._failure(
                    record, "truncated", ValueError("Completion token limit reached")
                )
            if response.finish_reason not in {"", "stop"}:
                return self._failure(
                    record,
                    "invalid_response",
                    ValueError(f"Unusable finish reason: {response.finish_reason}"),
                )
            try:
                raw = json.loads(response.text)
                if not isinstance(raw, dict):
                    raise ValueError("Judge response must be a JSON object")
                if raw.get("action") == "calculate":
                    if measure not in CALCULATOR_ROLES:
                        raise ValueError("This role has no calculator access")
                    batch = CalculateResponse.model_validate(raw)
                    existing = {item["request"]["id"] for item in record["calculations"]}
                    ids = [item.id for item in batch.checks]
                    if len(set(ids)) != len(ids) or existing.intersection(ids):
                        raise ValueError("Calculator ids must be unique across this role")
                    if len(existing) + len(ids) > self.max_calculations:
                        return self._failure(
                            record,
                            "budget_exhausted",
                            ValueError("Calculator check budget exhausted"),
                        )
                    for request in batch.checks:
                        _verify_quotes(request.task_quotes, payload["student_task"])
                    results = []
                    for request in batch.checks:
                        result = calculate_condition(
                            request.calculation.model_dump(), request.values, units=request.units
                        )
                        entry = {"request": request.model_dump(), "result": result}
                        record["calculations"].append(entry)
                        results.append(entry)
                        if result["status"] in {"unknown", "unsupported"}:
                            logger.warning(
                                "PF %s check %s: %s", measure, request.id, result["reason"]
                            )
                    messages.extend(
                        [
                            {"role": "assistant", "content": response.text},
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {"calculator_results": results}, ensure_ascii=False
                                ),
                            },
                        ]
                    )
                    continue
                final = FinalResponse[SCHEMAS[measure]].model_validate(raw)
                _validate_judgment(final.judgment, payload, record["calculations"])
            except (ValidationError, ValueError) as exc:
                return self._failure(record, "invalid_response", exc)
            record.update(
                {
                    "status": "assessed",
                    "value": final.judgment.verdict,
                    "judgment": final.judgment.model_dump(),
                }
            )
            return record
        return self._failure(record, "budget_exhausted", ValueError("Model call budget exhausted"))

    @staticmethod
    def _failure(record: dict, status: str, error: Exception) -> dict:
        logger.error("PF %s %s: %s", record["measure"], status, error)
        record.update(
            {
                "status": status,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        )
        return record

    def evaluate(self, task: str | dict, target: str, context: dict) -> dict:
        prepared = prepare_input(task, target, context)
        records = {}
        rubric = load_rubric()
        for measure in MEASURES:
            prerequisite = rubric["measures"][measure].get("requires")
            if prerequisite:
                parent = records[prerequisite["measure"]]
                if parent["status"] != "assessed" or parent["value"] != prerequisite["value"]:
                    records[measure] = {
                        "measure": measure,
                        "status": "not_assessed",
                        "value": "not_assessed",
                        "judgment": None,
                        "input": None,
                        "calls": [],
                        "calculations": [],
                        "error": None,
                        "prerequisite": {
                            "measure": prerequisite["measure"],
                            "value": parent["value"],
                            "status": parent["status"],
                        },
                    }
                    continue
            approaches = None
            if measure == "familiar_approach_limits":
                approaches = records["prior_knowledge_accessibility"]["judgment"]["approaches"]
            records[measure] = self.evaluate_role(
                measure, role_input(measure, prepared, approaches)
            )
        accessibility = records["prior_knowledge_accessibility"]
        limits = records["familiar_approach_limits"]
        outcomes = (
            Counter(review["outcome"] for review in limits["judgment"]["approach_reviews"])
            if limits["status"] == "assessed"
            else None
        )
        return {
            "version": VERSION,
            "rubric_sha256": hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
            "calibrated": False,
            "input_sha256": hashlib.sha256(
                json.dumps(prepared, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            "measures": records,
            "approach_counts": {
                "identified_starts": len(accessibility["judgment"]["approaches"])
                if accessibility["status"] == "assessed"
                else None,
                "reviewed": sum(outcomes.values()) if outcomes is not None else None,
                "with_limits": outcomes["limit"] if outcomes is not None else None,
                "meets_demands": outcomes["meets_demands"] if outcomes is not None else None,
                "unresolved": outcomes["unresolved"] if outcomes is not None else None,
                "scope": (
                    "Identified/checked methods, not a complete inventory or learner frequencies."
                ),
            },
        }


def summarize(results: list[dict]) -> dict:
    rubric = load_rubric()
    rows = {}
    for measure, contract in rubric["measures"].items():
        records = [result["measures"][measure] for result in results]
        prerequisite = contract.get("requires")
        eligible = (
            sum(
                result["measures"][prerequisite["measure"]]["status"] == "assessed"
                and result["measures"][prerequisite["measure"]]["value"] == prerequisite["value"]
                for result in results
            )
            if prerequisite
            else len(results)
        )
        reasons = Counter(
            f"{record['prerequisite']['status']}:{record['prerequisite']['value'] or 'no_verdict'}"
            for record in records
            if record["status"] == "not_assessed"
        )
        rows[measure] = {
            "eligible_tasks": eligible,
            "assessed_tasks": sum(record["status"] == "assessed" for record in records),
            "value_counts": {
                value: sum(record["value"] == value for record in records)
                for value in contract["values"]
            },
            "execution_status_counts": dict(Counter(record["status"] for record in records)),
            "not_assessed_reasons": dict(reasons),
        }
    failures = sum(
        record["status"] not in {"assessed", "not_assessed"}
        for result in results
        for record in result["measures"].values()
    )
    return {
        "version": VERSION,
        "calibrated": False,
        "tasks": len(results),
        "failed_role_executions": failures,
        "measures": rows,
        "model_calls": sum(
            len(record["calls"]) for result in results for record in result["measures"].values()
        ),
        "calculator_checks": sum(
            len(record["calculations"])
            for result in results
            for record in result["measures"].values()
        ),
        "limitation": "Conditional counts, not an overall PF score or learner outcomes.",
    }
