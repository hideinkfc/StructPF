"""Rate saved MCQ distractors with Azure OpenAI-compatible judge models."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, median
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "phase1_mcq"
    / "mcq_20_two_judge_plausibility.json"
)
OUTPUT_DIR = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq"
MANUAL_COMPARISON_PATH = OUTPUT_DIR / "mcq_19_manual_vs_judges.json"
EXCLUDED_QUESTION_ID = 1052
DEFAULT_TIMEOUT_S = 180.0
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_WORKERS = 2
PROMPT_VERSION = "contextual_rater_v2"

RATER_PROMPT_TEMPLATE = """You are an independent educational rater in a research study
on automatically generated mathematics distractors for Productive Failure exercises.

Study setting:
- The target learners are middle-school mathematics students.
- A distractor is a wrong answer option that a student might select when solving a
    multiple-choice mathematics question.
- We are evaluating whether the distractor reflects a recognizable, task-related student error.
- We are not evaluating whether the distractor matches an existing dataset option.
- We are not rewarding an answer merely because it is mathematically wrong or written in a
    convincing way.
- Judge the distractor independently. Do not use or invent a hidden generator rationale or
    reasoning pathway.
- The correct answer is provided only as a reference for you as the rater; it would not be
    shown as correct to a student.

Rating task:
Read the question, correct answer, and candidate distractor. Decide how likely it is that a
middle-school student with incomplete or incorrect mathematical knowledge could select the
distractor while attempting the question.

Give score 0 if the candidate is:
- mathematically equivalent to the correct answer;
- malformed, irrelevant, impossible, or random;
- obviously unrelated to the mathematical task; or
- not connected to a recognizable student error.

Give score 1 if the candidate is:
- possible but weak or ambiguous;
- connected to the task but not strongly diagnostic of a student misconception; or
- a possible arithmetic slip without a clear, recognizable error pattern.

Give score 2 if the candidate is:
- a recognizable error related to the question;
- a realistic consequence of incomplete mathematical knowledge; and
- likely enough that it could attract some target students.

Consider the mathematical structure and wording of the question. Prefer task-related
misconceptions, operation confusions, place-value errors, interpretation errors, or other
recognizable student approaches over arbitrary numerical guesses.

Return JSON only in this format:
{{"score": 0, "reason": "Brief explanation of the rating."}}

Question:
{question_text}

Correct answer (rater reference only):
{correct_answer}

Candidate distractor:
{distractor_text}

What plausibility score does this distractor receive?"""

JUDGE_ENV_VARS = {
    "luna": "AZURE_OPENAI_LUNA_MODEL",
    "gpt54": "AZURE_OPENAI_GPT54_MODEL",
    "gpt41": "AZURE_OPENAI_GPT41_MODEL",
    "gpt41mini": "AZURE_OPENAI_GPT41_MINI_MODEL",
}
JUDGE_DEFAULTS = {
    "luna": "gpt-5.6-luna",
    "gpt54": "gpt-5.4",
    "gpt41": "gpt-4.1",
    "gpt41mini": "gpt-4.1-mini",
}
JUDGE_LABELS = {
    "luna": "gpt_5_6_luna",
    "gpt54": "gpt_5_4",
    "gpt41": "gpt_4_1",
    "gpt41mini": "gpt_4_1_mini",
}
_CACHE_LOCK = threading.Lock()


def contextual_plausibility_prompt(
    record: dict[str, Any],
    distractor: dict[str, Any],
) -> str:
    return RATER_PROMPT_TEMPLATE.format(
        question_text=record["question_text"],
        correct_answer=record["correct_answer"],
        distractor_text=distractor.get("text", ""),
    )


def load_azure_config() -> tuple[str, str, dict[str, str]]:
    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    models = {
        judge: os.environ.get(env_var, JUDGE_DEFAULTS[judge]).strip()
        for judge, env_var in JUDGE_ENV_VARS.items()
    }
    if not base_url:
        raise RuntimeError("AZURE_OPENAI_BASE_URL is missing from .env.local or the environment.")
    if not api_key or api_key == "PASTE_ROTATED_KEY_HERE":
        raise RuntimeError("AZURE_OPENAI_API_KEY is missing or still uses the placeholder.")
    if any(not model for model in models.values()):
        raise RuntimeError("Both Azure judge model names must be non-empty.")
    return base_url, api_key, models


def source_records(
    limit: int | None = None,
    include_excluded: bool = False,
) -> list[dict[str, Any]]:
    payload = json.loads(SOURCE_PATH.read_text())
    records = payload["generated_records"]
    if not include_excluded:
        records = [record for record in records if record["question_id"] != EXCLUDED_QUESTION_ID]
    records = sorted(records, key=lambda record: record["question_id"])
    if limit is not None:
        records = records[:limit]
    if not records:
        raise ValueError("The selected source contains no records.")
    incomplete = [
        record["question_id"]
        for record in records
        if len(record.get("distractors", [])) != 3
    ]
    if incomplete:
        raise ValueError(f"Selected records are not complete three-distractor sets: {incomplete}")
    return records


def _json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in judge output.")
    json_text = cleaned[start : end + 1]
    try:
        result = json.loads(json_text)
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", json_text)
        result = json.loads(repaired)
    if not isinstance(result, dict):
        raise ValueError("Judge output is not a JSON object.")
    return result


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    output = getattr(response, "output", None) or []
    parts = []
    for item in output:
        for content in getattr(item, "content", None) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts)


def _cache_key(prompt: str, model: str) -> str:
    value = json.dumps({"model": model, "prompt": prompt}, sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()


def cached_judge_json(
    prompt: str,
    client: OpenAI,
    model: str,
    cache_path: Path,
    timeout: float,
    max_output_tokens: int,
) -> tuple[dict[str, Any], bool]:
    key = _cache_key(prompt, model)
    with _CACHE_LOCK:
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        if key in cache:
            return cache[key], True

    response = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=max_output_tokens,
        timeout=timeout,
    )
    result = _json_object(_response_text(response))
    with _CACHE_LOCK:
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        cache[key] = result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2))
    return result, False


def _redact_error(error: Exception, api_key: str) -> str:
    message = f"{type(error).__name__}: {error}"
    return message.replace(api_key, "<redacted>")


def judge_one(
    task: tuple[dict[str, Any], int, dict[str, Any]],
    client: OpenAI,
    model: str,
    cache_path: Path,
    api_key: str,
    timeout: float,
    max_output_tokens: int,
) -> dict[str, Any]:
    record, distractor_index, distractor = task
    started = time.perf_counter()
    try:
        result, cache_hit = cached_judge_json(
            contextual_plausibility_prompt(record, distractor),
            client=client,
            model=model,
            cache_path=cache_path,
            timeout=timeout,
            max_output_tokens=max_output_tokens,
        )
        score = int(result.get("score", -1))
        if score not in (0, 1, 2):
            raise ValueError("score must be 0, 1, or 2")
        return {
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": score,
            "reason": str(result.get("reason", "")),
            "cache_hit": cache_hit,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }
    except Exception as error:
        return {
            "question_id": record["question_id"],
            "distractor_index": distractor_index,
            "text": str(distractor.get("text", "")),
            "score": None,
            "reason": _redact_error(error, api_key),
            "cache_hit": False,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }


def run_judge(
    records: list[dict[str, Any]],
    client: OpenAI,
    model: str,
    cache_path: Path,
    api_key: str,
    workers: int,
    timeout: float,
    max_output_tokens: int,
) -> list[dict[str, Any]]:
    tasks = [
        (record, index, distractor)
        for record in records
        for index, distractor in enumerate(record["distractors"], start=1)
    ]
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
        futures = [
            pool.submit(
                judge_one,
                task,
                client,
                model,
                cache_path,
                api_key,
                timeout,
                max_output_tokens,
            )
            for task in tasks
        ]
        for completed, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            status = str(row["score"]) if row["score"] is not None else "missing"
            print(
                f"[{completed}/{len(tasks)}] Q{row['question_id']} "
                f"distractor {row['distractor_index']}: {status}",
                flush=True,
            )
    return sorted(rows, key=lambda row: (row["question_id"], row["distractor_index"]))


def summarize(rows: list[dict[str, Any]], expected: int) -> dict[str, Any]:
    scores = [row["score"] for row in rows if row["score"] is not None]
    missing = expected - len(scores)
    return {
        "expected_outputs": expected,
        "rows_written": len(rows),
        "valid_outputs": len(scores),
        "missing_output_count": missing,
        "valid_output_rate": round(len(scores) / expected, 3) if expected else None,
        "mean_score": round(mean(scores), 3) if scores else None,
        "median_score": median(scores) if scores else None,
        "screen_rate_score_at_least_1": (
            round(sum(score >= 1 for score in scores) / len(scores), 3)
            if scores
            else None
        ),
        "score_counts": {str(score): scores.count(score) for score in (0, 1, 2)},
        "cache_hits": sum(bool(row["cache_hit"]) for row in rows),
    }


def compare_reference(
    rows: list[dict[str, Any]],
    reference: str,
    reference_rows: dict[tuple[int, int], Any],
) -> dict[str, Any]:
    pairs = [
        (row["score"], reference_rows.get((row["question_id"], row["distractor_index"])))
        for row in rows
        if row["score"] is not None
        and reference_rows.get((row["question_id"], row["distractor_index"])) is not None
    ]
    if not pairs:
        return {
            "reference": reference,
            "paired": 0,
            "exact_agreement": None,
            "mean_absolute_difference": None,
            "screen_agreement": None,
        }
    exact = sum(actual == expected for actual, expected in pairs)
    screen = sum((actual >= 1) == (expected >= 1) for actual, expected in pairs)
    return {
        "reference": reference,
        "paired": len(pairs),
        "exact_agreement": round(exact / len(pairs), 3),
        "mean_absolute_difference": round(
            mean(abs(actual - expected) for actual, expected in pairs),
            3,
        ),
        "screen_agreement": round(screen / len(pairs), 3),
        "reference_score_counts": dict(sorted(Counter(expected for _, expected in pairs).items())),
    }


def load_reference_rows() -> tuple[dict[str, dict[tuple[int, int], Any]], str | None]:
    if not MANUAL_COMPARISON_PATH.exists():
        return {}, None
    payload = json.loads(MANUAL_COMPARISON_PATH.read_text())
    rows = payload.get("rows", [])
    references = {
        reference: {
            (row["question_id"], row["distractor_index"]): row.get(reference)
            for row in rows
            if row.get(reference) is not None
        }
        for reference in ("manual", "apertus", "glm")
    }
    return references, str(MANUAL_COMPARISON_PATH.relative_to(PROJECT_ROOT))


def output_path(judge: str) -> Path:
    return OUTPUT_DIR / (
        f"mcq_19_azure_{JUDGE_LABELS[judge]}_plausibility_{PROMPT_VERSION}.json"
    )


def run_one_model(
    judge: str,
    records: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    model: str,
    workers: int,
    timeout: float,
    max_output_tokens: int,
) -> Path:
    path = output_path(judge)
    cache_path = OUTPUT_DIR / (
        f"azure_{JUDGE_LABELS[judge]}_{PROMPT_VERSION}_distractor_judge_cache.json"
    )
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    expected = sum(len(record["distractors"]) for record in records)
    payload: dict[str, Any] = {
        "status": "running",
        "source": str(SOURCE_PATH.relative_to(PROJECT_ROOT)),
        "excluded_question_id": (
            None
            if any(record["question_id"] == EXCLUDED_QUESTION_ID for record in records)
            else EXCLUDED_QUESTION_ID
        ),
        "questions_evaluated": len(records),
        "distractors_expected": expected,
        "judge": judge,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "api": "OpenAI Responses API",
        "plausibility_scale": "0-2 compact student-selection rubric",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    rows = run_judge(
        records,
        client,
        model,
        cache_path,
        api_key,
        workers,
        timeout,
        max_output_tokens,
    )
    references, reference_source = load_reference_rows()
    summary = summarize(rows, expected)
    payload.update(
        {
            "status": "complete",
            "judgments": rows,
            "summary": summary,
            "comparisons": [
                compare_reference(rows, reference, reference_rows)
                for reference, reference_rows in references.items()
            ],
            "comparison_source": reference_source,
            "interpretation": (
                "Azure model scores are stronger LLM proxies, not human raters or ground truth. "
                "Agreement with assistant labels and local judges is descriptive only."
            ),
        }
    )
    path.write_text(json.dumps(payload, indent=2))
    print(f"Saved: {path}")
    print(json.dumps(summary, indent=2))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judge",
        choices=("luna", "gpt54", "gpt41", "gpt41mini", "all"),
        default="gpt41mini",
    )
    parser.add_argument("--limit", type=int, help="Evaluate only the first N selected questions.")
    parser.add_argument("--include-excluded", action="store_true", help="Include question 1052.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")

    base_url, api_key, models = load_azure_config()
    records = source_records(args.limit, args.include_excluded)
    judges = ("luna", "gpt54") if args.judge == "all" else (args.judge,)
    print(f"Azure endpoint: {base_url}")
    print(
        f"Questions: {len(records)}, "
        f"distractors: {sum(len(record['distractors']) for record in records)}"
    )
    for judge in judges:
        print(f"Judge: {judge} ({models[judge]})")
        run_one_model(
            judge,
            records,
            base_url,
            api_key,
            models[judge],
            args.workers,
            args.timeout,
            args.max_output_tokens,
        )


if __name__ == "__main__":
    main()
