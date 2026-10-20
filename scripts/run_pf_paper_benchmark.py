"""Run the resumable paper-setting PF benchmark.

This runner deliberately keeps scientific attempts separate from transport retries:
an interrupted or blocked attempt is recorded and is never silently replaced.
``--prepare``/``--dry-run`` only freeze inputs and create the attempt ledger.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from openai import APIConnectionError, APIError, APIStatusError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prior_methods.common import load_client  # noqa: E402, I001
from scripts.run_pf_diagnostic import (  # noqa: E402
    _determine_effective_settings,
    _frozen_grounding_records,
    run_case_worker,
)
from scripts.run_pf_judge import SETTINGS as JUDGE_SETTINGS  # noqa: E402
import scripts.run_situation_skeletons as d2_settings  # noqa: E402
from src.evaluation.pf_rubric import (  # noqa: E402
    DIMENSIONS,
    judge_input,
    load_prompt as load_judge_prompt,
    parse_rating,
    student_task_text,
)

CONFIG_PATH = ROOT / "experiments" / "configs" / "pf_paper_benchmark.json"
PROMPT_PATH = ROOT / "src" / "generation" / "prompts" / "pf_paper_benchmark.yaml"
DEFAULT_OUTPUT = ROOT / "experiments" / "results" / "pf_paper_benchmark"
CONDITIONS = ("V1", "V2", "V3", "PIPELINE")
RUN_SCHEMA = "pf-paper-benchmark/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _json_payload(raw: str) -> object | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None


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


def _render(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _misconceptions(config: dict[str, Any]) -> list[str]:
    raw = config.get("misconceptions", [])
    if isinstance(raw, dict):
        raw = raw.get("items", raw.get("values", raw.get("list", [])))
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError("misconceptions must be a list of strings")
    return [item.strip() for item in raw if item.strip()]


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("benchmark config must be a JSON object")
    if not isinstance(value.get("schema_version"), str):
        raise ValueError("benchmark config requires schema_version")
    if list(value.get("conditions", [])) != list(CONDITIONS):
        raise ValueError(f"conditions must be exactly {list(CONDITIONS)}")
    if not isinstance(value.get("n_per_condition"), int) or value["n_per_condition"] < 1:
        raise ValueError("n_per_condition must be a positive integer")
    if value.get("model_selector") != "luna":
        raise ValueError("paper benchmark model_selector must be 'luna'")
    for key in ("workers", "shuffle_seed", "generation_max_tokens", "inference_max_tokens"):
        if not isinstance(value.get(key), int) or value[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if "transport_retries" in value and (
        not isinstance(value["transport_retries"], int) or value["transport_retries"] < 0
    ):
        raise ValueError("transport_retries must be a non-negative integer")
    if "max_concurrent_api_requests" in value and (
        not isinstance(value["max_concurrent_api_requests"], int)
        or value["max_concurrent_api_requests"] < 1
    ):
        raise ValueError("max_concurrent_api_requests must be a positive integer")
    if not isinstance(value.get("case"), dict):
        raise ValueError("benchmark config requires a case object")
    if not isinstance(value.get("learner_context"), dict):
        raise ValueError("benchmark config requires a fixed learner_context object")
    pipeline = value.get("pipeline", {})
    if not isinstance(pipeline, dict):
        raise ValueError("pipeline must be an object")
    if not isinstance(pipeline.get("design_brief", True), bool):
        raise ValueError("pipeline.design_brief must be a boolean")
    for key in ("k", "max_resources", "evidence_k"):
        if key in pipeline and (not isinstance(pipeline[key], int) or pipeline[key] < 1):
            raise ValueError(f"pipeline.{key} must be a positive integer")
    _misconceptions(value)
    if "grounding_evidence" not in value:
        raise ValueError(
            "benchmark config requires grounding_evidence to freeze PIPELINE D1 inputs"
        )
    _frozen_grounding_records(value["grounding_evidence"])
    return value


def load_prompt(path: Path = PROMPT_PATH) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("paper benchmark prompt must be a YAML object")
    for key in ("version", "system", "infer_system", "infer_user"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"paper benchmark prompt requires non-empty {key}")
    return value


def _tracked_files(config_path: Path, prompt_path: Path) -> list[Path]:
    relative = (
        "scripts/run_pf_paper_benchmark.py",
        "scripts/run_pf_diagnostic.py",
        "scripts/run_pf_judge.py",
        "scripts/prior_methods/common.py",
        "scripts/design_brief_stage.py",
        "scripts/design_data_stage.py",
        "scripts/run_situation_skeletons.py",
        "scripts/run_prior_recommendations.py",
        "src/evaluation/pf_rubric.py",
        "src/evaluation/prompts/pf_rubric.yaml",
        "src/generation/fill_check.py",
        "src/generation/prompts/prior_recommendations.yaml",
        "src/generation/prompts/design_briefs.yaml",
        "src/generation/prompts/design_data.yaml",
        "src/generation/prompts/situation_skeletons.yaml",
        "src/generation/design_briefs.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/prior_recommendations.py",
        "src/generation/situation_skeletons.py",
    )
    paths = [config_path, prompt_path]
    paths.extend(ROOT / item for item in relative)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required frozen sources missing: {missing}")
    return list(dict.fromkeys(path.resolve() for path in paths))


def source_hashes(
    config_path: Path = CONFIG_PATH, prompt_path: Path = PROMPT_PATH
) -> dict[str, str]:
    output: dict[str, str] = {}
    for path in _tracked_files(config_path, prompt_path):
        try:
            key = str(path.relative_to(ROOT))
        except ValueError:
            key = str(path)
        output[key] = _sha256(path)
    return output


def _attempt_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = []
    for condition in CONDITIONS:
        for number in range(1, config["n_per_condition"] + 1):
            attempt_id = f"{condition}-{number:03d}"
            specs.append(
                {
                    "attempt_id": attempt_id,
                    "condition": condition,
                    "number": number,
                }
            )
    return specs


def _attempt_dir(root: Path, attempt_id: str) -> Path:
    condition, number = attempt_id.rsplit("-", 1)
    return root / "attempts" / condition / number


def _frozen_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Record resolved budgets separately from scientific attempt outcomes."""
    pipeline = config.get("pipeline", {})
    settings = {
        "transport_retries": int(config.get("transport_retries", 2)),
        "sdk_max_retries": 0,
        "max_concurrent_api_requests": int(
            config.get("max_concurrent_api_requests", config["workers"])
        ),
        "direct": {
            "generation_temperature": 0.0,
            "generation_max_tokens": config["generation_max_tokens"],
            "inference_temperature": 0.0,
            "inference_max_tokens": config["inference_max_tokens"],
        },
        "pipeline": {
            "design_brief": pipeline.get("design_brief", True),
            "proposal_k": int(pipeline.get("k", 6)),
            "max_resources": int(pipeline.get("max_resources", 4)),
            "evidence_k": int(pipeline.get("evidence_k", 6)),
            "d1_condition": str(pipeline.get("d1_condition", "grounded")),
            "proposal_retry_max": d2_settings.PROPOSAL_RETRY_MAX,
            "plan_retry_max": d2_settings.PLAN_RETRY_MAX,
            "fill_max_tries": d2_settings.FILL_MAX_TRIES,
            "proposal_temperature": d2_settings.PROPOSE_TEMPERATURE,
            "proposal_max_tokens": d2_settings.PROPOSE_MAX_TOKENS,
            "judge_temperature": d2_settings.JUDGE_TEMPERATURE,
            "judge_max_tokens": d2_settings.JUDGE_MAX_TOKENS,
            "fill_temperature": 0.7,
            "fill_max_tokens": d2_settings.PROPOSE_MAX_TOKENS,
            "writer_temperature": 0.7,
            "writer_max_tokens": d2_settings.PROPOSE_MAX_TOKENS,
        },
        "final_judge": dict(JUDGE_SETTINGS),
    }
    if pipeline.get("design_brief", True):
        from scripts.design_brief_stage import MAX_TOKENS
        from scripts.design_data_stage import MAX_CALLS
        from scripts.design_data_stage import MAX_TOKENS as DATA_MAX_TOKENS

        settings["pipeline"] = {
            "design_brief": True,
            "proposal_k": int(pipeline.get("k", 6)),
            "max_resources": int(pipeline.get("max_resources", 4)),
            "evidence_k": int(pipeline.get("evidence_k", 6)),
            "d1_condition": str(pipeline.get("d1_condition", "grounded")),
            "design_brief_settings": {
                "max_tokens": MAX_TOKENS,
                "proposal_temperature": d2_settings.PROPOSE_TEMPERATURE,
                "selection_temperature": 0.0,
                "proposal_retry_max": d2_settings.PROPOSAL_RETRY_MAX,
            },
            "design_data_settings": {
                "max_calls": MAX_CALLS,
                "max_tokens": DATA_MAX_TOKENS,
                "temperature": 0.0,
            },
            "writer_temperature": 0.7,
            "writer_max_tokens": d2_settings.PROPOSE_MAX_TOKENS,
        }
    return settings


def _manifest_seed(config: dict[str, Any], config_path: Path, prompt_path: Path) -> dict[str, Any]:
    specs = _attempt_specs(config)
    order = [item["attempt_id"] for item in specs]
    random.Random(config["shuffle_seed"]).shuffle(order)
    return {
        "schema_version": RUN_SCHEMA,
        "status": "prepared",
        "created_at": _now(),
        "config_path": str(config_path.resolve()),
        "prompt_path": str(prompt_path.resolve()),
        "config_sha256": _sha256(config_path),
        "prompt_sha256": _sha256(prompt_path),
        "source_hashes": source_hashes(config_path, prompt_path),
        "model_selector": config["model_selector"],
        "model_name": None,
        "frozen_settings": _frozen_settings(config),
        "usage_metadata": (
            "Direct and final-judge calls capture response usage when supplied. "
            "The reused diagnostic pipeline exposes no response usage metadata."
        ),
        "conditions": list(CONDITIONS),
        "n_per_condition": config["n_per_condition"],
        "workers": config["workers"],
        "shuffle_seed": config["shuffle_seed"],
        "judge_order": order,
        "attempts": {
            item["attempt_id"]: {
                **item,
                "status": "pending",
                "path": str(_attempt_dir(Path("."), item["attempt_id"])),
            }
            for item in specs
        },
    }


def _execution_scope(
    only_condition: str | None,
    limit_per_condition: int | None,
) -> dict[str, Any] | None:
    if limit_per_condition is not None and limit_per_condition < 1:
        raise ValueError("limit_per_condition must be positive")
    if only_condition is None:
        return None
    if only_condition not in CONDITIONS:
        raise ValueError(f"only_condition must be one of {list(CONDITIONS)}")
    return {
        "kind": "single_condition_calibration",
        "condition": only_condition,
        "limit_per_condition": limit_per_condition,
        "benchmark_status": "not_a_benchmark",
    }


def _verify_resume(
    output: Path,
    config_path: Path,
    prompt_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config = load_config(config_path)
    prompt = load_prompt(prompt_path)
    expected = {
        "config_sha256": _sha256(config_path),
        "prompt_sha256": _sha256(prompt_path),
        "source_hashes": source_hashes(config_path, prompt_path),
        "frozen_settings": _frozen_settings(config),
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Frozen {key} changed; do not resume this run")
    if manifest.get("schema_version") != RUN_SCHEMA:
        raise ValueError("Unsupported benchmark manifest schema")
    if manifest.get("n_per_condition") != config["n_per_condition"]:
        raise ValueError("Frozen n_per_condition does not match current config")
    for attempt_id, item in manifest.get("attempts", {}).items():
        stored = _read_attempt(output / item["path"])
        if stored.get("status") == "started":
            stored.update(status="interrupted", finished_at=_now())
            _write_json(output / item["path"] / "attempt.json", stored)
        if stored.get("status") not in {None, "missing", "pending"}:
            item.update(
                {
                    key: stored[key]
                    for key in ("status", "started_at", "finished_at", "error", "model_name")
                    if key in stored
                }
            )
        item["attempt_id"] = attempt_id
    if manifest.get("model_name") is None:
        manifest["model_name"] = next(
            (
                item.get("model_name")
                for item in manifest["attempts"].values()
                if item.get("model_name")
            ),
            None,
        )
    return manifest, config, prompt


def prepare_run(
    output: Path,
    *,
    config_path: Path = CONFIG_PATH,
    prompt_path: Path = PROMPT_PATH,
    resume: bool = False,
    only_condition: str | None = None,
    limit_per_condition: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    execution_scope = _execution_scope(only_condition, limit_per_condition)
    config_path = config_path.resolve()
    prompt_path = prompt_path.resolve()
    config = load_config(config_path)
    prompt = load_prompt(prompt_path)
    output = output.resolve()
    if output.exists():
        if not resume:
            raise FileExistsError(f"Output exists; pass --resume: {output}")
        manifest, config, prompt = _verify_resume(output, config_path, prompt_path)
        if manifest.get("execution_scope") != execution_scope:
            raise ValueError("Frozen execution_scope changed; do not resume this run")
        return manifest, config, prompt

    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_bytes(config_path.read_bytes())
    (output / "prompt.yaml").write_bytes(prompt_path.read_bytes())
    hashes = source_hashes(config_path, prompt_path)
    _write_json(output / "source_hashes.json", hashes)
    snapshot_root = output / "source_snapshot"
    for source in _tracked_files(config_path, prompt_path):
        try:
            relative = source.relative_to(ROOT)
        except ValueError:
            relative = Path("external") / source.name
        destination = snapshot_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    manifest = _manifest_seed(config, config_path, prompt_path)
    if execution_scope is not None:
        manifest["execution_scope"] = execution_scope
        manifest["benchmark_status"] = "not_a_benchmark"
        manifest["comparison_status"] = "not_computed"
        manifest["judging_status"] = "not_started"
    manifest["attempts_root"] = "attempts"
    manifest["source_snapshot_dir"] = "source_snapshot"
    for item in manifest["attempts"].values():
        relative = Path(item["path"])
        attempt_path = output / relative
        attempt_path.mkdir(parents=True, exist_ok=False)
        item["path"] = str(attempt_path.relative_to(output))
        _write_json(
            attempt_path / "attempt.json",
            {
                "schema_version": RUN_SCHEMA,
                "attempt_id": item["attempt_id"],
                "condition": item["condition"],
                "number": item["number"],
                "status": "pending",
                "created_at": _now(),
            },
        )
    _write_json(output / "manifest.json", manifest)
    return manifest, config, prompt


def _trace_append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()


def _call_json(
    client: Any,
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int,
    retries: int,
    trace_path: Path,
    stage: str,
    semaphore=None,
    temperature: float = 0.0,
    timeout_seconds: float = 180,
) -> tuple[object | None, str, dict[str, Any] | None, str | None]:
    """Call JSON mode with bounded transport retries and per-call trace flushing."""
    requested = {"temperature": temperature, "max_tokens": max_tokens}
    effective = _determine_effective_settings(model, requested)
    last_error: str | None = None
    for retry in range(retries + 1):
        call_id = f"{stage}:{retry + 1}"
        started = _now()
        _trace_append(
            trace_path,
            {
                "event": "model_call_started",
                "call_id": call_id,
                "stage": stage,
                "model": model,
                "requested_settings": requested,
                "effective_settings": effective,
                "system_prompt": system,
                "user_prompt": user,
                "started_at": started,
            },
        )
        t0 = time.perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "timeout": timeout_seconds,
                **effective,
            }
            if semaphore is not None:
                semaphore.acquire()
            try:
                response = client.chat.completions.create(**kwargs)
            finally:
                if semaphore is not None:
                    semaphore.release()
            raw = response.choices[0].message.content or ""
            usage = _jsonable(getattr(response, "usage", None))
            metadata = {
                "model": getattr(response, "model", model),
                "finish_reason": getattr(response.choices[0], "finish_reason", None),
                "usage": usage,
            }
            _trace_append(
                trace_path,
                {
                    "event": "model_call_finished",
                    "call_id": call_id,
                    "stage": stage,
                    "finished_at": _now(),
                    "elapsed_seconds": round(time.perf_counter() - t0, 3),
                    "raw_text": raw,
                    **metadata,
                },
            )
            return _json_payload(raw), raw, metadata, None
        except APIError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            _trace_append(
                trace_path,
                {
                    "event": "model_call_finished",
                    "call_id": call_id,
                    "stage": stage,
                    "finished_at": _now(),
                    "elapsed_seconds": round(time.perf_counter() - t0, 3),
                    "error": last_error,
                },
            )
            retryable = isinstance(exc, APIConnectionError) or (
                isinstance(exc, APIStatusError)
                and (exc.status_code in {408, 409, 429} or exc.status_code >= 500)
            )
            if retry >= retries or not retryable:
                break
            time.sleep(min(2**retry, 8))
    return None, "", None, last_error


def _direct_values(
    config: dict[str, Any],
    misconceptions: list[str],
) -> dict[str, str]:
    case = config["case"]
    learner = config["learner_context"]
    case_text = json.dumps(case, ensure_ascii=False, indent=2)
    learner_text = json.dumps(learner, ensure_ascii=False, indent=2)
    misc_text = json.dumps(misconceptions, ensure_ascii=False, indent=2)
    return {
        "case": case_text,
        "case_json": case_text,
        "learner_context": learner_text,
        "learner_context_json": learner_text,
        "misconceptions": misc_text,
        "misconceptions_json": misc_text,
    }


def _direct_user(
    prompt: dict[str, Any],
    values: dict[str, str],
    *,
    include_misconceptions: bool,
) -> str:
    template = next(
        (
            prompt.get(key)
            for key in ("user", "direct_user", "generate_user", "user_template")
            if isinstance(prompt.get(key), str) and prompt[key].strip()
        ),
        None,
    )
    if template is None:
        rendered = (
            "Generate one paper-setting Productive Failure task as JSON. "
            "Use this case and learner context:\n"
            f"{values['case_json']}\nLearner context:\n{values['learner_context_json']}"
        )
        if include_misconceptions:
            rendered += f"\nMisconceptions (optional):\n{values['misconceptions_json']}"
    else:
        rendered = _render(template, values)
    return _ensure_context(
        rendered,
        values,
        include_misconceptions=include_misconceptions,
    )


def _ensure_context(text: str, values: dict[str, str], *, include_misconceptions: bool) -> str:
    """Do not rely on a prompt author remembering context placeholders."""
    suffix = []
    if values["case_json"] not in text:
        suffix.append(f"CASE JSON:\n{values['case_json']}")
    if values["learner_context_json"] not in text:
        suffix.append(f"FIXED LEARNER CONTEXT JSON:\n{values['learner_context_json']}")
    if include_misconceptions and values["misconceptions_json"] not in text:
        suffix.append(f"OPTIONAL MISCONCEPTIONS JSON:\n{values['misconceptions_json']}")
    return text if not suffix else text + "\n\n" + "\n\n".join(suffix)


def _inferred_misconceptions(payload: object) -> list[str] | None:
    values = payload
    if isinstance(payload, dict):
        values = payload.get("misconceptions", payload.get("items"))
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        return None
    cleaned = [item.strip() for item in values]
    if len(cleaned) != 6 or any(not item for item in cleaned):
        return None
    if len(set(cleaned)) != 6:
        return None
    return cleaned


def _validate_task(payload: object) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        return "invalid_response", "writer response must be a JSON object"
    status = payload.get("status")
    if status not in {"ready", "blocked"}:
        return "invalid_response", "writer status must be ready or blocked"
    unexpected = sorted(set(payload) - {"status", "title", "body", "question", "blocking_issues"})
    if unexpected:
        return "invalid_response", f"unexpected task fields: {unexpected}"
    issues = payload.get("blocking_issues", [])
    if not isinstance(issues, list) or any(
        not isinstance(item, str) or not item.strip() for item in issues
    ):
        return "invalid_response", "blocking_issues must be a list of non-empty strings"
    if status == "blocked":
        return ("blocked", "; ".join(issues))
    if issues:
        return "invalid_response", "ready task cannot contain blocking_issues"
    for field in ("title", "body", "question"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            return "invalid_response", f"ready task requires non-empty {field}"
    return "ready", None


def _run_direct_attempt(
    config: dict[str, Any],
    prompt: dict[str, Any],
    condition: str,
    trace_path: Path,
    semaphore=None,
) -> dict[str, Any]:
    client, model = load_client("luna")
    if hasattr(client, "with_options"):
        client = client.with_options(max_retries=0)
    fixed_misc = _misconceptions(config)
    inferred: list[str] | None = None
    if condition == "V2":
        misc = fixed_misc
    elif condition == "V3":
        values = _direct_values(config, [])
        infer_user = _ensure_context(
            _render(prompt["infer_user"], values),
            values,
            include_misconceptions=False,
        )
        infer_payload, infer_raw, _, error = _call_json(
            client,
            model,
            _render(prompt["infer_system"], values),
            infer_user,
            max_tokens=config["inference_max_tokens"],
            retries=int(config.get("transport_retries", 2)),
            trace_path=trace_path,
            stage="V3.infer",
            semaphore=semaphore,
        )
        if error:
            return {
                "status": "api_error",
                "error": error,
                "raw_inference": infer_raw,
                "model_name": model,
            }
        inferred = _inferred_misconceptions(infer_payload)
        if inferred is None:
            return {
                "status": "invalid_response",
                "error": (
                    "V3 inference must return exactly six distinct non-empty misconception strings"
                ),
                "raw_inference": infer_raw,
                "model_name": model,
            }
        misc = inferred
    else:
        misc = []
    values = _direct_values(config, misc)
    user = _direct_user(
        prompt,
        values,
        include_misconceptions=condition != "V1",
    )
    payload, raw, metadata, error = _call_json(
        client,
        model,
        _render(prompt["system"], values),
        user,
        max_tokens=config["generation_max_tokens"],
        retries=int(config.get("transport_retries", 2)),
        trace_path=trace_path,
        stage=f"{condition}.generate",
        semaphore=semaphore,
    )
    if error:
        return {
            "status": "api_error",
            "error": error,
            "raw_response": raw,
            "inferred_misconceptions": inferred,
            "model_name": model,
        }
    status, schema_error = _validate_task(payload)
    result: dict[str, Any] = {
        "status": status,
        "task": payload,
        "raw_response": raw,
        "response_metadata": metadata,
        "inferred_misconceptions": inferred,
        "model_name": model,
    }
    if schema_error:
        result["error"] = schema_error
    return result


def _run_attempt_worker(
    spec: dict[str, Any],
    attempt_path_str: str,
    config: dict[str, Any],
    prompt: dict[str, Any],
    api_semaphore=None,
) -> dict[str, Any]:
    attempt_path = Path(attempt_path_str)
    attempt_path.mkdir(parents=True, exist_ok=True)
    trace_path = attempt_path / "model_trace.jsonl"
    started = _now()
    record = {
        "schema_version": RUN_SCHEMA,
        **spec,
        "status": "started",
        "started_at": started,
        "model_selector": "luna",
    }
    _write_json(attempt_path / "attempt.json", record)
    try:
        if spec["condition"] == "PIPELINE":
            case_id = f"paper_{spec['attempt_id']}"
            case = dict(config["case"])
            case["id"] = case_id
            if "teacher_skills" not in case and "teacher_recently_taught" in case:
                case["teacher_skills"] = case["teacher_recently_taught"]
            taught_resources = [
                {
                    "standard_id": evidence["standard_id"],
                    "label": evidence["label"],
                }
                for evidence in config.get("grounding_evidence", [])
            ]
            shared_context = {
                "learner_context": config["learner_context"],
                "benchmark_context": case.get("benchmark_context"),
                "teacher_context": {
                    "taught_resources": taught_resources,
                    "instruction_boundary": (
                        "Use only the listed official standards as taught resources. "
                        "Do not retrieve unrelated statistics or advanced curricula."
                    ),
                },
                "grounding_evidence": config.get("grounding_evidence", []),
            }
            pipeline = config.get("pipeline", {})
            pipeline_path = attempt_path / "pipeline"
            design_kwargs = {} if pipeline.get("design_brief", True) else {"design_brief": False}
            pipeline_result = run_case_worker(
                case_id,
                str(pipeline_path),
                "luna",
                int(pipeline.get("k", 6)),
                None,
                case_override=case,
                shared_context=shared_context,
                evidence_k=int(pipeline.get("evidence_k", 6)),
                max_resources=int(pipeline.get("max_resources", 5)),
                d1_condition=str(pipeline.get("d1_condition", "grounded")),
                grounding_evidence=config.get("grounding_evidence"),
                api_semaphore=api_semaphore,
                trace_filename="model_trace.jsonl",
                **design_kwargs,
            )
            pipeline_trace = pipeline_path / "model_trace.jsonl"
            if pipeline_trace.is_file():
                (attempt_path / "model_trace.jsonl").write_bytes(pipeline_trace.read_bytes())
            stage = (pipeline_result.get("stages") or {}).get("D2_D3") or {}
            task = stage.get("task")
            status = (
                "ready"
                if isinstance(task, dict) and task.get("status") == "ready"
                else (
                    "blocked"
                    if isinstance(task, dict) and task.get("status") == "blocked"
                    else str(pipeline_result.get("status", "pipeline_failed"))
                )
            )
            result = {
                "status": status,
                "task": task,
                "pipeline_result": pipeline_result,
                "model_name": pipeline_result.get("model"),
            }
            if pipeline_result.get("error"):
                result["error"] = pipeline_result["error"]
        else:
            result = _run_direct_attempt(
                config, prompt, spec["condition"], trace_path, api_semaphore
            )
        record.update(result, status=result.get("status", "failed"), finished_at=_now())
    except Exception as exc:
        record.update(
            status="api_error" if isinstance(exc, RuntimeError) else "worker_failed",
            error=f"{type(exc).__name__}: {exc}",
            finished_at=_now(),
        )
    _write_json(attempt_path / "result.json", record)
    _write_json(attempt_path / "attempt.json", record)
    return record


def _read_attempt(path: Path) -> dict[str, Any]:
    for name in ("result.json", "attempt.json"):
        candidate = path / name
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {"status": "missing"}


def _trace_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "calls": 0,
            "finished": 0,
            "errors": 0,
            "usage": None,
            "elapsed_seconds": 0.0,
            "calls_with_usage": 0,
            "malformed_lines": 0,
        }
    records = []
    malformed_lines = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            malformed_lines += 1
    finished = [item for item in records if item.get("event") == "model_call_finished"]
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    seen_usage = False
    for item in finished:
        value = item.get("usage")
        if isinstance(value, dict):
            seen_usage = True
            for key in usage:
                usage[key] += int(value.get(key, 0) or 0)
    return {
        "calls": len([item for item in records if item.get("event") == "model_call_started"]),
        "finished": len(finished),
        "errors": len([item for item in finished if item.get("error")]),
        "usage": usage if seen_usage else None,
        "calls_with_usage": sum(isinstance(item.get("usage"), dict) for item in finished),
        "malformed_lines": malformed_lines,
        "elapsed_seconds": round(
            sum(float(item.get("elapsed_seconds", 0.0) or 0.0) for item in finished), 3
        ),
    }


def _judge_one(
    attempt: dict[str, Any],
    attempt_path: Path,
    learner_context: dict[str, Any],
    judge_prompt: dict[str, str],
    config: dict[str, Any],
) -> dict[str, Any]:
    judgment_path = attempt_path / "judgment.json"
    if judgment_path.is_file():
        return json.loads(judgment_path.read_text(encoding="utf-8"))
    task = attempt.get("task")
    if attempt.get("status") != "ready" or not isinstance(task, dict):
        result = {
            "status": "not_eligible",
            "attempt_id": attempt["attempt_id"],
            "reason": "generation did not produce a ready task",
            "finished_at": _now(),
        }
        _write_json(judgment_path, result)
        return result
    trace_path = attempt_path / "judge_trace.jsonl"
    if trace_path.is_file() and trace_path.stat().st_size:
        result = {
            "status": "interrupted",
            "attempt_id": attempt["attempt_id"],
            "reason": "Saved judge trace without final judgment; not rated again.",
            "finished_at": _now(),
        }
        _write_json(judgment_path, result)
        return result
    try:
        user = judge_input(student_task_text(task), learner_context)
    except ValueError as exc:
        result = {"status": "invalid_input", "attempt_id": attempt["attempt_id"], "error": str(exc)}
        _write_json(judgment_path, result)
        return result
    try:
        client, model = load_client("luna")
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)
    except (RuntimeError, ValueError, APIError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        _trace_append(
            trace_path,
            {
                "event": "judge_setup_failed",
                "stage": "judge",
                "error": error,
                "finished_at": _now(),
            },
        )
        result = {
            "status": "api_error",
            "attempt_id": attempt["attempt_id"],
            "error": error,
            "raw_response": "",
            "response_metadata": None,
            "finished_at": _now(),
        }
        _write_json(judgment_path, result)
        return result
    payload, raw, metadata, error = _call_json(
        client,
        model,
        judge_prompt["system"],
        user,
        max_tokens=int(JUDGE_SETTINGS.get("max_tokens", 4000)),
        retries=int(config.get("transport_retries", 2)),
        trace_path=trace_path,
        stage="judge",
    )
    if error:
        result = {
            "status": "api_error",
            "attempt_id": attempt["attempt_id"],
            "error": error,
            "raw_response": raw,
            "response_metadata": metadata,
        }
    else:
        try:
            parsed = parse_rating(json.dumps(payload, ensure_ascii=False))
            result = {
                "attempt_id": attempt["attempt_id"],
                **parsed,
                "raw_response": raw,
                "response_metadata": metadata,
            }
        except ValueError as exc:
            result = {
                "status": "invalid_response",
                "attempt_id": attempt["attempt_id"],
                "scores": None,
                "error": f"{type(exc).__name__}: {exc}",
                "raw_response": raw,
                "response_metadata": metadata,
            }
    _write_json(judgment_path, result)
    return result


def _condition_summary(
    condition: str,
    attempts: list[dict[str, Any]],
    judgments: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for attempt in attempts:
        status = str(attempt.get("status", "missing"))
        status_counts[status] = status_counts.get(status, 0) + 1
    scores: dict[str, list[float]] = {key: [] for key in (*DIMENSIONS, "TOTAL")}
    for attempt in attempts:
        judgment = judgments.get(attempt["attempt_id"], {})
        raw_scores = judgment.get("scores")
        if isinstance(raw_scores, dict):
            for key in scores:
                value = raw_scores.get(key)
                if isinstance(value, (int, float)):
                    scores[key].append(float(value))
    dimensions = {}
    for key, values in scores.items():
        spread = statistics.stdev(values) if len(values) > 1 else None
        dimensions[key] = {
            "n": len(values),
            "mean": statistics.mean(values) if values else None,
            "sd": spread,
            "spread": spread,
        }
    trace = {
        "calls": 0,
        "finished": 0,
        "errors": 0,
        "usage": None,
        "calls_with_usage": 0,
        "malformed_lines": 0,
    }
    trace_elapsed = 0.0
    judge_trace = dict(trace)
    judge_elapsed = 0.0
    elapsed = 0.0
    for attempt in attempts:
        path = Path(attempt.get("_absolute_path", "")) if attempt.get("_absolute_path") else None
        if path is not None:
            generation_trace = path / "model_trace.jsonl"
            if not generation_trace.is_file():
                generation_trace = path / "pipeline" / "model_trace.jsonl"
            stats = _trace_stats(generation_trace)
            for key in ("calls", "finished", "errors", "calls_with_usage", "malformed_lines"):
                trace[key] += stats[key]
            trace_elapsed += stats["elapsed_seconds"]
            if stats["usage"] is not None:
                if trace["usage"] is None:
                    trace["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                for key in trace["usage"]:
                    trace["usage"][key] += stats["usage"][key]
            judge_stats = _trace_stats(path / "judge_trace.jsonl")
            for key in ("calls", "finished", "errors", "calls_with_usage", "malformed_lines"):
                judge_trace[key] += judge_stats[key]
            judge_elapsed += judge_stats["elapsed_seconds"]
            if judge_stats["usage"] is not None:
                if judge_trace["usage"] is None:
                    judge_trace["usage"] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }
                for key in judge_trace["usage"]:
                    judge_trace["usage"][key] += judge_stats["usage"][key]
        if isinstance(attempt.get("started_at"), str) and isinstance(
            attempt.get("finished_at"), str
        ):
            try:
                from datetime import datetime

                elapsed += max(
                    0.0,
                    (
                        datetime.fromisoformat(attempt["finished_at"])
                        - datetime.fromisoformat(attempt["started_at"])
                    ).total_seconds(),
                )
            except ValueError:
                pass
    blocked_statuses = {
        "blocked",
        "no_valid_proposals",
        "no_winner",
        "plan_blocked",
        "expression_blocked",
        "review_blocked",
        "fill_not_accepted",
        "data_review_needed",
        "data_not_accepted",
        "D3_blocked",
    }
    ready = status_counts.get("ready", 0)
    pending = status_counts.get("pending", 0)
    interrupted = status_counts.get("interrupted", 0) + status_counts.get("started", 0)
    blocked = sum(status_counts.get(status, 0) for status in blocked_statuses)
    missing = status_counts.get("missing", 0)
    rated = sum(
        judgments.get(attempt["attempt_id"], {}).get("status") == "scored" for attempt in attempts
    )
    return {
        "denominator": len(attempts),
        "counts": {
            "scheduled": len(attempts),
            "attempted": len(attempts) - pending - missing,
            "ready": ready,
            "blocked": blocked,
            "pending": pending,
            "interrupted": interrupted,
            "missing_attempt": missing,
            "failed": len(attempts) - ready - blocked - pending - interrupted - missing,
            "rated": rated,
            "ready_without_complete_rating": ready - rated,
        },
        "completion_rate": ready / len(attempts) if attempts else None,
        "status_counts": status_counts,
        "scores": dimensions,
        "generation": {
            "calls": trace,
            "elapsed_seconds": round(elapsed, 3),
            "model_call_elapsed_seconds": round(trace_elapsed, 3),
        },
        "judging": {"calls": judge_trace, "elapsed_seconds": round(judge_elapsed, 3)},
        "math_checks": {"status": "not_available_for_cross_arm_comparison"},
    }


def _bootstrap_difference_interval(
    current: list[float],
    baseline: list[float],
    *,
    seed: int,
    resamples: int = 2000,
) -> list[float] | None:
    if len(current) < 2 or len(baseline) < 2:
        return None
    rng = random.Random(seed)
    differences = []
    for _ in range(resamples):
        current_mean = statistics.mean(rng.choice(current) for _ in current)
        baseline_mean = statistics.mean(rng.choice(baseline) for _ in baseline)
        differences.append(current_mean - baseline_mean)
    differences.sort()
    lower = differences[int(0.025 * (len(differences) - 1))]
    upper = differences[int(0.975 * (len(differences) - 1))]
    return [lower, upper]


def _add_differences(
    summary: dict[str, Any],
    score_values: dict[str, dict[str, list[float]]] | None = None,
    *,
    seed: int = 0,
) -> None:
    baseline = summary["conditions"].get("V1", {}).get("scores", {})
    for condition, values in summary["conditions"].items():
        if condition == "V1":
            continue
        values["differences_vs_V1"] = {}
        for key, current in values.get("scores", {}).items():
            base = baseline.get(key, {})
            n, n0 = current.get("n", 0), base.get("n", 0)
            mean, mean0 = current.get("mean"), base.get("mean")
            if mean is None or mean0 is None:
                values["differences_vs_V1"][key] = None
                continue
            difference = mean - mean0
            current_values = (score_values or {}).get(condition, {}).get(key, [])
            baseline_values = (score_values or {}).get("V1", {}).get(key, [])
            seed_bytes = f"{seed}:{condition}:{key}".encode("utf-8")
            bootstrap_seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:8], "big")
            values["differences_vs_V1"][key] = {
                "n": n,
                "baseline_n": n0,
                "difference": difference,
                "bootstrap_95ci": _bootstrap_difference_interval(
                    current_values,
                    baseline_values,
                    seed=bootstrap_seed,
                ),
                "uncertainty_method": "deterministic independent-group bootstrap; exploratory",
            }


def _write_summary(
    output: Path, manifest: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    attempts_by_condition: dict[str, list[dict[str, Any]]] = {key: [] for key in CONDITIONS}
    for attempt_id, item in manifest["attempts"].items():
        path = output / item["path"]
        record = _read_attempt(path)
        record["attempt_id"] = attempt_id
        record["_absolute_path"] = str(path)
        attempts_by_condition[item["condition"]].append(record)
    judgments: dict[str, dict[str, Any]] = {}
    score_values: dict[str, dict[str, list[float]]] = {
        condition: {key: [] for key in (*DIMENSIONS, "TOTAL")} for condition in CONDITIONS
    }
    for condition_attempts in attempts_by_condition.values():
        for attempt in condition_attempts:
            path = Path(attempt["_absolute_path"]) / "judgment.json"
            if path.is_file():
                judgments[attempt["attempt_id"]] = json.loads(path.read_text(encoding="utf-8"))
            judgment = judgments.get(attempt["attempt_id"], {})
            scores = judgment.get("scores")
            if isinstance(scores, dict):
                for key in score_values[attempt["condition"]]:
                    value = scores.get(key)
                    if isinstance(value, (int, float)):
                        score_values[attempt["condition"]][key].append(float(value))
    summary = {
        "schema_version": RUN_SCHEMA,
        "generated_at": _now(),
        "source_integrity_unchanged": manifest.get("source_integrity_unchanged"),
        "denominators": {
            condition: len(items) for condition, items in attempts_by_condition.items()
        },
        "conditions": {
            condition: _condition_summary(condition, items, judgments)
            for condition, items in attempts_by_condition.items()
        },
        "judging": {
            "attempted": len(judgments),
            "scored": sum(item.get("status") == "scored" for item in judgments.values()),
            "frozen_order": manifest["judge_order"],
        },
    }
    execution_scope = manifest.get("execution_scope")
    if execution_scope is None:
        _add_differences(summary, score_values, seed=int(config["shuffle_seed"]))
    else:
        summary["execution_scope"] = execution_scope
        summary["benchmark_status"] = "not_a_benchmark"
        summary["comparisons"] = {
            "status": "not_computed",
            "reason": "single-condition calibration leaves benchmark conditions unattempted",
        }
        summary["judging"]["status"] = "skipped"
        summary["judging"]["reason"] = (
            "single-condition calibration is not benchmark-complete and must not be judged"
        )
    _write_json(output / "summary.json", summary)
    return summary


def run_benchmark(
    output: Path,
    *,
    config_path: Path = CONFIG_PATH,
    prompt_path: Path = PROMPT_PATH,
    resume: bool = False,
    dry_run: bool = False,
    limit_per_condition: int | None = None,
    only_condition: str | None = None,
) -> dict[str, Any]:
    execution_scope = _execution_scope(only_condition, limit_per_condition)
    manifest, config, prompt = prepare_run(
        output,
        config_path=config_path,
        prompt_path=prompt_path,
        resume=resume,
        only_condition=only_condition,
        limit_per_condition=limit_per_condition,
    )
    if dry_run:
        return manifest
    pending: list[tuple[dict[str, Any], Path]] = []
    conditions_to_run = [only_condition] if only_condition is not None else CONDITIONS
    for condition in conditions_to_run:
        selected = [
            item
            for item in manifest["attempts"].values()
            if item["condition"] == condition
            and _read_attempt(output / item["path"]).get("status") == "pending"
        ]
        if limit_per_condition is not None:
            selected = selected[:limit_per_condition]
        pending.extend((item, output / item["path"]) for item in selected)

    max_api = int(config.get("max_concurrent_api_requests", config["workers"]))
    max_api = max(1, max_api)
    manager = multiprocessing.Manager()
    semaphore = manager.BoundedSemaphore(max_api)
    manifest["status"] = "running"
    manifest["started_at"] = manifest.get("started_at", _now())
    _write_json(output / "manifest.json", manifest)
    futures: dict[concurrent.futures.Future, dict[str, Any]] = {}
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=config["workers"]) as pool:
            for item, path in pending:
                future = pool.submit(
                    _run_attempt_worker,
                    item,
                    str(path),
                    config,
                    prompt,
                    semaphore,
                )
                futures[future] = item
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        **item,
                        "status": "worker_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "finished_at": _now(),
                    }
                    _write_json(output / item["path"] / "attempt.json", result)
                manifest["attempts"][item["attempt_id"]].update(
                    {
                        key: result[key]
                        for key in ("status", "started_at", "finished_at", "error", "model_name")
                        if key in result
                    }
                )
                if result.get("model_name"):
                    manifest["model_name"] = result["model_name"]
                _write_json(output / "manifest.json", manifest)
                print(f"generation {item['attempt_id']}: {result.get('status')}", flush=True)
    finally:
        manager.shutdown()

    if execution_scope is not None:
        manifest["benchmark_status"] = "not_a_benchmark"
        manifest["comparison_status"] = "not_computed"
        manifest["judging_status"] = "skipped_single_condition_calibration"
        manifest["judging_skip_reason"] = (
            "single-condition calibration leaves benchmark conditions unattempted"
        )
        manifest["status"] = "summarizing"
        _write_json(output / "manifest.json", manifest)
    else:
        # Wait for all scheduled outcomes so limited technical batches do not change rating order.
        remaining = any(item.get("status") == "pending" for item in manifest["attempts"].values())
        # Judge in a deterministic, frozen order. Existing judgment files are reused.
        judge_prompt = load_judge_prompt()
        manifest["status"] = "judging"
        _write_json(output / "manifest.json", manifest)
        for attempt_id in manifest["judge_order"]:
            if remaining:
                break
            item = manifest["attempts"][attempt_id]
            attempt_path = output / item["path"]
            attempt = _read_attempt(attempt_path)
            if (attempt_path / "judgment.json").is_file():
                continue
            if attempt.get("status") not in {"ready", "blocked"}:
                continue
            judgment = _judge_one(
                attempt, attempt_path, config["learner_context"], judge_prompt, config
            )
            item["judge_status"] = judgment.get("status")
            _write_json(output / "manifest.json", manifest)
            print(f"judge {attempt_id}: {judgment.get('status')}", flush=True)
    manifest["finished_at"] = _now()
    pending_statuses = {"pending", "started", "missing"}
    statuses = [str(item.get("status")) for item in manifest["attempts"].values()]
    if any(status in pending_statuses for status in statuses):
        manifest["status"] = "incomplete"
    elif any(status not in {"ready", "blocked"} for status in statuses):
        manifest["status"] = "completed_with_failures"
    else:
        manifest["status"] = "completed"
    manifest["source_hashes_after"] = source_hashes(config_path, prompt_path)
    manifest["source_integrity_unchanged"] = (
        manifest["source_hashes_after"] == manifest["source_hashes"]
    )
    if not manifest["source_integrity_unchanged"]:
        manifest["status"] = "source_changed"
    summary = _write_summary(output, manifest, config)
    if manifest["status"] == "completed" and any(
        condition["counts"]["ready_without_complete_rating"]
        for condition in summary["conditions"].values()
    ):
        manifest["status"] = "completed_with_missing_ratings"
    manifest["summary_path"] = "summary.json"
    _write_json(output / "manifest.json", manifest)
    return manifest


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--prompts", type=Path, default=PROMPT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare", "--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--limit-per-condition", type=int)
    parser.add_argument(
        "--only-condition",
        choices=CONDITIONS,
        help="run one condition as a calibration; keeps the full schedule but is not a benchmark",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    parsed = parse_args(args)
    if parsed.limit_per_condition is not None and parsed.limit_per_condition < 1:
        raise SystemExit("--limit-per-condition must be positive")
    try:
        result = run_benchmark(
            parsed.output,
            config_path=parsed.config,
            prompt_path=parsed.prompts,
            resume=parsed.resume,
            dry_run=parsed.dry_run,
            limit_per_condition=parsed.limit_per_condition,
            only_condition=parsed.only_condition,
        )
    except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if parsed.dry_run:
        print(f"prepared: {parsed.output}")
        return 0
    manifest = result
    return 0 if manifest.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
