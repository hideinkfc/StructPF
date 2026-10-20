#!/usr/bin/env python3
"""Bounded, resumable D2a comparison using saved case inputs and D1 context."""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import importlib.metadata
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import design_brief_stage as brief_stage  # noqa: E402
from scripts import design_data_stage as data_stage  # noqa: E402
from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts import run_situation_skeletons as runner  # noqa: E402
from scripts.prior_methods import common  # noqa: E402

load_client = common.load_client
SEED = 20261011
ARMS = ("baseline", "intervention")
PHASES = ("calibration", "development")
UNFINISHED = {"running", "interrupted"}


class BudgetStoppedError(RuntimeError):
    """No further API request may be dispatched within the frozen budget."""


def _write_json(path: Path, value: object) -> None:
    pending = path.with_name(path.name + ".pending")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


def _append(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if path.exists() else []


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def source_hashes(config_path: Path, baseline_prompts: Path) -> dict[str, str]:
    """Freeze the transitive local Python imports and all stage prompt files."""
    sources = {
        Path(__file__).resolve(), config_path.resolve(), baseline_prompts.resolve(),
        brief_stage.PROMPTS_PATH.resolve(), data_stage.PROMPTS_PATH.resolve(),
        runner.PROMPTS_PATH.resolve(),
    }
    pending = [
        Path(module.__file__).resolve()
        for module in (brief_stage, data_stage, runner, diagnostic, common)
    ] + [Path(__file__).resolve()]
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        sources.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module, *(f"{node.module}.{item.name}" for item in node.names)]
            for name in names:
                if not name.startswith(("scripts.", "src.")):
                    continue
                candidate = ROOT.joinpath(*name.split(".")).with_suffix(".py")
                if candidate.is_file():
                    pending.append(candidate.resolve())
                parts = name.split(".")
                for length in range(1, len(parts) + 1):
                    package = ROOT.joinpath(*parts[:length]) / "__init__.py"
                    if package.is_file():
                        pending.append(package.resolve())
    # Imported D1 helpers are frozen for provenance but are never invoked.
    sources.add(ROOT / "src/generation/prompts/prior_recommendations.yaml")
    return {str(path): _sha(path) for path in sorted(sources)}


def _runtime() -> dict:
    return {
        "python": sys.version,
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("openai", "httpx", "python-dotenv", "PyYAML", "sympy")
        },
    }


def _integer(value: object, name: str, *, minimum: int, maximum: int | None = None) -> int:
    if (
        isinstance(value, bool) or not isinstance(value, int) or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def _validate(config: dict) -> dict:
    if config.get("schema_version") != "pf-d2a-comparison/v1":
        raise ValueError("Expected config schema_version pf-d2a-comparison/v1")
    if config.get("model_selector") not in common.MODEL_ENVS:
        raise ValueError("Unknown model_selector")
    if config.get("proposal_k") != 2 or isinstance(config["proposal_k"], bool):
        raise ValueError("Both comparison arms require proposal_k=2")
    if config.get("seed", SEED) != SEED:
        raise ValueError(f"This comparison requires seed={SEED}")
    _integer(config["repeats"], "repeats", minimum=1)
    ids = [case["id"] for case in config["cases"]]
    if (
        not ids or len(ids) != len(set(ids))
        or any(not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", case_id)
               for case_id in ids)
    ):
        raise ValueError("Case IDs must be nonempty, unique safe directory names")
    calibration = config["calibration_cases"]
    if (
        not isinstance(calibration, list) or not calibration
        or len(calibration) != len(set(calibration)) or set(calibration) - set(ids)
    ):
        raise ValueError("calibration_cases must be unique members of cases")
    protocol = config["protocol"]
    if protocol.get("sdk_max_retries") != 0:
        raise ValueError("sdk_max_retries must be zero")
    return {
        "max_calls_per_attempt": _integer(
            protocol["max_calls_per_attempt"], "max_calls_per_attempt", minimum=0, maximum=9
        ),
        "max_calls_total": _integer(protocol["max_calls_total"], "max_calls_total", minimum=0),
        "max_completion_tokens_per_call": _integer(
            protocol["max_completion_tokens_per_call"], "max_completion_tokens_per_call",
            minimum=1, maximum=6000,
        ),
        "timeout_seconds": _integer(
            protocol.get("timeout_seconds", 120), "timeout_seconds", minimum=1, maximum=120
        ),
        "sdk_max_retries": 0,
    }


def make_schedule(config: dict) -> list[dict]:
    rng = random.Random(SEED)
    schedule = []
    for phase in PHASES:
        ids = (
            list(config["calibration_cases"]) if phase == "calibration"
            else [case["id"] for case in config["cases"]]
        )
        repeats = 1 if phase == "calibration" else config["repeats"]
        for repeat in range(1, repeats + 1):
            rng.shuffle(ids)
            for case_id in ids:
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    schedule.append({
                        "attempt_id": f"{phase}--{case_id}--{arm}--{repeat}",
                        "phase": phase, "case_id": case_id, "arm": arm, "repeat": repeat,
                    })
    return schedule


def prepare(config_path: Path, output: Path) -> dict:
    """Validate and snapshot inputs without loading an API client or generating D1."""
    config_path = _path(config_path)
    output = _path(output)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    limits = _validate(config)
    baseline = _path(config["baseline_prompts"])
    hashes = source_hashes(config_path, baseline)
    inputs = {}
    models = set()
    for item in config["cases"]:
        case_id = item["id"]
        source = _path(config["source_directory"]) / case_id / "result.json"
        saved = json.loads(source.read_text(encoding="utf-8"))
        case = runner._stored_case_input(source, case_id)
        context = runner._stored_prior_context(source, case_id)
        if case is None or context is None or not context:
            raise ValueError(f"{case_id} requires saved case_input and D1 prior_context")
        if not isinstance(saved.get("model"), str) or not saved["model"].strip():
            raise ValueError(f"{case_id} requires a saved model")
        models.add(saved["model"])
        inputs[case_id] = {
            "source": str(source), "sha256": _sha(source),
            "case_input": case, "prior_context": context,
        }
    if len(models) != 1:
        raise ValueError("Saved inputs must use one frozen model")
    frozen = {
        "config": config, "inputs": inputs, "model": models.pop(),
        "source_hashes": hashes, "runtime": _runtime(), "limits": limits,
        "seed": SEED, "schedule": make_schedule(config),
        "baseline_prompts_sha256": _sha(baseline),
    }
    path = output / "manifest.json"
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if any(manifest.get(key) != value for key, value in frozen.items()):
            raise ValueError("Frozen inputs, model or sources changed; use a new output directory")
        for original, snapshot in manifest["snapshots"].items():
            if _sha(output / snapshot) != hashes[original]:
                raise ValueError(f"Frozen source snapshot changed: {snapshot}")
        if (output / manifest["baseline_prompts_snapshot"]).read_bytes() != baseline.read_bytes():
            raise ValueError("Frozen baseline prompt snapshot changed")
        return manifest
    if output.exists():
        permitted = {baseline.name} if baseline.parent == output else set()
        if {item.name for item in output.iterdir()} - permitted:
            raise ValueError("Refusing to replace an unmanifested output directory")
    output.mkdir(parents=True, exist_ok=True)
    snapshot_dir = output / "sources"
    snapshot_dir.mkdir()
    snapshots = {}
    for index, (original, digest) in enumerate(hashes.items()):
        snapshot = snapshot_dir / f"{index:03d}-{digest[:12]}-{Path(original).name}"
        snapshot.write_bytes(Path(original).read_bytes())
        snapshots[original] = str(snapshot.relative_to(output))
    baseline_snapshot = output / "baseline_prompts.yaml"
    baseline_snapshot.write_bytes(baseline.read_bytes())
    manifest = {
        "schema_version": "pf-d2a-comparison-run/v1", **frozen,
        "created_at": diagnostic._now(), "snapshots": snapshots,
        "baseline_prompts_snapshot": baseline_snapshot.name, "attempts": {},
        "evidence_kind": "generated_tasks_not_student_or_human_rating_evidence",
    }
    _write_json(path, manifest)
    return manifest


def usage_summary(rows: list[dict], attempt_id: str | None = None) -> dict:
    chosen = [row for row in rows if attempt_id is None or row["attempt_id"] == attempt_id]
    started = [row for row in chosen if row["event"] == "api_request_started"]
    finished = [row for row in chosen if row["event"] == "api_request_finished"]
    tokens = {}
    for name in ("input_tokens", "output_tokens", "reasoning_tokens"):
        available = [
            row["usage"][name] for row in finished if row.get("usage", {}).get(name) is not None
        ]
        tokens[name] = sum(available) if available else None
        tokens[f"{name}_available_calls"] = len(available)
    return {
        "attempted_calls": len(started), "completed_calls": len(finished),
        "error_calls": sum(row.get("error") is not None for row in finished),
        "unfinished_calls": len(started) - len(finished), **tokens,
    }


def _usage(response) -> dict:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "reasoning_tokens": getattr(details, "reasoning_tokens", None),
    }


class RequestBudget:
    """Sequential API-dispatch accounting, including failed and interrupted requests."""

    def __init__(self, output: Path, limits: dict):
        self.output = output
        self.limits = limits
        self.ledger = output / "ledger.jsonl"
        self.rows = _rows(self.ledger)
        starts = [row["call_id"] for row in self.rows if row["event"] == "api_request_started"]
        finishes = [row["call_id"] for row in self.rows if row["event"] == "api_request_finished"]
        if (
            len(starts) != len(set(starts)) or len(finishes) != len(set(finishes))
            or set(finishes) - set(starts)
        ):
            raise ValueError("Invalid request ledger")
        if set(starts) - set(finishes):
            raise ValueError("Interrupted API requests exist; refusing automatic replacement")

    def _event(self, trace: Path, row: dict) -> None:
        _append(self.ledger, row)
        self.rows.append(row)
        _append(trace, row)

    def traced_chat(self, client, attempt: dict, trace: Path, module: str):
        def traced(_client, model, system, user, temperature, max_tokens):
            limits = self.limits
            effective_tokens = min(max_tokens, limits["max_completion_tokens_per_call"])
            metadata = {
                **attempt, "module": module,
                "stage": diagnostic._stage_from_prompt(system, d1_prompt=False),
                "model": model, "system_prompt": system, "user_prompt": user,
                "requested_settings": {"temperature": temperature, "max_tokens": max_tokens},
                "runtime_overrides": {
                    "max_tokens": effective_tokens, "timeout_seconds": limits["timeout_seconds"],
                    "sdk_max_retries": 0,
                },
            }

            def create(**kwargs):
                total = usage_summary(self.rows)["attempted_calls"]
                count = usage_summary(self.rows, attempt["attempt_id"])["attempted_calls"]
                if total >= limits["max_calls_total"] or count >= limits["max_calls_per_attempt"]:
                    reason = (
                        "max_calls_total" if total >= limits["max_calls_total"]
                        else "max_calls_per_attempt"
                    )
                    _append(trace, {
                        **metadata, "event": "budget_stopped", "reason": reason,
                        "at": diagnostic._now(),
                    })
                    raise BudgetStoppedError(reason)
                kwargs["timeout"] = limits["timeout_seconds"]
                for key in ("max_tokens", "max_completion_tokens"):
                    if key in kwargs:
                        kwargs[key] = min(kwargs[key], limits["max_completion_tokens_per_call"])
                call_id = f"request-{total + 1:06d}"
                effective = {
                    key: kwargs[key] for key in
                    (
                        "temperature", "max_tokens", "max_completion_tokens",
                        "timeout", "response_format",
                    )
                    if key in kwargs
                }
                self._event(trace, {
                    **metadata, "event": "api_request_started", "call_id": call_id,
                    "started_at": diagnostic._now(), "attempted_count_total": total + 1,
                    "attempted_count_attempt": count + 1, "effective_settings": effective,
                })
                response = None
                started = time.monotonic()
                try:
                    dispatch_client = client
                    if getattr(client, "max_retries", 0) != 0:
                        dispatch_client = client.with_options(max_retries=0)
                    response = dispatch_client.chat.completions.create(**kwargs)
                    return response
                finally:
                    error = sys.exc_info()[1]
                    self._event(trace, {
                        **attempt, "module": module, "event": "api_request_finished",
                        "call_id": call_id, "finished_at": diagnostic._now(),
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                        "usage": _usage(response),
                        "error": f"{type(error).__name__}: {error}" if error is not None else None,
                    })

            proxy = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=create))
            )
            payload, raw = common.chat_json(
                proxy, model, system, user, temperature, effective_tokens
            )
            _append(trace, {
                **metadata, "event": "stage_response", "payload": payload,
                "raw_text": raw, "at": diagnostic._now(),
            })
            return payload, raw

        return traced


def run_attempt(
    attempt: dict, output: Path, manifest: dict, *, client, model: str, budget: RequestBudget
) -> dict:
    if model != manifest["model"]:
        raise ValueError("Resolved API model differs from the frozen model")
    directory = output / "attempts" / attempt["attempt_id"]
    directory.mkdir(parents=True, exist_ok=False)
    destination = directory / "result.json"
    trace = directory / "model_calls.jsonl"
    frozen = manifest["inputs"][attempt["case_id"]]
    case = json.loads(json.dumps(frozen["case_input"]))
    context = json.loads(json.dumps(frozen["prior_context"]))
    record = {
        "schema_version": "pf-d2a-comparison-attempt/v1", **attempt, "model": model,
        "status": "running", "started_at": diagnostic._now(), "error": None,
        "source_result": frozen["source"], "source_sha256": frozen["sha256"],
        "case_input": case, "prior_context": context, "d1_reused": True,
        "search": None, "winner": None, "design_data": None, "task": None,
        "writer_request": None, "traces": [],
        "brief_schema_version": (
            "design-brief/v1" if attempt["arm"] == "baseline" else "design-brief/v2"
        ),
    }
    _write_json(destination, record)
    try:
        with patch.object(
            runner, "chat_json", budget.traced_chat(client, attempt, trace, "D2a")
        ):
            search = brief_stage.run_design_brief_search(
                client, model, case, context, k=2, translate=False,
                prompts_path=(
                    _path(manifest["config"]["baseline_prompts"])
                    if attempt["arm"] == "baseline" else None
                ),
                brief_schema_version=record["brief_schema_version"],
            )
        record["search"] = {
            key: value for key, value in search.items() if key not in ("judged", "winners")
        }
        winners = search["winners"]
        if not winners:
            record.update(
                status="brief_not_selected",
                error=search.get("judge_error") or "No brief was selected",
            )
        else:
            winner = winners[0]
            record["winner"] = winner.to_dict()
            _write_json(destination, record)
            with patch.object(
                runner, "chat_json", budget.traced_chat(client, attempt, trace, "D2b")
            ):
                data = data_stage.run_design_data(client, model, case, winner, context)
            record["design_data"] = data
            _write_json(destination, record)
            if data["payload"] is None:
                record.update(status=f"data_{data['status']}", error=data.get("error"))
            else:
                record["writer_request"] = data_stage._writer_request(case, winner, data, context)
                _write_json(destination, record)
                with patch.object(
                    runner, "chat_json", budget.traced_chat(client, attempt, trace, "D3")
                ):
                    task, raw = data_stage.write_design_data_task(
                        client, model, case, winner, data, context
                    )
                record.update(task=task, task_raw_text=raw, status=task["status"])
    except BudgetStoppedError as error:
        record.update(status="budget_stopped", error=str(error))
    finally:
        error = sys.exc_info()[1]
        if error is not None:
            record.update(
                status="error" if isinstance(error, Exception) else "interrupted",
                error=f"{type(error).__name__}: {error}",
            )
        record.update(
            finished_at=diagnostic._now(), traces=_rows(trace),
            usage=usage_summary(budget.rows, attempt["attempt_id"]),
            source_artifact_unchanged=(
                Path(frozen["source"]).is_file()
                and _sha(Path(frozen["source"])) == frozen["sha256"]
            ),
            source_integrity_verified=all(
                Path(path).is_file() and _sha(Path(path)) == digest
                for path, digest in manifest["source_hashes"].items()
            ),
        )
        if error is None and (
            not record["source_artifact_unchanged"] or not record["source_integrity_verified"]
        ):
            record.update(status="integrity_error", error="Frozen sources changed during attempt")
        _write_json(destination, record)
    return record


def _saved_attempts(output: Path, manifest: dict) -> dict:
    saved = {}
    for attempt in manifest["schedule"]:
        directory = output / "attempts" / attempt["attempt_id"]
        if not directory.exists():
            continue
        path = directory / "result.json"
        if not path.exists():
            raise ValueError(f"Interrupted attempt has no result: {attempt['attempt_id']}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") in UNFINISHED or not record.get("finished_at"):
            raise ValueError(
                f"Refusing to replace running/interrupted attempt: {attempt['attempt_id']}"
            )
        saved[attempt["attempt_id"]] = record
    return saved


def run(config_path: Path, output: Path, phase: str, *, limit: int | None = None) -> dict:
    if phase not in PHASES:
        raise ValueError("phase must be calibration or development")
    if limit is not None:
        _integer(limit, "limit", minimum=0)
    config_path, output = _path(config_path), _path(output)
    manifest = prepare(config_path, output)
    lock = output / ".run-lock"
    if lock.exists():
        raise ValueError("A running/interrupted invocation exists; refusing replacement")
    lock.mkdir()
    budget = None
    try:
        saved = _saved_attempts(output, manifest)
        budget = RequestBudget(output, manifest["limits"])
        selected = [
            attempt for attempt in manifest["schedule"]
            if attempt["phase"] == phase and attempt["attempt_id"] not in saved
        ]
        if limit is not None:
            selected = selected[:limit]
        if selected:
            client, model = None, manifest["model"]
            if (
                manifest["limits"]["max_calls_per_attempt"] > 0
                and usage_summary(budget.rows)["attempted_calls"]
                < manifest["limits"]["max_calls_total"]
            ):
                client, model = load_client(manifest["config"]["model_selector"])
                if model != manifest["model"]:
                    raise ValueError("Resolved API model differs from the frozen model")
                client = client.with_options(
                    max_retries=0, timeout=manifest["limits"]["timeout_seconds"]
                )
            for attempt in selected:
                # Also verify between attempts, not just at invocation start.
                prepare(config_path, output)
                record = run_attempt(
                    attempt, output, manifest, client=client, model=model, budget=budget
                )
                saved[attempt["attempt_id"]] = record
                if record["status"] == "integrity_error":
                    raise ValueError(record["error"])
                print(
                    f"{attempt['attempt_id']}: {record['status']} "
                    f"({record['usage']['attempted_calls']} requests)", flush=True,
                )
    finally:
        saved = {
            attempt["attempt_id"]: json.loads(path.read_text(encoding="utf-8"))
            for attempt in manifest["schedule"]
            if (path := output / "attempts" / attempt["attempt_id"] / "result.json").exists()
        }
        manifest["attempts"] = {
            key: {"status": record["status"], "usage": record.get("usage")}
            for key, record in saved.items()
        }
        rows = budget.rows if budget is not None else _rows(output / "ledger.jsonl")
        manifest["usage"] = usage_summary(rows)
        manifest["phase_usage"] = {
            label: usage_summary([row for row in rows if row["phase"] == label])
            for label in PHASES
        }
        manifest["updated_at"] = diagnostic._now()
        _write_json(output / "manifest.json", manifest)
        lock.rmdir()
    return manifest


def render(output: Path, phase: str) -> None:
    """Task-only anonymized reading material, not a human blind-review result."""
    if phase not in PHASES:
        raise ValueError("phase must be calibration or development")
    output = _path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    attempts = [item for item in manifest["schedule"] if item["phase"] == phase]
    random.Random(SEED + 1).shuffle(attempts)
    review, mapping, sections = [], [], []
    for item in attempts:
        opaque = "task-" + hashlib.sha256(
            f"{SEED}:reading:{item['attempt_id']}".encode()
        ).hexdigest()[:16]
        path = output / "attempts" / item["attempt_id"] / "result.json"
        record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        task = record.get("task")
        text = {
            field: task[field] for field in ("title", "body", "question")
            if isinstance(task.get(field), str)
        } if isinstance(task, dict) else None
        text = text or None
        target = manifest["inputs"][item["case_id"]]["case_input"]["target_concept"]
        review.append({"task_id": opaque, "target_concept": target, "task": text})
        mapping.append({
            "task_id": opaque, **item, "model": manifest["model"],
            "status": record.get("status", "not_run"), "source_result": str(path),
        })
        content = (
            "".join(f"<p>{html.escape(text.get(field, ''))}</p>" for field in
                    ("title", "body", "question"))
            if text is not None else "<p>No task text available.</p>"
        )
        sections.append(
            f"<section><h2>{opaque}</h2><p>Target: {html.escape(target)}</p>{content}</section>"
        )
    gallery = output / "gallery" / phase
    gallery.mkdir(parents=True, exist_ok=True)
    _write_json(gallery / "review.json", {"tasks": review})
    _write_json(output / f"{phase}_task_mapping.json", {"tasks": mapping})
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Anonymized task reading</title>"
        "<style>body{max-width:900px;margin:2em auto;font:16px/1.5 system-ui}"
        "section{border-top:1px solid #ccc;padding:1em}p{white-space:pre-wrap}</style>"
        "<h1>Anonymized task reading</h1><p>Task text and supplied target only; "
        "absent tasks are retained. "
        "No human ratings or student-outcome evidence.</p>"
        + "".join(sections) + "</html>"
    )
    (gallery / "tasks.html").write_text(page, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--render-only", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    if args.render_only:
        prepare(args.config, args.output_dir)
        render(args.output_dir, args.phase)
    elif args.prepare_only:
        prepare(args.config, args.output_dir)
    else:
        run(args.config, args.output_dir, args.phase, limit=args.limit)
        render(args.output_dir, args.phase)


if __name__ == "__main__":
    main()
