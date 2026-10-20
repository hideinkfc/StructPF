"""Render Figure 5.2: questions a human PF designer asks, mapped to automated checks.

Monochrome JupyRecSys style matching Figure 4.1: sharp corners, #CFCFCF model
steps, #F2F2F2 containers, white question boxes.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BLACK = "#000000"
DARK = "#222222"
PROC = "#CFCFCF"
GROUP = "#F2F2F2"
WHITE = "#FFFFFF"
HEAD_STYLE = "-|>,head_length=0.42,head_width=0.26"

ROWS = [
    (
        "",
        "Does the task target the concept\nwith correct mathematics?",
        "Task Judge",
        "Target alignment and mathematical validity",
    ),
    (
        "Req. 1",
        "Can students start with\nwhat they already know?",
        "Task Judge",
        "Prior-knowledge accessibility",
    ),
    (
        "Req. 2",
        "Do familiar methods fall short\nfor the target reason?",
        "Prior-Knowledge Solver + Attempt Judge",
        "Limits of familiar approaches",
    ),
    ("Req. 3", "Is the key idea left\nfor students to invent?", "Task Judge", "Room for invention"),
]


def draw_rect(ax, x, y, w, h, facecolor=WHITE, linewidth=1.0, zorder=2):
    ax.add_patch(
        Rectangle(
            (x, y), w, h, facecolor=facecolor, edgecolor=BLACK, linewidth=linewidth, zorder=zorder
        )
    )


def container(ax, x, y, w, h, title):
    draw_rect(ax, x, y, w, h, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(
        x + 0.18,
        y + h - 0.26,
        title,
        fontsize=12.4,
        fontweight="bold",
        color=BLACK,
        ha="left",
        va="center",
        zorder=2,
    )


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42

    W, H = 10.2, 5.25
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    left_x, left_w = 0.08, 4.54
    right_x, right_w = 5.30, 4.82
    cont_y, cont_h = 0.08, H - 0.16
    container(ax, left_x, cont_y, left_w, cont_h, "Human PF Designer Asks")
    container(ax, right_x, cont_y, right_w, cont_h, "Automated Check")

    q_x, q_w = 1.02, 3.40
    c_x, c_w = 5.48, 4.46
    row_h, gap = 0.94, 0.20
    top = cont_y + cont_h - 0.58

    for i, (tag, question, role, measure) in enumerate(ROWS):
        y = top - (i + 1) * row_h - i * gap
        ym = y + row_h / 2
        if tag:
            ax.text(
                left_x + 0.20,
                ym,
                tag,
                fontsize=11.0,
                fontstyle="italic",
                color=DARK,
                ha="left",
                va="center",
                zorder=4,
            )
        draw_rect(ax, q_x, y, q_w, row_h, facecolor=WHITE, linewidth=1.0, zorder=3)
        ax.text(
            q_x + q_w / 2,
            ym,
            question,
            fontsize=11.6,
            color=BLACK,
            ha="center",
            va="center",
            linespacing=1.25,
            zorder=4,
        )

        draw_rect(ax, c_x, y, c_w, row_h, facecolor=PROC, linewidth=1.05, zorder=3)
        ax.text(
            c_x + c_w / 2,
            y + row_h * 0.67,
            role,
            fontsize=11.4,
            fontweight="bold",
            color=BLACK,
            ha="center",
            va="center",
            zorder=4,
        )
        ax.text(
            c_x + c_w / 2,
            y + row_h * 0.31,
            measure,
            fontsize=11.0,
            color=DARK,
            ha="center",
            va="center",
            zorder=4,
        )

        ax.annotate(
            "",
            xy=(c_x, ym),
            xytext=(q_x + q_w, ym),
            arrowprops=dict(arrowstyle=HEAD_STYLE, color=BLACK, lw=1.2, shrinkA=0, shrinkB=0),
            zorder=5,
        )

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig5_2_eval_overview.pdf"
    png_path = out_dir / "fig5_2_eval_overview.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
