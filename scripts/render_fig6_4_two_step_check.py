#!/usr/bin/env python3
"""Render the two Section 6.4 figures of the 30-topic curriculum-grounding study.

Figure A (Prior-Knowledge Check): proposed prior skills per generator, classified
as valid, irrelevant or target leak, with the number of topics containing a leak.
Figure B (Method-Failure Check): runs that passed the first check, split into
familiar methods falling short because the target is needed, bypassed by a
familiar method, or falling short for an unrelated reason.

Data: pf_progression_bridge_30cases_3arms_gpt5mini_20261021 (GPT-5 mini
generators, GPT-5.6-luna checks). Greyscale style of Figures 5.4 and 6.2.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

RESULTS = Path("experiments/results/pf_progression_bridge_30cases_3arms_gpt5mini_20261021")
OUT = Path("thesis/figures")
BLACK, DARK_GREY, MID_GREY, LIGHT_GREY = "#000000", "#595959", "#B8B8B8", "#EFEFEF"

ARMS = [
    ("direct", "One-Shot Prompt"),
    ("ungrounded", "StructPF without\nGrounding"),
    ("lc_grounded", "StructPF with\nGrounding"),
]
STYLES = [
    {"color": DARK_GREY},
    {"color": MID_GREY},
    {"color": LIGHT_GREY, "hatch": "//"},
]


def stacked(segments, labels, xlabel, xmax, xticks, right_notes, stem):
    arms_rev = list(reversed(ARMS))
    fig, ax = plt.subplots(figsize=(6.4, 2.35))
    y = list(range(len(arms_rev)))
    left = [0] * len(arms_rev)
    for seg, style in zip(segments, STYLES):
        ax.barh(y, seg, left=left, height=0.54, edgecolor=BLACK, lw=0.75, zorder=3, **style)
        for idx, val in enumerate(seg):
            if val >= 0.05 * xmax:
                dark = style["color"] == DARK_GREY
                ax.text(
                    left[idx] + val / 2,
                    idx,
                    str(val),
                    ha="center",
                    va="center",
                    color="white" if dark else BLACK,
                    fontweight="bold" if dark else "normal",
                    fontsize=8.5,
                    bbox=None
                    if "hatch" not in style
                    else dict(boxstyle="square,pad=0.12", facecolor="white", edgecolor="none"),
                    zorder=4,
                )
        left = [a + b for a, b in zip(left, seg)]
    for idx, note in enumerate(right_notes):
        ax.text(left[idx] + 0.012 * xmax, idx, note, ha="left", va="center", fontsize=8.2)

    ax.set_yticks(y)
    ax.set_yticklabels([label for _, label in arms_rev])
    ax.set_xlim(0, xmax)
    ax.set_xticks(xticks)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color="#D8D8D8", zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    leg = ax.legend(
        handles=[
            Patch(edgecolor=BLACK, linewidth=0.75, label=lab, facecolor=s["color"], hatch=s.get("hatch"))
            for lab, s in zip(labels, STYLES)
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.42),
        ncol=1,
        frameon=True,
        fancybox=False,
        edgecolor=BLACK,
        fontsize=8.2,
    )
    leg.get_frame().set_linewidth(0.8)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"{stem}.{ext}", bbox_inches="tight", pad_inches=0.04, **kw)
    plt.close(fig)
    print(f"Saved {OUT}/{stem}.{{pdf,png}}")


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "pdf.fonttype": 42,
        }
    )
    summary = json.loads((RESULTS / "summary_three_arm.json").read_text())["summary"]["arms"]
    arms_rev = list(reversed(ARMS))

    items = [summary[k]["item_totals"] for k, _ in arms_rev]
    valid = [it["valid_skills"] for it in items]
    irrelevant = [it["irrelevant_skills"] for it in items]
    leak = [it["spoiler_skills"] for it in items]
    leak_topics = [summary[k]["gate1_spoiler_set_count"] for k, _ in arms_rev]
    assert valid == [98, 85, 65] and irrelevant == [4, 7, 0] and leak == [0, 5, 25]
    assert leak_topics == [0, 5, 17]
    stacked(
        [valid, irrelevant, leak],
        ["Valid prior skill", "Irrelevant skill", "Target leak"],
        "Proposed prior skills (all 30 topics)",
        120,
        range(0, 101, 20),
        [f"leak on {n} of 30 topics" for n in leak_topics],
        "fig6_6_prior_knowledge_check",
    )

    outcomes = {k: collections.Counter() for k, _ in ARMS}
    for path in sorted((RESULTS / "evaluations_three_arm").glob("*.json")):
        record = json.loads(path.read_text())
        for k, _ in ARMS:
            gate = (record.get(k) or {}).get("two_gate")
            if gate:
                outcomes[k][gate["outcome"]] += 1
    target = [outcomes[k]["score_2_productive_trap"] for k, _ in arms_rev]
    bypass = [outcomes[k]["score_1_trap_bypassed"] for k, _ in arms_rev]
    unrelated = [outcomes[k]["score_1_off_target_failure"] for k, _ in arms_rev]
    assert target == [19, 16, 6] and bypass == [9, 5, 6] and unrelated == [2, 3, 1]
    totals = [a + b + c for a, b, c in zip(target, bypass, unrelated)]
    assert totals == [30, 24, 13]
    stacked(
        [target, bypass, unrelated],
        [
            "Familiar methods fall short and need the target",
            "Bypassed by a familiar method",
            "Falls short for an unrelated reason",
        ],
        "Runs that passed the Prior-Knowledge Check",
        36,
        range(0, 31, 5),
        [f"{t} of {n} ({round(100 * t / n)}%)" for t, n in zip(target, totals)],
        "fig6_7_method_failure_check",
    )


if __name__ == "__main__":
    main()
