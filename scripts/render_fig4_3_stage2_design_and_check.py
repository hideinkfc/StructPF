#!/usr/bin/env python3
"""Render Figure 4.3: Stage 2 (Step 2a Design Brief & Step 2b Number Check) for 6.G.A.1.

Follows the monochrome JupyRecSys style used across Chapters 3 and 4:
- #000000 borders and arrows
- #F2F2F2 stage/panel containers
- #E2E2E2 panel headers
- #CFCFCF LLM process boxes and highlighted polygons
- #4D4D4D dark outcome banner
- #FFFFFF data/geometry cards and calculator tool box
"""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle


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


def draw_poly(
    ax,
    pts: list[tuple[float, float]],
    facecolor: str = C_WHITE,
    edgecolor: str = C_BLACK,
    linewidth: float = 0.95,
    linestyle: str = "-",
    zorder: float = 3,
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


def render_fig4_3() -> None:
    setup_rc()
    W, H = 12.4, 3.65
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # ==========================================================================
    # Panel (a): Step 2a - Propose & Select Design Brief
    # ==========================================================================
    p1_x, p1_y, p1_w, p1_h = 0.08, 0.10, 3.35, 3.45
    draw_rect(ax, p1_x, p1_y, p1_w, p1_h, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1)
    draw_rect(ax, p1_x, p1_y + p1_h - 0.42, p1_w, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(p1_x + p1_w / 2, p1_y + p1_h - 0.21, "(a) Step 2a: Design Brief Selection", fontsize=9.1, fontweight="bold", ha="center", va="center")

    # LLM Process Box: Propose & Select Brief
    draw_round_box(ax, 0.24, 2.48, 3.03, 0.50, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=3)
    ax.text(
        1.755,
        2.73,
        "Propose & Select Brief (≤ 2 rev.)\nInput: Stage 1 Skills (4.MD.A.3, 5.NF.B.4)",
        fontsize=7.5,
        fontweight="bold",
        ha="center",
        va="center",
        linespacing=1.22,
        zorder=4,
    )

    draw_arrow(ax, 1.755, 2.48, 1.755, 2.24, lw=1.0)

    # Student-Facing Problem Setup card
    draw_rect(ax, 0.24, 1.24, 3.03, 0.98, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    draw_rect(ax, 0.24, 1.90, 3.03, 0.32, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.8, zorder=3)
    ax.text(1.755, 2.06, "Student-Facing Setup (To Stage 3)", fontsize=7.7, fontweight="bold", ha="center", va="center", zorder=4)
    ax.text(
        0.32,
        1.56,
        "• Goal: Compare two play-area floor plans\n"
        "• Rules: Identical outer boxes; A cuts a\n"
        "  slanted corner, B cuts a rectangle corner\n"
        "• Claim: \"Same outer box = same area\"",
        fontsize=7.25,
        color=C_DARK,
        ha="left",
        va="center",
        linespacing=1.22,
        zorder=4,
    )

    # Internal Design Notes card (Withheld)
    draw_rect(ax, 0.24, 0.22, 3.03, 0.90, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, linestyle="--", zorder=2)
    draw_rect(ax, 0.24, 0.80, 3.03, 0.32, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.8, zorder=3)
    ax.text(1.755, 0.96, "Internal Design Notes (Withheld)", fontsize=7.7, fontweight="bold", ha="center", va="center", zorder=4)
    ax.text(
        0.32,
        0.50,
        "• Impasse: Outer-box areas tie (l × w)\n"
        "• Route 1: Corner triangle = ½ of 4 × 3 box\n"
        "• Route 2: Split floor into rectangles",
        fontsize=7.25,
        color=C_DARK,
        ha="left",
        va="center",
        linespacing=1.22,
        zorder=4,
    )

    # Arrow from Panel (a) to Panel (b)
    draw_arrow(ax, p1_x + p1_w, 1.82, 3.72, 1.82, lw=1.15)

    # ==========================================================================
    # Panel (b): Selected Problem Structure (6.G.A.1 Play-Area Floors)
    # ==========================================================================
    p2_x, p2_y, p2_w, p2_h = 3.72, 0.10, 4.66, 3.45
    draw_rect(ax, p2_x, p2_y, p2_w, p2_h, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1)
    draw_rect(ax, p2_x, p2_y + p2_h - 0.42, p2_w, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(p2_x + p2_w / 2, p2_y + p2_h - 0.21, "(b) Selected Unsplit Geometry (6.G.A.1)", fontsize=9.1, fontweight="bold", ha="center", va="center")

    # Left geometry card: Design A (Right-Triangle Corner Removed)
    c1_x, c1_y, c1_w, c1_h = 3.88, 1.06, 2.10, 1.94
    draw_rect(ax, c1_x, c1_y, c1_w, c1_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(c1_x + c1_w / 2, c1_y + c1_h - 0.20, "Design A: Slanted Corner Cut", fontsize=8.0, fontweight="bold", ha="center", va="center", zorder=4)

    # Outer rectangle for Design A: width 1.56 (12 units), height 1.04 (8 units)
    # Scale: 1 unit = 0.13 in x and y
    ax0, ay0 = 4.15, 1.40
    aw, ah = 1.56, 1.04  # 12 x 8
    cut_w, cut_h = 0.52, 0.39  # 4 x 3 corner at top-right
    # Dashed full outer rectangle
    draw_rect(ax, ax0, ay0, aw, ah, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.8, linestyle="--", zorder=3)
    # Usable floor polygon (5-sided)
    pts_a = [
        (ax0, ay0),
        (ax0 + aw, ay0),
        (ax0 + aw, ay0 + ah - cut_h),
        (ax0 + aw - cut_w, ay0 + ah),
        (ax0, ay0 + ah),
    ]
    draw_poly(ax, pts_a, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=1.05, zorder=4)
    ax.text(ax0 + 0.54, ay0 + 0.38, "Usable Floor A\n(90 sq units)", fontsize=7.5, fontweight="bold", ha="center", va="center", zorder=5)
    # Dimension labels for Design A
    ax.text(ax0 + aw / 2, ay0 - 0.14, "12 units", fontsize=7.4, ha="center", va="center", zorder=5)
    ax.text(ax0 - 0.15, ay0 + ah / 2, "8", fontsize=7.4, ha="center", va="center", zorder=5)
    ax.text(ax0 + aw - cut_w / 2, ay0 + ah + 0.11, "4", fontsize=7.3, fontweight="bold", ha="center", va="center", zorder=5)
    ax.text(ax0 + aw + 0.11, ay0 + ah - cut_h / 2, "3", fontsize=7.3, fontweight="bold", ha="center", va="center", zorder=5)
    ax.text(ax0 + aw - cut_w / 2 - 0.08, ay0 + ah - cut_h / 2 - 0.06, "5", fontsize=7.3, fontweight="bold", ha="right", va="top", zorder=5)

    # Right geometry card: Design B (Rectangular Corner Removed)
    c2_x, c2_y, c2_w, c2_h = 6.12, 1.06, 2.10, 1.94
    draw_rect(ax, c2_x, c2_y, c2_w, c2_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(c2_x + c2_w / 2, c2_y + c2_h - 0.20, "Design B: Rectangular Cut", fontsize=8.0, fontweight="bold", ha="center", va="center", zorder=4)

    bx0, by0 = 6.39, 1.40
    # Dashed full outer rectangle
    draw_rect(ax, bx0, by0, aw, ah, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.8, linestyle="--", zorder=3)
    # Usable floor polygon (L-shaped 6-sided)
    pts_b = [
        (bx0, by0),
        (bx0 + aw, by0),
        (bx0 + aw, by0 + ah - cut_h),
        (bx0 + aw - cut_w, by0 + ah - cut_h),
        (bx0 + aw - cut_w, by0 + ah),
        (bx0, by0 + ah),
    ]
    draw_poly(ax, pts_b, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=1.05, zorder=4)
    ax.text(bx0 + 0.56, by0 + 0.40, "Usable Floor B\n(84 sq units)", fontsize=7.7, fontweight="bold", ha="center", va="center", zorder=5)
    # Dimension labels for Design B
    ax.text(bx0 + aw / 2, by0 - 0.14, "12 units", fontsize=7.4, ha="center", va="center", zorder=5)
    ax.text(bx0 - 0.15, by0 + ah / 2, "8", fontsize=7.4, ha="center", va="center", zorder=5)
    ax.text(bx0 + aw - cut_w / 2, by0 + ah + 0.11, "4", fontsize=7.3, fontweight="bold", ha="center", va="center", zorder=5)
    ax.text(bx0 + aw + 0.11, by0 + ah - cut_h / 2, "3", fontsize=7.3, fontweight="bold", ha="center", va="center", zorder=5)

    # Bottom summary inside Panel (b)
    draw_rect(ax, 3.88, 0.22, 4.34, 0.72, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(
        6.05,
        0.58,
        "Shortcut Impasse: Both floors sit inside 12 × 8 = 96 outer rectangles,\n"
        "so comparing outer dimensions ties (96 = 96) unless students\n"
        "find a way to account for the slanted vs. rectangular corner cuts.",
        fontsize=7.35,
        color=C_BLACK,
        ha="center",
        va="center",
        linespacing=1.20,
        zorder=4,
    )

    # Arrow from Panel (b) to Panel (c)
    draw_arrow(ax, p2_x + p2_w, 1.82, 8.67, 1.82, lw=1.15)

    # ==========================================================================
    # Panel (c): Step 2b - Number Selection & Python Math Calculator
    # ==========================================================================
    p3_x, p3_y, p3_w, p3_h = 8.67, 0.10, 3.65, 3.45
    draw_rect(ax, p3_x, p3_y, p3_w, p3_h, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=0.95, zorder=1)
    draw_rect(ax, p3_x, p3_y + p3_h - 0.42, p3_w, 0.42, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    ax.text(p3_x + p3_w / 2, p3_y + p3_h - 0.21, "(c) Step 2b: Calculator Verification", fontsize=9.1, fontweight="bold", ha="center", va="center")

    # Top row in Panel (c): Choose Numbers <-> Python Math Calculator
    draw_round_box(ax, 8.83, 2.48, 1.54, 0.50, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, zorder=3)
    ax.text(9.60, 2.73, "Choose Numbers\n(≤ 2 repairs)", fontsize=7.8, fontweight="bold", ha="center", va="center", linespacing=1.18, zorder=4)

    draw_round_box(ax, 10.62, 2.48, 1.54, 0.50, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.95, zorder=3)
    ax.text(11.39, 2.73, "Python Math\nCalculator", fontsize=7.8, fontweight="bold", ha="center", va="center", linespacing=1.18, zorder=4)

    # Bidirectional loop arrows between Choose Numbers and Calculator
    draw_arrow(ax, 10.37, 2.81, 10.62, 2.81, lw=0.95, style="-|>,head_length=0.20,head_width=0.13")
    draw_arrow(ax, 10.62, 2.64, 10.37, 2.64, lw=0.95, style="-|>,head_length=0.20,head_width=0.13")

    draw_arrow(ax, 10.495, 2.48, 10.495, 2.24, lw=1.0)

    # Checked Conditions Box
    draw_rect(ax, 8.83, 0.78, 3.33, 1.44, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.85, zorder=2)
    draw_rect(ax, 8.83, 1.90, 3.33, 0.32, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.8, zorder=3)
    ax.text(10.495, 2.06, "Checked Conditions on Values (12, 8, 4, 3, 5)", fontsize=7.6, fontweight="bold", ha="center", va="center", zorder=4)
    ax.text(
        8.95,
        1.34,
        "1. Shortcut Fails (Outer Tie):\n"
        "   12 × 8 = 96  vs.  12 × 8 = 96\n"
        "2. Consistent Right-Triangle Cut:\n"
        "   √(4² + 3²) = 5\n"
        "3. Distinct Usable Floor Areas:\n"
        "   96 - 6 = 90  >  96 - 12 = 84",
        fontsize=7.35,
        color=C_BLACK,
        ha="left",
        va="center",
        linespacing=1.22,
        zorder=4,
    )
    ax.text(
        12.04,
        1.34,
        "\n[Holds]\n\n[Holds]\n\n[Holds]",
        fontsize=7.35,
        fontweight="bold",
        color=C_BLACK,
        ha="right",
        va="center",
        linespacing=1.22,
        zorder=4,
    )

    # Bottom banner: Verified output
    draw_rect(ax, 8.83, 0.22, 3.33, 0.44, facecolor=C_MID, edgecolor=C_BLACK, linewidth=0.85, zorder=3)
    ax.text(
        10.495,
        0.44,
        "Verified Given Values (12, 8, 4, 3, 5) → Stage 3",
        fontsize=7.6,
        fontweight="bold",
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=4,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(
            OUT_DIR / f"fig4_3_stage2_design_and_check.{ext}",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.03,
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    render_fig4_3()
    print("Rendered fig4_3_stage2_design_and_check.{pdf,png}")
