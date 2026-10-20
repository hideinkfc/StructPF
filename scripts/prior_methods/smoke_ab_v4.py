"""A/B smoke: v3 vs v4 generation prompt on x_brackets.

Runs both prompt versions, both models, N repeats, on the concept that showed
the worst instance-padding. Prints raw outputs and a duplicate heuristic so the
user can inspect whether v4 collapses positional variants into rules.

Usage: ./.venv/bin/python scripts/prior_methods/smoke_ab_v4.py
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
OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "smoke_ab_v4.json"

CONCEPT = "x_brackets"
REPEATS = 3
N_METHODS = 10
MODELS = {"gpt41mini": "AZURE_OPENAI_GPT41_MINI_MODEL", "gpt41": "AZURE_OPENAI_GPT41_MODEL"}
MODEL_DEFAULTS = {"gpt41mini": "gpt-4.1-mini", "gpt41": "gpt-4.1"}

VERSIONS = {
    "v3": {"user": "PRIOR_METHODS_USER",
           "fields": ("method_name", "general_procedure", "student_thinking")},
    "v4": {"user": "PRIOR_METHODS_USER_V4",
           "fields": ("method_name", "rule", "student_belief", "failure_mode")},
}


def load_client():
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("Azure config missing")
    models = {k: os.environ.get(v, MODEL_DEFAULTS[k]).strip() for k, v in MODELS.items()}
    return OpenAI(base_url=base_url, api_key=api_key), models


def render(tmpl, package, n):
    out = tmpl
    for tok, val in {"{grade}": str(package["grade"]), "{topic}": package["anchor"]["topic"],
                     "{concept_text}": package["concept_text"], "{n_methods}": str(n)}.items():
        out = out.replace(tok, val)
    return out


def one_call(client, model, system, user, fields):
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.7, max_tokens=4000,
            response_format={"type": "json_object"}, timeout=120)
        text = r.choices[0].message.content or ""
        methods = json.loads(text).get("methods", [])
        problems = []
        if len(methods) != N_METHODS:
            problems.append(f"n={len(methods)}")
        for i, m in enumerate(methods):
            for f in fields:
                if not (isinstance(m, dict) and m.get(f)):
                    problems.append(f"method {i} missing {f}")
        return {"ok": not problems, "problems": problems, "methods": methods}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "problems": [str(exc)], "methods": []}


def main():
    prompts = yaml.safe_load(PROMPTS.read_text())
    package = json.loads((DATA / f"{CONCEPT}.json").read_text())
    client, models = load_client()

    jobs = []
    for ver, cfg in VERSIONS.items():
        user = render(prompts[cfg["user"]], package, N_METHODS)
        for label, model in models.items():
            for rep in range(REPEATS):
                jobs.append((ver, label, model, rep, user, cfg["fields"]))

    njobs = len(jobs)
    print(f"{njobs} calls on {CONCEPT} "
          f"({len(VERSIONS)} vers x {len(models)} models x {REPEATS} reps)")
    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {}
        for ver, label, model, rep, user, flds in jobs:
            fut = pool.submit(one_call, client, model, prompts["PRIOR_METHODS_SYSTEM"], user, flds)
            futs[fut] = (ver, label, rep)
        for fut, (ver, label, rep) in futs.items():
            res = fut.result()
            results.append({"version": ver, "model": label, "repeat": rep, **res})
            status = "ok" if res["ok"] else str(res["problems"][:2])
            print(f"  {ver} {label:9s} rep{rep}: {len(res['methods'])} methods {status}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"concept": CONCEPT, "results": results},
                              indent=2, ensure_ascii=False) + "\n")
    print(f"saved -> {OUT.relative_to(ROOT)}")

    # print one full raw list per version+model (repeat 0) for inspection
    for ver in VERSIONS:
        for label in models:
            for r in results:
                if r["version"] == ver and r["model"] == label and r["repeat"] == 0:
                    sep = "=" * 20
                    print(f"\n{sep} {ver} | {label} | rep0 {sep}")
                    print(json.dumps(r["methods"], indent=1, ensure_ascii=False))
                    break


if __name__ == "__main__":
    main()
