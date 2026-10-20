"""Pattern smoke test for prior-methods generation.

Runs N repeats x 2 models x 2 concepts to identify GENERAL failure patterns
(paraphrase padding, valid-method contamination, contract drift) before any
prompt fix is applied. Saves raw output for manual review.

Usage: ./.venv/bin/python scripts/prior_methods/smoke_patterns.py
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "experiments" / "data" / "prior_methods_benchmark"
PROMPTS = ROOT / "src" / "generation" / "prompts" / "prior_methods.yaml"
OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "smoke_patterns.json"

CONCEPTS = ["c5_commonbasis", "x_brackets"]
REPEATS = 5
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


def render(user_template: str, package: dict) -> str:
    user = user_template
    for token, value in {
        "{grade}": str(package["grade"]),
        "{topic}": package["anchor"]["topic"],
        "{concept_text}": package["concept_text"],
        "{n_methods}": str(N_METHODS),
    }.items():
        user = user.replace(token, value)
    return user


def one_call(client: OpenAI, model: str, system: str, user: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"},
            timeout=120,
        )
        text = response.choices[0].message.content or ""
        payload = json.loads(text)
        methods = payload.get("methods")
        problems = []
        if not isinstance(methods, list):
            problems.append("methods not a list")
            methods = []
        elif len(methods) != N_METHODS:
            problems.append(f"n_methods={len(methods)}")
        for i, m in enumerate(methods):
            if not isinstance(m, dict):
                problems.append(f"method {i} not object")
                continue
            for f in ("method_name", "general_procedure", "student_thinking"):
                if not m.get(f):
                    problems.append(f"method {i} missing {f}")
        return {"ok": not problems, "problems": problems, "methods": methods}
    except Exception as exc:  # noqa: BLE001 - record any failure as a contract problem
        return {"ok": False, "problems": [f"exception: {exc}"], "methods": []}


def main() -> None:
    prompts = yaml.safe_load(PROMPTS.read_text())
    client, models = load_client()
    packages = {cid: json.loads((DATA / f"{cid}.json").read_text()) for cid in CONCEPTS}

    jobs = []
    for cid, package in packages.items():
        user = render(prompts["PRIOR_METHODS_USER"], package)
        for label, model in models.items():
            for rep in range(REPEATS):
                jobs.append((cid, label, model, rep, user))

    n_jobs = len(jobs)
    print(f"{n_jobs} calls ({len(CONCEPTS)} concepts x {len(models)} models x {REPEATS} repeats)")

    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for cid, label, model, rep, user in jobs:
            fut = pool.submit(one_call, client, model, prompts["PRIOR_METHODS_SYSTEM"], user)
            futures[fut] = (cid, label, rep)
        for fut, (cid, label, rep) in futures.items():
            r = fut.result()
            results.append({"concept_id": cid, "model": label, "repeat": rep, **r})
            status = "ok" if r["ok"] else "PROBLEMS: " + "; ".join(r["problems"][:3])
            print(f"  {cid:16s} {label:9s} rep{rep}: {len(r['methods'])} methods, {status}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "concepts": CONCEPTS,
        "repeats": REPEATS,
        "n_methods_requested": N_METHODS,
        "temperature": 0.7,
        "results": results,
    }, indent=2, ensure_ascii=False) + "\n")
    n_ok = sum(1 for r in results if r["ok"])
    print(f"\n{n_ok}/{len(results)} calls fully contract-clean; saved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
