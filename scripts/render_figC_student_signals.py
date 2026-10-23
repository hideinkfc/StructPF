#!/usr/bin/env python3
"""Render the two appendix plots on student signals not used for generation.

(a) Eedi coverage pilot: student-weighted share of wrong answers reached by
    each system on 68 text-answerable items, against the best share possible
    with the same number of answers (pf_eedi_coverage_20261016/summary.json).
(b) Simulated students: intended-path reach on the unchanged fair-division
    task under two LLMs (0/8 GPT-4.1, 4/4 GPT-5.4), recorded in
    docs/pf-generation/PF_PIPELINE.md "Final findings and thesis boundary".
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

EEDI = Path("experiments/results/pf_eedi_coverage_20261016/summary.json")
OUT = Path("thesis/figures")
BLACK, DARK_GREY, LIGHT_GREY = "#000000", "#595959", "#EFEFEF"

SYSTEMS = [
    ("solver_luna", "GPT-5.6-luna\nsolver"),
    ("solver_gpt41", "GPT-4.1\nsolver"),
    ("direct", "Single LLM\ncall"),
    ("pf_solver", "Pooled\nsolvers"),
]
SIM = [("GPT-4.1", 0, 8), ("GPT-5.4", 4, 4)]


def style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "pdf.fonttype": 42,
        }
    )
    systems = json.loads(EEDI.read_text())["systems"]
    reached = [100 * systems[k]["means"]["value_weighted"] for k, _ in SYSTEMS]
    best = [100 * systems[k]["means"]["oracle_top_k_weighted"] for k, _ in SYSTEMS]
    assert [round(v, 1) for v in reached] == [13.6, 14.0, 13.2, 17.5]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.6), gridspec_kw={"width_ratios": [2.3, 1]})

    x = range(len(SYSTEMS))
    w = 0.36
    ax1.bar([i - w / 2 for i in x], reached, w, color=DARK_GREY, edgecolor=BLACK, lw=0.75, zorder=3)
    ax1.bar(
        [i + w / 2 for i in x],
        best,
        w,
        color=LIGHT_GREY,
        edgecolor=BLACK,
        lw=0.75,
        hatch="//",
        zorder=3,
    )
    for i, v in enumerate(reached):
        ax1.text(i - w / 2, v + 2, f"{v:.0f}%", ha="center", va="bottom", fontsize=8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([label for _, label in SYSTEMS], fontsize=8)
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Wrong-answer students (%)")
    ax1.set_title("(a) Eedi Wrong Answers Reached", fontsize=9, fontweight="bold")
    ax1.legend(
        handles=[
            Patch(facecolor=DARK_GREY, edgecolor=BLACK, linewidth=0.75, label="Reached"),
            Patch(
                facecolor=LIGHT_GREY,
                edgecolor=BLACK,
                linewidth=0.75,
                hatch="//",
                label="Best possible",
            ),
        ],
        loc="upper left",
        frameon=True,
        fancybox=False,
        edgecolor=BLACK,
        fontsize=7.5,
    ).get_frame().set_linewidth(0.8)
    style(ax1)

    shares = [100 * k / n for _, k, n in SIM]
    ax2.bar(range(len(SIM)), shares, 0.55, color=DARK_GREY, edgecolor=BLACK, lw=0.75, zorder=3)
    for i, (_, k, n) in enumerate(SIM):
        ax2.text(i, shares[i] + 2, f"{k} of {n}", ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(range(len(SIM)))
    ax2.set_xticklabels([name for name, _, _ in SIM], fontsize=8)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Replies reaching intended path (%)")
    ax2.set_title("(b) Simulated Students", fontsize=9, fontweight="bold")
    style(ax2)

    fig.tight_layout(w_pad=2.0)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"figC_student_signals.{ext}", bbox_inches="tight", pad_inches=0.04, **kw)
    plt.close(fig)
    print(f"Saved {OUT}/figC_student_signals.{{pdf,png}}")


if __name__ == "__main__":
    main()
