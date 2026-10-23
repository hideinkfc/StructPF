#!/usr/bin/env python3
"""Render Figure 6.2 for Section 6.2: Direct comparison of (a) Chapter 3 Surface Rubric
scores vs. (b) PF Eval outcomes on the exact same 238 One-Shot
tasks (118 ready for GPT-5 mini, 120 for GPT-4.1).

Monochrome style matching Figures 3.2 and 6.1.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path("experiments/results")
OUT = Path("thesis/figures")
BLACK, DARK_GREY, PROC, GROUP = "#000000", "#7F7F7F", "#CFCFCF", "#F2F2F2"

RUBRIC_KEYS = ["APK", "SSC", "AE", "MR", "OE"]
RUBRIC_LABELS = [
    "Prior knowledge (APK)",
    "Sweet spot (SSC)",
    "Engagement (AE)",
    "Representations (MR)",
    "Open-endedness (OE)",
]

MEASURES = [
    "target_alignment",
    "mathematical_validity",
    "prior_knowledge_accessibility",
    "familiar_approach_limits",
    "room_for_invention",
]
MEASURE_LABELS = [
    "Alignment",
    "Validity",
    "Accessibility",
    "Limits of familiar\napproaches",
    "Room for invention",
]

MODELS = [("gpt-5-mini", "GPT-5 mini", DARK_GREY), ("gpt-4.1", "GPT-4.1", PROC)]


def load_tasks() -> list[dict]:
    rubric = json.loads(
        (RESULTS / "pf_rahimi_multi_theme_20261013/main_30/scores.json").read_text()
    )["tasks"]
    attempts_dir = RESULTS / "pf_rahimi_multi_theme_20261013/main_30/attempts"
    jobs = RESULTS / "pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/main30_oneshot_v30"

    tasks = []
    for jf in sorted(jobs.glob("*.json")):
        attempt = jf.stem
        adata = json.loads((attempts_dir / f"{attempt}.json").read_text())
        measures = json.loads(jf.read_text())["result"]["measures"]
        sc = rubric[attempt]
        r_dims = None
        if sc["final"] is not None:
            j1 = sc["judges"]["luna-judge-1"]["scores"]
            j2 = sc["judges"]["luna-judge-2"]["scores"]
            r_dims = {k: (j1[k] + j2[k]) / 2.0 for k in RUBRIC_KEYS}
        tasks.append(
            {
                "attempt": attempt,
                "model": adata["model_requested"],
                "outcomes": {m: measures[m]["value"] for m in MEASURES},
                "rubric_total": sc["final"],
                "rubric_dims": r_dims,
            }
        )
    return tasks


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.8,
            "pdf.fonttype": 42,
        }
    )
    tasks = load_tasks()
    assert len(tasks) == 238

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(11.2, 2.95), gridspec_kw={"wspace": 0.62})

    height = 0.36

    # Panel (a): Chapter 3 Surface Rubric (mean score of 3)
    ssc_row = RUBRIC_KEYS.index("SSC")
    ax_l.axhspan(ssc_row - 0.5, ssc_row + 0.5, color=GROUP, lw=0, zorder=0)
    for k, (model, name, color) in enumerate(MODELS):
        rows = [t for t in tasks if t["model"] == model and t["rubric_dims"] is not None]
        means = [sum(t["rubric_dims"][rk] for t in rows) / len(rows) for rk in RUBRIC_KEYS]
        ys = [i + (k - 0.5) * height for i in range(len(RUBRIC_LABELS))]
        ax_l.barh(
            ys,
            means,
            height=height,
            color=color,
            edgecolor=BLACK,
            lw=0.7,
            zorder=3,
            label=name,
        )
        for y, m in zip(ys, means):
            ax_l.text(m + 0.05, y, f"{m:.2f}/3", va="center", fontsize=7.8, zorder=4)

    ax_l.set_yticks(range(len(RUBRIC_LABELS)))
    ax_l.set_yticklabels(RUBRIC_LABELS)
    ax_l.get_yticklabels()[ssc_row].set_fontweight("bold")
    ax_l.set_ylim(len(RUBRIC_LABELS) - 0.5, -0.5)
    ax_l.set_xlim(0, 3.55)
    ax_l.set_xticks([0, 1, 2, 3])
    ax_l.set_xlabel("(a) Chapter 3 Surface Rubric (mean score of 3)")
    ax_l.xaxis.grid(True, linestyle="--", color="#D9D9D9", lw=0.7, zorder=0)
    ax_l.set_axisbelow(True)
    ax_l.spines["top"].set_visible(False)
    ax_l.spines["right"].set_visible(False)

    # Panel (b): PF Eval (% of ready tasks receiving Yes)
    limits_row = MEASURES.index("familiar_approach_limits")
    ax_r.axhspan(limits_row - 0.5, limits_row + 0.5, color=GROUP, lw=0, zorder=0)
    for k, (model, name, color) in enumerate(MODELS):
        rows = [t for t in tasks if t["model"] == model]
        counts = [sum(t["outcomes"][m] == "yes" for t in rows) for m in MEASURES]
        pcts = [100.0 * c / len(rows) for c in counts]
        ys = [i + (k - 0.5) * height for i in range(len(MEASURE_LABELS))]
        ax_r.barh(ys, pcts, height=height, color=color, edgecolor=BLACK, lw=0.7, zorder=3)
        for y, c, p in zip(ys, counts, pcts):
            ax_r.text(p + 1.8, y, f"{c}/{len(rows)} ({p:.0f}%)", va="center", fontsize=7.8, zorder=4)

    ax_r.set_yticks(range(len(MEASURE_LABELS)))
    ax_r.set_yticklabels(MEASURE_LABELS)
    ax_r.get_yticklabels()[limits_row].set_fontweight("bold")
    ax_r.set_ylim(len(MEASURE_LABELS) - 0.5, -0.5)
    ax_r.set_xlim(0, 136)
    ax_r.set_xticks([0, 25, 50, 75, 100])
    ax_r.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax_r.set_xlabel("(b) PF Eval (tasks receiving Yes)")
    ax_r.xaxis.grid(True, linestyle="--", color="#D9D9D9", lw=0.7, zorder=0)
    ax_r.set_axisbelow(True)
    ax_r.spines["top"].set_visible(False)
    ax_r.spines["right"].set_visible(False)

    handles, labels = ax_l.get_legend_handles_labels()
    legend = fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=2,
        frameon=True,
        fontsize=8.5,
        fancybox=False,
        edgecolor=BLACK,
    )
    legend.get_frame().set_linewidth(0.8)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"fig6_3_oneshot_outcomes.{ext}", bbox_inches="tight", pad_inches=0.04, **kw)
    plt.close(fig)
    print(f"Saved {OUT}/fig6_3_oneshot_outcomes.{{pdf,png}}")


if __name__ == "__main__":
    main()

