#!/usr/bin/env python3
"""Generate prior-method candidates for the benchmark.

The runner is deliberately separate from the smoke scripts. It:

* loads the frozen concept packages;
* runs GPT-4.1-mini and GPT-4.1 with the frozen v3 prompt;
* preserves the rendered prompts and raw model responses;
* records contract failures instead of silently dropping them; and
* appends each completed call so an interrupted run can be resumed.

Examples:

    # Inspect the planned calls without contacting Azure.
    ./.venv/bin/python scripts/prior_methods/run_generation.py --dry-run

    # Run one call as a cheap end-to-end check.
    ./.venv/bin/python scripts/prior_methods/run_generation.py \
        --concept c5_commonbasis --model gpt41mini --repeats 1

    # Run the complete generation arm.
    ./.venv/bin/python scripts/prior_methods/run_generation.py --repeats 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "experiments" / "data" / "prior_methods_benchmark"
PROMPT_PATH = ROOT / "src" / "generation" / "prompts" / "prior_methods.yaml"
DEFAULT_WORKERS = 10
DEFAULT_REPEATS = 3
DEFAULT_N_METHODS = 10
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT = 120.0
PROMPT_VERSION = "v3"

MODEL_ENV = {
    "gpt41mini": "AZURE_OPENAI_GPT41_MINI_MODEL",
    "gpt41": "AZURE_OPENAI_GPT41_MODEL",
}
MODEL_DEFAULTS = {
    "gpt41mini": "gpt-4.1-mini",
    "gpt41": "gpt-4.1",
}
REQUIRED_FIELDS = ("method_name", "general_procedure", "student_thinking")


def utc_now() -> str:
    """Return a stable, timezone-aware timestamp for saved records."""
    return datetime.now(timezone.utc).isoformat()


def redact_error(error: Exception, api_key: str) -> str:
    """Prevent an API key from entering the saved result artifact."""
    return f"{type(error).__name__}: {error}".replace(api_key, "<redacted>")


def load_azure() -> tuple[OpenAI, str, dict[str, str]]:
    """Load Azure configuration using the repository's .env.local convention."""
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not base_url:
        raise RuntimeError("AZURE_OPENAI_BASE_URL is missing from .env.local or the environment.")
    if not api_key or api_key == "PASTE_ROTATED_KEY_HERE":
        raise RuntimeError("AZURE_OPENAI_API_KEY is missing or still uses the placeholder.")
    models = {
        label: os.environ.get(env_name, MODEL_DEFAULTS[label]).strip()
        for label, env_name in MODEL_ENV.items()
    }
    if any(not model for model in models.values()):
        raise RuntimeError("Configured model names must be non-empty.")
    return OpenAI(base_url=base_url, api_key=api_key, max_retries=0), api_key, models


def load_prompt() -> dict[str, str]:
    """Load and validate the frozen prompt file."""
    prompts = yaml.safe_load(PROMPT_PATH.read_text())
    if not isinstance(prompts, dict):
        raise ValueError(f"Prompt file is not a mapping: {PROMPT_PATH}")
    for key in ("PRIOR_METHODS_SYSTEM", "PRIOR_METHODS_USER"):
        if not isinstance(prompts.get(key), str) or not prompts[key].strip():
            raise ValueError(f"Prompt file is missing non-empty {key}: {PROMPT_PATH}")
    return prompts


def load_packages(selected: list[str] | None) -> list[dict[str, Any]]:
    """Load concept packages in deterministic order and reject unknown IDs."""
    paths = sorted(DATA_DIR.glob("*.json"))
    packages_by_id: dict[str, dict[str, Any]] = {}
    for path in paths:
        if path.name == "expert_anticipated.json":
            continue
        package = json.loads(path.read_text())
        concept_id = package.get("concept_id")
        if not isinstance(concept_id, str) or not concept_id:
            raise ValueError(f"Ground-truth package has no concept_id: {path}")
        if concept_id in packages_by_id:
            raise ValueError(f"Duplicate concept_id: {concept_id}")
        packages_by_id[concept_id] = package

    if selected is None:
        return [packages_by_id[key] for key in sorted(packages_by_id)]

    unknown = sorted(set(selected) - packages_by_id.keys())
    if unknown:
        raise ValueError(f"Unknown concept IDs: {', '.join(unknown)}")
    return [packages_by_id[key] for key in selected]


def render_user_prompt(template: str, package: dict[str, Any], n_methods: int) -> str:
    """Replace only known tokens, preserving literal JSON braces in the example."""
    anchor = package.get("anchor")
    if not isinstance(anchor, dict):
        raise ValueError(f"Package {package.get('concept_id')} has no anchor mapping.")
    values = {
        "{grade}": str(package["grade"]),
        "{topic}": str(anchor["topic"]),
        "{concept_text}": str(package["concept_text"]),
        "{n_methods}": str(n_methods),
    }
    prompt = template
    for token, value in values.items():
        if token not in prompt:
            raise ValueError(f"Prompt is missing placeholder {token}.")
        prompt = prompt.replace(token, value)
    return prompt


def prompt_hash(system_prompt: str, user_prompt: str) -> str:
    value = json.dumps(
        {"system": system_prompt, "user": user_prompt},
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_payload(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a JSON object, allowing a fenced/object-only recovery path."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as first_error:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end <= start:
            return None, f"JSON parse failed: {first_error}"
        try:
            payload = json.loads(raw_text[start : end + 1])
        except json.JSONDecodeError as second_error:
            return None, f"JSON parse failed: {second_error}"
    if not isinstance(payload, dict):
        return None, "Parsed response is not a JSON object."
    return payload, None


def validate_methods(payload: dict[str, Any] | None, n_methods: int) -> list[str]:
    """Validate the output contract while retaining all returned content."""
    if payload is None:
        return ["no parsed payload"]
    methods = payload.get("methods")
    if not isinstance(methods, list):
        return ["'methods' is not a list"]

    problems = []
    if len(methods) != n_methods:
        problems.append(f"expected {n_methods} methods, got {len(methods)}")
    for index, method in enumerate(methods):
        if not isinstance(method, dict):
            problems.append(f"method {index}: not an object")
            continue
        missing = [field for field in REQUIRED_FIELDS if not isinstance(method.get(field), str)]
        problems.extend(f"method {index}: missing/non-string '{field}'" for field in missing)
        extras = sorted(set(method) - set(REQUIRED_FIELDS))
        if extras:
            problems.append(f"method {index}: unexpected fields {extras}")
    return problems


def usage_dict(response: Any) -> dict[str, Any] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {
        key: getattr(usage, key)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if getattr(usage, key, None) is not None
    }


def run_one(
    client: OpenAI,
    api_key: str,
    job: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    attempts: int,
) -> dict[str, Any]:
    """Run one generation and return an explicit success or failure record."""
    started = time.perf_counter()
    raw_text = ""
    response_model = ""
    usage: dict[str, Any] | None = None
    errors: list[str] = []

    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model=job["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
            raw_text = response.choices[0].message.content or ""
            response_model = getattr(response, "model", "") or ""
            usage = usage_dict(response)
            payload, parse_error = parse_payload(raw_text)
            problems = validate_methods(payload, job["n_methods"])
            if parse_error:
                problems.insert(0, parse_error)
            status = "ok" if not problems else "contract_error"
            return {
                **job,
                "status": status,
                "attempts": attempt,
                "started_at": utc_now(),
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "response_model": response_model,
                "usage": usage,
                "prompt_sha256": prompt_hash(system_prompt, user_prompt),
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_text": raw_text,
                "payload": payload,
                "methods": (payload or {}).get("methods", []),
                "contract_problems": problems,
                "error": "",
            }
        # Record each failed call explicitly so one transient failure does not abort the batch.
        except Exception as error:
            errors.append(redact_error(error, api_key))
            if attempt < attempts:
                time.sleep(min(2**attempt, 8))

    return {
        **job,
        "status": "request_error",
        "attempts": attempts,
        "started_at": utc_now(),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "response_model": response_model,
        "usage": usage,
        "prompt_sha256": prompt_hash(system_prompt, user_prompt),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_text": raw_text,
        "payload": None,
        "methods": [],
        "contract_problems": [],
        "error": errors[-1] if errors else "request failed without an error",
        "attempt_errors": errors,
    }


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL result file and fail loudly on malformed saved state."""
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Malformed JSONL at {path}:{line_number}: {error}") from error
        if not isinstance(record, dict):
            raise ValueError(f"Non-object JSONL record at {path}:{line_number}")
        records.append(record)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))


def result_key(record: dict[str, Any]) -> tuple[str, str, int]:
    return record["concept_id"], record["model_label"], int(record["repeat"])


def prepare_output(
    output_dir: Path,
    manifest: dict[str, Any],
    resume: bool,
) -> tuple[Path, list[dict[str, Any]]]:
    """Create or validate run state before scheduling any calls."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    records_path = output_dir / "generations.jsonl"
    if resume:
        if not manifest_path.exists():
            raise FileNotFoundError(f"--resume requires an existing manifest: {manifest_path}")
        existing_manifest = json.loads(manifest_path.read_text())
        comparable = (
            "prompt_sha256",
            "concept_ids",
            "model_labels",
            "repeats",
            "n_methods",
            "temperature",
        )
        mismatches = [key for key in comparable if existing_manifest.get(key) != manifest.get(key)]
        if mismatches:
            raise ValueError(f"Cannot resume with changed run settings: {', '.join(mismatches)}")
        records = read_records(records_path)
        return records_path, records
    if manifest_path.exists() or records_path.exists():
        raise FileExistsError(
            f"Output directory is not empty: {output_dir}. "
            "Choose a new --results-dir or pass --resume."
        )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return records_path, []


def build_jobs(
    packages: list[dict[str, Any]],
    model_labels: list[str],
    repeats: int,
    n_methods: int,
    system_prompt: str,
    user_template: str,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], str]]:
    jobs = []
    user_prompts: dict[tuple[str, str], str] = {}
    for package in packages:
        concept_id = package["concept_id"]
        for model_label in model_labels:
            user_prompt = render_user_prompt(user_template, package, n_methods)
            user_prompts[(concept_id, model_label)] = user_prompt
            for repeat in range(repeats):
                jobs.append(
                    {
                        "concept_id": concept_id,
                        "model_label": model_label,
                        "repeat": repeat,
                        "model": "",
                        "n_methods": n_methods,
                        "prompt_version": PROMPT_VERSION,
                    }
                )
    return jobs, user_prompts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--concept",
        dest="concepts",
        action="append",
        help="Concept ID to run; repeat for multiple IDs (default: all packages).",
    )
    parser.add_argument(
        "--model",
        choices=("gpt41mini", "gpt41", "all"),
        default="all",
        help="Generator model arm (default: all).",
    )
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--n-methods", type=int, default=DEFAULT_N_METHODS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help=(
            "Output directory (default: "
            "experiments/results/prior_methods_benchmark/<date>_generation_v3)."
        ),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.repeats < 1 or args.n_methods < 1 or args.workers < 1 or args.attempts < 1:
        raise ValueError("repeats, n-methods, workers, and attempts must be positive.")
    if not 0 <= args.temperature:
        raise ValueError("temperature must be non-negative.")

    prompts = load_prompt()
    packages = load_packages(args.concepts)
    model_labels = ["gpt41mini", "gpt41"] if args.model == "all" else [args.model]
    jobs, user_prompts = build_jobs(
        packages,
        model_labels,
        args.repeats,
        args.n_methods,
        prompts["PRIOR_METHODS_SYSTEM"],
        prompts["PRIOR_METHODS_USER"],
    )
    model_prompt_hash = prompt_hash(
        prompts["PRIOR_METHODS_SYSTEM"],
        "\n".join(
            user_prompts[(package["concept_id"], model_label)]
            for package in packages
            for model_label in model_labels
        ),
    )
    for job in jobs:
        job["model"] = MODEL_DEFAULTS[job["model_label"]]

    if args.results_dir is None:
        date_label = datetime.now(timezone.utc).strftime("%Y%m%d")
        output_dir = (
            ROOT
            / "experiments"
            / "results"
            / "prior_methods_benchmark"
            / f"{date_label}_generation_{PROMPT_VERSION}"
        )
    else:
        output_dir = args.results_dir
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir

    manifest = {
        "status": "planned",
        "created_at": utc_now(),
        "prompt_file": str(PROMPT_PATH.relative_to(ROOT)),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": model_prompt_hash,
        "concept_ids": [package["concept_id"] for package in packages],
        "model_labels": model_labels,
        "models": {label: MODEL_DEFAULTS[label] for label in model_labels},
        "repeats": args.repeats,
        "n_methods": args.n_methods,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "timeout": args.timeout,
        "attempts": args.attempts,
        "workers": args.workers,
        "expected_calls": len(jobs),
        "expected_methods": len(jobs) * args.n_methods,
    }

    print(
        f"planned {len(jobs)} calls "
        f"({len(packages)} concepts x {len(model_labels)} models x {args.repeats} repeats)"
    )
    print(f"output: {output_dir}")
    if args.dry_run:
        return

    client, api_key, configured_models = load_azure()
    manifest["models"] = configured_models
    for job in jobs:
        job["model"] = configured_models[job["model_label"]]

    records_path, existing_records = prepare_output(output_dir, manifest, args.resume)
    latest = {result_key(record): record for record in existing_records}
    if args.retry_failures:
        latest = {key: record for key, record in latest.items() if record.get("status") == "ok"}
        write_jsonl(records_path, list(latest.values()))

    pending = [job for job in jobs if result_key(job) not in latest]
    if not pending:
        print("nothing to run; all requested calls are already complete")
        return

    manifest["status"] = "running"
    manifest["started_at"] = utc_now()
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )

    print(f"running {len(pending)} calls with {min(args.workers, len(pending))} workers")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(args.workers, len(pending))) as pool:
        futures = {}
        for job in pending:
            user_prompt = user_prompts[(job["concept_id"], job["model_label"])]
            future = pool.submit(
                run_one,
                client,
                api_key,
                job,
                prompts["PRIOR_METHODS_SYSTEM"],
                user_prompt,
                args.temperature,
                args.max_tokens,
                args.timeout,
                args.attempts,
            )
            futures[future] = job
        for completed, future in enumerate(as_completed(futures), start=1):
            record = future.result()
            latest[result_key(record)] = record
            with records_path.open("a") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
            problem = record["error"] or "; ".join(record["contract_problems"][:2])
            suffix = f" ({problem})" if problem else ""
            print(
                f"  [{completed}/{len(pending)}] {record['concept_id']} "
                f"{record['model_label']} rep{record['repeat']}: {record['status']}{suffix}",
                flush=True,
            )

    ok = sum(record.get("status") == "ok" for record in latest.values())
    contract_errors = sum(record.get("status") == "contract_error" for record in latest.values())
    request_errors = sum(record.get("status") == "request_error" for record in latest.values())
    manifest.update(
        {
            "status": "completed",
            "completed_at": utc_now(),
            "elapsed_seconds": round(time.perf_counter() - started, 2),
            "records": len(latest),
            "successful_calls": ok,
            "contract_error_calls": contract_errors,
            "request_error_calls": request_errors,
        }
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        f"saved {len(latest)}/{len(jobs)} records: "
        f"{ok} ok, {contract_errors} contract errors, {request_errors} request errors"
    )


if __name__ == "__main__":
    main()
