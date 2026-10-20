"""Recover failed generations and judge outputs for the 20-question MCQ run."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compare_saved_pilot_plausibility_judges import (  # noqa: E402
    JUDGES,
    compare_judges,
    run_judges,
    summarize,
)
from scripts.run_basic_glm_correctness_pilot import (  # noqa: E402
    evaluate_records,
    generate_distractors,
    get_client,
    get_judge_client,
    load_questions,
)

OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "phase1_mcq" / "mcq_20_two_judge_plausibility.json"
RECOVERY_TIMEOUT = 180.0
RECOVERY_WORKERS = 1


def main() -> None:
    payload = json.loads(OUTPUT_PATH.read_text())
    question_map = {question["QuestionId"]: question for question in load_questions()}
    records = payload["generated_records"]
    failed = [record for record in records if record.get("parse_error") or len(record.get("distractors", [])) != 3]
    print("failed generations before recovery:", [record["question_id"] for record in failed])

    generator_client = get_client()
    with ThreadPoolExecutor(max_workers=min(RECOVERY_WORKERS, max(1, len(failed)))) as pool:
        futures = [
            pool.submit(generate_distractors, question_map[record["question_id"]], generator_client, timeout=RECOVERY_TIMEOUT, structured_paths=False)
            for record in failed
        ]
        recovered = [future.result() for future in futures]
    recovered_by_id = {record["question_id"]: record for record in recovered}
    merged_records = [recovered_by_id.get(record["question_id"], record) for record in records]
    merged_records.sort(key=lambda record: record["question_id"])

    judge_rows = run_judges(merged_records, client=get_judge_client())
    judge_summaries = {judge_name: summarize(judge_rows, judge_name) for judge_name in JUDGES}
    _, correctness = evaluate_records(merged_records)
    correctness_summary = correctness.iloc[0].to_dict() if not correctness.empty else {}
    payload.update(
        {
            "status": "complete",
            "recovery": {
                "attempted_question_ids": [record["question_id"] for record in failed],
                "timeout_seconds": RECOVERY_TIMEOUT,
                "workers": RECOVERY_WORKERS,
                "remaining_failed_question_ids": [record["question_id"] for record in merged_records if record.get("parse_error") or len(record.get("distractors", [])) != 3],
            },
            "generated_records": merged_records,
            "generation_summary": {
                "questions_generated": len(merged_records),
                "complete_three_distractor_sets": sum(len(record.get("distractors", [])) == 3 and not record.get("parse_error") for record in merged_records),
                "parse_failures": sum(bool(record.get("parse_error")) for record in merged_records),
                "distractors_parsed": sum(len(record.get("distractors", [])) for record in merged_records),
            },
            "correctness_summary": correctness_summary,
            "plausibility_judgments": judge_rows,
            "plausibility_summaries": judge_summaries,
            "judge_comparison": compare_judges(judge_rows),
        }
    )
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print("generation:", payload["generation_summary"])
    print("recovery:", payload["recovery"])
    for judge_name in JUDGES:
        print(judge_name, judge_summaries[judge_name])
    print("comparison", payload["judge_comparison"])


if __name__ == "__main__":
    main()
