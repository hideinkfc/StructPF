"""Shared helpers for the prior-methods benchmark runners."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "experiments" / "data" / "prior_methods_benchmark"
RESULTS = ROOT / "experiments" / "results" / "prior_methods_benchmark"

JUDGE_MODEL_ENV = "AZURE_OPENAI_GPT41_MINI_MODEL"
JUDGE_MODEL_DEFAULT = "gpt-4.1-mini"


MODEL_ENVS = {
    "gpt41mini": ("AZURE_OPENAI_GPT41_MINI_MODEL", "gpt-4.1-mini"),
    "gpt41": ("AZURE_OPENAI_GPT41_MODEL", "gpt-4.1"),
    "gpt54": ("AZURE_OPENAI_GPT54_MODEL", "gpt-5.4"),
    "luna": ("AZURE_OPENAI_LUNA_MODEL", "gpt-5.6-luna"),
}


def load_client(which: str = "gpt41mini") -> tuple[OpenAI, str]:
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    env, default = MODEL_ENVS.get(which, MODEL_ENVS["gpt41mini"])
    model = os.environ.get(env, default).strip()
    if not base_url or not api_key:
        raise RuntimeError("Azure config missing from .env.local")
    return OpenAI(base_url=base_url, api_key=api_key), model


def load_packages() -> dict[str, dict]:
    packages = {}
    for path in sorted(DATA.glob("*.json")):
        if path.name == "expert_anticipated.json":
            continue
        pkg = json.loads(path.read_text())
        packages[pkg["concept_id"]] = pkg
    return packages


def ground_truth_list(package: dict) -> str:
    lines = []
    for i, e in enumerate(package["all_errors"]):
        expl = e["explanation"] or "(no explanation available)"
        lines.append(
            f"[{i}] {e['pct_students']}% of students chose \"{e['option_text']}\" "
            f"on: {e['question_stem'][:120]} | teacher note: {expl[:220]}"
        )
    return "\n".join(lines)


def chat_json(client: OpenAI, model: str, system: str, user: str,
              temperature: float, max_tokens: int) -> tuple[dict | None, str]:
    """One JSON-mode chat call. Returns (parsed_payload, raw_text)."""
    is_new = model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3")
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        timeout=180,
    )
    if is_new:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)
    text = response.choices[0].message.content or ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                payload = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                payload = None
        else:
            payload = None
    return payload, text


def load_generation_records(results_dir: Path) -> list[dict]:
    path = results_dir / "generations.jsonl"
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records
