"""Bounded D2b data proposal, exact checking, and numbers-only repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from scripts import run_situation_skeletons as runner
from src.generation.design_data import (
    check_proposal,
    proposal_from_payload,
    text_numerals,
    validate_values,
    value_numerals,
)

PROMPTS_PATH = runner.ROOT / "src/generation/prompts/design_data.yaml"
MAX_CALLS = 3
MAX_TOKENS = 6000


def _source_hashes() -> dict[str, str]:
    sources = (
        Path(__file__),
        PROMPTS_PATH,
        runner.ROOT / "src/generation/design_data.py",
        runner.ROOT / "src/generation/design_calculator.py",
        runner.ROOT / "src/generation/fill_check.py",
        Path(runner.__file__),
    )
    return {
        str(path.relative_to(runner.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sources
    }


def _prompts() -> dict[str, str]:
    return yaml.safe_load(PROMPTS_PATH.read_text())


def _requirements(winner) -> list[str]:
    requirements = list(winner.design_brief.number_requirements)
    for requirement in winner.number_requirements:
        if requirement.condition not in requirements:
            requirements.append(requirement.condition)
    return requirements


def _context(case: dict, winner, prior_context: dict) -> dict[str, str]:
    return {
        "target_concept": case["target_concept"],
        "student_context": json.dumps(runner._writer_student_context(case, prior_context)),
        "prior_context": runner._format_prior_context(prior_context),
        "design_brief": json.dumps(winner.design_brief.to_dict(), ensure_ascii=False),
        "requirements": json.dumps(list(enumerate(_requirements(winner))), ensure_ascii=False),
    }


def run_design_data(
    client,
    model: str,
    case: dict,
    winner,
    prior_context: dict,
    *,
    initial_proposal=None,
    require_roles: bool = True,
) -> dict:
    source_hashes = _source_hashes()
    prompts = _prompts()
    context = _context(case, winner, prior_context)
    requirements = _requirements(winner)
    attempts = []
    proposal = (
        None if initial_proposal is None else proposal_from_payload(initial_proposal, requirements)
    )
    check = None if proposal is None else check_proposal(proposal)
    initial_check = check
    feedback = ""
    status = "invalid"
    error = None
    for attempt in range(1, MAX_CALLS + 1):
        if check is not None and not check["failures"]:
            status = check["status"]
            error = None if check["accepted"] else check["reason"]
            break
        if check is not None and not feedback:
            feedback = json.dumps(check, ensure_ascii=False)
        stage = "PROPOSE" if proposal is None else "REPAIR"
        values = {
            **context,
            "feedback": feedback,
            "proposal": json.dumps(proposal, ensure_ascii=False),
        }
        request = {
            role.lower(): runner._render(prompts[f"{stage}_DATA_{role}"], values)
            for role in ("SYSTEM", "USER")
        }
        payload, raw = runner.chat_json(
            client,
            model,
            request["system"],
            request["user"],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
        )
        record = {
            "attempt": attempt,
            "stage": stage.lower(),
            "payload": payload,
            "raw_text": raw,
            "prompts": request,
            "error": None,
            "check": None,
        }
        attempts.append(record)
        try:
            if proposal is None:
                proposal = proposal_from_payload(payload, requirements, require_roles=require_roles)
            else:
                if not isinstance(payload, dict) or set(payload) != {"values"}:
                    raise ValueError("repair may return only values; conditions remain frozen")
                repaired = validate_values(
                    payload["values"], proposal["quantities"], proposal["values"]
                )
                proposal = {**proposal, "values": repaired}
        except ValueError as exc:
            error = record["error"] = str(exc)
            status = "invalid"
            feedback = json.dumps({"error": error, "previous_response": payload})
            continue
        check = check_proposal(proposal)
        record["check"] = check
        status = check["status"]
        error = None if check["accepted"] else check["reason"]
        if not check["failures"]:
            break
        feedback = json.dumps(check, ensure_ascii=False)
    source_hashes_after = _source_hashes()
    return {
        "schema_version": "design-data-run/v1",
        "status": status,
        "accepted": status == "accepted",
        "proceed": proposal is not None,
        "quality_findings": (
            []
            if check is None
            else list(
                dict.fromkeys(check["failures"] + check["textual_failures"] + check["warnings"])
            )
        )
        + ([error] if status == "invalid" and error else []),
        "payload": proposal,
        "initial_proposal": initial_proposal,
        "initial_check": initial_check,
        "requirements": requirements,
        "new_proposal_roles_required": require_roles,
        "check": check,
        "attempts": attempts,
        "error": error,
        "source_hashes": source_hashes,
        "source_hashes_after": source_hashes_after,
        "source_integrity_verified": source_hashes == source_hashes_after,
        "prompt_snapshot": prompts,
    }


def _writer_sources(winner, proposal: dict) -> dict[str, str]:
    brief = winner.design_brief
    sources = {
        f"design_brief.{field}": getattr(brief, field)
        for field in (
            "goal",
            "situation_and_rules",
            "student_question",
            "successful_route",
            "learning_opportunity",
        )
    }
    for field in ("key_idea", "naive_answer"):
        text = getattr(brief, field)
        if text:
            sources[f"design_brief.{field}"] = text
    for index, approach in enumerate(brief.approaches):
        for field in ("first_action", "what_it_establishes", "limitation"):
            text = getattr(approach, field)
            if text:
                sources[f"design_brief.approaches[{index}].{field}"] = text
    for index, requirement in enumerate(_requirements(winner)):
        sources[f"requirements[{index}]"] = requirement
    for name, metadata in proposal["quantities"].items():
        sources[f"proposal.quantities.{name}.description"] = metadata["description"]
    for index, condition in enumerate(proposal["conditions"]):
        sources[f"proposal.conditions[{index}].statement"] = condition["statement"]
    return sources


def _writer_request(case: dict, winner, data_run: dict, prior_context: dict) -> dict[str, str]:
    proposal = data_run["payload"]
    sources = _writer_sources(winner, proposal)
    draft_fields = ("goal", "situation_and_rules", "student_question")
    draft = {f"design_brief.{field}": sources[f"design_brief.{field}"] for field in draft_fields}
    teacher_evidence = [
        {
            "source": source,
            "text": text,
            "instruction": (
                "Do not state or imply the planned method, discovery, or result."
                if source.startswith("design_brief.")
                else "Withhold derived conclusions and method details, not necessary task rules."
            ),
        }
        for source, text in sources.items()
        if source not in draft and not source.startswith("proposal.quantities.")
    ]
    teacher_evidence.extend(
        {
            "source": f"proposal.quantities.{name}.description",
            "text": metadata["description"],
            "unit": metadata["unit"],
            "role": "teacher_example",
            "values": proposal["values"][name],
            "instruction": (
                "Teacher-only verification example. Do not supply these values or "
                "a substitute construction; students must choose their own."
            ),
        }
        for name, metadata in proposal["quantities"].items()
        if metadata.get("role") == "teacher_example"
    )
    # Historical unlabeled quantities remain candidates for the content-based writer rule.
    student_quantities = {
        name: metadata
        for name, metadata in proposal["quantities"].items()
        if metadata.get("role") != "teacher_example"
    }

    prompts = _prompts()
    context = {
        "student_context": json.dumps(runner._writer_student_context(case, prior_context)),
        "prior_context": runner._format_prior_context(prior_context),
        "student_draft": json.dumps(draft, ensure_ascii=False),
        "proposal": json.dumps(
            {
                "quantities": student_quantities,
                "values": {name: proposal["values"][name] for name in student_quantities},
            },
            ensure_ascii=False,
        ),
        "do_not_state": json.dumps(teacher_evidence, ensure_ascii=False),
        "check": json.dumps(data_run["check"], ensure_ascii=False),
    }
    request = {
        role.lower(): runner._render(prompts[f"WRITE_DATA_TASK_{role}"], context)
        for role in ("SYSTEM", "USER")
    }
    findings = ([winner.main_concern] if winner.main_concern else []) + data_run.get(
        "quality_findings", []
    )
    if findings:
        request["user"] += "\n\nINTERNAL UNRESOLVED FINDINGS (not student wording):\n" + json.dumps(
            findings, ensure_ascii=False
        )
    return request


def _validate_writer_payload(payload: object, winner, proposal: dict) -> dict:
    task = runner._validate_task_payload(payload)
    withheld = task.get("withheld")
    if not isinstance(withheld, list):
        raise ValueError("writer withheld must be a list, including when empty")
    sources = _writer_sources(winner, proposal)
    for item in withheld:
        if not isinstance(item, dict) or set(item) != {"kind", "source", "quote", "reason"}:
            raise ValueError("withheld entries require kind, source, quote and reason")
        if item["kind"] not in ("discovery", "quantity"):
            raise ValueError("withheld kind must be discovery or quantity")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in item):
            raise ValueError("withheld fields must be non-empty strings")
        source = item["source"]
        if source not in sources or item["quote"] not in sources[source]:
            raise ValueError("withheld quote must occur verbatim in its identified source")
        if item["kind"] == "quantity" and (
            not source.startswith("proposal.quantities.") or item["quote"] != sources[source]
        ):
            raise ValueError("withheld quantity must quote its complete quantity description")
    if task["status"] == "ready" and any(
        metadata.get("role") == "teacher_example" for metadata in proposal["quantities"].values()
    ):
        observed = text_numerals("\n".join(task[field] for field in ("title", "body", "question")))
        warnings = [
            {
                "source": f"proposal.quantities.{name}.description",
                "reason": (
                    "All numerals of this teacher example occur in student text. "
                    "Inspect for a disclosed construction; shared numerals can be coincidental. "
                    "This is a nonblocking screen, not a semantic leakage judgment."
                ),
            }
            for name, metadata in proposal["quantities"].items()
            if metadata.get("role") == "teacher_example"
            and not (value_numerals(proposal["values"][name]) - observed)
        ]
        task = {**task, "teacher_example_warnings": warnings}
    return task


def write_design_data_task(
    client, model: str, case: dict, winner, data_run: dict, prior_context: dict
) -> tuple[dict, str]:
    request = _writer_request(case, winner, data_run, prior_context)
    check = data_run["check"] or {}
    findings = list(
        dict.fromkeys(
            ([winner.main_concern] if winner.main_concern else [])
            + data_run.get("quality_findings", [])
            + check.get("failures", [])
            + check.get("textual_failures", [])
            + check.get("warnings", [])
        )
    )
    attempts = []
    draft = None
    feedback = ""
    for attempt in range(MAX_CALLS):
        active_request = {**request, "user": request["user"] + feedback}
        payload, raw = runner.chat_json(
            client,
            model,
            active_request["system"],
            active_request["user"],
            temperature=0.7,
            max_tokens=runner.PROPOSE_MAX_TOKENS,
        )
        record = {
            "payload": payload,
            "raw_text": raw,
            "prompts": active_request,
            "error": None,
        }
        attempts.append(record)
        try:
            task = _validate_writer_payload(payload, winner, data_run["payload"])
            if task["status"] != "ready":
                raise ValueError("; ".join(task["blocking_issues"]))
        except ValueError as exc:
            record["error"] = str(exc)
            if isinstance(payload, dict):
                try:
                    core = runner._validate_task_payload(
                        {
                            **payload,
                            "status": "ready",
                            "blocking_issues": [],
                        }
                    )
                except ValueError as core_error:
                    record["draft_error"] = str(core_error)
                else:
                    draft = (core, raw, attempt)
            feedback = "\n\nREVISION FEEDBACK:\n" + json.dumps(
                {
                    "previous_response": payload,
                    "issue": str(exc),
                    "instruction": (
                        "Return a complete student task, not a refusal. Revise the draft to "
                        "address the issue. Preserve the supplied target and data. Correct "
                        "omission records using exact source quotes; unresolved design concerns "
                        "are internal findings, not reasons to leave student text empty."
                    ),
                },
                ensure_ascii=False,
            )
        else:
            return {
                **task,
                "quality_status": "review_needed" if findings else "no_reported_concern",
                "quality_findings": findings,
                "writer_attempts": attempts,
                "writer_selected_attempt": attempt,
            }, raw
    if draft is None:
        raise ValueError(
            f"Writer produced no usable task after {MAX_CALLS} calls: {attempts[-1]['error']}"
        )
    task, raw, selected_attempt = draft
    findings = list(
        dict.fromkeys(
            findings
            + [
                attempts[selected_attempt]["error"],
                attempts[-1]["error"],
            ]
        )
    )
    return {
        **task,
        "quality_status": "review_needed",
        "quality_findings": findings,
        "withheld": [],
        "unverified_withheld": task.get("withheld"),
        "withheld_validation_status": "unverified",
        "writer_attempts": attempts,
        "writer_selected_attempt": selected_attempt,
    }, raw
