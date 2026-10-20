"""Scale the Rahimi-matched single-topic direct comparison to many tasks per model.

Same learner context, target, prompt and validation as the saved V1 condition.
Sampling uses each API's default because the source paper reports no sampling
setting. Inputs are frozen before any call. Failed attempts are kept, not replaced.
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
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_paper_benchmark as bench  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_paper_benchmark.json"
PROMPT = ROOT / "src/generation/prompts/pf_paper_benchmark.yaml"
MODELS = {"gpt-5-mini": "gpt5mini", "gpt-4.1": "gpt41"}
SCHEMA_VERSION = "pf-rahimi-scale-comparison/v1"
RESULT_ROOT = ROOT / "experiments/results/pf_rahimi_scale_comparison_20261013"


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
    output.mkdir(parents=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "frozen_at": now(),
        "condition": "V1 direct, Rahimi-matched single topic, no misconceptions",
        "topic_matched_to_rahimi_2025": {
            "grade": 7,
            "standard": "CCSS.Math.Content.7.RP.A.2",
            "prior_knowledge": ["7.RP.A.1 unit rates", "7.NS.A.1 rational-number operations"],
            "theme": "sports, basketball, Stephen Curry",
            "sample_per_model_in_paper": 30,
        },
        "case_id": config["case"]["id"],
        "learning_target": config["case"]["target_concept"],
        "learner_context": config["learner_context"],
        "models": {name: {"tag": tag, "sampling": "API default"} for name, tag in MODELS.items()},
        "attempts_per_model": n,
        "max_completion_tokens": config["generation_max_tokens"],
        "transport_retries": 0,
        "failed_attempts_replaced": False,
        "paper_sampling_setting": "not reported",
        "prompt_system_sha256": sha256_text(system),
        "prompt_user_sha256": sha256_text(user),
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (CONFIG, PROMPT, Path(bench.__file__), Path(__file__))
        },
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def call_api_default(
    api: OpenAI, model: str, system: str, user: str, max_tokens: int, trace: Path
) -> tuple[object | None, str, dict[str, Any] | None, str | None]:
    """One JSON-mode call with no temperature field, so the API default applies."""
    settings = bench._determine_effective_settings(model, {"max_tokens": max_tokens})
    started = now()
    try:
        response = api.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            timeout=240,
            **settings,
        )
    except OpenAIError as exc:
        error = f"{type(exc).__name__}: {exc}"
        with trace.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {"started_at": started, "finished_at": now(), "model": model, "error": error}
                )
                + "\n"
            )
        return None, "", None, error
    raw = response.choices[0].message.content or ""
    metadata = {
        "model": getattr(response, "model", model),
        "finish_reason": response.choices[0].finish_reason,
        "usage": bench._jsonable(getattr(response, "usage", None)),
        "settings_sent": settings,
    }
    with trace.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "started_at": started,
                    "finished_at": now(),
                    "model": model,
                    "raw_text": raw,
                    **metadata,
                }
            )
            + "\n"
        )
    return bench._json_payload(raw), raw, metadata, None


def run_attempt(
    api: OpenAI, output: Path, model: str, index: int, system: str, user: str, max_tokens: int
) -> dict[str, Any]:
    attempt_id = f"{MODELS[model]}-{index:03d}"
    directory = output / "attempts" / attempt_id
    result_path = directory / "attempt.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    directory.mkdir(parents=True)
    started = now()
    payload, raw, metadata, error = call_api_default(
        api, model, system, user, max_tokens, directory / "model_trace.jsonl"
    )
    if error:
        record: dict[str, Any] = {
            "status": "api_error",
            "error": error,
            "raw_response": raw,
            "task": None,
        }
    else:
        status, schema_error = bench._validate_task(payload)
        record = {"status": status, "error": schema_error, "task": payload, "raw_response": raw}
    record.update(
        attempt_id=attempt_id,
        model_requested=model,
        response_metadata=metadata,
        started_at=started,
        finished_at=now(),
        effective_truncation=bool(metadata and metadata.get("finish_reason") == "length"),
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
        (model, index) for index in range(1, manifest["attempts_per_model"] + 1) for model in MODELS
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(
                lambda job: run_attempt(
                    api, output, job[0], job[1], system, user, manifest["max_completion_tokens"]
                ),
                jobs,
            )
        )
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
            "distinct_tasks": len(
                {json.dumps(row["task"], sort_keys=True) for row in rows if row["task"]}
            ),
        }
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="new subdirectory under the result root")
    parser.add_argument("--attempts", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    output = RESULT_ROOT / args.name
    summary = run(output, args.attempts, args.workers)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
