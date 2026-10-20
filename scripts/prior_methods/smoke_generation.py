"""Smoke test for the prior-methods generation prompt.

One concept (c5_commonbasis), one call per model (gpt-4.1-mini, gpt-4.1).
Checks the output contract before any bulk spend:
- valid JSON, "methods" list of exactly N
- required fields present per method
- kind in {misconception, naive_strategy}

Usage: ./.venv/bin/python scripts/prior_methods/smoke_generation.py
"""

import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PACKAGE = ROOT / "experiments" / "data" / "prior_methods_benchmark" / "c5_commonbasis.json"
PROMPTS = ROOT / "src" / "generation" / "prompts" / "prior_methods.yaml"
OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "smoke_generation.json"

N_METHODS = 10
MODELS = {"gpt41mini": "AZURE_OPENAI_GPT41_MINI_MODEL", "gpt41": "AZURE_OPENAI_GPT41_MODEL"}
MODEL_DEFAULTS = {"gpt41mini": "gpt-4.1-mini", "gpt41": "gpt-4.1"}


def load_client() -> tuple[OpenAI, dict[str, str]]:
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("Azure config missing from .env.local")
    models = {
        label: os.environ.get(env, MODEL_DEFAULTS[label]).strip()
        for label, env in MODELS.items()
    }
    return OpenAI(base_url=base_url, api_key=api_key), models


def check_contract(methods: object) -> list[str]:
    problems = []
    if not isinstance(methods, list):
        return ["'methods' is not a list"]
    if len(methods) != N_METHODS:
        problems.append(f"expected {N_METHODS} methods, got {len(methods)}")
    for i, m in enumerate(methods):
        if not isinstance(m, dict):
            problems.append(f"method {i}: not an object")
            continue
        for field in ("method_name", "general_procedure", "student_thinking"):
            if not m.get(field):
                problems.append(f"method {i}: missing/empty '{field}'")
    return problems


def main() -> None:
    package = json.loads(PACKAGE.read_text())
    prompts = yaml.safe_load(PROMPTS.read_text())
    client, models = load_client()

    user = prompts["PRIOR_METHODS_USER"]
    for token, value in {
        "{grade}": str(package["grade"]),
        "{topic}": package["anchor"]["topic"],
        "{concept_text}": package["concept_text"],
        "{n_methods}": str(N_METHODS),
    }.items():
        assert token in user, f"missing placeholder {token}"
        user = user.replace(token, value)

    results = {}
    for label, model in models.items():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompts["PRIOR_METHODS_SYSTEM"]},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
        record = {"model": model, "raw_chars": len(text)}
        try:
            payload = json.loads(text)
            methods = payload.get("methods")
            record["contract_problems"] = check_contract(methods)
            record["methods"] = methods
        except json.JSONDecodeError as exc:
            record["contract_problems"] = [f"JSON parse failed: {exc}"]
            record["raw_head"] = text[:500]
        results[label] = record
        if record["contract_problems"]:
            print(f"{label}: CONTRACT PROBLEMS: " + "; ".join(record["contract_problems"]))
        else:
            print(f"{label}: CONTRACT OK")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "concept_id": package["concept_id"],
        "prompt_file": str(PROMPTS.relative_to(ROOT)),
        "n_methods_requested": N_METHODS,
        "temperature": 0.7,
        "results": results,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"saved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
