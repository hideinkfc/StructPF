"""Render Figure 4.1: simple process model of the StructPF pipeline.

One top-to-bottom chain from the target standard to the student task. Each step
shows its bounded revision loop on the left and its external tool on the right.
Monochrome JupyRecSys style: sharp corners, #CFCFCF model steps, #F2F2F2 stage
containers, white inputs, outputs and tools.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BLACK = "#000000"
DARK = "#222222"
PROC = "#CFCFCF"
GROUP = "#F2F2F2"
HEAD = "#E2E2E2"
WHITE = "#FFFFFF"
HEAD_STYLE = "-|>,head_length=0.42,head_width=0.26"
SMALL_HEAD = "-|>,head_length=0.32,head_width=0.20"


def draw_rect(ax, x, y, w, h, facecolor=WHITE, linewidth=1.0, linestyle="-", zorder=2):
    ax.add_patch(
        Rectangle(
            (x, y), w, h, facecolor=facecolor, edgecolor=BLACK,
            linewidth=linewidth, linestyle=linestyle, zorder=zorder,
        )
    )


def draw_arrow(ax, x0, y0, x1, y1, lw=1.2, style=HEAD_STYLE, zorder=5):
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle=style, color=BLACK, lw=lw, shrinkA=0, shrinkB=0),
        zorder=zorder,
    )


def draw_polyline_arrow(ax, pts, lw=1.2, style=HEAD_STYLE, zorder=5):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=BLACK, lw=lw, zorder=zorder, solid_capstyle="butt")
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    draw_arrow(ax, x0, y0, x1, y1, lw=lw, style=style, zorder=zorder)


def block(ax, x, y, w, h, title, body=None, facecolor=PROC, linewidth=1.05):
    draw_rect(ax, x, y, w, h, facecolor=facecolor, linewidth=linewidth, zorder=3)
    cx = x + w / 2
    if body is None:
        ax.text(cx, y + h / 2, title, fontsize=12.5, fontweight="bold", color=BLACK,
                ha="center", va="center", linespacing=1.2, zorder=4)
    else:
        ax.text(cx, y + h * 0.66, title, fontsize=12.5, fontweight="bold", color=BLACK,
                ha="center", va="center", zorder=4)
        ax.text(cx, y + h * 0.30, body, fontsize=11.2, color=DARK,
                ha="center", va="center", linespacing=1.2, zorder=4)


def stage_container(ax, x, y, w, h, title):
    draw_rect(ax, x, y, w, h, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(x + 0.18, y + h - 0.24, title, fontsize=11.6, fontweight="bold", color=BLACK,
            ha="left", va="center", zorder=2)


def revision_loop(ax, x_left, y_top, y_bottom, label, loop_x):
    """Self-loop on the left side of a block: leave at y_top, return at y_bottom."""
    draw_polyline_arrow(
        ax,
        [(x_left, y_top), (loop_x, y_top), (loop_x, y_bottom), (x_left, y_bottom)],
        lw=1.05, style=SMALL_HEAD,
    )
    ax.text(loop_x - 0.14, (y_top + y_bottom) / 2, label, fontsize=10.8, color=DARK,
            ha="right", va="center", linespacing=1.2, zorder=4)


def tool_call(ax, x_block, x_tool, y_mid, out_label, back_label):
    """Two-way call between a model step (left) and an external tool (right)."""
    up, down = y_mid + 0.20, y_mid - 0.20
    draw_arrow(ax, x_block, up, x_tool, up, lw=1.05, style=SMALL_HEAD)
    draw_arrow(ax, x_tool, down, x_block, down, lw=1.05, style=SMALL_HEAD)
    xc = (x_block + x_tool) / 2
    ax.text(xc, up + 0.16, out_label, fontsize=9.8, color=DARK, ha="center", va="center", zorder=4)
    ax.text(xc, down - 0.17, back_label, fontsize=9.8, color=DARK, ha="center", va="center", zorder=4)


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42

    W, H = 8.6, 9.4
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    col_x, col_w = 2.45, 2.95
    cx = col_x + col_w / 2
    tool_x, tool_w = 6.62, 1.74
    loop_x = col_x - 0.38
    box_x, box_w = 0.12, W - 0.24

    # Input
    in_y, in_h = 8.72, 0.62
    block(ax, col_x, in_y, col_w, in_h, "Target Learning Concept", facecolor=WHITE, linewidth=1.0)

    # Legend (top left)
    draw_rect(ax, 0.16, 9.10, 0.28, 0.20, facecolor=PROC, linewidth=0.95, zorder=3)
    ax.text(0.52, 9.20, "LLM step", fontsize=10.4, color=DARK, ha="left", va="center")
    draw_rect(ax, 0.16, 8.78, 0.28, 0.20, facecolor=WHITE, linewidth=0.95, zorder=3)
    ax.text(0.52, 8.88, "Input, output or tool", fontsize=10.4, color=DARK, ha="left", va="center")

    # Stage 1
    s1_y, s1_h = 6.72, 1.62
    stage_container(ax, box_x, s1_y, box_w, s1_h, "Stage 1 (Sec. 4.2)")
    b1_y, b1_h = s1_y + 0.28, 0.94
    block(ax, col_x, b1_y, col_w, b1_h, "Identify Prior\nKnowledge")
    block(ax, tool_x, b1_y, tool_w, b1_h, "Learning\nCommons\nGraph", facecolor=WHITE, linewidth=1.0)
    tool_call(ax, col_x + col_w, tool_x, b1_y + b1_h / 2, "query", "prerequisites")
    draw_arrow(ax, cx, in_y, cx, b1_y + b1_h)

    # Stage 2
    s2_y, s2_h = 2.98, 3.36
    stage_container(ax, box_x, s2_y, box_w, s2_h, "Stage 2 (Sec. 4.3)")
    b2a_y, b2b_y, b2_h = s2_y + 1.94, s2_y + 0.28, 0.94
    block(ax, col_x, b2a_y, col_w, b2_h, "Step 2a: Propose &\nSelect Design Brief")
    block(ax, col_x, b2b_y, col_w, b2_h, "Step 2b: Choose &\nCheck Numbers")
    block(ax, tool_x, b2b_y, tool_w, b2_h, "Python\nMath\nCalculator", facecolor=WHITE, linewidth=1.0)
    revision_loop(ax, col_x, b2a_y + b2_h - 0.24, b2a_y + 0.24, "Revise brief\n(\u2264 2 times)", loop_x)
    revision_loop(ax, col_x, b2b_y + b2_h - 0.24, b2b_y + 0.24, "Repair numbers\n(\u2264 3 calls)", loop_x)
    tool_call(ax, col_x + col_w, tool_x, b2b_y + b2_h / 2, "check", "holds / fails")
    draw_arrow(ax, cx, b1_y, cx, b2a_y + b2_h)
    draw_arrow(ax, cx, b2a_y, cx, b2b_y + b2_h)

    # Stage 3
    s3_y, s3_h = 0.98, 1.62
    stage_container(ax, box_x, s3_y, box_w, s3_h, "Stage 3 (Sec. 4.4)")
    b3_y, b3_h = s3_y + 0.28, 0.94
    block(ax, col_x, b3_y, col_w, b3_h, "Write Open\nStudent Task")
    revision_loop(ax, col_x, b3_y + b3_h - 0.24, b3_y + 0.24, "Revise draft\n(\u2264 3 calls)", loop_x)
    draw_arrow(ax, cx, b2b_y, cx, b3_y + b3_h)

    # Output
    out_y, out_h = 0.08, 0.62
    block(ax, col_x, out_y, col_w, out_h, "Student-Facing PF Task", facecolor=WHITE, linewidth=1.3)
    draw_arrow(ax, cx, b3_y, cx, out_y + out_h)

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig4_1_structpf_overview.pdf"
    png_path = out_dir / "fig4_1_structpf_overview.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
