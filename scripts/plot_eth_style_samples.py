"""Generate ETH LRE (Macina & Sachan style: MathDial / StratL) sample diagrams and plots.

Produces both vector PDF (for LaTeX) and 300-DPI PNG (for quick preview) in
docs/status/figures/eth_samples/:
  1. eth_sample_1_structpf_diagram.{pdf,png} — MathDial/StratL-style dashed-container
     pipeline diagram with semantic pastel palette and embedded worked math example
  2. eth_sample_2_grounding_3arms.{pdf,png}  — MathDial Fig. 3 style multi-hue
     horizontal stacked bar chart for the 30-topic 3-arm Two-Gate study
  3. eth_sample_3_solver_recall.{pdf,png}    — StratL Fig. 3 / MathDial Fig. 5 style
     grouped multi-hue vertical bar chart for the 76-task Solver Recall benchmark
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "status" / "figures" / "eth_samples"

# Academic Multi-Hue Palette (used across MathDial 2023 & StratL 2025)
# 1. Quantitative plot colors (Seaborn Deep / Academic Publication Standard)
CLR_BLUE = "#4C72B0"  # Primary / Model A / Grounded
CLR_ORANGE = "#DD8452"  # Secondary / Model B / Partial-Bypass
CLR_GREEN = "#55A868"  # Positive / Productive Trap / Combined Union
CLR_RED = "#C44E52"  # Negative / Spoiler Leak / Failure
CLR_PURPLE = "#8172B3"  # Tertiary accent
CLR_GREY_DARK = "#2B2B2B"
CLR_GREY = "#666666"

# 2. Diagram semantic pastel palette (draw.io academic palette from MathDial Fig. 2)
DIAG_BLUE_FILL = "#DAE8FC"
DIAG_BLUE_EDGE = "#6C8EBF"
DIAG_YELLOW_FILL = "#FFF2CC"
DIAG_YELLOW_EDGE = "#D6B656"
DIAG_GREEN_FILL = "#D5E8D4"
DIAG_GREEN_EDGE = "#82B366"
DIAG_RED_FILL = "#F8CECC"
DIAG_RED_EDGE = "#B85450"
DIAG_GREY_FILL = "#F5F5F5"
DIAG_GREY_EDGE = "#666666"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 9.5,
        "axes.edgecolor": "#444444",
        "axes.linewidth": 0.8,
        "xtick.color": "#2B2B2B",
        "ytick.color": "#2B2B2B",
        "text.color": "#222222",
    }
)


def _draw_stage_container(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
) -> None:
    """Dashed outer container box with bold numbered stage header (MathDial Fig. 2 style)."""
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor="#FAFAFA",
        edgecolor="#888888",
        linewidth=1.1,
        linestyle="--",
        zorder=1,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h - 0.20,
        title,
        ha="center",
        va="center",
        fontsize=8.8,
        fontweight="bold",
        color=CLR_GREY_DARK,
        zorder=4,
    )


def _draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    facecolor: str = "#FFFFFF",
    edgecolor: str = DIAG_GREY_EDGE,
    fontsize: float = 8.2,
    bold: bool = False,
    italic: bool = False,
    rounded: bool = True,
    textcolor: str = CLR_GREY_DARK,
) -> None:
    if rounded:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.09",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=1.15,
            zorder=3,
        )
    else:
        patch = mpatches.Rectangle(
            (x, y),
            w,
            h,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=1.1,
            zorder=3,
        )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        fontstyle="italic" if italic else "normal",
        color=textcolor,
        linespacing=1.22,
        zorder=4,
    )


def _arrow(
    ax: plt.Axes,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    color: str = "#444444",
) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>,head_length=0.42,head_width=0.24",
            color=color,
            lw=1.05,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=5,
    )


def make_sample_1_diagram() -> None:
    """Sample 1: MathDial / StratL style pipeline diagram with concrete worked math snippet."""
    fig, ax = plt.subplots(figsize=(8.6, 3.35))
    ax.set_xlim(0, 11.4)
    ax.set_ylim(0, 3.85)
    ax.axis("off")

    # Left Input Column (Blue = Curriculum & Input Data)
    _draw_box(
        ax,
        0.10,
        2.35,
        1.75,
        1.05,
        "Target Concept\n\nSlope m = Δy / Δx\n(Grade 8, 8.EE.B.6)",
        facecolor=DIAG_BLUE_FILL,
        edgecolor=DIAG_BLUE_EDGE,
        fontsize=8.0,
        bold=True,
    )
    _draw_box(
        ax,
        0.10,
        0.75,
        1.75,
        1.15,
        "Learning Commons\nKnowledge Graph\n\nAncestors:\n7.RP.A.2 -> 8.EE.B.5",
        facecolor=DIAG_BLUE_FILL,
        edgecolor=DIAG_BLUE_EDGE,
        fontsize=7.8,
    )

    # Dashed Container 1: Stage 1 Prior-Skill Grounding
    _draw_stage_container(ax, 2.15, 0.55, 2.75, 3.15, "1. Prior-Skill Selection (D1)")
    _draw_box(
        ax,
        2.35,
        2.45,
        2.35,
        0.80,
        "LLM Prior-Skill Selector\nRestricts to earlier skills",
        facecolor=DIAG_YELLOW_FILL,
        edgecolor=DIAG_YELLOW_EDGE,
        fontsize=7.8,
        bold=True,
    )
    _draw_box(
        ax,
        2.35,
        1.45,
        2.35,
        0.72,
        '✓ Valid Prior Skill (K_prior):\n"Unit rate y / x from origin"',
        facecolor=DIAG_GREEN_FILL,
        edgecolor=DIAG_GREEN_EDGE,
        fontsize=7.7,
    )
    _draw_box(
        ax,
        2.35,
        0.68,
        2.35,
        0.60,
        '✗ Blocked Spoiler:\n"Slope (y2 - y1) / (x2 - x1)"',
        facecolor=DIAG_RED_FILL,
        edgecolor=DIAG_RED_EDGE,
        fontsize=7.4,
        textcolor="#7A1C19",
    )

    # Dashed Container 2: Stage 2 Trap Design & Verification
    _draw_stage_container(ax, 5.20, 0.55, 3.05, 3.15, "2. Trap Design & Check (D2a/b)")
    _draw_box(
        ax,
        5.40,
        2.45,
        2.65,
        0.80,
        "Contrastive Design Brief\nNon-zero intercept breaks y / x",
        facecolor=DIAG_YELLOW_FILL,
        edgecolor=DIAG_YELLOW_EDGE,
        fontsize=7.8,
        bold=True,
    )
    _draw_box(
        ax,
        5.40,
        1.45,
        2.65,
        0.72,
        "Python Calculator Verifier\nChecks K_prior conflict & Δy/Δx",
        facecolor=DIAG_GREEN_FILL,
        edgecolor=DIAG_GREEN_EDGE,
        fontsize=7.8,
        bold=True,
    )
    _draw_box(
        ax,
        5.40,
        0.68,
        2.65,
        0.60,
        "Verified Table: (2, 7) -> (6, 15)\ny/x gives 3.5 != 2.5;  Δy/Δx = 2",
        facecolor="#FFFFFF",
        edgecolor=DIAG_GREEN_EDGE,
        fontsize=7.5,
        italic=True,
        rounded=False,
    )

    # Dashed Container 3: Stage 3 Student Task Generation
    _draw_stage_container(ax, 8.55, 0.55, 2.70, 3.15, "3. Student Task (D3)")
    _draw_box(
        ax,
        8.75,
        2.45,
        2.30,
        0.80,
        "Open Task Writer\nWithholds target formula",
        facecolor=DIAG_YELLOW_FILL,
        edgecolor=DIAG_YELLOW_EDGE,
        fontsize=7.9,
        bold=True,
    )
    _draw_box(
        ax,
        8.75,
        0.75,
        2.30,
        1.42,
        'Student PF Task T\n\n"Compare three ramps\nusing the measurements.\nInvent a steepness rule\nthat works for all ramps."',
        facecolor="#FFFFFF",
        edgecolor=DIAG_BLUE_EDGE,
        fontsize=7.7,
        rounded=False,
    )

    # Arrows connecting stages
    _arrow(ax, 1.85, 2.85, 2.35, 2.85)
    _arrow(ax, 1.85, 1.32, 2.35, 2.65)
    _arrow(ax, 3.52, 2.45, 3.52, 2.17)
    _arrow(ax, 4.70, 1.81, 5.40, 2.75)
    _arrow(ax, 6.72, 2.45, 6.72, 2.17)
    _arrow(ax, 6.72, 1.45, 6.72, 1.28)
    _arrow(ax, 8.05, 1.81, 8.75, 2.75)
    _arrow(ax, 9.90, 2.45, 9.90, 2.17)

    # Compact semantic legend at bottom (MathDial style)
    legend_items = [
        (DIAG_BLUE_FILL, DIAG_BLUE_EDGE, "Curriculum / Input"),
        (DIAG_YELLOW_FILL, DIAG_YELLOW_EDGE, "LLM Generation Step"),
        (DIAG_GREEN_FILL, DIAG_GREEN_EDGE, "Verified / Grounded Check"),
        (DIAG_RED_FILL, DIAG_RED_EDGE, "Blocked Spoiler Leak"),
    ]
    x_start = 1.15
    for fill, edge, label in legend_items:
        _draw_box(ax, x_start, 0.08, 0.32, 0.24, "", facecolor=fill, edgecolor=edge)
        ax.text(
            x_start + 0.40,
            0.20,
            label,
            va="center",
            ha="left",
            fontsize=7.8,
            color=CLR_GREY_DARK,
        )
        x_start += 2.38

    fig.tight_layout(pad=0.15)
    fig.savefig(OUT_DIR / "eth_sample_1_structpf_diagram.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "eth_sample_1_structpf_diagram.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_sample_2_grounding_3arms() -> None:
    """Sample 2: MathDial Fig. 3 style multi-hue horizontal stacked bar chart."""
    summary_path = (
        ROOT
        / "experiments/results/pf_progression_bridge_30cases_3arms_20261016/summary_three_arm.json"
    )
    data = json.loads(summary_path.read_text(encoding="utf-8"))["summary"]["arms"]

    arms = [
        ("direct", "Direct Generation\n(One-Shot Baseline)"),
        ("ungrounded", "StructPF Pipeline\n(Without LC Graph)"),
        ("lc_grounded", "StructPF Pipeline\n(With LC Graph)"),
    ]
    arms = list(reversed(arms))

    s0 = [data[k]["score_counts"]["score_0_invalid_prior_set"] for k, _ in arms]
    s1 = [data[k]["score_counts"]["score_1_trap_bypassed_or_off_target"] for k, _ in arms]
    s2 = [data[k]["score_counts"]["score_2_productive_trap"] for k, _ in arms]
    means = [data[k]["two_gate_score_mean"] for k, _ in arms]
    labels = [lbl for _, lbl in arms]

    fig, ax = plt.subplots(figsize=(7.0, 2.75))
    y = range(len(arms))
    bar_h = 0.55

    b0 = ax.barh(
        y,
        s0,
        height=bar_h,
        color=CLR_RED,
        edgecolor="#FFFFFF",
        linewidth=0.9,
        label="Score 0: Invalid K_prior (Spoiler Leak — Failed Gate 1)",
        zorder=3,
    )
    b1 = ax.barh(
        y,
        s1,
        left=s0,
        height=bar_h,
        color=CLR_ORANGE,
        edgecolor="#FFFFFF",
        linewidth=0.9,
        label="Score 1: Valid K_prior, Trap Bypassed (Failed Gate 2)",
        zorder=3,
    )
    b2 = ax.barh(
        y,
        s2,
        left=[a + b for a, b in zip(s0, s1)],
        height=bar_h,
        color=CLR_GREEN,
        edgecolor="#FFFFFF",
        linewidth=0.9,
        label="Score 2: Valid K_prior + Productive Trap (Passed Both Gates)",
        zorder=3,
    )

    for i in range(len(arms)):
        if s0[i] >= 3:
            ax.text(
                s0[i] / 2,
                i,
                f"{s0[i]}/30 ({round(s0[i] * 100 / 30):.0f}%)",
                ha="center",
                va="center",
                color="#FFFFFF",
                fontweight="bold",
                fontsize=8.5,
                zorder=4,
            )
        if s1[i] >= 4:
            ax.text(
                s0[i] + s1[i] / 2,
                i,
                f"{s1[i]}/30 ({round(s1[i] * 100 / 30):.0f}%)",
                ha="center",
                va="center",
                color="#FFFFFF",
                fontweight="bold",
                fontsize=8.5,
                zorder=4,
            )
        if s2[i] >= 4:
            ax.text(
                s0[i] + s1[i] + s2[i] / 2,
                i,
                f"{s2[i]}/30 ({round(s2[i] * 100 / 30):.0f}%)",
                ha="center",
                va="center",
                color="#FFFFFF",
                fontweight="bold",
                fontsize=8.5,
                zorder=4,
            )
        ax.text(
            30.6,
            i,
            f"Mean: {means[i]:.2f} / 2.0",
            ha="left",
            va="center",
            color=CLR_GREY_DARK,
            fontweight="bold",
            fontsize=8.6,
        )

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9.2, fontweight="bold")
    ax.set_xlim(0, 37.5)
    ax.set_ylim(-0.50, 2.55)
    ax.set_xticks([0, 5, 10, 15, 20, 25, 30])
    ax.set_xlabel("Number of Curriculum Topics (N = 30, Grades 5–10)", fontsize=9.2)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        handles=[b0, b1, b2],
        loc="lower center",
        bbox_to_anchor=(0.46, 1.04),
        ncol=1,
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        fontsize=8.2,
    )

    fig.tight_layout()
    fig.savefig(OUT_DIR / "eth_sample_2_grounding_3arms.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "eth_sample_2_grounding_3arms.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_sample_3_solver_recall() -> None:
    """Sample 3: StratL Fig. 3 / MathDial Fig. 5 style grouped multi-hue vertical bar chart."""
    summary_path = ROOT / "experiments/results/pf_solver_recall_20261016/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    by_role = summary["recall_by_role"]
    by_cohort = summary["recall_by_cohort_primary_complete"]

    categories = [
        (
            "All Reference\nApproaches (n=256)",
            by_role["gpt41"]["primary_complete"],
            by_role["luna"]["primary_complete"],
            by_role["combined"]["primary_complete"],
        ),
        (
            "Prior-Skill Trap\nRoutes (n=173)",
            by_role["gpt41"]["baseline_trap"],
            by_role["luna"]["baseline_trap"],
            by_role["combined"]["baseline_trap"],
        ),
        (
            "Resolving Target\nRoutes (n=64)",
            by_role["gpt41"]["resolving_route"],
            by_role["luna"]["resolving_route"],
            by_role["combined"]["resolving_route"],
        ),
        (
            "Expert PF\nCohort (n=28)",
            by_cohort["gpt41"]["expert_pf"],
            by_cohort["luna"]["expert_pf"],
            by_cohort["combined"]["expert_pf"],
        ),
        (
            "StructPF Sweep\nCohort (n=75)",
            by_cohort["gpt41"]["pipeline_topic_sweep"],
            by_cohort["luna"]["pipeline_topic_sweep"],
            by_cohort["combined"]["pipeline_topic_sweep"],
        ),
    ]

    labels = [c[0] for c in categories]
    gpt41_vals = [c[1]["recall_strict_pct"] for c in categories]
    luna_vals = [c[2]["recall_strict_pct"] for c in categories]
    comb_vals = [c[3]["recall_strict_pct"] for c in categories]

    x = list(range(len(categories)))
    w = 0.27

    fig, ax = plt.subplots(figsize=(7.6, 3.0))

    b1 = ax.bar(
        [i - w for i in x],
        gpt41_vals,
        width=w * 0.92,
        color=CLR_ORANGE,
        edgecolor="#FFFFFF",
        linewidth=0.7,
        label="Single Solver: GPT-4.1",
        zorder=3,
    )
    b2 = ax.bar(
        x,
        luna_vals,
        width=w * 0.92,
        color=CLR_BLUE,
        edgecolor="#FFFFFF",
        linewidth=0.7,
        label="Single Solver: GPT-5.6-Luna",
        zorder=3,
    )
    b3 = ax.bar(
        [i + w for i in x],
        comb_vals,
        width=w * 0.92,
        color=CLR_GREEN,
        edgecolor="#FFFFFF",
        linewidth=0.7,
        label="Two-Solver Union (Evaluator Panel)",
        zorder=3,
    )

    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 1.5,
                f"{h:.1f}%",
                ha="center",
                va="bottom",
                fontsize=6.9,
                fontweight="bold",
                color=CLR_GREY_DARK,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5, fontweight="bold")
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    ax.set_ylabel("Strict Reference Approach Recall (%)", fontsize=9.0)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        handles=[b1, b2, b3],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=3,
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        fontsize=8.2,
    )

    fig.tight_layout()
    fig.savefig(OUT_DIR / "eth_sample_3_solver_recall.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "eth_sample_3_solver_recall.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_sample_1_diagram()
    make_sample_2_grounding_3arms()
    make_sample_3_solver_recall()
    print(f"Saved ETH LRE style samples to {OUT_DIR}")


if __name__ == "__main__":
    main()
