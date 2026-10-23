#!/usr/bin/env python3
"""Render the Section 6.3 figure: two StructPF tasks that pass all five PF Eval measures.

Sources (Study (a), pf-three-role/v3.1 evaluation):
experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/rahimi_cells_v30/
  sports_basketball_ratio__pipeline_lc__018.json
  shopping_percent__pipeline_lc__026.json
Task text is shortened; numbers, question and familiar-method ties follow the saved
task and the recorded solver attempts.

Monochrome style matching Figure 6.3.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures"
OUT_NAME = "fig6_5_structpf_examples"

C_BLACK = "#000000"
C_DARK = "#222222"
C_MID = "#4D4D4D"
C_PROC = "#CFCFCF"
C_SUB = "#E2E2E2"
C_GROUP = "#F2F2F2"
C_WHITE = "#FFFFFF"

ARROW = "\u2192"


def draw_rect(ax, x, y, w, h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.8, zorder=2):
    ax.add_patch(
        Rectangle((x, y), w, h, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, zorder=zorder)
    )


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "pdf.fonttype": 42,
        }
    )

    W, H = 12.2, 4.05
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    panels = [
        {
            "x": 0.10,
            "header": "(a) Proportional Relationships (StructPF Basketball Task 18)",
            "task": [
                ("Two shooting drills, each recorded as timed segments (minutes, points).", "normal"),
                ("Drill A:   (2, 4),   (3, 6),   (5, 10)", "data"),
                ("Drill B:   (2, 3),   (3, 8),   (5, 9)", "data"),
                ('"Which drill shows that points are proportional to minutes?"', "question"),
            ],
            "familiar_title": "Familiar Grade 6 Method (Overall Rate per Drill):",
            "familiar_body": f"A: 20 pts / 10 min = 2      B: 20 pts / 10 min = 2      {ARROW}   Tie",
            "open_title": "Left for Students (Constant Rate in Every Segment):",
            "open_body": "A: 2, 2, 2  (proportional)      B: 1.5, 2.7, 1.8  (not proportional)",
        },
        {
            "x": 6.25,
            "header": "(b) Percent Discounts (StructPF Shopping Task 26)",
            "task": [
                ("An \\$80 jacket; both stores add the same 8% sales tax.", "normal"),
                ("Store A:   20% off, then 10% off the reduced price", "data"),
                ("Store B:   30% off once", "data"),
                ('Friend: "20% off and then 10% off is the same as 30% off."', "normal"),
                ('"Which store will give you the lower final price?"', "question"),
            ],
            "familiar_title": "Familiar Shortcut (Add the Percentages):",
            "familiar_body": f"20% + 10% = 30%      {ARROW}   A = B = \\$60.48      {ARROW}   Tie",
            "open_title": "Left for Students (Second Discount on the Reduced Price):",
            "open_body": f"A: \\$80 {ARROW} \\$64 {ARROW} \\$57.60 {ARROW} \\$62.21      B: \\$80 {ARROW} \\$56 {ARROW} \\$60.48",
        },
    ]

    pw = 5.85
    for p in panels:
        x = p["x"]
        cx = x + pw / 2

        draw_rect(ax, x, 0.10, pw, 3.85, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1)
        draw_rect(ax, x, 3.53, pw, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
        ax.text(cx, 3.74, p["header"], fontsize=10.2, fontweight="bold", color=C_BLACK, ha="center", va="center", zorder=3)

        # Shortened student task
        draw_rect(ax, x + 0.20, 2.02, pw - 0.40, 1.40, facecolor=C_WHITE, zorder=2)
        ax.text(cx, 3.25, "Student Task (Shortened)", fontsize=9.3, fontweight="bold", color=C_BLACK,
                ha="center", va="center", zorder=3)
        lines = p["task"]
        top, bottom = 3.02, 2.15
        step = (top - bottom) / max(len(lines) - 1, 1)
        for i, (text, kind) in enumerate(lines):
            y = top - i * step
            if kind == "data":
                ax.text(cx, y, text, fontsize=9.1, color=C_DARK, ha="center", va="center", zorder=3)
            elif kind == "question":
                ax.text(cx, y, text, fontsize=8.9, style="italic", fontweight="bold", color=C_BLACK,
                        ha="center", va="center", zorder=3)
            else:
                ax.text(cx, y, text, fontsize=8.7, style="italic", color=C_MID, ha="center", va="center", zorder=3)

        # Familiar method that ties
        draw_rect(ax, x + 0.20, 1.30, pw - 0.40, 0.62, facecolor=C_WHITE, zorder=2)
        ax.text(cx, 1.74, p["familiar_title"], fontsize=9.1, fontweight="bold", color=C_BLACK,
                ha="center", va="center", zorder=3)
        ax.text(cx, 1.48, p["familiar_body"], fontsize=9.1, color=C_DARK, ha="center", va="center", zorder=3)

        # Key idea left for students
        draw_rect(ax, x + 0.20, 0.58, pw - 0.40, 0.62, facecolor=C_WHITE, zorder=2)
        ax.text(cx, 1.02, p["open_title"], fontsize=9.1, fontweight="bold", color=C_BLACK,
                ha="center", va="center", zorder=3)
        ax.text(cx, 0.76, p["open_body"], fontsize=9.1, color=C_DARK, ha="center", va="center", zorder=3)

        draw_rect(ax, x + 0.45, 0.17, pw - 0.90, 0.32, facecolor=C_PROC, linewidth=0.85, zorder=2)
        ax.text(cx, 0.33, "PF Eval: Yes on All Five Measures", fontsize=9.4, fontweight="bold", color=C_BLACK,
                ha="center", va="center", zorder=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"{OUT_NAME}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
    print(f"Saved {OUT_DIR}/{OUT_NAME}.{{pdf,png}}")


if __name__ == "__main__":
    main()
