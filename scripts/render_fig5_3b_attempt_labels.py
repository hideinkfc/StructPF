"""Render Figure 5.3b: Attempt-judge labels and priority rule for Limits of Familiar Approaches.

Monochrome JupyRecSys style matching Figures 5.1, 5.2, and 5.3: sharp corners,
#CFCFCF shaded blocks, #F2F2F2 containers, white cards, and explicit priority arrows.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BLACK = "#000000"
DARK = "#222222"
MID = "#555555"
PROC = "#CFCFCF"
LIGHT_GREY = "#E4E4E4"
GROUP = "#F2F2F2"
WHITE = "#FFFFFF"
HEAD_STYLE = "-|>,head_length=0.40,head_width=0.24"

ROWS = [
    (
        "Target limit",
        "familiar method hits\nthe target impasse",
        "Compares means (10 vs. 10)\n\u2192 tie needs spread to break",
        "Yes",
        "if \u2265 1 Target limit\n(familiar method falls short)",
        PROC,
    ),
    (
        "Meets demands",
        "listed skills solve\nthe task completely",
        "Sums distances from 10 (14 vs. 16)\n\u2192 picks Player A",
        "No",
        "if \u2265 1 Meets demands\n(solved by prior skills)",
        WHITE,
    ),
    (
        "Unresolved",
        "stops after setup\nwithout answering",
        "Sorts each player\u2019s five scores,\nthen stops before comparing",
        "Unclear",
        "only Unresolved remain\n(no finished attempt)",
        WHITE,
    ),
    (
        "Unrelated shortfall",
        "blocked by a flaw\nin the task itself",
        "Stops because task text misstates\nPlayer A\u2019s mean as 11",
        None,
        None,
        LIGHT_GREY,
    ),
    (
        "Unsupported",
        "uses untaught concept\nor miscalculates",
        "Applies the untaught standard\ndeviation formula directly",
        None,
        None,
        LIGHT_GREY,
    ),
]


def draw_rect(ax, x, y, w, h, facecolor=WHITE, linewidth=1.0, linestyle="-", zorder=2):
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=facecolor,
            edgecolor=BLACK,
            linewidth=linewidth,
            linestyle=linestyle,
            zorder=zorder,
        )
    )


def draw_arrow(ax, x0, y0, x1, y1, lw=1.2):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle=HEAD_STYLE, color=BLACK, lw=lw, shrinkA=0, shrinkB=0),
        zorder=5,
    )


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42

    W, H = 10.2, 5.80
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    left_x, left_w = 0.08, 6.72
    right_x, right_w = 7.22, 2.90
    cont_y, cont_h = 0.08, H - 0.16

    # Left container: Attempt Judge classification
    draw_rect(ax, left_x, cont_y, left_w, cont_h, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(
        left_x + 0.18,
        cont_y + cont_h - 0.27,
        "(a) Attempt Judge Labels",
        fontsize=12.0,
        fontweight="bold",
        color=BLACK,
        ha="left",
        va="center",
        zorder=2,
    )
    ax.text(
        left_x + left_w - 0.18,
        cont_y + cont_h - 0.27,
        "Consistency task examples",
        fontsize=10.8,
        fontstyle="italic",
        color=DARK,
        ha="right",
        va="center",
        zorder=2,
    )

    # Right container: Task-level Limits Outcome
    draw_rect(ax, right_x, cont_y, right_w, cont_h, facecolor=GROUP, linewidth=1.05, zorder=1)
    ax.text(
        right_x + 0.18,
        cont_y + cont_h - 0.27,
        "(b) Limits Outcome",
        fontsize=12.0,
        fontweight="bold",
        color=BLACK,
        ha="left",
        va="center",
        zorder=2,
    )

    lbl_x, lbl_w = left_x + 0.18, 2.52
    ex_x, ex_w = lbl_x + lbl_w + 0.14, 3.70
    out_x, out_w = right_x + 0.18, right_w - 0.36

    row_h = 0.78
    gap_valid = 0.30
    divider_gap = 0.34
    gap_excl = 0.18
    top_y = cont_y + cont_h - 0.56

    row_ys = []
    curr_y = top_y
    for i in range(5):
        curr_y -= row_h
        row_ys.append(curr_y)
        if i in (0, 1):
            curr_y -= gap_valid
        elif i == 2:
            curr_y -= divider_gap
        elif i == 3:
            curr_y -= gap_excl

    # Dashed divider between valid prior-knowledge attempts (rows 0..2) and excluded (rows 3..4)
    div_y = row_ys[2] - divider_gap / 2
    ax.plot(
        [left_x + 0.16, right_x + right_w - 0.16],
        [div_y, div_y],
        color=MID,
        linestyle="--",
        linewidth=1.0,
        zorder=3,
    )

    for i, (label, meaning, example, out_title, out_sub, out_face) in enumerate(ROWS):
        y = row_ys[i]
        ym = y + row_h / 2
        lbl_face = PROC if i < 3 else LIGHT_GREY

        # Label + meaning box
        draw_rect(ax, lbl_x, y, lbl_w, row_h, facecolor=lbl_face, linewidth=1.0, zorder=3)
        ax.text(
            lbl_x + lbl_w / 2,
            y + row_h * 0.72,
            label,
            fontsize=10.8,
            fontweight="bold",
            color=BLACK,
            ha="center",
            va="center",
            zorder=4,
        )
        ax.text(
            lbl_x + lbl_w / 2,
            y + row_h * 0.30,
            meaning,
            fontsize=9.6,
            color=DARK,
            ha="center",
            va="center",
            linespacing=1.18,
            zorder=4,
        )

        # Example box
        draw_rect(ax, ex_x, y, ex_w, row_h, facecolor=WHITE, linewidth=1.0, zorder=3)
        ax.text(
            ex_x + ex_w / 2,
            ym,
            example,
            fontsize=9.8,
            color=BLACK,
            ha="center",
            va="center",
            linespacing=1.22,
            zorder=4,
        )

        # Outcome box for rows 0..2
        if out_title is not None:
            draw_rect(ax, out_x, y, out_w, row_h, facecolor=out_face, linewidth=1.05, zorder=3)
            ax.text(
                out_x + out_w / 2,
                y + row_h * 0.72,
                f"Outcome: {out_title}",
                fontsize=10.8,
                fontweight="bold",
                color=BLACK,
                ha="center",
                va="center",
                zorder=4,
            )
            ax.text(
                out_x + out_w / 2,
                y + row_h * 0.30,
                out_sub,
                fontsize=9.5,
                color=DARK,
                ha="center",
                va="center",
                linespacing=1.18,
                zorder=4,
            )
            draw_arrow(ax, ex_x + ex_w, ym, out_x, ym)

    # Priority arrows between Yes -> No -> Unclear
    for i in (0, 1):
        y_top = row_ys[i]
        y_bot = row_ys[i + 1] + row_h
        xm = out_x + out_w / 2
        draw_arrow(ax, xm, y_top, xm, y_bot, lw=1.1)
        ax.text(
            xm + 0.10,
            (y_top + y_bot) / 2,
            "if none",
            fontsize=9.4,
            fontstyle="italic",
            color=BLACK,
            ha="left",
            va="center",
            zorder=5,
        )

    # Excluded spanning box for rows 3..4
    excl_y = row_ys[4]
    excl_h = (row_ys[3] + row_h) - row_ys[4]
    draw_rect(
        ax,
        out_x,
        excl_y,
        out_w,
        excl_h,
        facecolor=LIGHT_GREY,
        linewidth=1.0,
        linestyle="--",
        zorder=3,
    )
    ax.text(
        out_x + out_w / 2,
        excl_y + excl_h * 0.64,
        "Excluded",
        fontsize=10.8,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        out_x + out_w / 2,
        excl_y + excl_h * 0.36,
        "ignored when deriving\nthe task outcome",
        fontsize=9.6,
        color=DARK,
        ha="center",
        va="center",
        linespacing=1.20,
        zorder=4,
    )
    for i in (3, 4):
        ym = row_ys[i] + row_h / 2
        draw_arrow(ax, ex_x + ex_w, ym, out_x, ym)

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig5_3b_attempt_labels.pdf"
    png_path = out_dir / "fig5_3b_attempt_labels.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()
