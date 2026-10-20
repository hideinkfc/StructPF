"""Plot the 20-case 2-arm Learning Commons Progression Bridge study results.

Reads saved evaluations from experiments/results/pf_progression_bridge_20cases_20261016
and makes no model calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "experiments/results/pf_progression_bridge_20cases_20261016/summary.json"
EVAL_DIR = ROOT / "experiments/results/pf_progression_bridge_20cases_20261016/evaluations"
OUT_PNG = ROOT / "docs/status/figures/pf_progression_bridge_20cases_20261016.png"


def main() -> None:
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    rows = data["per_case"]
    summary = data["summary"]

    fig = plt.figure(figsize=(15.5, 7.6))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0])

    # Panel (a): 20-case heatmap of Progression Bridge Fit (0 / 1 / 2) + leak flags
    ax = fig.add_subplot(grid[0, 0])
    matrix = []
    labels = []
    annotations = []
    for r in rows:
        cid = r["case_id"]
        ev = json.loads((EVAL_DIR / f"{cid}.json").read_text(encoding="utf-8"))
        u_bf = ev["ungrounded"]["bridge_fit"]
        g_bf = ev["lc_grounded"]["bridge_fit"]
        matrix.append([u_bf["score"], g_bf["score"]])
        p_str = ",".join(r["prereq_codes"][:2])
        if len(r["prereq_codes"]) > 2:
            p_str += "+.."
        labels.append(f"G{r['grade']} · {p_str} -> {r['target_code']}")

        def _tag(bf: dict) -> str:
            s = bf["score"]
            leaks = []
            if bf["d1_target_leak"]:
                leaks.append("D1 leak")
            if bf["d3_target_leak"]:
                leaks.append("D3 leak")
            if leaks:
                return f"{s} ({', '.join(leaks)})"
            return f"{s} (exact bridge)" if s == 2 else f"{s} (loose match)"

        annotations.append((_tag(u_bf), _tag(g_bf)))

    arr = np.array(matrix, dtype=float)
    cmap = matplotlib.colors.ListedColormap(["#e8b4b4", "#f3dfb3", "#2f6f4a"])
    ax.imshow(arr, cmap=cmap, aspect="auto", vmin=0, vmax=2)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(
        ["Arm A: Ungrounded\n(LLM guesses D1)", "Arm B: LC-Grounded\n(S_prior -> S_target graph)"],
        fontsize=9.5,
        fontweight="bold",
    )
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8.2)
    for y in range(arr.shape[0]):
        for x in range(2):
            val = int(arr[y, x])
            txt = annotations[y][x]
            color = "white" if val == 2 else "#1f2a36"
            ax.text(
                x,
                y,
                txt,
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold" if val == 2 else "normal",
                color=color,
            )
    ax.set_title(
        "(a) Progression Bridge Fit (0/1/2) across 20 curriculum bridges",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Panel (b): Key grounding & downstream v2.9 metrics (out of 20 tasks)
    ax2 = fig.add_subplot(grid[0, 1])
    u_arm = summary["arms"]["ungrounded"]
    g_arm = summary["arms"]["lc_grounded"]

    categories = [
        "Exact bridge\n(Score = 2)",
        "Boundary miss\n(Score = 0)",
        "Stage D1\ntarget leak",
        "Stage D3\ntarget leak",
        "v2.9 Math\nvalidity",
        "v2.9 Room\nfor invention",
    ]
    u_vals = [
        u_arm["bridge_fit_score_counts"]["score_2_exact_bridge"],
        u_arm["bridge_fit_score_counts"]["score_0_boundary_miss"],
        u_arm["d1_target_leak_count"],
        u_arm["d3_target_leak_count"],
        u_arm["v29_measures"]["mathematical_validity"].get("yes", 0),
        u_arm["v29_measures"]["room_for_invention"].get("yes", 0),
    ]
    g_vals = [
        g_arm["bridge_fit_score_counts"]["score_2_exact_bridge"],
        g_arm["bridge_fit_score_counts"]["score_0_boundary_miss"],
        g_arm["d1_target_leak_count"],
        g_arm["d3_target_leak_count"],
        g_arm["v29_measures"]["mathematical_validity"].get("yes", 0),
        g_arm["v29_measures"]["room_for_invention"].get("yes", 0),
    ]

    x = np.arange(len(categories))
    width = 0.34
    ax2.bar(
        x - width / 2,
        u_vals,
        width,
        color="#8fa4b8",
        label=f"Ungrounded (mean fit = {u_arm['bridge_fit_mean']:.2f}/2)",
    )
    ax2.bar(
        x + width / 2,
        g_vals,
        width,
        color="#2f6f4a",
        label=f"LC-Grounded (mean fit = {g_arm['bridge_fit_mean']:.2f}/2)",
    )
    for i, (uv, gv) in enumerate(zip(u_vals, g_vals)):
        ax2.text(x[i] - width / 2, uv + 0.35, f"{uv}/20", ha="center", fontsize=8.5)
        ax2.text(
            x[i] + width / 2,
            gv + 0.35,
            f"{gv}/20",
            ha="center",
            fontsize=8.5,
            fontweight="bold",
            color="#2f6f4a",
        )

    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, fontsize=8.2)
    ax2.set_ylim(0, 22)
    ax2.set_ylabel("Number of tasks (out of 20)")
    ax2.set_title(
        "(b) Grounding cuts boundary misses (5->1) and D1 target leaks (3->0)",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    ax2.legend(fontsize=9, loc="upper right", frameon=False)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.text(
        0.01,
        0.012,
        "20 curriculum bridges (G5-10), 20/20 tasks per arm from Stage D1 (no hand-written D1). "
        "Paired Bridge Fit: LC > Ungrounded on 6 topics, Ungrounded > LC on 2, tied on 12 "
        "(mean 1.65 vs 1.30; computational gpt-5.6-luna judge).",
        fontsize=8.2,
        color="#4a5560",
    )
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150)
    print("Saved", OUT_PNG)


if __name__ == "__main__":
    main()
