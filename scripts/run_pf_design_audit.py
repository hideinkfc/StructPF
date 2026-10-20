"""Run a bounded, blind exploratory audit on saved PF tasks; never generate tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAIError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.evaluation.pf_design_audit as design_audit  # noqa: E402
import src.evaluation.pf_rubric as table1  # noqa: E402
from scripts.prior_methods.common import MODEL_ENVS, chat_json, load_client  # noqa: E402
from scripts.run_pf_diagnostic import _determine_effective_settings  # noqa: E402

DEFAULT_BENCHMARK = ROOT / "experiments/results/pf_paper_benchmark/20260923_luna_v4"
DEFAULT_PILOT = ROOT / (
    "experiments/results/pf_paper_benchmark/20260925_grade7_pipeline_feasibility_standalone_table1"
)
DEFAULT_CONTROLS = ROOT / "experiments/configs/pf_design_audit_controls.json"
CONDITIONS = ("V1", "V2", "V3", "PIPELINE")
SETTINGS = {"temperature": 0.0, "max_tokens": 4000}
RUBRIC_VERSION = "pf-design-audit/exploratory-v5"
TABLE1_VERSION = "rahimi-table1/v1"
SHUFFLE_SEED = 20260925
COMPARISON_DIMENSIONS = {
    "MR": "approach_diversity",
    "OE": "task_openness",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _recorded_path(value: str, project_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _validate_saved_benchmark(benchmark_root: Path, project_root: Path) -> tuple[dict, dict]:
    manifest = _read_json(benchmark_root / "manifest.json")
    config = _read_json(benchmark_root / "config.json")
    if list(manifest.get("conditions", [])) != list(CONDITIONS):
        raise ValueError(f"Saved benchmark conditions must be exactly {list(CONDITIONS)}")
    if manifest.get("source_integrity_unchanged") is not True:
        raise ValueError("Saved benchmark source integrity is not confirmed")
    before = manifest.get("source_hashes")
    after = manifest.get("source_hashes_after")
    if not isinstance(before, dict) or before != after:
        raise ValueError("Saved benchmark source hashes differ before and after the run")

    for relative in (
        "src/evaluation/prompts/pf_rubric.yaml",
        "src/evaluation/pf_rubric.py",
    ):
        expected = before.get(relative)
        path = project_root / relative
        if not isinstance(expected, str) or not path.is_file() or _sha256(path) != expected:
            raise ValueError(
                f"Frozen Table 1 source does not match the saved benchmark: {relative}"
            )
    if table1.load_prompt()["version"] != TABLE1_VERSION:
        raise ValueError(f"Frozen comparison requires {TABLE1_VERSION}")
    if not isinstance(config.get("case", {}).get("target_concept"), str):
        raise ValueError("Saved benchmark config is missing its shared target concept")
    if not isinstance(config.get("learner_context"), dict):
        raise ValueError("Saved benchmark config is missing its shared learner context")
    return manifest, config


def _frozen_baseline(judgment: dict, source_path: Path) -> dict:
    raw = judgment.get("raw_response")
    if judgment.get("status") != "scored" or not isinstance(raw, str):
        raise ValueError(f"Frozen Table 1 judgment is not scored: {source_path}")
    parsed = table1.parse_rating(raw)
    if parsed["status"] != "scored" or parsed["scores"] != judgment.get("scores"):
        raise ValueError(f"Frozen Table 1 judgment does not match its raw response: {source_path}")
    return {
        "rubric_version": TABLE1_VERSION,
        "scores": parsed["scores"],
        "mathematical_concerns": parsed["rating"]["mathematical_concerns"],
        "source": str(source_path),
        "source_sha256": _sha256(source_path),
    }


def _trace_evidence(
    record: dict,
    source_path: Path,
    source_bytes: bytes,
    expected_source_ids: set[str],
) -> dict:
    pipeline = record.get("pipeline_result")
    source = _relative_or_absolute(source_path, ROOT)
    if not isinstance(pipeline, dict):
        return {
            "availability": "unavailable",
            "source": source,
            "source_sha256": _sha256_bytes(source_bytes),
            "verification": "unknown",
            "interpretation": (
                "No structured pathway trace was supplied; unavailable is not a task failure."
            ),
        }

    stages = pipeline.get("stages", {})
    d1 = stages.get("D1", {}) if isinstance(stages, dict) else {}
    d2 = stages.get("D2_D3", {}) if isinstance(stages, dict) else {}
    d1_output = d1.get("output", {}) if isinstance(d1, dict) else {}
    retrieval = d1_output.get("retrieval", {}) if isinstance(d1_output, dict) else {}
    found_ids = retrieval.get("evidence_ids", []) if isinstance(retrieval, dict) else []
    found_ids = [value for value in found_ids if isinstance(value, str)]
    expected_trace_ids = {
        f"official:{standard_id}": standard_id for standard_id in expected_source_ids
    }
    mapped_source_ids = sorted(
        {expected_trace_ids[value] for value in found_ids if value in expected_trace_ids}
    )
    if found_ids:
        unexpected_ids = sorted(set(found_ids) - set(expected_trace_ids))
        source_verification = "concern" if unexpected_ids else "checked"
    else:
        unexpected_ids = []
        source_verification = "unknown"

    math_plan = d2.get("math_plan", {}) if isinstance(d2, dict) else {}
    fill = d2.get("fill", {}) if isinstance(d2, dict) else {}
    check = fill.get("check", {}) if isinstance(fill, dict) else {}
    if isinstance(check, dict) and check.get("accepted") is True:
        recorded_status = "accepted_recorded"
    elif isinstance(check, dict) and check.get("accepted") is False:
        recorded_status = "rejected_recorded"
    else:
        recorded_status = "not_provided"
    prior_contrast = math_plan.get("prior_contrast") if isinstance(math_plan, dict) else None
    return {
        "availability": "available",
        "source": source,
        "source_sha256": _sha256_bytes(source_bytes),
        "verification": "trace_present_not_independently_verified",
        "curriculum_evidence_ids": found_ids,
        "mapped_curriculum_standard_ids": mapped_source_ids,
        "curriculum_id_check": {
            "status": source_verification,
            "scope": (
                "Exact official:{standard_id} mapping to standard_id values in the saved "
                "benchmark config; no prefix stripping."
            ),
            "unexpected_ids": unexpected_ids,
        },
        "selected_prior_contrast": (
            "provided_not_independently_reverified" if prior_contrast else "not_provided"
        ),
        "recorded_math_check": {
            "status": recorded_status,
            "check_status": check.get("status") if isinstance(check, dict) else None,
            "reason": check.get("reason") if isinstance(check, dict) else None,
            "scope": (
                "Recorded outcome from the saved checker only. It is not independently "
                "verified mathematical truth or proof, and says nothing about student behavior "
                "or task openness."
            ),
        },
    }


def _make_case(
    *,
    case_id: str,
    kind: str,
    condition: str,
    task: dict,
    context: dict,
    target: str,
    source_path: Path,
    source_bytes: bytes,
    baseline: dict | None,
    trace_evidence: dict,
) -> dict:
    student_text = table1.student_task_text(task)
    user_prompt = design_audit.design_audit_input(student_text, target, context)
    input_object = json.loads(user_prompt)
    if set(input_object) != {"learning_target", "learner_context", "student_task"}:
        raise ValueError("Design-audit input contains fields outside the blind allowlist")
    return {
        "case_id": case_id,
        "kind": kind,
        "condition": condition,
        "source": _relative_or_absolute(source_path, ROOT),
        "source_sha256": _sha256_bytes(source_bytes),
        "student_task_sha256": _sha256_bytes(student_text.encode("utf-8")),
        "user_input_sha256": _sha256_bytes(user_prompt.encode("utf-8")),
        "user_prompt": user_prompt,
        "frozen_table1_baseline": baseline,
        "trace_evidence": trace_evidence,
    }


def load_calibration_cases(
    benchmark_root: Path = DEFAULT_BENCHMARK,
    pilot_root: Path = DEFAULT_PILOT,
    *,
    per_condition: int = 1,
    offset_per_condition: int = 2,
    include_checked_pilot: bool = False,
    seed: int = SHUFFLE_SEED,
    project_root: Path = ROOT,
) -> list[dict]:
    """Select a bounded, balanced set without defaulting to the earlier v1 cases."""
    if per_condition not in (1, 2):
        raise ValueError("The exploratory calibration is capped at one or two cases per condition")
    if offset_per_condition not in (0, 1, 2, 3):
        raise ValueError("offset_per_condition must be 0, 1, 2, or 3")
    manifest, config = _validate_saved_benchmark(benchmark_root, project_root)
    target = config["case"]["target_concept"]
    context = config["learner_context"]
    expected_source_ids = {
        item.get("standard_id")
        for item in config.get("grounding_evidence", [])
        if isinstance(item, dict) and isinstance(item.get("standard_id"), str)
    }
    cases = []
    for condition in CONDITIONS:
        attempt_paths = sorted(
            (benchmark_root / "attempts" / condition).glob("*/attempt.json"),
            key=lambda path: int(path.parent.name),
        )
        selected = []
        skipped = 0
        for attempt_path in attempt_paths:
            attempt_bytes = attempt_path.read_bytes()
            attempt = json.loads(attempt_bytes)
            if attempt.get("attempt_id", "").split("-", 1)[0] != condition:
                raise ValueError(f"Attempt condition mismatch in {attempt_path}")
            if attempt.get("status") != "ready":
                continue
            judgment_path = attempt_path.parent / "judgment.json"
            if not judgment_path.is_file():
                continue
            judgment = _read_json(judgment_path)
            baseline = _frozen_baseline(judgment, judgment_path)
            if skipped < offset_per_condition:
                skipped += 1
                continue
            selected.append((attempt_path, attempt_bytes, attempt, baseline))
            if len(selected) == per_condition:
                break
        if len(selected) != per_condition:
            raise ValueError(
                f"Only {len(selected)} ready, Table 1-scored cases found for {condition}; "
                f"requested {per_condition}"
            )
        for attempt_path, attempt_bytes, attempt, baseline in selected:
            cases.append(
                _make_case(
                    case_id=attempt["attempt_id"],
                    kind="saved_benchmark_task",
                    condition=condition,
                    task=attempt["task"],
                    context=context,
                    target=target,
                    source_path=attempt_path,
                    source_bytes=attempt_bytes,
                    baseline=baseline,
                    trace_evidence=_trace_evidence(
                        attempt, attempt_path, attempt_bytes, expected_source_ids
                    ),
                )
            )

    if not include_checked_pilot:
        random.Random(seed).shuffle(cases)
        return cases

    pilot_provenance = _read_json(pilot_root / "input/provenance.json")
    replay_path = pilot_root / "input/grade7_replay.json"
    replay_bytes = replay_path.read_bytes()
    if _sha256_bytes(replay_bytes) != pilot_provenance.get("replay_input_sha256"):
        raise ValueError("Checked-pilot replay input hash does not match its provenance")
    if pilot_provenance.get("learner_context_identical_to_frozen_config") is not True:
        raise ValueError("Checked-pilot learner context is not attested as the frozen context")
    replay = json.loads(replay_bytes)
    pilot_context = replay.get("new_writer_context", {}).get("student_context")
    if pilot_context != context:
        raise ValueError("Checked-pilot learner context differs from the shared benchmark context")

    pilot_source_path = _recorded_path(pilot_provenance["source_attempt"], project_root)
    pilot_source_bytes = pilot_source_path.read_bytes()
    if _sha256_bytes(pilot_source_bytes) != pilot_provenance.get("source_attempt_sha256"):
        raise ValueError("Checked-pilot source attempt hash does not match its provenance")
    pilot_record = json.loads(pilot_source_bytes)
    rating_path = pilot_root / "judge_run/ratings.jsonl"
    ratings = [
        json.loads(line)
        for line in rating_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [item for item in ratings if item.get("case_id") == replay.get("case_id")]
    if len(matches) != 1 or matches[0].get("rubric_version") != TABLE1_VERSION:
        raise ValueError("Checked pilot must have exactly one frozen Table 1/v1 baseline")
    if matches[0].get("source_sha256") != _sha256_bytes(replay_bytes):
        raise ValueError("Checked-pilot baseline was rated from a different replay input")
    baseline = _frozen_baseline(matches[0], rating_path)
    cases.append(
        _make_case(
            case_id="checked_grade7_pilot_20260925",
            kind="checked_pilot_task",
            condition="calibration_pilot",
            task=replay["task"],
            context=pilot_context,
            target=target,
            source_path=replay_path,
            source_bytes=replay_bytes,
            baseline=baseline,
            trace_evidence=_trace_evidence(
                pilot_record, pilot_source_path, pilot_source_bytes, expected_source_ids
            ),
        )
    )
    random.Random(seed).shuffle(cases)
    return cases


def load_synthetic_controls(path: Path = DEFAULT_CONTROLS) -> list[dict]:
    source_bytes = path.read_bytes()
    controls = json.loads(source_bytes)
    if not isinstance(controls, list) or not 1 <= len(controls) <= 6:
        raise ValueError("Synthetic controls must be a fixed list of one to six cases")
    source_hash = _sha256_bytes(source_bytes)
    cases = []
    for item in controls:
        if not isinstance(item, dict) or item.get("kind") != "synthetic_control_not_human_rated":
            raise ValueError(
                "Every control must be explicitly marked synthetic and not human-rated"
            )
        case_id = item.get("case_id")
        target = item.get("learning_target")
        student_text = item.get("student_task")
        context = item.get("learner_context")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("Each synthetic control requires a case_id")
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"Synthetic control {case_id} requires a learning_target")
        if not isinstance(student_text, str) or not student_text.strip():
            raise ValueError(f"Synthetic control {case_id} requires a student_task")
        if not isinstance(context, dict):
            raise ValueError(f"Synthetic control {case_id} requires a learner_context object")
        user_prompt = design_audit.design_audit_input(student_text, target, context)
        payload = json.loads(user_prompt)
        if set(payload) != {"learning_target", "learner_context", "student_task"}:
            raise ValueError(f"Synthetic control {case_id} exceeds the blind input allowlist")
        cases.append(
            {
                "case_id": case_id,
                "kind": "synthetic_control_not_human_rated",
                "condition": "synthetic_control",
                "control_topic": item.get("topic"),
                "control_purpose": item.get("control_purpose"),
                "illustrative_signals": item.get("illustrative_signals"),
                "source": _relative_or_absolute(path, ROOT),
                "source_sha256": source_hash,
                "student_task_sha256": _sha256_bytes(student_text.encode("utf-8")),
                "user_input_sha256": _sha256_bytes(user_prompt.encode("utf-8")),
                "user_prompt": user_prompt,
                "frozen_table1_baseline": None,
                "trace_evidence": {
                    "availability": "unavailable",
                    "source": _relative_or_absolute(path, ROOT),
                    "source_sha256": source_hash,
                    "verification": "unknown",
                    "interpretation": (
                        "Synthetic control has no pathway trace; unavailable is not a task failure."
                    ),
                },
            }
        )
    identifiers = [item["case_id"] for item in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Synthetic control IDs must be unique")
    return cases


def _potential_disagreements(baseline: dict, audit: dict) -> list[dict]:
    flags = []
    scores = baseline["scores"]
    for dimension, finding_name in COMPARISON_DIMENSIONS.items():
        score = scores.get(dimension)
        status = audit[finding_name]["status"]
        if (score == 3 and status == "not_evidenced") or (score == 1 and status == "supported"):
            flags.append(
                {
                    "kind": "directional_extreme_review",
                    "table1_dimension": dimension,
                    "table1_score": score,
                    "audit_finding": finding_name,
                    "audit_status": status,
                    "interpretation": "Potential cross-protocol tension; not a score equivalence.",
                }
            )
    old_concerns = baseline["mathematical_concerns"]
    new_concerns = audit["mathematics_review"]["concerns"]
    if audit["mathematics_review"]["status"] != "unknown" and bool(old_concerns) != bool(
        new_concerns
    ):
        flags.append(
            {
                "kind": "mathematics_concern_presence_review",
                "table1_concern_count": len(old_concerns),
                "audit_concern_count": len(new_concerns),
                "interpretation": (
                    "Concern presence differs; compare the text manually. "
                    "The finding is not an adjudicated disagreement."
                ),
            }
        )
    return flags


def rate_case(
    client: Any,
    model: str,
    system: str,
    user: str,
    *,
    chat=chat_json,
) -> dict:
    try:
        _, raw = chat(client, model, system, user, **SETTINGS)
    except OpenAIError as exc:
        return {
            "status": "api_error",
            "audit": None,
            "raw_response": None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    try:
        return {**design_audit.parse_design_audit(raw), "raw_response": raw}
    except ValidationError as exc:
        return {
            "status": "invalid_response",
            "audit": None,
            "raw_response": raw,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }


def run_cases(
    cases: list[dict],
    output: Path,
    *,
    selector: str = "luna",
    dry_run: bool = False,
    client_loader=load_client,
    chat=chat_json,
) -> dict:
    if selector not in MODEL_ENVS:
        raise ValueError(f"Unknown model selector: {selector}")
    case_ids = [case["case_id"] for case in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise ValueError("Case IDs must be nonempty and unique")
    prompt = design_audit.load_prompt()
    if prompt["version"] != RUBRIC_VERSION:
        raise ValueError(f"Unexpected exploratory rubric version: {prompt['version']}")
    benchmark_inputs = []
    synthetic_control_ids = []
    for case in cases:
        user_prompt = case["user_prompt"]
        payload = json.loads(user_prompt)
        if set(payload) != {"learning_target", "learner_context", "student_task"}:
            raise ValueError("Judge input contains fields outside the blind allowlist")
        if any(label in user_prompt for label in (*CONDITIONS, "calibration_pilot")):
            raise ValueError("Judge input contains an explicit condition label")
        if case.get("kind") == "saved_benchmark_task":
            benchmark_inputs.append(
                (
                    payload["learning_target"],
                    json.dumps(payload["learner_context"], sort_keys=True),
                )
            )
        elif case.get("kind") == "synthetic_control_not_human_rated":
            synthetic_control_ids.append(case["case_id"])
    shared_benchmark_context = len(set(benchmark_inputs)) <= 1
    if not shared_benchmark_context:
        raise ValueError("Saved benchmark tasks must share one target and learner context")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "pf-design-audit-run/v1",
        "status": "prepared" if dry_run else "starting",
        "scope": (
            "Bounded exploratory calibration; not a full benchmark, human calibration, "
            "or evidence of student outcomes."
        ),
        "rubric_version": prompt["version"],
        "rubric_source": prompt["source"],
        "condition_blind": True,
        "blind_input_verification": {
            "passed": True,
            "cases_checked": len(cases),
            "allowed_fields": ["learning_target", "learner_context", "student_task"],
            "explicit_condition_labels_in_inputs": False,
            "teacher_facing_wrapper_fields_included": False,
            "benchmark_target_and_context_shared": shared_benchmark_context,
            "synthetic_control_metadata_included": False,
        },
        "synthetic_control_use": {
            "included": bool(synthetic_control_ids),
            "case_ids": synthetic_control_ids,
            "interpretation": (
                "Reused controls are schema/unknown smoke only, not independent validation "
                "or human-rated reference cases."
                if synthetic_control_ids
                else "No synthetic controls were included."
            ),
        },
        "blinding_policy": (
            "The model receives only the learning target, learner context, and allowlisted "
            "student-facing task text. Compared benchmark cases share target/context; synthetic "
            "controls use their own stated context. Case identifiers, condition labels, "
            "control metadata, teacher claims, frozen ratings, and traces are not sent."
        ),
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in (
                design_audit.PROMPT_PATH,
                Path(__file__).resolve(),
                ROOT / "src/evaluation/pf_design_audit.py",
                table1.PROMPT_PATH,
                ROOT / "src/evaluation/pf_rubric.py",
                ROOT / "scripts/prior_methods/common.py",
                ROOT / "scripts/run_pf_diagnostic.py",
                DEFAULT_CONTROLS,
            )
        },
        "system_prompt": prompt["system"],
        "model_selector": selector,
        "requested_settings": SETTINGS,
        "case_count": len(cases),
        "created_at": _now(),
        "cases": cases,
    }
    _write_json(output / "manifest.json", manifest)
    if dry_run:
        return manifest

    try:
        client, model = client_loader(selector)
    except Exception:
        manifest["status"] = "client_load_failed"
        manifest["finished_at"] = _now()
        _write_json(output / "manifest.json", manifest)
        raise
    manifest.update(
        {
            "status": "running",
            "model_name": model,
            "effective_settings": {
                **_determine_effective_settings(model, SETTINGS),
                "response_format": {"type": "json_object"},
                "timeout": 180,
            },
            "usage_metadata": "Not returned by the shared chat_json helper.",
        }
    )
    _write_json(output / "manifest.json", manifest)

    results = []
    with (output / "ratings.jsonl").open("x", encoding="utf-8") as stream:
        for case in cases:
            started = _now()
            rating = rate_case(client, model, prompt["system"], case["user_prompt"], chat=chat)
            result = {
                **case,
                "started_at": started,
                "finished_at": _now(),
                "model_name": model,
                "rubric_version": prompt["version"],
                "model_calls": 1,
                **rating,
            }
            if isinstance(rating.get("audit"), dict):
                baseline = case.get("frozen_table1_baseline")
                result["potential_disagreements"] = (
                    _potential_disagreements(baseline, rating["audit"])
                    if isinstance(baseline, dict)
                    else None
                )
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            results.append(result)
            print(f"{case['case_id']}: {rating['status']}", flush=True)
            if "error" in rating:
                print(f"  {rating['error']['type']}: {rating['error']['message']}", flush=True)

    finding_counts: Counter[str] = Counter()
    for result in results:
        audit = result.get("audit")
        if not isinstance(audit, dict):
            continue
        for name in (
            "target_relevance",
            "prior_resource_start",
            "useful_contrast",
            "approach_diversity",
            "task_openness",
        ):
            finding_counts[f"{name}:{audit[name]['status']}"] += 1
        finding_counts[f"mathematics_review:{audit['mathematics_review']['status']}"] += 1

    scored = sum(result["status"] == "scored" for result in results)
    unknown = sum(result["status"] == "unknown" for result in results)
    failed = len(results) - scored - unknown
    baseline_results = [
        result for result in results if isinstance(result.get("frozen_table1_baseline"), dict)
    ]
    baseline_valid = sum(result["status"] in {"scored", "unknown"} for result in baseline_results)
    baseline_scored = sum(result["status"] == "scored" for result in baseline_results)
    potential = [
        {"case_id": result["case_id"], **flag}
        for result in results
        for flag in (result.get("potential_disagreements") or [])
    ]
    controls_included = any(
        result["kind"] == "synthetic_control_not_human_rated" for result in results
    )
    summary = {
        "attempted": len(results),
        "scored": scored,
        "unknown": unknown,
        "failed": failed,
        "model_calls": len(results),
        "condition_blind": True,
        "blind_input_verification": manifest["blind_input_verification"],
        "synthetic_control_use": manifest["synthetic_control_use"],
        "response_rates": {
            "scored": scored / len(results),
            "unknown": unknown / len(results),
            "failed": failed / len(results),
        },
        "case_counts_by_kind": dict(Counter(result["kind"] for result in results)),
        "unknown_findings_by_field": {
            key: count for key, count in sorted(finding_counts.items()) if key.endswith(":unknown")
        },
        "finding_status_counts": dict(sorted(finding_counts.items())),
        "potential_disagreements_with_frozen_judge": potential,
        "frozen_judge_comparison": {
            "status": (
                "not_assessable"
                if baseline_scored == 0
                else "complete"
                if baseline_scored == len(baseline_results)
                else "partial"
            ),
            "comparable_total": False,
            "cases_with_valid_responses": baseline_valid,
            "cases_with_assessable_findings": baseline_scored,
            "cases_without_assessable_findings": len(baseline_results) - baseline_scored,
            "potential_disagreement_count": len(potential) if baseline_scored else None,
            "rule": (
                "Report only predeclared endpoint tensions for MR/OE and differences in "
                "mathematical-concern presence. These are review flags, not score conversions "
                "or adjudicated disagreements."
            ),
            "limitation": (
                "No common total exists across protocols. Semantic differences between concern "
                "texts and all other cross-rubric disagreements require human review."
            ),
        },
        "limitations": [
            "One automated rating per task; no repeatability or human agreement was measured.",
            "Task affordance findings are hypotheses, not observed student approaches or learning.",
            (
                "The fixed synthetic controls are reused across runs; here they are only "
                "schema/unknown smoke, not independent validation or human-rated references."
                if controls_included
                else "No synthetic controls were included in this run."
            ),
            "The trace channel is post-hoc and separate; unavailable trace is not a failed task.",
            "The small, preselected calibration set cannot establish condition-level quality.",
            (
                "Do not revise this prompt to improve its apparent condition comparison "
                "on these cases."
            ),
            "No provider usage or cost metadata was available from chat_json.",
        ],
        "ratings": [
            {
                "case_id": result["case_id"],
                "condition": result["condition"],
                "kind": result["kind"],
                "status": result["status"],
                "frozen_table1_scores": (
                    result["frozen_table1_baseline"]["scores"]
                    if isinstance(result.get("frozen_table1_baseline"), dict)
                    else None
                ),
                "potential_disagreement_count": (
                    len(result["potential_disagreements"])
                    if isinstance(result.get("potential_disagreements"), list)
                    else None
                ),
                "model_rationale": result.get("audit"),
            }
            for result in results
        ],
    }
    manifest["status"] = "completed_with_failures" if failed else "completed"
    manifest["finished_at"] = _now()
    _write_json(output / "summary.json", summary)
    _write_json(output / "manifest.json", manifest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--per-condition", type=int, choices=(1, 2), default=1)
    parser.add_argument("--offset-per-condition", type=int, choices=(0, 1, 2, 3), default=2)
    parser.add_argument("--include-checked-pilot", action="store_true")
    parser.add_argument("--include-synthetic-controls", action="store_true")
    parser.add_argument("--seed", type=int, default=SHUFFLE_SEED)
    parser.add_argument("--model", choices=sorted(MODEL_ENVS), default="luna")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cases = load_calibration_cases(
        args.benchmark,
        args.pilot,
        per_condition=args.per_condition,
        offset_per_condition=args.offset_per_condition,
        include_checked_pilot=args.include_checked_pilot,
        seed=args.seed,
    )
    if args.include_synthetic_controls:
        cases.extend(load_synthetic_controls())
        random.Random(args.seed + 1).shuffle(cases)
    result = run_cases(cases, args.output, selector=args.model, dry_run=args.dry_run)
    if result.get("failed", 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
