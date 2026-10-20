"""Smoke test for the prior-methods plausibility judge.

Judges a hand-picked calibration set of methods (known-real, known-fake, and
ambiguous) with the adapted 0-2 blinded plausibility prompt, on GPT-4.1-mini.
Checks the judge can separate real student methods from confabulation before
any bulk judging.

Usage: ./.venv/bin/python scripts/prior_methods/smoke_plausibility.py
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

OUT = ROOT / "experiments" / "results" / "prior_methods_benchmark" / "smoke_plausibility.json"

# Judge prompt v2 (post-smoke revision):
# - two-step gate: concept-overlap check FIRST and terminal, plausibility second;
#   the v1 exclusion bullet failed (target-concept method scored 2 because
#   plausibility reasoning overrode the buried exclusion).
# - judged object is the general_procedure (skill level), not a numeric instance.
# - score 1 explicitly covers "vague / not a definite procedure" (v1 gave 2 to
#   "one of them just looks like a better deal").
JUDGE_SYSTEM = """You are an independent educational rater in a research study on
automatically generated descriptions of student problem-solving methods.

Study setting:
- The target learners are middle-school mathematics students.
- A "prior method" is a general, transferable procedure a student reaches for BEFORE
  being taught the target concept, using only knowledge they already have.
- A prior method is NOT the concept itself, not one specific calculation, and not a
  general mood or guess — it is a definite procedure.
- Judge the method independently. You see no information about where it came from.

Rating task (two steps, in order):

STEP 1 — CONCEPT CHECK (overrides everything):
Read the hidden concept. Does the candidate's general procedure APPLY the concept's
insight — i.e., does it use the correct mathematical relationship the concept teaches?
- YES → concept_overlap = true, score = 0. (A student who already does this has nothing
  to learn from the lesson.)
- NO → concept_overlap = false, go to step 2. IMPORTANT: a method that VIOLATES or
  IGNORES the concept (the natural wrong approach the concept exists to correct) is a
  prior method, not concept overlap. Only flag overlap when the procedure itself
  embodies the concept's correct insight.

STEP 2 — PLAUSIBILITY (only if step 1 passed):
Judge the general procedure as described, on the topic given.
- Score 2: a definite, executable procedure a real student with only prior knowledge
  would plausibly apply to problems of this topic.
- Score 1: possible but vague, not really a definite procedure, or an unusual reach
  for such a student.
- Score 0: unexecutable, nonsensical, or requires knowledge the student cannot have.

Return JSON only in this format:
{"concept_overlap": false, "score": 2, "reason": "Brief explanation."}
"""

JUDGE_USER = """Topic: {topic}
Hidden concept (students have NOT learned this yet): {concept_text}

Candidate prior method:
- Name: {method_name}
- General procedure: {general_procedure}
- Student thinking: {student_thinking}

Score this prior method."""

# Hand-picked calibration cases for c5 (mixtures / best-buy), written at SKILL level
# (transferable procedure, no bound numbers) per the v2 prompt revision.
CALIBRATION = [
    {
        "case": "real_dominant",
        "note": "the documented 57% best-buy error, stated as a general procedure",
        "expected_band": 2,
        "method": {
            "method_name": "Compare raw amounts",
            "general_procedure": (
                "Compare the raw quantities or prices of the options "
                "directly, without adjusting for differences in size or amount."
            ),
            "student_thinking": "More of it for the money looks like better value.",
        },
    },
    {
        "case": "real_partial_strategy",
        "note": "a real partial strategy: scale one option to a round price, stated generally",
        "expected_band": 2,
        "method": {
            "method_name": "Scale one option to a round amount",
            "general_procedure": (
                "Take the option that looks easiest, scale it up to a "
                "nice round price or amount, and compare the others roughly."
            ),
            "student_thinking": "If I make one of them a nice number I can see which is better.",
        },
    },
    {
        "case": "fake_buzzword",
        "note": "confabulated: sounds technical, unexecutable by a student",
        "expected_band": 0,
        "method": {
            "method_name": "Harmonic density balancing",
            "general_procedure": (
                "Balance the harmonic densities of the options to find the optimal value."
            ),
            "student_thinking": "The harmonic densities need to be balanced out.",
        },
    },
    {
        "case": "target_concept",
        "note": "IS the hidden concept (normalize to common basis); must be gated to 0",
        "expected_band": 0,
        "method": {
            "method_name": "Normalize to the same basis",
            "general_procedure": (
                "Convert each option to the same unit basis (per ml, "
                "per pound, or per 100 ml) and compare the unit values."
            ),
            "student_thinking": "If I get them all to the same unit I can compare directly.",
        },
    },
    {
        "case": "vague_mood",
        "note": "not a definite procedure; v1 scored this 2, v2 should cap at 1",
        "expected_band": 1,
        "method": {
            "method_name": "Guess from the look of the numbers",
            "general_procedure": (
                "Look at the numbers and pick whichever option feels like a better deal."
            ),
            "student_thinking": "One of them just seems like more for the money.",
        },
    },
]


def load_client() -> tuple[OpenAI, str]:
    load_dotenv(ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    model = os.environ.get("AZURE_OPENAI_GPT41_MINI_MODEL", "gpt-4.1-mini").strip()
    if not base_url or not api_key:
        raise RuntimeError("Azure config missing from .env.local")
    return OpenAI(base_url=base_url, api_key=api_key), model


def judge_one(client: OpenAI, model: str, package: dict, case: dict) -> dict:
    user = JUDGE_USER.format(
        topic=package["anchor"]["topic"],
        concept_text=package["concept_text"],
        method_name=case["method"]["method_name"],
        general_procedure=case["method"]["general_procedure"],
        student_thinking=case["method"]["student_thinking"],
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
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
        score = payload.get("score")
        reason = payload.get("reason", "")
        overlap = payload.get("concept_overlap")
        ok = score in (0, 1, 2) and isinstance(overlap, bool)
    except json.JSONDecodeError:
        score, reason, overlap, ok = None, f"parse failure: {text[:120]}", None, False
    return {
        "case": case["case"],
        "score": score,
        "concept_overlap": overlap,
        "reason": reason,
        "parse_ok": ok,
        "expected_band": case["expected_band"],
        "note": case["note"],
    }


def main() -> None:
    package_path = ROOT / "experiments" / "data" / "prior_methods_benchmark" / "c5_commonbasis.json"
    package = json.loads(package_path.read_text())
    client, model = load_client()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda c: judge_one(client, model, package, c), CALIBRATION))

    print(f"judge model: {model}")
    hits = 0
    for r in results:
        band = r["expected_band"]
        mark = ""
        if band is not None:
            mark = "HIT" if r["score"] == band else "MISS"
            hits += r["score"] == band
        print(
            f"  {r['case']:20s} score={r['score']} overlap={r['concept_overlap']} "
            f"expected={band} {mark:4s} | {r['reason'][:70]}"
        )

    n_banded = sum(1 for c in CALIBRATION if c["expected_band"] is not None)
    n_parse_fail = sum(1 for r in results if not r["parse_ok"])
    print(f"\n{hits}/{n_banded} banded cases hit; parse failures: {n_parse_fail}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "judge_model": model,
        "prompt_version": "prior_methods_plausibility_v2",
        "results": results,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"saved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
