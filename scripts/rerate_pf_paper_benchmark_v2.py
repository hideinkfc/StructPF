"""Freeze and rerate saved PF benchmark tasks with Rahimi Table 1 rubric v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIError, APIStatusError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.run_pf_diagnostic import _determine_effective_settings  # noqa: E402
from src.evaluation.pf_rubric_v2 import (  # noqa: E402
    DIMENSIONS,
    PROMPT_PATH,
    judge_input,
    load_prompt,
    parse_rating,
    student_task_text,
)

PROTOCOL_PATH = ROOT / "experiments/configs/pf_rubric_v2_rerating.json"
DEFAULT_OUTPUT = ROOT / (
    "experiments/results/pf_paper_benchmark/20260925_rahimi_table1_v2_rerating"
)
CONDITIONS = ("V1", "V2", "V3", "PIPELINE")
VALID_RATING_STATUSES = {"scored", "insufficient_evidence"}
TERMINAL_STATUSES = VALID_RATING_STATUSES | {
    "api_error",
    "api_setup_error",
    "invalid_response",
    "runner_error",
    "interrupted",
    "not_attempted_calibration_blocked",
    "not_eligible",
}
REQUESTED_SETTINGS = {"temperature": 0.0, "max_tokens": 4000}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _append_jsonl(path: Path, value: object) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()


def _source_files() -> dict[str, Path]:
    return {
        "scripts/rerate_pf_paper_benchmark_v2.py": Path(__file__).resolve(),
        "src/evaluation/pf_rubric_v2.py": ROOT / "src/evaluation/pf_rubric_v2.py",
        "src/evaluation/prompts/pf_rubric_v2.yaml": PROMPT_PATH,
        "src/evaluation/pf_rubric.py": ROOT / "src/evaluation/pf_rubric.py",
        "src/evaluation/prompts/pf_rubric.yaml": ROOT / "src/evaluation/prompts/pf_rubric.yaml",
        "scripts/prior_methods/common.py": ROOT / "scripts/prior_methods/common.py",
        "scripts/run_pf_diagnostic.py": ROOT / "scripts/run_pf_diagnostic.py",
    }


def _load_protocol(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    protocol = json.loads(raw)
    if not isinstance(protocol, dict):
        raise ValueError("Rerating protocol must be a JSON object")
    if protocol.get("schema_version") != "rahimi-table1-rerating/v2":
        raise ValueError("Unsupported rerating protocol version")
    if tuple(protocol.get("conditions", ())) != CONDITIONS:
        raise ValueError(f"conditions must be exactly {list(CONDITIONS)}")
    if protocol.get("rubric_version") != "rahimi-table1/v2":
        raise ValueError("Protocol must select rahimi-table1/v2")
    if protocol.get("model_selector") != "luna":
        raise ValueError("The frozen rerating model must be luna")
    if protocol.get("requested_settings", {}).get("temperature") != 0.0:
        raise ValueError("The frozen temperature must be 0.0")
    if protocol.get("requested_settings", {}).get("max_tokens") != 4000:
        raise ValueError("The frozen output limit must be 4000 tokens")
    if protocol.get("prompt_path") != "src/evaluation/prompts/pf_rubric_v2.yaml":
        raise ValueError("Protocol prompt path does not identify the versioned v2 prompt")
    if protocol.get("expected_attempts_per_condition", 0) < 1:
        raise ValueError("Protocol requires a positive scheduled denominator")
    if protocol.get("calibration", {}).get("cases_per_condition", 0) < 1:
        raise ValueError("Protocol requires a balanced calibration sample")
    return protocol, raw


def _source_run_path(protocol: dict[str, Any], root: Path, source_run: Path | None) -> Path:
    candidate = source_run if source_run is not None else root / protocol["source_run"]
    return candidate.resolve()


def _verify_source_snapshot(source_run: Path, manifest: dict[str, Any]) -> None:
    snapshot_root = source_run / manifest.get("source_snapshot_dir", "source_snapshot")
    for relative, expected in manifest.get("source_hashes", {}).items():
        snapshot = (snapshot_root / relative).resolve()
        if not snapshot.is_relative_to(snapshot_root.resolve()) or not snapshot.is_file():
            raise ValueError(f"Frozen source snapshot missing or unsafe: {relative}")
        if _sha256(snapshot) != expected:
            raise ValueError(f"Frozen benchmark source snapshot differs: {relative}")


def _calibration_ids(cases: list[dict[str, Any]], protocol: dict[str, Any]) -> list[str]:
    ready_by_condition = {
        condition: [
            case["attempt_id"]
            for case in cases
            if case["condition"] == condition and case["eligible"]
        ]
        for condition in CONDITIONS
    }
    per_condition = int(protocol["calibration"]["cases_per_condition"])
    seed = int(protocol["calibration"]["selection_seed"])
    rng = random.Random(seed)
    selections: dict[str, list[str]] = {}
    for condition in CONDITIONS:
        eligible = ready_by_condition[condition]
        if len(eligible) < per_condition:
            raise ValueError(
                f"Not enough ready {condition} tasks for balanced calibration "
                f"({len(eligible)} available, {per_condition} required)"
            )
        selections[condition] = sorted(rng.sample(eligible, per_condition))
    return [
        selections[condition][round_number]
        for round_number in range(per_condition)
        for condition in CONDITIONS
    ]


def _load_source_cases(
    source_run: Path, protocol: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = source_run / "manifest.json"
    config_path = source_run / "config.json"
    summary_path = source_run / "summary.json"
    manifest = _read_json(manifest_path)
    config = _read_json(config_path)
    summary = _read_json(summary_path)
    if manifest.get("status") not in {
        "completed",
        "completed_with_failures",
        "completed_with_missing_ratings",
    }:
        raise ValueError(f"Source benchmark is not complete: {manifest.get('status')}")
    if manifest.get("source_integrity_unchanged") is not True:
        raise ValueError("Source benchmark did not pass its frozen-source integrity check")
    _verify_source_snapshot(source_run, manifest)
    if list(config.get("conditions", [])) != list(CONDITIONS):
        raise ValueError("Source benchmark condition order does not match the frozen protocol")
    expected = int(protocol["expected_attempts_per_condition"])
    if config.get("n_per_condition") != expected:
        raise ValueError("Source benchmark scheduled denominator differs from the protocol")
    if config.get("model_selector") != "luna":
        raise ValueError("Source benchmark does not use the frozen Luna model")
    learner_context = config.get("learner_context")
    target = config.get("case", {}).get("target_concept")
    if not isinstance(learner_context, dict) or not isinstance(target, str) or not target.strip():
        raise ValueError("Source benchmark is missing its fixed learner context or target")

    scheduled = manifest.get("attempts")
    order = manifest.get("judge_order")
    if not isinstance(scheduled, dict) or not isinstance(order, list):
        raise ValueError("Source benchmark is missing its frozen schedule or judge order")
    if len(scheduled) != len(CONDITIONS) * expected or len(order) != len(scheduled):
        raise ValueError("Source benchmark denominator or frozen judge order is incomplete")
    if len(set(order)) != len(order) or set(order) != set(scheduled):
        raise ValueError("Source benchmark judge order does not match its schedule")

    counts = Counter(item.get("condition") for item in scheduled.values())
    if counts != Counter({condition: expected for condition in CONDITIONS}):
        raise ValueError("Source benchmark has unexpected condition denominators")
    actual_statuses: dict[str, Counter] = {condition: Counter() for condition in CONDITIONS}
    cases = []
    for attempt_id in order:
        item = scheduled[attempt_id]
        condition = item.get("condition")
        attempt_path = (source_run / item["path"]).resolve()
        if not attempt_path.is_relative_to(source_run.resolve()):
            raise ValueError(f"Unsafe source attempt path: {attempt_id}")
        record_path = attempt_path / "attempt.json"
        source_bytes = record_path.read_bytes()
        record = json.loads(source_bytes)
        if record.get("attempt_id") != attempt_id or record.get("condition") != condition:
            raise ValueError(f"Source attempt identity mismatch: {attempt_id}")
        generation_status = record.get("status", "unknown")
        actual_statuses[condition][generation_status] += 1
        entry: dict[str, Any] = {
            "attempt_id": attempt_id,
            "condition": condition,
            "number": item.get("number"),
            "source_generation_status": generation_status,
            "source_attempt_path": str(record_path.relative_to(source_run)),
            "source_attempt_sha256": _sha256_bytes(source_bytes),
            "eligible": False,
            "student_task_sha256": None,
            "user_prompt": None,
            "user_prompt_sha256": None,
        }
        if generation_status == "ready":
            task_text = student_task_text(record.get("task"))
            user_prompt = judge_input(task_text, learner_context, target)
            entry.update(
                eligible=True,
                student_task_sha256=_sha256_bytes(task_text.encode("utf-8")),
                user_prompt=user_prompt,
                user_prompt_sha256=_sha256_bytes(user_prompt.encode("utf-8")),
            )
        cases.append(entry)

    for condition in CONDITIONS:
        source_summary = summary.get("conditions", {}).get(condition, {})
        counts_summary = source_summary.get("counts", {})
        if counts_summary.get("scheduled") != expected:
            raise ValueError(f"Saved source summary has a bad scheduled count for {condition}")
        ready = sum(case["eligible"] for case in cases if case["condition"] == condition)
        if counts_summary.get("ready") != ready:
            raise ValueError(f"Saved source summary has a bad ready count for {condition}")
        if ready != actual_statuses[condition].get("ready", 0):
            raise ValueError(f"Source task eligibility mismatch for {condition}")
    return cases, {
        "manifest_sha256": _sha256(manifest_path),
        "config_sha256": _sha256(config_path),
        "summary_sha256": _sha256(summary_path),
        "scheduled_counts": dict(counts),
        "generation_status_counts": {
            condition: dict(actual_statuses[condition]) for condition in CONDITIONS
        },
        "ready_counts": {
            condition: sum(case["eligible"] for case in cases if case["condition"] == condition)
            for condition in CONDITIONS
        },
    }


def _jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records
    ).encode("utf-8")


def prepare_run(
    output: Path,
    *,
    protocol_path: Path = PROTOCOL_PATH,
    source_run: Path | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    protocol_path = protocol_path.resolve()
    protocol, protocol_bytes = _load_protocol(protocol_path)
    source_run = _source_run_path(protocol, root.resolve(), source_run)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output exists; refusing to overwrite: {output}")
    prompt = load_prompt()
    if prompt["version"] != protocol["rubric_version"]:
        raise ValueError("Loaded prompt version differs from the frozen protocol")
    cases, source_hashes = _load_source_cases(source_run, protocol)
    calibration_ids = _calibration_ids(cases, protocol)
    for case in cases:
        case["calibration_selected"] = case["attempt_id"] in calibration_ids
    input_bytes = _jsonl_bytes(cases)
    source_files = _source_files()
    missing_sources = [name for name, path in source_files.items() if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError(f"Required rerating source files missing: {missing_sources}")
    code_hashes = {name: _sha256(path) for name, path in source_files.items()}

    output.mkdir(parents=True, exist_ok=False)
    (output / "protocol.json").write_bytes(protocol_bytes)
    (output / "prompt.yaml").write_bytes(PROMPT_PATH.read_bytes())
    (output / "inputs.jsonl").write_bytes(input_bytes)
    (output / "source_snapshot").mkdir()
    for relative, path in source_files.items():
        destination = output / "source_snapshot" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    frozen_source_run = output / "source_run_snapshot"
    frozen_source_run.mkdir()
    for name, path in (
        ("manifest.json", source_run / "manifest.json"),
        ("config.json", source_run / "config.json"),
        ("summary.json", source_run / "summary.json"),
    ):
        (frozen_source_run / name).write_bytes(path.read_bytes())

    input_hash = _sha256_bytes(input_bytes)
    manifest = {
        "schema_version": "rahimi-table1-rerating/v2",
        "status": "prepared",
        "created_at": _now(),
        "rubric_version": prompt["version"],
        "model_selector": protocol["model_selector"],
        "model_name": None,
        "requested_settings": protocol["requested_settings"],
        "effective_settings": None,
        "source_run": str(source_run),
        "source_run_id": source_run.name,
        "source_hashes": source_hashes,
        "source_code_hashes": code_hashes,
        "protocol_sha256": _sha256_bytes(protocol_bytes),
        "prompt_sha256": _sha256(PROMPT_PATH),
        "inputs_sha256": input_hash,
        "case_count": len(cases),
        "eligible_count": sum(case["eligible"] for case in cases),
        "scheduled_counts": source_hashes["scheduled_counts"],
        "ready_counts": source_hashes["ready_counts"],
        "calibration": {
            "status": "pending",
            "case_ids": calibration_ids,
            "cases_per_condition": protocol["calibration"]["cases_per_condition"],
            "selection_seed": protocol["calibration"]["selection_seed"],
        },
        "transport_retry_policy": {
            "max_retries": protocol["requested_settings"]["transport_retries"],
            "sdk_max_retries": protocol["requested_settings"]["sdk_retries"],
        },
    }
    for case in cases:
        initial_status = "pending" if case["eligible"] else "not_eligible"
        _write_json(
            output / "ratings" / f"{case['attempt_id']}.json",
            {
                "attempt_id": case["attempt_id"],
                "condition": case["condition"],
                "source_generation_status": case["source_generation_status"],
                "status": initial_status,
                "scores": None,
                "reason": (
                    None
                    if case["eligible"]
                    else f"Generation status was {case['source_generation_status']}; not rated."
                ),
            },
        )
    _write_json(output / "manifest.json", manifest)
    _write_json(
        output / "source_hashes.json",
        {
            "protocol_sha256": manifest["protocol_sha256"],
            "prompt_sha256": manifest["prompt_sha256"],
            "inputs_sha256": input_hash,
            "source_code_hashes": code_hashes,
            "source_benchmark": source_hashes,
        },
    )
    _write_json(
        output / "calibration_summary.json",
        {
            "status": "not_started",
            "case_ids": calibration_ids,
            "cases_per_condition": protocol["calibration"]["cases_per_condition"],
            "scores_deliberately_omitted": True,
        },
    )
    return manifest


def _load_frozen_run(output: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    output = output.resolve()
    manifest = _read_json(output / "manifest.json")
    protocol_path = output / "protocol.json"
    prompt_path = output / "prompt.yaml"
    inputs_path = output / "inputs.jsonl"
    if _sha256(protocol_path) != manifest.get("protocol_sha256"):
        raise ValueError("Frozen rerating protocol changed; refusing to continue")
    if _sha256(prompt_path) != manifest.get("prompt_sha256"):
        raise ValueError("Frozen v2 prompt changed; refusing to continue")
    if _sha256(inputs_path) != manifest.get("inputs_sha256"):
        raise ValueError("Frozen input selection changed; refusing to continue")
    for relative, expected in manifest.get("source_code_hashes", {}).items():
        current = _source_files().get(relative)
        snapshot = output / "source_snapshot" / relative
        if current is None or not current.is_file() or _sha256(current) != expected:
            raise ValueError(f"Rerating code changed since preparation: {relative}")
        if not snapshot.is_file() or _sha256(snapshot) != expected:
            raise ValueError(f"Saved rerating code snapshot differs: {relative}")
    for name, expected in (
        ("manifest.json", manifest["source_hashes"]["manifest_sha256"]),
        ("config.json", manifest["source_hashes"]["config_sha256"]),
        ("summary.json", manifest["source_hashes"]["summary_sha256"]),
    ):
        snapshot = output / "source_run_snapshot" / name
        if not snapshot.is_file() or _sha256(snapshot) != expected:
            raise ValueError(f"Frozen source-run snapshot differs: {name}")
    cases = [
        json.loads(line)
        for line in inputs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cases) != manifest.get("case_count"):
        raise ValueError("Frozen input case count changed")
    source_run = Path(manifest["source_run"])
    for case in cases:
        if case["eligible"]:
            prompt = case.get("user_prompt")
            if not isinstance(prompt, str) or _sha256_bytes(prompt.encode("utf-8")) != case.get(
                "user_prompt_sha256"
            ):
                raise ValueError(f"Frozen user input hash mismatch: {case['attempt_id']}")
        source_path = (source_run / case["source_attempt_path"]).resolve()
        if not source_path.is_relative_to(source_run.resolve()) or not source_path.is_file():
            raise ValueError(f"Source task file missing or unsafe: {case['attempt_id']}")
        if _sha256(source_path) != case["source_attempt_sha256"]:
            raise ValueError(f"Source task changed since preparation: {case['attempt_id']}")
    protocol, _ = _load_protocol(protocol_path)
    return manifest, protocol, cases


def _rating_path(output: Path, attempt_id: str) -> Path:
    return output / "ratings" / f"{attempt_id}.json"


def _load_rating(output: Path, attempt_id: str) -> dict[str, Any]:
    return _read_json(_rating_path(output, attempt_id))


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _retryable(exc: APIError) -> bool:
    if isinstance(exc, APIConnectionError):
        return True
    return isinstance(exc, APIStatusError) and (
        exc.status_code in {408, 409, 429} or exc.status_code >= 500
    )


def _rate_case(
    client: Any,
    model: str,
    system: str,
    user: str,
    *,
    settings: dict[str, Any],
    retries: int,
    trace_path: Path,
    attempt_id: str,
) -> dict[str, Any]:
    effective = _determine_effective_settings(model, settings)
    last_error: APIError | None = None
    total_elapsed = 0.0
    for retry in range(retries + 1):
        started_at = _now()
        _append_jsonl(
            trace_path,
            {
                "event": "model_call_started",
                "attempt_id": attempt_id,
                "retry": retry,
                "model": model,
                "requested_settings": settings,
                "effective_settings": effective,
                "started_at": started_at,
            },
        )
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                timeout=180,
                **effective,
            )
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            raw = response.choices[0].message.content or ""
            usage = _jsonable(getattr(response, "usage", None))
            response_model = getattr(response, "model", model)
            finish_reason = getattr(response.choices[0], "finish_reason", None)
            _append_jsonl(
                trace_path,
                {
                    "event": "model_call_finished",
                    "attempt_id": attempt_id,
                    "retry": retry,
                    "finished_at": _now(),
                    "elapsed_seconds": round(elapsed, 3),
                    "model": response_model,
                    "finish_reason": finish_reason,
                    "usage": usage,
                },
            )
            try:
                parsed = parse_rating(raw)
            except ValidationError as exc:
                return {
                    "status": "invalid_response",
                    "scores": None,
                    "rating": None,
                    "raw_response": raw,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    "response_model": response_model,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "request_attempts": retry + 1,
                    "elapsed_seconds": round(total_elapsed, 3),
                }
            return {
                **parsed,
                "raw_response": raw,
                "response_model": response_model,
                "finish_reason": finish_reason,
                "usage": usage,
                "request_attempts": retry + 1,
                "elapsed_seconds": round(total_elapsed, 3),
            }
        except APIError as exc:
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            last_error = exc
            _append_jsonl(
                trace_path,
                {
                    "event": "model_call_finished",
                    "attempt_id": attempt_id,
                    "retry": retry,
                    "finished_at": _now(),
                    "elapsed_seconds": round(elapsed, 3),
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            )
            if retry >= retries or not _retryable(exc):
                break
            time.sleep(min(2**retry, 8))
    assert last_error is not None
    return {
        "status": "api_error",
        "scores": None,
        "rating": None,
        "raw_response": None,
        "error": {"type": type(last_error).__name__, "message": str(last_error)},
        "request_attempts": min(retries + 1, retry + 1),
        "elapsed_seconds": round(total_elapsed, 3),
    }


def _write_case_result(output: Path, case: dict[str, Any], value: dict[str, Any]) -> None:
    _write_json(_rating_path(output, case["attempt_id"]), value)


def _setup_error_results(
    output: Path, cases_by_id: dict[str, dict[str, Any]], case_ids: list[str], exc: Exception
) -> None:
    error = {"type": type(exc).__name__, "message": str(exc)}
    for attempt_id in case_ids:
        case = cases_by_id[attempt_id]
        current = _load_rating(output, attempt_id)
        if current.get("status") not in {"pending", "started"}:
            continue
        _write_case_result(
            output,
            case,
            {
                **current,
                "status": "api_setup_error",
                "scores": None,
                "error": error,
                "finished_at": _now(),
                "request_attempts": 0,
            },
        )


def run_calibration(
    output: Path,
    *,
    client_loader=load_client,
) -> dict[str, Any]:
    manifest, protocol, cases = _load_frozen_run(output)
    calibration = manifest["calibration"]
    if calibration["status"] == "passed":
        return _read_json(output / "calibration_summary.json")
    if calibration["status"] == "failed":
        raise RuntimeError("Calibration previously failed; the frozen protocol requires stopping.")
    cases_by_id = {case["attempt_id"]: case for case in cases}
    case_ids = calibration["case_ids"]
    results = [_load_rating(output, identifier) for identifier in case_ids]
    if all(item.get("status") in VALID_RATING_STATUSES for item in results):
        calibration["status"] = "passed"
        calibration["finished_at"] = _now()
        _write_json(output / "manifest.json", manifest)
        summary = _calibration_summary(case_ids, cases_by_id, output)
        _write_json(output / "calibration_summary.json", summary)
        return summary
    if any(item.get("status") not in {"pending"} for item in results):
        calibration["status"] = "failed"
        calibration["finished_at"] = _now()
        summary = _calibration_summary(case_ids, cases_by_id, output)
        summary["status"] = "failed"
        _write_json(output / "manifest.json", manifest)
        _write_json(output / "calibration_summary.json", summary)
        return summary

    prompt = load_prompt()
    settings = dict(REQUESTED_SETTINGS)
    try:
        client, model = client_loader(protocol["model_selector"])
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)
    except Exception as exc:
        _setup_error_results(output, cases_by_id, case_ids, exc)
        calibration.update(status="failed", finished_at=_now())
        manifest.update(
            status="calibration_failed",
            model_setup_error={
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )
        summary = _calibration_summary(case_ids, cases_by_id, output)
        summary.update(
            status="failed",
            blocker="Model client setup failed; no v2 calibration calls were made.",
        )
        _write_json(output / "manifest.json", manifest)
        _write_json(output / "calibration_summary.json", summary)
        return summary

    manifest.update(
        status="calibrating",
        model_name=model,
        effective_settings={
            **_determine_effective_settings(model, settings),
            "response_format": {"type": "json_object"},
            "timeout_seconds": 180,
            "sdk_max_retries": 0,
        },
    )
    calibration.update(status="running", started_at=_now())
    _write_json(output / "manifest.json", manifest)
    for index, attempt_id in enumerate(case_ids):
        case = cases_by_id[attempt_id]
        result_path = _rating_path(output, attempt_id)
        _write_json(
            result_path,
            {
                "attempt_id": attempt_id,
                "condition": case["condition"],
                "source_generation_status": case["source_generation_status"],
                "rubric_version": manifest["rubric_version"],
                "status": "started",
                "started_at": _now(),
                "user_prompt_sha256": case["user_prompt_sha256"],
            },
        )
        try:
            rating = _rate_case(
                client,
                model,
                prompt["system"],
                case["user_prompt"],
                settings=settings,
                retries=int(protocol["requested_settings"]["transport_retries"]),
                trace_path=output / "call_trace.jsonl",
                attempt_id=attempt_id,
            )
        except Exception as exc:
            rating = {
                "status": "runner_error",
                "scores": None,
                "rating": None,
                "raw_response": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "request_attempts": 0,
            }
        _write_case_result(
            output,
            case,
            {
                "attempt_id": attempt_id,
                "condition": case["condition"],
                "source_generation_status": case["source_generation_status"],
                "rubric_version": manifest["rubric_version"],
                "model_name": model,
                "user_prompt_sha256": case["user_prompt_sha256"],
                "started_at": _now(),
                "finished_at": _now(),
                **rating,
            },
        )
        if rating["status"] not in VALID_RATING_STATUSES:
            for remaining_id in case_ids[index + 1 :]:
                remaining_case = cases_by_id[remaining_id]
                remaining_result = _load_rating(output, remaining_id)
                if remaining_result.get("status") == "pending":
                    _write_case_result(
                        output,
                        remaining_case,
                        {
                            **remaining_result,
                            "status": "not_attempted_calibration_blocked",
                            "scores": None,
                            "reason": (
                                f"Calibration stopped after {attempt_id} returned "
                                f"{rating['status']}."
                            ),
                            "finished_at": _now(),
                        },
                    )
            break
    case_results = [_load_rating(output, identifier) for identifier in case_ids]
    passed = all(item.get("status") in VALID_RATING_STATUSES for item in case_results)
    calibration.update(status="passed" if passed else "failed", finished_at=_now())
    manifest.update(status="calibration_passed" if passed else "calibration_failed")
    summary = _calibration_summary(case_ids, cases_by_id, output)
    summary["status"] = "passed" if passed else "failed"
    if not passed:
        summary["blocker"] = (
            "At least one balanced calibration response had an API, runner, interruption, "
            "or schema failure. The frozen prompt was not altered; the full run was stopped."
        )
    _write_json(output / "manifest.json", manifest)
    _write_json(output / "calibration_summary.json", summary)
    return summary


def _calibration_summary(
    case_ids: list[str], cases_by_id: dict[str, dict[str, Any]], output: Path
) -> dict[str, Any]:
    outcomes = []
    for attempt_id in case_ids:
        rating = _load_rating(output, attempt_id)
        outcomes.append(
            {
                "attempt_id": attempt_id,
                "condition": cases_by_id[attempt_id]["condition"],
                "status": rating["status"],
                "request_attempts": rating.get("request_attempts", 0),
            }
        )
    return {
        "schema_version": "rahimi-table1-rerating-calibration/v1",
        "status": (
            "passed"
            if all(item["status"] in VALID_RATING_STATUSES for item in outcomes)
            else "not_started"
        ),
        "purpose": "Call and schema reliability only; not prompt tuning or score validation.",
        "scores_deliberately_omitted": True,
        "balanced_case_count": len(outcomes),
        "outcomes": outcomes,
    }


def run_full(
    output: Path,
    *,
    client_loader=load_client,
    retry_interrupted: bool = False,
) -> dict[str, Any]:
    manifest, protocol, cases = _load_frozen_run(output)
    if manifest["calibration"]["status"] != "passed":
        raise RuntimeError("Full run blocked until the balanced v2 calibration passes.")
    cases_by_id = {case["attempt_id"]: case for case in cases}
    todo = []
    for case in cases:
        if not case["eligible"]:
            continue
        result = _load_rating(output, case["attempt_id"])
        status = result.get("status")
        if status == "pending":
            todo.append(case)
        elif status == "interrupted" and retry_interrupted:
            todo.append(case)
        elif status == "started":
            if retry_interrupted:
                todo.append(case)
            else:
                _write_case_result(
                    output,
                    case,
                    {
                        **result,
                        "status": "interrupted",
                        "scores": None,
                        "finished_at": _now(),
                        "reason": (
                            "Previous process stopped after recording the call as started; "
                            "not repeated without --retry-interrupted."
                        ),
                    },
                )
        elif status not in TERMINAL_STATUSES:
            raise ValueError(f"Unknown saved rating status for {case['attempt_id']}: {status}")
    if not todo:
        return _write_summary(output, manifest, cases)

    prompt = load_prompt()
    settings = dict(REQUESTED_SETTINGS)
    try:
        client, model = client_loader(protocol["model_selector"])
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)
    except Exception as exc:
        _setup_error_results(
            output,
            cases_by_id,
            [case["attempt_id"] for case in todo],
            exc,
        )
        manifest.update(
            status="completed_with_failures",
            model_setup_error={"type": type(exc).__name__, "message": str(exc)},
            updated_at=_now(),
        )
        _write_json(output / "manifest.json", manifest)
        return _write_summary(output, manifest, cases)

    manifest.update(
        status="running",
        model_name=model,
        effective_settings={
            **_determine_effective_settings(model, settings),
            "response_format": {"type": "json_object"},
            "timeout_seconds": 180,
            "sdk_max_retries": 0,
        },
        full_run_started_at=manifest.get("full_run_started_at", _now()),
    )
    _write_json(output / "manifest.json", manifest)
    for case in todo:
        attempt_id = case["attempt_id"]
        _write_json(
            _rating_path(output, attempt_id),
            {
                "attempt_id": attempt_id,
                "condition": case["condition"],
                "source_generation_status": case["source_generation_status"],
                "rubric_version": manifest["rubric_version"],
                "model_name": model,
                "user_prompt_sha256": case["user_prompt_sha256"],
                "status": "started",
                "started_at": _now(),
            },
        )
        try:
            rating = _rate_case(
                client,
                model,
                prompt["system"],
                case["user_prompt"],
                settings=settings,
                retries=int(protocol["requested_settings"]["transport_retries"]),
                trace_path=output / "call_trace.jsonl",
                attempt_id=attempt_id,
            )
        except Exception as exc:
            rating = {
                "status": "runner_error",
                "scores": None,
                "rating": None,
                "raw_response": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "request_attempts": 0,
            }
        _write_case_result(
            output,
            case,
            {
                "attempt_id": attempt_id,
                "condition": case["condition"],
                "source_generation_status": case["source_generation_status"],
                "rubric_version": manifest["rubric_version"],
                "model_name": model,
                "user_prompt_sha256": case["user_prompt_sha256"],
                "started_at": _now(),
                "finished_at": _now(),
                **rating,
            },
        )
        print(
            f"{attempt_id}: {rating['status']} (requests={rating.get('request_attempts', 0)})",
            flush=True,
        )
    final_statuses = [
        _load_rating(output, case["attempt_id"]).get("status") for case in cases if case["eligible"]
    ]
    manifest["status"] = (
        "completed"
        if all(status in VALID_RATING_STATUSES for status in final_statuses)
        else "completed_with_failures"
    )
    manifest["finished_at"] = _now()
    _write_json(output / "manifest.json", manifest)
    return _write_summary(output, manifest, cases)


def _scores_summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "sd": statistics.stdev(values) if len(values) > 1 else None,
    }


def _write_summary(
    output: Path, manifest: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, Any]:
    conditions = {}
    for condition in CONDITIONS:
        group = [case for case in cases if case["condition"] == condition]
        eligible = [case for case in group if case["eligible"]]
        ratings = [_load_rating(output, case["attempt_id"]) for case in group]
        generation_status_counts = dict(Counter(case["source_generation_status"] for case in group))
        rating_status_counts = dict(Counter(rating["status"] for rating in ratings))
        score_values: dict[str, list[float]] = {
            dimension: [] for dimension in (*DIMENSIONS, "TOTAL")
        }
        usage_totals: Counter = Counter()
        responses_with_usage = 0
        request_attempts = 0
        elapsed_seconds = 0.0
        for rating in ratings:
            request_attempts += int(rating.get("request_attempts", 0) or 0)
            elapsed_seconds += float(rating.get("elapsed_seconds", 0.0) or 0.0)
            usage = rating.get("usage")
            if isinstance(usage, dict):
                responses_with_usage += 1
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    value = usage.get(key)
                    if isinstance(value, (int, float)):
                        usage_totals[key] += value
            scores = rating.get("scores")
            if isinstance(scores, dict):
                for key in score_values:
                    value = scores.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        score_values[key].append(float(value))
        conditions[condition] = {
            "denominators": {
                "scheduled": len(group),
                "ready": len(eligible),
                "not_ready": len(group) - len(eligible),
                "ratings_attempted": sum(
                    rating["status"] not in {"pending", "not_eligible"} for rating in ratings
                ),
                "complete_five_dimension_scores": rating_status_counts.get("scored", 0),
            },
            "generation_status_counts": generation_status_counts,
            "rating_status_counts": rating_status_counts,
            "scores": {key: _scores_summary(values) for key, values in score_values.items()},
            "model_calls": {
                "request_attempts_including_transport_retries": request_attempts,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "responses_with_usage": responses_with_usage,
                "usage_tokens_when_returned": dict(usage_totals) if responses_with_usage else None,
            },
        }
    summary = {
        "schema_version": "rahimi-table1-rerating/v2",
        "generated_at": _now(),
        "status": manifest.get("status"),
        "rubric_version": manifest["rubric_version"],
        "source_run_id": manifest["source_run_id"],
        "model_selector": manifest["model_selector"],
        "model_name": manifest.get("model_name"),
        "requested_settings": manifest["requested_settings"],
        "effective_settings": manifest.get("effective_settings"),
        "calibration_status": manifest["calibration"]["status"],
        "overall_denominators": {
            "scheduled": len(cases),
            "ready": sum(case["eligible"] for case in cases),
            "not_ready": sum(not case["eligible"] for case in cases),
            "complete_five_dimension_scores": sum(
                _load_rating(output, case["attempt_id"]).get("status") == "scored" for case in cases
            ),
        },
        "conditions": conditions,
        "interpretation_limitations": [
            (
                "This is an exploratory automated rerating under adapted task-level "
                "guidance, not the paper's exact rubric wording or human-rating procedure."
            ),
            (
                "Ratings are conditional on a task having been marked ready; blocked and "
                "failed generations remain in the scheduled denominators and receive no scores."
            ),
            (
                "A single model (Luna) generated the benchmark tasks and rated them; no "
                "independent human agreement or repeatability was measured."
            ),
            (
                "Scores assess task affordances, not observed student approaches, productive "
                "failure, engagement, or learning."
            ),
            "Mathematical concerns are unverified model claims, not independent validity checks.",
            (
                "Method packages differ in their generation and checking costs; this rerating "
                "does not isolate one component or constitute a confirmatory comparison."
            ),
        ],
    }
    _write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--prepare",
        action="store_true",
        help="Freeze source inputs and hashes; make no API calls.",
    )
    mode.add_argument(
        "--calibrate",
        action="store_true",
        help="Run the frozen balanced reliability calibration.",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help="Rate all remaining ready cases after calibration.",
    )
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--retry-interrupted",
        action="store_true",
        help="Explicitly repeat calls left in started state after interruption.",
    )
    args = parser.parse_args()
    if args.prepare:
        manifest = prepare_run(
            args.output,
            protocol_path=args.protocol,
            source_run=args.source_run,
        )
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "output": str(args.output.resolve()),
                    "scheduled": manifest["case_count"],
                    "ready": manifest["eligible_count"],
                    "calibration_case_ids": manifest["calibration"]["case_ids"],
                    "inputs_sha256": manifest["inputs_sha256"],
                    "prompt_sha256": manifest["prompt_sha256"],
                },
                indent=2,
            )
        )
        return
    if args.calibrate:
        summary = run_calibration(args.output)
        print(json.dumps(summary, indent=2))
        if summary["status"] != "passed":
            raise SystemExit(2)
        return
    summary = run_full(args.output, retry_interrupted=args.retry_interrupted)
    print(json.dumps(summary, indent=2))
    if (
        summary["overall_denominators"]["complete_five_dimension_scores"]
        < summary["overall_denominators"]["ready"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
