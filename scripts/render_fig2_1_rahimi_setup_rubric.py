"""Render Figure 2.1: Overview of (a) the one-shot PF problem generation setup and
(b) the five-dimension evaluation rubric introduced by Rahimi et al. (2025, 2026).

Styled in the exact JupyRecSys / Figure 3.1 visual language:
- Sharp rectangular corners, monochrome/grayscale blocks (#F2F2F2 group containers,
  #E6E6E6 header strips, #CFCFCF process blocks, #FFFFFF data/rubric cards)
- Crisp 0.95pt black borders and orthogonal arrows.
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
    dx=0.045,
    dy=0.045,
    facecolor="#FFFFFF",
    edgecolor="#000000",
    linewidth=0.85,
    linestyle="-",
    zorder=2,
):
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
    style="-|>,head_length=0.36,head_width=0.21",
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


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["axes.edgecolor"] = "none"

    W, H = 12.8, 7.8
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Monochrome / JupyRecSys palette (matching Figure 3.1)
    c_black = "#000000"
    c_dark = "#222222"
    c_proc = "#CFCFCF"   # JupyRecSys process block gray
    c_group = "#F2F2F2"  # Outer container light gray
    c_sub = "#E6E6E6"    # Header strip gray
    c_white = "#FFFFFF"

    # ==========================================================================
    # ROW (a): One-Shot PF Task Generation and Evaluation Setup
    # ==========================================================================
    top_y, top_h = 4.22, 3.42
    draw_rect(
        ax, 0.14, top_y, 12.52, top_h,
        facecolor=c_group, edgecolor=c_black, linewidth=0.95, zorder=1
    )

    ax.text(
        0.28,
        top_y + top_h - 0.30,
        "(a) One-Shot PF Task Generation and Evaluation Setup in Rahimi et al. (2025, 2026)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )

    # Legend in top-right of Row (a)
    leg_y = top_y + top_h - 0.40
    draw_rect(ax, 9.50, leg_y, 0.26, 0.20, facecolor=c_white, edgecolor=c_black, linewidth=0.85, zorder=3)
    ax.text(9.82, leg_y + 0.10, "= Input / Artifact", fontsize=8.3, color=c_dark, ha="left", va="center")
    draw_rect(ax, 11.22, leg_y, 0.26, 0.20, facecolor=c_proc, edgecolor=c_black, linewidth=0.85, zorder=3)
    ax.text(11.54, leg_y + 0.10, "= Process", fontsize=8.3, color=c_dark, ha="left", va="center")

    box_y = top_y + 0.26
    box_h = 2.58
    mid_y = box_y + box_h / 2
    hdr_h = 0.44

    # 4 horizontal blocks in Row (a)
    # 1. Fixed Input | 2. Six-Part Prompt | 3. One-Shot Generation & Tasks | 4. Rubric Evaluation
    b1_x, b1_w = 0.30, 2.62
    b2_x, b2_w = 3.24, 3.16
    b3_x, b3_w = 6.72, 2.74
    b4_x, b4_w = 9.78, 2.72

    # Block 1: Fixed Input Specification
    draw_rect(ax, b1_x, box_y, b1_w, box_h, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
    draw_rect(ax, b1_x, box_y + box_h - hdr_h, b1_w, hdr_h, facecolor=c_sub, edgecolor=c_black, linewidth=0.8, zorder=3)
    ax.text(
        b1_x + b1_w / 2, box_y + box_h - hdr_h / 2,
        "1. Fixed Input Specification",
        fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", zorder=4,
    )
    ax.text(
        b1_x + 0.14, box_y + (box_h - hdr_h) / 2,
        "• Grade 7 mathematics (CCSSM)\n"
        "• Target: Ratios & proportionality\n"
        "• Prior: Unit rates & rational ops\n"
        "• Theme: Basketball (S. Curry)",
        fontsize=8.2, color=c_dark, ha="left", va="center", linespacing=1.55, zorder=4,
    )

    # Block 2: Six-Part One-Shot Prompt
    draw_rect(ax, b2_x, box_y, b2_w, box_h, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
    draw_rect(ax, b2_x, box_y + box_h - hdr_h, b2_w, hdr_h, facecolor=c_sub, edgecolor=c_black, linewidth=0.8, zorder=3)
    ax.text(
        b2_x + b2_w / 2, box_y + box_h - hdr_h / 2,
        "2. Six-Part One-Shot Prompt",
        fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", zorder=4,
    )
    ax.text(
        b2_x + 0.14, box_y + (box_h - hdr_h) / 2,
        "(1) Role description  (2) Response rules\n"
        "(3) Productive Failure overview\n"
        "(4) 5-dimension evaluation rubric (1–3)\n"
        "(5) 5 human-written PF example tasks\n"
        "(6) One-shot generation instructions",
        fontsize=8.1, color=c_dark, ha="left", va="center", linespacing=1.48, zorder=4,
    )

    # Block 3: One-Shot Generation (Process block containing model runs -> 60 tasks)
    draw_rect(ax, b3_x, box_y, b3_w, box_h, facecolor=c_proc, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(
        b3_x + b3_w / 2, box_y + box_h - 0.26,
        "3. One-Shot LLM Generation",
        fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", zorder=4,
    )
    # Inner white card for the two models
    in3_x = b3_x + 0.16
    in3_w = b3_w - 0.32
    draw_rect(ax, in3_x, box_y + 1.06, in3_w, 1.04, facecolor=c_white, edgecolor=c_black, linewidth=0.8, zorder=4)
    ax.text(
        in3_x + in3_w / 2, box_y + 1.58,
        "Single-Pass Generation (60 Tasks)\n"
        "• GPT-4o (Large LLM): 30 tasks\n"
        "• Phi-3 mini (3.8B SLM): 30 tasks",
        fontsize=8.0, color=c_dark, ha="center", va="center", linespacing=1.42, zorder=5,
    )
    draw_stack(
        ax, in3_x + 0.08, box_y + 0.18, in3_w - 0.24, 0.58,
        n=3, dx=0.045, dy=0.045, facecolor=c_white, edgecolor=c_black, linewidth=0.8, zorder=4
    )
    ax.text(
        in3_x + 0.08 + (in3_w - 0.24) / 2, box_y + 0.47,
        "60 Generated PF Tasks",
        fontsize=8.2, fontweight="bold", color=c_black, ha="center", va="center", zorder=6,
    )

    # Block 4: Evaluation Process
    draw_rect(ax, b4_x, box_y, b4_w, box_h, facecolor=c_proc, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(
        b4_x + b4_w / 2, box_y + box_h - 0.26,
        "4. Rubric Evaluation",
        fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", zorder=4,
    )
    in4_x = b4_x + 0.16
    in4_w = b4_w - 0.32
    draw_rect(ax, in4_x, box_y + 0.20, in4_w, 1.90, facecolor=c_white, edgecolor=c_black, linewidth=0.8, zorder=4)
    ax.text(
        in4_x + 0.12, box_y + 1.15,
        "• 2 blinded human raters\n"
        "  (or GPT-4o automated judge)\n"
        "• 3rd rater adjudication if gap ≥ 5\n"
        "• Scored on 5 dimensions below\n"
        "  (1–3 each; total score 5–15)",
        fontsize=8.0, color=c_dark, ha="left", va="center", linespacing=1.45, zorder=5,
    )

    # Horizontal arrows connecting 1 -> 2 -> 3 -> 4
    draw_arrow(ax, b1_x + b1_w, mid_y, b2_x, mid_y)
    draw_arrow(ax, b2_x + b2_w, mid_y, b3_x, mid_y)
    draw_arrow(ax, b3_x + b3_w, mid_y, b4_x, mid_y)

    # Vertical transition arrow from Block 4 (Evaluation) to Row (b)
    bot_y, bot_h = 0.16, 3.36
    trans_x = b4_x + b4_w / 2
    draw_arrow(ax, trans_x, top_y, trans_x, bot_y + bot_h, lw=1.15)
    ax.text(
        trans_x - 0.14, (top_y + bot_y + bot_h) / 2,
        "Uses 5-Dimension Rubric (1–3 each)",
        fontsize=8.6, fontweight="bold", color=c_black, ha="right", va="center",
    )

    # ==========================================================================
    # ROW (b): Five-Dimension PF Evaluation Rubric
    # ==========================================================================
    draw_rect(
        ax, 0.14, bot_y, 12.52, bot_h,
        facecolor=c_group, edgecolor=c_black, linewidth=0.95, zorder=1
    )

    ax.text(
        0.28,
        bot_y + bot_h - 0.30,
        "(b) Five-Dimension PF Evaluation Rubric (Each Dimension Scored 1–3; Total Score 5–15)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )

    r_y = bot_y + 0.24
    r_h = 2.54
    r_gap = 0.15
    r_w = (12.52 - 0.32 - 4 * r_gap) / 5  # 5 equal cards across 12.20 width
    r_x0 = 0.30

    rubric_dims = [
        (
            "1. APK (1–3)",
            "Activation of\nPrior Knowledge",
            "Builds on taught prior\nskills without requiring\nuntaught concepts\n"
            "(1: None · 2: 1 skill · 3: ≥2)",
        ),
        (
            "2. SSC (1–3)",
            "Sweet Spot\nCalibration",
            "Challenging enough not\nto be trivial, yet\nmanageable to attempt\n"
            "(1: Too easy/hard · 3: Calibrated)",
        ),
        (
            "3. AE (1–3)",
            "Affective\nEngagement",
            "Connects to student\ninterests with a relatable,\nreal-world narrative\n"
            "(1: Unrelatable · 3: Engaging)",
        ),
        (
            "4. MR (1–3)",
            "Multiple\nRepresentations",
            "Invites diverse tables,\ngraphs, equations, or\nsolution methods\n"
            "(1: Few/none · 3: Wide range)",
        ),
        (
            "5. OE (1–3)",
            "Open-Endedness /\nIll-Structuredness",
            "Requires integrating\nmultiple variables and\nrepresentations\n"
            "(1: Single path · 3: Complex)",
        ),
    ]

    for idx, (code_lbl, title_lbl, desc_lbl) in enumerate(rubric_dims):
        rx = r_x0 + idx * (r_w + r_gap)
        draw_rect(ax, rx, r_y, r_w, r_h, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
        draw_rect(ax, rx, r_y + r_h - 0.42, r_w, 0.42, facecolor=c_sub, edgecolor=c_black, linewidth=0.8, zorder=3)
        ax.text(
            rx + r_w / 2, r_y + r_h - 0.21,
            code_lbl,
            fontsize=8.9, fontweight="bold", color=c_black, ha="center", va="center", zorder=4,
        )
        ax.text(
            rx + r_w / 2, r_y + r_h - 0.78,
            title_lbl,
            fontsize=8.5, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.28, zorder=4,
        )
        ax.plot([rx + 0.16, rx + r_w - 0.16], [r_y + r_h - 1.15, r_y + r_h - 1.15], color=c_black, lw=0.70, zorder=4)
        ax.text(
            rx + r_w / 2, r_y + 0.70,
            desc_lbl,
            fontsize=7.85, color=c_dark, ha="center", va="center", linespacing=1.42, zorder=4,
        )

    out_dir = Path("thesis/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "fig2_1_rahimi_setup_rubric.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out_dir / "fig2_1_rahimi_setup_rubric.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("Saved thesis/figures/fig2_1_rahimi_setup_rubric.{pdf,png}")


if __name__ == "__main__":
    main()
