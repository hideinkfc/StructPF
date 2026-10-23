#!/usr/bin/env python3
"""Render Figure 6.5a: Kapur classroom student algorithms vs LLM simulated student attempts."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("thesis/figures")
BLACK, DARK_GREY, MID_GREY, LIGHT_GREY = "#000000", "#595959", "#A6A6A6", "#F4F4F4"

# Data from docs/pf-generation/PF_PIPELINE.md ("October 11: source-normalized Kapur pathway reference check", N=24 learner attempts)
ALGORITHMS = [
    ("Ratio-Based Partition\n(classroom error path)", 0),
    ("LCM / HCF Partition\n(classroom error path)", 0),
    ("Ratio-Informed Trial\n(classroom strategy)", 0),
    ("Multi-Variable Algebra\n(classroom strategy)", 0),
    ("Brute-Force Numerical Trial\n(classroom strategy)", 6),
    ("Single-Variable Algebra\n(canonical expert equation)", 19),
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
    labels = [lab for lab, _ in ALGORITHMS]
    counts = [c for _, c in ALGORITHMS]
    y = [0.0, 1.0, 2.0, 3.0, 4.35, 5.35]

    fig, ax = plt.subplots(figsize=(6.8, 3.05))

    # Shaded background band for the 4 missed classroom pathways (y = 0..3)
    ax.axhspan(-0.48, 3.48, color=LIGHT_GREY, zorder=1)
    ax.axhline(3.68, color="#666666", linestyle="--", linewidth=0.9, zorder=2)

    # Group headers on the right side of each section
    ax.text(
        24.8,
        5.98,
        "Enacted by Simulated Students (2 of 6 pathways)",
        ha="right",
        va="center",
        fontsize=8.1,
        fontweight="bold",
        color=BLACK,
        bbox=dict(boxstyle="round,pad=0.26", facecolor="#EFEFEF", edgecolor=BLACK, lw=0.75),
        zorder=4,
    )
    ax.text(
        24.8,
        3.02,
        "Missed Classroom Pathways (0 of 24 attempts)",
        ha="right",
        va="center",
        fontsize=8.1,
        fontweight="bold",
        color=DARK_GREY,
        bbox=dict(boxstyle="round,pad=0.26", facecolor="#FFFFFF", edgecolor="#888888", lw=0.75),
        zorder=4,
    )

    colors = [LIGHT_GREY, LIGHT_GREY, LIGHT_GREY, LIGHT_GREY, MID_GREY, DARK_GREY]
    ax.barh(y, counts, height=0.58, color=colors, edgecolor=BLACK, lw=0.8, zorder=3)

    for ypos, c in zip(y, counts):
        pct = 100 * c / 24
        note = f"{c} of 24 ({pct:.0f}%)"
        ax.text(
            c + 0.45,
            ypos,
            note,
            ha="left",
            va="center",
            fontsize=8.4,
            fontweight="bold" if c > 0 else "normal",
            color=BLACK if c > 0 else DARK_GREY,
            zorder=4,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.4)
    ax.set_ylim(-0.55, 6.42)
    ax.set_xlim(0, 25.5)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xlabel("Simulated student attempts enacting the pathway (out of 24)")
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"fig6_8_kapur_pathways.{ext}", bbox_inches="tight", pad_inches=0.05, **kw)
    plt.close(fig)
    print(f"Saved {OUT}/fig6_8_kapur_pathways.{{pdf,png}}")


def render_virtual_classroom() -> None:
    from matplotlib.patches import Patch, Rectangle

    BLACK = "#000000"
    DARK = "#222222"
    DARK_GREY = "#595959"
    PROC = "#CFCFCF"
    SUB = "#E2E2E2"
    GROUP = "#F2F2F2"
    LIGHT_GREY = "#EFEFEF"
    WHITE = "#FFFFFF"
    HEAD_STYLE = "-|>,head_length=0.34,head_width=0.22"

    fig = plt.figure(figsize=(12.2, 2.55), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.48, 1.0], wspace=0.25)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # ---------------- Panel (a): Procedural Setup ----------------
    W, H = 8.4, 2.55
    ax1.set_xlim(0, W)
    ax1.set_ylim(0, H)
    ax1.axis("off")

    def draw_rect(x, y, w, h, facecolor=WHITE, linewidth=0.9, zorder=2):
        ax1.add_patch(
            Rectangle((x, y), w, h, facecolor=facecolor, edgecolor=BLACK, linewidth=linewidth, zorder=zorder)
        )

    def box(x, y, w, h, title, detail=None, face=WHITE):
        draw_rect(x, y, w, h, facecolor=face, linewidth=0.85, zorder=2)
        cx = x + w / 2
        if detail is None:
            ax1.text(cx, y + h / 2, title, fontsize=7.8, fontweight="bold", color=BLACK, ha="center", va="center", zorder=3)
        else:
            ax1.text(cx, y + h * 0.66, title, fontsize=7.8, fontweight="bold", color=BLACK, ha="center", va="center", zorder=3)
            ax1.text(cx, y + h * 0.31, detail, fontsize=7.3, color=DARK, ha="center", va="center", linespacing=1.12, zorder=3)

    def arrow(x0, y0, x1, y1):
        ax1.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(arrowstyle=HEAD_STYLE, color=BLACK, lw=1.0, shrinkA=0, shrinkB=0),
            zorder=5,
        )

    # Outer container for Panel (a)
    draw_rect(0.04, 0.04, W - 0.08, H - 0.08, facecolor=GROUP, linewidth=0.95, zorder=1)
    draw_rect(0.04, H - 0.42, W - 0.08, 0.38, facecolor=SUB, linewidth=0.85, zorder=2)
    ax1.text(W / 2, H - 0.23, "(a) Matched Revision Setup (6 Tasks, Same Prompt & Budget)", fontsize=8.8, fontweight="bold", color=BLACK, ha="center", va="center", zorder=3)

    # Input box on left (centered vertically between the two horizontal paths: (1.58 + 0.56)/2 = 1.07)
    box(0.22, 0.74, 1.28, 0.66, "Initial Task", "n = 6", face=WHITE)

    # Top path: Self-Review without Simulated Students (1.94 to 6.48, width 4.54)
    box(1.94, 1.25, 4.54, 0.66, "Baseline: Self-Review (No Students)", "Revises task using only the task text", face=WHITE)

    # Bottom path: Virtual-Classroom Loop (aligned with top path: 1.94 to 6.48)
    box(1.94, 0.23, 2.15, 0.66, "Simulated Students", "8 attempts per task", face=PROC)
    box(4.33, 0.23, 2.15, 0.66, "Rewriter (+ Attempts)", "Task + Attempt Details", face=PROC)
    arrow(4.09, 0.56, 4.33, 0.56)

    # Split arrows from Initial Task (right edge 1.50) to both paths (left edge 1.94)
    ax1.plot([1.50, 1.72], [1.07, 1.07], color=BLACK, lw=1.0, zorder=4)
    ax1.plot([1.72, 1.72], [0.56, 1.58], color=BLACK, lw=1.0, zorder=4)
    arrow(1.72, 1.58, 1.94, 1.58)
    arrow(1.72, 0.56, 1.94, 0.56)

    # Output boxes on right (aligned at x = 6.72..8.18)
    box(6.72, 1.25, 1.46, 0.66, "Revised Task", "No students", face=WHITE)
    box(6.72, 0.23, 1.46, 0.66, "Revised Task", "With students", face=WHITE)
    arrow(6.48, 1.58, 6.72, 1.58)
    arrow(6.48, 0.56, 6.72, 0.56)

    # ---------------- Panel (b): Outcome Bar Plot ----------------
    conds = [
        ("Original Tasks", 5, 1, "5 of 6"),
        ("Self-Review\n(No Students)", 6, 0, "6 of 6 (13.6k tok)"),
        ("Virtual-Classroom\nFeedback", 4, 2, "4 of 6 (60.4k tok)"),
    ]
    conds_rev = list(reversed(conds))
    labels = [c[0] for c in conds_rev]
    passed = [c[1] for c in conds_rev]
    failed = [c[2] for c in conds_rev]
    notes = [c[3] for c in conds_rev]
    y = list(range(len(conds_rev)))

    ax2.barh(y, passed, height=0.52, color=DARK_GREY, edgecolor=BLACK, lw=0.75, zorder=3)
    ax2.barh(y, failed, left=passed, height=0.52, color=LIGHT_GREY, edgecolor=BLACK, lw=0.75, hatch="//", zorder=3)

    for idx, (p, f, note) in enumerate(zip(passed, failed, notes)):
        ax2.text(p / 2, idx, str(p), ha="center", va="center", color="white", fontweight="bold", fontsize=8.5, zorder=4)
        if f > 0:
            ax2.text(
                p + f / 2,
                idx,
                str(f),
                ha="center",
                va="center",
                color=BLACK,
                fontsize=8.5,
                bbox=dict(boxstyle="square,pad=0.10", facecolor="white", edgecolor="none"),
                zorder=4,
            )
        ax2.text(6.15, idx, note, ha="left", va="center", fontsize=8.0, fontweight="bold")

    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=8.3)
    ax2.set_xlim(0, 8.9)
    ax2.set_xticks([0, 2, 4, 6])
    ax2.set_xlabel("Tasks (out of 6)", fontsize=8.5)
    ax2.set_title("(b) Tasks Meeting All PF Requirements", fontsize=9.1, fontweight="bold", pad=30)
    ax2.grid(axis="x", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    for side in ("top", "right"):
        ax2.spines[side].set_visible(False)

    leg = ax2.legend(
        handles=[
            Patch(facecolor=DARK_GREY, edgecolor=BLACK, linewidth=0.75, label="Meets PF requirements"),
            Patch(facecolor=LIGHT_GREY, edgecolor=BLACK, linewidth=0.75, hatch="//", label="Broken or narrowed"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.48, 1.19),
        ncol=2,
        frameon=True,
        fancybox=False,
        edgecolor=BLACK,
        fontsize=7.6,
        columnspacing=0.9,
        handletextpad=0.4,
    )
    leg.get_frame().set_linewidth(0.8)

    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"fig6_9_virtual_classroom_feedback.{ext}", bbox_inches="tight", pad_inches=0.04, **kw)
    plt.close(fig)
    print(f"Saved {OUT}/fig6_9_virtual_classroom_feedback.{{pdf,png}}")


if __name__ == "__main__":
    main()
    render_virtual_classroom()

