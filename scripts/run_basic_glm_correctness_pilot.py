"""Run the basic GLM distractor pilot and measure answer-level correctness."""

from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openai import OpenAI

from scripts.run_azure_mcq_plausibility import load_azure_config
from src.evaluation.mcq_metrics import normalize_expression
from src.utils.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "eedi" / "test_set_200.json"
RESULTS_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "basic_glm_correctness_pilot.json"
)
MODEL = "zai-org/GLM-4.7-Flash"
MAX_TOKENS = 8192
RETRY_MAX_TOKENS = 16384
TEMPERATURE = 0.2
RANDOM_SEED = 42
SAMPLE_SIZE = 10
ALLOWED_FORMATS = ("numeric", "equation")
GENERATION_TIMEOUT_S = 30.0
WORKERS = 5
DERIVATION_ENABLED = False
JUDGE_MODEL = "gpt-4.1-mini"
JUDGE_TIMEOUT_S = 20.0
JUDGE_MAX_TOKENS = 2048
JUDGE_REPEATS = 1
JUDGE_CACHE_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "distractor_judge_cache.json"
)
_JUDGE_CACHE_LOCK = threading.Lock()

BASIC_SYSTEM_PROMPT = (
    "You generate wrong answers for math multiple-choice questions. Respond with a JSON array only."
)
BASIC_USER_TEMPLATE = """Generate exactly 3 wrong but plausible distractors for this math question.

Question: {question}
Correct answer: {correct_answer}

For each distractor return:
- text: the bare wrong answer only
- target_misconception: a short name for the error
- error_rationale: one short sentence

Return exactly 3 JSON objects in an array."""
STRUCTURED_USER_TEMPLATE = """Generate exactly 3 wrong but plausible student error pathways for this math question.

Question: {question}
Correct answer: {correct_answer}

For each distractor return JSON fields:
- text: the bare wrong answer only
- target_misconception: a short name for the error
- error_rationale: one short sentence
- faulty_step: the exact student mistake
- reasoning_steps: a short ordered list describing how the student reaches the answer

Return exactly 3 JSON objects in an array. Do not use markdown fences. Do not add predicted_answer or student_calculation."""


def get_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        base_url=settings.swissai_base_url,
        api_key=settings.swissai_api_key,
        max_retries=0,
    )


def load_questions(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def answer_text(question: dict[str, Any]) -> str:
    letter = question.get("CorrectAnswer", "")
    return str(question.get(f"Answer{letter}Text", "") or "").strip()


def answer_format_text(text: str) -> str:
    text = normalize_expression(text)
    if not text:
        return "unknown"
    if re.fullmatch(r"[\d\s+\-*/().,×÷·^]+", text):
        return "numeric"
    if "=" in text:
        return "equation"
    return "other"


def answer_format(question: dict[str, Any]) -> str:
    return answer_format_text(answer_text(question))


def contains_image_placeholder(question: dict[str, Any]) -> bool:
    fields = [question.get("QuestionText", "")]
    fields.extend(question.get(f"Answer{letter}Text", "") for letter in "ABCD")
    return any("![" in str(field) for field in fields)


def is_viable(question: dict[str, Any]) -> bool:
    option_texts = [str(question.get(f"Answer{letter}Text", "") or "").strip() for letter in "ABCD"]
    return (
        bool(str(question.get("QuestionText", "")).strip())
        and bool(answer_text(question))
        and not contains_image_placeholder(question)
        and len(option_texts) == 4
        and all(option_texts)
        and answer_format(question) in ALLOWED_FORMATS
    )


def select_questions(
    questions: list[dict[str, Any]],
    sample_size: int = SAMPLE_SIZE,
    seed: int = RANDOM_SEED,
) -> list[dict[str, Any]]:
    viable = [question for question in questions if is_viable(question)]
    if sample_size > len(viable):
        raise ValueError(f"Requested {sample_size} questions, but only {len(viable)} are viable.")
    sample = random.Random(seed).sample(viable, sample_size)
    return sorted(sample, key=lambda question: question["QuestionId"])


def display_text(value: Any, limit: int | None = None) -> str:
    text = normalize_expression(" ".join(str(value or "").split()))
    text = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", text)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    return text[:limit] if limit else text


def question_table(questions: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "QuestionId": question["QuestionId"],
                "Subject": question["SubjectName"],
                "AnswerFormat": answer_format(question),
                "Question": display_text(question["QuestionText"], limit=180),
                "CorrectAnswer": display_text(answer_text(question)),
            }
            for question in questions
        ]
    )


def build_prompt(question: dict[str, Any], structured_paths: bool = False) -> str:
    template = STRUCTURED_USER_TEMPLATE if structured_paths else BASIC_USER_TEMPLATE
    return template.format(
        question=" ".join(question["QuestionText"].split()),
        correct_answer=answer_text(question),
    )


def parse_distractors(raw_text: str) -> list[dict[str, Any]]:
    cleaned = (raw_text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("No JSON array found in model output.")

    json_text = cleaned[start : end + 1]
    # Protect LaTeX commands such as \frac or \times from being read as valid
    # JSON escapes (\f = form feed, \t = tab), which would corrupt the text.
    # Only a single backslash needs protection; an already-escaped \\frac is valid.
    json_text = re.sub(r"(?<!\\)\\(?=[a-zA-Z][a-zA-Z])", r"\\\\", json_text)
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", json_text)
        parsed = json.loads(repaired)

    if isinstance(parsed, dict):
        parsed = parsed.get("distractors", parsed.get("items", []))
    if not isinstance(parsed, list):
        raise ValueError("Model output is not a list.")
    return [item if isinstance(item, dict) else {"text": str(item)} for item in parsed[:3]]


def _response_record(
    question: dict[str, Any],
    response: Any,
    started: float,
    budget: int,
) -> dict[str, Any]:
    message = response.choices[0].message
    raw_output = message.content or ""
    return {
        "question_id": question["QuestionId"],
        "subject": question["SubjectName"],
        "question_text": question["QuestionText"],
        "correct_answer": answer_text(question),
        "raw_output": raw_output,
        "finish_reason": response.choices[0].finish_reason,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "completion_budget": budget,
        "reasoning_chars": len(getattr(message, "reasoning_content", "") or ""),
        "completion_tokens": getattr(response.usage, "completion_tokens", None),
    }


def _failure_record(
    question: dict[str, Any],
    note: str,
    elapsed: float | None = None,
    attempts: int = 0,
) -> dict[str, Any]:
    return {
        "question_id": question["QuestionId"],
        "subject": question["SubjectName"],
        "question_text": question["QuestionText"],
        "correct_answer": answer_text(question),
        "raw_output": "",
        "finish_reason": "failed",
        "elapsed_seconds": round(elapsed, 2) if elapsed is not None else None,
        "completion_budget": None,
        "reasoning_chars": 0,
        "completion_tokens": None,
        "attempts": attempts,
        "distractors": [],
        "parse_error": note,
    }


def generate_distractors(
    question: dict[str, Any],
    client: OpenAI | None = None,
    model: str = MODEL,
    max_tokens: int = MAX_TOKENS,
    retry_max_tokens: int = RETRY_MAX_TOKENS,
    timeout: float = GENERATION_TIMEOUT_S,
    structured_paths: bool = False,
) -> dict[str, Any]:
    client = client or get_client()
    last_record: dict[str, Any] | None = None
    attempts = 0
    total_elapsed = 0.0

    for budget in dict.fromkeys((max_tokens, retry_max_tokens)):
        started = time.perf_counter()
        attempts += 1
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": BASIC_SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(question, structured_paths)},
                ],
                temperature=TEMPERATURE,
                max_tokens=budget,
                timeout=timeout,
                extra_body={"thinking": {"type": "enabled"}},
            )
        except Exception as error:
            total_elapsed += time.perf_counter() - started
            last_record = _failure_record(
                question,
                f"{type(error).__name__}: {str(error)[:200]}",
                total_elapsed,
                attempts=attempts,
            )
            continue

        attempt_elapsed = time.perf_counter() - started
        total_elapsed += attempt_elapsed
        record = _response_record(question, response, started, budget)
        record["structured_paths"] = structured_paths
        record["attempts"] = attempts
        record["total_elapsed_seconds"] = round(total_elapsed, 2)
        try:
            record["distractors"] = parse_distractors(record["raw_output"])
            record["parse_error"] = ""
        except Exception as error:
            record["distractors"] = []
            record["parse_error"] = f"{type(error).__name__}: {error}"

        last_record = record
        complete = len(record["distractors"]) == 3 and not record["parse_error"]
        if complete and record["finish_reason"] != "length":
            return record

    if last_record is not None:
        return last_record
    return _failure_record(question, "No response returned.", attempts=attempts)


def run_pilot(
    questions: list[dict[str, Any]],
    output_path: Path = RESULTS_PATH,
    client: OpenAI | None = None,
    workers: int = WORKERS,
    structured_paths: bool = False,
) -> list[dict[str, Any]]:
    client = client or get_client()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                generate_distractors, question, client, structured_paths=structured_paths
            ): question
            for question in questions
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            question = futures[future]
            try:
                record = future.result()
            except Exception as error:
                record = _failure_record(
                    question,
                    f"{type(error).__name__}: {str(error)[:200]}",
                )
            records.append(record)
            print(
                f"[{completed}/{len(questions)}] Q{question['QuestionId']} "
                f"{record.get('finish_reason', 'unknown')}, "
                f"{record.get('elapsed_seconds', '?')}s",
                flush=True,
            )

    records.sort(key=lambda record: record["question_id"])
    output_path.write_text(json.dumps(records, indent=2))
    print("Saved:", output_path)
    return records


def load_records(path: Path = RESULTS_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def is_method_question(question_text: str) -> bool:
    question_lower = question_text.lower()
    markers = (
        "which one of the following calculations",
        "which calculation",
        "which expression",
        "which one of the following expressions",
    )
    return any(marker in question_lower for marker in markers)


def evaluate_numeric_ast(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Expression):
        return evaluate_numeric_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate_numeric_ast(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = evaluate_numeric_ast(node.left)
        right = evaluate_numeric_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div) and right != 0:
            return left / right
        if isinstance(node.op, ast.Pow) and right.denominator == 1 and abs(right.numerator) <= 20:
            return left**right.numerator
    raise ValueError("Unsupported numeric expression")


def parse_numeric_expression(text: str) -> Fraction | None:
    normalized = normalize_expression(text)
    if not normalized or not re.search(r"\d", normalized):
        return None
    if not re.fullmatch(r"[0-9\s+\-*/().,×÷·^]+", normalized):
        return None
    expression = normalized.replace("×", "*").replace("·", "*").replace("÷", "/")
    expression = expression.replace("^", "**").replace(",", "")
    mixed_parenthesized = re.fullmatch(r"(\d+)\s+\((\d+)\)/\((\d+)\)", expression)
    if mixed_parenthesized:
        expression = f"{mixed_parenthesized.group(1)}+({mixed_parenthesized.group(2)}/{mixed_parenthesized.group(3)})"
    mixed_number = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", expression)
    if mixed_number:
        expression = f"{mixed_number.group(1)}+({mixed_number.group(2)}/{mixed_number.group(3)})"
    expression = re.sub(r"(?<=\d)\s*(?=\()", "*", expression)
    if "=" in expression:
        return None
    try:
        return evaluate_numeric_ast(ast.parse(expression, mode="eval"))
    except Exception:
        return None


def canonical_answer_key(text: str) -> str:
    """Canonicalize simple equations without changing expression answers."""
    normalized = normalize_expression(text)
    if normalized.count("=") == 1:
        left, right = normalized.split("=", 1)
        return "=".join(sorted((left, right)))
    return normalized


def duplicate_key(text: str) -> str:
    normalized = normalize_expression(text)
    numeric = parse_numeric_expression(normalized)
    if numeric is not None:
        return f"numeric:{numeric.numerator}/{numeric.denominator}"
    return canonical_answer_key(normalized)


def simple_equation_key(text: str) -> tuple[str, str] | None:
    normalized = normalize_expression(text)
    if normalized.count("=") != 1:
        return None
    left, right = normalized.split("=", 1)
    if not re.fullmatch(r"[A-Za-z]+", left) or not re.fullmatch(r"-?\d+(?:\.\d+)?", right):
        return None
    return left, right


def classify_correctness(
    candidate_text: str,
    correct_text: str,
    question_text: str,
) -> tuple[str, str]:
    candidate = normalize_expression(str(candidate_text or ""))
    correct = normalize_expression(str(correct_text or ""))
    if not candidate:
        return "unusable", "empty answer"
    if canonical_answer_key(candidate) == canonical_answer_key(correct):
        return "correct", "normalized exact match"

    correct_kind = answer_format_text(correct)
    if correct_kind == "numeric":
        candidate_value = parse_numeric_expression(candidate)
        correct_value = parse_numeric_expression(correct)
        if candidate_value is None or correct_value is None:
            return "unknown", "numeric equivalence is not supported for this expression"
        if is_method_question(question_text):
            if candidate_value == correct_value:
                return "unknown", "same value, but expression equivalence is unverified"
            return "incorrect", "different numeric value for a method question"
        if candidate_value == correct_value:
            return "correct", "numeric equivalence"
        return "incorrect", "different numeric value"

    if correct_kind == "equation":
        if candidate.count("=") != 1:
            return "unknown", "candidate is not a simple equation answer"
        candidate_key = simple_equation_key(candidate)
        correct_key = simple_equation_key(correct)
        if candidate_key is None:
            return "unknown", "symbolic equation equivalence is unverified"
        if correct_key is not None and candidate_key[0] == correct_key[0]:
            return "incorrect", "same variable, different constant"
        if correct_key is not None:
            return "incorrect", "different variable in simple equation"
        return "unknown", "symbolic equation equivalence is unverified"

    return "unknown", "answer format is outside the pilot checker"


def evaluate_derivation(
    distractor: dict[str, Any],
    correct_text: str,
    question_text: str,
) -> tuple[str, str]:
    """Check whether a structured student calculation produces its answer."""
    text = str(distractor.get("text", "") or "")
    predicted = str(distractor.get("predicted_answer", "") or "")
    calculation = str(distractor.get("student_calculation", "") or "")
    if not predicted or not calculation:
        return "unknown", "missing predicted_answer or student_calculation"

    correct_kind = answer_format_text(correct_text)
    if canonical_answer_key(predicted) != canonical_answer_key(text):
        predicted_value = parse_numeric_expression(predicted)
        text_value = parse_numeric_expression(text)
        if predicted_value is None or text_value is None or predicted_value != text_value:
            return "fail", "predicted_answer does not match text"

    if correct_kind != "numeric":
        return "unknown", "calculation execution is only supported for numeric answers"

    calculation_value = parse_numeric_expression(calculation)
    predicted_value = parse_numeric_expression(predicted)
    if calculation_value is None or predicted_value is None:
        return "unknown", "calculation or predicted answer is not a supported numeric expression"
    if calculation_value != predicted_value:
        return "fail", "student_calculation does not produce predicted_answer"
    return "pass", "student_calculation produces predicted_answer"


def evaluate_records(
    records: list[dict[str, Any]],
    include_derivation: bool = DERIVATION_ENABLED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for record in records:
        seen_keys: dict[str, int] = {}
        for index, distractor in enumerate(record.get("distractors", []), start=1):
            status, reason = classify_correctness(
                distractor.get("text", ""),
                record.get("correct_answer", ""),
                record.get("question_text", ""),
            )
            normalized_key = duplicate_key(distractor.get("text", ""))
            duplicate_of = seen_keys.get(normalized_key) if normalized_key else None
            if normalized_key and duplicate_of is None:
                seen_keys[normalized_key] = index
            row = {
                "question_id": record["question_id"],
                "subject": record["subject"],
                "distractor_index": index,
                "text": display_text(distractor.get("text", "")),
                "status": status,
                "reason": reason,
                "duplicate": duplicate_of is not None,
                "duplicate_of": duplicate_of,
                "target_misconception": distractor.get("target_misconception", ""),
            }
            if include_derivation:
                derivation_status, derivation_reason = evaluate_derivation(
                    distractor,
                    record.get("correct_answer", ""),
                    record.get("question_text", ""),
                )
                row["derivation_status"] = derivation_status
                row["derivation_reason"] = derivation_reason
            rows.append(row)

    evaluation = pd.DataFrame(rows)
    usable = evaluation[evaluation["status"] != "unusable"] if not evaluation.empty else evaluation
    decisive = usable[usable["status"].isin(("correct", "incorrect"))]
    complete_sets = sum(
        len(record.get("distractors", [])) == 3 and not record.get("parse_error")
        for record in records
    )
    summary_data = {
        "questions_generated": len(records),
        "complete_3_distractor_sets": complete_sets,
        "completeness_rate": round(complete_sets / len(records), 3) if records else None,
        "distractors_parsed": len(evaluation),
        "expected_distractors": len(records) * 3,
        "usable_distractors": len(usable),
        "decisive_distractors": len(decisive),
        "incorrect_distractors": int((decisive["status"] == "incorrect").sum())
        if not decisive.empty
        else 0,
        "accidentally_correct": int((decisive["status"] == "correct").sum())
        if not decisive.empty
        else 0,
        "unknown_equivalence": int((usable["status"] == "unknown").sum())
        if not usable.empty
        else 0,
        "unusable": int((evaluation["status"] == "unusable").sum()) if not evaluation.empty else 0,
        "incorrectness_rate": round(float((decisive["status"] == "incorrect").mean()), 3)
        if not decisive.empty
        else None,
        "accidental_correct_rate": round(float((decisive["status"] == "correct").mean()), 3)
        if not decisive.empty
        else None,
        "unknown_rate": round(float((usable["status"] == "unknown").mean()), 3)
        if not usable.empty
        else None,
        "duplicate_distractors": int(evaluation["duplicate"].sum()) if not evaluation.empty else 0,
    }
    if include_derivation:
        derivation_decisive = (
            evaluation[evaluation["derivation_status"].isin(("pass", "fail"))]
            if not evaluation.empty
            else evaluation
        )
        summary_data.update(
            {
                "derivation_pass": int((derivation_decisive["derivation_status"] == "pass").sum())
                if not derivation_decisive.empty
                else 0,
                "derivation_fail": int((derivation_decisive["derivation_status"] == "fail").sum())
                if not derivation_decisive.empty
                else 0,
                "derivation_unknown": int((evaluation["derivation_status"] == "unknown").sum())
                if not evaluation.empty
                else 0,
                "derivation_fidelity_rate": round(
                    float((derivation_decisive["derivation_status"] == "pass").mean()), 3
                )
                if not derivation_decisive.empty
                else None,
            }
        )
    summary = pd.DataFrame([summary_data])
    return evaluation, summary


def get_judge_client() -> OpenAI:
    base_url, api_key, _ = load_azure_config()
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        max_retries=0,
    )


def get_judge_model() -> str:
    """Return the configured Azure GPT-4.1-mini deployment name."""
    _, _, models = load_azure_config()
    return models["gpt41mini"]


def _json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in judge output")
    json_text = cleaned[start : end + 1]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        repaired = re.sub(r"\\(?![\"\\/bfnrtu])", r"\\\\", json_text)
        return json.loads(repaired)


def _cache_key(prompt: str, model: str) -> str:
    payload = json.dumps({"model": model, "prompt": prompt}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def cached_judge_json(
    prompt: str,
    client: OpenAI | None = None,
    model: str | None = None,
    timeout: float = JUDGE_TIMEOUT_S,
    max_tokens: int = JUDGE_MAX_TOKENS,
) -> tuple[dict[str, Any], bool]:
    model = model or get_judge_model()
    key = _cache_key(prompt, model)
    with _JUDGE_CACHE_LOCK:
        cache = json.loads(JUDGE_CACHE_PATH.read_text()) if JUDGE_CACHE_PATH.exists() else {}
        if key in cache:
            return cache[key], True

    client = client or get_judge_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    result = _json_object(response.choices[0].message.content or "")
    with _JUDGE_CACHE_LOCK:
        cache = json.loads(JUDGE_CACHE_PATH.read_text()) if JUDGE_CACHE_PATH.exists() else {}
        cache[key] = result
        JUDGE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        JUDGE_CACHE_PATH.write_text(json.dumps(cache, indent=2))
    return result, False


def plausibility_prompt(record: dict[str, Any], distractor: dict[str, Any]) -> str:
    return f"""You are rating the plausibility of one math distractor using a compact student-selection rubric.
This is a model-based proxy, not a human annotation. Judge whether a middle-school student with insufficient math knowledge might select the distractor.
Do not judge path coherence, and do not reward an answer merely because it is mathematically wrong.
Return JSON only: {{"score": 0, "reason": "..."}}
Score 0 = unlikely: random, irrelevant, impossible, or too obviously wrong.
Score 1 = possible but weak, ambiguous, or not especially tempting.
Score 2 = likely: a recognizable error that could realistically attract the target students.
Random numerical guesses with no recognizable connection to the question should receive 0.

Question: {record["question_text"]}
Correct answer: {record["correct_answer"]}
Distractor: {distractor.get("text", "")}

How likely is a middle-school student to select this distractor?"""


def evaluate_plausibility(
    records: list[dict[str, Any]],
    repeats: int = JUDGE_REPEATS,
    client: OpenAI | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tasks = [
        (record, index, distractor, repeat)
        for record in records
        for index, distractor in enumerate(record.get("distractors", []), start=1)
        for repeat in range(repeats)
    ]

    def run_one(task: tuple[dict[str, Any], int, dict[str, Any], int]) -> dict[str, Any]:
        record, index, distractor, repeat = task
        try:
            result, cache_hit = cached_judge_json(plausibility_prompt(record, distractor), client)
            score = int(result.get("score", -1))
            if score not in (0, 1, 2):
                raise ValueError("score must be 0, 1, or 2")
            return {
                "question_id": record["question_id"],
                "distractor_index": index,
                "repeat": repeat,
                "score": score,
                "reason": str(result.get("reason", "")),
                "cache_hit": cache_hit,
            }
        except Exception as error:
            return {
                "question_id": record["question_id"],
                "distractor_index": index,
                "repeat": repeat,
                "score": None,
                "reason": f"{type(error).__name__}: {error}",
                "cache_hit": False,
            }

    with ThreadPoolExecutor(max_workers=min(WORKERS, max(1, len(tasks)))) as pool:
        rows = list(pool.map(run_one, tasks))
    raw = pd.DataFrame(rows)
    if raw.empty:
        return raw, pd.DataFrame()
    judged = raw.dropna(subset=["score"])
    summary_rows = []
    for (question_id, index), group in judged.groupby(["question_id", "distractor_index"]):
        score = int(round(float(np.median(group["score"].astype(int).tolist()))))
        summary_rows.append(
            {
                "question_id": question_id,
                "distractor_index": index,
                "plausibility_score": score,
                "plausible": score >= 1,
                "judge_calls": len(group),
                "cache_hits": int(group["cache_hit"].sum()),
            }
        )
    return raw, pd.DataFrame(summary_rows)


def coherence_prompt(record: dict[str, Any], distractor: dict[str, Any]) -> str:
    steps = distractor.get("reasoning_steps", [])
    if isinstance(steps, str):
        steps = [steps]
    numbered_steps = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return f"""You are verifying whether the listed student-error steps reach the stated distractor.
Execute the steps without correcting them, then compare the final result with the distractor.
Return JSON only: {{"final_from_steps": "...", "matches_text": true, "reason": "..."}}

Question: {record["question_text"]}
Distractor text: {distractor.get("text", "")}
Faulty step: {distractor.get("faulty_step", "")}
Reasoning steps:
{numbered_steps}

Ignore whether the student's method is mathematically correct.
Determine the exact final expression or value produced by the listed steps and put it in final_from_steps.
Compare final_from_steps with the distractor text. Set matches_text=true only when they are the same answer, allowing harmless formatting differences.
Wrong operation order is allowed and expected; do not judge whether the path is mathematically correct or psychologically plausible.
Set matches_text=false when the steps end at a different expression or value. Set it to null only when the information is genuinely insufficient."""


def evaluate_coherence(
    records: list[dict[str, Any]],
    client: OpenAI | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for record in records:
        for index, distractor in enumerate(record.get("distractors", []), start=1):
            steps = distractor.get("reasoning_steps")
            if not steps:
                rows.append(
                    {
                        "question_id": record["question_id"],
                        "distractor_index": index,
                        "coherent": None,
                        "status": "unknown",
                        "reason": "missing reasoning_steps",
                        "cache_hit": False,
                    }
                )
                continue
            try:
                result, cache_hit = cached_judge_json(coherence_prompt(record, distractor), client)
                coherent = result.get("matches_text", result.get("coherent"))
                if coherent not in (True, False, None):
                    raise ValueError("matches_text must be true, false, or null")
                rows.append(
                    {
                        "question_id": record["question_id"],
                        "distractor_index": index,
                        "coherent": coherent,
                        "final_from_steps": result.get("final_from_steps"),
                        "status": "pass"
                        if coherent is True
                        else "fail"
                        if coherent is False
                        else "unknown",
                        "reason": str(result.get("reason", "")),
                        "cache_hit": cache_hit,
                    }
                )
            except Exception as error:
                rows.append(
                    {
                        "question_id": record["question_id"],
                        "distractor_index": index,
                        "coherent": None,
                        "status": "unknown",
                        "reason": f"{type(error).__name__}: {error}",
                        "cache_hit": False,
                    }
                )
    details = pd.DataFrame(rows)
    decisive = details[details["status"].isin(("pass", "fail"))] if not details.empty else details
    summary = pd.DataFrame(
        [
            {
                "distractors_seen": len(details),
                "coherence_pass": int((decisive["status"] == "pass").sum())
                if not decisive.empty
                else 0,
                "coherence_fail": int((decisive["status"] == "fail").sum())
                if not decisive.empty
                else 0,
                "coherence_unknown": int((details["status"] == "unknown").sum())
                if not details.empty
                else 0,
                "coherence_rate": float((decisive["status"] == "pass").mean())
                if not decisive.empty
                else None,
            }
        ]
    )
    return details, summary


def _pathway_text(label: str, distractor: dict[str, Any]) -> str:
    steps = distractor.get("reasoning_steps", [])
    if isinstance(steps, str):
        steps = [steps]
    numbered_steps = (
        "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
        or "(not provided)"
    )
    return f"""{label} final answer: {distractor.get("text", "")}
{label} faulty step: {distractor.get("faulty_step", "(not provided)")}
{label} reasoning steps:
{numbered_steps}
{label} claimed label: {distractor.get("target_misconception", "")}
{label} rationale: {distractor.get("error_rationale", "")}"""


def _same_error_prompt(record: dict[str, Any], left: dict[str, Any], right: dict[str, Any]) -> str:
    return f"""You are an independent math teacher comparing two structured student error pathways.
Return JSON only: {{"same_error": true, "shared_faulty_step": "...", "reason": "..."}}
Two pathways have the same error type iff they arise from the same underlying faulty step relative
to the correct solution. Compare the faulty steps and reasoning steps first. Use the claimed labels
and rationales only as supporting context; different wording is not evidence of different errors.

Question: {record["question_text"]}
Correct answer: {record["correct_answer"]}

{_pathway_text("A", left)}

{_pathway_text("B", right)}

Are A and B the same underlying error type?"""


def evaluate_diversity(
    records: list[dict[str, Any]],
    plausibility: pd.DataFrame | None,
    repeats: int = JUDGE_REPEATS,
    client: OpenAI | None = None,
    use_derivation: bool = DERIVATION_ENABLED,
    coherence: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if plausibility is None or plausibility.empty:
        result = pd.DataFrame(
            [
                {
                    "question_id": record["question_id"],
                    "diversity": None,
                    "valid_distractors": 0,
                    "reason": "plausibility not measured",
                }
                for record in records
            ]
        )
        return result, pd.DataFrame([{"questions_measured": 0, "mean_diversity": None}])
    correctness, _ = evaluate_records(records)
    derivation = {}
    if use_derivation:
        derivation = {
            (record["question_id"], index): evaluate_derivation(
                distractor, record["correct_answer"], record["question_text"]
            )[0]
            for record in records
            for index, distractor in enumerate(record.get("distractors", []), start=1)
        }
    valid: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        for index, distractor in enumerate(record.get("distractors", []), start=1):
            row = correctness[
                (correctness["question_id"] == record["question_id"])
                & (correctness["distractor_index"] == index)
            ]
            p = plausibility[
                (plausibility["question_id"] == record["question_id"])
                & (plausibility["distractor_index"] == index)
            ]
            derivation_ok = (
                not use_derivation or derivation.get((record["question_id"], index)) == "pass"
            )
            coherence_ok = (
                coherence is None
                or not coherence.empty
                and not coherence[
                    (coherence["question_id"] == record["question_id"])
                    & (coherence["distractor_index"] == index)
                ].empty
                and coherence[
                    (coherence["question_id"] == record["question_id"])
                    & (coherence["distractor_index"] == index)
                ].iloc[0]["status"]
                == "pass"
            )
            if (
                not row.empty
                and row.iloc[0]["status"] == "incorrect"
                and not p.empty
                and bool(p.iloc[0]["plausible"])
                and derivation_ok
                and coherence_ok
            ):
                valid.setdefault(record["question_id"], []).append(distractor)

    rows = []
    for record in records:
        options = valid.get(record["question_id"], [])
        if len(options) < 2:
            rows.append(
                {
                    "question_id": record["question_id"],
                    "diversity": None,
                    "valid_distractors": len(options),
                    "reason": "fewer than two valid distractors",
                }
            )
            continue
        edges = []
        for left_index, right_index in itertools.combinations(range(len(options)), 2):
            decisions = []
            for _ in range(repeats):
                try:
                    result, _ = cached_judge_json(
                        _same_error_prompt(record, options[left_index], options[right_index]),
                        client,
                    )
                    decisions.append(bool(result["same_error"]))
                except Exception:
                    pass
            if decisions:
                edges.append((left_index, right_index, sum(decisions) > len(decisions) / 2))
        parent = list(range(len(options)))

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        for left, right, same in edges:
            if same:
                left_root, right_root = find(left), find(right)
                if left_root != right_root:
                    parent[right_root] = left_root
        classes = len({find(index) for index in range(len(options))})
        rows.append(
            {
                "question_id": record["question_id"],
                "diversity": (classes - 1) / (len(options) - 1),
                "valid_distractors": len(options),
                "error_classes": classes,
                "reason": "pairwise faulty-step judgments",
            }
        )
    result = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "questions_measured": int(result["diversity"].notna().sum())
                if not result.empty
                else 0,
                "mean_diversity": float(result["diversity"].mean())
                if not result.empty and result["diversity"].notna().any()
                else None,
            }
        ]
    )
    return result, summary


def _maximum_matches(generated: list[str], human: list[str], matcher: Any) -> list[tuple[int, int]]:
    best: list[tuple[int, int]] = []
    for permutation in itertools.permutations(range(len(human)), min(len(generated), len(human))):
        pairs = [
            (index, human_index)
            for index, human_index in enumerate(permutation)
            if matcher(generated[index], human[human_index])
        ]
        if len(pairs) > len(best):
            best = pairs
    return best


def _maximum_matrix_matches(matrix: list[list[bool | None]]) -> list[tuple[int, int]]:
    generated_count = len(matrix)
    human_count = len(matrix[0]) if matrix else 0
    match_count = min(generated_count, human_count)
    best: list[tuple[int, int]] = []
    for generated_indices in itertools.combinations(range(generated_count), match_count):
        for human_indices in itertools.permutations(range(human_count), match_count):
            pairs = [
                (generated_index, human_index)
                for generated_index, human_index in zip(generated_indices, human_indices)
                if matrix[generated_index][human_index] is True
            ]
            if len(pairs) > len(best):
                best = pairs
    return best


def _pm_llm_prompt(
    question_text: str,
    correct_answer: str,
    generated_text: str,
    human_text: str,
) -> str:
    return f"""You are verifying whether two candidate answer texts express the same mathematical
answer to the same question.
Return JSON only: {{"same_answer": true, "reason": "..."}}

Compare the GENERATED ANSWER directly with the HUMAN ANSWER. Do not compare either candidate with
the correct answer: the correct answer is context only and both candidates are expected to be
wrong distractors. For example, if the correct answer is 75 and both candidates are 1, return
same_answer=true because the two candidates express the same answer. If one candidate is 1 and the
other is -1, return same_answer=false even though neither is correct.

Judge answer equivalence only. Do not judge whether either candidate is correct, plausible, or based
on the same misconception, and do not reward similar wording. First interpret each candidate in the
context of the question, then compare:

1. numerical or symbolic value;
2. units and dimensions;
3. the order of values when they correspond to named groups;
4. the requested answer form, such as x = 5 versus 5;
5. whether rounding or approximation is explicitly allowed.

Treat equivalent values, expressions, fractions, decimals, units, and harmless formatting as the
same only when the question context supports that interpretation. For example, 1/2 and 0.5,
2 x 3 x 4 and 24, and x = 5 and 5 (when the question asks for x) are equivalent. Do not treat
10 cm and 10 cm^2 as equivalent, or 60 euros for club A and 180 euros for club B as equivalent to
the reversed assignment. Treat a rounded decimal as equivalent to an exact fraction only when the
question or answer explicitly permits approximation. Return same_answer=null only when the question
or answer texts do not contain enough information to decide; do not guess.

Question: {question_text}
Correct answer (context only; do not compare candidates against it): {correct_answer}
GENERATED ANSWER: <{generated_text}>
HUMAN ANSWER: <{human_text}>

"""


def _llm_answer_match(
    prompt: str,
    client: OpenAI,
    repeats: int,
    model: str | None = None,
) -> tuple[bool | None, str, int, int]:
    decisions: list[bool] = []
    reasons: list[str] = []
    cache_hits = 0
    for _ in range(max(1, repeats)):
        result, cache_hit = cached_judge_json(prompt, client=client, model=model)
        cache_hits += int(cache_hit)
        decision = result.get("same_answer")
        if decision not in (True, False, None):
            raise ValueError("same_answer must be true, false, or null")
        if decision is not None:
            decisions.append(decision)
        if result.get("reason"):
            reasons.append(str(result["reason"]))
    if not decisions:
        return (
            None,
            reasons[-1] if reasons else "judge returned no decisive answer",
            len(decisions),
            cache_hits,
        )
    true_count = sum(decisions)
    false_count = len(decisions) - true_count
    if true_count == false_count:
        return None, reasons[-1] if reasons else "judge decisions tied", len(decisions), cache_hits
    return true_count > false_count, reasons[-1] if reasons else "", len(decisions), cache_hits


def compute_pm(
    record: dict[str, Any],
    question: dict[str, Any],
    *,
    llm_verify: bool = False,
    judge_client: OpenAI | None = None,
    judge_repeats: int = 1,
    judge_model: str | None = None,
) -> dict[str, Any]:
    generated = [str(item.get("text", "")) for item in record.get("distractors", [])]
    human = [
        str(question.get(f"Answer{letter}Text", ""))
        for letter in "ABCD"
        if letter != question.get("CorrectAnswer")
    ]

    def normalized(text):
        return normalize_expression(text)

    def numeric(text):
        return parse_numeric_expression(text)

    tiers = {
        "raw": lambda left, right: left.strip() == right.strip(),
        "normalized": lambda left, right: normalized(left) == normalized(right),
        "typed": lambda left, right: (
            (
                numeric(left) is not None
                and numeric(right) is not None
                and numeric(left) == numeric(right)
            )
            or canonical_answer_key(left) == canonical_answer_key(right)
        ),
    }
    result: dict[str, Any] = {
        "question_id": record["question_id"],
        "generated_count": len(generated),
        "human_count": len(human),
    }
    for name, matcher in tiers.items():
        pairs = _maximum_matches(generated, human, matcher)
        result[f"pm_{name}"] = len(pairs) / len(generated) if generated else None
        result[f"matches_{name}"] = pairs
    if llm_verify:
        client = judge_client or get_judge_client()
        matrix: list[list[bool | None]] = []
        llm_pairs: list[dict[str, Any]] = []
        for generated_index, generated_text in enumerate(generated):
            row: list[bool | None] = []
            for human_index, human_text in enumerate(human):
                prompt = _pm_llm_prompt(
                    record.get("question_text", ""),
                    str(record.get("correct_answer", "")),
                    generated_text,
                    human_text,
                )
                try:
                    decision, reason, decisive_calls, cache_hits = _llm_answer_match(
                        prompt,
                        client,
                        judge_repeats,
                        judge_model,
                    )
                except Exception as error:
                    decision, reason, decisive_calls, cache_hits = (
                        None,
                        f"{type(error).__name__}: {error}",
                        0,
                        0,
                    )
                row.append(decision)
                llm_pairs.append(
                    {
                        "generated_index": generated_index,
                        "human_index": human_index,
                        "same_answer": decision,
                        "reason": reason,
                        "decisive_calls": decisive_calls,
                        "cache_hits": cache_hits,
                    }
                )
            matrix.append(row)
        pairs = _maximum_matrix_matches(matrix)
        result["pm_llm"] = len(pairs) / len(generated) if generated else None
        result["matches_llm"] = pairs
        result["llm_unknown_pairs"] = sum(item["same_answer"] is None for item in llm_pairs)
        result["llm_pairs"] = llm_pairs
    return result


def evaluate_pm(
    records: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    *,
    llm_verify: bool = False,
    judge_client: OpenAI | None = None,
    judge_repeats: int = 1,
    judge_model: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    references = {question["QuestionId"]: question for question in questions}
    rows = [
        compute_pm(
            record,
            references[record["question_id"]],
            llm_verify=llm_verify,
            judge_client=judge_client,
            judge_repeats=judge_repeats,
            judge_model=judge_model,
        )
        for record in records
        if record["question_id"] in references
    ]
    details = pd.DataFrame(rows)
    if details.empty:
        return details, pd.DataFrame()
    measured = details[details["generated_count"] > 0]
    summary_data = {
        "questions_seen": len(details),
        "questions_measured": len(measured),
        "pm_raw": float(measured["pm_raw"].mean()) if not measured.empty else None,
        "pm_normalized": float(measured["pm_normalized"].mean()) if not measured.empty else None,
        "pm_typed": float(measured["pm_typed"].mean()) if not measured.empty else None,
    }
    if llm_verify:
        summary_data["pm_llm"] = float(measured["pm_llm"].mean()) if not measured.empty else None
        summary_data["llm_unknown_pairs"] = int(details["llm_unknown_pairs"].sum())
    summary = pd.DataFrame([summary_data])
    return details, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", action="store_true", help="Call GLM instead of loading saved results."
    )
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--timeout", type=float, default=GENERATION_TIMEOUT_S)
    parser.add_argument("--structured-paths", action="store_true")
    args = parser.parse_args()

    questions = select_questions(load_questions(), sample_size=args.sample_size, seed=args.seed)
    if args.run:
        records = run_pilot(questions, workers=args.workers, structured_paths=args.structured_paths)
    else:
        records = load_records()
    _, summary = evaluate_records(records)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
