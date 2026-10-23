"""Render Figure 6.1 (Study a setup) and Figure 6.2 (Study b setup + Two-Step Check)
for Section 6.1 of Chapter 6.

Monochrome style matching Figures 3.1, 3.3, and 5.2: sharp corners, #CFCFCF model
steps, #F2F2F2 containers, white inner cards, #4D4D4D dark badges.
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
HEAD_STYLE = "-|>,head_length=0.38,head_width=0.24"

OUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures"


def draw_rect(ax, x, y, w, h, facecolor=WHITE, linewidth=0.95, zorder=2):
    ax.add_patch(
        Rectangle(
            (x, y), w, h, facecolor=facecolor, edgecolor=BLACK, linewidth=linewidth, zorder=zorder
        )
    )


def labelled_box(ax, x, y, w, h, title, detail, facecolor, title_fs=10.0, detail_fs=9.0):
    draw_rect(ax, x, y, w, h, facecolor=facecolor, linewidth=0.95, zorder=3)
    ax.text(
        x + w / 2,
        y + h * 0.67,
        title,
        fontsize=title_fs,
        fontweight="bold",
        color=BLACK,
        ha="center",
        va="center",
        zorder=4,
    )
    ax.text(
        x + w / 2,
        y + h * 0.30,
        detail,
        fontsize=detail_fs,
        color=DARK,
        ha="center",
        va="center",
        linespacing=1.15,
        zorder=4,
    )


def arrow(ax, x0, y0, x1, y1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle=HEAD_STYLE, color=BLACK, lw=1.05, shrinkA=0, shrinkB=0),
        zorder=5,
    )


def render_study_a() -> None:
    W, H = 10.2, 2.15
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    in_x, in_w = 0.25, 2.35
    gen_x, gen_w = 3.35, 3.20
    ev_x, ev_w = 7.30, 2.65

    draw_rect(ax, 0.08, 0.08, W - 0.16, H - 0.16, facecolor=GROUP, linewidth=1.0, zorder=1)
    draw_rect(ax, 0.08, H - 0.46, W - 0.16, 0.38, facecolor=SUB, linewidth=0.9, zorder=2)
    for xc, text in (
        (in_x + in_w / 2, "1. Fixed Input"),
        (gen_x + gen_w / 2, "2. Generators (120 Runs Each)"),
        (ev_x + ev_w / 2, "3. Evaluation"),
    ):
        ax.text(xc, H - 0.27, text, fontsize=9.8, fontweight="bold", ha="center", va="center", zorder=3)

    generators = [
        ("One-Shot Prompt", "GPT-5 mini (118) & GPT-4.1 (120)"),
        ("StructPF", "GPT-5 mini (120 tasks)"),
    ]
    box_h, gap = 0.54, 0.12
    stack_h = 2 * box_h + gap
    yc = 0.16 + stack_h / 2

    labelled_box(
        ax,
        in_x,
        yc - 0.46,
        in_w,
        0.92,
        "4 Grade 7 Settings",
        "Target concept and prior\nknowledge both given",
        facecolor=WHITE,
    )
    labelled_box(
        ax,
        ev_x,
        yc - 0.46,
        ev_w,
        0.92,
        "PF Eval (Chapter 5)",
        "5 measures (Task Judge,\nSolver, Attempt Judge)",
        facecolor=PROC,
    )

    centers = []
    for i, (name, detail) in enumerate(generators):
        y = 0.16 + stack_h - (i + 1) * box_h - i * gap
        labelled_box(ax, gen_x, y, gen_w, box_h, name, detail, facecolor=PROC)
        centers.append(y + box_h / 2)

    bus_in, bus_out = gen_x - 0.36, gen_x + gen_w + 0.36
    ax.plot([in_x + in_w, bus_in], [yc, yc], color=BLACK, lw=1.05, zorder=5)
    ax.plot([bus_in, bus_in], [min(centers), max(centers)], color=BLACK, lw=1.05, zorder=5)
    ax.plot([bus_out, bus_out], [min(centers), max(centers)], color=BLACK, lw=1.05, zorder=5)
    for c in centers:
        arrow(ax, bus_in, c, gen_x, c)
        ax.plot([gen_x + gen_w, bus_out], [c, c], color=BLACK, lw=1.05, zorder=5)
    arrow(ax, bus_out, yc, ev_x, yc)

    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6_1_study_a_setup.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def render_study_b() -> None:
    W, H = 12.2, 2.70
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    cols = [
        (0.08, 3.62, "1. Input & Generators (GPT-5 mini)", SUB),
        (4.02, 3.66, "2. Step 1: Prior-Knowledge Check", PROC),
        (8.46, 3.66, "3. Step 2: Method-Failure Check", PROC),
    ]
    for x, w, title, hfill in cols:
        draw_rect(ax, x, 0.08, w, H - 0.16, facecolor=GROUP, linewidth=0.95, zorder=1)
        draw_rect(ax, x, H - 0.48, w, 0.40, facecolor=hfill, linewidth=0.85, zorder=2)
        ax.text(x + w / 2, H - 0.28, title, fontsize=9.8, fontweight="bold", color=BLACK, ha="center", va="center", zorder=3)

    def box(x, w, y0, h, title, detail=None, face=WHITE, color=BLACK):
        draw_rect(ax, x + 0.18, y0, w - 0.36, h, facecolor=face, linewidth=0.85, zorder=2)
        cx = x + w / 2
        if detail is None:
            ax.text(cx, y0 + h / 2, title, fontsize=8.9, fontweight="bold", color=color, ha="center", va="center", zorder=3)
        else:
            ax.text(cx, y0 + h * 0.67, title, fontsize=8.9, fontweight="bold", color=color, ha="center", va="center", zorder=3)
            ax.text(cx, y0 + h * 0.29, detail, fontsize=8.2, color=DARK if color == BLACK else color, ha="center", va="center", zorder=3)

    # Column 1: input -> three generators -> run output
    x1, w1 = 0.08, 3.62
    cx1 = x1 + w1 / 2
    box(x1, w1, 1.62, 0.52, "Input: 30 Topics (Grades 5 to 10)", "Only the target concept is given")
    arms = [
        "One-Shot Prompt (30 runs)",
        "StructPF without Grounding (30 runs)",
        "StructPF with Grounding (30 runs)",
    ]
    for idx, arm_txt in enumerate(arms):
        ay = 1.26 - idx * 0.27
        draw_rect(ax, x1 + 0.18, ay, w1 - 0.36, 0.22, facecolor=PROC, linewidth=0.8, zorder=2)
        ax.text(cx1, ay + 0.11, arm_txt, fontsize=8.5, fontweight="bold", ha="center", va="center", zorder=3)
    box(x1, w1, 0.18, 0.42, "Run Output", "Proposed prior skills + student task")
    arrow(ax, cx1, 1.62, cx1, 1.48)
    arrow(ax, cx1, 0.72, cx1, 0.60)
    arrow(ax, x1 + w1, 1.14, 4.02, 1.14)

    # Column 2: Prior-Knowledge Check
    x2, w2 = 4.02, 3.66
    cx2 = x2 + w2 / 2
    box(x2, w2, 1.62, 0.52, "Curriculum Judge", "Compares each skill with the graph prerequisites")
    arrow(ax, cx2, 1.62, cx2, 1.38)
    box(x2, w2, 0.90, 0.48, "Pass: No Leak and a Valid Start", "Proceeds to Step 2")
    box(x2, w2, 0.18, 0.48, "Fail: Target Leak or No Valid Start", "Stops at Step 1", face=MID, color=WHITE)
    arrow(ax, x2 + w2 - 0.18, 1.14, 8.46, 1.14)
    ax.text((x2 + w2 + 8.46) / 2, 1.24, "Pass only", fontsize=7.5, fontweight="bold", color=BLACK, ha="center", va="bottom", zorder=4)

    # Column 3: Method-Failure Check
    x3, w3 = 8.46, 3.66
    cx3 = x3 + w3 / 2
    box(x3, w3, 1.62, 0.52, "Target-Blind Solver + Attempt Judge", "Tests whether valid skills fall short on the task")
    arrow(ax, cx3, 1.62, cx3, 1.38)
    box(x3, w3, 0.90, 0.48, "Pass: Familiar Methods Fall Short", "Task requires the target concept", face=PROC)
    box(x3, w3, 0.18, 0.48, "Fail: Familiar Method Solves Task", "Valid skill bypasses target or fails unrelatedly", face=MID, color=WHITE)

    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6_2_study_b_setup.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_study_a()
    render_study_b()
    print(f"Saved {OUT_DIR}/fig6_1_study_a_setup.{{pdf,png}} and fig6_2_study_b_setup.{{pdf,png}}")


if __name__ == "__main__":
    main()
