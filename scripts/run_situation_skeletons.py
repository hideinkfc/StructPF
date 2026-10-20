"""D2 design search: brief selection, concrete data, exact checks and bounded repair.

For one prior-recommendation case, sample k design briefs before declaring typed
quantities. Select a brief and preserve its learning opportunity through
data selection and value-only repair. Saved historical skeletons
remain readable for explicit replanning without regenerating the task design.

Usage:
    ./.venv/bin/python scripts/run_situation_skeletons.py \
        --case kapur_average_speed_g7_singapore \
        --from-d1 experiments/results/prior_recommendations/d1.json
    ./.venv/bin/python scripts/run_situation_skeletons.py \
        --case loibl_variance_g10_nrw --k 8 --model gpt41mini \
        --use-expert-resources
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.learning_commons_context import (  # noqa: E402
    REFERENCE_INSTRUCTION,
    format_selected_references,
    selected_references,
)
from scripts.prior_methods.common import chat_json, load_client  # noqa: E402
from src.generation.fill_check import (  # noqa: E402
    check_fill,
    checker_capability_contract,
    validate_plan_expressions,
)
from src.generation.situation_skeletons import (  # noqa: E402
    ALLOWED_VALUE_DOMAINS,
    MathPlan,
    Quantity,
    number_requirements_from_payload,
    prior_contrast_intent_from_payload,
    skeleton_from_payload,
    skeleton_from_proposal_payload,
    skeleton_metadata_errors,
    skeleton_schema_contract,
)

PROMPTS_PATH = ROOT / "src" / "generation" / "prompts" / "situation_skeletons.yaml"
CASES_PATH = ROOT / "experiments" / "configs" / "prior_recommendation_cases.json"
RESULTS_DIR = ROOT / "experiments" / "results" / "situation_skeletons"

DEFAULT_K = 6
PROPOSE_TEMPERATURE = 0.9
JUDGE_TEMPERATURE = 0.0
PROPOSE_MAX_TOKENS = 4000
JUDGE_MAX_TOKENS = 6000
FILL_MAX_TRIES = 3
PLAN_RETRY_MAX = 1
PROPOSAL_RETRY_MAX = 1


def _prompts() -> dict[str, str]:
    prompts = yaml.safe_load(PROMPTS_PATH.read_text())
    if not isinstance(prompts, dict):
        raise ValueError(f"Prompt file must contain an object: {PROMPTS_PATH}")
    required = {
        "PROPOSE_SKELETON_SYSTEM",
        "PROPOSE_SKELETON_USER",
        "REPAIR_PROPOSAL_SYSTEM",
        "REPAIR_PROPOSAL_USER",
        "REPAIR_SELECTED_SYSTEM",
        "REPAIR_SELECTED_USER",
        "JUDGE_SKELETONS_SYSTEM",
        "JUDGE_SKELETONS_USER",
        "PLAN_SKELETON_SYSTEM",
        "PLAN_SKELETON_USER",
        "REVIEW_PLAN_SYSTEM",
        "REVIEW_PLAN_USER",
        "FILL_SKELETON_SYSTEM",
        "FILL_SKELETON_USER",
        "WRITE_TASK_SYSTEM",
        "WRITE_TASK_USER",
    }
    missing = required - prompts.keys()
    if missing:
        raise ValueError(f"Missing prompts: {sorted(missing)}")
    contract_stages = {
        "PROPOSE_SKELETON_SYSTEM",
        "REPAIR_PROPOSAL_SYSTEM",
        "REPAIR_SELECTED_SYSTEM",
        "JUDGE_SKELETONS_SYSTEM",
        "PLAN_SKELETON_SYSTEM",
        "REVIEW_PLAN_SYSTEM",
        "FILL_SKELETON_SYSTEM",
    }
    missing_contract = sorted(
        key for key in contract_stages if "{checker_contract}" not in prompts[key]
    )
    if missing_contract:
        raise ValueError(
            "Checker contract placeholder missing from prompts: " + ", ".join(missing_contract)
        )
    missing_skeleton_contract = sorted(
        key
        for key in (
            "PROPOSE_SKELETON_SYSTEM",
            "REPAIR_PROPOSAL_SYSTEM",
            "REPAIR_SELECTED_SYSTEM",
        )
        if "{skeleton_contract}" not in prompts[key]
    )
    if missing_skeleton_contract:
        raise ValueError(
            "Skeleton schema placeholder missing from prompts: "
            + ", ".join(missing_skeleton_contract)
        )
    repair_required = {
        "REPAIR_PROPOSAL_SYSTEM": (
            "{checker_contract}",
            "{skeleton_contract}",
            "{proposal_feedback}",
            "Repair the proposed",
        ),
        "REPAIR_SELECTED_SYSTEM": (
            "{checker_contract}",
            "{skeleton_contract}",
            "{original_design}",
            "{repair_diagnosis}",
            "Repair the selected",
        ),
        "REPAIR_SELECTED_USER": (
            "{target_concept}",
            "{case_context}",
            "{original_design}",
            "{repair_diagnosis}",
        ),
        "REPAIR_PROPOSAL_USER": (
            "{target_concept}",
            "{prior_context}",
            "{proposal_feedback}",
            "Return the same complete proposal shape",
        ),
    }
    missing_repair = sorted(
        key
        for key, required_values in repair_required.items()
        if any(value not in prompts[key] for value in required_values)
    )
    if missing_repair:
        raise ValueError(
            "Proposal repair prompt is missing required placeholders or prefix: "
            + ", ".join(missing_repair)
        )
    return prompts


def _render(template: str, values: dict[str, str]) -> str:
    output = re.sub(
        r"\{([A-Za-z_][A-Za-z_0-9]*)\}",
        lambda match: values.get(match[1], match[0]),
        template,
    )
    references = values.get("mathematical_references")
    if references and "{mathematical_references}" not in template:
        output += "\n\n" + REFERENCE_INSTRUCTION + references
    return output


def _output_path(requested: str, stem: str) -> Path:
    if requested:
        path = Path(requested)
        return path if path.is_absolute() else ROOT / path
    return RESULTS_DIR / f"{stem}.json"


def _format_quantities(skeleton, *, given_only: bool = False) -> str:
    quantities = skeleton.quantities
    if given_only:
        quantities = tuple(q for q in quantities if q.value_source == "given")
    return "\n".join(
        "  - "
        f"{q.name} ({q.role}, source={q.value_source}, unit={q.unit or 'unspecified'}"
        f"{', length=' + str(q.list_length) if q.list_length is not None else ''}, "
        f"domain={q.value_domain}): "
        f"{q.description}"
        for q in quantities
    )


def _format_approaches(skeleton) -> str:
    return json.dumps(
        [approach.to_dict() for approach in skeleton.approaches],
        ensure_ascii=False,
        indent=2,
    )


def _load_case(case_id: str) -> dict:
    cases = json.loads(CASES_PATH.read_text())
    for case in cases:
        if case["id"] == case_id:
            return case
    known = [c["id"] for c in cases]
    raise ValueError(f"Unknown case {case_id!r}. Known: {known}")


def _prior_methods(case: dict) -> list[str]:
    methods = case.get("expected_resources", [])
    if not methods:
        raise ValueError(f"Case {case['id']!r} has no expected_resources to seed from")
    return list(methods)


def _expert_prior_context(case: dict) -> dict[str, Any]:
    methods = _prior_methods(case)
    return {
        "source": "expert_case_config",
        "path": str(CASES_PATH),
        "case_id": case["id"],
        "condition": "expert",
        "recommendations": [
            {
                "resource": method,
                "taught_as": "Curated expert-listed prior resource.",
                "student_move": "",
                "falls_short_because": "",
                "relevance": "",
                "condition": "expert",
                "evidence_ids": [],
                "provenance": {
                    "type": "paper",
                    "source": case.get("gold_source", ""),
                    "page": None,
                    "document": None,
                    "source_url": None,
                    "evidence": case.get("evaluation_note", ""),
                },
            }
            for method in methods
        ],
    }


def _d1_result_for(
    payload: dict[str, Any],
    path: Path,
    case_id: str,
    condition: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = payload.get("records") or []
    if not isinstance(records, list):
        raise ValueError(f"D1 records must be a list in {path}")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one D1 record for case {case_id!r} in {path}; found {len(matches)}"
        )
    record = matches[0]
    conditions = record.get("conditions")
    if isinstance(conditions, dict):
        result = conditions.get(condition)
        if not isinstance(result, dict):
            raise ValueError(f"D1 record {case_id!r} has no {condition!r} condition in {path}")
    else:
        if record.get("condition") != condition:
            raise ValueError(
                f"D1 record {case_id!r} is {record.get('condition')!r}, "
                f"not requested condition {condition!r}"
            )
        result = record.get("result")
        if not isinstance(result, dict):
            raise ValueError(f"D1 record {case_id!r} has no result in {path}")
    return record, result


def _recommendations_from_d1(result: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    raw_items = result.get("recommendations") or result.get("resource_candidates") or []
    if not isinstance(raw_items, list):
        raise ValueError(f"D1 recommendations must be a list in {path}")
    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError(f"D1 recommendation must be an object in {path}")
        resource = str(item.get("resource") or "").strip()
        if not resource:
            raise ValueError(f"D1 recommendation is missing resource in {path}")
        if resource in seen:
            continue
        seen.add(resource)
        provenance = item.get("provenance")
        recommendations.append(
            {
                "resource": resource,
                "taught_as": str(item.get("taught_as") or "").strip(),
                "student_move": str(
                    item.get("student_move") or item.get("relevance") or ""
                ).strip(),
                "falls_short_because": str(item.get("falls_short_because") or "").strip(),
                "relevance": str(item.get("relevance") or "").strip(),
                "why_it_looks_applicable": str(item.get("why_it_looks_applicable") or "").strip(),
                "condition": str(result.get("condition") or "").strip(),
                "evidence_ids": list(item.get("evidence_ids") or []),
                "provenance": provenance if isinstance(provenance, dict) else {},
            }
        )
    if not recommendations:
        raise ValueError(f"D1 result in {path} has no resources")
    return recommendations


def _prior_context_from_d1(
    path: Path,
    case_id: str,
    condition: str = "grounded",
) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"D1 payload must be an object in {path}")
    record, result = _d1_result_for(payload, path, case_id, condition)
    context = {
        "source": "d1_recommendations",
        "path": str(path),
        "case_id": case_id,
        "condition": condition,
        "record_schema_version": record.get("schema_version"),
        "result_schema_version": result.get("schema_version"),
        "recommendations": _recommendations_from_d1(result, path),
    }
    if "learning_commons" in result:
        selected_references(result["learning_commons"])
        context["learning_commons"] = result["learning_commons"]
    return context


def _method_names(prior_context: dict[str, Any]) -> list[str]:
    names = [
        str(item.get("resource") or "").strip()
        for item in prior_context.get("recommendations", [])
        if isinstance(item, dict)
    ]
    names = [name for name in names if name]
    if not names:
        raise ValueError("Prior context has no resources")
    return names


def _format_prior_context(prior_context: dict[str, Any]) -> str:
    lines = []
    for item in prior_context.get("recommendations", []):
        provenance = item.get("provenance") or {}
        evidence_ids = ", ".join(item.get("evidence_ids") or []) or "none recorded"
        lines.append(
            "\n".join(
                [
                    f"- resource: {item.get('resource', '')}",
                    f"  taught_as: {item.get('taught_as', '') or 'not supplied'}",
                    f"  student_move: {item.get('student_move', '') or 'not supplied'}",
                    (
                        "  falls_short_because: "
                        f"{item.get('falls_short_because', '') or 'not supplied'}"
                    ),
                    f"  evidence_ids: {evidence_ids}",
                    (f"  provenance: {provenance.get('source', '') or provenance.get('type', '')}"),
                ]
            )
        )
    formatted = "\n\n".join(lines)
    if "learning_commons" in prior_context:
        references = format_selected_references(prior_context["learning_commons"])
        if references:
            formatted += "\n\n" + references
    return formatted


def _stored_prior_context(
    path: Path,
    expected_case_id: str | None = None,
) -> dict[str, Any] | None:
    payload = json.loads(path.read_text())
    context = payload.get("prior_context")
    if not isinstance(context, dict) and isinstance(payload.get("d2"), dict):
        context = payload["d2"].get("prior_context")
    if not isinstance(context, dict) and isinstance(payload.get("stages"), dict):
        d2 = payload["stages"].get("D2_D3")
        if isinstance(d2, dict):
            context = d2.get("prior_context")
    if isinstance(context, dict) and not context.get("case_id"):
        root_case = payload.get("case_id")
        if root_case:
            context = {**context, "case_id": root_case}
    if isinstance(context, dict) and expected_case_id:
        context_case = context.get("case_id")
        if context_case and context_case != expected_case_id:
            raise ValueError(
                f"stored prior_context is for case {context_case!r}, not {expected_case_id!r}"
            )
    return context if isinstance(context, dict) else None


def _stored_case_input(path: Path, expected_case_id: str) -> dict[str, Any] | None:
    """Load the case snapshot used by a saved run, when present."""
    payload = json.loads(path.read_text())
    case_input = payload.get("case_input")
    if not isinstance(case_input, dict):
        return None
    saved_id = case_input.get("id") or case_input.get("case_id")
    if saved_id and saved_id != expected_case_id:
        raise ValueError(f"stored case_input is for case {saved_id!r}, not {expected_case_id!r}")
    return case_input


def _propose_one(
    client,
    model: str,
    prompts: dict[str, str],
    case: dict,
    prior_context: dict[str, Any],
    *,
    initial_proposal: dict | None = None,
    initial_proposal_raw: str = "",
) -> dict:
    methods = _method_names(prior_context)
    saved_initial_payload: object = initial_proposal
    saved_initial_raw = initial_proposal_raw
    if isinstance(initial_proposal, dict) and "payload" in initial_proposal:
        saved_initial_payload = initial_proposal["payload"]
        saved_initial_raw = initial_proposal.get("raw_text", initial_proposal_raw)
    values = {
        "target_concept": case["target_concept"],
        "topic": case["topic"],
        "grade": str(case["grade"]),
        "subject": case["subject"],
        "checker_contract": checker_capability_contract(),
        "skeleton_contract": skeleton_schema_contract(),
        "prior_methods": "\n".join(f"- {m}" for m in methods),
        "prior_context": _format_prior_context(prior_context),
    }
    attempts: list[dict[str, Any]] = []
    feedback = ""
    original_payload: object = None
    original_raw = ""
    for attempt in range(1, PROPOSAL_RETRY_MAX + 2):
        repair = attempt > 1
        saved_first = attempt == 1 and initial_proposal is not None
        if saved_first:
            request = None
        else:
            request_values = {
                **values,
                "proposal_feedback": json.dumps(
                    {
                        "original_payload": original_payload,
                        "original_raw_text": original_raw,
                        "parser_errors": feedback.split("; ") if feedback else [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            }
            system_key = "REPAIR_PROPOSAL_SYSTEM" if repair else "PROPOSE_SKELETON_SYSTEM"
            user_key = "REPAIR_PROPOSAL_USER" if repair else "PROPOSE_SKELETON_USER"
            request = {
                "system": _render(
                    prompts.get(system_key, prompts.get("PROPOSE_SKELETON_SYSTEM", "")),
                    request_values,
                ),
                "user": _render(
                    prompts.get(user_key, prompts.get("PROPOSE_SKELETON_USER", "")),
                    request_values,
                ),
            }
        if saved_first:
            payload = saved_initial_payload
            raw = saved_initial_raw
            source = "saved_proposal"
        else:
            payload, raw = chat_json(
                client,
                model,
                request["system"],
                request["user"],
                temperature=PROPOSE_TEMPERATURE,
                max_tokens=PROPOSE_MAX_TOKENS,
            )
            source = "repaired" if repair else "generated"
        error = None
        attempt_record: dict[str, Any] = {
            "attempt": attempt,
            "raw_text": raw,
            "payload": payload,
            "prompts": request,
            "source": source,
            "error": error,
        }
        if not isinstance(payload, dict):
            error = "proposal payload must be a JSON object"
        else:
            try:
                skeleton = skeleton_from_proposal_payload(payload)
                resource_errors = _proposal_resource_errors(skeleton, methods)
                if resource_errors:
                    raise ValueError("; ".join(resource_errors))
            except (TypeError, ValueError) as exc:
                error = str(exc)
            else:
                attempt_record["skeleton"] = skeleton.to_dict()
                attempts.append(attempt_record)
                record: dict[str, Any] = {
                    "raw_text": raw,
                    "payload": payload,
                    "skeleton": skeleton.to_dict(),
                    "skeleton_obj": skeleton,
                    "attempts": attempts,
                }
                return record
        attempt_record["error"] = error
        attempts.append(attempt_record)
        feedback = str(error)
        if attempt == 1:
            original_payload = payload
            original_raw = raw
    final = attempts[-1]
    return {
        "raw_text": final["raw_text"],
        "payload": final["payload"],
        "error": final["error"],
        "attempts": attempts,
    }


def _proposal_resource_errors(skeleton, supplied_resources: list[str]) -> list[str]:
    """Reject approach links that are not present in the supplied prior context."""
    supplied = set(supplied_resources)
    errors = []
    for approach in skeleton.approaches:
        missing = sorted(set(approach.resources) - supplied)
        if missing:
            errors.append(
                f"approach {approach.id!r} references unsupported prior resource(s) "
                f"{missing}; supplied prior resources: {sorted(supplied)}"
            )
    return errors


def _judge_all(
    client,
    model: str,
    prompts: dict[str, str],
    case: dict,
    prior_context: dict[str, Any],
    skeletons: list,
) -> tuple[dict | None, str]:
    methods = _method_names(prior_context)
    rendered = []
    for cid, skeleton in enumerate(skeletons):
        d = skeleton.to_dict()
        quantities = "\n".join(
            (
                f"    - {q['name']} ({q['role']}, length={q.get('list_length')}, "
                f"domain={q.get('value_domain', 'positive')}, "
                f"unit={q.get('unit') or 'unspecified'}): "
                f"{q['description']}"
            )
            for q in d["quantities"]
        )
        rendered.append(
            f"  [id {cid}]\n"
            f"    quantities:\n{quantities}\n"
            f"    question: {d['question']}\n"
            f"    number_constraints: "
            f"{json.dumps(d.get('number_constraints', []), ensure_ascii=False)}\n"
            f"    approaches:\n{json.dumps(d.get('approaches', []), ensure_ascii=False)}"
        )
    values = {
        "target_concept": case["target_concept"],
        "topic": case["topic"],
        "grade": str(case["grade"]),
        "checker_contract": checker_capability_contract(),
        "prior_methods": "\n".join(f"- {m}" for m in methods),
        "prior_context": _format_prior_context(prior_context),
        "candidates": "\n\n".join(rendered),
    }
    return chat_json(
        client,
        model,
        _render(prompts["JUDGE_SKELETONS_SYSTEM"], values),
        _render(prompts["JUDGE_SKELETONS_USER"], values),
        temperature=JUDGE_TEMPERATURE,
        max_tokens=JUDGE_MAX_TOKENS,
    )


def _winner_from_result(
    path: Path,
    expected_case_id: str | None = None,
    winner_field: str = "winner",
):
    from src.generation.situation_skeletons import (
        JudgedCandidate,
        MethodVerdict,
    )

    d = json.loads(Path(path).read_text())
    source_case = d.get("case") or d.get("case_id")
    case_input = d.get("case_input")
    input_case = (
        case_input.get("id") or case_input.get("case_id") if isinstance(case_input, dict) else None
    )
    if source_case and input_case and source_case != input_case:
        raise ValueError(
            f"saved result case_id {source_case!r} disagrees with case_input id {input_case!r}"
        )
    if source_case is None:
        source_case = input_case
    if expected_case_id and source_case and source_case != expected_case_id:
        raise ValueError(f"saved winner is for case {source_case!r}, not {expected_case_id!r}")
    source = d
    if isinstance(d.get("stages"), dict) and isinstance(d["stages"].get("D2_D3"), dict):
        source = d["stages"]["D2_D3"]
    elif isinstance(d.get("d2"), dict):
        source = d["d2"]
    winners = source.get("winners", [])
    selected = source.get(winner_field)
    if isinstance(selected, dict):
        winners = [selected]
    elif not winners and isinstance(source.get("winner"), dict):
        winners = [source["winner"]]
    if not winners:
        raise ValueError(f"No winners stored in {path}")
    w = winners[0]
    sk = w["skeleton"]
    design_brief = None
    if "design_brief" in w:
        from src.generation.design_briefs import design_brief_from_payload

        design_brief = design_brief_from_payload(w["design_brief"])
    skeleton = (
        design_brief.skeleton(())
        if design_brief is not None and sk.get("quantities") == []
        else skeleton_from_payload(sk)
    )
    verdicts = tuple(MethodVerdict(**v) for v in w["verdicts"])
    requirements = number_requirements_from_payload(
        {
            "candidates": [
                {
                    "id": w["candidate_id"],
                    "number_requirements": w.get("number_requirements", []),
                }
            ]
        }
    )[w["candidate_id"]]
    return JudgedCandidate(
        candidate_id=w["candidate_id"],
        skeleton=skeleton,
        verdicts=verdicts,
        practice_item=w.get("practice_item", False),
        target_named=w.get("target_named", False),
        activation_count=w.get("activation_count", w.get("hook_count", 0)),
        number_requirements=requirements,
        selection_reason=w.get("selection_reason", ""),
        main_concern=w.get("main_concern"),
        selection_approaches=tuple(w.get("selection_approaches", [])),
        prior_contrast=prior_contrast_intent_from_payload(w.get("prior_contrast")),
        design_brief=design_brief,
    )


def _design_context(winner) -> dict[str, Any]:
    requirements = [
        {"id": f"original_{index}", "condition": condition, "purpose": None}
        for index, condition in enumerate(winner.skeleton.number_constraints)
    ]
    requirements.extend(
        {"id": f"judge_{index}", **requirement.to_dict()}
        for index, requirement in enumerate(getattr(winner, "number_requirements", ()))
    )
    context = {
        "selection_reason": getattr(winner, "selection_reason", ""),
        "selected_approaches": list(getattr(winner, "selection_approaches", ())),
        "main_concern": getattr(winner, "main_concern", None),
        "prior_contrast": (
            None
            if getattr(winner, "prior_contrast", None) is None
            else winner.prior_contrast.to_dict()
        ),
        "requirements": requirements,
    }
    if getattr(winner, "design_brief", None) is not None:
        context["original_design_brief"] = winner.design_brief.to_dict()
    return context


def _writer_student_context(case: dict, prior_context: dict[str, Any]) -> dict[str, Any]:
    """Keep the learner-facing context separate from D1 provenance metadata."""
    recommendations = []
    for item in prior_context.get("recommendations", []):
        if not isinstance(item, dict):
            continue
        recommendations.append(
            {
                "resource": item.get("resource", ""),
                "taught_as": item.get("taught_as", ""),
                "student_move": item.get("student_move", ""),
                "falls_short_because": item.get("falls_short_because", ""),
            }
        )
    return {
        "grade": str(case.get("grade", "")),
        "subject": case.get("subject", ""),
        "topic": case.get("topic", ""),
        "jurisdiction": case.get("jurisdiction", ""),
        "assumed_prior_knowledge": recommendations,
    }


def _intended_student_output(winner, plan: MathPlan) -> dict[str, Any]:
    """Describe the required student product without prescribing its method."""
    return {
        "question": winner.skeleton.question,
        "answer_rule": plan.answer_rule.to_dict(),
        "student_work": (
            "Answer the question, show how you worked, and explain why your approach "
            "or decision makes sense. When useful for this design, invite comparison "
            "of different solution approaches or representations and what they reveal. "
            "Do not require students to be wrong, use a wrong method, or invent a second "
            "method. Do not reduce the task to a bare numerical answer."
        ),
        "exploration_guidance": (
            "Do not reveal the selected operational prior move, an anticipated equality, "
            "winner, or target procedure before students explore, unless the fixed question "
            "already requires that relation."
            "Do not list or reveal the selected prior move or explain why it may fail."
        ),
    }


def _writer_design_context(winner, plan_review: dict | None) -> dict[str, Any]:
    context = _design_context(winner)
    context["plan_review"] = None
    if plan_review is not None:
        context["plan_review"] = {
            key: plan_review.get(key)
            for key in (
                "status",
                "question_answer_alignment",
                "approach_formula_alignment",
                "distinct_approaches",
                "constraints_covered",
                "requirement_coverage",
                "issues",
            )
        }
    return context


def _writer_context(
    case: dict,
    prior_context: dict[str, Any],
    winner,
    plan: MathPlan,
    fill: dict,
    plan_review: dict | None,
) -> dict[str, Any]:
    context = {
        "student_context": _writer_student_context(case, prior_context),
        "target_concept": case["target_concept"],
        "approaches": [approach.to_dict() for approach in winner.skeleton.approaches],
        "task_design": {
            "quantities": [q.to_dict() for q in winner.skeleton.quantities],
            "question": winner.skeleton.question,
            "values": fill.get("values", {}),
            "math_plan": plan.to_dict(),
            "approaches": [approach.to_dict() for approach in winner.skeleton.approaches],
        },
        "intended_student_output": _intended_student_output(winner, plan),
        "design_context": _writer_design_context(winner, plan_review),
    }
    if "learning_commons" in prior_context:
        references = selected_references(prior_context["learning_commons"])
        if references:
            context["mathematical_references"] = references
    return context


def _blocked_task_payload(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocking_issues": [reason],
        "title": "",
        "body": "",
        "question": "",
    }


def _validate_task_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("writer response must be a JSON object")
    status = payload.get("status")
    if not isinstance(status, str) or status not in {"ready", "blocked"}:
        raise ValueError("writer status must be ready or blocked")
    issues = payload.get("blocking_issues")
    if not isinstance(issues, list) or any(
        not isinstance(issue, str) or not issue.strip() for issue in issues
    ):
        raise ValueError("writer blocking_issues must be a list of non-empty strings")
    if status == "ready" and issues:
        raise ValueError("writer marked task ready with blocking issues")
    if status == "blocked":
        if not issues:
            raise ValueError("blocked writer task must list a blocking issue")
        return payload
    for field in ("title", "body", "question"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"writer {field} must be a non-empty string")
    return payload


def _plan_winner(
    client,
    model,
    prompts,
    case,
    winner,
    prior_context: dict[str, Any],
    feedback: str = "",
    previous_plan: dict[str, Any] | None = None,
) -> tuple[dict | None, str]:
    request = _plan_request(
        prompts, case, winner, prior_context, feedback=feedback, previous_plan=previous_plan
    )
    return chat_json(
        client,
        model,
        request["system"],
        request["user"],
        temperature=0.0,
        max_tokens=JUDGE_MAX_TOKENS,
    )


def _plan_request(
    prompts,
    case,
    winner,
    prior_context: dict[str, Any],
    *,
    feedback: str = "",
    previous_plan: dict[str, Any] | None = None,
) -> dict[str, str]:
    values = {
        "target_concept": case["target_concept"],
        "question": winner.skeleton.question,
        "quantities": _format_quantities(winner.skeleton),
        "approaches": _format_approaches(winner.skeleton),
        "design_context": json.dumps(_design_context(winner), ensure_ascii=False, indent=2),
        "checker_contract": checker_capability_contract(),
        "prior_context": _format_prior_context(prior_context),
        "plan_feedback": json.dumps(
            {
                "previous_plan": previous_plan or {},
                "feedback": feedback.strip() or "first attempt",
            },
            ensure_ascii=False,
            indent=2,
        ),
    }
    return {
        "system": _render(prompts["PLAN_SKELETON_SYSTEM"], values),
        "user": _render(prompts["PLAN_SKELETON_USER"], values),
    }


def _review_plan(
    client,
    model,
    prompts,
    case,
    winner,
    plan: MathPlan,
    prior_context: dict[str, Any] | None = None,
    *,
    original_winner=None,
    repair_diagnosis: dict[str, Any] | None = None,
) -> tuple[dict | None, str, dict[str, str]]:
    values = {
        "target_concept": case["target_concept"],
        "grade": str(case.get("grade", "")),
        "question": winner.skeleton.question,
        "quantities": _format_quantities(winner.skeleton),
        "approaches": _format_approaches(winner.skeleton),
        "design_context": json.dumps(_design_context(winner), ensure_ascii=False, indent=2),
        "checker_contract": checker_capability_contract(),
        "math_plan": json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        "indexed_constraints": json.dumps(
            [
                {"index": index, **constraint.to_dict()}
                for index, constraint in enumerate(plan.constraints)
            ],
            ensure_ascii=False,
            indent=2,
        ),
        "intended_student_output": json.dumps(
            _intended_student_output(winner, plan),
            ensure_ascii=False,
            indent=2,
        ),
        "prior_context": _format_prior_context(prior_context or {}),
        "original_design": json.dumps(
            {
                "skeleton": (original_winner or winner).skeleton.to_dict(),
                "selection": _design_context(original_winner or winner),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "repair_diagnosis": json.dumps(
            repair_diagnosis or {"route": "none", "reason": "initial review"},
            ensure_ascii=False,
            indent=2,
        ),
    }
    system_prompt = _render(prompts["REVIEW_PLAN_SYSTEM"], values)
    if getattr(winner, "design_brief", None) is not None:
        system_prompt += (
            "\nThe original_design_brief in design_context is the unchanged pedagogical "
            "specification. Review whether the encoded quantities and plan preserve its "
            "whole goal, situation rules, and attainable successful route. Do not accept "
            "a narrower numerical proxy as fulfillment of an unsupported whole goal. "
            "Plausible routes are hypotheses, not proof. A successful familiar route is "
            "allowed; do not require every approach to fail. Use the existing review "
            "verdict and repair diagnosis to surface unresolved translation or scope "
            "problems rather than silently dropping the original goal."
        )
    user_prompt = _render(prompts["REVIEW_PLAN_USER"], values)
    payload, raw = chat_json(
        client,
        model,
        system_prompt,
        user_prompt,
        temperature=0.0,
        max_tokens=JUDGE_MAX_TOKENS,
    )
    request = {"system": system_prompt, "user": user_prompt}
    if not isinstance(payload, dict):
        return None, raw, request
    payload = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "retryable",
            "_retryable_correction",
            "_retryable_source",
            "_internal_retryable",
        }
    }
    status = payload.get("status")
    diagnosis = payload.get("repair_diagnosis")
    if diagnosis is None and isinstance(status, str) and status in {"pass", "revise"}:
        diagnosis = {"route": "none", "reason": "no explicit repair requested"}
        payload["repair_diagnosis"] = diagnosis
    diagnosis_errors = _repair_diagnosis_errors(diagnosis)
    if diagnosis_errors:
        payload["repair_diagnosis"] = {"route": "none", "reason": ""}
    if not isinstance(status, str) or status not in {"pass", "revise", "unknown"}:
        return (
            {
                "status": "unknown",
                "issues": ["review response has invalid status"],
                "repair_diagnosis": {},
                "retryable": True,
                **(
                    {"_internal_retryable": True, "_retryable_correction": "malformed"}
                    if status != "unknown"
                    else {}
                ),
                "_retryable_correction": "malformed",
            },
            raw,
            request,
        )
    issues = payload.get("issues", [])
    if not isinstance(issues, list) or not all(
        isinstance(issue, str) and issue.strip() for issue in issues
    ):
        return (
            {
                "status": "unknown",
                "issues": ["review response has invalid issues"],
                "repair_diagnosis": {},
                "retryable": True,
                **(
                    {"_internal_retryable": True, "_retryable_correction": "malformed"}
                    if status != "unknown"
                    else {}
                ),
                "_retryable_correction": "malformed",
            },
            raw,
            request,
        )
    for field in ("distinct_approaches", "constraints_covered"):
        if not isinstance(payload.get(field), bool):
            return (
                {
                    "status": "unknown",
                    "issues": [f"review response is missing boolean {field}"],
                    "repair_diagnosis": {},
                    "retryable": True,
                    **(
                        {"_internal_retryable": True, "_retryable_correction": "malformed"}
                        if status != "unknown"
                        else {}
                    ),
                    "_retryable_correction": "malformed",
                },
                raw,
                request,
            )
    coverage_errors = _requirement_coverage_errors(payload, winner, plan)
    response_errors = [*diagnosis_errors, *coverage_errors]
    if status == "pass" and issues:
        response_errors.append(
            "pass review must have an empty issues list; put actual blockers in revise or unknown"
        )
    if status == "pass" and isinstance(diagnosis, dict) and diagnosis.get("route") != "none":
        response_errors.append("pass review cannot request a repair route")
    if response_errors:
        payload = {
            **payload,
            # An explicit revise remains retryable when the structural
            # coverage validator finds a concrete missing condition. Unknown
            # reviews still need an explicit structured diagnosis below.
            "status": "revise" if status == "revise" else "unknown",
            "constraints_covered": False,
            "issues": [*issues, *response_errors],
        }
        if status != "unknown":
            payload["_internal_retryable"] = True
            payload["_retryable_correction"] = "pass" if status == "pass" else "revise"
    if original_winner is not None:
        for field in (
            "target_preserved",
            "approaches_preserved",
            "requirements_preserved",
            "repair_resolved",
        ):
            if not isinstance(payload.get(field), bool):
                response_errors.append(f"joint repair review is missing boolean {field}")
        if any(
            payload.get(field) is not True
            for field in (
                "target_preserved",
                "approaches_preserved",
                "requirements_preserved",
                "repair_resolved",
            )
        ):
            response_errors.append(
                "joint repair review did not validate preservation and resolution"
            )
        if response_errors:
            payload = {
                **payload,
                "status": "unknown" if status == "pass" else status,
                "constraints_covered": False,
                "issues": [*payload.get("issues", []), *response_errors],
            }
    return payload, raw, request


def _repair_diagnosis_errors(raw: object) -> list[str]:
    if raw is None:
        return ["review response is missing repair_diagnosis"]
    if not isinstance(raw, dict):
        return ["repair_diagnosis must be an object"]
    route = raw.get("route")
    reason = raw.get("reason")
    if not isinstance(route, str) or route not in {"plan", "design", "none"}:
        return ["repair_diagnosis.route must be plan, design, or none"]
    if route != "none" and (not isinstance(reason, str) or not reason.strip()):
        return ["repair_diagnosis.reason must be non-empty for a repair route"]
    if route == "none" and reason is not None and not isinstance(reason, str):
        return ["repair_diagnosis.reason must be a string"]
    return []


def _requirement_coverage_errors(review: dict, winner, plan: MathPlan) -> list[str]:
    expected = {item["id"] for item in _design_context(winner)["requirements"]}
    coverage = review.get("requirement_coverage", [])
    if not isinstance(coverage, list):
        return ["requirement_coverage must be a list"]
    errors = []
    seen = set()
    for item in coverage:
        if not isinstance(item, dict):
            errors.append("requirement coverage entry must be an object")
            continue
        requirement_id = item.get("requirement_id")
        if not isinstance(requirement_id, str) or requirement_id not in expected:
            errors.append(f"unknown requirement in coverage: {requirement_id!r}")
            continue
        if requirement_id in seen:
            errors.append(f"duplicate requirement coverage: {requirement_id}")
        seen.add(requirement_id)
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{requirement_id}: coverage needs a reason")
        status = item.get("status")
        if not isinstance(status, str) or status not in {"numerical", "qualitative", "unresolved"}:
            errors.append(f"{requirement_id}: invalid coverage status")
        indices = item.get("constraint_indices")
        if not isinstance(indices, list) or any(
            type(index) is not int or not 0 <= index < len(plan.constraints) for index in indices
        ):
            errors.append(f"{requirement_id}: invalid constraint_indices")
        elif status in ("qualitative", "unresolved") and indices:
            errors.append(f"{requirement_id}: non-numerical coverage must not cite constraints")
        fact_refs = item.get("quantity_fact_refs", [])
        fact_errors = _quantity_fact_reference_errors(fact_refs, plan)
        errors.extend(f"{requirement_id}: {error}" for error in fact_errors)
        answer_rule_refs = item.get("answer_rule_fact_refs", [])
        answer_rule_errors = _answer_rule_fact_reference_errors(answer_rule_refs, plan)
        errors.extend(f"{requirement_id}: {error}" for error in answer_rule_errors)
        plan_fact_refs = item.get("plan_fact_refs", [])
        plan_fact_errors = _plan_fact_reference_errors(plan_fact_refs, plan)
        errors.extend(f"{requirement_id}: {error}" for error in plan_fact_errors)
        if status in ("qualitative", "unresolved") and answer_rule_refs:
            errors.append(
                f"{requirement_id}: non-numerical coverage must not cite answer-rule facts"
            )
        if status in ("qualitative", "unresolved") and plan_fact_refs:
            errors.append(f"{requirement_id}: non-numerical coverage must not cite plan facts")
        if (
            status == "numerical"
            and not indices
            and not fact_errors
            and not fact_refs
            and not answer_rule_errors
            and not answer_rule_refs
            and not plan_fact_errors
            and not plan_fact_refs
        ):
            errors.append(
                f"{requirement_id}: numerical condition needs a constraint, quantity fact, "
                "answer-rule fact, or plan fact"
            )
        valid_indices = isinstance(indices, list) and all(
            type(index) is int and 0 <= index < len(plan.constraints) for index in indices
        )
        if status == "numerical" and valid_indices and indices:
            for constraint_index in indices:
                constraint = plan.constraints[constraint_index]
                if _constraint_is_structural_tautology(constraint):
                    errors.append(f"{requirement_id}: constraint {constraint_index} is a tautology")
        if status in ("qualitative", "unresolved") and fact_refs:
            errors.append(f"{requirement_id}: non-numerical coverage must not cite quantity facts")
        if status == "unresolved":
            errors.append(f"{requirement_id}: requirement is unresolved")
    if expected - seen:
        errors.append(f"missing requirement coverage: {sorted(expected - seen)}")
    return errors


def _answer_rule_fact_reference_errors(raw_refs: object, plan: MathPlan) -> list[str]:
    """Validate references to deterministic facts in the frozen answer rule."""
    if not isinstance(raw_refs, list):
        return ["answer_rule_fact_refs must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, fact in enumerate(raw_refs):
        if not isinstance(fact, str):
            errors.append(f"answer rule fact {index} must be a string")
            continue
        if fact != "require_unique":
            errors.append(f"answer rule fact {index} fact must be exactly 'require_unique'")
            continue
        if fact in seen:
            errors.append(f"duplicate answer-rule fact reference: {fact}")
            continue
        seen.add(fact)
        if plan.answer_rule.kind not in {"largest", "smallest"}:
            errors.append("require_unique is only enforced for largest/smallest answer rules")
        elif plan.answer_rule.require_unique is not True:
            errors.append("require_unique is not enabled in the answer rule")
    return errors


def _plan_fact_reference_errors(raw_refs: object, plan: MathPlan) -> list[str]:
    """Validate references to non-value-dependent sections of the frozen plan."""
    if not isinstance(raw_refs, list):
        return ["plan_fact_refs must be a list"]
    serialized = plan.to_dict()
    sections = {
        "quantities": serialized.get("quantities"),
        "target": serialized.get("target"),
        "answer_rule": serialized.get("answer_rule"),
    }
    errors: list[str] = []
    seen: set[str] = set()
    for index, reference in enumerate(raw_refs):
        if not isinstance(reference, str):
            errors.append(f"plan fact {index} must be a string")
            continue
        if reference not in sections:
            errors.append(f"plan fact {index} must be one of {sorted(sections)}")
            continue
        if reference in seen:
            errors.append(f"duplicate plan fact reference: {reference}")
            continue
        seen.add(reference)
        if not sections[reference]:
            errors.append(
                f"plan fact reference {reference!r} does not resolve to a "
                "non-empty MathPlan.to_dict section"
            )
    return errors


def _quantity_fact_reference_errors(raw_refs: object, plan: MathPlan) -> list[str]:
    """Validate review references to facts enforced by the frozen quantity contract."""
    if not isinstance(raw_refs, list):
        return ["quantity_fact_refs must be a list"]
    quantities = {quantity.name: quantity for quantity in plan.given_quantities}
    allowed_facts = {"unit", "list_length", "value_domain"}
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, ref in enumerate(raw_refs):
        if not isinstance(ref, dict):
            errors.append(f"quantity fact {index} must be an object")
            continue
        quantity_name = ref.get("quantity")
        fact = ref.get("fact")
        if not isinstance(quantity_name, str) or not quantity_name.strip():
            errors.append(f"quantity fact {index} needs a quantity")
            continue
        if not isinstance(fact, str) or fact not in allowed_facts:
            errors.append(f"quantity fact {index} fact must be one of {sorted(allowed_facts)}")
            continue
        key = (quantity_name, fact)
        if key in seen:
            errors.append(f"duplicate quantity fact reference: {quantity_name}.{fact}")
            continue
        seen.add(key)
        quantity = quantities.get(quantity_name)
        if quantity is None:
            errors.append(f"quantity fact references unknown given quantity {quantity_name!r}")
            continue
        if fact == "unit" and not quantity.unit:
            errors.append(f"{quantity_name}.unit is not declared")
        elif fact == "list_length" and (quantity.role != "list" or quantity.list_length is None):
            errors.append(f"{quantity_name}.list_length is not enforced")
        elif fact == "value_domain" and quantity.value_domain not in ALLOWED_VALUE_DOMAINS:
            errors.append(f"{quantity_name}.value_domain is not enforced")
    return errors


def _constraint_is_structural_tautology(constraint) -> bool:
    if constraint.operator != "==":
        return False
    if constraint.left.strip() == constraint.right.strip():
        return True
    try:
        left = ast.parse(constraint.left, mode="eval").body
        right = ast.parse(constraint.right, mode="eval").body
    except SyntaxError:
        return False
    return ast.dump(left, annotate_fields=False) == ast.dump(right, annotate_fields=False)


def _review_passes(review: dict | None) -> bool:
    return bool(
        review
        and review.get("status") == "pass"
        and review.get("distinct_approaches") is True
        and review.get("constraints_covered") is True
        and not review.get("issues")
    )


def _review_retryable(review: dict | None) -> bool:
    if not review:
        return False
    if review.get("status") == "revise":
        return True
    if review.get("status") != "unknown":
        return False
    if review.get("_internal_retryable") is True:
        return True
    diagnosis = review.get("repair_diagnosis")
    if _repair_diagnosis_errors(diagnosis):
        return False
    return not _repair_diagnosis_errors(diagnosis) and diagnosis.get("route") in {
        "plan",
        "design",
    }


def _joint_repair(
    client,
    model,
    prompts,
    case,
    original_winner,
    current_plan: MathPlan,
    prior_context: dict[str, Any],
    diagnosis: dict[str, Any],
) -> tuple[Any | None, MathPlan | None, dict[str, Any]]:
    values = {
        "target_concept": case["target_concept"],
        "case_context": json.dumps(case, ensure_ascii=False, indent=2),
        "prior_context": _format_prior_context(prior_context),
        "original_design": json.dumps(
            {
                "skeleton": original_winner.skeleton.to_dict(),
                "selection": _design_context(original_winner),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "original_math_plan": json.dumps(current_plan.to_dict(), ensure_ascii=False, indent=2),
        "repair_diagnosis": json.dumps(diagnosis, ensure_ascii=False, indent=2),
        "checker_contract": checker_capability_contract(),
        "skeleton_contract": skeleton_schema_contract(),
    }
    request = {
        "system": _render(prompts["REPAIR_SELECTED_SYSTEM"], values),
        "user": _render(prompts["REPAIR_SELECTED_USER"], values),
    }
    before = {
        "skeleton": original_winner.skeleton.to_dict(),
        "math_plan": current_plan.to_dict(),
    }
    payload, raw = chat_json(
        client,
        model,
        request["system"],
        request["user"],
        temperature=0.0,
        max_tokens=JUDGE_MAX_TOKENS,
    )
    record: dict[str, Any] = {
        "before": before,
        "proposed": payload,
        "diagnosis": diagnosis,
        "validation": [],
        "accepted": False,
        "raw_text": raw,
        "payload": payload,
        "prompts": request,
    }
    if not isinstance(payload, dict):
        record["validation"] = ["joint repair response must be a JSON object"]
        return None, None, record
    skeleton_payload = payload.get("skeleton")
    plan_payload = payload.get("math_plan")
    try:
        if not isinstance(skeleton_payload, dict):
            raise ValueError("joint repair response is missing skeleton object")
        repaired_skeleton = skeleton_from_proposal_payload(skeleton_payload)
        resource_errors = _proposal_resource_errors(repaired_skeleton, _method_names(prior_context))
        if resource_errors:
            raise ValueError("; ".join(resource_errors))
        original_quantities = {
            quantity.name: quantity.to_dict() for quantity in original_winner.skeleton.quantities
        }
        revised_quantities = {
            quantity.name: quantity.to_dict() for quantity in repaired_skeleton.quantities
        }
        missing_quantities = sorted(set(original_quantities) - set(revised_quantities))
        if missing_quantities:
            raise ValueError(
                "joint repair removed original quantities: " + ", ".join(missing_quantities)
            )
        for name, original_quantity in original_quantities.items():
            revised_quantity = revised_quantities[name]
            for field in ("value_source", "value_domain"):
                if revised_quantity[field] != original_quantity[field]:
                    raise ValueError(f"joint repair weakened quantity {name!r} {field} metadata")
            if (
                original_quantity.get("list_length") is not None
                and revised_quantity.get("list_length") != original_quantity["list_length"]
            ):
                raise ValueError(f"joint repair changed fixed list_length for {name!r}")
        original_constraints = original_winner.skeleton.number_constraints
        if tuple(repaired_skeleton.number_constraints[: len(original_constraints)]) != tuple(
            original_constraints
        ):
            raise ValueError("joint repair removed or reordered original number_constraints")
        original_approaches = {approach.id for approach in original_winner.skeleton.approaches}
        revised_approaches = {approach.id for approach in repaired_skeleton.approaches}
        if not original_approaches.issubset(revised_approaches):
            raise ValueError("joint repair removed original proposed approaches")
        if not isinstance(plan_payload, dict):
            raise ValueError("joint repair response is missing math_plan object")
        if plan_payload.get("schema_version") != "math-plan/v2":
            raise ValueError("joint repair requires math-plan/v2 schema_version")
        repaired_winner = replace(original_winner, skeleton=repaired_skeleton)
        repaired_plan = _math_plan_from_payload(plan_payload, repaired_winner)
        expression_errors = validate_plan_expressions(repaired_plan)
        if expression_errors:
            raise ValueError(
                "joint repair has unsupported expressions: " + "; ".join(expression_errors)
            )
    except (TypeError, ValueError) as exc:
        record["validation"] = [str(exc)]
        return None, None, record
    record["validation"] = [
        "skeleton, preserved requirements, approaches, and expressions validated"
    ]
    record["structure_valid"] = True
    record["proposed"] = {
        "skeleton": repaired_skeleton.to_dict(),
        "math_plan": repaired_plan.to_dict(),
    }
    return repaired_winner, repaired_plan, record


def _plan_until_reviewed(
    client,
    model,
    prompts,
    case,
    winner,
    prior_context: dict[str, Any],
    *,
    require_v2: bool = True,
    initial_plan_payload: dict | None = None,
) -> dict[str, Any]:
    """Review an optional saved plan, then make at most one shared correction."""
    metadata_errors = skeleton_metadata_errors(winner.skeleton)
    if metadata_errors:
        return {
            "winner": winner,
            "original_winner": winner,
            "design_repair_attempts": [],
            "plan": None,
            "plan_payload": None,
            "plan_raw_text": "",
            "plan_review": None,
            "plan_review_raw_text": "",
            "plan_review_prompts": None,
            "attempts": [
                {
                    "attempt": 0,
                    "raw_text": "",
                    "payload": None,
                    "prompts": None,
                    "stage": "structure",
                    "errors": list(metadata_errors),
                }
            ],
            "error": "; ".join(metadata_errors),
        }
    attempts: list[dict[str, Any]] = []
    design_repair_attempts: list[dict[str, Any]] = []
    feedback = ""
    previous_payload: dict[str, Any] | None = None
    corrections_used = 0
    current_winner = winner
    for attempt in range(1, PLAN_RETRY_MAX + 2):
        saved_first = attempt == 1 and initial_plan_payload is not None
        if saved_first:
            request = None
            payload = initial_plan_payload
            raw = ""
        else:
            request = _plan_request(
                prompts,
                case,
                winner,
                prior_context,
                feedback=feedback,
                previous_plan=previous_payload,
            )
            payload, raw = _plan_winner(
                client, model, prompts, case, winner, prior_context, feedback, previous_payload
            )
        record: dict[str, Any] = {
            "attempt": attempt,
            "raw_text": raw,
            "payload": payload,
            "prompts": request,
            "source": "saved_plan" if saved_first else "generated",
            "stage": None,
            "errors": [],
        }
        if not isinstance(payload, dict):
            record["stage"] = "structure"
            record["errors"] = ["unparseable mathematical plan"]
            attempts.append(record)
            corrections_used = min(corrections_used + 1, PLAN_RETRY_MAX)
            feedback = record["errors"][0]
            previous_payload = None
            continue
        try:
            plan = _math_plan_from_payload(payload, winner)
            if require_v2 and plan.schema_version != "math-plan/v2":
                raise ValueError("new mathematical plans must use schema_version math-plan/v2")
        except ValueError as exc:
            record["stage"] = "structure"
            record["errors"] = [str(exc)]
            attempts.append(record)
            corrections_used = min(corrections_used + 1, PLAN_RETRY_MAX)
            feedback = str(exc)
            previous_payload = payload
            continue
        record["math_plan"] = plan.to_dict()
        preflight_errors = validate_plan_expressions(plan)
        if preflight_errors:
            record["stage"] = "expression"
            record["errors"] = list(preflight_errors)
            attempts.append(record)
            corrections_used = min(corrections_used + 1, PLAN_RETRY_MAX)
            feedback = "; ".join(preflight_errors)
            previous_payload = payload
            continue
        review, review_raw, review_prompts = _review_plan(
            client, model, prompts, case, winner, plan, prior_context
        )
        record["review"] = review
        record["review_raw_text"] = review_raw
        record["review_prompts"] = review_prompts
        if review is None:
            record["stage"] = "meaning_review"
            record["errors"] = ["unparseable plan review"]
            attempts.append(record)
            break
        if _review_passes(review):
            record["stage"] = "accepted"
            attempts.append(record)
            return {
                "winner": current_winner,
                "original_winner": winner,
                "design_repair_attempts": design_repair_attempts,
                "plan": plan,
                "plan_payload": payload,
                "plan_raw_text": raw,
                "plan_review": review,
                "plan_review_raw_text": review_raw,
                "plan_review_prompts": review_prompts,
                "attempts": attempts,
                "error": None,
            }
        record["stage"] = "meaning_review"
        record["errors"] = list(review.get("issues") or ["plan review did not pass"])
        attempts.append(record)
        route = (review.get("repair_diagnosis") or {}).get("route")
        plan_stage_retryable = False
        diagnosed_route = not _repair_diagnosis_errors(
            review.get("repair_diagnosis")
        ) and route in {"plan", "design"}
        if corrections_used >= PLAN_RETRY_MAX or (
            not plan_stage_retryable
            and (
                not _review_retryable(review)
                or (
                    review.get("status") == "unknown"
                    and not diagnosed_route
                    and review.get("_internal_retryable") is not True
                )
            )
        ):
            break
        if route == "design":
            corrections_used += 1
            repaired_winner, repaired_plan, repair_record = _joint_repair(
                client,
                model,
                prompts,
                case,
                winner,
                plan,
                prior_context,
                review["repair_diagnosis"],
            )
            design_repair_attempts.append(repair_record)
            if repaired_winner is None or repaired_plan is None:
                break
            current_winner = repaired_winner
            repaired_review, repaired_review_raw, repaired_review_prompts = _review_plan(
                client,
                model,
                prompts,
                case,
                current_winner,
                repaired_plan,
                prior_context,
                original_winner=winner,
                repair_diagnosis=review["repair_diagnosis"],
            )
            repair_record["review"] = repaired_review
            repair_record["review_raw_text"] = repaired_review_raw
            repair_record["review_prompts"] = repaired_review_prompts
            repaired_attempt = {
                "attempt": attempt,
                "source": "joint_repair_review",
                "raw_text": repair_record.get("raw_text", ""),
                "payload": repair_record.get("payload"),
                "prompts": repair_record.get("prompts"),
                "math_plan": repaired_plan.to_dict(),
                "review": repaired_review,
                "review_raw_text": repaired_review_raw,
                "review_prompts": repaired_review_prompts,
                "stage": "accepted" if _review_passes(repaired_review) else "meaning_review",
                "errors": []
                if _review_passes(repaired_review)
                else list(
                    (repaired_review or {}).get("issues") or ["repaired plan review did not pass"]
                ),
            }
            attempts.append(repaired_attempt)
            if _review_passes(repaired_review):
                repair_record["accepted"] = True
                return {
                    "winner": current_winner,
                    "original_winner": winner,
                    "design_repair_attempts": design_repair_attempts,
                    "plan": repaired_plan,
                    "plan_payload": repaired_plan.to_dict(),
                    "plan_raw_text": repair_record["raw_text"],
                    "plan_review": repaired_review,
                    "plan_review_raw_text": repaired_review_raw,
                    "plan_review_prompts": repaired_review_prompts,
                    "attempts": attempts,
                    "error": None,
                }
            repair_record["accepted"] = False
            break
        corrections_used += 1
        feedback = "; ".join(record["errors"])
        previous_payload = payload
    final = attempts[-1] if attempts else {}
    return {
        "winner": winner,
        "original_winner": winner,
        "design_repair_attempts": design_repair_attempts,
        "plan": None,
        "plan_payload": final.get("payload"),
        "plan_raw_text": final.get("raw_text", ""),
        "plan_review": final.get("review"),
        "plan_review_raw_text": final.get("review_raw_text", ""),
        "plan_review_prompts": final.get("review_prompts"),
        "attempts": attempts,
        "error": "; ".join(final.get("errors") or ["mathematical plan blocked"]),
    }


def _math_plan_from_payload(payload: dict, winner) -> MathPlan:
    approach_ids = {approach.id for approach in winner.skeleton.approaches}
    schema_version = str(payload.get("schema_version") or "math-plan/v1")
    if schema_version != "math-plan/v2" and not approach_ids:
        raise ValueError("winner has no proposed approaches to link to prior paths")
    plan = MathPlan.from_payload(
        payload,
        winner.skeleton.quantities,
        approach_ids=approach_ids,
    )
    selected_contrast = getattr(winner, "prior_contrast", None)
    if selected_contrast is None:
        if plan.prior_contrast is not None:
            raise ValueError("math plan added a prior_contrast not selected in the design")
    elif selected_contrast.checkability == "numerical":
        if plan.prior_contrast is None:
            raise ValueError("selected numerical prior_contrast is missing from the math plan")
        if plan.prior_contrast.approach_id != selected_contrast.approach_id:
            raise ValueError(
                "math plan prior_contrast does not match the selected approach_id "
                f"{selected_contrast.approach_id!r}"
            )
        if plan.answer_rule.kind == "equal":
            if (
                selected_contrast.expected_target_equal is None
                or selected_contrast.expected_prior_equal is None
            ):
                raise ValueError(
                    "selected equal prior_contrast needs explicit target and prior outcomes"
                )
            if (
                plan.prior_contrast_expected_target_equal != selected_contrast.expected_target_equal
                or plan.prior_contrast_expected_prior_equal
                != selected_contrast.expected_prior_equal
            ):
                raise ValueError(
                    "math plan prior_contrast equality outcomes do not match the selected design"
                )
        elif (
            selected_contrast.expected_target_equal is not None
            or selected_contrast.expected_prior_equal is not None
        ):
            raise ValueError("selected equality outcomes require an equal target answer rule")
    elif plan.prior_contrast is not None:
        raise ValueError(
            "math plan cannot claim a machine-checked path for a "
            f"{selected_contrast.checkability} prior_contrast"
        )
    return plan


def _legacy_math_plan_from_fill(payload: dict, winner) -> MathPlan:
    target = payload.get("target")
    priors = payload.get("priors")
    raw_values = payload.get("values")
    if not isinstance(target, dict) or not isinstance(priors, list):
        raise ValueError("stored result has no formula-bearing fill to build a legacy plan")
    if not isinstance(raw_values, dict) or not raw_values:
        raise ValueError("stored result has no legacy values to define plan input slots")
    target_expressions = target.get("expressions")
    if not isinstance(target_expressions, dict) or not target_expressions:
        raise ValueError("stored result target expressions are missing")
    labels = [str(label) for label in target_expressions]
    comparable_priors = []
    ignored_priors = []
    for index, item in enumerate(priors):
        if not isinstance(item, dict):
            raise ValueError(f"stored prior {index} is not an object")
        expressions = item.get("expressions")
        if not isinstance(expressions, dict):
            raise ValueError(f"stored prior {index} expressions are missing")
        if set(expressions) != set(target_expressions):
            ignored_priors.append(str(item.get("resource") or f"prior_{index}"))
            continue
        comparable_priors.append(
            {
                "name": str(item.get("resource") or f"prior_{index}"),
                "expressions": expressions,
            }
        )
    if not comparable_priors:
        raise ValueError(
            "stored result has no prior path with labels matching the target; "
            f"ignored paths: {ignored_priors}"
        )
    plan_payload = {
        "schema_version": "math-plan/legacy-adapter",
        "target": {"name": "target", "expressions": target_expressions},
        "priors": comparable_priors,
        "answer_rule": {
            "kind": "largest",
            "labels": labels,
            "unit": "",
            "require_unique": True,
        },
        "required_checks": ["at_least_one_prior_disagrees"],
    }
    legacy_quantities = tuple(
        Quantity(
            name=name,
            role="list" if isinstance(value, list) else "other",
            description="legacy fill slot",
            value_source="given",
            list_length=len(value) if isinstance(value, list) else None,
        )
        for name, value in raw_values.items()
    )
    return MathPlan.from_payload(
        plan_payload,
        legacy_quantities,
        approach_ids=None,
    )


def _stored_math_plan(path: Path, winner) -> MathPlan:
    payload = json.loads(path.read_text())
    source = payload
    if isinstance(payload.get("stages"), dict) and isinstance(payload["stages"].get("D2_D3"), dict):
        source = payload["stages"]["D2_D3"]
    elif isinstance(payload.get("d2"), dict):
        source = payload["d2"]
    raw_plan = source.get("math_plan")
    if isinstance(raw_plan, dict):
        metadata_errors = skeleton_metadata_errors(winner.skeleton)
        if metadata_errors:
            raise ValueError(
                "saved winner has incomplete quantity metadata; re-propose a new "
                "skeleton with fixed given-list lengths before filling: "
                + "; ".join(metadata_errors)
            )
        return _math_plan_from_payload(raw_plan, winner)
    raise ValueError(
        f"Historical result {path} has no explicit math_plan; replan it before filling"
    )


def _fill_winner(
    client,
    model,
    prompts,
    case,
    winner,
    plan: MathPlan,
    prior_context: dict[str, Any],
    feedback: str = "",
    previous_values: dict[str, Any] | None = None,
) -> tuple[dict | None, str, dict[str, str]]:
    values = {
        "target_concept": case["target_concept"],
        "grade": str(case["grade"]),
        "quantities": "\n".join(
            (
                f"  - {q.name} ({q.role}, source={q.value_source}, "
                f"unit={q.unit or 'unspecified'}, domain={q.value_domain}): {q.description}"
            )
            for q in plan.given_quantities
        ),
        "question": winner.skeleton.question,
        "math_plan": json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        "design_context": json.dumps(_design_context(winner), ensure_ascii=False, indent=2),
        "approaches": _format_approaches(winner.skeleton),
        "checker_contract": checker_capability_contract(),
        "prior_context": _format_prior_context(prior_context),
        "fill_feedback": json.dumps(
            {
                "previous_values": previous_values or {},
                "checker_feedback": feedback.strip() or "first attempt",
            },
            ensure_ascii=False,
            indent=2,
        ),
    }
    request = {
        "system": _render(prompts["FILL_SKELETON_SYSTEM"], values),
        "user": _render(prompts["FILL_SKELETON_USER"], values),
    }
    payload, raw = chat_json(
        client,
        model,
        request["system"],
        request["user"],
        temperature=0.7,
        max_tokens=PROPOSE_MAX_TOKENS,
    )
    return payload, raw, request


def _fill_until_accepted(
    client,
    model,
    prompts,
    case,
    winner,
    plan: MathPlan,
    prior_context: dict[str, Any],
    *,
    plan_review: dict | None = None,
) -> dict:
    coverage_errors = _requirement_coverage_errors(plan_review or {}, winner, plan)
    if _design_context(winner)["requirements"] or plan_review is not None:
        if not _review_passes(plan_review) or coverage_errors:
            return {
                "accepted": False,
                "payload": None,
                "check": {
                    "accepted": False,
                    "status": "needs_review",
                    "reason": "design requirements need a passing coverage review",
                    "failures": coverage_errors or ["plan review did not pass"],
                },
                "attempts": [],
            }
    unverified = [
        item
        for item in (plan_review or {}).get("requirement_coverage", [])
        if item["status"] == "qualitative"
    ]
    selected_contrast = getattr(winner, "prior_contrast", None)
    if selected_contrast is not None and selected_contrast.checkability != "numerical":
        unverified.append(
            {
                "requirement_id": "selected_prior_contrast",
                "status": "unverified",
                "checkability": selected_contrast.checkability,
                "approach_id": selected_contrast.approach_id,
                "reason": selected_contrast.reason,
            }
        )
    attempts = []
    feedback = ""
    previous_values: dict[str, Any] | None = None
    for attempt in range(1, FILL_MAX_TRIES + 1):
        payload, raw, request = _fill_winner(
            client,
            model,
            prompts,
            case,
            winner,
            plan,
            prior_context,
            feedback,
            previous_values,
        )
        record = {"attempt": attempt, "raw_text": raw, "payload": payload, "prompts": request}
        if not isinstance(payload, dict):
            record["check"] = {"accepted": False, "reason": "unparseable fill"}
            attempts.append(record)
            feedback = "Previous fill was not valid JSON. Return only the required JSON object."
            continue
        unexpected = sorted(set(payload) - {"values"})
        if unexpected:
            check_dict = {
                "accepted": False,
                "status": "needs_review",
                "reason": f"fill attempted to change the frozen plan: {unexpected}",
                "failures": [f"unexpected top-level fields: {unexpected}"],
            }
            record["check"] = check_dict
            attempts.append(record)
            return {
                "accepted": False,
                "payload": payload,
                "check": check_dict,
                "attempts": attempts,
            }
        raw_values = payload.get("values")
        check = check_fill(plan, raw_values)
        record["check"] = check.to_dict()
        record["check"]["unverified_requirements"] = unverified
        attempts.append(record)
        if check.accepted:
            return {
                "accepted": True,
                "payload": payload,
                "check": record["check"],
                "attempts": attempts,
            }
        if check.status == "needs_review":
            return {
                "accepted": False,
                "payload": payload,
                "check": record["check"],
                "attempts": attempts,
            }
        feedback = json.dumps(
            {
                "message": check.retry_feedback(),
                "computed_check": check.to_dict(),
            },
            ensure_ascii=False,
        )
        previous_values = raw_values if isinstance(raw_values, dict) else None
    return {
        "accepted": False,
        "payload": attempts[-1]["payload"] if attempts else None,
        "check": attempts[-1].get("check") if attempts else None,
        "attempts": attempts,
    }


def _write_task(
    client,
    model,
    prompts,
    case,
    winner,
    plan: MathPlan,
    fill: dict,
    prior_context: dict[str, Any],
    plan_review: dict | None,
) -> tuple[dict | None, str]:
    context = _writer_context(case, prior_context, winner, plan, fill, plan_review)
    values = {
        key: json.dumps(value, ensure_ascii=False, indent=2) for key, value in context.items()
    }
    payload, raw = chat_json(
        client,
        model,
        _render(prompts["WRITE_TASK_SYSTEM"], values),
        _render(prompts["WRITE_TASK_USER"], values),
        temperature=0.7,
        max_tokens=PROPOSE_MAX_TOKENS,
    )
    if payload is None:
        return _blocked_task_payload("writer response was not valid JSON"), raw
    try:
        return _validate_task_payload(payload), raw
    except ValueError as exc:
        return _blocked_task_payload(str(exc)), raw


def _run_design_data(client, model, case, winner, prior_context, *, initial_proposal=None):
    from scripts.design_data_stage import run_design_data

    return run_design_data(
        client, model, case, winner, prior_context, initial_proposal=initial_proposal
    )


def _write_design_data_task(client, model, case, winner, data_run, prior_context):
    from scripts.design_data_stage import write_design_data_task

    return write_design_data_task(client, model, case, winner, data_run, prior_context)


def _resume_design_data(args, case, prior_context, winner, stored_source, client, model):
    if args.plan_only:
        raise ValueError("--plan-only is for historical mathematical plans, not design data")
    data_run = stored_source.get("design_data")
    history = list(stored_source.get("design_data_history", []))
    if data_run is not None and not args.no_fill:
        history.append(data_run)
    if not args.no_fill:
        data_run = _run_design_data(
            client, model, case, winner, prior_context,
            initial_proposal=None if args.replan or data_run is None else data_run["payload"],
        )
    task, raw = (None, "")
    accepted = data_run is not None and data_run["accepted"]
    if data_run is not None and data_run["payload"] is not None and not args.no_fill:
        task, raw = _write_design_data_task(
            client, model, case, winner, data_run, prior_context
        )
    result = {
        "schema_version": "pf-design-data/v1",
        "case": args.case,
        "case_input": case,
        "case_input_provenance": "saved_snapshot",
        "model": model,
        "reused_from": args.from_result,
        "replanned": args.replan,
        "prior_context": prior_context,
        "winner": winner.to_dict(),
        "original_winner": stored_source.get("original_winner", winner.to_dict()),
        "design_brief": True,
        "design_data": data_run,
        "design_data_history": history,
        "filled_values": None if data_run is None else data_run["payload"],
        "fill_check": None if data_run is None else data_run["check"],
        "fill_accepted": accepted if data_run is not None else None,
        "task": task,
        "task_raw_text": raw,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = _output_path(args.output, f"{args.case}_{stamp}_task")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if data_run is not None:
        print(f"D2b: {data_run['status']}")
        if data_run["error"]:
            print(data_run["error"])
        if data_run["check"]:
            for warning in data_run["check"].get("warnings", []):
                print(f"Warning: {warning}")
    print(f"saved: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="case id from the cases config")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="number of proposal samples")
    parser.add_argument(
        "--model",
        default="gpt41mini",
        choices=["gpt41mini", "gpt41", "gpt54", "luna"],
    )
    parser.add_argument("--label", default="", help="optional suffix for the result filename")
    parser.add_argument(
        "--output",
        default="",
        help="exact JSON output path; otherwise save under the situation results directory",
    )
    parser.add_argument("--no-fill", action="store_true", help="skip the number-fill call")
    parser.add_argument(
        "--from-result",
        default="",
        help="reuse a saved design and its frozen calculations",
    )
    parser.add_argument(
        "--replan",
        action="store_true",
        help="explicitly regenerate data/calculations, or a historical mathematical plan",
    )
    parser.add_argument(
        "--from-d1",
        default="",
        help="use prior resources from a D1 recommendations JSON",
    )
    parser.add_argument(
        "--d1-condition",
        choices=("grounded", "ungrounded"),
        default="grounded",
        help="condition to select when --from-d1 contains a comparison",
    )
    parser.add_argument(
        "--use-expert-resources",
        action="store_true",
        help="explicitly use curated expected_resources instead of a D1 artifact",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="save the frozen mathematical plan for review without generating values",
    )
    args = parser.parse_args()

    if args.output and Path(args.output).exists():
        raise ValueError(f"Refusing to overwrite generation output: {args.output}")
    if args.replan and not args.from_result:
        raise ValueError("--replan requires --from-result")
    if args.plan_only and args.from_result and not args.replan:
        raise ValueError("--plan-only with --from-result requires --replan")
    if args.plan_only and args.no_fill:
        raise ValueError("--plan-only cannot be combined with --no-fill")
    if args.plan_only and not args.from_result:
        raise ValueError("--plan-only requires a saved historical mathematical plan")
    saved_case_input = (
        _stored_case_input(Path(args.from_result), args.case) if args.from_result else None
    )
    case = saved_case_input if saved_case_input is not None else _load_case(args.case)
    if args.from_d1:
        prior_context = _prior_context_from_d1(
            Path(args.from_d1),
            args.case,
            args.d1_condition,
        )
    elif args.from_result and not args.use_expert_resources:
        prior_context = _stored_prior_context(Path(args.from_result), args.case)
        if prior_context is None:
            raise ValueError(
                "--from-result has no stored prior_context; provide --from-d1 "
                "or explicitly pass --use-expert-resources"
            )
    elif args.use_expert_resources:
        prior_context = _expert_prior_context(case)
    else:
        raise ValueError(
            "Provide --from-d1 for curriculum recommendations or explicitly "
            "pass --use-expert-resources"
        )
    methods = _method_names(prior_context)
    prompts = _prompts()
    client, model = load_client(args.model)

    if args.from_result:
        source_path = Path(args.from_result)
        winner = _winner_from_result(source_path, args.case)
        stored_original_winner = _winner_from_result(
            source_path, args.case, winner_field="original_winner"
        )
        stored_repair_attempts: list[dict[str, Any]] = []
        stored_payload = json.loads(source_path.read_text())
        stored_source = stored_payload
        if isinstance(stored_payload.get("stages"), dict) and isinstance(
            stored_payload["stages"].get("D2_D3"), dict
        ):
            stored_source = stored_payload["stages"]["D2_D3"]
        elif isinstance(stored_payload.get("d2"), dict):
            stored_source = stored_payload["d2"]
        if (
            "design_data" in stored_source
            or stored_payload.get("schema_version") == "pf-design-data/v1"
        ):
            _resume_design_data(
                args, case, prior_context, winner, stored_source, client, model
            )
            return
        if isinstance(stored_source.get("design_repair_attempts"), list):
            stored_repair_attempts = stored_source["design_repair_attempts"]
        if args.replan:
            planning = _plan_until_reviewed(client, model, prompts, case, winner, prior_context)
            winner = planning["winner"]
            math_plan = planning["plan"]
            plan_review = planning["plan_review"]
            plan_review_raw = planning["plan_review_raw_text"]
            plan_review_prompts = planning["plan_review_prompts"]
            plan_attempts = planning["attempts"]
            plan_stop_stage = plan_attempts[-1]["stage"]
            plan_review_error = (
                planning["error"]
                if plan_stop_stage == "meaning_review" and plan_review is None
                else None
            )
            math_plan_error = planning["error"] if math_plan is None else None
            math_plan_raw = planning["plan_raw_text"]
        else:
            math_plan = _stored_math_plan(source_path, winner)
            math_plan_raw = ""
            math_plan_error = None
            plan_attempts = []
            plan_review = None
            plan_review_raw = ""
            plan_review_prompts = None
            plan_review_error = None
            plan_stop_stage = None
        if not args.replan:
            preflight_errors = validate_plan_expressions(math_plan)
            if preflight_errors:
                plan_stop_stage = "expression"
                math_plan_error = "expression preflight failed: " + "; ".join(preflight_errors)
            else:
                plan_review, plan_review_raw, plan_review_prompts = _review_plan(
                    client, model, prompts, case, winner, math_plan, prior_context
                )
                plan_stop_stage = "accepted" if _review_passes(plan_review) else "meaning_review"
                if plan_review is None:
                    plan_review_error = "unparseable plan review"
        fill_run = None
        fill = None
        fill_blocked_reason = None
        if not _review_passes(plan_review):
            fill_blocked_reason = (
                math_plan_error
                if plan_stop_stage in {"structure", "expression"}
                else "plan review did not pass"
            )
        elif not args.no_fill and not args.plan_only:
            fill_run = _fill_until_accepted(
                client,
                model,
                prompts,
                case,
                winner,
                math_plan,
                prior_context,
                plan_review=plan_review,
            )
            fill = fill_run["payload"] if fill_run["accepted"] else None
        task = None
        task_raw = ""
        if fill and not args.no_fill and not args.plan_only:
            task, task_raw = _write_task(
                client,
                model,
                prompts,
                case,
                winner,
                math_plan,
                fill,
                prior_context,
                plan_review,
            )
        out = {
            "case": args.case,
            "case_input": case,
            "case_input_provenance": (
                "saved_snapshot"
                if saved_case_input is not None
                else "legacy_source_without_snapshot"
            ),
            "model": model,
            "reused_from": args.from_result,
            "replanned": args.replan,
            "input_artifacts": {
                "case_config": str(CASES_PATH),
                "prompt_template": str(PROMPTS_PATH),
                "d1_recommendations": str(args.from_d1) if args.from_d1 else None,
                "d1_condition": args.d1_condition if args.from_d1 else None,
                "use_expert_resources": args.use_expert_resources,
            },
            "prior_context": prior_context,
            "prior_methods": methods,
            "winner": winner.to_dict(),
            "original_winner": (
                planning.get("original_winner", winner).to_dict()
                if args.replan
                else stored_original_winner.to_dict()
            ),
            "design_repair_attempts": (
                planning.get("design_repair_attempts", [])
                if args.replan
                else stored_repair_attempts
            ),
            "math_plan": None if math_plan is None else math_plan.to_dict(),
            "math_plan_raw_text": math_plan_raw,
            "math_plan_error": math_plan_error,
            "plan_attempts": plan_attempts,
            "plan_stop_stage": plan_stop_stage,
            "plan_review": plan_review,
            "plan_review_raw_text": plan_review_raw,
            "plan_review_prompts": plan_review_prompts,
            "plan_review_error": plan_review_error,
            "filled_values": fill,
            "fill_check": None if fill_run is None else fill_run.get("check"),
            "fill_accepted": None if fill_run is None else fill_run["accepted"],
            "fill_attempts": None if fill_run is None else fill_run["attempts"],
            "fill_blocked_reason": fill_blocked_reason,
            "task": task,
            "task_raw_text": task_raw,
        }
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = _output_path(
            args.output,
            f"{args.case}_{model.replace('-', '')}_{stamp}_task",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"reused winner from {args.from_result}")
        print(f"fill accepted: {None if fill_run is None else fill_run['accepted']}")
        if fill_run is not None and fill_run.get("check"):
            print(f"fill check: {fill_run['check'].get('reason')}")
        if fill:
            print(f"filled values: {json.dumps(fill.get('values', fill), ensure_ascii=False)}")
        if task and task.get("status") == "ready":
            print("\n=== TASK ===")
            print(task.get("title", ""))
            print(task.get("body", ""))
            print("\nQ:", task.get("question", ""))
        elif task and task.get("status") == "blocked":
            print(f"D3 blocked: {task.get('blocking_issues', [])}")
        print(f"\nsaved: {path}")
        return

    from scripts.design_brief_stage import run_design_brief_search

    brief_run = run_design_brief_search(client, model, case, prior_context, k=args.k)
    proposals = brief_run["proposals"]
    skeleton_objs = [winner.skeleton for winner in brief_run["winners"]]
    judged = brief_run["judged"]
    judge_raw = brief_run["judge_raw_text"]
    judge_error = brief_run["judge_error"]

    winners = brief_run["winners"]

    fill = None
    fill_run: dict | None = None
    fill_blocked_reason = None
    effective_winner = winners[0] if winners else None
    if winners and not args.no_fill:
        fill_run = _run_design_data(client, model, case, effective_winner, prior_context)
        fill = fill_run["payload"]
        fill_blocked_reason = fill_run["error"]

    task = None
    task_raw = ""
    if fill:
        task, task_raw = _write_design_data_task(
            client, model, case, effective_winner, fill_run, prior_context
        )

    result = {
        "schema_version": "pf-design-data/v1",
        "case": args.case,
        "case_input": case,
        "case_input_provenance": "current_case_config",
        "model": model,
        "k": args.k,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "input_artifacts": {
            "case_config": str(CASES_PATH),
            "prompt_template": str(PROMPTS_PATH),
            "d1_recommendations": str(args.from_d1) if args.from_d1 else None,
            "d1_condition": args.d1_condition if args.from_d1 else None,
            "use_expert_resources": args.use_expert_resources,
        },
        "prior_methods": methods,
        "prior_context": prior_context,
        "proposals": proposals,
        "n_valid_proposals": len(skeleton_objs),
        "judged_candidates": [c.to_dict() for c in judged],
        "judge_error": judge_error,
        "judge_raw_text": judge_raw,
        "winners": [c.to_dict() for c in winners],
        "winner": effective_winner.to_dict() if winners else None,
        "original_winner": effective_winner.to_dict() if winners else None,
        "filled_values": fill,
        "fill_check": None if fill_run is None else fill_run.get("check"),
        "fill_accepted": None if fill_run is None else fill_run["accepted"],
        "fill_attempts": None if fill_run is None else fill_run["attempts"],
        "fill_blocked_reason": fill_blocked_reason,
        "design_data": fill_run,
        "task": task,
        "task_raw_text": task_raw,
    }
    if brief_run is not None:
        result.update(
            design_brief=True,
            n_valid_proposals=brief_run["n_valid_proposals"],
            brief_selection=brief_run["brief_selection"],
            selection_attempts=brief_run.get("selection_attempts", []),
            design_quality_status=brief_run.get("quality_status"),
            design_quality_findings=brief_run.get("quality_findings", []),
            translation=brief_run["translation"],
            design_brief_source_hashes=brief_run["source_hashes"],
            design_brief_prompt_snapshot=brief_run["prompt_snapshot"],
            design_brief_prompt_template=str(ROOT / "src/generation/prompts/design_briefs.yaml"),
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    label = f"_{args.label}" if args.label else ""
    path = _output_path(
        args.output,
        f"{args.case}_{model.replace('-', '')}_{stamp}{label}",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    print(f"case: {args.case}  model: {model}  k={args.k}")
    if brief_run is None:
        print(f"valid proposals: {len(skeleton_objs)}/{args.k}")
    else:
        print(f"valid design briefs: {brief_run['n_valid_proposals']}/{args.k}")
        translation = brief_run["translation"]
        if translation is not None:
            print(f"D2b translation: {translation['status']}")
            if translation.get("error"):
                print(f"D2b translation reason: {translation['error']}")
    if judge_error:
        print(f"JUDGE ERROR: {judge_error}")
    for c in judged:
        if c.practice_item:
            mark = "PRACTICE"
        elif c.target_named:
            mark = "TARGET-NAMED"
        else:
            mark = "ok"
        print(
            f"  [{c.candidate_id}] activable={c.activation_count} "
            f"{mark}  {c.skeleton.question[:90]}"
        )
    print(f"winners: {[c.candidate_id for c in winners]}")
    if fill_run is not None:
        print(f"fill accepted: {fill_run['accepted']}")
        if fill_run.get("check"):
            print(f"fill check: {fill_run['check'].get('reason')}")
    if fill:
        print(f"filled values: {json.dumps(fill.get('values', fill), ensure_ascii=False)[:200]}")
    if task and task.get("status") == "ready":
        print("\n=== TASK ===")
        print(task.get("title", ""))
        print(task.get("body", ""))
        print("\nQ:", task.get("question", ""))
    elif task and task.get("status") == "blocked":
        print(f"D3 blocked: {task.get('blocking_issues', [])}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
