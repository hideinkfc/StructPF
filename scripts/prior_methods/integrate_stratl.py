"""Integrate the StratL Productive-Failure dataset into data/pf_exercises as YAML.

Source: Puech, Macina, Chatain, Sachan & Kapur (2025), arXiv:2410.03781, CC-BY-4.0,
dataset repo eth-lre/Productive-Failure-Problems (PFdataset.csv, 15 exercises).

The CSV provides type / grade / name / reference / exercise / solution. It does NOT
provide prior_knowledge_required, expected_student_rsms, or critical_conceptual_features.
To keep one schema across expert exercises, those fields are emitted as empty lists with
an explicit provenance marker, so downstream code can rely on the keys existing.

Usage: ./.venv/bin/python scripts/prior_methods/integrate_stratl.py <csv_path>
"""

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "pf_exercises" / "puech_macina_2025_stratl_full.yaml"

SOURCE = "Puech, Macina, Chatain, Sachan & Kapur (2025) — StratL PF dataset"
ARXIV = "arXiv:2410.03781"
REPO = "github.com/eth-lre/Productive-Failure-Problems"
# Fields the source does not provide; emitted empty so the schema stays uniform.
UNSOURCED = ["prior_knowledge_required", "expected_student_rsms", "critical_conceptual_features"]


def topic_of(name: str) -> str:
    table = {
        "consistency": "variance / consistency (descriptive statistics)",
        "country": "apportionment / proportional representation",
        "land-sharing": "fair division",
        "fair-distribution": "fair division",
        "fair-distrubution-time": "fair division",  # typo present in source CSV
        "biking": "average speed / rates",
        "biking-structured": "average speed / rates",
        "hummingbird": "rates / proportion",
        "lawer": "speed, distance, time (car braking)",  # 'lawer' is a source typo
        "lawer-structured": "speed, distance, time (car braking)",
        "lawer-2": "speed, distance, time (car braking)",
        "lawer-2-structured": "speed, distance, time (car braking)",
        "fraction-comparison": "fraction comparison",
        "fraction-comparison-2": "fraction comparison",
        "consistency-tea": "variance / consistency",
    }
    return table.get(name, "mathematics")


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/pf_dataset.csv")
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))

    exercises = []
    for r in rows:
        name = r["name"].strip()
        # Suffix avoids collision with the hand-curated puech_macina_2025_stratl.yaml,
        # which already defines puech2025_consistency and puech2025_country.
        exercises.append(
            {
                "id": f"puech2025_stratl_{name.replace('-', '_')}",
                "type": r["type"].strip(),
                "phase": "generation",
                "topic": topic_of(name),
                "format": "word_problem",
                "grade": r["grade"].strip(),
                "source_reference": r["reference"].strip(),
                "problem": r["exercise"].strip(),
                "canonical_solution": (r.get("solution") or "").strip(),
                # Not present in the StratL CSV; kept empty to preserve the shared schema.
                "prior_knowledge_required": [],
                "expected_student_rsms": [],
                "critical_conceptual_features": [],
            }
        )

    doc = {
        "metadata": {
            "source": SOURCE,
            "license": "CC-BY-4.0",
            "arxiv": ARXIV,
            "dataset_repo": REPO,
            "domain": "Mathematics",
            "n_exercises": len(exercises),
            "grade_levels": sorted({e["grade"] for e in exercises}),
            "provenance_note": (
                "Exercise and solution text come from the StratL PF dataset CSV. "
                "The fields prior_knowledge_required, expected_student_rsms, and "
                "critical_conceptual_features are NOT in the source and are left empty; "
                "do not treat their emptiness as 'none exist'."
            ),
        },
        "exercises": exercises,
    }

    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    print(f"rows read: {len(rows)}")
    print(f"wrote {len(exercises)} exercises -> {OUT.relative_to(ROOT)}")
    print("grades:", sorted({e["grade"] for e in exercises}))
    print("names:", [e["id"] for e in exercises])


if __name__ == "__main__":
    main()
