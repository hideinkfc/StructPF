"""Render the Chapter 4 summary figure: detailed StructPF architecture.
Styled after JupyRecSys (Fig. 1-3) and Figure 3.1: sharp rectangular corners,
monochrome/grayscale blocks (#FFFFFF, #F2F2F2, #CFCFCF, #E2E2E2), generous whitespace,
short architectural labels, and a spacious top-to-bottom three-stage layout.
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
    linewidth=1.0,
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
    dx=0.055,
    dy=0.055,
    facecolor="#FFFFFF",
    edgecolor="#000000",
    linewidth=0.95,
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
    lw=1.15,
    style="-|>,head_length=0.40,head_width=0.24",
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


def draw_polyline_arrow(
    ax,
    pts,
    color="#000000",
    lw=1.15,
    style="-|>,head_length=0.40,head_width=0.24",
    linestyle="-",
    zorder=5,
):
    for i in range(len(pts) - 2):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        ax.plot([x0, x1], [y0, y1], color=color, lw=lw, linestyle=linestyle, zorder=zorder)
    x0, y0 = pts[-2]
    x1, y1 = pts[-1]
    draw_arrow(ax, x0, y0, x1, y1, color=color, lw=lw, style=style, linestyle=linestyle, zorder=zorder)


def main():
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["axes.edgecolor"] = "none"
    plt.rcParams["pdf.fonttype"] = 42

    # Tall architectural proportions so it takes a large, clear height on the page
    W, H = 10.8, 10.4
    fig, ax = plt.subplots(figsize=(W, H), dpi=300)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    c_black = "#000000"
    c_dark = "#222222"
    c_proc = "#CFCFCF"   # JupyRecSys process block gray
    c_group = "#F2F2F2"  # Stage container light gray
    c_sub = "#E2E2E2"    # Header strip gray
    c_white = "#FFFFFF"

    # Top Title & Legend Bar
    leg_y = 9.96
    ax.text(
        0.16,
        leg_y + 0.10,
        "StructPF Pipeline Architecture",
        fontsize=11.2,
        fontweight="bold",
        color=c_black,
        ha="left",
        va="center",
    )
    draw_rect(ax, 4.15, leg_y, 0.26, 0.20, facecolor=c_proc, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(4.49, leg_y + 0.10, "= Pipeline step", fontsize=8.8, color=c_dark, ha="left", va="center")

    draw_rect(ax, 6.00, leg_y, 0.26, 0.20, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="--", zorder=3)
    ax.text(6.34, leg_y + 0.10, "= Internal design artifact (withheld)", fontsize=8.8, color=c_dark, ha="left", va="center")

    draw_rect(ax, 9.05, leg_y, 0.26, 0.20, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="-", zorder=3)
    ax.text(9.39, leg_y + 0.10, "= Input / Student text", fontsize=8.8, color=c_dark, ha="left", va="center")

    ax.plot([0.16, 10.64], [9.74, 9.74], color=c_black, lw=1.0, zorder=3)

    # Column layout inside each stage band:
    # Left column: Human Designer Step & PF Principle (x = 0.34 to 2.68)
    # Vertical routing channel at x = 3.04
    # Right area: Pipeline Flow (x = 3.30 to 10.46)
    band_x, band_w = 0.16, 10.48
    left_x, left_w = 0.34, 2.36
    div_x = 2.86
    # Headers start right of the x = 3.04 routing channel so inter-stage arrows cross only the band border.
    head_x = 3.20

    # Three spacious vertical stage bands (top to bottom)
    # Band 1 (Stage 1): y = 6.84 to 9.52 (h = 2.68)
    # Band 2 (Stage 2): y = 3.52 to 6.26 (h = 2.74)
    # Band 3 (Stage 3): y = 0.20 to 2.94 (h = 2.74)
    b1_y, b1_h = 6.84, 2.68
    b2_y, b2_h = 3.52, 2.74
    b3_y, b3_h = 0.20, 2.74

    bands = [
        (
            b1_y,
            b1_h,
            "Stage 1: Retrieving Prerequisite Knowledge (Section 4.2)",
            "Human Step 1",
            "List taught skills\n(Grades 1 to k-1)\n\nPF Req. 1:\nActivate prior\nknowledge",
        ),
        (
            b2_y,
            b2_h,
            "Stage 2: Problem Design and Number Verification (Section 4.3)",
            "Human Steps 2 & 3",
            "Anticipate attempts\n& tune numbers\n\nPF Req. 2:\nFamiliar shortcuts\nfall short",
        ),
        (
            b3_y,
            b3_h,
            "Stage 3: Open-Ended Task Generation (Section 4.4)",
            "Human Step 4",
            "Write open problem\nwithout formula\n\nPF Req. 3:\nRoom to invent\n& explain",
        ),
    ]

    for by, bh, btitle, htitle, hbody in bands:
        # Outer stage container
        draw_rect(ax, band_x, by, band_w, bh, facecolor=c_group, edgecolor=c_black, linewidth=1.05, zorder=1)
        # Header bar
        draw_rect(ax, head_x, by + bh - 0.44, band_x + band_w - head_x, 0.44, facecolor=c_sub, edgecolor=c_black, linewidth=0.95, zorder=2)
        ax.text(head_x + 0.16, by + bh - 0.22, btitle, fontsize=9.6, fontweight="bold", color=c_black, ha="left", va="center", zorder=3)

        # Vertical dotted separator between Human Design Rationale (left) and Pipeline Flow (right)
        ax.plot([div_x, div_x], [by + 0.18, by + bh - 0.18], color="#555555", lw=0.9, linestyle=":", zorder=2)

        # Left rationale box
        lbox_y = by + 0.22
        lbox_h = bh - 0.44
        draw_rect(ax, left_x, lbox_y, left_w, lbox_h, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
        draw_rect(ax, left_x, lbox_y + lbox_h - 0.36, left_w, 0.36, facecolor=c_sub, edgecolor=c_black, linewidth=0.85, zorder=3)
        ax.text(left_x + left_w / 2, lbox_y + lbox_h - 0.18, htitle, fontsize=8.8, fontweight="bold", color=c_black, ha="center", va="center", zorder=4)
        ax.text(left_x + left_w / 2, lbox_y + (lbox_h - 0.36) / 2, hbody, fontsize=8.4, color=c_dark, ha="center", va="center", linespacing=1.24, zorder=4)

    # ==========================================================================
    # BAND 1 FLOW: Stage 1 (y = 6.84 to 9.52)
    # ==========================================================================
    s1_mid_y = b1_y + 1.15

    # Input 1: Target Learning Concept (top left of flow)
    in1_x, in1_w = 3.16, 1.78
    draw_rect(ax, in1_x, b1_y + 1.24, in1_w, 0.80, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(in1_x + in1_w / 2, b1_y + 1.64, "Target Learning\nConcept", fontsize=8.8, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.22, zorder=4)

    # Input 2: Learning Commons Graph (bottom left of flow)
    draw_rect(ax, in1_x, b1_y + 0.24, in1_w, 0.82, facecolor=c_white, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(in1_x + in1_w / 2, b1_y + 0.65, "Learning Commons\nKnowledge Graph", fontsize=8.5, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.22, zorder=4)

    # Process 1a: Query Graph Prerequisites
    p1a_x, p1a_w = 5.30, 1.54
    draw_rect(ax, p1a_x, b1_y + 0.50, p1a_w, 1.30, facecolor=c_proc, edgecolor=c_black, linewidth=1.0, zorder=3)
    ax.text(p1a_x + p1a_w / 2, s1_mid_y, "Query\nPrerequisite\nGraph", fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.24, zorder=4)

    # Arrows from Inputs into 1a
    draw_polyline_arrow(ax, [(in1_x + in1_w, b1_y + 1.64), (5.12, b1_y + 1.64), (5.12, s1_mid_y + 0.22), (p1a_x, s1_mid_y + 0.22)])
    draw_polyline_arrow(ax, [(in1_x + in1_w, b1_y + 0.65), (5.12, b1_y + 0.65), (5.12, s1_mid_y - 0.22), (p1a_x, s1_mid_y - 0.22)])

    # Process 1b: Map Prior-Skill Records
    p1b_x, p1b_w = 7.16, 1.54
    draw_rect(ax, p1b_x, b1_y + 0.50, p1b_w, 1.30, facecolor=c_proc, edgecolor=c_black, linewidth=1.0, zorder=3)
    ax.text(p1b_x + p1b_w / 2, s1_mid_y, "Map Prior\nSkills\n(No Spoilers)", fontsize=9.0, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.24, zorder=4)
    draw_arrow(ax, p1a_x + p1a_w, s1_mid_y, p1b_x, s1_mid_y)

    # Output 1: Prior-Skill Records Stack
    o1_x, o1_w = 9.02, 1.32
    draw_stack(ax, o1_x, b1_y + 0.45, o1_w, 1.30, n=3, dx=0.045, dy=0.045, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="--", zorder=3)
    ax.text(o1_x + o1_w / 2, s1_mid_y - 0.05, "Prior-Skill\nRecords\n(≤ 5 Skills)", fontsize=8.8, fontweight="bold", color=c_dark, ha="center", va="center", linespacing=1.22, zorder=5)
    draw_arrow(ax, p1b_x + p1b_w, s1_mid_y, o1_x, s1_mid_y)

    # ==========================================================================
    # INTER-STAGE ARROW: Stage 1 Output -> Stage 2 Input (routed cleanly without crossing header!)
    # ==========================================================================
    s2_mid_y = b2_y + 1.18
    p2a_x, p2a_w = 3.30, 1.56
    gap12_y = 6.55
    draw_polyline_arrow(
        ax,
        [
            (o1_x + o1_w / 2, b1_y + 0.45),
            (o1_x + o1_w / 2, gap12_y),
            (3.04, gap12_y),
            (3.04, s2_mid_y),
            (p2a_x, s2_mid_y),
        ],
    )
    ax.text(6.40, gap12_y + 0.13, "Pass prior-skill records to Stage 2", fontsize=8.6, fontweight="bold", color=c_black, ha="center", va="center")

    # ==========================================================================
    # BAND 2 FLOW: Stage 2 (y = 3.52 to 6.26)
    # ==========================================================================
    # Step 2a: Propose & Select Design Brief
    draw_rect(ax, p2a_x, b2_y + 0.54, p2a_w, 1.28, facecolor=c_proc, edgecolor=c_black, linewidth=1.0, zorder=3)
    ax.text(p2a_x + p2a_w / 2, s2_mid_y, "Step 2a:\nPropose & Select\nDesign Brief", fontsize=8.8, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.22, zorder=4)

    # Bounded brief-revision loop under Step 2a
    draw_polyline_arrow(
        ax,
        [
            (p2a_x + p2a_w * 0.72, b2_y + 0.54),
            (p2a_x + p2a_w * 0.72, b2_y + 0.30),
            (p2a_x + p2a_w * 0.28, b2_y + 0.30),
            (p2a_x + p2a_w * 0.28, b2_y + 0.54),
        ],
        lw=0.95,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    ax.text(p2a_x + p2a_w / 2, b2_y + 0.16, "Revise brief (≤ 2 times)", fontsize=7.8, color=c_dark, ha="center", va="center")

    # Output 2a: Selected Design Brief
    o2a_x, o2a_w = 5.18, 1.56
    draw_rect(ax, o2a_x, b2_y + 0.54, o2a_w, 1.28, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="--", zorder=3)
    ax.text(o2a_x + o2a_w / 2, s2_mid_y, "Selected\nDesign Brief\n(Withheld Idea)", fontsize=8.6, fontweight="bold", color=c_dark, ha="center", va="center", linespacing=1.22, zorder=4)
    draw_arrow(ax, p2a_x + p2a_w, s2_mid_y, o2a_x, s2_mid_y)

    # Step 2b: Choose Numbers & Calculator Check
    p2b_x, p2b_w = 7.06, 1.62
    draw_rect(ax, p2b_x, b2_y + 0.54, p2b_w, 1.28, facecolor=c_proc, edgecolor=c_black, linewidth=1.0, zorder=3)
    ax.text(p2b_x + p2b_w / 2, s2_mid_y, "Step 2b:\nChoose & Check\nNumbers (Python)", fontsize=8.7, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.22, zorder=4)
    draw_arrow(ax, o2a_x + o2a_w, s2_mid_y, p2b_x, s2_mid_y)

    # Bounded numbers-only repair loop indicator under Step 2b (label cleanly below the loop line)
    loop_y = b2_y + 0.30
    draw_polyline_arrow(
        ax,
        [
            (p2b_x + p2b_w * 0.72, b2_y + 0.54),
            (p2b_x + p2b_w * 0.72, loop_y),
            (p2b_x + p2b_w * 0.28, loop_y),
            (p2b_x + p2b_w * 0.28, b2_y + 0.54),
        ],
        lw=0.95,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    ax.text(p2b_x + p2b_w / 2, loop_y - 0.14, "Repair numbers (≤ 3 calls)", fontsize=7.8, color=c_dark, ha="center", va="center")

    # Output 2b: Checked Problem Data
    o2b_x, o2b_w = 9.00, 1.42
    draw_rect(ax, o2b_x, b2_y + 0.54, o2b_w, 1.28, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="--", zorder=3)
    ax.text(o2b_x + o2b_w / 2, s2_mid_y, "Checked\nProblem Data", fontsize=8.8, fontweight="bold", color=c_dark, ha="center", va="center", linespacing=1.22, zorder=4)
    draw_arrow(ax, p2b_x + p2b_w, s2_mid_y, o2b_x, s2_mid_y)

    # ==========================================================================
    # INTER-STAGE ARROW: Stage 2 Output -> Stage 3 Input (routed cleanly without crossing header!)
    # ==========================================================================
    s3_mid_y = b3_y + 1.15
    in3_x, in3_w = 3.30, 2.10
    gap23_y = 3.23
    draw_polyline_arrow(
        ax,
        [
            (o2b_x + o2b_w / 2, b2_y + 0.54),
            (o2b_x + o2b_w / 2, gap23_y),
            (3.04, gap23_y),
            (3.04, b3_y + 1.64),
            (in3_x, b3_y + 1.64),
        ],
    )
    ax.text(6.40, gap23_y + 0.13, "Split student-visible values from withheld notes", fontsize=8.6, fontweight="bold", color=c_black, ha="center", va="center")

    # ==========================================================================
    # BAND 3 FLOW: Stage 3 (y = 0.20 to 2.94)
    # ==========================================================================
    # Input 3a (Top): Passed to Writer (Given Setup & Fixed Numbers)
    draw_rect(ax, in3_x, b3_y + 1.24, in3_w, 0.80, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="-", zorder=3)
    ax.text(in3_x + in3_w / 2, b3_y + 1.64, "Passed to Writer\nFixed Numbers & Setup", fontsize=8.5, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.22, zorder=4)

    # Input 3b (Bottom): Withheld from Student Prompt (Key Idea & Rubric)
    draw_rect(ax, in3_x, b3_y + 0.24, in3_w, 0.80, facecolor=c_white, edgecolor=c_black, linewidth=0.95, linestyle="--", zorder=3)
    ax.text(in3_x + in3_w / 2, b3_y + 0.64, "Withheld Notes\nKey Idea & Rubric", fontsize=8.5, color=c_dark, ha="center", va="center", linespacing=1.22, zorder=4)

    # Process 3: Open Task Writer
    p3_x, p3_w = 5.96, 1.96
    draw_rect(ax, p3_x, b3_y + 0.50, p3_w, 1.30, facecolor=c_proc, edgecolor=c_black, linewidth=1.0, zorder=3)
    ax.text(p3_x + p3_w / 2, s3_mid_y, "Stage 3:\nOpen Task Writer\n(No Giveaways)", fontsize=8.9, fontweight="bold", color=c_black, ha="center", va="center", linespacing=1.24, zorder=4)

    # Bounded draft-revision loop under the writer
    draw_polyline_arrow(
        ax,
        [
            (p3_x + p3_w * 0.72, b3_y + 0.50),
            (p3_x + p3_w * 0.72, b3_y + 0.28),
            (p3_x + p3_w * 0.28, b3_y + 0.28),
            (p3_x + p3_w * 0.28, b3_y + 0.50),
        ],
        lw=0.95,
        style="-|>,head_length=0.28,head_width=0.18",
    )
    ax.text(p3_x + p3_w / 2, b3_y + 0.14, "Revise draft (≤ 3 calls)", fontsize=7.8, color=c_dark, ha="center", va="center")

    # Arrow from Passed Setup into Process 3
    draw_polyline_arrow(ax, [(in3_x + in3_w, b3_y + 1.64), (5.68, b3_y + 1.64), (5.68, s3_mid_y), (p3_x, s3_mid_y)])

    # Final Output: Student-Facing PF Task
    o3_x, o3_w = 8.48, 1.94
    draw_rect(ax, o3_x, b3_y + 0.50, o3_w, 1.30, facecolor=c_white, edgecolor=c_black, linewidth=1.2, linestyle="-", zorder=3)
    draw_rect(ax, o3_x, b3_y + 1.44, o3_w, 0.36, facecolor=c_sub, edgecolor=c_black, linewidth=0.95, zorder=3)
    ax.text(o3_x + o3_w / 2, b3_y + 1.62, "Student-Facing Task", fontsize=8.8, fontweight="bold", color=c_black, ha="center", va="center", zorder=4)
    ax.text(o3_x + o3_w / 2, b3_y + 0.96, "Context, fixed values\n& open question", fontsize=8.4, color=c_dark, ha="center", va="center", linespacing=1.22, zorder=4)
    draw_arrow(ax, p3_x + p3_w, s3_mid_y, o3_x, s3_mid_y)

    out_dir = Path(__file__).resolve().parents[1] / "thesis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig4_6_structpf_architecture.pdf"
    png_path = out_dir / "fig4_6_structpf_architecture.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")


if __name__ == "__main__":
    main()

