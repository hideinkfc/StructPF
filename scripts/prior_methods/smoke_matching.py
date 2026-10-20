"""Smoke test for the prior-methods matcher.

Runs the three-way matcher on hand-picked candidates against the x_brackets
ground-truth package. Cases chosen so the expected verdict is known:
- a real documented error (multiply only first term -> Eedi explanation)
- the same error on the second term (mirror)
- a plausible undocumented strategy
- a confabulation
- the target concept itself

Usage: ./.venv/bin/python scripts/prior_methods/smoke_matching.py
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "experiments" / "data" / "prior_methods_benchmark"
OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "smoke_matching.json"

MATCHER_SYSTEM = """You compare a candidate student method against documented real
student errors. You answer exactly one question: does the candidate describe the
SAME underlying error as one of the documented entries?

You are not judging quality, plausibility, or correctness. Only sameness.

Respond ONLY with valid JSON."""

MATCHER_USER = """Topic: {topic}

CANDIDATE METHOD:
- General procedure: {general_procedure}
- Student thinking: {student_thinking}

DOCUMENTED ERRORS (each from a teacher explaining an option real students chose):
{ground_truth_list}

Two descriptions are the SAME error when the student performs the same wrong
action for the same reason. Judge by what the student DOES, not by what they
fail to do — many different errors share the same omission.

Return the entry number only when you would be comfortable telling a teacher
"this candidate IS this documented error." When in doubt, return null — an
unmatched candidate is a normal and expected outcome, not a failure.

Return JSON only:
{{"matched_error_index": 0 or null, "confidence": "high"|"medium"|"low",
  "reason": "one sentence"}}"""


def ground_truth_list(package: dict) -> str:
    lines = []
    for i, e in enumerate(package["all_errors"]):
        expl = e["explanation"] or "(no explanation available)"
        lines.append(
            f"[{i}] {e['pct_students']}% of students chose \"{e['option_text']}\" "
            f"on: {e['question_stem'][:120]} | teacher note: {expl[:220]}"
        )
    return "\n".join(lines)


# Candidates from real smoke_patterns output + hand-written controls.
CASES = [
    {
        "case": "real_multiply_first_term",
        "expected": "MATCH",
        "note": "Eedi Q3D: 'forgot to multiply BOTH terms' (14%)",
        "method": {
            "method_name": "Multiply Only the First Number",
            "general_procedure": ("Multiply the outside number by the first number inside, "
                "and leave the rest as they are."),
            "student_thinking": (
                "You start with the first part, so just use that for multiplication."),
        },
    },
    {
        "case": "real_sign_error",
        "expected": "MATCH",
        "note": "Eedi Q2A: subtracting all of (5x-9), sign on 9 wrong (26%)",
        "method": {
            "method_name": "Forget to flip the second sign",
            "general_procedure": (
                "When subtracting a group, change the sign of the first term inside but forget to "
                "change the sign of the second term."),
            "student_thinking": "I flip the sign on the first thing but the rest stays the same.",
        },
    },
    {
        "case": "strategy_concatenate",
        "expected": None,
        "note": "plausible but no Eedi row describes it -> expect matched_error_index null",
        "method": {
            "method_name": "Concatenate Terms",
            "general_procedure": (
                "Write the outside number and the inside numbers next to each other as one "
                "combined number without multiplying."),
            "student_thinking": (
                "Brackets just mean to list the terms together with the outside number."),
        },
    },
    {
        "case": "confabulation_extra_step",
        "expected": None,
        "note": "invented +1 step; matcher should return null (no documented match)",
        "method": {
            "method_name": "Multiply each term and add one extra",
            "general_procedure": (
                "Multiply the outside number by each number inside, then add one more to the "
                "total at the end."),
            "student_thinking": (
                "I know multiplication sometimes needs an extra step, so I add one at the end."),
        },
    },
    {
        "case": "target_concept_distribute",
        "expected": None,
        "note": "correct distribution; upstream judge gates this, matcher should return null",
        "method": {
            "method_name": "Multiply every inside term",
            "general_procedure": (
                "Multiply the outside number by every term inside the brackets and add the "
                "results."),
            "student_thinking": "The outside number belongs to every term inside.",
        },
    },
]


def load_client(which: str = "mini") -> tuple[OpenAI, str]:
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    env = ("AZURE_OPENAI_GPT41_MODEL" if which == "full"
           else "AZURE_OPENAI_GPT41_MINI_MODEL")
    default = "gpt-4.1" if which == "full" else "gpt-4.1-mini"
    model = os.environ.get(env, default).strip()
    if not base_url or not api_key:
        raise RuntimeError("Azure config missing from .env.local")
    return OpenAI(base_url=base_url, api_key=api_key), model


def match_one(client: OpenAI, model: str, package: dict, gt_list: str, case: dict) -> dict:
    m = case["method"]
    user = MATCHER_USER.format(
        topic=package["anchor"]["topic"],
        general_procedure=m["general_procedure"],
        student_thinking=m["student_thinking"],
        ground_truth_list=gt_list,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": MATCHER_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=300,
        response_format={"type": "json_object"},
        timeout=120,
    )
    text = response.choices[0].message.content or ""
    try:
        payload = json.loads(text)
        idx = payload.get("matched_error_index")
        ok = (idx is None) or isinstance(idx, int)
        return {
            "case": case["case"], "expected": case["expected"], "note": case["note"],
            "matched_error_index": idx,
            "confidence": payload.get("confidence"),
            "reason": payload.get("reason", ""),
            "parse_ok": ok, "raw": payload,
        }
    except json.JSONDecodeError:
        return {
            "case": case["case"], "expected": case["expected"], "note": case["note"],
            "matched_error_index": None, "confidence": None,
            "reason": f"parse failure: {text[:200]}", "parse_ok": False, "raw": text,
        }


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "mini"
    package = json.loads((DATA / "x_brackets.json").read_text())
    gt_list = ground_truth_list(package)
    client, model = load_client(which)

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda c: match_one(client, model, package, gt_list, c), CASES))

    def _hit(r):
        exp = r["expected"]
        idx = r["matched_error_index"]
        if exp == "MATCH":
            return r["parse_ok"] and idx is not None
        return r["parse_ok"] and idx is None  # expected None -> no match
    hits = sum(_hit(r) for r in results)
    for r in results:
        mark = "HIT " if _hit(r) else "MISS"
        idx = r["matched_error_index"]
        print(f"{mark} {r['case']:28s} -> idx={idx} (conf={r['confidence']})")
        print(f"      {r['reason'][:120]}")

    out_path = OUT if which == "mini" else OUT.with_name("smoke_matching_gpt41.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "matcher_model": model,
        "prompt_version": "matcher_v1",
        "concept": package["concept_id"],
        "hits": hits, "total": len(results),
        "results": results,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{hits}/{len(results)} hit; saved -> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
