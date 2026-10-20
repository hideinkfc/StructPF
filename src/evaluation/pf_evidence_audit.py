"""Task-text-only PF evidence supplement; never a replacement rubric or learner proof."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError, model_validator

from src.evaluation.pf_rubric import learner_context

PROMPT_PATH = Path(__file__).parent / "prompts" / "pf_evidence_audit_v1.yaml"
VERSION = "pf-evidence-audit/v1"
ANALYSIS_VERSION = "pf-evidence-aggregation/v1.3"
PARSER_VERSION = "pf-evidence-parser/v1.3"
PARSED_STATUSES = ("parsed", "partially_parsed")
Status = Literal["supported", "partial", "not_evidenced", "unknown"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FINDINGS = (
    "target_relevance",
    "accessible_start",
    "task_specification",
    "preserved_discovery",
    "consequential_choice",
    "distinct_mathematical_ideas",
    "useful_prior_contrast",
)
CHECKLIST = (
    "mathematics",
    "target_relevance",
    "accessible_start",
    "preserved_discovery",
    "consequential_choice",
)
ANCHORS = ("APK", "MR", "OE")
HIGH_SCORE_SCREEN = 14


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Finding(StrictModel):
    status: Status
    task_quotes: list[Text]
    reason: Text
    counterevidence: str

    @model_validator(mode="after")
    def evidence_required(self) -> "Finding":
        if self.status != "unknown" and not self.task_quotes:
            raise ValueError("A substantive finding requires an exact task quote")
        return self


class Approach(StrictModel):
    label: Text
    category: Literal["mathematical_idea", "algorithm", "representation"]
    action: Text
    underlying_idea: Text
    starting_resource: Text
    task_quote: Text


class Diversity(Finding):
    approaches: list[Approach]

    @model_validator(mode="after")
    def two_ideas(self) -> "Diversity":
        if self.status == "supported":
            ideas = {
                route.underlying_idea.casefold()
                for route in self.approaches
                if route.category == "mathematical_idea"
            }
            if len(ideas) < 2:
                raise ValueError("Supported idea diversity needs two explicit idea routes")
        return self


class Witness(StrictModel):
    expression: Text
    claimed_value: Text
    task_quotes: list[Text]
    interpretation: Text


class ConcernWitness(Witness):
    @model_validator(mode="after")
    def quoted_operands_required(self) -> "ConcernWitness":
        if not self.task_quotes:
            raise ValueError("A structured concern witness requires source quotes")
        return self


class Mathematics(StrictModel):
    status: Literal["model_recomputed", "concern", "unknown"]
    task_quotes: list[Text]
    reason: Text
    counterevidence: str
    witnesses: list[Witness]
    concerns: list[Text | ConcernWitness]

    @model_validator(mode="after")
    def meaningful_review(self) -> "Mathematics":
        if self.status == "model_recomputed" and not self.witnesses:
            raise ValueError("model_recomputed requires a mathematical witness")
        if self.status == "concern" and not self.concerns:
            raise ValueError("A math concern requires a concrete explanation")
        return self


class AnchorChecks(StrictModel):
    APK: Finding
    MR: Finding
    OE: Finding


class PFEvidenceAudit(StrictModel):
    target_relevance: Finding
    accessible_start: Finding
    task_specification: Finding
    preserved_discovery: Finding
    consequential_choice: Finding
    distinct_mathematical_ideas: Diversity
    useful_prior_contrast: Finding
    mathematics: Mathematics
    original_high_anchor_support: AnchorChecks


def sha256(data: str | bytes) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def load_prompt() -> dict:
    prompt = yaml.safe_load(PROMPT_PATH.read_text())
    if prompt.get("version") != VERSION or not isinstance(prompt.get("system"), str):
        raise ValueError("Unexpected PF evidence audit version")
    return prompt


def student_text(task: dict) -> str:
    if not isinstance(task, dict):
        raise ValueError("No usable student task object was supplied")
    parts = [task.get(key) for key in ("title", "body", "question")]
    if not all(isinstance(part, str) and part.strip() for part in parts):
        raise ValueError("Task requires nonempty title, body and question")
    return "\n\n".join(parts)


def evidence_audit_input(entry: dict) -> str:
    """Only student task, common target and allowlisted prior context reach a judge."""
    target = entry.get("learning_target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("learning_target must be nonempty")
    context = entry["learner_context"]
    if (
        isinstance(context, dict)
        and context.get("recently_taught")
        and context.get("assumed_prior_knowledge") is None
    ):
        raise ValueError(
            "recently_taught would be lost by the auditor allowlist; adapt the frozen "
            "history to assumed_prior_knowledge before auditing"
        )
    return json.dumps(
        {
            "learning_target": target,
            "learner_context": learner_context(context),
            "student_task": student_text(entry["task"]),
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def quote_anchor(quote: str, text: str) -> dict:
    start = text.find(quote)
    return {
        "quote": quote,
        "verified": start >= 0,
        "start": start if start >= 0 else None,
        "end": start + len(quote) if start >= 0 else None,
    }


def _numbers(text: str) -> set[Fraction]:
    return {
        Fraction(match.group(0).replace(",", ""))
        for match in re.finditer(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?", text)
    }


def exact_arithmetic(expression: str) -> tuple[Fraction, list[Fraction]]:
    """Parse bounded arithmetic literals/operators with Fractions, not Python eval."""
    if len(expression) > 512:
        raise ValueError("Expression exceeds the bounded arithmetic limit")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError("Too many arithmetic nodes")
    literals: list[Fraction] = []

    def visit(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            token = ast.get_source_segment(expression, node)
            if token is None or not re.fullmatch(r"\d+(?:\.\d+)?", token):
                raise ValueError("Only decimal numeric literals are supported")
            value = Fraction(token)
            literals.append(value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            else:
                value = left / right
        else:
            raise ValueError("Only supplied arithmetic literals and + - * / are supported")
        if max(abs(value.numerator), value.denominator) > 10**15:
            raise ValueError("Arithmetic value exceeds bounded size")
        return value

    return visit(tree.body), literals


def check_witness(witness: dict, text: str) -> dict:
    anchors = [quote_anchor(quote, text) for quote in witness["task_quotes"]]
    if not anchors or not all(anchor["verified"] for anchor in anchors):
        return {"status": "unknown", "reason": "Witness source quote absent or not exact"}
    try:
        computed, operands = exact_arithmetic(witness["expression"])
        claimed, _ = exact_arithmetic(witness["claimed_value"])
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as error:
        return {"status": "unknown", "reason": f"{type(error).__name__}: {error}"}
    available = _numbers("\n".join(witness["task_quotes"]))
    if not all(abs(number) in available or number in (0, 1) for number in operands):
        return {
            "status": "unknown",
            "reason": "An expression operand is not supplied in its exact task quotes",
            "computed_value": str(computed),
        }
    return {
        "status": "verified_arithmetic" if computed == claimed else "arithmetic_mismatch",
        "computed_value": str(computed),
        "claimed_value": str(claimed),
        "scope": "Exact arithmetic only; neither task validity nor interpretation is proven",
    }


def parse_evidence_audit(raw: str, text: str) -> dict:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Audit response must be a JSON object")
    field_errors = {}
    audit = {}
    expected = {*FINDINGS, "mathematics", "original_high_anchor_support"}
    extras = sorted(set(payload) - expected)
    if extras:
        field_errors["_envelope"] = {
            "type": "UnexpectedFields", "fields": extras,
            "raw_data": {name: payload[name] for name in extras},
        }

    def parse_field(name: str, value: object, model: type[BaseModel]) -> dict:
        try:
            return model.model_validate(value).model_dump()
        except ValidationError as error:
            field_errors[name] = {
                "type": "ValidationError",
                "errors": error.errors(
                    include_url=False, include_context=False, include_input=False
                ),
                "raw_data": value,
            }
            unknown = {
                "status": "unknown", "task_quotes": [],
                "reason": f"Field validation failed for {name}; see field_errors.",
                "counterevidence": "",
            }
            if model is Diversity:
                unknown["approaches"] = []
            if model is Mathematics:
                unknown.update(witnesses=[], concerns=[])
            return unknown

    for name in FINDINGS:
        model = Diversity if name == "distinct_mathematical_ideas" else Finding
        audit[name] = parse_field(name, payload.get(name), model)
    audit["mathematics"] = parse_field("mathematics", payload.get("mathematics"), Mathematics)
    anchors = payload.get("original_high_anchor_support")
    audit["original_high_anchor_support"] = {}
    for name in ANCHORS:
        value = anchors.get(name) if isinstance(anchors, dict) else anchors
        audit["original_high_anchor_support"][name] = parse_field(f"anchor_{name}", value, Finding)
    if isinstance(anchors, dict) and set(anchors) - set(ANCHORS):
        field_errors["_anchor_envelope"] = {
            "type": "UnexpectedFields", "fields": sorted(set(anchors) - set(ANCHORS)),
            "raw_data": anchors,
        }
    validated_fields = [
        name for name in (*FINDINGS, "mathematics", *(f"anchor_{a}" for a in ANCHORS))
        if name not in field_errors
    ]
    fidelity = {}
    findings = {name: audit[name] for name in (*FINDINGS, "mathematics")}
    findings.update(
        {f"anchor_{name}": value for name, value in audit["original_high_anchor_support"].items()}
    )
    for name, finding in findings.items():
        anchors = [quote_anchor(quote, text) for quote in finding["task_quotes"]]
        fidelity[name] = {
            "anchors": anchors,
            "all_verified": bool(anchors) and all(item["verified"] for item in anchors),
        }
    approach_anchors = [
        quote_anchor(route["task_quote"], text)
        for route in audit["distinct_mathematical_ideas"]["approaches"]
    ]
    return {
        "status": (
            "field_validation_error" if not validated_fields
            else "partially_parsed" if field_errors else "parsed"
        ),
        "parser_version": PARSER_VERSION,
        "field_errors": field_errors,
        "validated_fields": validated_fields,
        "audit": audit,
        "quote_fidelity": fidelity,
        "approach_quote_anchors": approach_anchors,
        "mathematical_witness_checks": [
            check_witness(witness, text) for witness in audit["mathematics"]["witnesses"]
        ],
        "mathematical_concern_witness_checks": [
            check_witness(witness, text)
            for witness in audit["mathematics"]["concerns"] if isinstance(witness, dict)
        ],
        "math_status": audit["mathematics"]["status"],
        "scope": "computational_task_affordance_evidence_not_student_or_human_validation",
    }


def _decision(result: dict | None, name: str) -> str:
    if not result or result.get("status") not in PARSED_STATUSES:
        return "unknown"
    if name in result.get("field_errors", {}):
        return "unknown"
    if name.startswith("anchor_"):
        finding = result["audit"]["original_high_anchor_support"][name[7:]]
    else:
        finding = result["audit"][name]
    if not result["quote_fidelity"][name]["all_verified"]:
        return "unknown"
    if name == "task_specification" and finding["status"] == "not_evidenced" and (
        result["audit"]["mathematics"]["status"] == "concern"
        or result["audit"]["mathematics"]["concerns"]
        or any(
            check["status"] == "arithmetic_mismatch"
            for check in result["mathematical_witness_checks"]
        )
    ):
        return "unknown"
    if name == "mathematics":
        if finding["concerns"]:
            return "unknown"
        checks = result["mathematical_witness_checks"]
        if finding["status"] == "model_recomputed" and checks and all(
            check["status"] == "verified_arithmetic" for check in checks
        ):
            return "pass"
        # Concern interpretation needs exact recheck and/or a human review.
        return "unknown"
    if name == "distinct_mathematical_ideas" and finding["status"] == "supported":
        if not all(item["verified"] for item in result["approach_quote_anchors"]):
            return "unknown"
    return {"supported": "pass", "not_evidenced": "concern"}.get(finding["status"], "unknown")


def consensus(decisions: list[str]) -> str:
    if len(decisions) != 2:
        return "unknown"
    return decisions[0] if decisions[0] == decisions[1] else "unknown"


def aggregate_audits(catalog: list[dict], results: list[dict], judges: list[str]) -> dict:
    """Paired, quote-checked two-judge rates retaining all catalog denominators."""
    if len(judges) != 2 or len(set(judges)) != 2:
        raise ValueError("Consensus requires exactly two distinct judge selectors")
    catalog_ids = [entry["task_id"] for entry in catalog]
    if len(set(catalog_ids)) != len(catalog_ids):
        raise ValueError("Catalog task IDs must be unique")
    indexed = {}
    for result in results:
        if result["task_id"] not in catalog_ids or result["judge"] not in judges:
            raise ValueError("Result does not belong to this catalog/judge pair")
        key = (result["task_id"], result["judge"])
        if key in indexed:
            raise ValueError(f"Duplicate task/judge result: {key}")
        indexed[key] = result
    rows = []
    for entry in catalog:
        pair = [indexed.get((entry["task_id"], judge)) for judge in judges]
        usable_judgments = sum(
            bool(result and result.get("status") in PARSED_STATUSES) for result in pair
        )
        try:
            student_text(entry.get("task"))
        except ValueError as error:
            availability = "task_unavailable"
            availability_reason = str(error)
            usable_judgments = 0
        else:
            availability = "available" if usable_judgments == 2 else "audit_unavailable"
            availability_reason = (
                None if availability == "available" else "; ".join(
                    f"{judge}: {result.get('status', 'missing_status') if result else 'missing'}"
                    for judge, result in zip(judges, pair)
                    if not result or result.get("status") not in PARSED_STATUSES
                )
            )
        decisions = {
            name: [
                _decision(result, name) if availability != "task_unavailable" else "unknown"
                for result in pair
            ]
            for name in (*FINDINGS, "mathematics", *(f"anchor_{a}" for a in ANCHORS))
        }
        raw_statuses = {
            name: [
                (
                    result["audit"]["original_high_anchor_support"][name[7:]]["status"]
                    if name.startswith("anchor_") else result["audit"][name]["status"]
                ) if result and result.get("status") in PARSED_STATUSES
                and name not in result.get("field_errors", {}) else None
                for result in pair
            ]
            for name in decisions
        }
        agreed = {name: consensus(values) for name, values in decisions.items()}
        individual_checklists = []
        for index in range(2):
            values = [decisions[name][index] for name in CHECKLIST]
            individual_checklists.append(
                "concern" if "concern" in values
                else "pass" if set(values) == {"pass"} else "unknown"
            )
        # A concern must agree on the same component, not two different failures.
        checklist = (
            "concern" if any(agreed[name] == "concern" for name in CHECKLIST)
            else "pass" if all(agreed[name] == "pass" for name in CHECKLIST) else "unknown"
        )
        core_errors = [
            f"{judge}: {name}"
            for judge, result in zip(judges, pair) if result
            for name in CHECKLIST if name in result.get("field_errors", {})
        ]
        if availability == "available" and checklist == "unknown" and core_errors:
            availability = "audit_unavailable"
            availability_reason = "Invalid checklist fields: " + "; ".join(core_errors)
        property_availability = {}
        property_failure_reasons = {}
        for name in decisions:
            reasons = [
                f"{judge}: missing audit" if not result
                else f"{judge}: {result['status']}" if result["status"] not in PARSED_STATUSES
                else f"{judge}: invalid {name}" if name in result.get("field_errors", {})
                else None
                for judge, result in zip(judges, pair)
            ]
            reasons = [reason for reason in reasons if reason is not None]
            property_availability[name] = (
                "task_unavailable" if availability == "task_unavailable"
                else "audit_unavailable" if reasons else "available"
            )
            property_failure_reasons[name] = (
                availability_reason if availability == "task_unavailable"
                else "; ".join(reasons) if reasons else None
            )
        baseline = entry.get("original_rating") or {}
        scores = baseline.get("scores") or {}
        high = isinstance(scores.get("TOTAL"), int) and scores["TOTAL"] >= HIGH_SCORE_SCREEN
        tensions = [
            name for name in ANCHORS
            if scores.get(name) == 3 and agreed[f"anchor_{name}"] == "concern"
        ]
        extra = [name for name in FINDINGS if agreed[name] == "concern"]
        math_concerns = [
            judge for judge, result in zip(judges, pair)
            if result and result.get("status") in PARSED_STATUSES
            and (
                result["audit"]["mathematics"]["status"] == "concern"
                or result["audit"]["mathematics"]["concerns"]
            )
        ]
        rows.append(
            {
                "task_id": entry["task_id"],
                "arm": entry.get("arm", "unspecified"),
                "case": entry.get("case"),
                "repeat": entry.get("repeat"),
                "source_path": entry.get("source_path"),
                "availability": availability,
                "availability_reason": availability_reason,
                "scheduled_judgments": 2,
                "field_validation_errors": {
                    judge: result.get("field_errors", {}) if result else {}
                    for judge, result in zip(judges, pair)
                },
                "property_availability": property_availability,
                "property_failure_reasons": property_failure_reasons,
                "original_scores": scores or None,
                "original_high_score_screen": high if scores else None,
                "consensus": agreed,
                "consensus_values": {
                    name: {"pass": True, "concern": False, "unknown": None}[value]
                    for name, value in agreed.items()
                },
                "individual_decisions": decisions,
                "judge_statuses": raw_statuses,
                "fixed_checklist": checklist,
                "fixed_checklist_value": {
                    "pass": True, "concern": False, "unknown": None,
                }[checklist],
                "math_support_label": (
                    "model_supported_no_confirmed_concern"
                    if agreed["mathematics"] == "pass" else "unknown_or_unresolved"
                ),
                "mathematical_witness_statuses": [
                    [
                        check["status"] for check in result["mathematical_witness_checks"]
                    ] if result and result.get("status") in PARSED_STATUSES else []
                    for result in pair
                ],
                "individual_checklists": individual_checklists,
                "agreed_additional_concerns": extra,
                "agreed_original_anchor_tensions": tensions,
                "unresolved_mathematical_concern_judges": math_concerns,
                "usable_judgments": usable_judgments,
            }
        )
    rates = {}
    for name in (*FINDINGS, "mathematics", "fixed_checklist"):
        counts = Counter(
            row["fixed_checklist"] if name == "fixed_checklist" else row["consensus"][name]
            for row in rows
        )
        rates[name] = {
            "pass": counts["pass"],
            "concern": counts["concern"],
            "unknown": counts["unknown"],
            "denominator_all_catalog_tasks": len(rows),
            "denominator_delivered_property_audits": sum(
                (
                    row["availability"] if name == "fixed_checklist"
                    else row["property_availability"][name]
                ) == "available" for row in rows
            ),
            "unknown_due_to_unavailability": sum(
                (
                    row["fixed_checklist"] if name == "fixed_checklist"
                    else row["consensus"][name]
                ) == "unknown" and (
                    row["availability"] if name == "fixed_checklist"
                    else row["property_availability"][name]
                ) != "available" for row in rows
            ),
            "substantive_unknown_or_disputed_available": sum(
                (
                    row["fixed_checklist"] if name == "fixed_checklist"
                    else row["consensus"][name]
                ) == "unknown" and (
                    row["availability"] if name == "fixed_checklist"
                    else row["property_availability"][name]
                ) == "available" for row in rows
            ),
            "pass_rate_all_tasks": counts["pass"] / len(rows) if rows else None,
            "pass_rate_known_only": (
                counts["pass"] / (counts["pass"] + counts["concern"])
                if counts["pass"] + counts["concern"] else None
            ),
        }
    agreement = {}
    for name in (*FINDINGS, "mathematics", *(f"anchor_{a}" for a in ANCHORS)):
        pairs = [
            row["individual_decisions"][name] for row in rows if row["usable_judgments"] == 2
        ]
        exact = sum(values[0] == values[1] for values in pairs)
        known = [values for values in pairs if "unknown" not in values]
        agreement[name] = {
            "matched_categories": exact,
            "paired_parsed_denominator": len(pairs),
            "agreement_including_unknown": exact / len(pairs) if pairs else None,
            "known_pair_denominator": len(known),
            "agreement_known_pairs": (
                sum(values[0] == values[1] for values in known) / len(known) if known else None
            ),
            "unknown_in_either": len(pairs) - len(known),
        }
        raw_pairs = [
            row["judge_statuses"][name] for row in rows
            if all(value is not None for value in row["judge_statuses"][name])
        ]
        agreement[name]["raw_status_pair_denominator"] = len(raw_pairs)
        agreement[name]["matched_raw_statuses"] = sum(
            values[0] == values[1] for values in raw_pairs
        )
        agreement[name]["raw_status_agreement"] = (
            agreement[name]["matched_raw_statuses"] / len(raw_pairs) if raw_pairs else None
        )
    high_rows = [row for row in rows if row["original_high_score_screen"] is True]
    totals = [
        row["original_scores"]["TOTAL"] for row in rows
        if row["original_scores"] and row["original_scores"].get("TOTAL") is not None
    ]
    checked_quotes = [
        anchor
        for result in results if result.get("status") in PARSED_STATUSES
        for finding in result["quote_fidelity"].values() for anchor in finding["anchors"]
    ]
    return {
        "version": VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "parser_version": PARSER_VERSION,
        "scope": "same-task_model_agreement_with_exact_quote_fidelity_not_human_proof",
        "judges": judges,
        "judge_independence": (
            "Two model series in the same OpenAI family; not different vendors or human judges"
        ),
        "catalog_tasks": len(rows),
        "availability_counts": {
            status: sum(row["availability"] == status for row in rows)
            for status in ("available", "task_unavailable", "audit_unavailable")
        },
        "delivered_denominators": {
            "scheduled_tasks": len(rows),
            "student_tasks_supplied": sum(
                row["availability"] != "task_unavailable" for row in rows
            ),
            "paired_parseable_audits": sum(row["availability"] == "available" for row in rows),
            "interpretation": (
                "Unavailable task/audit entries remain scheduled unknowns, "
                "not judged mathematical failures"
            ),
        },
        "scheduled_judgments": len(rows) * 2,
        "requested_judgments": len(rows) * 2,
        "recorded_judgments": len(results),
        "parsed_judgments": sum(result.get("status") in PARSED_STATUSES for result in results),
        "fully_valid_judgments": sum(result.get("status") == "parsed" for result in results),
        "partially_valid_judgments": sum(
            result.get("status") == "partially_parsed" for result in results
        ),
        "field_validation_error_counts": dict(Counter(
            name for result in results for name in result.get("field_errors", {})
        )),
        "missing_judgments": len(rows) * 2 - len(results),
        "error_status_counts": dict(Counter(
            result.get("status", "missing")
            for result in results if result.get("status") not in PARSED_STATUSES
        )),
        "rates": rates,
        "agreement": agreement,
        "judge_status_distributions": {
            judge: {
                name: dict(Counter(
                    row["judge_statuses"][name][index] or "unavailable" for row in rows
                ))
                for name in (*FINDINGS, "mathematics", *(f"anchor_{a}" for a in ANCHORS))
            }
            for index, judge in enumerate(judges)
        },
        "quote_fidelity": {
            "verified_exact_quotes": sum(anchor["verified"] for anchor in checked_quotes),
            "quoted_spans_checked": len(checked_quotes),
        },
        "original_distribution": {
            "paired_rating_count": len(totals),
            "totals": dict(sorted(Counter(totals).items())),
            "ceiling_15_count": totals.count(15),
            "high_score_screen_total_at_least": HIGH_SCORE_SCREEN,
            "high_score_count": len(high_rows),
            "interpretation": (
                "14 is a prespecified screening flag, not a PF quality truth threshold"
            ),
        },
        "same_task_high_score_findings": {
            "denominator": len(high_rows),
            "with_agreed_original_anchor_tension": sum(
                bool(row["agreed_original_anchor_tensions"]) for row in high_rows
            ),
            "with_agreed_additional_concern": sum(
                bool(row["agreed_additional_concerns"]) for row in high_rows
            ),
            "additional_concern_without_anchor_tension": sum(
                bool(row["agreed_additional_concerns"])
                and not row["agreed_original_anchor_tensions"]
                for row in high_rows
            ),
            "interpretation": (
                "Anchor tensions are model-agreed candidates for review, "
                "not proof the original score is false. "
                "Additional concerns do not contradict the historical rubric by themselves."
            ),
        },
        "fixed_checklist_definition": {
            "components": list(CHECKLIST),
            "interpretation": (
                "Conjunction of five task-evidence hypotheses, NOT all PF requirements "
                "or observed outcomes. "
                "Mathematics pass is model_recomputed plus exact source-grounded arithmetic, "
                "not deterministic task proof. "
                "Distinct ideas remain a separate outcome."
            ),
        },
        "rows": rows,
    }
