"""Match generated prior-method candidates against documented Eedi errors.

Reads generations.jsonl + plausibility.jsonl from a run directory, and for each
candidate that is NOT concept_overlap (gated upstream by the judge), runs the
minimal matcher: matched_error_index (pointer into the concept's error set) or
null. Writes matching.jsonl.

Usage:
  ./.venv/bin/python scripts/prior_methods/run_matching.py \
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
    ground_truth_list,
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


def match_one(client, model, matcher_system, matcher_user_tmpl,
              package, gt_list, gen, m_idx, method):
    user = render(matcher_user_tmpl, {
        "{topic}": package["anchor"]["topic"],
        "{general_procedure}": method.get("general_procedure", ""),
        "{student_thinking}": method.get("student_thinking", ""),
        "{ground_truth_list}": gt_list,
    })
    key = {
        "concept_id": gen["concept_id"], "model_label": gen["model_label"],
        "repeat": gen["repeat"], "method_index": m_idx,
    }
    try:
        payload, raw = chat_json(client, model, matcher_system, user,
                                 temperature=0.0, max_tokens=300)
        if payload is None:
            return {**key, "matched_error_index": None, "confidence": None,
                    "reason": f"parse failure: {raw[:150]}", "parse_ok": False}
        idx = payload.get("matched_error_index")
        ok = (idx is None) or isinstance(idx, int)
        return {**key, "matched_error_index": idx, "confidence": payload.get("confidence"),
                "reason": payload.get("reason", ""), "parse_ok": ok}
    except Exception as exc:  # noqa: BLE001
        return {**key, "matched_error_index": None, "confidence": None,
                "reason": f"exception: {exc}", "parse_ok": False}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    results_dir = args.results_dir if args.results_dir.is_absolute() else ROOT / args.results_dir

    prompts = yaml.safe_load(PROMPT_PATH.read_text())
    packages = load_packages()
    gt_lists = {cid: ground_truth_list(pkg) for cid, pkg in packages.items()}
    client, model = load_client()
    generations = [g for g in load_generation_records(results_dir) if g.get("status") == "ok"]

    # Judge results gate: skip candidates flagged concept_overlap (they are the
    # target concept, not prior methods, and never reach matching).
    plaus = {}
    plaus_path = results_dir / "plausibility.jsonl"
    if plaus_path.exists():
        for line in plaus_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                plaus[(r["concept_id"], r["model_label"], r["repeat"], r["method_index"])] = r

    jobs = []
    n_gated = 0
    for gen in generations:
        for m_idx, method in enumerate(gen.get("methods", [])):
            p = plaus.get((gen["concept_id"], gen["model_label"], gen["repeat"], m_idx))
            if p and p.get("concept_overlap"):
                n_gated += 1
                continue
            jobs.append((packages[gen["concept_id"]], gen, m_idx, method))

    print(f"{len(jobs)} matching judgments ({n_gated} candidates gated as concept_overlap)")

    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(match_one, client, model, prompts["MATCHER_SYSTEM"],
                            prompts["MATCHER_USER"], pkg, gt_lists[pkg["concept_id"]],
                            gen, i, m)
                for pkg, gen, i, m in jobs]
        for k, fut in enumerate(futs, 1):
            rows.append(fut.result())
            if k % 50 == 0 or k == len(futs):
                print(f"  {k}/{len(futs)}")

    n_bad = sum(1 for r in rows if not r["parse_ok"])
    out = results_dir / "matching.jsonl"
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"parse failures: {n_bad}; saved {len(rows)} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
