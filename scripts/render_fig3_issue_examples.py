#!/usr/bin/env python3
"""Render Figures 3.3–3.6: Compact JupyRecSys-style intuitive diagrams for each one-shot PF failure pattern in Section 3.2.

- fig3_3_impasse_example.{pdf,png}: Section 3.2.1 (GPT-4.1 Home & Garden Task 2, 10.0/15)
- fig3_4_giveaway_example.{pdf,png}: Section 3.2.2 (GPT-5 mini Basketball Task 21, 15.0/15)
- fig3_5_worksheet_example.{pdf,png}: Section 3.2.3 (GPT-5 mini Home & Garden Task 1, 14.0/15)
- fig3_6_math_error_example.{pdf,png}: Section 3.2.4 (GPT-5 mini Home & Garden Task 28, 15.0/15)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

OUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures"

# Monochrome / JupyRecSys palette (matching Fig 3.1 and Fig 3.2)
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
    hatch: str | None = None,
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
        hatch=hatch,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_poly(
    ax,
    pts: list[tuple[float, float]],
    facecolor: str = C_WHITE,
    edgecolor: str = C_BLACK,
    linewidth: float = 0.9,
    linestyle: str = "-",
    zorder: float = 2,
):
    patch = Polygon(
        pts,
        closed=True,
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
    color: str = C_BLACK,
    lw: float = 1.05,
    style: str = "-|>,head_length=0.32,head_width=0.19",
    linestyle: str = "-",
    zorder: float = 5,
) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle=style,
            color=color,
            lw=lw,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=zorder,
    )


def save_fig(fig, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(
            OUT_DIR / f"{stem}.{ext}",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.03,
            facecolor="white",
        )
    plt.close(fig)


# ==============================================================================
# Figure 3.3: Familiar Methods Remove the Impasse (GPT-4.1 Garden Task 2)
# ==============================================================================
def render_fig3_3() -> None:
    W, H = 12.4, 3.10
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Left container: What PF Needs
    draw_rect(
        ax, 0.10, 0.10, 3.55, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 0.10, 2.58, 3.55, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        1.875,
        2.79,
        "(a) Intended PF Design",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # Unsplit composite polygon inside white card
    draw_rect(
        ax, 0.26, 0.68, 3.23, 1.74, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    pts_pf = [
        (0.58, 0.98),
        (2.48, 0.98),
        (2.48, 1.32),
        (3.12, 1.32),
        (3.12, 1.76),
        (1.85, 2.26),
        (0.58, 1.76),
    ]
    draw_poly(ax, pts_pf, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=1.05, zorder=3)
    ax.text(
        1.82,
        1.50,
        "Unsplit Composite Shape\n(Outer boundary only)",
        fontsize=8.2,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        1.875,
        0.38,
        "Students must decide where to\nsplit or subtract shapes",
        fontsize=8.3,
        color=C_DARK,
        ha="center",
        va="center",
    )

    # Center container: What Task 2 Gives
    draw_rect(
        ax, 3.95, 0.10, 4.75, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 3.95, 2.58, 4.75, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        6.325,
        2.79,
        "(b) GPT-4.1 Garden Task 2 (Score: 10.0 / 15)",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    draw_rect(
        ax, 4.13, 0.68, 4.39, 1.74, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    # Pre-split Piece 1: Rectangle 10m x 6m
    draw_rect(
        ax, 4.30, 1.24, 1.55, 0.96, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=3
    )
    ax.text(
        5.075,
        1.72,
        "1. Rectangle\n10 m × 6 m",
        fontsize=8.2,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    # Pre-split Piece 2: Triangle base 6m, height 4m
    draw_poly(
        ax,
        [(6.02, 1.24), (7.38, 1.24), (6.70, 2.22)],
        facecolor=C_SUB,
        edgecolor=C_BLACK,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        6.70,
        1.50,
        "2. Triangle\nb = 6, h = 4 m",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    # Pre-split Piece 3: Square 3m x 3m
    draw_rect(
        ax, 7.54, 1.24, 0.82, 0.82, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.95, zorder=3
    )
    ax.text(
        7.95,
        1.65,
        "3. Square\n3 × 3 m",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )

    ax.text(
        6.325,
        0.94,
        "Task lists three separate shapes with every base and height",
        fontsize=8.1,
        color=C_DARK,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        6.325,
        0.38,
        "Every piece matches a known Grade 6 formula\n(nothing left for the student to decompose)",
        fontsize=8.3,
        color=C_DARK,
        ha="center",
        va="center",
    )

    # Arrow from (b) to (c)
    draw_arrow(ax, 8.70, 1.55, 9.05, 1.55, lw=1.15)

    # Right container: Routine Calculation Outcome
    draw_rect(
        ax, 9.05, 0.10, 3.25, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 9.05, 2.58, 3.25, 0.42, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        10.675,
        2.79,
        "(c) Student Solution Path",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    draw_rect(
        ax, 9.23, 0.80, 2.89, 1.62, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        10.675,
        1.61,
        "Direct Grade 6 Formulas:\n"
        "• Rect: 10 × 6 = 60 m²\n"
        "• Tri: ½ × 6 × 4 = 12 m²\n"
        "• Square: 3 × 3 = 9 m²\n"
        "Total = 60 + 12 + 9 = 81 m²",
        fontsize=8.4,
        color=C_BLACK,
        ha="center",
        va="center",
        linespacing=1.32,
        zorder=3,
    )
    draw_rect(
        ax, 9.23, 0.22, 2.89, 0.44, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    ax.text(
        10.675,
        0.44,
        "Result: Solved with Familiar Methods",
        fontsize=8.3,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=4,
    )

    save_fig(fig, "fig3_3_impasse_example")


# ==============================================================================
# Figure 3.4: Wording Gives Away Target & Method (GPT-5 mini Basketball Task 21)
# ==============================================================================
def render_fig3_4() -> None:
    W, H = 12.4, 3.20
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Left container: Generated Task Excerpts
    draw_rect(
        ax, 0.10, 0.10, 7.35, 3.00, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 0.10, 2.68, 7.35, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        3.775,
        2.89,
        "(a) GPT-5 mini Basketball Task 21 Prompt Text (Rubric Score: 15.0 / 15)",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # Small data card at left
    draw_rect(
        ax, 0.26, 0.26, 2.15, 2.26, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    draw_rect(
        ax, 0.26, 2.14, 2.15, 0.38, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.8, zorder=3
    )
    ax.text(
        1.335,
        2.33,
        "Given Drill Data",
        fontsize=8.5,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        1.335,
        1.20,
        "Drill A (Spot-Up 3s):\n"
        "  6 min → 9 shots\n"
        " 12 min → 18 shots\n"
        " 18 min → 27 shots\n\n"
        "Drill B (Off-Dribble):\n"
        "  5 min → 8 shots\n"
        " 10 min → 15 shots\n"
        " 15 min → 22 shots",
        fontsize=8.0,
        color=C_DARK,
        ha="center",
        va="center",
        linespacing=1.24,
        zorder=4,
    )

    # Three quoted giveaway boxes in the prompt
    bx, bw = 2.56, 4.72
    # Box 1: Classroom cue
    draw_rect(
        ax, bx, 1.92, bw, 0.60, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        bx + 0.14,
        2.22,
        'Body: "You have recently practiced computing unit rates...\n'
        'not yet teaching you a formal rule for proportional relationships."',
        fontsize=8.0,
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.25,
        zorder=3,
    )
    # Box 2: Target giveaway
    draw_rect(ax, bx, 1.12, bw, 0.64, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=2)
    ax.text(
        bx + 0.14,
        1.44,
        'Question Part 1: "For each drill (A, B, and C), decide whether\n'
        'the number of made 3s is proportional to the time."',
        fontsize=8.1,
        fontweight="bold",
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.25,
        zorder=3,
    )
    # Box 3: Method list giveaway
    draw_rect(ax, bx, 0.26, bw, 0.70, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=2)
    ax.text(
        bx + 0.14,
        0.61,
        'Question Part 2: "Possible representations include: unit-rate\n'
        "calculations, tables of equivalent pairs, repeated addition,\n"
        'number-line reasoning, or a sketched graph."',
        fontsize=8.0,
        fontweight="bold",
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.22,
        zorder=3,
    )

    # Arrows to right container
    draw_arrow(ax, bx + bw, 2.22, 7.80, 2.22, lw=1.05)
    draw_arrow(ax, bx + bw, 1.44, 7.80, 1.44, lw=1.05)
    draw_arrow(ax, bx + bw, 0.61, 7.80, 0.61, lw=1.05)

    # Right container: Diagnosis & Rubric Effect
    draw_rect(
        ax, 7.80, 0.10, 4.50, 3.00, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 7.80, 2.68, 4.50, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        10.05,
        2.89,
        "(b) Effect on Student vs. Rubric Judge",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    rx, rw = 7.98, 4.14
    draw_rect(
        ax, rx, 1.92, rw, 0.60, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        rx + rw / 2,
        2.22,
        "1. Classroom Practice Cue\nTells student which prior skill to apply",
        fontsize=8.2,
        ha="center",
        va="center",
        linespacing=1.24,
        zorder=3,
    )

    draw_rect(
        ax, rx, 1.12, rw, 0.64, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        rx + rw / 2,
        1.44,
        "2. Target Concept Giveaway\nNames proportionality instead of asking\nfor an open comparison of consistency",
        fontsize=8.1,
        ha="center",
        va="center",
        linespacing=1.22,
        zorder=3,
    )

    draw_rect(ax, rx, 0.26, rw, 0.70, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.9, zorder=2)
    ax.text(
        rx + rw / 2,
        0.61,
        "3. Method Menu Rewards the Rubric\n"
        "Removes invention, yet judge cites this list\n"
        "to award MR = 3/3 and Total = 15.0 / 15",
        fontsize=8.1,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        linespacing=1.22,
        zorder=3,
    )

    save_fig(fig, "fig3_4_giveaway_example")


# ==============================================================================
# Figure 3.5: Worksheets Replace the Open Challenge (GPT-5 mini Garden Task 1)
# ==============================================================================
def render_fig3_5() -> None:
    W, H = 12.4, 3.10
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Left container: Pre-solved obstacle in body
    draw_rect(
        ax, 0.10, 0.10, 3.95, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 0.10, 2.58, 3.95, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        2.075,
        2.79,
        "(a) Body Pre-Solves the Only Trap",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    draw_rect(
        ax, 0.26, 0.26, 3.63, 2.16, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    # Mini L-shaped walkway diagram
    draw_rect(
        ax, 0.48, 1.08, 0.36, 1.16, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    draw_rect(
        ax, 0.48, 1.08, 1.40, 0.36, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    draw_rect(
        ax, 0.48, 1.08, 0.36, 0.36, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.95, zorder=4
    )
    ax.text(
        2.04,
        1.88,
        "L-Walkway (2 ft wide)\nin 24 ft × 18 ft Yard",
        fontsize=8.4,
        fontweight="bold",
        ha="left",
        va="center",
        zorder=4,
    )
    ax.text(
        0.96, 1.62, "2×2 ft\ncorner", fontsize=7.9, color=C_DARK, ha="left", va="center", zorder=4
    )
    draw_arrow(ax, 0.94, 1.54, 0.72, 1.32, lw=0.9, style="-|>,head_length=0.22,head_width=0.14")

    ax.text(
        2.075,
        0.62,
        'Body instruction: "Treat the corner where\n'
        "the two strips meet so that the overlapping\n"
        'square is only counted once."',
        fontsize=8.0,
        color=C_BLACK,
        ha="center",
        va="center",
        linespacing=1.24,
        zorder=4,
    )

    # Right container: 4-Step Worksheet Pipeline
    draw_rect(
        ax, 4.30, 0.10, 8.00, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 4.30, 2.58, 8.00, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        8.30,
        2.79,
        "(b) GPT-5 mini Garden Task 1: Fixed 4-Part Worksheet (722 Words, Score: 14.0 / 15)",
        fontsize=9.1,
        fontweight="bold",
        ha="center",
        va="center",
    )

    steps = [
        (
            "Part 1: Compute\n5 Feature Areas",
            "Patio, walkway,\ntriangle, trapezoid,\nand pentagon bed",
            C_WHITE,
        ),
        (
            "Part 2: Check\n$200 Budget",
            "Multiply areas by\n$4.00, $0.85, $3.50\nand sum total cost",
            C_WHITE,
        ),
        (
            "Part 3: Test 3\nGiven Edits",
            "Widen path to 3 ft,\nlengthen patio 2 ft,\nor height to 6 ft",
            C_WHITE,
        ),
        (
            "Part 4: Detached\nMethod Prompt",
            '"Describe at least\ntwo different ways\nto break a shape"',
            C_PROC,
        ),
    ]
    sx0 = 4.48
    sw = 1.72
    gap = 0.25
    for i, (stitle, sbody, sfill) in enumerate(steps):
        sx = sx0 + i * (sw + gap)
        draw_rect(
            ax, sx, 0.84, sw, 1.56, facecolor=sfill, edgecolor=C_BLACK, linewidth=0.9, zorder=2
        )
        draw_rect(
            ax,
            sx,
            1.90,
            sw,
            0.50,
            facecolor=C_PROC if sfill == C_WHITE else C_MID,
            edgecolor=C_BLACK,
            linewidth=0.8,
            zorder=3,
        )
        ax.text(
            sx + sw / 2,
            2.15,
            stitle,
            fontsize=8.1,
            fontweight="bold",
            color=C_BLACK if sfill == C_WHITE else C_WHITE,
            ha="center",
            va="center",
            linespacing=1.16,
            zorder=4,
        )
        ax.text(
            sx + sw / 2,
            1.37,
            sbody,
            fontsize=8.0,
            color=C_DARK if sfill == C_WHITE else C_BLACK,
            ha="center",
            va="center",
            linespacing=1.24,
            zorder=4,
        )
        if i < 3:
            draw_arrow(
                ax,
                sx + sw,
                1.62,
                sx + sw + gap,
                1.62,
                lw=1.0,
                style="-|>,head_length=0.24,head_width=0.15",
            )

    draw_rect(
        ax, 4.48, 0.24, 7.63, 0.44, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    ax.text(
        8.295,
        0.46,
        "Judge notes fixed steps (OE = 2/3), yet task still scores 14.0 / 15 across the five dimensions",
        fontsize=8.3,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=4,
    )

    save_fig(fig, "fig3_5_worksheet_example")


# ==============================================================================
# Figure 3.6: Contradictory Geometry in One-Shot Task (GPT-5 mini Garden Task 28)
# ==============================================================================
def render_fig3_6() -> None:
    W, H = 12.4, 3.10
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Left container: Contradictory Text Specifications
    draw_rect(
        ax, 0.10, 0.10, 5.75, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 0.10, 2.58, 5.75, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        2.975,
        2.79,
        "(a) GPT-5 mini Garden Task 28 Text (Score: 15.0 / 15)",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    draw_rect(
        ax, 0.28, 1.58, 5.39, 0.84, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        0.42,
        2.00,
        "Paragraph 1 (Story Layout):\n"
        '"three main parts in a row: a central rectangle, a right triangle attached\n'
        'to one long side... and a trapezoid attached to the opposite long side."',
        fontsize=8.0,
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.25,
        zorder=3,
    )

    draw_rect(
        ax, 0.28, 0.26, 5.39, 1.18, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=2
    )
    ax.text(
        0.42,
        0.85,
        "Measurement Bullets (Contradiction):\n"
        "• Rectangle R: 12 ft (long) by 10 ft (wide).\n"
        '• Right triangle T: "attached along one of the 10-ft sides of R"\n'
        '• Trapezoid P: "attached along the opposite 12-ft side of R"',
        fontsize=8.1,
        fontweight="bold",
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.28,
        zorder=3,
    )

    draw_arrow(ax, 5.85, 1.55, 6.20, 1.55, lw=1.15)

    # Right container: Geometric Impossible Layout
    draw_rect(
        ax, 6.20, 0.10, 6.10, 2.90, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1
    )
    draw_rect(
        ax, 6.20, 2.58, 6.10, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )
    ax.text(
        9.25,
        2.79,
        "(b) Resulting Geometric Contradiction",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
    )

    draw_rect(
        ax, 6.38, 0.78, 5.74, 1.64, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2
    )

    # Central Rectangle R (12 ft horizontal x 10 ft vertical)
    rx, ry, rw, rh = 8.18, 1.04, 1.86, 0.78
    draw_rect(ax, rx, ry, rw, rh, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=1.0, zorder=3)
    ax.text(
        rx + rw / 2,
        ry + rh / 2,
        "Rectangle R\n12 ft × 10 ft",
        fontsize=8.3,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        rx + rw / 2,
        ry - 0.14,
        "Opposite 12-ft long side (empty)",
        fontsize=7.7,
        color=C_DARK,
        ha="center",
        va="center",
        zorder=4,
    )

    # Top Trapezoid P on top 12-ft long side
    trap_pts = [
        (rx, ry + rh),
        (rx + rw, ry + rh),
        (rx + rw - 0.15, ry + rh + 0.46),
        (rx + 0.15, ry + rh + 0.46),
    ]
    draw_poly(ax, trap_pts, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=3)
    ax.text(
        rx + rw / 2,
        ry + rh + 0.23,
        "Trapezoid P (12-ft base)",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )

    # Left Triangle T on 10-ft short side (adjacent, NOT opposite!)
    tri_pts = [(rx, ry), (rx, ry + rh), (rx - 0.82, ry)]
    draw_poly(
        ax, tri_pts, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, linestyle="--", zorder=3
    )
    ax.text(
        6.98,
        1.62,
        "Triangle T\n(10-ft base\non short side)",
        fontsize=7.8,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=4,
    )

    # Callout on right inside white box
    ax.text(
        11.08,
        1.56,
        "10-ft side and\n12-ft side are\nadjacent (90°),\nnot opposite!",
        fontsize=8.2,
        fontweight="bold",
        color=C_BLACK,
        ha="center",
        va="center",
        linespacing=1.26,
        zorder=4,
    )

    draw_rect(
        ax, 6.38, 0.22, 5.74, 0.44, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.85, zorder=3
    )
    ax.text(
        9.25,
        0.44,
        "Judge logs the side mismatch as a concern, yet still awards 15.0 / 15",
        fontsize=8.3,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=4,
    )

    save_fig(fig, "fig3_6_math_error_example")


def main() -> None:
    setup_rc()
    render_fig3_3()
    render_fig3_4()
    render_fig3_5()
    render_fig3_6()
    print("Rendered fig3_3 through fig3_6 successfully.")


if __name__ == "__main__":
    main()
