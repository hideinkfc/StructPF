#!/usr/bin/env python3
"""Render Figure 4.4: Stage 3 Information Barrier and Resulting Student PF Task (6.G.A.1).

Follows the monochrome JupyRecSys style used across Chapters 3 and 4:
- #000000 borders and arrows
- #F2F2F2 stage/panel containers
- #E2E2E2 panel headers
- #CFCFCF LLM process boxes and callout tags
- #4D4D4D dark outcome banner
- #FFFFFF task cards
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures"

C_BLACK = "#000000"
C_DARK = "#222222"
C_MID = "#4D4D4D"
C_PROC = "#CFCFCF"
C_SUB = "#E2E2E2"
C_GROUP = "#F2F2F2"
C_WHITE = "#FFFFFF"


def setup_rc() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "axes.edgecolor": "none",
        }
    )


def draw_rect(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    facecolor: str = C_WHITE,
    edgecolor: str = C_BLACK,
    linewidth: float = 0.9,
    linestyle: str = "-",
    zorder: float = 2,
):
    patch = Rectangle(
        (x, y),
        w,
        h,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        linestyle=linestyle,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_round_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    facecolor: str = C_WHITE,
    edgecolor: str = C_BLACK,
    linewidth: float = 0.9,
    linestyle: str = "-",
    pad: float = 0.05,
    zorder: float = 2,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.01,rounding_size={pad}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        linestyle=linestyle,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_arrow(
    ax,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    lw: float = 1.05,
    style: str = "-|>,head_length=0.28,head_width=0.17",
    linestyle: str = "-",
    zorder: float = 6,
) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle=style,
            color=C_BLACK,
            lw=lw,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=zorder,
    )


def render_fig4_4() -> None:
    setup_rc()
    W, H = 12.4, 3.60
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # ==========================================================================
    # Panel (a): Stage 3 Information Barrier & Task Writer
    # ==========================================================================
    p1_x, p1_y, p1_w, p1_h = 0.08, 0.10, 4.45, 3.40
    draw_rect(
        ax, p1_x, p1_y, p1_w, p1_h, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax,
        p1_x,
        p1_y + p1_h - 0.42,
        p1_w,
        0.42,
        facecolor=C_SUB,
        edgecolor=C_BLACK,
        linewidth=0.85,
        zorder=2,
    )
    ax.text(
        p1_x + p1_w / 2,
        p1_y + p1_h - 0.21,
        "(a) Stage 3 Information Barrier & Writer",
        fontsize=9.1,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # Box 1 (Top): Withheld Across Information Barrier
    draw_rect(
        ax,
        0.24,
        2.04,
        4.13,
        0.90,
        facecolor=C_WHITE,
        edgecolor=C_BLACK,
        linewidth=0.85,
        linestyle="--",
        zorder=2,
    )
    draw_rect(
        ax, 0.24, 2.62, 4.13, 0.32, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.8, zorder=3
    )
    ax.text(
        2.305,
        2.78,
        "Withheld Across Information Barrier",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        0.34,
        2.33,
        "• Internal Solution Notes: Key idea, ½ bh, routes, areas (90, 84)\n"
        "• Five-Dimension Evaluation Rubric: Withheld so writer does not\n"
        "  append representation menus or 4-part worksheets (Chapter 3)",
        fontsize=7.20,
        color=C_DARK,
        ha="left",
        va="center",
        linespacing=1.20,
        zorder=4,
    )

    # Box 2 (Middle): Passed to Task Writer
    draw_rect(
        ax, 0.24, 0.96, 4.13, 0.94, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    draw_rect(
        ax, 0.24, 1.58, 4.13, 0.32, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.8, zorder=3
    )
    ax.text(
        2.305,
        1.74,
        "Passed to Stage 3 Task Writer",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        0.34,
        1.27,
        "• Student-Facing Setup: Play-area comparison & volunteer claim\n"
        "• Verified Given Values: Outer 12, 8; Corner cuts 4, 3, 5 and 4, 3\n"
        "• Open-Prompt Rule: State boundary facts; ask 1 open question",
        fontsize=7.25,
        color=C_DARK,
        ha="left",
        va="center",
        linespacing=1.20,
        zorder=4,
    )

    # Downward arrow from Passed inputs to Stage 3 Writer
    draw_arrow(ax, 2.305, 0.96, 2.305, 0.74, lw=1.0)

    # Stage 3 LLM Process Box at bottom of Panel (a)
    draw_round_box(
        ax, 0.24, 0.22, 4.13, 0.52, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=3
    )
    ax.text(
        2.305,
        0.48,
        "Stage 3: Write Student Task (≤ 2 rev.)\nChecks: All given values present; no formula or splitting hint",
        fontsize=7.25,
        fontweight="bold",
        ha="center",
        va="center",
        linespacing=1.20,
        zorder=4,
    )

    # Arrow from Panel (a) to Panel (b)
    draw_arrow(ax, 4.53, 1.80, 4.88, 1.80, lw=1.15)

    # ==========================================================================
    # Panel (b): Resulting Student-Facing Task ("Two Play-Area Floor Designs")
    # ==========================================================================
    p2_x, p2_y, p2_w, p2_h = 4.88, 0.10, 7.44, 3.40
    draw_rect(
        ax, p2_x, p2_y, p2_w, p2_h, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax,
        p2_x,
        p2_y + p2_h - 0.42,
        p2_w,
        0.42,
        facecolor=C_SUB,
        edgecolor=C_BLACK,
        linewidth=0.85,
        zorder=2,
    )
    ax.text(
        p2_x + p2_w / 2,
        p2_y + p2_h - 0.21,
        '(b) Generated Student PF Task for 6.G.A.1: "Two Play-Area Floor Designs" (158 Words)',
        fontsize=9.0,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # Left sub-card inside Panel (b): Excerpt of Student Task Text
    tx, ty, tw, th = 5.04, 0.76, 4.74, 2.18
    draw_rect(ax, tx, ty, tw, th, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)

    # Paragraph 1: Given Geometry
    draw_rect(
        ax,
        tx + 0.10,
        ty + 1.24,
        tw - 0.20,
        0.84,
        facecolor=C_GROUP,
        edgecolor=C_BLACK,
        linewidth=0.75,
        zorder=3,
    )
    ax.text(
        tx + 0.18,
        ty + 1.66,
        "Problem Setup & Given Dimensions:\n"
        '"Both designs fit inside an outer rectangle that is 12 units long and\n'
        "8 units wide. In Design A, a corner is removed... bounded by perpendicular\n"
        "sides of lengths 4 units and 3 units and a slanted side of length 5 units.\n"
        'In Design B, a rectangular corner of 4 units by 3 units is removed."',
        fontsize=7.05,
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.16,
        zorder=4,
    )

    # Paragraph 2: Volunteer Conjecture & Open Question
    draw_rect(
        ax,
        tx + 0.10,
        ty + 0.10,
        tw - 0.20,
        1.04,
        facecolor=C_PROC,
        edgecolor=C_BLACK,
        linewidth=0.85,
        zorder=3,
    )
    ax.text(
        tx + 0.18,
        ty + 0.62,
        "Shortcut Conjecture & Single Open Question:\n"
        '"A volunteer conjectures that the designs have the same usable area\n'
        "because their outer rectangles match.\n"
        "Question: Which design should the parks team choose for more usable\n"
        'floor space, and what is each usable area? Show your reasoning."',
        fontsize=6.95,
        fontweight="bold",
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.18,
        zorder=4,
    )

    # Right annotations inside Panel (b): Why Each Part Preserves PF
    rx, rw = 10.02, 2.14
    draw_arrow(ax, tx + tw, ty + 1.66, rx, ty + 1.66, lw=1.0)
    draw_rect(
        ax, rx, ty + 1.24, rw, 0.84, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        rx + rw / 2,
        ty + 1.66,
        "Support, Not Giveaway\nStates boundary lengths\n(12, 8, 4, 3, 5) without\nnaming ½ bh or splitting",
        fontsize=7.15,
        color=C_DARK,
        ha="center",
        va="center",
        linespacing=1.18,
        zorder=3,
    )

    draw_arrow(ax, tx + tw, ty + 0.62, rx, ty + 0.62, lw=1.0)
    draw_rect(
        ax, rx, ty + 0.10, rw, 1.04, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        rx + rw / 2,
        ty + 0.62,
        "Open Student Invention\nTests outer-box trap\n(96 = 96) in 1 open prompt\ninstead of a worksheet",
        fontsize=7.15,
        color=C_DARK,
        ha="center",
        va="center",
        linespacing=1.18,
        zorder=3,
    )

    # Bottom banner inside Panel (b)
    draw_rect(
        ax, 5.04, 0.22, 7.12, 0.44, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    ax.text(
        8.60,
        0.44,
        "Contrast with Chapter 3 One-Shot Garden Tasks: 0 pre-split shapes, 0 formula hints, 1 open question",
        fontsize=7.65,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=4,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(
            OUT_DIR / f"fig4_4_stage3_task_writer.{ext}",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.03,
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    render_fig4_4()
    print("Rendered fig4_4_stage3_task_writer.{pdf,png}")
