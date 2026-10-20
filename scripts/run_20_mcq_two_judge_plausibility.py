"""Generate 20 new MCQs and compare Apertus/GLM plausibility judgments."""

from __future__ import annotations

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compare_saved_pilot_plausibility_judges import (  # noqa: E402
    JUDGES,
    compare_judges,
    run_judges,
    summarize,
)
from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    RESULTS_PATH,
    WORKERS,
    evaluate_records,
    generate_distractors,
    get_client,
    get_judge_client,
    is_viable,
    load_questions,
)

OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_20_two_judge_plausibility.json"
SAMPLE_SIZE = 20
SAMPLE_SEED = 2026

EXPECTATIONS = {
    "sampling": "Use 20 viable numeric/equation questions not present in the saved 10-question pilot.",
    "generation": "Most questions should produce complete three-distractor basic-format outputs, but generation failures remain possible.",
    "judges": "Both judges should return valid compact 0-2 scores for most parsed distractors.",
    "comparison": "Do not assume Apertus or GLM is better; report score distributions and agreement descriptively.",
    "bias": "GLM is also the generator, so a higher GLM score may reflect self-evaluation bias rather than better plausibility judgment.",
    "evidence_limit": "LLM scores are exploratory proxies and do not establish real-student plausibility.",
}


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def write_payload(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(jsonable(payload), indent=2))


def main() -> None:
    saved_records = json.loads(RESULTS_PATH.read_text())
    old_ids = {record["question_id"] for record in saved_records}
    questions = [question for question in load_questions() if is_viable(question) and question["QuestionId"] not in old_ids]
    selected = sorted(random.Random(SAMPLE_SEED).sample(questions, SAMPLE_SIZE), key=lambda question: question["QuestionId"])
    question_ids = [question["QuestionId"] for question in selected]

    payload: dict[str, Any] = {
        "status": "running",
        "expectations": EXPECTATIONS,
        "sampling": {
            "source": str(RESULTS_PATH.relative_to(PROJECT_ROOT)),
            "seed": SAMPLE_SEED,
            "sample_size": SAMPLE_SIZE,
            "viable_nonoverlap_pool": len(questions),
            "question_ids": question_ids,
            "output_format": "basic",
        },
        "judges": JUDGES,
    }
    write_payload(payload)

    generator_client = get_client()
    with ThreadPoolExecutor(max_workers=min(WORKERS, len(selected))) as pool:
        futures = [pool.submit(generate_distractors, question, generator_client, structured_paths=False) for question in selected]
        generated_records = [future.result() for future in futures]
    generated_records.sort(key=lambda record: record["question_id"])

    judge_rows = run_judges(generated_records, client=get_judge_client())
    judge_summaries = {judge_name: summarize(judge_rows, judge_name) for judge_name in JUDGES}
    _, correctness = evaluate_records(generated_records)
    correctness_summary = correctness.iloc[0].to_dict() if not correctness.empty else {}

    payload.update(
        {
            "status": "complete",
            "generated_records": generated_records,
            "generation_summary": {
                "questions_generated": len(generated_records),
                "complete_three_distractor_sets": sum(len(record.get("distractors", [])) == 3 and not record.get("parse_error") for record in generated_records),
                "parse_failures": sum(bool(record.get("parse_error")) for record in generated_records),
                "distractors_parsed": sum(len(record.get("distractors", [])) for record in generated_records),
            },
            "correctness_summary": correctness_summary,
            "plausibility_judgments": judge_rows,
            "plausibility_summaries": judge_summaries,
            "judge_comparison": compare_judges(judge_rows),
        }
    )
    write_payload(payload)

    print(f"Saved: {OUTPUT_PATH}")
    print("question_ids", question_ids)
    print("generation", payload["generation_summary"])
    for judge_name in JUDGES:
        print(judge_name, judge_summaries[judge_name])
    print("comparison", payload["judge_comparison"])


if __name__ == "__main__":
    main()
