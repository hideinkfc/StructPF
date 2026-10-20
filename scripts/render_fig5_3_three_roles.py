"""Render Figure 5.3: the three evaluation roles and what each one sees.

Monochrome JupyRecSys style matching Figures 4.1, 5.1 and 5.2: sharp corners,
#CFCFCF model steps, #F2F2F2 containers, white inputs and outputs.
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
    {
        "title": "Reading the Task",
        "principle": "Does not see the solver\u2019s attempts",
        "boxes": [
            (WHITE, "Task + Skills + Target", "student task, listed\nskills, target concept", 1),
            (PROC, "Task Judge", "quotes the task,\nchecks with calculator", 1),
            (
                WHITE,
                "Four Verdicts",
                "target alignment, mathematical validity,\naccessibility, room for invention",
                2,
            ),
        ],
    },
    {
        "title": "Trying Familiar Methods",
        "principle": "Only the solver is blind to the target",
        "boxes": [
            (WHITE, "Task + Skills", "target concept\nwithheld", 1),
            (PROC, "Solver", "2 to 4 complete attempts,\nfamiliar methods first", 1),
            (PROC, "Attempt Judge", "also sees the target,\nlabels each attempt", 1),
            (WHITE, "Limits Verdict", "derived in code\nfrom the labels", 1),
        ],
    },
]


def draw_rect(ax, x, y, w, h, facecolor=WHITE, linewidth=1.0, zorder=2):
    ax.add_patch(
        Rectangle(
            (x, y), w, h, facecolor=facecolor, edgecolor=BLACK, linewidth=linewidth, zorder=zorder
        )
    )


def draw_arrow(ax, x0, y0, x1, y1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle=HEAD_STYLE, color=BLACK, lw=1.2, shrinkA=0, shrinkB=0),
        zorder=5,
    )


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42

    cont_h, cont_gap = 1.80, 0.56
    W, H = 10.2, 0.16 + 2 * cont_h + cont_gap
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    cont_x, cont_w = 0.08, W - 0.16
    box_w, box_h = 2.20, 1.04
    arrow_gap = (cont_w - 0.36 - 4 * box_w) / 3
    col_x = [cont_x + 0.18 + i * (box_w + arrow_gap) for i in range(4)]
    box_bottoms = []

    for r, row in enumerate(ROWS):
        cont_y = H - 0.08 - (r + 1) * cont_h - r * cont_gap
        draw_rect(ax, cont_x, cont_y, cont_w, cont_h, facecolor=GROUP, linewidth=1.05, zorder=1)
        title_y = cont_y + cont_h - 0.27
        ax.text(
            cont_x + 0.18,
            title_y,
            row["title"],
            fontsize=12.4,
            fontweight="bold",
            color=BLACK,
            ha="left",
            va="center",
            zorder=2,
        )
        ax.text(
            cont_x + cont_w - 0.18,
            title_y,
            row["principle"],
            fontsize=11.4,
            fontstyle="italic",
            color=BLACK,
            ha="right",
            va="center",
            zorder=2,
        )

        box_y = cont_y + 0.20
        box_bottoms.append(box_y)
        ym = box_y + box_h / 2
        col = 0
        for i, (face, label, detail, span) in enumerate(row["boxes"]):
            x = col_x[col]
            w = span * box_w + (span - 1) * arrow_gap
            draw_rect(ax, x, box_y, w, box_h, facecolor=face, linewidth=1.05, zorder=3)
            ax.text(
                x + w / 2,
                box_y + box_h * 0.76,
                label,
                fontsize=10.8,
                fontweight="bold",
                color=BLACK,
                ha="center",
                va="center",
                zorder=4,
            )
            ax.text(
                x + w / 2,
                box_y + box_h * 0.34,
                detail,
                fontsize=10.0,
                color=DARK,
                ha="center",
                va="center",
                linespacing=1.25,
                zorder=4,
            )
            if i < len(row["boxes"]) - 1:
                draw_arrow(ax, x + w, ym, x + w + arrow_gap, ym)
            col += span

    gate_x = col_x[1] + box_w / 2
    draw_arrow(ax, gate_x, box_bottoms[0], gate_x, box_bottoms[1] + box_h)
    ax.text(
        gate_x + 0.12,
        box_bottoms[0] - 0.20 - cont_gap / 2,
        "runs only if accessibility is Yes",
        fontsize=10.6,
        fontstyle="italic",
        color=BLACK,
        ha="left",
        va="center",
        zorder=4,
    )

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig5_3_three_roles.pdf"
    png_path = out_dir / "fig5_3_three_roles.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
