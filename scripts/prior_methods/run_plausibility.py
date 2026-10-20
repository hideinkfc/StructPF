"""Judge plausibility of all generated prior-method candidates.

Reads a generations.jsonl from run_generation.py, judges each method with the
frozen JUDGE prompt (concept_overlap gate + 0-2 plausibility), writes
plausibility.jsonl in the same run directory. Blinded: judge sees no model
label and no repeat info.

Usage:
  ./.venv/bin/python scripts/prior_methods/run_plausibility.py \
      --results-dir experiments/results/prior_methods_benchmark/<date>_generation_v3
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prior_methods.common import (  # noqa: E402
    ROOT,
    chat_json,
    load_client,
    load_generation_records,
    load_packages,
)

PROMPT_PATH = ROOT / "src" / "generation" / "prompts" / "prior_methods.yaml"
WORKERS = 10


def render(template: str, values: dict) -> str:
    out = template
    for token, value in values.items():
        out = out.replace(token, value)
    return out


def judge_one(client, model, judge_system, judge_user_tmpl, package, gen, m_idx, method):
    user = render(
        judge_user_tmpl,
        {
            "{topic}": package["anchor"]["topic"],
            "{concept_text}": package["concept_text"],
            "{method_name}": method.get("method_name", ""),
            "{general_procedure}": method.get("general_procedure", ""),
            "{student_thinking}": method.get("student_thinking", ""),
        },
    )
    key = {
        "concept_id": gen["concept_id"],
        "model_label": gen["model_label"],
        "repeat": gen["repeat"],
        "method_index": m_idx,
    }
    try:
        payload, raw = chat_json(client, model, judge_system, user, temperature=0.0, max_tokens=300)
        if payload is None:
            return {
                **key,
                "score": None,
                "concept_overlap": None,
                "reason": f"parse failure: {raw[:150]}",
                "parse_ok": False,
            }
        score = payload.get("score")
        overlap = payload.get("concept_overlap")
        ok = score in (0, 1, 2) and isinstance(overlap, bool)
        return {
            **key,
            "score": score,
            "concept_overlap": overlap,
            "reason": payload.get("reason", ""),
            "parse_ok": ok,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            **key,
            "score": None,
            "concept_overlap": None,
            "reason": f"exception: {exc}",
            "parse_ok": False,
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    results_dir = args.results_dir if args.results_dir.is_absolute() else ROOT / args.results_dir

    prompts = yaml.safe_load(PROMPT_PATH.read_text())
    packages = load_packages()
    client, model = load_client()
    generations = [g for g in load_generation_records(results_dir) if g.get("status") == "ok"]

    jobs = []
    for gen in generations:
        for m_idx, method in enumerate(gen.get("methods", [])):
            jobs.append((packages[gen["concept_id"]], gen, m_idx, method))

    print(f"{len(jobs)} plausibility judgments over {len(generations)} generation calls")

    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [
            pool.submit(
                judge_one,
                client,
                model,
                prompts["JUDGE_SYSTEM"],
                prompts["JUDGE_USER"],
                pkg,
                gen,
                i,
                m,
            )
            for pkg, gen, i, m in jobs
        ]
        for k, fut in enumerate(futs, 1):
            rows.append(fut.result())
            if k % 50 == 0 or k == len(futs):
                print(f"  {k}/{len(futs)}")

    n_bad = sum(1 for r in rows if not r["parse_ok"])
    out = results_dir / "plausibility.jsonl"
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"parse failures: {n_bad}; saved {len(rows)} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
