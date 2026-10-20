"""Evidence-linked review of written PF attempts, not learner-fidelity scoring."""

from __future__ import annotations

from copy import deepcopy

APPROACHES = {
    "arithmetic_mean", "range", "mean_absolute_deviation", "variance_or_sd",
    "frequency_or_concentration", "mean_pairwise_distance", "adjacent_difference",
    "max_deviation", "median_absolute_deviation", "other_measure",
    "equal_fraction_each_block", "whole_block_search", "greedy_or_proportional_claims",
    "recursive_divider_chooser", "other_allocation", "unknown",
    "whole_journey_rate", "unweighted_stage_rates", "elapsed_time_comparison",
    "other_rate_method",
}
FINDINGS = (
    "accessible_start", "familiar_method_limit", "distinct_approaches",
    "task_supplied_method", "missing_or_ambiguous_information",
)


def parse_panel_review(payload: object, panel: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Attempt-panel review must be a JSON object")
    if set(payload) != {"attempts", "findings", "feedback", "summary"}:
        raise ValueError("Panel review requires attempts, findings, feedback and summary")
    attempts = payload["attempts"]
    if not isinstance(attempts, dict) or set(attempts) != set(panel["attempts"]):
        raise ValueError("Panel review must cover every attempted response")
    for label, row in attempts.items():
        if not isinstance(row, dict) or set(row) != {
            "approaches", "mathematics_status", "named_advanced_procedure", "rationale",
        }:
            raise ValueError(f"Invalid attempt coding fields: {label}")
        methods = row["approaches"]
        if (
            not isinstance(methods, list) or not methods
            or any(not isinstance(method, str) or method not in APPROACHES for method in methods)
            or len(set(methods)) != len(methods)
        ):
            raise ValueError(f"Unknown or repeated approach coding: {label}")
        if row["mathematics_status"] not in {"supported", "invalid", "unknown"}:
            raise ValueError(f"Unknown mathematics classification: {label}")
        if not isinstance(row["named_advanced_procedure"], bool):
            raise ValueError(f"Named procedure flag must be a boolean: {label}")
        _text(row["rationale"], label)
    findings = payload["findings"]
    if not isinstance(findings, dict) or set(findings) != set(FINDINGS):
        raise ValueError("Panel review must cover the five fixed findings")
    for name, finding in findings.items():
        if not isinstance(finding, dict) or set(finding) != {"status", "evidence", "reason"}:
            raise ValueError(f"Invalid finding fields: {name}")
        if finding["status"] not in {"observed", "not_observed", "unknown"}:
            raise ValueError(f"Unknown finding status: {name}")
        _evidence(finding["evidence"], panel, required=finding["status"] == "observed")
        _text(finding["reason"], name)
    feedback = payload["feedback"]
    if not isinstance(feedback, list):
        raise ValueError("Panel feedback must be a list")
    for item in feedback:
        if not isinstance(item, dict) or set(item) != {
            "attribution", "destination", "evidence", "observation", "suggestion",
        }:
            raise ValueError("Invalid feedback fields")
        if item["attribution"] not in {"task_evidence", "simulator_slip", "uncertain"}:
            raise ValueError("Unknown feedback attribution")
        if item["destination"] not in {"design", "data", "writer", "none"}:
            raise ValueError("Unknown feedback destination")
        if item["attribution"] != "task_evidence" and item["destination"] != "none":
            raise ValueError("Simulator slips and uncertain findings cannot drive task revision")
        _evidence(item["evidence"], panel, required=True)
        if item["attribution"] == "task_evidence":
            if not any(e["source"] == "task" for e in item["evidence"]):
                raise ValueError("Task attribution requires a task-text evidence anchor")
            if not any(e["source"] in panel["attempts"] for e in item["evidence"]):
                raise ValueError("Task attribution requires an attempt evidence anchor")
        _text(item["observation"], "feedback observation")
        _text(item["suggestion"], "feedback suggestion")
    _text(payload["summary"], "summary")
    return payload


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def _evidence(value: object, panel: dict, *, required: bool) -> None:
    if not isinstance(value, list) or (required and not value):
        raise ValueError("Observed findings require quoted evidence")
    sources = {"task": panel["student_task"]}
    for label, entry in panel["attempts"].items():
        attempt = entry["attempt"]
        sources[label] = (
            attempt["written_work"] + "\n" + attempt["answer"]
            if attempt is not None else entry["unparsed_raw_text"] or ""
        )
    for item in value:
        if not isinstance(item, dict) or set(item) != {"source", "quote"}:
            raise ValueError("Evidence requires source and quote")
        if item["source"] not in sources:
            raise ValueError("Evidence references an unknown source")
        _text(item["quote"], "evidence quote")
        if item["quote"] not in sources[item["source"]]:
            raise ValueError("Evidence quote does not match the saved source")


def retain_panel_review(payload: object, panel: dict) -> dict:
    """Retain usable coding while isolating unverified evidence field by field."""
    if not isinstance(payload, dict):
        raise ValueError("Attempt-panel review must be a JSON object")
    baseline = deepcopy(payload)
    original_findings = baseline.get("findings")
    original_feedback = baseline.get("feedback")
    baseline["findings"] = {
        name: {"status": "unknown", "evidence": [], "reason": "No verified finding available."}
        for name in FINDINGS
    }
    baseline["feedback"] = []
    parse_panel_review(baseline, panel)
    errors, unverified = [], {}
    if not isinstance(original_findings, dict):
        errors.append("Missing or malformed findings map")
        unverified["findings"] = original_findings
    else:
        for name in FINDINGS:
            finding = original_findings.get(name)
            candidate = deepcopy(baseline)
            candidate["findings"][name] = finding
            try:
                parse_panel_review(candidate, panel)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
                unverified[name] = finding
            else:
                baseline["findings"][name] = finding
    if not isinstance(original_feedback, list):
        errors.append("Missing or malformed feedback list")
        unverified["feedback"] = original_feedback
    else:
        for index, item in enumerate(original_feedback):
            candidate = deepcopy(baseline)
            candidate["feedback"] = [item]
            try:
                parse_panel_review(candidate, panel)
            except ValueError as exc:
                errors.append(f"feedback[{index}]: {exc}")
                unverified[f"feedback[{index}]"] = item
            else:
                baseline["feedback"].append(item)
    return {**baseline, "evidence_errors": errors, "unverified_evidence": unverified}
