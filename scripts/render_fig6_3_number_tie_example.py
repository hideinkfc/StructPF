#!/usr/bin/env python3
"""Render Figure 6.3: Side-by-side comparison of untied One-Shot numbers vs. tied PF numbers
in the Music setting (showing why a familiar Grade 6 average solves the task unless the numbers tie).

Monochrome style matching Figures 3.3 and 6.1.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures"

C_BLACK = "#000000"
C_DARK = "#222222"
C_MID = "#4D4D4D"
C_PROC = "#CFCFCF"
C_SUB = "#E2E2E2"
C_GROUP = "#F2F2F2"
C_WHITE = "#FFFFFF"


def draw_rect(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    facecolor: str = C_WHITE,
    edgecolor: str = C_BLACK,
    linewidth: float = 0.9,
    zorder: float = 2,
):
    patch = Rectangle(
        (x, y),
        w,
        h,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "pdf.fonttype": 42,
        }
    )

    W, H = 12.2, 3.15
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    panels = [
        {
            "x": 0.10,
            "w": 5.85,
            "header": "(a) Untied Numbers (GPT-5 mini One-Shot Music Task 4)",
            "header_fill": C_PROC,
            "question": 'Question: "Which band has longer typical songs?"',
            "band_a": "Band A (Skyline):  12 songs   \u2192   Average = 417.5 sec",
            "band_b": "Band B (Midnight): 12 songs   \u2192   Average = 359.0 sec",
            "note": "The two averages already differ (417.5 vs. 359.0 sec)",
            "step_title": "Familiar Grade 6 Method (Take the Average):",
            "step_body": "417.5 sec > 359.0 sec   \u2192   Picks Band A right away",
            "badge": "Result: Familiar Method Succeeds (Limits = No)",
            "badge_fill": C_MID,
            "badge_fg": C_WHITE,
        },
        {
            "x": 6.25,
            "w": 5.85,
            "header": "(b) Tied Numbers (StructPF Music Task 1)",
            "header_fill": C_SUB,
            "question": 'Question: "Which band\'s songs tend to be longer?"',
            "band_a": "Band A:  2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3 min   \u2192   Average = 3.0 min",
            "band_b": "Band B:  1.8, 1.9, 2.0, 2.2, 2.3, 2.6, 8.2 min   \u2192   Average = 3.0 min",
            "note": "One 8.2 min outlier pulls Band B's average up to match Band A",
            "step_title": "Familiar Grade 6 Method (Take the Average):",
            "step_body": "3.0 min = 3.0 min (Tie!)   \u2192   Must compare spread and median",
            "badge": "Result: Familiar Method Falls Short (Limits = Yes)",
            "badge_fill": C_PROC,
            "badge_fg": C_BLACK,
        },
    ]

    for p in panels:
        x, w = p["x"], p["w"]
        cx = x + w / 2

        # Outer container + header
        draw_rect(ax, x, 0.10, w, 2.95, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1)
        draw_rect(ax, x, 2.63, w, 0.42, facecolor=p["header_fill"], edgecolor=C_BLACK, linewidth=0.85, zorder=2)
        ax.text(cx, 2.84, p["header"], fontsize=10.2, fontweight="bold", color=C_BLACK, ha="center", va="center", zorder=3)

        # Given numbers box
        draw_rect(ax, x + 0.20, 1.48, w - 0.40, 1.03, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.8, zorder=2)
        ax.text(cx, 2.33, p["question"], fontsize=9.3, fontweight="bold", color=C_BLACK, ha="center", va="center", zorder=3)
        ax.text(cx, 2.04, p["band_a"], fontsize=9.1, color=C_DARK, ha="center", va="center", zorder=3)
        ax.text(cx, 1.80, p["band_b"], fontsize=9.1, color=C_DARK, ha="center", va="center", zorder=3)
        ax.text(cx, 1.59, p["note"], fontsize=8.5, style="italic", color=C_MID, ha="center", va="center", zorder=3)

        # Familiar method box
        draw_rect(ax, x + 0.20, 0.72, w - 0.40, 0.64, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.8, zorder=2)
        ax.text(cx, 1.17, p["step_title"], fontsize=9.1, fontweight="bold", color=C_BLACK, ha="center", va="center", zorder=3)
        ax.text(cx, 0.90, p["step_body"], fontsize=9.2, color=C_DARK, ha="center", va="center", zorder=3)

        # Bottom result badge
        draw_rect(ax, x + 0.45, 0.20, w - 0.90, 0.40, facecolor=p["badge_fill"], edgecolor=C_BLACK, linewidth=0.85, zorder=2)
        ax.text(cx, 0.40, p["badge"], fontsize=9.4, fontweight="bold", color=p["badge_fg"], ha="center", va="center", zorder=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(
            OUT_DIR / f"fig6_4_number_tie_example.{ext}",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.03,
            facecolor="white",
        )
    plt.close(fig)
    print(f"Saved {OUT_DIR}/fig6_4_number_tie_example.{{pdf,png}}")


if __name__ == "__main__":
    main()
