"""Plot per-task v2.9 measures for the old pipeline, Round 1, Round 2 and the generalized check.

Reads saved outputs only and makes no model calls. A measure with no completed
judgment (for example, a model-call budget was exhausted) is shown as "not run"
and is excluded from that measure's denominator.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OLD_JOBS = ROOT / "experiments/results/pf_generated_tasks_v29_20261015/jobs"
ROUND_DIRS = {
    "Round 1": ROOT / "experiments/results/pf_pipeline_lc_impasse_v2_20261015",
    "Round 2": ROOT / "experiments/results/pf_pipeline_lc_impasse_v3_20261015",
    "Generalized check": ROOT / "experiments/results/pf_pipeline_generalized_check_20261016",
}
OUT_PNG = ROOT / "docs/status/figures/pf_pipeline_rounds_20261016.png"

MEASURES = [
    ("target_alignment", "Target\nalignment"),
    ("mathematical_validity", "Math\nvalidity"),
    ("prior_knowledge_accessibility", "Prior-knowledge\naccess"),
    ("familiar_approach_limits", "Approach\nlimits"),
    ("room_for_invention", "Room for\ninvention"),
]
FAMILY_LABEL = {"kapur": "Average speed", "kerrigan": "Fair division", "loibl": "Variance"}
NOT_RUN = np.nan


def family_from_target(learning_target: str) -> str:
    text = learning_target.lower()
    if "average speed" in text:
        return "kapur"
    if "fair" in text:
        return "kerrigan"
    if "spread" in text or "consistency" in text:
        return "loibl"
    raise ValueError(learning_target)


def family_from_case_id(case_id: str) -> str:
    for fam in FAMILY_LABEL:
        if fam in case_id:
            return fam
    raise ValueError(case_id)


def verdict_to_value(measure: object) -> float:
    value = measure.get("value") if isinstance(measure, dict) else measure
    if value is None or value == "not_assessed":
        return NOT_RUN
    return 1.0 if value == "yes" else 0.0


def load_old() -> list[dict]:
    spec = importlib.util.spec_from_file_location(
        "run_pf_generated_v29", ROOT / "scripts/run_pf_generated_v29.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(module)
    cohorts, by_id = module.select_cohorts(2)
    cohort = next(
        c for c in cohorts if c["label"].startswith("Latest fresh method comparison pipeline")
    )
    rows = []
    for case_id in cohort["case_ids"]:
        result = json.loads((OLD_JOBS / f"{case_id}.json").read_text())["result"]
        rows.append({
            "family": family_from_target(by_id[case_id]["learning_target"]),
            "values": [verdict_to_value(result["measures"][m]) for m, _ in MEASURES],
        })
    return rows


def load_round(root: Path) -> list[dict]:
    rows = []
    for path in sorted((root / "evaluations").glob("*.json")):
        measures = json.loads(path.read_text())["v29"]["measures"]
        rows.append({
            "family": family_from_case_id(path.stem),
            "values": [verdict_to_value(measures[m]) for m, _ in MEASURES],
        })
    return rows


def summarize(rows: list[dict]) -> tuple[list[int], list[int], int, int]:
    matrix = np.array([r["values"] for r in rows], dtype=float)
    passes = [int(np.nansum(matrix[:, j])) for j in range(matrix.shape[1])]
    evaluated = [int(np.sum(~np.isnan(matrix[:, j]))) for j in range(matrix.shape[1])]
    fully_run = ~np.isnan(matrix).any(axis=1)
    all_five = int((np.nan_to_num(matrix[fully_run]) == 1).all(axis=1).sum())
    return passes, evaluated, all_five, int(fully_run.sum())


def main() -> None:
    sets = {"Old pipeline": load_old()}
    for label, root in ROUND_DIRS.items():
        sets[label] = load_round(root)

    summary = {}
    for label, rows in sets.items():
        passes, evaluated, all_five, fully_run = summarize(rows)
        summary[label] = {"n": len(rows), "fully_run": fully_run, "all_five": all_five,
                          "passes": passes, "evaluated": evaluated}
        print(f"{label:<18} n={len(rows)} fully_run={fully_run} all_five={all_five} "
              f"passes={passes} evaluated={evaluated}")

    fig = plt.figure(figsize=(15, 7.2))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.3, 1])

    ax = fig.add_subplot(grid[0, 0])
    blocks, labels, edges = [], [], []
    for label, rows in sets.items():
        edges.append(len(labels))
        for r in rows:
            blocks.append(r["values"])
            labels.append(f"{label} · {FAMILY_LABEL[r['family']]}")
    matrix = np.array(blocks, dtype=float)
    all_five_col = np.where(np.isnan(matrix).any(axis=1), NOT_RUN,
                            (matrix == 1).all(axis=1).astype(float))
    full = np.column_stack([matrix, all_five_col])
    display = np.where(np.isnan(full), 0.5, full)
    cmap = matplotlib.colors.ListedColormap(["#e3e8ee", "#c9ced6", "#2f6f4a"])
    ax.imshow(display, cmap=cmap, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(full.shape[1]))
    ax.set_xticklabels([lab for _, lab in MEASURES] + ["All five\nyes"], fontsize=8.5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    for edge in edges[1:]:
        ax.axhline(edge - 0.5, color="white", linewidth=4)
    for y in range(full.shape[0]):
        for x in range(full.shape[1]):
            v = full[y, x]
            text = "not run" if np.isnan(v) else ("yes" if v == 1 else "no")
            color = "white" if v == 1 else "#4a5560"
            ax.text(x, y, text, ha="center", va="center", fontsize=7.5, color=color)
    ax.set_title("(a) Each task and measure: green = yes, grey = no, light grey = not run",
                 loc="left", fontsize=10.5)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax2 = fig.add_subplot(grid[0, 1])
    names = list(sets.keys())
    measure_labels = [lab for _, lab in MEASURES] + ["All five\nyes"]
    colors = ["#8fa4b8", "#2f6f9f", "#2f6f4a", "#b08a3e"]
    x = np.arange(len(measure_labels))
    width = 0.2
    for i, name in enumerate(names):
        s = summary[name]
        heights = s["passes"] + [s["all_five"]]
        denominators = s["evaluated"] + [s["fully_run"]]
        pos = x + (i - 1.5) * width
        ax2.bar(pos, heights, width, color=colors[i], label=f"{name} (n={s['n']})")
        for px, h, d in zip(pos, heights, denominators):
            ax2.text(px, h + 0.15, f"{h}/{d}", ha="center", fontsize=6.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(measure_labels, fontsize=8)
    ax2.set_ylabel("Tasks rated yes")
    ax2.set_ylim(0, 10)
    ax2.set_title("(b) Tasks passing each measure (passes/evaluated)", loc="left", fontsize=10.5)
    ax2.legend(fontsize=7.5, loc="upper right", frameon=False, ncol=2)
    ax2.spines[["top", "right"]].set_visible(False)

    old = summary["Old pipeline"]
    fig.text(
        0.01, 0.012,
        f"Computational model judgments (pf-three-role v2.9), not human ratings. Old pipeline: "
        f"{old['fully_run']} of {old['n']} tasks fully evaluated "
        "(one hit the model-call budget and is not run). "
        "Generalized check: 3 tasks, one repeat per family.",
        fontsize=8, color="#4a5560",
    )
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150)
    print("saved", OUT_PNG)


if __name__ == "__main__":
    main()
