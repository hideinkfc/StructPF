import json
from unittest.mock import Mock

import pytest

from scripts.learning_commons_guided_search import (
    load_targets,
    prompt_query_jobs,
    run_queries,
    save_run,
)


def _targets():
    return [
        {
            "id": "spread",
            "learning_target": "Measure consistency or spread",
            "context": "Grade 10, NRW, mathematics",
        },
        {
            "id": "fair-division",
            "learning_target": "Resolve a fair-division standoff",
            "context": "Undergraduate, USA, mathematics",
        },
    ]


def test_load_targets_reads_the_three_expert_tasks(tmp_path):
    path = tmp_path / "selection.json"
    path.write_text(json.dumps({"targets": _targets()}), encoding="utf-8")

    assert load_targets(path) == _targets()


def test_load_targets_rejects_incomplete_target(tmp_path):
    path = tmp_path / "selection.json"
    path.write_text(json.dumps({"targets": [{"id": "missing-context"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="learning_target, and context"):
        load_targets(path)


def test_prompt_query_jobs_collects_known_and_custom_tasks():
    answers = iter(
        [
            "1",
            "data spread around the mean",
            "10",
            "",
            "c",
            "A new task",
            "Grade 8, mathematics",
            "",
            "compare ratios in tables",
            "8",
            "Multi-State",
            "",
        ]
    )
    jobs = prompt_query_jobs(_targets(), input_fn=lambda _: next(answers), output_fn=lambda _: None)

    assert jobs == [
        {
            "target_id": "spread",
            "target_name": "Measure consistency or spread",
            "context": "Grade 10, NRW, mathematics",
            "query": "data spread around the mean",
            "grade_levels": ["10"],
            "academic_subject": "Mathematics",
            "jurisdiction": None,
        },
        {
            "target_id": "custom",
            "target_name": "A new task",
            "context": "Grade 8, mathematics",
            "query": "compare ratios in tables",
            "grade_levels": ["8"],
            "academic_subject": "Mathematics",
            "jurisdiction": "Multi-State",
        },
    ]


def test_run_queries_passes_filters_and_preserves_responses():
    response = [{"statementCode": "6.RP.A.2", "score": 0.7}]
    client = Mock()
    client.search_standards.return_value = response
    jobs = [
        {
            "target_id": "speed",
            "target_name": "Average speed",
            "context": "Grade 7",
            "query": "total distance divided by total time",
            "grade_levels": ["7"],
            "academic_subject": "Mathematics",
            "jurisdiction": None,
        }
    ]

    results = run_queries(client, jobs, limit=10)

    client.search_standards.assert_called_once_with(
        query="total distance divided by total time",
        grade_levels=["7"],
        academic_subject="Mathematics",
        jurisdiction=None,
        limit=10,
    )
    assert results == [{**jobs[0], "results": response}]


def test_save_run_refuses_to_overwrite_existing_results(tmp_path):
    output = tmp_path / "results.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        save_run({"queries": []}, output)


def test_save_run_writes_json(tmp_path):
    output = tmp_path / "nested" / "results.json"
    record = {"queries": [{"query": "spread", "results": []}]}

    save_run(record, output)

    assert json.loads(output.read_text(encoding="utf-8")) == record
