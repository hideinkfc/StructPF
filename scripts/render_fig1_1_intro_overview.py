"""Render Figure 1.1: Overview of (a) existing one-shot PF generation and rubric scoring (G1)
versus (b) our staged generation pipeline StructPF and requirement-based evaluation (G2-G4).

Styled in the exact JupyRecSys / Figure 3.1 visual language:
- Sharp rectangular corners, monochrome/grayscale blocks (#F2F2F2 group containers,
  #E6E6E6 header strips, #CFCFCF process blocks, #FFFFFF input/artifact cards)
- Crisp 0.95pt black borders and orthogonal/clean arrows, with generous vertical height.
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
    linewidth=0.95,
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


def draw_arrow(
    ax,
    x0,
    y0,
    x1,
    y1,
    color="#000000",
    lw=1.15,
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


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["axes.edgecolor"] = "none"

    W, H = 12.8, 7.2
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # Monochrome / JupyRecSys palette (matching Figure 3.1)
    c_black = "#000000"
    c_dark = "#222222"
    c_proc = "#CFCFCF"  # JupyRecSys process block gray
    c_group = "#F2F2F2"  # Outer container light gray
    c_sub = "#E6E6E6"  # Header strip gray
    c_white = "#FFFFFF"

    # ==========================================================================
    # SHARED LEFT INPUT BLOCK
    # ==========================================================================
    in_x, in_w = 0.16, 2.18
    in_y, in_h = 1.62, 3.96
    in_hdr_h = 0.50

    draw_rect(
        ax, in_x, in_y, in_w, in_h, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3
    )
    draw_rect(
        ax,
        in_x,
        in_y + in_h - in_hdr_h,
        in_w,
        in_hdr_h,
        facecolor=c_sub,
        edgecolor=c_black,
        linewidth=0.85,
        zorder=3,
    )
    ax.text(
        in_x + in_w / 2,
        in_y + in_h - in_hdr_h / 2,
        "Input",
        fontsize=9.8,
        fontweight="bold",
        color=c_black,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        in_x + in_w / 2,
        in_y + (in_h - in_hdr_h) / 2,
        "Target Concept\nto Introduce\nBefore Instruction",
        fontsize=9.0,
        color=c_dark,
        ha="center",
        va="center",
        linespacing=1.50,
        zorder=4,
    )

    # ==========================================================================
    # RIGHT CONTAINERS: ROW (a) AND ROW (b)
    # ==========================================================================
    grp_x, grp_w = 2.68, 9.96
    top_y, top_h = 3.78, 3.24
    bot_y, bot_h = 0.18, 3.24

    # Outer containers
    draw_rect(
        ax,
        grp_x,
        top_y,
        grp_w,
        top_h,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=1,
    )
    draw_rect(
        ax,
        grp_x,
        bot_y,
        grp_w,
        bot_h,
        facecolor=c_group,
        edgecolor=c_black,
        linewidth=0.95,
        zorder=1,
    )

    # Titles for (a) and (b)
    ax.text(
        grp_x + 0.22,
        top_y + top_h - 0.32,
        "(a) Existing Approach: One-Shot Generation and Rubric Scoring (G1)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )
    ax.text(
        grp_x + 0.22,
        bot_y + bot_h - 0.32,
        "(b) Our Approach: Staged Generation and Requirement-Based Evaluation (G2–G4)",
        fontsize=10.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )

    # Legend in top-right of Row (a)
    leg_y = top_y + top_h - 0.42
    draw_rect(
        ax, 9.52, leg_y, 0.26, 0.20, facecolor=c_white, edgecolor=c_black, linewidth=0.85, zorder=3
    )
    ax.text(
        9.84, leg_y + 0.10, "= Input / Artifact", fontsize=8.3, color=c_dark, ha="left", va="center"
    )
    draw_rect(
        ax, 11.24, leg_y, 0.26, 0.20, facecolor=c_proc, edgecolor=c_black, linewidth=0.85, zorder=3
    )
    ax.text(11.56, leg_y + 0.10, "= Process", fontsize=8.3, color=c_dark, ha="left", va="center")

    # Shared 3-column geometry inside (a) and (b)
    b_gap = 0.38
    b_w = (grp_w - 0.44 - 2 * b_gap) / 3  # 3 equal blocks across inner width
    b1_x = grp_x + 0.22
    b2_x = b1_x + b_w + b_gap
    b3_x = b2_x + b_w + b_gap

    box_h = 2.34
    hdr_h = 0.48

    # ------------------------------------------------------------------
    # ROW (a) BLOCKS
    # ------------------------------------------------------------------
    a_y = top_y + 0.26
    a_mid_y = a_y + box_h / 2

    a_blocks = [
        (
            b1_x,
            c_proc,
            "One-Shot Prompting",
            "Asks LLM to write the\ncomplete PF task in\none pass",
        ),
        (
            b2_x,
            c_white,
            "Generated Task",
            "Routine story problem\nsolvable with familiar methods,\nor step-by-step hints",
        ),
        (
            b3_x,
            c_proc,
            "Broad Rubric Evaluation",
            "Rates surface features\n(engaging story, open wording)\nrather than the 3 requirements",
        ),
    ]

    for bx, bfill, btitle, bbody in a_blocks:
        draw_rect(
            ax, bx, a_y, b_w, box_h, facecolor=bfill, edgecolor=c_black, linewidth=0.95, zorder=3
        )
        draw_rect(
            ax,
            bx,
            a_y + box_h - hdr_h,
            b_w,
            hdr_h,
            facecolor=c_sub if bfill == c_white else c_proc,
            edgecolor=c_black,
            linewidth=0.85,
            zorder=3,
        )
        ax.text(
            bx + b_w / 2,
            a_y + box_h - hdr_h / 2,
            btitle,
            fontsize=9.3,
            fontweight="bold",
            color=c_black,
            ha="center",
            va="center",
            zorder=4,
        )
        ax.text(
            bx + b_w / 2,
            a_y + (box_h - hdr_h) / 2,
            bbody,
            fontsize=8.6,
            color=c_dark,
            ha="center",
            va="center",
            linespacing=1.48,
            zorder=4,
        )

    draw_arrow(ax, b1_x + b_w, a_mid_y, b2_x, a_mid_y)
    draw_arrow(ax, b2_x + b_w, a_mid_y, b3_x, a_mid_y)

    # ------------------------------------------------------------------
    # ROW (b) BLOCKS
    # ------------------------------------------------------------------
    b_y = bot_y + 0.26
    b_mid_y = b_y + box_h / 2

    b_blocks = [
        (
            b1_x,
            c_proc,
            "StructPF Pipeline (G2)",
            "Follows human teacher design\ndecisions, grounded in students'\nprior knowledge in checked steps",
        ),
        (
            b2_x,
            c_white,
            "Generated PF Task",
            "Accessible with familiar\nmethods, numbers make them\nfail, and open wording",
        ),
        (
            b3_x,
            c_proc,
            "Direct Evaluation (G3)",
            "Tests the 3 PF requirements\ndirectly instead of rating a\ngeneral impression of the text",
        ),
    ]

    for bx, bfill, btitle, bbody in b_blocks:
        draw_rect(
            ax, bx, b_y, b_w, box_h, facecolor=bfill, edgecolor=c_black, linewidth=0.95, zorder=3
        )
        draw_rect(
            ax,
            bx,
            b_y + box_h - hdr_h,
            b_w,
            hdr_h,
            facecolor=c_sub if bfill == c_white else c_proc,
            edgecolor=c_black,
            linewidth=0.85,
            zorder=3,
        )
        ax.text(
            bx + b_w / 2,
            b_y + box_h - hdr_h / 2,
            btitle,
            fontsize=9.3,
            fontweight="bold",
            color=c_black,
            ha="center",
            va="center",
            zorder=4,
        )
        ax.text(
            bx + b_w / 2,
            b_y + (box_h - hdr_h) / 2,
            bbody,
            fontsize=8.6,
            color=c_dark,
            ha="center",
            va="center",
            linespacing=1.48,
            zorder=4,
        )

    draw_arrow(ax, b1_x + b_w, b_mid_y, b2_x, b_mid_y)
    draw_arrow(ax, b2_x + b_w, b_mid_y, b3_x, b_mid_y)

    # Arrows from Shared Input to Row (a) Block 1 and Row (b) Block 1
    draw_arrow(ax, in_x + in_w, in_y + in_h * 0.68, b1_x, a_mid_y)
    draw_arrow(ax, in_x + in_w, in_y + in_h * 0.32, b1_x, b_mid_y)

    out_dir = Path("thesis/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "fig1_1_intro_overview.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(
        out_dir / "fig1_1_intro_overview.png", dpi=300, bbox_inches="tight", pad_inches=0.04
    )
    plt.close(fig)
    print("Saved thesis/figures/fig1_1_intro_overview.{pdf,png}")


if __name__ == "__main__":
    main()
