"""Solution-blind prompts and response parsing for first-attempt PF diagnostics."""

from __future__ import annotations

import json

from src.evaluation.pf_rubric import learner_context, student_task_text

OUTPUT_FIELDS = ("written_work", "answer", "unfinished")
SYSTEM_COMMON = (
    "Attempt the supplied mathematics exercise independently. Return the work and "
    "explanation you would put on the page, not private internal deliberations. "
    "A partial attempt is permitted. Do not invent missing task information. "
    "Do not deliberately make errors or manufacture alternative methods. "
    "Return only JSON with written_work (nonempty string), answer (string, possibly "
    "empty for an unfinished attempt), and unfinished (boolean)."
)
STUDENT_SYSTEM = (
    "You are representing a learner making a first attempt before further instruction. "
    "The supplied record describes recently learned resources, not an assigned "
    "solution method. Start from these resources and reason as this learner. "
    "An unfamiliar idea may be constructed from familiar operations; do not assume "
    "a named procedure has already been learned. Do not claim that the record "
    "guarantees an accurate model of a real student.\n\n" + SYSTEM_COMMON
)
SOLVER_SYSTEM = (
    "You are an ordinary mathematical problem solver, without a student persona "
    "or restrictions on learned procedures.\n\n" + SYSTEM_COMMON
)


def attempt_prompt(task: dict, context: dict, profile: dict) -> dict[str, str]:
    condition = profile["condition"]
    if condition not in {"solver", "learner"}:
        raise ValueError(f"Unknown PF attempt condition: {condition!r}")
    data = {"student_task": student_task_text(task)}
    if condition == "learner":
        prior = learner_context(context)
        resources = prior["assumed_prior_knowledge"]
        if resources is None:
            raise ValueError("Learner probe requires explicit prerequisite resources")
        withheld_resource = profile.get("omit_resource")
        if withheld_resource is not None:
            matches = [item for item in resources if item["resource"] == withheld_resource]
            if len(matches) != 1:
                raise ValueError("Omitted prerequisite must match exactly one resource")
            prior["assumed_prior_knowledge"] = [
                item for item in resources if item["resource"] != withheld_resource
            ]
        additions = profile.get("add_resources", [])
        if not isinstance(additions, list):
            raise ValueError("Added learned resources must be a list")
        names = {item["resource"] for item in prior["assumed_prior_knowledge"]}
        for resource in additions:
            if (
                not isinstance(resource, dict)
                or set(resource) != {"resource", "taught_as"}
                or any(
                    not isinstance(resource[field], str) or not resource[field].strip()
                    for field in ("resource", "taught_as")
                )
            ):
                raise ValueError("Added resource requires nonempty resource and taught_as")
            if resource["resource"] in names:
                raise ValueError("Added resource duplicates an existing learned resource")
            names.add(resource["resource"])
            prior["assumed_prior_knowledge"].append(dict(resource))
        prior["record_scope"] = (
            "Hypothetical recent learning record, not a measured mastery diagnosis. "
            "Procedures outside the listed resources have not been directly instructed."
        )
        data["learner_record"] = prior
    return {
        "system": SOLVER_SYSTEM if condition == "solver" else STUDENT_SYSTEM,
        "user": json.dumps(data, ensure_ascii=False, indent=2),
    }


def parse_attempt(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("PF attempt must be a JSON object")
    if set(payload) != set(OUTPUT_FIELDS):
        raise ValueError("PF attempt requires exactly written_work, answer and unfinished")
    if not isinstance(payload["written_work"], str) or not payload["written_work"].strip():
        raise ValueError("PF attempt requires nonempty written work")
    if not isinstance(payload["answer"], str):
        raise ValueError("PF attempt answer must be a string")
    if not isinstance(payload["unfinished"], bool):
        raise ValueError("PF attempt unfinished must be a boolean")
    return {field: payload[field] for field in OUTPUT_FIELDS}
