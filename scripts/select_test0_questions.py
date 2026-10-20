"""Test 0 of the functional-diversity verification plan: pick Eedi questions
usable as a known-answer reference set for the simulated-student experiments.

Writes experiments/configs/functional_diversity_test0_questions.json.
"""

import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data" / "eedi" / "train.csv"
MAPPING = ROOT / "data" / "eedi" / "misconception_mapping.csv"
OUT = ROOT / "experiments" / "configs" / "functional_diversity_test0_questions.json"

MIN_SIBLINGS = 7

DEFICIT_PREFIXES = (
    "does not",
    "do not",
    "doesnt",
    "does nt",
    "not ",
    "unable",
    "fails",
    "cannot",
    "can not",
    "has no",
    "lacks",
    "forgets",
    "is unable",
)

IMAGE_MARKERS = ("![", "image", "diagram", "graph")


def misconception_id(row: dict, letter: str) -> str:
    raw = row[f"Misconception{letter}Id"].strip()
    return str(int(float(raw))) if raw else ""


def is_deficit_phrased(label: str) -> bool:
    return label.strip().lower().startswith(DEFICIT_PREFIXES)


def needs_image(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in IMAGE_MARKERS)


def main() -> None:
    rows = list(csv.DictReader(TRAIN.open()))
    labels = {r["MisconceptionId"]: r["MisconceptionName"] for r in csv.DictReader(MAPPING.open())}

    by_construct = collections.defaultdict(list)
    for row in rows:
        by_construct[row["ConstructName"]].append(row)

    selected = []
    for row in rows:
        siblings = [
            r for r in by_construct[row["ConstructName"]] if r["QuestionId"] != row["QuestionId"]
        ]
        if len(siblings) < MIN_SIBLINGS:
            continue

        wrong_letters = [letter for letter in "ABCD" if letter != row["CorrectAnswer"]]
        ids = [misconception_id(row, letter) for letter in wrong_letters]
        names = [labels.get(mid, "") for mid in ids]
        if not all(ids) or not all(names):
            continue
        if len(set(ids)) != 3:
            continue
        if any(is_deficit_phrased(name) for name in names):
            continue
        if needs_image(row["QuestionText"]):
            continue

        # Each error rule must be observable in another question of the same skill,
        # so profiles can be built without reading the target question's own labels.
        elsewhere = {}
        for mid in ids:
            elsewhere[mid] = [
                sibling["QuestionId"]
                for sibling in siblings
                if any(misconception_id(sibling, letter) == mid for letter in "ABCD")
            ]
        if not all(elsewhere[mid] for mid in ids):
            continue

        correct = row["CorrectAnswer"]
        selected.append(
            {
                "question_id": int(row["QuestionId"]),
                "subject": row["SubjectName"],
                "skill": row["ConstructName"],
                "questions_sharing_skill": len(siblings) + 1,
                "question_text": row["QuestionText"],
                "correct_option": correct,
                "correct_text": row[f"Answer{correct}Text"].strip(),
                "distractors": [
                    {
                        "option": letter,
                        "text": row[f"Answer{letter}Text"].strip(),
                        "misconception_id": misconception_id(row, letter),
                        "misconception_label": labels[misconception_id(row, letter)],
                        "same_error_in_questions": elsewhere[misconception_id(row, letter)],
                        "error_rule": None,
                        "predicted_answer": None,
                        "rule_verified_by_hand": False,
                    }
                    for letter in wrong_letters
                ],
            }
        )

    payload = {
        "purpose": (
            "Reference questions for Tests 1-5 of the functional-diversity verification plan. "
            "Eedi's own labelled distractors provide a known answer key; profiles for the real "
            "experiment must be built from same_error_in_questions, not from the target question."
        ),
        "source": "data/eedi/train.csv",
        "filters": {
            "min_other_questions_sharing_skill": MIN_SIBLINGS,
            "all_three_distractors_labelled": True,
            "three_distinct_misconception_ids": True,
            "each_error_also_appears_in_another_question_of_same_skill": True,
            "labels_phrased_as_actions_not_deficits": True,
            "no_image_or_diagram_marker": True,
        },
        "status": "candidates; error_rule and predicted_answer still need manual authoring",
        "n_questions": len(selected),
        "n_skills": len({item["skill"] for item in selected}),
        "questions": selected,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(selected)} questions, {payload['n_skills']} skills")


if __name__ == "__main__":
    main()
