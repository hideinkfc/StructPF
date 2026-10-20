"""Retrieve curriculum grounding for an expert PF task by (grade, topic) or exercise id.

Reads the YAML files in data/curriculum_grounding/ (excluding documents/) and
returns the matching cell with its page-referenced prior resources.

Usage:
    ./.venv/bin/python scripts/lookup_curriculum_grounding.py --exercise kapur2012_complex_1
    ./.venv/bin/python scripts/lookup_curriculum_grounding.py --grade 10 --topic variance
    ./.venv/bin/python scripts/lookup_curriculum_grounding.py --list
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

GROUNDING_DIR = Path(__file__).resolve().parents[1] / "data" / "curriculum_grounding"


def load_cells() -> list[dict]:
    cells = []
    for path in sorted(GROUNDING_DIR.glob("*.yaml")):
        with open(path) as f:
            cell = yaml.safe_load(f)
        cell["_file"] = path.name
        cells.append(cell)
    return cells


def find(cells: list[dict], exercise: str | None, grade: int | None, topic: str | None) -> list[dict]:
    hits = []
    for cell in cells:
        if exercise and exercise in cell.get("expert_tasks_grounded", []):
            hits.append(cell)
            continue
        if grade is not None and str(cell.get("grade")) != str(grade):
            continue
        if topic and topic.lower() not in (cell.get("target_concept", "") + " " + cell.get("id", "")).lower():
            continue
        if exercise is None:
            hits.append(cell)
    return hits


def summarize(cell: dict) -> dict:
    return {
        "id": cell["id"],
        "file": cell["_file"],
        "grade": cell["grade"],
        "country": cell["country"],
        "target_concept": cell["target_concept"],
        "sources": [s["name"] for s in cell.get("sources", [])],
        "prior_resources": [
            {
                "resource": r["resource"],
                "taught_at": r.get("taught_at"),
                "section": r.get("section"),
                "pages": r.get("pages"),
                "source": r.get("source"),
            }
            for r in cell.get("prior_resources_taught_before_target", [])
        ],
        "target_first_appearance": cell.get("target_concept_first_appearance", {}).get("location"),
        "caveats": cell.get("caveats", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise", help="Expert exercise id, e.g. kapur2012_complex_1")
    parser.add_argument("--grade", type=int, help="Grade number")
    parser.add_argument("--topic", help="Topic substring, e.g. variance")
    parser.add_argument("--list", action="store_true", help="List all grounding cells")
    args = parser.parse_args()

    cells = load_cells()

    if args.list:
        for c in cells:
            print(f"{c['id']:42s} grade={c['grade']!s:12s} {c['target_concept'][:60]}")
        return

    hits = find(cells, args.exercise, args.grade, args.topic)
    if not hits:
        print("No grounding cell found.")
        return
    print(json.dumps([summarize(c) for c in hits], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
