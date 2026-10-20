"""Build the text-answerable Eedi cases with per-option student percentages and misconception explanations.

Picture-dependent questions (shape identification or plan/view items) are excluded because the
solver receives text only. Options are removed from the stem and kept as separate fields; the
solver never sees them. Output: experiments/configs/pf_eedi_coverage_cases_20261016.json
"""

from __future__ import annotations

import glob
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_GLOB = ROOT / "data/eedi_scraped/e*.json"
OUTPUT = ROOT / "experiments/configs/pf_eedi_coverage_cases_20261016.json"
OPTION_TAIL = re.compile(r"\n\n((?:\[[^\[\]]*\]\s*){4})\s*$")
PICTURE_CUE = re.compile(r"\b(this shape|shown|view|plan|diagram|picture)\b", re.I)
MANUAL_EXCLUDE = {
    "eedi_emn0_q2": "the calculation is shown only in a thermometer picture",
}
SHAPE_TOPIC = "Shapes - 3D"
CHOSEN = re.compile(r"\d+% of students on Eedi chose [A-D]\.?\s*$")
HEADING = re.compile(r"^Common misconception", re.I)


def clean_explanation(text: str) -> str:
    text = HEADING.sub("", text or "").strip()
    text = CHOSEN.sub("", text).strip()
    return text


def build() -> dict:
    cases, excluded = [], Counter()
    for path in sorted(glob.glob(str(SOURCE_GLOB))):
        quiz = json.loads(Path(path).read_text())
        for q in quiz["questions"]:
            text = q["question_text"]
            if quiz["topic"] == SHAPE_TOPIC:
                excluded["shape_topic_picture"] += 1
                continue
            match = OPTION_TAIL.search(text)
            if not match:
                excluded["options_not_in_text"] += 1
                continue
            if PICTURE_CUE.search(text[: match.start()]):
                excluded["picture_cue"] += 1
                continue
            case_id = f"eedi_{quiz['quiz_id']}_q{q['question_number']}"
            if case_id in MANUAL_EXCLUDE:
                excluded["manual_picture_only"] += 1
                continue
            stem = text[: match.start()].strip()
            option_texts = re.findall(r"\[([^\[\]]*)\]", match.group(1))
            letters = list("ABCD")
            options = []
            for letter, option_text in zip(letters, option_texts):
                answer = q["answers"][letter]
                options.append(
                    {
                        "letter": letter,
                        "text": option_text.strip(),
                        "is_correct": bool(answer["is_correct"]),
                        "pct_students": answer["pct_students"],
                        "error_explanation": None
                        if answer["is_correct"]
                        else clean_explanation(answer["explanation"]),
                    }
                )
            wrong_total = sum(o["pct_students"] for o in options if not o["is_correct"])
            if wrong_total <= 0:
                excluded["no_wrong_mass"] += 1
                continue
            cases.append(
                {
                    "case_id": case_id,
                    "quiz_name": quiz["quiz_name"],
                    "topic": quiz["topic"],
                    "subject": quiz.get("subject"),
                    "stem": stem,
                    "options": options,
                    "wrong_pct_total": wrong_total,
                }
            )
    payload = {
        "version": "pf-eedi-coverage-cases/v1",
        "source": "data/eedi_scraped (student percentages and common-misconception explanations)",
        "excluded": dict(excluded),
        "case_count": len(cases),
        "cases": cases,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(blob).hexdigest()
    return payload


def main() -> None:
    payload = build()
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "cases"}, indent=2))
    topics = Counter(c["topic"] for c in payload["cases"])
    for topic, n in topics.most_common():
        print(f"{n:3d}  {topic}")


if __name__ == "__main__":
    main()
