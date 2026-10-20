"""Render Figure 4.2: Learning Commons Knowledge Graph traversal and Stage 1 prior-skill mapping for 6.G.A.1.

Follows the monochrome JupyRecSys diagram style (#000000 borders, #CFCFCF LLM step,
#F2F2F2 group containers, #E2E2E2 headers, #FFFFFF data/graph nodes).
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BLACK = "#000000"
DARK = "#222222"
MID = "#4D4D4D"
PROC = "#CFCFCF"
SUB = "#E2E2E2"
GROUP = "#F2F2F2"
WHITE = "#FFFFFF"

HEAD_STYLE = "-|>,head_length=0.38,head_width=0.22"
SMALL_HEAD = "-|>,head_length=0.30,head_width=0.18"


def draw_rect(
    ax, x, y, w, h, facecolor=WHITE, edgecolor=BLACK, linewidth=1.0, linestyle="-", zorder=2
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


def draw_arrow(ax, x0, y0, x1, y1, lw=1.1, style=HEAD_STYLE, linestyle="-", zorder=5):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle=style,
            color=BLACK,
            lw=lw,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=zorder,
    )


def draw_polyline_arrow(ax, pts, lw=1.1, style=HEAD_STYLE, linestyle="-", zorder=5):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.plot(
            [x0, x1],
            [y0, y1],
            color=BLACK,
            lw=lw,
            linestyle=linestyle,
            zorder=zorder,
            solid_capstyle="butt",
        )
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    draw_arrow(ax, x0, y0, x1, y1, lw=lw, style=style, linestyle=linestyle, zorder=zorder)


def draw_header_card(
    ax,
    x,
    y,
    w,
    h,
    header_text,
    body_lines,
    header_h=0.34,
    facecolor=WHITE,
    header_fill=SUB,
    linestyle="-",
    zorder=3,
):
    draw_rect(
        ax, x, y, w, h, facecolor=facecolor, linewidth=1.0, linestyle=linestyle, zorder=zorder
    )
    draw_rect(
        ax,
        x,
        y + h - header_h,
        w,
        header_h,
        facecolor=header_fill,
        linewidth=1.0,
        linestyle=linestyle,
        zorder=zorder + 0.1,
    )
    ax.text(
        x + w / 2,
        y + h - header_h / 2,
        header_text,
        fontsize=9.4,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=zorder + 0.2,
    )
    body_y = y + (h - header_h) / 2
    ax.text(
        x + w / 2,
        body_y,
        "\n".join(body_lines),
        fontsize=8.8,
        color=DARK,
        ha="center",
        va="center",
        linespacing=1.22,
        zorder=zorder + 0.2,
    )


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42

    W, H = 13.0, 5.25
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # =========================================================================
    # 1. Left Container: Learning Commons Knowledge Graph (x = 0.12 to 6.58)
    # =========================================================================
    gx, gy, gw, gh = 0.12, 0.16, 6.46, 4.92
    draw_rect(ax, gx, gy, gw, gh, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(
        gx + 0.18,
        gy + gh - 0.26,
        "Learning Commons Knowledge Graph (Subgraph for 6.G.A.1)",
        fontsize=10.2,
        fontweight="bold",
        color=BLACK,
        ha="left",
        va="center",
        zorder=2,
    )

    col1_x, col2_x, col_w = 0.30, 3.46, 2.94
    cx1 = col1_x + col_w / 2
    cx2 = col2_x + col_w / 2

    # Top row inside Graph: Supporting Learning Components
    comp_y, comp_h = 3.52, 1.08
    draw_header_card(
        ax,
        col1_x,
        comp_y,
        col_w,
        comp_h,
        "Learning Components (4.MD.A.3)",
        ["Apply rectangle area and perimeter", "formulas to real-world & math problems"],
        header_h=0.31,
    )
    draw_header_card(
        ax,
        col2_x,
        comp_y,
        col_w,
        comp_h,
        "Learning Component (5.NF.B.4)",
        ["Multiply a whole number or", "fraction by a fraction"],
        header_h=0.31,
    )

    # Middle row inside Graph: Prerequisite Standards (Grade 4 & Grade 5)
    std_y, std_h = 1.92, 1.08
    draw_header_card(
        ax,
        col1_x,
        std_y,
        col_w,
        std_h,
        "Grade 4 Standard (4.MD.A.3)",
        ["Apply area and perimeter formulas", "for rectangles (A = l \u00d7 w)"],
        header_h=0.31,
    )
    draw_header_card(
        ax,
        col2_x,
        std_y,
        col_w,
        std_h,
        "Grade 5 Standard (5.NF.B.4)",
        ["Extend multiplication to multiply a", "whole number or fraction by a fraction"],
        header_h=0.31,
    )

    # Straight vertical "supports" arrows from Components down to Prerequisite Standards
    draw_arrow(ax, cx1, comp_y, cx1, std_y + std_h, lw=1.05, style=SMALL_HEAD)
    ax.text(
        cx1 + 0.12,
        (comp_y + std_y + std_h) / 2,
        "supports",
        fontsize=8.4,
        style="italic",
        color=DARK,
        ha="left",
        va="center",
    )
    draw_arrow(ax, cx2, comp_y, cx2, std_y + std_h, lw=1.05, style=SMALL_HEAD)
    ax.text(
        cx2 + 0.12,
        (comp_y + std_y + std_h) / 2,
        "supports",
        fontsize=8.4,
        style="italic",
        color=DARK,
        ha="left",
        va="center",
    )

    # Bottom row inside Graph: Target Learning Concept (Grade 6, 6.G.A.1)
    t_x, t_y, t_w, t_h = 0.62, 0.30, 5.46, 1.08
    draw_header_card(
        ax,
        t_x,
        t_y,
        t_w,
        t_h,
        "Target Learning Concept: Grade 6 Standard (6.G.A.1)",
        [
            "Find area of right triangles, other triangles, and polygons",
            "by composing into rectangles or decomposing into shapes",
        ],
        header_h=0.31,
        linestyle="--",
    )

    # Straight vertical "buildsTowards" arrows from Prerequisite Standards down to Target 6.G.A.1
    draw_arrow(ax, cx1, std_y, cx1, t_y + t_h, lw=1.05, style=SMALL_HEAD)
    ax.text(
        cx1 + 0.12,
        (std_y + t_y + t_h) / 2,
        "buildsTowards",
        fontsize=8.4,
        style="italic",
        color=DARK,
        ha="left",
        va="center",
    )
    draw_arrow(ax, cx2, std_y, cx2, t_y + t_h, lw=1.05, style=SMALL_HEAD)
    ax.text(
        cx2 + 0.12,
        (std_y + t_y + t_h) / 2,
        "buildsTowards",
        fontsize=8.4,
        style="italic",
        color=DARK,
        ha="left",
        va="center",
    )

    # =========================================================================
    # 2. Middle LLM Process Box: Stage 1 Mapping & No-Spoiler Filter
    # =========================================================================
    px, py, pw, ph = 7.36, 1.72, 1.94, 2.76
    draw_rect(ax, px, py, pw, ph, facecolor=PROC, linewidth=1.1, zorder=3)
    ax.text(
        px + pw / 2,
        py + ph - 0.46,
        "Stage 1:\nMap Prior\nKnowledge",
        fontsize=10.4,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        linespacing=1.2,
        zorder=4,
    )
    ax.plot(
        [px + 0.16, px + pw - 0.16], [py + ph - 0.94, py + ph - 0.94], color=BLACK, lw=0.8, zorder=4
    )
    ax.text(
        px + pw / 2,
        py + 0.90,
        "1. Extract taught\n   skill & first move\n2. State why it falls\n   short on 6.G.A.1\n3. Filter out target\n   formulas (\u00bd bh)",
        fontsize=8.4,
        color=DARK,
        ha="center",
        va="center",
        linespacing=1.24,
        zorder=4,
    )

    # Arrow from Prerequisite tier (components + standards) into Stage 1 Box
    prereq_out_y = 3.10
    draw_arrow(ax, gx + gw, prereq_out_y, px, prereq_out_y, lw=1.15, style=SMALL_HEAD)
    ax.text(
        (gx + gw + px) / 2,
        prereq_out_y + 0.24,
        "prereq.\nbundle",
        fontsize=8.3,
        color=DARK,
        ha="center",
        va="center",
        linespacing=1.15,
    )

    # Dashed boundary arrow from Target 6.G.A.1 to Stage 1 ("no-spoiler boundary")
    draw_polyline_arrow(
        ax,
        [(t_x + t_w, t_y + t_h / 2), (px + pw / 2, t_y + t_h / 2), (px + pw / 2, py)],
        lw=1.0,
        style=SMALL_HEAD,
        linestyle="--",
    )
    ax.text(
        (gx + gw + px + pw / 2) / 2,
        t_y + t_h / 2 - 0.20,
        "target boundary (withheld)",
        fontsize=8.3,
        style="italic",
        color=DARK,
        ha="center",
        va="center",
    )

    # =========================================================================
    # 3. Right Output Container: Prior-Skill Records (x = 9.76 to 12.88)
    # =========================================================================
    ox, oy, ow, oh = 9.74, 0.36, 3.14, 4.54
    draw_rect(ax, ox, oy, ow, oh, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(
        ox + ow / 2,
        oy + oh - 0.26,
        "Stage 1 Output: Prior-Skill Records",
        fontsize=9.6,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=2,
    )

    # Record 1
    r1_x, r1_y, r_w, r_h = ox + 0.14, 2.58, ow - 0.28, 1.88
    draw_rect(ax, r1_x, r1_y, r_w, r_h, facecolor=WHITE, linewidth=0.95, zorder=3)
    draw_rect(ax, r1_x, r1_y + r_h - 0.32, r_w, 0.32, facecolor=SUB, linewidth=0.95, zorder=3.1)
    ax.text(
        r1_x + r_w / 2,
        r1_y + r_h - 0.16,
        "Record 1: Rectangle Area (4.MD.A.3)",
        fontsize=8.5,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        r1_x + 0.12,
        r1_y + 0.78,
        "Taught as: Multiply length \u00d7 width.\nFirst move: Identify a rectangle and\n  multiply its length and width.\nFalls short: Cannot find slanted or\n  composite areas without splitting.",
        fontsize=8.1,
        color=DARK,
        ha="left",
        va="center",
        linespacing=1.24,
        zorder=4,
    )

    # Record 2
    r2_y = 0.54
    draw_rect(ax, r1_x, r2_y, r_w, r_h, facecolor=WHITE, linewidth=0.95, zorder=3)
    draw_rect(ax, r1_x, r2_y + r_h - 0.32, r_w, 0.32, facecolor=SUB, linewidth=0.95, zorder=3.1)
    ax.text(
        r1_x + r_w / 2,
        r2_y + r_h - 0.16,
        "Record 2: Fraction Product (5.NF.B.4)",
        fontsize=8.5,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        r1_x + 0.12,
        r2_y + 0.78,
        "Taught as: Multiply by a fraction.\nFirst move: Take a fractional part\n  (e.g., \u00bd) of a known product.\nFalls short: Needs a geometric reason\n  for why the triangle is \u00bd of a box.",
        fontsize=8.1,
        color=DARK,
        ha="left",
        va="center",
        linespacing=1.24,
        zorder=4,
    )

    # Arrow from Stage 1 Box to Output Container
    draw_arrow(ax, px + pw, py + ph / 2, ox, py + ph / 2, lw=1.15, style=HEAD_STYLE)

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig4_2_learning_commons_graph.pdf"
    png_path = out_dir / "fig4_2_learning_commons_graph.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
