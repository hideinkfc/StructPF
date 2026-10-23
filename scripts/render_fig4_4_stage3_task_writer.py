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
    plt.rcParams["pdf.fonttype"] = 42
    W, H = 12.6, 3.15
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Shared vertical coordinates across all three panels
    py, ph = 0.10, 2.95
    hdr_h = 0.38
    inner_top = py + ph - hdr_h - 0.14  # 2.53
    inner_bot = py + 0.14               # 0.24
    inner_h = inner_top - inner_bot     # 2.29
    mid_y = py + (ph - hdr_h) / 2       # 1.385

    # Panel X positions and widths
    p1_x, p1_w = 0.08, 3.75
    p2_x, p2_w = 4.23, 3.10
    p3_x, p3_w = 7.73, 4.79

    # ==========================================================================
    # Panel (a): Stage 2 Output & Information Barrier
    # ==========================================================================
    draw_rect(ax, p1_x, py, p1_w, ph, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=1.0, zorder=1)
    draw_rect(
        ax, p1_x, py + ph - hdr_h, p1_w, hdr_h, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.9, zorder=2
    )
    ax.text(
        p1_x + p1_w / 2,
        py + ph - hdr_h / 2,
        "(a) Stage 2 Output & Barrier",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
    )

    c_pad = 0.15
    cx = p1_x + c_pad
    cw = p1_w - 2 * c_pad
    gap = 0.23
    card_h = (inner_h - gap) / 2  # 1.03 each

    # Top card inside (a): Passed to Task Writer (Solid)
    c1_y = inner_bot + card_h + gap
    draw_rect(ax, cx, c1_y, cw, card_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.9, zorder=3)
    draw_rect(
        ax, cx, c1_y + card_h - 0.28, cw, 0.28, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.8, zorder=4
    )
    ax.text(
        cx + cw / 2,
        c1_y + card_h - 0.14,
        "Passed to Task Writer",
        fontsize=8.4,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
        zorder=5,
    )
    ax.text(
        cx + 0.12,
        c1_y + (card_h - 0.28) / 2,
        "• Student-facing setup & comparison\n• Verified given values (12, 8, 4, 3, 5)",
        fontsize=8.1,
        ha="left",
        va="center",
        color=C_DARK,
        linespacing=1.32,
        zorder=5,
    )

    # Bottom card inside (a): Withheld by Barrier (Dashed)
    c2_y = inner_bot
    draw_rect(
        ax, cx, c2_y, cw, card_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.9, linestyle="--", zorder=3
    )
    draw_rect(
        ax,
        cx,
        c2_y + card_h - 0.28,
        cw,
        0.28,
        facecolor=C_SUB,
        edgecolor=C_BLACK,
        linewidth=0.8,
        linestyle="--",
        zorder=4,
    )
    ax.text(
        cx + cw / 2,
        c2_y + card_h - 0.14,
        "Withheld by Information Barrier",
        fontsize=8.4,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
        zorder=5,
    )
    ax.text(
        cx + 0.12,
        c2_y + (card_h - 0.28) / 2,
        "• Target formula (½ bh) & solution paths\n• Internal areas (90 vs. 84) & rubric",
        fontsize=8.1,
        ha="left",
        va="center",
        color=C_DARK,
        linespacing=1.32,
        zorder=5,
    )

    # ==========================================================================
    # Panel (b): Stage 3 Task Writer
    # ==========================================================================
    draw_rect(ax, p2_x, py, p2_w, ph, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=1.0, zorder=1)
    draw_rect(
        ax, p2_x, py + ph - hdr_h, p2_w, hdr_h, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.9, zorder=2
    )
    ax.text(
        p2_x + p2_w / 2,
        py + ph - hdr_h / 2,
        "(b) Stage 3: Task Writer",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
    )

    bx = p2_x + c_pad
    bw = p2_w - 2 * c_pad

    # Top box inside (b): LLM Writer (aligned with top card in (a))
    draw_round_box(
        ax, bx, c1_y, bw, card_h, facecolor=C_PROC, edgecolor=C_BLACK, linewidth=0.95, pad=0.06, zorder=3
    )
    ax.text(
        bx + bw / 2,
        c1_y + card_h - 0.22,
        "Write Open Student Task",
        fontsize=8.5,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
        zorder=4,
    )
    ax.text(
        bx + 0.12,
        c1_y + 0.38,
        "• Turn setup & givens into story\n• Ask one open comparison question",
        fontsize=8.0,
        ha="left",
        va="center",
        color=C_DARK,
        linespacing=1.30,
        zorder=4,
    )

    # Downward arrow inside (b)
    draw_arrow(
        ax,
        bx + bw / 2,
        c1_y - 0.01,
        bx + bw / 2,
        c2_y + card_h + 0.01,
        lw=1.0,
        style="-|>,head_length=0.20,head_width=0.14",
    )

    # Bottom card inside (b): Post-Writing Checks (aligned with bottom card in (a))
    draw_rect(ax, bx, c2_y, bw, card_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.9, zorder=3)
    draw_rect(
        ax, bx, c2_y + card_h - 0.28, bw, 0.28, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.8, zorder=4
    )
    ax.text(
        bx + bw / 2,
        c2_y + card_h - 0.14,
        "Stage 3 Checks (≤ 2 rev.)",
        fontsize=8.4,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
        zorder=5,
    )
    ax.text(
        bx + 0.12,
        c2_y + (card_h - 0.28) / 2,
        "• All given values (12, 8, 4, 3, 5) appear\n• No formula or splitting hint added",
        fontsize=8.0,
        ha="left",
        va="center",
        color=C_DARK,
        linespacing=1.32,
        zorder=5,
    )

    # ==========================================================================
    # Panel (c): Stage 3 Output (Student PF Task)
    # ==========================================================================
    draw_rect(ax, p3_x, py, p3_w, ph, facecolor=C_GROUP, edgecolor=C_BLACK, linewidth=1.0, zorder=1)
    draw_rect(
        ax, p3_x, py + ph - hdr_h, p3_w, hdr_h, facecolor=C_SUB, edgecolor=C_BLACK, linewidth=0.9, zorder=2
    )
    ax.text(
        p3_x + p3_w / 2,
        py + ph - hdr_h / 2,
        "(c) Stage 3 Output: Student PF Task",
        fontsize=9.2,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
    )

    # Single inner card inside (c) spanning exact same inner_bot to inner_top
    tx = p3_x + c_pad
    tw = p3_w - 2 * c_pad
    draw_rect(ax, tx, inner_bot, tw, inner_h, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=0.9, zorder=3)
    draw_rect(
        ax,
        tx,
        inner_bot + inner_h - 0.28,
        tw,
        0.28,
        facecolor=C_SUB,
        edgecolor=C_BLACK,
        linewidth=0.8,
        zorder=4,
    )
    ax.text(
        tx + tw / 2,
        inner_bot + inner_h - 0.14,
        "Two Play-Area Floor Designs (Grade 6 Polygon Area)",
        fontsize=8.4,
        fontweight="bold",
        ha="center",
        va="center",
        color=C_BLACK,
        zorder=5,
    )

    ax.text(
        tx + 0.14,
        inner_bot + 1.44,
        "Setup:\n"
        "Both designs fit inside a 12 × 8 rectangle. Design A removes\n"
        "a corner with perpendicular legs of 4 and 3 and slanted side 5.\n"
        "Design B removes a 4 × 3 rectangular corner.",
        fontsize=8.1,
        ha="left",
        va="center",
        color=C_DARK,
        linespacing=1.26,
        zorder=5,
    )

    ax.plot(
        [tx + 0.14, tx + tw - 0.14],
        [inner_bot + 0.94, inner_bot + 0.94],
        color=C_MID,
        lw=0.6,
        linestyle=":",
        zorder=4,
    )

    ax.text(
        tx + 0.14,
        inner_bot + 0.47,
        "Open Question:\n"
        "A volunteer claims both designs have the same usable area\n"
        "because their outer boxes match. Which design has more\n"
        "floor space, and what is each area? Show your reasoning.",
        fontsize=8.1,
        fontweight="bold",
        ha="left",
        va="center",
        color=C_BLACK,
        linespacing=1.26,
        zorder=5,
    )

    # ==========================================================================
    # Aligned Inter-Panel Arrows (both at mid_y)
    # ==========================================================================
    draw_arrow(ax, p1_x + p1_w, mid_y, p2_x, mid_y, lw=1.15)
    draw_arrow(ax, p2_x + p2_w, mid_y, p3_x, mid_y, lw=1.15)

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
