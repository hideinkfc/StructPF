"""D2a brief search, with explicit historical quantity translation."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from scripts import run_situation_skeletons as runner
from src.generation.design_briefs import DesignBrief, design_brief_from_payload
from src.generation.fill_check import checker_capability_contract
from src.generation.situation_skeletons import (
    JudgedCandidate,
    JudgeSelection,
    judge_selection_from_payload,
    prior_contrast_intent_from_payload,
    quantity_schema_contract,
    skeleton_from_proposal_payload,
)

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "src/generation/prompts/design_briefs.yaml"
MAX_TOKENS = 6000
MAX_SELECTION_REVISIONS = 2


def _prompts(path: Path | None = None) -> dict[str, str]:
    prompts = yaml.safe_load((path or PROMPTS_PATH).read_text())
    required = {
        f"{stage}_BRIEF_{role}"
        for stage in ("PROPOSE", "SELECT", "TRANSLATE")
        for role in ("SYSTEM", "USER")
    }
    if not isinstance(prompts, dict) or set(prompts) != required:
        raise ValueError("design brief prompt file has missing or unexpected sections")
    if any(not isinstance(value, str) or not value.strip() for value in prompts.values()):
        raise ValueError("design brief prompts must be non-empty strings")
    return prompts


def _rubric_guidance() -> str:
    original = runner._prompts()["PROPOSE_SKELETON_SYSTEM"]
    heading = "PUBLISHED RUBRIC (Rahimi et al., Table 1)"
    boundary = "Before proposing or ruling out a situation"
    if heading not in original or boundary not in original:
        raise ValueError("cannot locate the shared published rubric in production prompts")
    return heading + original.split(heading, 1)[1].split(boundary, 1)[0].rstrip()


def _request(
    client, model: str, prompts: dict[str, str], stage: str, values: dict[str, str]
) -> tuple[dict | None, str, dict[str, str]]:
    request = {
        role.lower(): runner._render(prompts[f"{stage}_BRIEF_{role}"], values)
        for role in ("SYSTEM", "USER")
    }
    payload, raw = runner.chat_json(
        client,
        model,
        request["system"],
        request["user"],
        temperature=runner.PROPOSE_TEMPERATURE if stage == "PROPOSE" else 0.0,
        max_tokens=MAX_TOKENS,
    )
    return payload, raw, request


def _propose(
    client,
    model: str,
    prompts: dict[str, str],
    values: dict[str, str],
    resources: list[str],
    *,
    brief_schema_version: str,
    initial_feedback: str = "",
) -> dict[str, Any]:
    attempts = []
    feedback = initial_feedback
    for attempt in range(runner.PROPOSAL_RETRY_MAX + 1):
        payload, raw, request = _request(
            client, model, prompts, "PROPOSE", {**values, "proposal_feedback": feedback}
        )
        record = {"payload": payload, "raw_text": raw, "prompts": request, "error": None}
        try:
            brief = design_brief_from_payload(payload, resources)
            if brief.schema_version != brief_schema_version:
                raise ValueError(f"new design brief requires schema_version={brief_schema_version}")
        except ValueError as exc:
            record["error"] = str(exc)
            attempts.append(record)
            feedback = (
                "Correct only the format/resource-link errors in the original proposal. "
                "Keep its valid goal, rules, approaches, and requirements unchanged.\n"
                + json.dumps({"original_payload": payload, "raw_text": raw, "error": str(exc)})
            )
        else:
            attempts.append(record)
            return {"brief": brief.to_dict(), "brief_obj": brief, "attempts": attempts}
    return {"error": attempts[-1]["error"], "attempts": attempts}


def _translate(
    client, model: str, prompts: dict[str, str], values: dict[str, str], brief: DesignBrief
) -> dict[str, Any]:
    attempts = []
    feedback = ""
    for attempt in range(runner.PROPOSAL_RETRY_MAX + 1):
        payload, raw, request = _request(
            client, model, prompts, "TRANSLATE", {**values, "translation_feedback": feedback}
        )
        record = {"payload": payload, "raw_text": raw, "prompts": request, "error": None}
        if isinstance(payload, dict) and payload.get("status") == "unsupported":
            reason = payload.get("reason")
            if isinstance(reason, str) and reason.strip() and set(payload) == {"status", "reason"}:
                record["error"] = reason.strip()
                attempts.append(record)
                return {"status": "unsupported", "error": reason.strip(), "attempts": attempts}
        try:
            if (
                not isinstance(payload, dict)
                or not {"status", "quantities"}.issubset(payload)
                or set(payload) - {"status", "quantities", "prior_contrast"}
                or payload["status"] != "translated"
            ):
                raise ValueError(
                    "translation requires status=translated, quantities, "
                    "and optional prior_contrast"
                )
            prior_contrast = prior_contrast_intent_from_payload(payload.get("prior_contrast"))
            if prior_contrast is not None and prior_contrast.approach_id not in {
                f"brief_{index}" for index in range(len(brief.approaches))
            }:
                raise ValueError("translation prior_contrast references an unknown brief approach")
            projected = brief.skeleton(()).to_dict()
            projected["approaches"] = [
                {**approach, "resources": list(approach["resources"])}
                for approach in projected["approaches"]
            ]
            projected["quantities"] = payload["quantities"]
            skeleton = skeleton_from_proposal_payload(projected)
        except ValueError as exc:
            record["error"] = str(exc)
            attempts.append(record)
            feedback = "Correct the quantity metadata only; do not change the original brief.\n"
            feedback += json.dumps({"original_payload": payload, "error": str(exc)})
        else:
            attempts.append(record)
            return {
                "status": "translated",
                "skeleton_obj": skeleton,
                "skeleton": skeleton.to_dict(),
                "prior_contrast": (
                    prior_contrast.to_dict() if prior_contrast is not None else None
                ),
                "attempts": attempts,
                "error": None,
            }
    return {"status": "invalid", "error": attempts[-1]["error"], "attempts": attempts}


def run_design_brief_search(
    client,
    model: str,
    case: dict,
    prior_context: dict[str, Any],
    *,
    k: int = 1,
    translate: bool = False,
    prompts_path: Path | None = None,
    brief_schema_version: str = "design-brief/v2",
    design_feedback: str = "",
) -> dict[str, Any]:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("design brief proposal count must be a positive integer")
    if brief_schema_version not in ("design-brief/v1", "design-brief/v2"):
        raise ValueError("unsupported design brief schema version")
    active_prompts_path = prompts_path or PROMPTS_PATH
    prompts = _prompts(active_prompts_path)
    resources = runner._method_names(prior_context)
    values = {
        "target_concept": case["target_concept"],
        "topic": case["topic"],
        "grade": str(case["grade"]),
        "subject": case["subject"],
        "prior_context": runner._format_prior_context(prior_context),
        "rubric_guidance": _rubric_guidance(),
        "checker_contract": checker_capability_contract(),
        "quantity_contract": quantity_schema_contract(),
    }
    source_hashes = {
        str(path.relative_to(runner.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            active_prompts_path,
            Path(__file__),
            runner.ROOT / "src/generation/design_briefs.py",
            runner.ROOT / "src/generation/situation_skeletons.py",
            runner.PROMPTS_PATH,
            runner.ROOT / "scripts/run_situation_skeletons.py",
        )
    }
    if k == 1:
        proposals = [
            _propose(
                client,
                model,
                prompts,
                values,
                resources,
                brief_schema_version=brief_schema_version,
                initial_feedback=design_feedback,
            )
        ]
    else:
        with ThreadPoolExecutor(max_workers=k) as pool:
            futs = [
                pool.submit(
                    _propose,
                    client,
                    model,
                    prompts,
                    values,
                    resources,
                    brief_schema_version=brief_schema_version,
                    initial_feedback=design_feedback,
                )
                for _ in range(k)
            ]
            proposals = [fut.result() for fut in futs]
    briefs = {
        index: proposal.pop("brief_obj")
        for index, proposal in enumerate(proposals)
        if "brief_obj" in proposal
    }
    result: dict[str, Any] = {
        "proposals": proposals,
        "n_valid_proposals": len(briefs),
        "judged": [],
        "winners": [],
        "judge_error": None,
        "judge_raw_text": "",
        "judge_payload": None,
        "brief_selection": None,
        "translation": None,
        "prompt_snapshot": prompts,
        "source_hashes": source_hashes,
        "brief_schema_version": brief_schema_version,
        "selection_attempts": [],
        "quality_status": "unavailable",
        "quality_findings": [],
        "design_feedback": design_feedback,
    }
    if not briefs:
        result["judge_error"] = "no valid design briefs to select"
        return result
    for revision in range(MAX_SELECTION_REVISIONS + 1):
        candidates = [
            {
                "id": index,
                **brief.to_dict(),
                "approaches": [
                    {"id": f"brief_{approach_index}", **approach.to_dict()}
                    for approach_index, approach in enumerate(brief.approaches)
                ],
            }
            for index, brief in briefs.items()
        ]
        payload, raw, request = _request(
            client,
            model,
            prompts,
            "SELECT",
            {**values, "candidates": json.dumps(candidates, ensure_ascii=False)},
        )
        record = {"payload": payload, "raw_text": raw, "prompts": request, "error": None}
        result["selection_attempts"].append(record)
        result["judge_payload"] = payload
        result["judge_raw_text"] = raw
        result["brief_selection"] = dict(record)
        selection = None
        try:
            if not isinstance(payload, dict):
                raise ValueError("unparseable design brief selection")
            selection = judge_selection_from_payload(payload, set(briefs))
            if selection is None:
                raise ValueError("design brief selection requires compact recommended_id")
            if selection.prior_contrast is not None:
                raise ValueError(
                    "design brief selection must not freeze a numerical prior contrast"
                )
            if selection.recommended_id is not None:
                approach_ids = {
                    f"brief_{index}"
                    for index in range(len(briefs[selection.recommended_id].approaches))
                }
                if not selection.approaches or set(selection.approaches) - approach_ids:
                    raise ValueError("design brief selection requires known approaches")
            concern = (
                selection.reason if selection.recommended_id is None else selection.main_concern
            )
        except ValueError as exc:
            concern = record["error"] = str(exc)
            selection = None
        if not concern:
            result["quality_status"] = "no_selection_concern"
            break
        if revision == MAX_SELECTION_REVISIONS:
            result["quality_status"] = "review_needed"
            result["quality_findings"] = [concern]
            if selection is None or selection.recommended_id is None:
                index = max(briefs)
                selection = JudgeSelection(
                    recommended_id=index,
                    approaches=tuple(
                        f"brief_{approach_index}"
                        for approach_index in range(len(briefs[index].approaches))
                    ),
                    reason="Continuing with the latest usable brief after bounded revisions.",
                    main_concern=concern,
                )
                result["brief_selection"]["continuation"] = "latest_usable_brief"
            break
        feedback_index = (
            selection.recommended_id
            if selection is not None and selection.recommended_id is not None
            else max(briefs)
        )
        proposal = _propose(
            client,
            model,
            prompts,
            values,
            resources,
            brief_schema_version=brief_schema_version,
            initial_feedback=(
                "Revise the selected design using this selection feedback. Preserve the target "
                "and learners; keep necessary definitions and permissions. Correct actual "
                "disclosures or feasibility problems rather than refusing the task.\n"
                + json.dumps(
                    {
                        "design_brief": briefs[feedback_index].to_dict(),
                        "feedback": concern,
                    }
                )
                + ("\nOriginal research feedback:\n" + design_feedback if design_feedback else "")
            ),
        )
        index = len(proposals)
        if "brief_obj" in proposal:
            briefs[index] = proposal.pop("brief_obj")
        proposals.append(proposal)
    result["n_valid_proposals"] = len(briefs)
    brief = briefs[selection.recommended_id]
    result["brief_selection"]["selected_brief"] = brief.to_dict()
    skeleton = brief.skeleton(())
    contrast = None
    if translate:
        translated = _translate(
            client,
            model,
            prompts,
            {
                **values,
                "design_brief": json.dumps(brief.to_dict(), ensure_ascii=False),
                "selection": json.dumps(payload, ensure_ascii=False),
            },
            brief,
        )
        skeleton = translated.pop("skeleton_obj", None)
        result["translation"] = translated
        contrast = prior_contrast_intent_from_payload(translated.get("prior_contrast"))
    if skeleton is not None:
        winner = JudgedCandidate(
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
            prior_contrast=contrast,
            design_brief=brief,
        )
        result["judged"] = [winner]
        result["winners"] = [winner]
    return result
