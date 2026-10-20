"""Build an interactive review markdown for v5 prior-method verification.

Joins the full v5 generation outputs (method text) with the Luna evaluation
(fitness verdicts + expert-coverage matches) into one markdown the user edits
directly: tick accept/reject per method, fix the falls_short text, add notes.

Output: experiments/results/prior_methods_benchmark/v5_review.md

Usage: ./.venv/bin/python scripts/prior_methods/build_review_md.py [generator]
       default generator: gpt-5.6-luna (highest fitness rate)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prior_methods.common import load_packages  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GEN_DIR = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "full_v5_all_concepts_v2"
EVAL = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "v5_eval_full_luna_v2.json"
OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "v5_review.md"

MODEL_FILES = {
    "gpt-4.1": "curriculum_v5_gpt_4_1.json",
    "gpt-4.1-mini": "curriculum_v5_gpt_4_1_mini.json",
    "gpt-5.4": "curriculum_v5_gpt_5_4.json",
    "gpt-5.6-luna": "curriculum_v5_gpt_5_6_luna.json",
}


def main() -> None:
    generator = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-luna"
    gen = json.loads((GEN_DIR / MODEL_FILES[generator]).read_text())
    ev = json.loads(EVAL.read_text())["by_generator"][generator]
    packages = load_packages()

    lines = []
    lines.append("# V5 Prior-Method Review")
    lines.append("")
    lines.append(f"Generator: **{generator}** — edit the `Verdict` and `My note` fields.")
    lines.append(
        "Verdict values: `accept` / `reject` / `fix`. If `fix`, rewrite the falls_short line."
    )
    lines.append("")

    for cid, cdata in gen["concepts"].items():
        evc = ev.get(cid, {})
        concept_text = packages.get(cid, {}).get("concept_text", "")
        lines.append(f"## {cid}")
        lines.append("")
        if concept_text:
            lines.append(f"**Hidden concept:** {concept_text}")
            lines.append("")
        # expert list if any
        expert = cdata.get("expert_expected", [])
        if expert:
            exp_names = [m for e in expert for m in e["methods"]]
            lines.append(f"**Expert-anticipated methods ({len(exp_names)}):**")
            for name in exp_names:
                lines.append(f"- {name}")
            lines.append("")
        fitness = evc.get("fitness", {})
        for i, m in enumerate(cdata.get("prior_methods", [])):
            fit = fitness.get(str(i), {})
            verdict = fit.get("fitness")
            reason = fit.get("reason", "")
            lines.append(f"### [{cid}#{i}] {m.get('prior_method', '?')}")
            lines.append("")
            lines.append(f"- **Taught as:** {m.get('taught_as', '')}")
            lines.append(f"- **Student does:** {m.get('what_student_does', '')}")
            lines.append(f"- **Falls short because:** {m.get('falls_short_because', '')}")
            lines.append(f"- **Luna fitness:** {verdict} — {reason}")
            lines.append("- **Verdict:** ")
            lines.append("- **My note:** ")
            lines.append("")

    OUT.write_text("\n".join(lines) + "\n")
    n_methods = sum(len(c["prior_methods"]) for c in gen["concepts"].values())
    print(f"generator={generator}  concepts={len(gen['concepts'])}  methods={n_methods}")
    print(f"saved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
