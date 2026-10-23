#!/usr/bin/env python3
"""Render Figure 6.3 for Section 6.4 (30-topic curriculum-grounding study).

Horizontal stacked bar chart across the 30 Common Core progression topics
(Grades 5 to 10) for the three GPT-5 mini arms in
pf_progression_bridge_30cases_3arms_gpt5mini_20261021, using the greyed
monochrome palette of Figures 5.4 and 6.2 and the Two-Step Check labels
(Prior-Knowledge Check and Method-Failure Check).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

RESULTS = Path("experiments/results/pf_progression_bridge_30cases_3arms_gpt5mini_20261021")
OUT = Path("thesis/figures")
BLACK, DARK_GREY, MID_GREY, LIGHT_GREY = "#000000", "#595959", "#B8B8B8", "#EFEFEF"

ARMS = [
    ("direct", "One-Shot Prompt"),
    ("ungrounded", "StructPF without\nGrounding"),
    ("lc_grounded", "StructPF with\nGrounding"),
]


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "pdf.fonttype": 42,
        }
    )
    summary = json.loads((RESULTS / "summary_three_arm.json").read_text())["summary"]["arms"]

    arms_rev = list(reversed(ARMS))
    s_both = [summary[k]["score_counts"]["score_2_productive_trap"] for k, _ in arms_rev]
    s_bypass = [
        summary[k]["score_counts"]["score_1_trap_bypassed_or_off_target"] for k, _ in arms_rev
    ]
    s_leak = [summary[k]["score_counts"]["score_0_invalid_prior_set"] for k, _ in arms_rev]

    assert s_both == [19, 16, 6]
    assert s_bypass == [11, 8, 7]
    assert s_leak == [0, 6, 17]

    fig, ax = plt.subplots(figsize=(6.4, 2.35))
    y = range(len(arms_rev))
    h = 0.54

    ax.barh(y, s_both, height=h, color=DARK_GREY, edgecolor=BLACK, lw=0.75, zorder=3)
    ax.barh(
        y,
        s_bypass,
        left=s_both,
        height=h,
        color=MID_GREY,
        edgecolor=BLACK,
        lw=0.75,
        zorder=3,
    )
    ax.barh(
        y,
        s_leak,
        left=[a + b for a, b in zip(s_both, s_bypass)],
        height=h,
        color=LIGHT_GREY,
        edgecolor=BLACK,
        lw=0.75,
        hatch="//",
        zorder=3,
    )

    for idx in range(len(arms_rev)):
        if s_both[idx] >= 3:
            ax.text(
                s_both[idx] / 2,
                idx,
                f"{s_both[idx]} of 30",
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                fontsize=8.5,
                zorder=4,
            )
        if s_bypass[idx] >= 3:
            ax.text(
                s_both[idx] + s_bypass[idx] / 2,
                idx,
                f"{s_bypass[idx]} of 30",
                ha="center",
                va="center",
                color=BLACK,
                fontsize=8.5,
                zorder=4,
            )
        if s_leak[idx] >= 3:
            ax.text(
                s_both[idx] + s_bypass[idx] + s_leak[idx] / 2,
                idx,
                f"{s_leak[idx]} of 30",
                ha="center",
                va="center",
                color=BLACK,
                fontsize=8.5,
                bbox=dict(boxstyle="square,pad=0.12", facecolor="white", edgecolor="none"),
                zorder=4,
            )

    ax.set_yticks(list(y))
    ax.set_yticklabels([label for _, label in arms_rev])
    ax.set_xlim(0, 30)
    ax.set_xticks(range(0, 31, 5))
    ax.set_xlabel("Curriculum topics (of 30 across Grades 5 to 10)")
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    leg = ax.legend(
        handles=[
            Patch(
                facecolor=DARK_GREY,
                edgecolor=BLACK,
                linewidth=0.75,
                label="Both checks passed",
            ),
            Patch(
                facecolor=MID_GREY,
                edgecolor=BLACK,
                linewidth=0.75,
                label="Method-failure check failed",
            ),
            Patch(
                facecolor=LIGHT_GREY,
                edgecolor=BLACK,
                linewidth=0.75,
                hatch="//",
                label="Prior-knowledge check failed or no task",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.42),
        ncol=1,
        frameon=True,
        fancybox=False,
        edgecolor=BLACK,
        fontsize=8.2,
    )
    leg.get_frame().set_linewidth(0.8)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(
            OUT / f"fig6_4_grounding_3arms.{ext}", bbox_inches="tight", pad_inches=0.04, **kw
        )
    plt.close(fig)
    print(f"Saved {OUT}/fig6_4_grounding_3arms.{{pdf,png}}")


if __name__ == "__main__":
    main()
