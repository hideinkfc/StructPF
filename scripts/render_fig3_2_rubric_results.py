#!/usr/bin/env python3
"""Render Figure 3.2: Multi-Theme One-Shot Rubric Evaluation Results.

Panel (a): Mean score across the five rubric dimensions (1-3 scale) for GPT-5 mini (n=117) and GPT-4.1 (n=120).
Panel (b): Mean total rubric score across the four Grade 7 curriculum topic cells (5-15 scale).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "axes.edgecolor": "#222222",
            "axes.linewidth": 0.9,
        }
    )

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(12.6, 4.7),
        dpi=300,
        gridspec_kw={"width_ratios": [1.12, 1.0], "wspace": 0.24},
    )
    fig.patch.set_facecolor("white")

    # Monochrome JupyRecSys / Fig 3.1 palette
    c_mini = "#4D4D4D"  # Dark neutral gray for GPT-5 mini
    c_41 = "#CFCFCF"  # Medium-light gray (matches Fig 3.1 process gray) for GPT-4.1
    c_edge = "#111111"  # Crisp black borders
    c_grid = "#D8D8D8"  # Subtle horizontal grid
    c_box = "#F2F2F2"  # Matches Fig 3.1 container gray

    # ==========================================================================
    # Panel (a): Per-Dimension Scores (1-3 Scale)
    # ==========================================================================
    dims = ["APK", "SSC", "AE", "MR", "OE"]
    mini_means = [2.99, 2.95, 3.00, 2.93, 2.69]
    g41_means = [2.97, 2.54, 3.00, 2.50, 1.82]
    d_labels = ["d = 0.16", "d = 0.90", "Ceiling", "d = 1.17", "d = 1.98"]

    x1 = np.arange(len(dims))
    w = 0.35

    ax1.grid(axis="y", linestyle="--", linewidth=0.65, color=c_grid, zorder=0)
    ax1.axhline(3.0, color=c_edge, linestyle="--", linewidth=0.95, zorder=2)

    ax1.bar(
        x1 - w / 2,
        mini_means,
        w,
        color=c_mini,
        edgecolor=c_edge,
        linewidth=0.9,
        label="GPT-5 mini (n = 117, Mean Total = 14.56 ± 0.49 / 15)",
        zorder=3,
    )
    ax1.bar(
        x1 + w / 2,
        g41_means,
        w,
        color=c_41,
        edgecolor=c_edge,
        linewidth=0.9,
        label="GPT-4.1 (n = 120, Mean Total = 12.82 ± 1.23 / 15)",
        zorder=3,
    )

    label_bg = {"boxstyle": "square,pad=0.07", "facecolor": "white", "edgecolor": "none"}

    for i, (m_val, g_val, d_txt) in enumerate(zip(mini_means, g41_means, d_labels)):
        ax1.text(
            x1[i] - w / 2,
            m_val + 0.05,
            f"{m_val:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.3,
            fontweight="bold",
            color=c_edge,
            bbox=label_bg,
            zorder=4,
        )
        ax1.text(
            x1[i] + w / 2,
            g_val + 0.05,
            f"{g_val:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.3,
            color=c_edge,
            bbox=label_bg,
            zorder=4,
        )
        ax1.text(
            x1[i],
            3.38,
            d_txt,
            ha="center",
            va="center",
            fontsize=7.9,
            fontweight="bold",
            color=c_edge,
            bbox={
                "boxstyle": "square,pad=0.22",
                "facecolor": c_box,
                "edgecolor": c_edge,
                "linewidth": 0.75,
            },
            zorder=4,
        )

    ax1.set_xticks(x1)
    ax1.set_xticklabels(dims, fontsize=9.5, fontweight="bold", color=c_edge)
    ax1.set_ylim(0, 3.62)
    ax1.set_yticks([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    ax1.tick_params(axis="y", labelsize=8.8, colors=c_edge)
    ax1.set_ylabel(
        "Mean Dimension Score (1–3 Scale)", fontsize=9.8, fontweight="bold", color=c_edge
    )
    ax1.set_title(
        "(a) Mean Score by Rubric Dimension (4 Topics Combined)",
        fontsize=10.4,
        fontweight="bold",
        pad=12,
        color=c_edge,
    )
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # ==========================================================================
    # Panel (b): Per-Topic-Cell Total Scores (5-15 Scale)
    # ==========================================================================
    cells = [
        "1. Sports\n(Basketball)",
        "2. Shopping\n(Percent)",
        "3. Music\n(Playlists)",
        "4. Home &\nGarden",
    ]
    c_mini_tot = [14.57, 14.70, 14.60, 14.37]
    c_g41_tot = [13.23, 13.08, 13.63, 11.35]
    c_d_labels = ["d = 1.77", "d = 2.69", "d = 1.69", "d = 3.47"]

    x2 = np.arange(len(cells))

    ax2.grid(axis="y", linestyle="--", linewidth=0.65, color=c_grid, zorder=0)
    ax2.axhline(15.0, color=c_edge, linestyle="--", linewidth=0.95, zorder=2)

    ax2.bar(
        x2 - w / 2,
        c_mini_tot,
        w,
        color=c_mini,
        edgecolor=c_edge,
        linewidth=0.9,
        zorder=3,
    )
    ax2.bar(
        x2 + w / 2,
        c_g41_tot,
        w,
        color=c_41,
        edgecolor=c_edge,
        linewidth=0.9,
        zorder=3,
    )

    for i, (m_val, g_val, d_txt) in enumerate(zip(c_mini_tot, c_g41_tot, c_d_labels)):
        ax2.text(
            x2[i] - w / 2,
            m_val + 0.25,
            f"{m_val:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.3,
            fontweight="bold",
            color=c_edge,
            bbox=label_bg,
            zorder=4,
        )
        ax2.text(
            x2[i] + w / 2,
            g_val + 0.25,
            f"{g_val:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.3,
            color=c_edge,
            bbox=label_bg,
            zorder=4,
        )
        ax2.text(
            x2[i],
            16.9,
            d_txt,
            ha="center",
            va="center",
            fontsize=7.9,
            fontweight="bold",
            color=c_edge,
            bbox={
                "boxstyle": "square,pad=0.22",
                "facecolor": c_box,
                "edgecolor": c_edge,
                "linewidth": 0.75,
            },
            zorder=4,
        )

    ax2.set_xticks(x2)
    ax2.set_xticklabels(cells, fontsize=8.8, fontweight="bold", color=c_edge)
    ax2.set_ylim(0, 18.1)
    ax2.set_yticks([0, 3, 6, 9, 12, 15])
    ax2.tick_params(axis="y", labelsize=8.8, colors=c_edge)
    ax2.set_ylabel("Mean Total Score (5–15 Scale)", fontsize=9.8, fontweight="bold", color=c_edge)
    ax2.set_title(
        "(b) Mean Total Score by Topic Cell (5–15 Scale)",
        fontsize=10.4,
        fontweight="bold",
        pad=12,
        color=c_edge,
    )
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Shared legend at top (sharp corners matching Fig 3.1)
    handles, labels = ax1.get_legend_handles_labels()
    leg = fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=2,
        frameon=True,
        fancybox=False,
        facecolor=c_box,
        edgecolor=c_edge,
        fontsize=9.2,
    )
    leg.get_frame().set_linewidth(0.85)

    out_dir = Path("thesis/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "fig3_2_rubric_comparison.pdf", bbox_inches="tight", pad_inches=0.06)
    fig.savefig(
        out_dir / "fig3_2_rubric_comparison.png", dpi=300, bbox_inches="tight", pad_inches=0.06
    )
    plt.close(fig)
    print("Saved thesis/figures/fig3_2_rubric_comparison.{pdf,png}")


if __name__ == "__main__":
    main()
