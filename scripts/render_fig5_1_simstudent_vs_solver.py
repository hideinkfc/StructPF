"""Render Figure 5.1: simulated student versus prior-knowledge solver.

Monochrome JupyRecSys style matching Figures 4.1 and 5.2: sharp corners,
#CFCFCF model steps, #F2F2F2 containers, white inputs and outputs. The
consistency task is an illustrative teaching example, not a saved run.
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
        "title": "(a) Simulated Student",
        "principle": "Asks the model to perform worse than it can",
        "boxes": [
            (WHITE, "Task + Profile", "knows: mean, range\ndoes not know: spread"),
            (PROC, "LLM as Student", "answers as this student,\nincluding mistakes"),
            (
                WHITE,
                "Predicted Answer",
                "\u201cA stays closer to 10,\nso A is more consistent\u201d",
            ),
            (WHITE, "Task Verdict", "solved, so familiar\nmethods seem to suffice"),
        ],
        "note": "Problem: we cannot tell whether this is a student\u2019s invention or "
        "knowledge the model should have set aside.",
    },
    {
        "title": "(b) Prior-Knowledge Solver (Ours)",
        "principle": "Asks the model to do its best with listed skills only",
        "boxes": [
            (
                WHITE,
                "Task + Listed Skills",
                "mean: sum \u00f7 count\nrange: largest \u2212 smallest",
            ),
            (PROC, "Solver", "tries every listed skill,\nno deliberate errors"),
            (WHITE, "Written Attempts", "mean: 10 vs 10, tie\nrange: 12 vs 12, tie"),
            (PROC, "Attempt Judge", "knows the target,\nrejects unlisted steps"),
        ],
        "note": "Result: both listed skills stop at a tie, so the judge finds that familiar "
        "methods fall short because spread is needed.",
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

    W, H = 10.2, 5.50
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    task_x, task_w = 0.08, W - 0.16
    task_h = 0.62
    task_y = H - 0.08 - task_h
    draw_rect(ax, task_x, task_y, task_w, task_h, facecolor=WHITE, linewidth=1.05)
    ax.text(
        task_x + 0.18,
        task_y + task_h * 0.66,
        "Same task for (a) and (b), illustrative:",
        fontsize=11.0,
        fontweight="bold",
        color=BLACK,
        ha="left",
        va="center",
        zorder=4,
    )
    ax.text(
        task_x + 0.18,
        task_y + task_h * 0.28,
        "Which player is more consistent?   A: 4, 9, 10, 11, 16   "
        "B: 4, 8, 10, 12, 16   (both: mean 10, range 12)",
        fontsize=11.0,
        color=DARK,
        ha="left",
        va="center",
        zorder=4,
    )

    cont_x, cont_w = 0.08, W - 0.16
    cont_h = 2.20
    cont_gap = 0.16
    box_w, box_h = 2.20, 1.04
    arrow_gap = (cont_w - 0.36 - 4 * box_w) / 3

    for r, row in enumerate(ROWS):
        cont_y = task_y - cont_gap - (r + 1) * cont_h - r * cont_gap
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

        box_y = cont_y + 0.58
        ym = box_y + box_h / 2
        for i, (face, label, detail) in enumerate(row["boxes"]):
            x = cont_x + 0.18 + i * (box_w + arrow_gap)
            draw_rect(ax, x, box_y, box_w, box_h, facecolor=face, linewidth=1.05, zorder=3)
            ax.text(
                x + box_w / 2,
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
                x + box_w / 2,
                box_y + box_h * 0.34,
                detail,
                fontsize=10.0,
                color=DARK,
                ha="center",
                va="center",
                linespacing=1.25,
                zorder=4,
            )
            if i < 3:
                draw_arrow(ax, x + box_w, ym, x + box_w + arrow_gap, ym)

        ax.text(
            cont_x + 0.18,
            cont_y + 0.30,
            row["note"],
            fontsize=10.8,
            color=BLACK,
            ha="left",
            va="center",
            zorder=2,
        )

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig5_1_simstudent_vs_solver.pdf"
    png_path = out_dir / "fig5_1_simstudent_vs_solver.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
