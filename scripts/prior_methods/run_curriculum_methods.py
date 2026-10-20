"""Curriculum-anchored prior-methods generation (v5 redesign).

Two-step generation per concept:
  Step 1 (inventory): what was the student taught before this concept that
    deals with this kind of task?  -> curriculum tools (resources)
  Step 2 (transfer):   for each tool, apply it to the task type and report
    what it produces and how it falls short.

Step 2 uses forward execution (run a known tool), not inverse inference
(infer an error from a misconception). Validated against the expert
prior_knowledge_required lists in data/pf_exercises (expert_anticipated.json).

Usage: ./.venv/bin/python scripts/prior_methods/run_curriculum_methods.py
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


def render(tmpl: str, values: dict) -> str:
    out = tmpl
    for token, value in values.items():
        out = out.replace(token, value)
    return out


def run_step1(client, model, sys1, user1_tmpl, package):
    user = render(
        user1_tmpl,
        {
            "{grade}": str(package["grade"]),
            "{topic}": package["anchor"]["topic"],
            "{concept_text}": package["concept_text"],
        },
    )
    payload, raw = chat_json(client, model, sys1, user, temperature=0.7, max_tokens=1500)
    if payload is None or not isinstance(payload.get("tools"), list):
        return {"ok": False, "tools": [], "raw": raw[:200]}
    tools = [t for t in payload["tools"] if isinstance(t, dict) and t.get("tool")]
    return {"ok": True, "tools": tools, "raw": raw}


def run_step2(client, model, user2_tmpl, package, tool):
    user = (
        user2_tmpl.replace("{grade}", str(package["grade"]))
        .replace("{topic}", package["anchor"]["topic"])
        .replace("{concept_text}", package["concept_text"])
        .replace("{tool}", tool.get("tool", ""))
        .replace("{taught_as}", tool.get("taught_as", ""))
    )
    max_tokens = 1200 if model.startswith("gpt-5") else 600
    payload, raw = chat_json(client, model, "", user, temperature=0.7, max_tokens=max_tokens)
    if payload is None or not payload.get("what_student_does"):
        return {"ok": False, "tool": tool.get("tool"), "raw": raw[:200]}
    payload["ok"] = True
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "model",
        nargs="?",
        default="gpt41mini",
        choices=("gpt41mini", "gpt41", "gpt54", "luna"),
        help="Generator model label (default: gpt41mini).",
    )
    parser.add_argument(
        "--all-concepts",
        action="store_true",
        help="Run all frozen concept packages instead of expert-anchored concepts only.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS,
        help="Directory for the generated curriculum JSON.",
    )
    args = parser.parse_args()

    prompts = yaml.safe_load(PROMPTS_PATH.read_text())
    for key in ("CURRICULUM_STEP1_SYSTEM", "CURRICULUM_STEP1_USER", "CURRICULUM_STEP2_USER"):
        if key not in prompts:
            raise ValueError(f"missing prompt {key} in {PROMPTS_PATH}")
    sys1 = prompts["CURRICULUM_STEP1_SYSTEM"]
    user1 = prompts["CURRICULUM_STEP1_USER"]
    user2 = prompts["CURRICULUM_STEP2_USER"]

    packages = load_packages()
    # validate against the expert-anchored concepts only
    expert_path = (
        ROOT / "experiments" / "data" / "prior_methods_benchmark" / "expert_anticipated.json"
    )
    expert = json.loads(expert_path.read_text())
    target_concepts = sorted({c for e in expert for c in e["closest_benchmark_concepts"]})
    if args.all_concepts:
        target_concepts = sorted(packages)
        print("all benchmark concepts:", target_concepts)
    else:
        print("expert-anchored concepts:", target_concepts)

    client, model = load_client(args.model)
    concepts = [c for c in target_concepts if c in packages]

    all_results = {}
    with ThreadPoolExecutor(max_workers=min(4, len(concepts))) as pool:
        step1_futs = {
            pool.submit(run_step1, client, model, sys1, user1, packages[c]): c for c in concepts
        }
        step1 = {cid: fut.result() for fut, cid in step1_futs.items()}

        step2_futs = {}
        for cid, s1 in step1.items():
            print(f"\n=== {cid}: step1 tools ({len(s1['tools'])}) ===")
            for tool in s1["tools"]:
                print(f"  - {tool.get('tool')}")
                step2_futs[pool.submit(run_step2, client, model, user2, packages[cid], tool)] = (
                    cid,
                    tool,
                )

        methods_by_concept = {cid: [] for cid in concepts}
        failures_by_concept = {cid: [] for cid in concepts}
        for future, (cid, tool) in step2_futs.items():
            method = future.result()
            if method.get("ok"):
                methods_by_concept[cid].append(method)
                name = str(method.get("prior_method", "?"))[:40]
                short = str(method.get("falls_short_because", ""))[:70]
                print(f"    {cid:16s} {name:40s} -> {short}")
            else:
                failures_by_concept[cid].append(
                    {
                        "tool": tool.get("tool", ""),
                        "error": method.get("raw", ""),
                    }
                )
                print(f"    {cid:16s} [step2 failed for {tool.get('tool')}]")

        for cid in concepts:
            all_results[cid] = {
                "tools": step1[cid]["tools"],
                "prior_methods": methods_by_concept[cid],
                "step1_ok": step1[cid].get("ok", False),
                "step2_failures": failures_by_concept[cid],
                "expert_expected": [
                    {"exercise": e["exercise"], "methods": [m["name"] for m in e["methods"]]}
                    for e in expert
                    if cid in e["closest_benchmark_concepts"]
                ],
            }

    model_slug = model.replace(".", "_").replace("-", "_")
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_path = output_dir / f"curriculum_v5_{model_slug}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "concepts": all_results}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"\nsaved -> {out_path.relative_to(ROOT)}")

    # qualitative comparison to expert lists
    print("\n=== coverage vs expert lists ===")
    for cid, data in all_results.items():
        gen = {m.get("prior_method", "").lower() for m in data["prior_methods"]}
        print(f"{cid}: generated {len(gen)} prior methods")
        for ex in data["expert_expected"]:
            print(f"   expert {ex['exercise']}: {ex['methods']}")


if __name__ == "__main__":
    main()
