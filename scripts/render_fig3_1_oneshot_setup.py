"""Render Figure 3.1: Direct visual comparison of Rahimi et al. (2025, 2026) vs. our reconstructed multi-theme setup.
Styled after classic IEEE/ACM and JupyRecSys diagrams: sharp rectangular corners, monochrome/grayscale blocks,
solid vs. dashed borders for released vs. unreleased artifacts, and clean orthogonal arrows.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def draw_rect(
    ax,
    x,
    y,
    w,
    h,
    facecolor="#FFFFFF",
    edgecolor="#000000",
    linewidth=0.9,
    linestyle="-",
    zorder=2,
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


def draw_stack(
    ax,
    x,
    y,
    w,
    h,
    n=3,
    dx=0.05,
    dy=0.05,
    facecolor="#FFFFFF",
    edgecolor="#000000",
    linewidth=0.9,
    linestyle="-",
    zorder=2,
):
    """Draw stacked sharp rectangles (like Pre-Processed Cells in JupyRecSys Fig. 1)."""
    for i in range(n - 1, -1, -1):
        patch = Rectangle(
            (x + i * dx, y + i * dy),
            w,
            h,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth,
            linestyle=linestyle,
            zorder=zorder + (n - i) * 0.1,
        )
        ax.add_patch(patch)


def draw_arrow(
    ax,
    x0,
    y0,
    x1,
    y1,
    color="#000000",
    lw=1.1,
    style="-|>,head_length=0.38,head_width=0.22",
    linestyle="-",
    zorder=5,
):
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


def draw_h_bracket(ax, x_left, x_right, y, tick=0.08, lw=0.9, color="#000000", zorder=4):
    ax.plot([x_left, x_right], [y, y], color=color, lw=lw, zorder=zorder)
    ax.plot([x_left, x_left], [y, y - tick], color=color, lw=lw, zorder=zorder)
    ax.plot([x_right, x_right], [y, y - tick], color=color, lw=lw, zorder=zorder)


def draw_v_bracket(ax, x, y_bot, y_top, tick=0.08, lw=0.9, color="#000000", zorder=4):
    """Left-opening or right-opening vertical bracket. Positive tick points right."""
    ax.plot([x, x], [y_bot, y_top], color=color, lw=lw, zorder=zorder)
    ax.plot([x, x + tick], [y_bot, y_bot], color=color, lw=lw, zorder=zorder)
    ax.plot([x, x + tick], [y_top, y_top], color=color, lw=lw, zorder=zorder)


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["axes.edgecolor"] = "none"

    W, H = 12.8, 11.2
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Monochrome / JupyRecSys palette
    c_black = "#000000"
    c_dark = "#222222"
    c_proc = "#CFCFCF"  # JupyRecSys process block gray
    c_group = "#F2F2F2"  # Outer container light gray
    c_sub = "#E6E6E6"  # Subtle header/divider gray
    c_white = "#FFFFFF"

    # Column geometry (4 pipeline stages left-to-right)
    # Stage 1: Curriculum Topics | Stage 2: Six-Part Prompt | Stage 3: LLM Generation | Stage 4: Tasks & Evaluation
    s1_x, s1_w = 0.26, 3.46
    s2_x, s2_w = 4.08, 3.44
    s3_x, s3_w = 7.88, 1.98
    s4_x, s4_w = 10.22, 2.42

    # Centered column headers at top
    leg_y = 10.88
    stage_headers = [
        (s1_x + 0.76 + (s1_w - 0.76) / 2, "1. Grade 7 Settings"),
        (s2_x + s2_w / 2, "2. Six-Part One-Shot Prompt"),
        (s3_x + s3_w / 2, "3. LLM Generation"),
        (s4_x + s4_w / 2, "4. Tasks & Evaluation"),
    ]
    for sx, stitle in stage_headers:
        ax.text(
            sx,
            leg_y,
            stitle,
            fontsize=10.2,
            fontweight="bold",
            color=c_black,
            ha="center",
            va="center",
        )

    # Thin horizontal rule under column headers
    ax.plot([0.14, 12.66], [10.60, 10.60], color=c_black, lw=0.95, zorder=3)

    # ==========================================================================
    # ROW (a): Rahimi et al. (2025, 2026) Baseline
    # ==========================================================================
    top_y, top_h = 7.42, 3.00
    draw_rect(
        ax,
        0.14,
        top_y,
        12.52,
        top_h,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=1,
    )

    # Row (a) Title Banner
    ax.text(
        0.28,
        top_y + top_h - 0.30,
        "(a) Prior Study: Rahimi et al. (2025, 2026) (Single Setting & Unreleased Artifacts)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )
    # Legend for box styles inside top right of Row (a)
    leg_box_y = top_y + top_h - 0.41
    draw_rect(
        ax,
        8.55,
        leg_box_y,
        0.26,
        0.21,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        linestyle="-",
        zorder=3,
    )
    ax.text(
        8.87,
        leg_box_y + 0.105,
        "= Open / saved",
        fontsize=8.3,
        color=c_dark,
        ha="left",
        va="center",
    )
    draw_rect(
        ax,
        10.10,
        leg_box_y,
        0.26,
        0.21,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        linestyle="--",
        zorder=3,
    )
    ax.text(
        10.42, leg_box_y + 0.105, "= Unreleased", fontsize=8.3, color=c_dark, ha="left", va="center"
    )
    draw_rect(
        ax,
        11.46,
        leg_box_y,
        0.26,
        0.21,
        facecolor=c_proc,
        edgecolor=c_black,
        linewidth=0.85,
        linestyle="-",
        zorder=3,
    )
    ax.text(
        11.78, leg_box_y + 0.105, "= Process", fontsize=8.3, color=c_dark, ha="left", va="center"
    )

    a_box_y = top_y + 0.24
    a_box_h = 2.22
    a_mid_y = a_box_y + a_box_h / 2

    # Shared geometry for Stage 1 topic cards across (a) and (b)
    brk_x = s1_x + 0.74
    cell_x = s1_x + 0.83
    cell_w = s1_w - 0.83

    # (a) Stage 1: Single Topic (aligned_x with Cell 1 in Row b)
    a_c1_h = 1.38
    a_c1_y = a_mid_y - a_c1_h / 2
    draw_rect(
        ax,
        cell_x,
        a_c1_y,
        cell_w,
        a_c1_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    draw_rect(
        ax,
        cell_x,
        a_c1_y + a_c1_h - 0.40,
        cell_w,
        0.40,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.8,
        zorder=3,
    )
    ax.text(
        cell_x + 0.10,
        a_c1_y + a_c1_h - 0.20,
        "1. Sports / Basketball",
        fontsize=8.9,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
        zorder=4,
    )
    ax.text(
        cell_x + 0.10,
        a_c1_y + (a_c1_h - 0.40) / 2,
        "Target: Proportional relationships\nPrior: Unit rates & rational numbers",
        fontsize=8.1,
        color=c_dark,
        ha="left",
        va="center",
        linespacing=1.42,
        zorder=4,
    )

    draw_v_bracket(ax, brk_x, a_c1_y + 0.06, a_c1_y + a_c1_h - 0.06, tick=0.06, lw=1.0)
    ax.text(
        brk_x - 0.06,
        a_mid_y,
        "Single\nSetting\nOnly",
        fontsize=8.2,
        fontweight="bold",
        color=c_black,
        ha="right",
        va="center",
        linespacing=1.28,
    )

    # (a) Stage 2: Unreleased Six-Part Prompt (Dashed container with 2 inner dashed boxes matching Row b)
    draw_rect(
        ax,
        s2_x,
        a_box_y,
        s2_w,
        a_box_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.95,
        linestyle="--",
        zorder=3,
    )
    ax.text(
        s2_x + s2_w / 2,
        a_box_y + a_box_h - 0.28,
        "Six-Part Prompt (Unreleased Text)",
        fontsize=9.1,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )
    in_w = (s2_w - 0.32) / 2
    draw_rect(
        ax,
        s2_x + 0.11,
        a_box_y + 0.20,
        in_w,
        1.48,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.85,
        linestyle="--",
        zorder=4,
    )
    ax.text(
        s2_x + 0.11 + in_w / 2,
        a_box_y + 0.94,
        "System & Rubric\n(Parts 1–3, 5–6)\nWording not released",
        fontsize=8.1,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.42,
        zorder=5,
    )
    draw_rect(
        ax,
        s2_x + 0.21 + in_w,
        a_box_y + 0.20,
        in_w,
        1.48,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.85,
        linestyle="--",
        zorder=4,
    )
    ax.text(
        s2_x + 0.21 + in_w + in_w / 2,
        a_box_y + 0.94,
        "5 In-Prompt PF\nExamples (Part 4)\nTasks not released",
        fontsize=8.1,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.42,
        zorder=5,
    )

    # (a) Stage 3: Process node (JupyRecSys gray block)
    draw_rect(
        ax,
        s3_x,
        a_box_y + 0.26,
        s3_w,
        a_box_h - 0.52,
        facecolor=c_proc,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s3_x + s3_w / 2,
        a_mid_y + 0.34,
        "One-Shot Generation",
        fontsize=8.9,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        s3_x + s3_w / 2,
        a_mid_y - 0.22,
        "GPT-4o (30 runs)\nPhi-3 mini (30 runs)",
        fontsize=8.2,
        color=c_black,
        ha="center",
        va="center",
        linespacing=1.40,
        zorder=4,
    )

    # (a) Stage 4: Unreleased 60 Tasks + Scores Only
    draw_stack(
        ax,
        s4_x,
        a_box_y + 1.00,
        s4_w - 0.12,
        1.04,
        n=3,
        dx=0.055,
        dy=0.055,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.9,
        linestyle="--",
        zorder=3,
    )
    ax.text(
        s4_x + (s4_w - 0.12) / 2,
        a_box_y + 1.52,
        "60 Generated Tasks\n(Unreleased text)",
        fontsize=8.5,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        linespacing=1.36,
        zorder=5,
    )
    draw_arrow(
        ax,
        s4_x + s4_w / 2,
        a_box_y + 1.00,
        s4_x + s4_w / 2,
        a_box_y + 0.64,
        lw=1.0,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    draw_rect(
        ax,
        s4_x,
        a_box_y + 0.08,
        s4_w,
        0.56,
        facecolor=c_proc,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=3,
    )
    ax.text(
        s4_x + s4_w / 2,
        a_box_y + 0.36,
        "Human 5D Scores Only (Table 2.1)",
        fontsize=8.0,
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )

    # Horizontal arrows in Row (a)
    draw_arrow(ax, s1_x + s1_w, a_mid_y, s2_x, a_mid_y)
    draw_arrow(ax, s2_x + s2_w, a_mid_y, s3_x, a_mid_y)
    draw_arrow(ax, s3_x + s3_w, a_mid_y, s4_x, a_mid_y)

    # ==========================================================================
    # VERTICAL TRANSITION ARROWS (Row a -> Row b)
    # ==========================================================================
    trans_y_top = top_y
    trans_y_bot = 6.50
    trans_mid = (trans_y_top + trans_y_bot) / 2

    transitions = [
        (cell_x + 0.45, "Keep 1 + Add 3 Settings", "left", 0.12),
        (s2_x + 0.55, "Reconstruct Prompt (Table A.1)", "left", 0.12),
        (s3_x + 0.30, "Scale to 4 × 2 × 30 Runs", "left", 0.12),
        (s4_x + 0.30, "Save & Inspect 240 Tasks", "left", 0.12),
    ]
    for tx, tlabel, tha, tdx in transitions:
        draw_arrow(ax, tx, trans_y_top, tx, trans_y_bot, lw=1.15)
        ax.text(
            tx + tdx,
            trans_mid,
            tlabel,
            fontsize=8.7,
            fontweight="bold",
            color=c_black,
            ha=tha,
            va="center",
        )

    # ==========================================================================
    # ROW (b): Our Reconstructed & Extended Multi-Theme Study
    # ==========================================================================
    bot_y, bot_h = 0.16, 6.34
    draw_rect(
        ax,
        0.14,
        bot_y,
        12.52,
        bot_h,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=1,
    )

    ax.text(
        0.28,
        bot_y + bot_h - 0.32,
        "(b) Our Study: Reconstructed Prompt & Multi-Theme Expansion (4 Grade 7 Settings × 2 Models × 30 Runs = 240 Saved Tasks)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )

    b_box_y = bot_y + 0.24
    b_box_h = 5.50
    b_mid_y = b_box_y + b_box_h / 2

    # ------------------------------------------------------------------
    # (b) Stage 1: 4 Curriculum Topic Cells (Bracketed: 1 Shared + 3 Added)
    # ------------------------------------------------------------------
    cell_h = 1.18
    cell_gap = 0.26

    topics = [
        (
            "1. Sports / Basketball",
            "Target: Proportional relationships\nPrior: Unit rates & rational numbers",
        ),
        (
            "2. Shopping / Pocket Money",
            "Target: Multistep percents & markups\nPrior: Proportions & rational ops",
        ),
        ("3. Music / Playlists", "Target: Compare samples\nPrior: Mean, median, IQR & MAD"),
        (
            "4. Home & Garden Design",
            "Target: Area of composite 2D figures\nPrior: Composing & decomposing area",
        ),
    ]

    top_cell_y = b_box_y + b_box_h - cell_h
    cell_ys = []
    for idx, (t_title, t_sub) in enumerate(topics):
        cy = top_cell_y - idx * (cell_h + cell_gap)
        cell_ys.append(cy)
        draw_rect(
            ax,
            cell_x,
            cy,
            cell_w,
            cell_h,
            facecolor=c_white,
            edgecolor=c_black,
            linewidth=0.95,
            zorder=3,
        )
        draw_rect(
            ax,
            cell_x,
            cy + cell_h - 0.38,
            cell_w,
            0.38,
            facecolor=c_sub if idx > 0 else c_white,
            edgecolor=c_black,
            linewidth=0.8,
            zorder=3,
        )
        ax.text(
            cell_x + 0.10,
            cy + cell_h - 0.19,
            t_title,
            fontsize=8.8,
            fontweight="bold",
            color=c_black,
            ha="left",
            va="center",
            zorder=4,
        )
        ax.text(
            cell_x + 0.10,
            cy + (cell_h - 0.38) / 2,
            t_sub,
            fontsize=8.0,
            color=c_dark,
            ha="left",
            va="center",
            linespacing=1.40,
            zorder=4,
        )

    # Bracket for Cell 1 (Shared Baseline)
    draw_v_bracket(ax, brk_x, cell_ys[0] + 0.06, cell_ys[0] + cell_h - 0.06, tick=0.06, lw=1.0)
    ax.text(
        brk_x - 0.06,
        cell_ys[0] + cell_h / 2,
        "Shared\nBaseline\n(1 Setting)",
        fontsize=8.0,
        fontweight="bold",
        color=c_black,
        ha="right",
        va="center",
        linespacing=1.28,
    )

    # Bracket for Cells 2-4 (+3 Extended Settings)
    draw_v_bracket(ax, brk_x, cell_ys[3] + 0.06, cell_ys[1] + cell_h - 0.06, tick=0.06, lw=1.0)
    ax.text(
        brk_x - 0.06,
        (cell_ys[3] + cell_ys[1] + cell_h) / 2,
        "Added in\nOur Study\n(3 Settings)",
        fontsize=8.0,
        fontweight="bold",
        color=c_black,
        ha="right",
        va="center",
        linespacing=1.28,
    )

    # ------------------------------------------------------------------
    # (b) Stage 2: Reconstructed Six-Part Prompt (Solid container, Table A.1)
    # ------------------------------------------------------------------
    draw_rect(
        ax,
        s2_x,
        b_box_y,
        s2_w,
        b_box_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    draw_rect(
        ax,
        s2_x,
        b_box_y + b_box_h - 0.44,
        s2_w,
        0.44,
        facecolor=c_sub,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s2_x + s2_w / 2,
        b_box_y + b_box_h - 0.22,
        "Reconstructed Prompt (Table A.1)",
        fontsize=9.2,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )

    p_in_x = s2_x + 0.13
    p_in_w = s2_w - 0.26

    # Sub-block 1: System Instructions & Rubric (Parts 1-3)
    b1_h = 1.48
    b1_y = b_box_y + b_box_h - 0.62 - b1_h
    draw_rect(
        ax,
        p_in_x,
        b1_y,
        p_in_w,
        b1_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=4,
    )
    draw_rect(
        ax,
        p_in_x,
        b1_y + b1_h - 0.36,
        p_in_w,
        0.36,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.8,
        zorder=4,
    )
    ax.text(
        p_in_x + 0.10,
        b1_y + b1_h - 0.18,
        "System Role & Rubric (Parts 1–3)",
        fontsize=8.7,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
        zorder=5,
    )
    ax.text(
        p_in_x + 0.10,
        b1_y + (b1_h - 0.36) / 2,
        "(1) Role & Rules: Math PF designer; no solution\n"
        "(2) PF Overview: Explore prior to instruction\n"
        "(3) Design Criteria: Verbatim 5D rubric (1–3)",
        fontsize=8.0,
        color=c_dark,
        ha="left",
        va="center",
        linespacing=1.42,
        zorder=5,
    )

    # Sub-block 2: 5 Published StratL PF Examples (Part 4)
    b2_h = 1.48
    b2_y = b1_y - 0.22 - b2_h
    draw_rect(
        ax,
        p_in_x,
        b2_y,
        p_in_w,
        b2_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=4,
    )
    draw_rect(
        ax,
        p_in_x,
        b2_y + b2_h - 0.36,
        p_in_w,
        0.36,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.8,
        zorder=4,
    )
    ax.text(
        p_in_x + 0.10,
        b2_y + b2_h - 0.18,
        "5 Published StratL PF Examples (Part 4)",
        fontsize=8.5,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
        zorder=5,
    )
    ax.text(
        p_in_x + 0.10,
        b2_y + (b2_h - 0.36) / 2,
        "Human PF tasks from Puech et al. (2025):\n"
        "1. Consistency  2. Seat allocation  3. Land sharing\n"
        "4. Shared furniture  5. Bicycle tie",
        fontsize=7.75,
        color=c_dark,
        ha="left",
        va="center",
        linespacing=1.42,
        zorder=5,
    )

    # Sub-block 3: Per-Cell User Input & Output Schema (Parts 5-6)
    b3_h = 1.44
    b3_y = b_box_y + 0.18
    draw_rect(
        ax,
        p_in_x,
        b3_y,
        p_in_w,
        b3_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=4,
    )
    draw_rect(
        ax,
        p_in_x,
        b3_y + b3_h - 0.36,
        p_in_w,
        0.36,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.8,
        zorder=4,
    )
    ax.text(
        p_in_x + 0.10,
        b3_y + b3_h - 0.18,
        "Setting Input & Output Schema (Parts 5–6)",
        fontsize=8.3,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
        zorder=5,
    )
    ax.text(
        p_in_x + 0.10,
        b3_y + (b3_h - 0.36) / 2,
        "(5) Supplies Grade 7, Target, Prior Knowledge &\n"
        "     Student Interest for Setting 1–4\n"
        "(6) Returns JSON task (title, body, question)",
        fontsize=8.0,
        color=c_dark,
        ha="left",
        va="center",
        linespacing=1.40,
        zorder=5,
    )

    # ------------------------------------------------------------------
    # (b) Stage 3: LLM Generation Process (JupyRecSys gray process box)
    # ------------------------------------------------------------------
    draw_rect(
        ax,
        s3_x,
        b_box_y + 0.50,
        s3_w,
        b_box_h - 1.00,
        facecolor=c_proc,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s3_x + s3_w / 2,
        b_box_y + b_box_h - 0.90,
        "One-Shot\nGeneration",
        fontsize=9.1,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        linespacing=1.26,
        zorder=4,
    )

    m_x = s3_x + 0.13
    m_w = s3_w - 0.26
    draw_rect(
        ax,
        m_x,
        b_mid_y + 0.16,
        m_w,
        1.18,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=4,
    )
    ax.text(
        m_x + m_w / 2,
        b_mid_y + 0.98,
        "GPT-5 mini",
        fontsize=8.8,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=5,
    )
    ax.text(
        m_x + m_w / 2,
        b_mid_y + 0.50,
        "4 settings × 30 runs\n= 120 tasks",
        fontsize=8.1,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.36,
        zorder=5,
    )

    draw_rect(
        ax,
        m_x,
        b_mid_y - 1.24,
        m_w,
        1.18,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=4,
    )
    ax.text(
        m_x + m_w / 2,
        b_mid_y - 0.42,
        "GPT-4.1",
        fontsize=8.8,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=5,
    )
    ax.text(
        m_x + m_w / 2,
        b_mid_y - 0.90,
        "4 settings × 30 runs\n= 120 tasks",
        fontsize=8.1,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.36,
        zorder=5,
    )

    ax.text(
        s3_x + s3_w / 2,
        b_box_y + 0.94,
        "Default sampling\n(No retries)",
        fontsize=8.1,
        color=c_black,
        ha="center",
        va="center",
        linespacing=1.34,
        zorder=4,
    )

    # ------------------------------------------------------------------
    # (b) Stage 4: Saved Corpus & Blinded Evaluation
    # ------------------------------------------------------------------
    st_y = b_box_y + b_box_h - 1.66
    draw_stack(
        ax,
        s4_x,
        st_y,
        s4_w - 0.12,
        1.50,
        n=3,
        dx=0.055,
        dy=0.055,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s4_x + (s4_w - 0.12) / 2,
        st_y + 1.00,
        "240 Saved PF Tasks",
        fontsize=8.9,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=5,
    )
    ax.text(
        s4_x + (s4_w - 0.12) / 2,
        st_y + 0.46,
        "Full task JSONs & prompts\nretained for inspection",
        fontsize=8.0,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.38,
        zorder=5,
    )

    # JupyRecSys solid black synchronization bar below saved tasks
    bar_y = b_box_y + 3.30
    draw_rect(
        ax,
        s4_x + 0.06,
        bar_y,
        s4_w - 0.12,
        0.06,
        facecolor=c_black,
        edgecolor=c_black,
        linewidth=0.5,
        zorder=4,
    )
    draw_arrow(
        ax,
        s4_x + s4_w / 2,
        st_y,
        s4_x + s4_w / 2,
        bar_y + 0.06,
        lw=1.05,
        style="-|>,head_length=0.28,head_width=0.18",
    )

    ev_proc_y = b_box_y + 1.70
    ev_proc_h = 1.24
    draw_arrow(
        ax,
        s4_x + s4_w / 2,
        bar_y,
        s4_x + s4_w / 2,
        ev_proc_y + ev_proc_h,
        lw=1.05,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    draw_rect(
        ax,
        s4_x,
        ev_proc_y,
        s4_w,
        ev_proc_h,
        facecolor=c_proc,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s4_x + s4_w / 2,
        ev_proc_y + 0.86,
        "Blinded 5D Rubric Judge",
        fontsize=8.7,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        s4_x + s4_w / 2,
        ev_proc_y + 0.38,
        "2 independent judge passes\nVerbatim 1–3 anchors (Table A.2)",
        fontsize=7.95,
        color=c_black,
        ha="center",
        va="center",
        linespacing=1.36,
        zorder=4,
    )

    ev_out_y = b_box_y + 0.08
    ev_out_h = 1.24
    draw_arrow(
        ax,
        s4_x + s4_w / 2,
        ev_proc_y,
        s4_x + s4_w / 2,
        ev_out_y + ev_out_h,
        lw=1.05,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    draw_rect(
        ax,
        s4_x,
        ev_out_y,
        s4_w,
        ev_out_h,
        facecolor=c_white,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=3,
    )
    ax.text(
        s4_x + s4_w / 2,
        ev_out_y + 0.86,
        "Direct Task & Score Audit",
        fontsize=8.7,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        s4_x + s4_w / 2,
        ev_out_y + 0.38,
        "Compare rubric ratings against\ntask failure modes (Sec. 3.2)",
        fontsize=7.95,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.36,
        zorder=4,
    )

    # Horizontal arrows in Row (b)
    # Right-side collector spine joining all 4 topic cells into Stage 2
    spine_x = s1_x + s1_w + 0.16
    c_mids = [cy + cell_h / 2 for cy in cell_ys]
    for cm in c_mids:
        ax.plot([s1_x + s1_w, spine_x], [cm, cm], color=c_black, lw=1.0, zorder=4)
    ax.plot([spine_x, spine_x], [c_mids[-1], c_mids[0]], color=c_black, lw=1.0, zorder=4)
    draw_arrow(ax, spine_x, b_mid_y, s2_x, b_mid_y)
    draw_arrow(ax, s2_x + s2_w, b_mid_y, s3_x, b_mid_y)
    # Orthogonal arrow from Stage 3 (One-Shot Generation) up to 240 Saved PF Tasks
    mid_34_x = (s3_x + s3_w + s4_x) / 2
    target_4_y = st_y + 0.75
    ax.plot(
        [s3_x + s3_w, mid_34_x, mid_34_x],
        [b_mid_y, b_mid_y, target_4_y],
        color=c_black,
        lw=1.1,
        zorder=5,
    )
    draw_arrow(ax, mid_34_x, target_4_y, s4_x, target_4_y, lw=1.1)

    out_dir = Path("thesis/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "fig3_1_oneshot_setup.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out_dir / "fig3_1_oneshot_setup.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("Saved thesis/figures/fig3_1_oneshot_setup.{pdf,png}")


if __name__ == "__main__":
    main()
