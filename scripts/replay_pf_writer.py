#!/usr/bin/env python3
"""Replay only the Productive Failure task writer on frozen saved inputs.

The utility deliberately does not rerun proposals, selection, planning, review,
or filling.  ``--prepare-only`` and ``--dry-run`` render the production writer
request without making a model call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_situation_skeletons as runner  # noqa: E402
from scripts.learning_commons_context import REFERENCE_DATA_LABEL  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.run_pf_diagnostic import (  # noqa: E402
    DiagnosticTracer,
    _determine_effective_settings,
    _traced_chat,
    compute_source_hashes,
    trace_summary,
)

SCHEMA_VERSION = "pf-writer-replay/v1"
WRITER_MODULE = "run_situation_skeletons"
WRITER_STAGE = "D3.writer"
WRITER_SETTINGS = {"temperature": 0.7, "max_tokens": runner.PROPOSE_MAX_TOKENS}
CONTEXT_BLOCKS = {
    "student_context": "STUDENT CONTEXT",
    "target_concept": "TARGET CONCEPT",
    "task_design": "SELECTED TASK DESIGN",
    "approaches": "FULL STRUCTURED APPROACH RECORDS",
    "intended_student_output": "INTENDED STUDENT OUTPUT",
    "design_context": "DESIGN CONTEXT",
}
FIXED_INTENDED_KEYS = ("question", "answer_rule")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_hashes(case_dir: Path) -> dict[str, str]:
    required = ("input.json", "d1.json", "result.json", "model_calls.jsonl")
    missing = [name for name in required if not (case_dir / name).is_file()]
    if missing:
        raise ValueError(f"Saved case {case_dir} is missing artifacts: {missing}")
    return {name: _sha256(case_dir / name) for name in required}


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _stage(result: dict[str, Any]) -> dict[str, Any]:
    stages = result.get("stages")
    if isinstance(stages, dict) and isinstance(stages.get("D2_D3"), dict):
        return stages["D2_D3"]
    if isinstance(result.get("d2"), dict):
        return result["d2"]
    raise ValueError("Saved result is missing D2_D3 stage")


def _read_trace(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Trace line {line_number} is not an object: {path}")
        records.append(value)
    return records


def _writer_trace(records: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    stage_records = [record for record in records if record.get("stage") == WRITER_STAGE]
    start_ids = [
        record.get("call_id")
        for record in stage_records
        if record.get("event") == "model_call_started"
    ]
    finish_ids = [
        record.get("call_id")
        for record in stage_records
        if record.get("event") == "model_call_finished"
    ]
    if (
        any(call_id is None for call_id in start_ids + finish_ids)
        or len(start_ids) != len(set(start_ids))
        or len(finish_ids) != len(set(finish_ids))
    ):
        raise ValueError("Saved writer trace has duplicate or missing call ids")
    starts = {
        record.get("call_id"): record
        for record in records
        if record.get("event") == "model_call_started" and record.get("stage") == WRITER_STAGE
    }
    finishes = {
        record.get("call_id"): record
        for record in records
        if record.get("event") == "model_call_finished" and record.get("stage") == WRITER_STAGE
    }
    if not starts or not finishes:
        raise ValueError(f"Saved writer trace is missing paired {WRITER_STAGE} records")
    if None in starts or None in finishes or set(starts) != set(finishes):
        raise ValueError("Saved writer trace has unpaired or missing call ids")
    ordered = sorted(finishes.values(), key=lambda record: record.get("call_number", 0))
    finished = ordered[-1]
    started = starts[finished["call_id"]]
    if started.get("case_id") not in (None, case_id) or finished.get("case_id") not in (
        None,
        case_id,
    ):
        raise ValueError(f"Saved writer trace is for a different case than {case_id!r}")
    source_model = started.get("model")
    if not isinstance(source_model, str) or not source_model.strip():
        raise ValueError("Saved writer trace has no source model")
    for key in (
        "model",
        "requested_settings",
        "effective_settings",
        "system_prompt",
        "user_prompt",
    ):
        if started.get(key) != finished.get(key):
            raise ValueError(f"Saved writer trace start/finish mismatch for {key}")
    if "error" in finished:
        raise ValueError("Saved final writer trace contains an error")
    return {
        "started": started,
        "finished": finished,
        "count": len(ordered),
    }


def _json_after_label(prompt: str, label: str) -> Any:
    """Decode the first JSON value after a rendered writer section heading."""
    position = prompt.find(label)
    if position < 0:
        raise ValueError(f"Writer prompt is missing section {label!r}")
    decoder = json.JSONDecoder()
    start = prompt.find(":", position + len(label))
    if start < 0:
        raise ValueError(f"Writer prompt section {label!r} has no JSON value")
    start += 1
    while start < len(prompt) and prompt[start].isspace():
        start += 1
    if start == len(prompt):
        raise ValueError(f"Writer prompt section {label!r} has no JSON value")
    try:
        value, _ = decoder.raw_decode(prompt[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Writer prompt section {label!r} has malformed JSON") from exc
    return value


def _original_context(writer_record: dict[str, Any]) -> dict[str, Any]:
    prompt = writer_record["started"].get("user_prompt")
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("Saved writer trace has no original user prompt")
    context: dict[str, Any] = {}
    for key, label in CONTEXT_BLOCKS.items():
        context[key] = _json_after_label(prompt, label)
    if REFERENCE_DATA_LABEL in prompt:
        context["mathematical_references"] = _json_after_label(prompt, REFERENCE_DATA_LABEL)
    return context


def _assert_context_unchanged(current: dict[str, Any], original: dict[str, Any]) -> None:
    def equivalent(left: object, right: object) -> bool:
        return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(
            right, ensure_ascii=False, sort_keys=True
        )

    for key in CONTEXT_BLOCKS:
        if key == "intended_student_output":
            for fixed_key in FIXED_INTENDED_KEYS:
                if not equivalent(current[key].get(fixed_key), original[key].get(fixed_key)):
                    raise ValueError(
                        f"Writer context changed fixed intended_student_output.{fixed_key}"
                    )
        elif not equivalent(current.get(key), original.get(key)):
            raise ValueError(f"Writer context changed fixed section {key}")
    if not equivalent(
        current.get("mathematical_references"), original.get("mathematical_references")
    ):
        raise ValueError("Writer context changed fixed section mathematical_references")


def _text_stats(task: object) -> dict[str, Any]:
    if not isinstance(task, dict):
        return {"fields": {}, "total_characters": 0, "total_words": 0}
    fields = {
        key: value
        for key in ("title", "body", "question")
        if isinstance(value := task.get(key), str)
    }
    return {
        "fields": {
            key: {"characters": len(value), "words": len(value.split())}
            for key, value in fields.items()
        },
        "total_characters": sum(len(value) for value in fields.values()),
        "total_words": sum(len(value.split()) for value in fields.values()),
    }


def _length_comparison(previous_task: object, task: object) -> dict[str, Any]:
    previous_stats = _text_stats(previous_task)
    task_stats = _text_stats(task)
    return {
        "previous_task": {
            "characters": previous_stats["total_characters"],
            "words": previous_stats["total_words"],
        },
        "task": {
            "characters": task_stats["total_characters"],
            "words": task_stats["total_words"],
        },
        "delta": {
            "characters": task_stats["total_characters"] - previous_stats["total_characters"],
            "words": task_stats["total_words"] - previous_stats["total_words"],
        },
    }


def _source_bundle(case_dir: Path) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    hashes_before = _artifact_hashes(case_dir)
    case = _load_object(case_dir / "input.json", "Saved input")
    case_id = case.get("id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError(f"Saved input has no string id: {case_dir / 'input.json'}")
    result = _load_object(case_dir / "result.json", "Saved result")
    result_case_id = result.get("case_id") or result.get("case")
    if result_case_id not in (None, case_id):
        raise ValueError(f"Saved result case_id {result_case_id!r} disagrees with {case_id!r}")
    prior_context = result.get("prior_context")
    if not isinstance(prior_context, dict):
        raise ValueError("Saved result is missing frozen prior_context")
    stage = _stage(result)
    task = stage.get("task")
    if not isinstance(task, dict) or task.get("status") != "ready":
        raise ValueError(f"Saved source task is not ready for {case_id!r}")
    review = stage.get("plan_review")
    if not runner._review_passes(review):
        raise ValueError(f"Saved plan review is not accepted for {case_id!r}")
    fill = stage.get("fill")
    if not isinstance(fill, dict) or fill.get("accepted") is not True:
        raise ValueError(f"Saved fill is not accepted for {case_id!r}")
    fill_payload = fill.get("payload")
    if not isinstance(fill_payload, dict) or not isinstance(fill_payload.get("values"), dict):
        raise ValueError(f"Saved accepted fill has no values for {case_id!r}")

    winner = runner._winner_from_result(case_dir / "result.json", expected_case_id=case_id)
    raw_plan = stage.get("math_plan")
    if not isinstance(raw_plan, dict):
        raise ValueError(f"Saved result has no math_plan for {case_id!r}")
    plan = runner._math_plan_from_payload(raw_plan, winner)
    plan_errors = runner.validate_plan_expressions(plan)
    if plan_errors:
        raise ValueError(f"Saved math_plan is invalid for {case_id!r}: {plan_errors}")
    fill_check = runner.check_fill(plan, fill_payload["values"])
    if not fill_check.accepted:
        raise ValueError(f"Saved fill failed deterministic recheck for {case_id!r}")

    trace = _writer_trace(_read_trace(case_dir / "model_calls.jsonl"), case_id)
    if trace["started"].get("requested_settings") != WRITER_SETTINGS:
        raise ValueError(f"Saved writer settings differ from current settings for {case_id!r}")
    original_context = _original_context(trace)
    context = runner._writer_context(case, prior_context, winner, plan, fill_payload, review)
    _assert_context_unchanged(context, original_context)
    return {
        "dir": case_dir,
        "case": case,
        "case_id": case_id,
        "result": result,
        "stage": stage,
        "task": task,
        "prior_context": prior_context,
        "winner": winner,
        "plan": plan,
        "fill": fill_payload,
        "fill_record": fill,
        "review": review,
        "context": context,
        "original_context": original_context,
        "writer_trace": trace,
        "hashes_before": hashes_before,
    }


def _render_writer_request(bundle: dict[str, Any], prompts: dict[str, str]) -> dict[str, Any]:
    values = {
        key: json.dumps(value, ensure_ascii=False, indent=2)
        for key, value in bundle["context"].items()
    }
    return {
        "system_prompt": runner._render(prompts["WRITE_TASK_SYSTEM"], values),
        "user_prompt": runner._render(prompts["WRITE_TASK_USER"], values),
        "requested_settings": dict(WRITER_SETTINGS),
    }


def _source_provenance(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_dir": str(bundle["dir"]),
        "source_case_id": bundle["case_id"],
        "source_model": bundle["writer_trace"]["started"].get("model"),
        "source_artifact_sha256_before": bundle["hashes_before"],
    }


def replay_case(
    bundle: dict[str, Any],
    output_dir: Path,
    *,
    model_selector: str,
    model_name: str | None,
    prompts: dict[str, str],
    prepare_only: bool = False,
    client: Any = None,
) -> dict[str, Any]:
    case_id = bundle["case_id"]
    out_case = output_dir / case_id
    out_case.mkdir(parents=True, exist_ok=False)
    shutil.copy2(bundle["dir"] / "input.json", out_case / "input.json")
    shutil.copy2(bundle["dir"] / "d1.json", out_case / "d1.json")
    shutil.copy2(bundle["dir"] / "result.json", out_case / "source_result.json")
    shutil.copy2(bundle["dir"] / "model_calls.jsonl", out_case / "source_model_calls.jsonl")

    request = _render_writer_request(bundle, prompts)
    effective_model = model_name or bundle["writer_trace"]["started"].get("model") or model_selector
    request["effective_settings"] = _determine_effective_settings(
        effective_model, request["requested_settings"]
    )
    provenance = _source_provenance(bundle)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "model_selector": model_selector,
        "model_name": effective_model,
        "status": "planned" if prepare_only else "running",
        "source_provenance": provenance,
        "source_writer_request": bundle["writer_trace"],
        "source_writer_call_count": bundle["writer_trace"]["count"],
        "original_writer_context": bundle["original_context"],
        "new_writer_context": bundle["context"],
        "planned_writer_request": request,
        "started_at": _now(),
    }
    _write_json(out_case / "result.json", record)

    new_task: dict[str, Any] | None = None
    new_raw = ""
    if not prepare_only:
        trace_file = out_case / "model_calls.jsonl"
        tracer = DiagnosticTracer(trace_file, case_id, default_model=effective_model)
        original_chat = runner.chat_json
        runner.chat_json = _traced_chat(tracer, WRITER_MODULE, d1_prompt=False)
        try:
            new_task, new_raw = runner._write_task(
                client,
                effective_model,
                prompts,
                bundle["case"],
                bundle["winner"],
                bundle["plan"],
                bundle["fill"],
                bundle["prior_context"],
                bundle["review"],
            )
        finally:
            runner.chat_json = original_chat
        counts = trace_summary(trace_file)
    else:
        counts = {"started": 0, "finished": 0, "errors": 0, "call_ids": []}

    status = (
        "planned"
        if prepare_only
        else (
            "ready"
            if isinstance(new_task, dict) and new_task.get("status") == "ready"
            else "blocked"
        )
    )
    new_request = request
    trace_records = (
        _read_trace(out_case / "model_calls.jsonl")
        if (out_case / "model_calls.jsonl").exists()
        else []
    )
    if trace_records:
        for item in trace_records:
            if item.get("event") == "model_call_started":
                new_request = {
                    "system_prompt": item.get("system_prompt"),
                    "user_prompt": item.get("user_prompt"),
                    "requested_settings": item.get("requested_settings"),
                    "effective_settings": item.get("effective_settings"),
                    "model": item.get("model"),
                }
                break
    record.update(
        status=status,
        previous_task=bundle["task"],
        task=new_task,
        task_raw_text=new_raw,
        length_comparison=_length_comparison(bundle["task"], new_task),
        before_after={
            "before_task": bundle["task"],
            "after_task": new_task,
            "before_text_stats": _text_stats(bundle["task"]),
            "after_text_stats": _text_stats(new_task),
        },
        new_writer_request=new_request,
        new_trace_counts=counts,
        source_provenance={
            **provenance,
            "source_artifact_sha256_after": _artifact_hashes(bundle["dir"]),
        },
        finished_at=_now(),
    )
    _write_json(out_case / "before_after.json", record["before_after"])
    _write_json(out_case / "result.json", record)
    if record["source_provenance"]["source_artifact_sha256_after"] != bundle["hashes_before"]:
        raise ValueError(f"Saved source artifacts changed during replay of {case_id!r}")
    return record


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="luna")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    ns = parse_args(args)
    if ns.prepare_only and ns.dry_run:
        raise ValueError("--prepare-only and --dry-run are aliases; pass only one")
    if ns.output.exists():
        raise FileExistsError(f"Output directory already exists: {ns.output}")

    bundles = [_source_bundle(path) for path in ns.sources]
    case_ids = [bundle["case_id"] for bundle in bundles]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate case IDs: {duplicates}")
    source_models = {bundle["writer_trace"]["started"].get("model") for bundle in bundles}
    if len(source_models) != 1:
        raise ValueError(f"Source writer traces use different models: {sorted(source_models)}")

    prepare_only = ns.prepare_only or ns.dry_run
    prompts = runner._prompts()
    client = None
    model_name = None
    if not prepare_only:
        client, model_name = load_client(ns.model)
        if model_name not in source_models:
            raise ValueError(
                f"Replay model {model_name!r} differs from saved writer model {source_models}"
            )
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)

    runtime_hashes = compute_source_hashes(ROOT)
    runtime_hashes["scripts/replay_pf_writer.py"] = _sha256(Path(__file__))
    ns.output.mkdir(parents=True, exist_ok=False)
    results = [
        replay_case(
            bundle,
            ns.output,
            model_selector=ns.model,
            model_name=model_name,
            prompts=prompts,
            prepare_only=prepare_only,
            client=client,
        )
        for bundle in bundles
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "planned" if prepare_only else "completed",
        "model_selector": ns.model,
        "source_models": sorted(source_models),
        "source_count": len(bundles),
        "runtime_source_sha256": runtime_hashes,
        "counts": {
            "cases": len(results),
            "source_writer_calls": sum(item["source_writer_call_count"] for item in results),
            "new_model_calls": sum(item["new_trace_counts"]["finished"] for item in results),
        },
        "cases": [
            {
                "case_id": item["case_id"],
                "status": item["status"],
                "new_trace_counts": item["new_trace_counts"],
            }
            for item in results
        ],
        "started_at": results[0]["started_at"] if results else _now(),
        "finished_at": _now(),
    }
    _write_json(ns.output / "manifest.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
