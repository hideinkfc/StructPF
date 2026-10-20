"""Generate frozen V1 direct-prompt PF tasks from GPT-5 mini and GPT-4.1 under one condition.

Reuses the exact prompt, learner context, target and validation of the saved
paper-setting V1 condition. Inputs are frozen before any model call. Failed,
blocked or truncated attempts are kept and never replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_paper_benchmark as bench  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_paper_benchmark.json"
PROMPT = ROOT / "src/generation/prompts/pf_paper_benchmark.yaml"
MODELS = {
    "gpt-5-mini": {"tag": "gpt5mini", "temperature": None},
    "gpt-4.1": {"tag": "gpt41", "temperature": 0.0},
}
SCHEMA_VERSION = "pf-direct-model-comparison/v1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def client() -> OpenAI:
    load_dotenv(ROOT / ".env.local", override=False)
    return OpenAI(
        base_url=os.environ["AZURE_OPENAI_BASE_URL"].strip(),
        api_key=os.environ["AZURE_OPENAI_API_KEY"].strip(),
        max_retries=0,
        timeout=240,
    )


def frozen_prompt(config: dict[str, Any], prompt: dict[str, Any]) -> tuple[str, str]:
    """Render the V1 system and user text exactly as the saved direct condition does."""
    values = bench._direct_values(config, [])
    system = bench._render(prompt["system"], values)
    user = bench._direct_user(prompt, values, include_misconceptions=False)
    return system, user


def prepare(output: Path, n: int) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Use a new output directory; frozen inputs are immutable")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    prompt = bench.load_prompt(PROMPT)
    system, user = frozen_prompt(config, prompt)
    if config["case"]["id"] != "rahimi_ratio_g7_usa_basketball":
        raise ValueError("Unexpected benchmark case")
    output.mkdir(parents=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "frozen_at": now(),
        "condition": "V1 direct, paper-setting reconstruction, no misconceptions",
        "case_id": config["case"]["id"],
        "learning_target": config["case"]["target_concept"],
        "learner_context": config["learner_context"],
        "models": {
            name: {"tag": spec["tag"], "temperature_requested": spec["temperature"]}
            for name, spec in MODELS.items()
        },
        "attempts_per_model": n,
        "max_completion_tokens": config["generation_max_tokens"],
        "transport_retries": 0,
        "failed_attempts_replaced": False,
        "prompt_system_sha256": sha256_text(system),
        "prompt_user_sha256": sha256_text(user),
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (CONFIG, PROMPT, Path(bench.__file__), Path(__file__))
        },
        "boundary": (
            "Model outputs are generated tasks. No human ratings, student attempts or "
            "learning are implied."
        ),
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def run_attempt(
    api: OpenAI,
    output: Path,
    model: str,
    index: int,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float | None,
) -> dict[str, Any]:
    spec = MODELS[model]
    attempt_id = f"{spec['tag']}-{index:03d}"
    directory = output / "attempts" / attempt_id
    result_path = directory / "attempt.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    directory.mkdir(parents=True)
    trace = directory / "model_trace.jsonl"
    started = now()
    payload, raw, metadata, error = bench._call_json(
        api,
        model,
        system,
        user,
        max_tokens=max_tokens,
        retries=0,
        trace_path=trace,
        stage=f"V1.{spec['tag']}",
        temperature=temperature if temperature is not None else 0.0,
    )
    if error:
        record: dict[str, Any] = {
            "attempt_id": attempt_id,
            "model_requested": model,
            "status": "api_error",
            "error": error,
            "raw_response": raw,
            "response_metadata": metadata,
            "task": None,
        }
    else:
        status, schema_error = bench._validate_task(payload)
        record = {
            "attempt_id": attempt_id,
            "model_requested": model,
            "status": status,
            "error": schema_error,
            "task": payload,
            "raw_response": raw,
            "response_metadata": metadata,
        }
    record["started_at"] = started
    record["finished_at"] = now()
    record["effective_truncation"] = bool(
        metadata and metadata.get("finish_reason") == "length"
    )
    write_json(result_path, record)
    return record


def run(output: Path, n: int, workers: int) -> dict[str, Any]:
    if not (output / "manifest.json").exists():
        manifest = prepare(output, n)
    else:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    prompt = bench.load_prompt(PROMPT)
    system, user = frozen_prompt(config, prompt)
    if sha256_text(system) != manifest["prompt_system_sha256"]:
        raise ValueError("Frozen system prompt changed since preparation")
    if sha256_text(user) != manifest["prompt_user_sha256"]:
        raise ValueError("Frozen user prompt changed since preparation")
    api = client()
    jobs = [
        (model, index)
        for index in range(1, manifest["attempts_per_model"] + 1)
        for model in MODELS
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                run_attempt,
                api,
                output,
                model,
                index,
                system,
                user,
                manifest["max_completion_tokens"],
                MODELS[model]["temperature"],
            )
            for model, index in jobs
        ]
        for future in futures:
            results.append(future.result())
    summary: dict[str, Any] = {"generated_at": now(), "by_model": {}}
    for model in MODELS:
        rows = [row for row in results if row["model_requested"] == model]
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary["by_model"][model] = {
            "attempts": len(rows),
            "status_counts": counts,
            "truncated": sum(bool(row.get("effective_truncation")) for row in rows),
            "returned_models": sorted(
                {str((row.get("response_metadata") or {}).get("model")) for row in rows}
            ),
        }
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        manifest = prepare(args.output, args.attempts)
        print(f"Froze {2 * args.attempts} scheduled generations in {args.output}")
        print(json.dumps(manifest["models"], indent=2))
        return
    summary = run(args.output, args.attempts, args.workers)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
