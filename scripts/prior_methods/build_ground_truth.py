"""Build ground-truth packages for the prior-methods benchmark.

Implements section 11 of docs/pf-generation/PRIOR_METHODS_BENCHMARK.md:
one JSON per concept, extracted from data/eedi_scraped/. No API calls.

Known data caveats (recorded in the benchmark doc):
- gg81 explanations are OCR-corrupted (reference shapes from another quiz);
  only option texts and pick rates are usable -> explanation=None.
- Options with "No explanation" stay in all_errors (prevalence) but are
  excluded from matching (explanation=None).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRAPED = ROOT / "data" / "eedi_scraped"
OUT = ROOT / "experiments" / "data" / "prior_methods_benchmark"

HEADING_PREFIXES = ("Common misconception", "Eedi explanation")
PCT_SUFFIX = re.compile(r"\s*\d+% of students on Eedi.*$", re.S)
NO_EXPL = "No explanation"

# Frozen concept list from PRIOR_METHODS_BENCHMARK.md section 4.
CONCEPTS = [
    {
        "concept_id": "c4_partwhole",
        "concept_text": (
            "Part-to-part versus part-to-whole: a ratio 5:3 means 5/8 of the whole, "
            "not 5/3 and not '5 out of 10'."
        ),
        "grade": 7,
        "quiz": "gg81",
        "questions": [4, 5],
        "explanations_corrupted": True,
    },
    {
        "concept_id": "c5_commonbasis",
        "concept_text": (
            "Comparing mixtures needs a common basis: compare unit rates or fractions "
            "of the whole, not raw amounts."
        ),
        "grade": 7,
        "quiz": "e92o",
        "questions": [1, 3, 4],
    },
    {
        "concept_id": "x_estimation",
        "concept_text": (
            "Overestimating requires rounding at least one number up and none down."
        ),
        "grade": 7,
        "quiz": "emnt",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_orderfrac",
        "concept_text": (
            "Ordering fractions requires a common basis (common denominator or decimal), "
            "not comparing numerators or denominators on their own."
        ),
        "grade": 7,
        "quiz": "e901",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_brackets",
        "concept_text": (
            "Expanding a(b + c) requires multiplying every inside term by the outside factor."
        ),
        "grade": 7,
        "quiz": "emlb",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_range",
        "concept_text": (
            "The range measures spread as max - min over all values, not the gap between "
            "two listed numbers."
        ),
        "grade": 7,
        "quiz": "gfk1",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_revperc",
        "concept_text": (
            "Reversing a p% change needs division by (1 +/- p/100), not subtracting p% "
            "of the new value."
        ),
        "grade": 7,
        "quiz": "fso6",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_onestepeq",
        "concept_text": (
            "Solving a one-step equation needs the inverse operation applied to both sides."
        ),
        "grade": 7,
        "quiz": "emcv",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_decimals",
        "concept_text": (
            "Adding or subtracting decimals requires aligning place value (decimal points), "
            "not right-aligning digits."
        ),
        "grade": 7,
        "quiz": "emkd",
        "questions": [1, 2, 3, 4, 5],
    },
    {
        "concept_id": "x_avgfreq",
        "concept_text": (
            "The mean from a frequency table weights values by frequency; it is not the "
            "mean of the value column."
        ),
        "grade": 7,
        "quiz": "emo8",
        "questions": [1, 2, 3, 4, 5],
    },
]

DOMINANT_PCT = 10


def parse_options(question_text: str) -> list[str]:
    """Extract the bracketed option list from the end of the question text."""
    tail = question_text.rsplit("\n", 1)[-1]
    options = re.findall(r"\[([^\]]+)\]", tail)
    return [o.strip() for o in options]


def clean_explanation(raw: str) -> str | None:
    """Strip heading prefix and trailing pick-rate sentence; None if unusable."""
    text = raw or ""
    for prefix in HEADING_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = PCT_SUFFIX.sub("", text).strip()
    if not text or text.startswith(NO_EXPL):
        return None
    return text


def stem_only(question_text: str) -> str:
    """Question text without the bracketed option line."""
    parts = question_text.rsplit("\n", 1)
    return parts[0].strip() if len(parts) == 2 and "[" in parts[1] else question_text.strip()


def build_concept(spec: dict) -> dict:
    quiz_file = SCRAPED / f"{spec['quiz']}.json"
    quiz = json.loads(quiz_file.read_text())
    corrupted = spec.get("explanations_corrupted", False)

    all_errors = []
    excluded = []
    for q in quiz["questions"]:
        qn = q["question_number"]
        if qn not in spec["questions"]:
            continue
        options = parse_options(q["question_text"])
        stem = stem_only(q["question_text"])
        for letter in sorted(q["answers"]):
            a = q["answers"][letter]
            if a.get("is_correct") in (True, "True"):
                continue
            idx = ord(letter) - ord("A")
            option_text = options[idx] if idx < len(options) else None
            if corrupted:
                explanation = None
                reason = "explanations OCR-corrupted (reference a different quiz)"
            else:
                explanation = clean_explanation(a.get("explanation", ""))
                reason = "No explanation" if explanation is None else None
            entry = {
                "question": qn,
                "option_label": letter,
                "option_text": option_text,
                "explanation": explanation,
                "pct_students": int(a.get("pct_students") or 0),
                "question_stem": stem,
                # Matching requires an explanation (or, for corrupted quizzes, the option
                # text alone is the only signal and matching is option-text-based).
                "matchable": (explanation is not None) or corrupted,
            }
            all_errors.append(entry)
            if reason and not corrupted:
                excluded.append({"question": qn, "option_label": letter, "reason": reason})

    dominant = [e for e in all_errors if e["pct_students"] >= DOMINANT_PCT]

    package = {
        "concept_id": spec["concept_id"],
        "concept_text": spec["concept_text"],
        "grade": spec["grade"],
        "anchor": {
            "quiz": spec["quiz"],
            "quiz_name": quiz.get("quiz_name"),
            "topic": quiz.get("topic"),
            "questions": spec["questions"],
            "questions_omitted": [
                q["question_number"]
                for q in quiz["questions"]
                if q["question_number"] not in spec["questions"]
            ],
        },
        "dominant_threshold_pct": DOMINANT_PCT,
        "dominant_errors": dominant,
        "all_errors": all_errors,
        "excluded": excluded,
    }
    if corrupted:
        package["prevalence_note"] = (
            "gg81: pick rates and option texts only; explanations OCR-corrupted "
            "and excluded from matching"
        )
    return package


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in CONCEPTS:
        package = build_concept(spec)
        path = OUT / f"{spec['concept_id']}.json"
        path.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n")
        n_dom = len(package["dominant_errors"])
        n_all = len(package["all_errors"])
        n_expl = sum(1 for e in package["all_errors"] if e["explanation"])
        print(f"{spec['concept_id']:16s} errors={n_all:2d} with_expl={n_expl:2d} dominant={n_dom}")


if __name__ == "__main__":
    main()
