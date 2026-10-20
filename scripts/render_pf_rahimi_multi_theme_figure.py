"""Render the Rahimi-style two-model comparison from the saved multi-theme scores.

Inputs: experiments/results/pf_rahimi_multi_theme_20261013/main_30/scores.json.
Each task's dimension score is the mean of its two judge passes; only tasks with
both passes scored are used. Outputs are standalone SVGs with their own styles:
our two models alone, and our two models beside Rahimi et al. Table 2.
"""

from __future__ import annotations

import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/results/pf_rahimi_multi_theme_20261013/main_30"
OUT = RUN / "rahimi_style_comparison.svg"
COMBINED = RUN / "rahimi_vs_replication_comparison.svg"
DIMS = ["APK", "SSC", "AE", "MR", "OE"]
NAMES = {
    "APK": "Activation of prior knowledge",
    "SSC": "Sweet spot calibration",
    "AE": "Affective engagement",
    "MR": "Multiple representations",
    "OE": "Open-endedness",
}
MODELS = [("gpt-5-mini", "GPT-5 mini", "#5b9b4a"), ("gpt-4.1", "GPT-4.1", "#d9a21b")]
# Rahimi et al. (ICLS 2026) Table 2, p. 2: (mean, SD) per model and Cohen's d, GPT-4o minus Phi-3.
# Checked against the PDF text; n = 30 per model, two trained human raters.
PAPER = {
    "APK": ((2.65, 0.35), (2.42, 0.53), 0.52),
    "SSC": ((2.52, 0.55), (2.08, 0.62), 0.74),
    "AE": ((2.75, 0.47), (2.45, 0.71), 0.50),
    "MR": ((2.70, 0.43), (1.83, 0.61), 1.65),
    "OE": ((2.77, 0.47), (1.88, 0.64), 1.58),
}
PAPER_TOTAL = ((13.38, 1.88), (10.67, 2.73), 1.16)
PAPER_MODELS = [("GPT-4o", "#2f6f9f"), ("Phi-3 mini", "#b5523b")]
X0, PX_PER_POINT = 250, 180


def load_scores() -> dict[str, list[dict]]:
    tasks = json.loads((RUN / "scores.json").read_text(encoding="utf-8"))["tasks"]
    grouped: dict[str, list[dict]] = {model: [] for model, _, _ in MODELS}
    for task in tasks.values():
        if task["status"] != "final":
            continue
        row = {"total": task["final"]}
        for dim in DIMS:
            values = [task["judges"][j]["scores"][dim] for j in task["judges"]]
            row[dim] = st.mean(values)
        grouped[task["model"]].append(row)
    return grouped


def describe(rows: list[dict], key: str) -> tuple[float, float, int]:
    values = [row[key] for row in rows]
    return st.mean(values), st.stdev(values), len(values)


def cohens_d(a: list[dict], b: list[dict], key: str) -> float | None:
    m1, s1, n1 = describe(a, key)
    m2, s2, n2 = describe(b, key)
    pooled = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled == 0:
        return None
    return (m1 - m2) / pooled


def render(grouped: dict[str, list[dict]]) -> str:
    a, b = grouped[MODELS[0][0]], grouped[MODELS[1][0]]
    row_h = 92
    height = 90 + row_h * len(DIMS) + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" '
        'aria-label="Mean dimension scores for GPT-5 mini and GPT-4.1 under the Rahimi setting">',
        "<style>text{font:15px system-ui,-apple-system,Segoe UI,sans-serif;fill:#1d2733}"
        ".big{font-size:20px;font-weight:600}.small{font-size:13px;fill:#596878}</style>",
        f'<rect x="0" y="0" width="1000" height="{height}" fill="#ffffff"/>',
    ]
    legend_x = 0
    for model, label, color in MODELS:
        parts.append(f'<rect x="{legend_x}" y="14" width="13" height="13" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 20}" y="26">{label} (n = {len(grouped[model])})</text>')
        legend_x += 220
    parts.append('<text x="920" y="26" class="small">Cohen&#8217;s d</text>')
    for i, dim in enumerate(DIMS):
        y = 58 + i * row_h
        parts.append(f'<text x="0" y="{y + 26}" class="big">{dim}</text>')
        parts.append(f'<text x="0" y="{y + 46}" class="small">{NAMES[dim]}</text>')
        for j, (model, label, color) in enumerate(MODELS):
            rows = grouped[model]
            mean, sd, _ = describe(rows, dim)
            by = y + j * 28
            width = mean * PX_PER_POINT
            parts.append(
                f'<rect x="{X0}" y="{by}" width="{width:.1f}" height="22" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{X0 + width + 10:.1f}" y="{by + 17}">'
                f"{mean:.2f} (SD {sd:.2f})</text>"
            )
        d = cohens_d(a, b, dim)
        d_text = "n/a" if d is None else f"{d:.2f}"
        parts.append(f'<text x="920" y="{y + 36}" class="big">{d_text}</text>')
    axis_top = 46
    axis_bottom = 58 + row_h * len(DIMS) - 20
    parts.append(f'<line x1="{X0}" y1="{axis_top}" x2="{X0}" y2="{axis_bottom}" stroke="#c4cfdb"/>')
    x3 = X0 + 3 * PX_PER_POINT
    parts.append(
        f'<line x1="{x3}" y1="{axis_top}" x2="{x3}" y2="{axis_bottom}" '
        'stroke="#c4cfdb" stroke-dasharray="4 4"/>'
    )
    parts.append(
        f'<text x="{x3}" y="{axis_bottom + 18}" class="small" text-anchor="middle">'
        "3 = top of scale</text>"
    )
    total_y = height - 26
    total_a = describe(a, "total")
    total_b = describe(b, "total")
    parts.append(
        f'<text x="0" y="{total_y}">Total out of 15: GPT-5 mini {total_a[0]:.2f} '
        f"(SD {total_a[1]:.2f}); GPT-4.1 {total_b[0]:.2f} (SD {total_b[1]:.2f})</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_combined(grouped: dict[str, list[dict]]) -> str:
    a, b = grouped[MODELS[0][0]], grouped[MODELS[1][0]]
    offsets = [0, 22, 54, 76]
    row_h = 104
    top = 112
    height = top + row_h * len(DIMS) + 96
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" '
        'aria-label="Mean dimension scores: Rahimi et al. and our two models">',
        "<style>text{font:15px system-ui,-apple-system,Segoe UI,sans-serif;fill:#1d2733}"
        ".big{font-size:20px;font-weight:600}.small{font-size:13px;fill:#596878}</style>",
        f'<rect x="0" y="0" width="1000" height="{height}" fill="#ffffff"/>',
    ]
    legend_1 = [(name, color) for name, color in PAPER_MODELS]
    legend_2 = [(label, color) for _, label, color in MODELS]
    for row, (legend, note) in enumerate([
        (legend_1, "Rahimi et al. (paper): two trained human raters, n = 30 per model"),
        (legend_2, f"This replication: two Luna AI passes, n = {len(a)} and {len(b)}"),
    ]):
        y = 22 + row * 30
        x = 0
        for name, color in legend:
            parts.append(
                f'<rect x="{x}" y="{y - 12}" width="13" height="13" rx="3" fill="{color}"/>'
            )
            parts.append(f'<text x="{x + 20}" y="{y}">{name}</text>')
            x += 150
        parts.append(f'<text x="{x + 10}" y="{y}" class="small">{note}</text>')
    for i, dim in enumerate(DIMS):
        y = top + i * row_h
        parts.append(f'<text x="0" y="{y + 22}" class="big">{dim}</text>')
        parts.append(f'<text x="0" y="{y + 40}" class="small">{NAMES[dim]}</text>')
        ours_d = cohens_d(a, b, dim)
        ours_text = "n/a" if ours_d is None else f"{ours_d:.2f}"
        parts.append(
            f'<text x="0" y="{y + 58}" class="small">'
            f"d paper {PAPER[dim][2]:.2f} · ours {ours_text}</text>"
        )
        paper_bars = [
            (name, color, *PAPER[dim][j]) for j, (name, color) in enumerate(PAPER_MODELS)
        ]
        our_bars = [
            (label, color, *describe(grouped[model], dim)[:2]) for model, label, color in MODELS
        ]
        bars = paper_bars + our_bars
        for offset, (_, color, mean, sd) in zip(offsets, bars):
            by = y + offset
            width = mean * PX_PER_POINT
            parts.append(
                f'<rect x="{X0}" y="{by}" width="{width:.1f}" height="18" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{X0 + width + 8:.1f}" y="{by + 14}">{mean:.2f} (SD {sd:.2f})</text>'
            )
    axis_top = top - 8
    axis_bottom = top + row_h * len(DIMS) - 14
    parts.append(f'<line x1="{X0}" y1="{axis_top}" x2="{X0}" y2="{axis_bottom}" stroke="#c4cfdb"/>')
    x3 = X0 + 3 * PX_PER_POINT
    parts.append(
        f'<line x1="{x3}" y1="{axis_top}" x2="{x3}" y2="{axis_bottom}" '
        'stroke="#c4cfdb" stroke-dasharray="4 4"/>'
    )
    parts.append(
        f'<text x="{x3}" y="{axis_bottom + 16}" class="small" text-anchor="middle">'
        "3 = top of scale</text>"
    )
    ours_total = (describe(a, "total"), describe(b, "total"))
    ours_total_d = cohens_d(a, b, "total")
    (p1, p2, pd) = PAPER_TOTAL
    parts.append(
        f'<text x="0" y="{height - 46}">Total out of 15 (mean, SD), paper: GPT-4o '
        f"{p1[0]:.2f} ({p1[1]:.2f}) vs Phi-3 mini {p2[0]:.2f} ({p2[1]:.2f}), d = {pd:.2f}</text>"
    )
    parts.append(
        f'<text x="0" y="{height - 22}">Total out of 15 (mean, SD), ours: GPT-5 mini '
        f"{ours_total[0][0]:.2f} ({ours_total[0][1]:.2f}) vs GPT-4.1 "
        f"{ours_total[1][0]:.2f} ({ours_total[1][1]:.2f}), d = {ours_total_d:.2f}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    grouped = load_scores()
    OUT.write_text(render(grouped), encoding="utf-8")
    COMBINED.write_text(render_combined(grouped), encoding="utf-8")
    print("wrote", COMBINED)
    for model, label, _ in MODELS:
        print(label, "n =", len(grouped[model]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
