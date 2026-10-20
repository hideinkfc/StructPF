"""Evaluate v5 curriculum-anchored prior methods against expert ground truth.

Two judges (GPT-5.6-luna by default):
  - coverage: expert method -> is it covered by any generated method?
  - fitness:  is falls_short_because correct / wrong / vague?

Reads curriculum_v5_<model>.json files, writes v5_eval.json. Reports, per model
and per expert-anchored concept: expert-recall (covered expert methods / total),
fitness distribution, and a qualitative table.

Usage: ./.venv/bin/python scripts/prior_methods/eval_curriculum_v5.py [judge_model]
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prior_methods.common import (  # noqa: E402
    RESULTS,
    ROOT,
    chat_json,
    load_client,
    load_packages,
)

PROMPTS_PATH = ROOT / "src" / "generation" / "prompts" / "prior_methods.yaml"
OUT = RESULTS / "v5_eval.json"
WORKERS = 8
COVERAGE_MAX_TOKENS = 1000
FITNESS_MAX_TOKENS = 800


def render(tmpl: str, values: dict) -> str:
    out = tmpl
    for token, value in values.items():
        out = out.replace(token, value)
    return out


def generated_methods_str(methods: list[dict]) -> str:
    lines = []
    for i, method in enumerate(methods):
        lines.append(
            f"[{i}] Tool: {method.get('prior_method', '')}\n"
            f"    Taught as: {method.get('taught_as', '')}\n"
            f"    What the student does: {method.get('what_student_does', '')}"
        )
    return "\n".join(lines)


def judge_coverage(client, model, prompts, package, expert_method, generated_methods):
    user = render(
        prompts["V5_COVERAGE_USER"],
        {
            "{concept_text}": package["concept_text"],
            "{expert_method}": expert_method,
            "{generated_methods}": generated_methods_str(generated_methods),
        },
    )
    payload, raw = chat_json(
        client,
        model,
        prompts["V5_COVERAGE_SYSTEM"],
        user,
        temperature=0.0,
        max_tokens=COVERAGE_MAX_TOKENS,
    )
    if payload is None:
        return {
            "matched_generated_index": None,
            "confidence": None,
            "reason": f"parse fail: {raw[:120]}",
            "parse_ok": False,
        }
    idx = payload.get("matched_generated_index")
    ok = (idx is None) or (isinstance(idx, int) and 0 <= idx < len(generated_methods))
    return {
        "matched_generated_index": idx,
        "confidence": payload.get("confidence"),
        "reason": payload.get("reason", ""),
        "parse_ok": ok,
    }


def judge_fitness(client, model, prompts, package, method):
    user = render(
        prompts["V5_FITNESS_USER"],
        {
            "{concept_text}": package["concept_text"],
            "{topic}": package["anchor"]["topic"],
            "{prior_method}": method.get("prior_method", ""),
            "{taught_as}": method.get("taught_as", ""),
            "{what_student_does}": method.get("what_student_does", ""),
            "{falls_short_because}": method.get("falls_short_because", ""),
        },
    )
    payload, raw = chat_json(
        client,
        model,
        prompts["V5_FITNESS_SYSTEM"],
        user,
        temperature=0.0,
        max_tokens=FITNESS_MAX_TOKENS,
    )
    if payload is None:
        return {"fitness": None, "reason": f"parse fail: {raw[:120]}", "parse_ok": False}
    fit = payload.get("fitness")
    ok = fit in ("correct", "wrong", "vague")
    return {"fitness": fit, "reason": payload.get("reason", ""), "parse_ok": ok}


def eval_one_file(client, judge_model, prompts, packages, path: Path):
    data = json.loads(path.read_text())
    gen_model = data["model"]
    results = {}
    for cid, cdata in data["concepts"].items():
        if cid not in packages:
            continue
        package = packages[cid]
        expert_methods = []
        for ex in cdata.get("expert_expected", []):
            expert_methods.extend(ex["methods"])
        methods = cdata.get("prior_methods", [])
        if not methods:
            results[cid] = {"skipped": True, "reason": "no generated methods"}
            continue

        cov_futs, fit_futs = {}, {}
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for expert_index, expert_method in enumerate(expert_methods):
                cov_futs[
                    pool.submit(
                        judge_coverage,
                        client,
                        judge_model,
                        prompts,
                        package,
                        expert_method,
                        methods,
                    )
                ] = expert_index
            for i, m in enumerate(methods):
                fit_futs[pool.submit(judge_fitness, client, judge_model, prompts, package, m)] = i
            cov = {cov_futs[f]: f.result() for f in cov_futs}
            fit = {fit_futs[f]: f.result() for f in fit_futs}

        covered = {
            expert_index
            for expert_index, result in cov.items()
            if result.get("parse_ok") and result.get("matched_generated_index") is not None
        }
        for expert_index, result in cov.items():
            result["expert_index"] = expert_index
            result["expert_method"] = expert_methods[expert_index]
            generated_index = result.get("matched_generated_index")
            if isinstance(generated_index, int) and 0 <= generated_index < len(methods):
                result["matched_generated_method"] = methods[generated_index]
        n_fit = len(fit)
        fit_counts = {
            k: sum(1 for v in fit.values() if v["fitness"] == k)
            for k in ("correct", "wrong", "vague")
        }
        results[cid] = {
            "n_generated": len(methods),
            "n_expert_methods": len(expert_methods),
            "expert_recall": (
                round(len(covered) / len(expert_methods), 3) if expert_methods else None
            ),
            "covered_expert_indices": sorted(covered),
            "fitness_counts": fit_counts,
            "fitness_correct_rate": round(fit_counts["correct"] / n_fit, 3) if n_fit else None,
            "coverage": cov,
            "fitness": fit,
        }
    return gen_model, results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "judge_model",
        nargs="?",
        default="luna",
        choices=("gpt41mini", "gpt41", "gpt54", "luna"),
    )
    parser.add_argument(
        "--generation-dir",
        type=Path,
        default=RESULTS,
        help="Directory containing curriculum_v5_*.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: v5_eval_expert_first_<judge>_v4.json).",
    )
    args = parser.parse_args()
    which = args.judge_model
    prompts = yaml.safe_load(PROMPTS_PATH.read_text())
    packages = load_packages()
    client, judge_model = load_client(which)

    generation_dir = args.generation_dir
    if not generation_dir.is_absolute():
        generation_dir = ROOT / generation_dir
    files = sorted(generation_dir.glob("curriculum_v5_*.json"))
    print(f"evaluating {len(files)} generation files with judge={judge_model}")

    all_out = {}
    for path in files:
        gen_model, results = eval_one_file(client, judge_model, prompts, packages, path)
        all_out[gen_model] = results
        print(f"\n=== generator {gen_model} ===")
        for cid, r in results.items():
            if r.get("skipped"):
                print(f"  {cid}: skipped ({r['reason']})")
                continue
            print(
                f"  {cid}: expert_recall={r['expert_recall']} "
                f"({len(r['covered_expert_indices'])}/{r['n_expert_methods']}) "
                f"fitness correct={r['fitness_correct_rate']} {r['fitness_counts']}"
            )

    output_path = args.output
    if output_path is None:
        output_path = RESULTS / f"v5_eval_expert_first_{which}_v4.json"
    elif not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.write_text(
        json.dumps(
            {
                "judge_model": judge_model,
                "coverage_direction": "expert_to_generated",
                "coverage_max_tokens": COVERAGE_MAX_TOKENS,
                "fitness_max_tokens": FITNESS_MAX_TOKENS,
                "by_generator": all_out,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"\nsaved -> {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
