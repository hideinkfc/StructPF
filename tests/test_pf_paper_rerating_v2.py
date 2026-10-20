import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError

from scripts import rerate_pf_paper_benchmark_v2 as rerate
from src.evaluation.pf_rubric_v2 import DIMENSIONS


def _rating_response(score=2):
    return json.dumps({
        **{
            dimension: {"evidence": "Concrete task evidence.", "score": score}
            for dimension in DIMENSIONS
        },
        "mathematical_concerns": [],
    })


def _make_source_run(root: Path, protocol_path: Path) -> Path:
    protocol = json.loads(protocol_path.read_text())
    protocol["source_run"] = "source"
    protocol["expected_attempts_per_condition"] = 2
    protocol["calibration"]["cases_per_condition"] = 1
    protocol_path.write_text(json.dumps(protocol))
    source = root / "source"
    (source / "attempts").mkdir(parents=True)
    (source / "source_snapshot").mkdir()
    context = {
        "grade": 7,
        "subject": "mathematics",
        "jurisdiction": "USA",
        "assumed_prior_knowledge": [{
            "resource": "Unit rates",
            "taught_as": "Compute rates.",
        }],
    }
    config = {
        "conditions": list(rerate.CONDITIONS),
        "n_per_condition": 2,
        "model_selector": "luna",
        "case": {"target_concept": "Recognize proportional relationships."},
        "learner_context": context,
    }
    (source / "config.json").write_text(json.dumps(config))
    attempts = {}
    order = []
    ready_counts = {}
    for condition in rerate.CONDITIONS:
        ready_counts[condition] = 2 if condition != "PIPELINE" else 1
        for number in range(1, 3):
            attempt_id = f"{condition}-{number:03d}"
            relative = Path("attempts") / condition / f"{number:03d}"
            attempt_dir = source / relative
            attempt_dir.mkdir(parents=True)
            is_ready = number == 1 or condition != "PIPELINE"
            status = "ready" if is_ready else "review_blocked"
            record = {
                "attempt_id": attempt_id,
                "condition": condition,
                "status": status,
                "task": (
                    {
                        "status": "ready",
                        "title": f"Task {number}",
                        "body": "Two basketball groups have these results.",
                        "question": "Compare them.",
                    }
                    if is_ready
                    else {"status": "blocked", "blocking_issues": ["review stopped"]}
                ),
            }
            (attempt_dir / "attempt.json").write_text(json.dumps(record))
            attempts[attempt_id] = {
                "attempt_id": attempt_id,
                "condition": condition,
                "number": number,
                "status": status,
                "path": str(relative),
            }
            order.append(attempt_id)
    manifest = {
        "status": "completed_with_failures",
        "source_integrity_unchanged": True,
        "source_snapshot_dir": "source_snapshot",
        "source_hashes": {},
        "attempts": attempts,
        "judge_order": order,
    }
    (source / "manifest.json").write_text(json.dumps(manifest))
    summary = {
        "conditions": {
            condition: {
                "counts": {"scheduled": 2, "ready": ready_counts[condition]}
            }
            for condition in rerate.CONDITIONS
        }
    }
    (source / "summary.json").write_text(json.dumps(summary))
    return source


def _prepare(tmp_path):
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(Path(rerate.PROTOCOL_PATH).read_text())
    source = _make_source_run(tmp_path, protocol_path)
    output = tmp_path / "rerating"
    manifest = rerate.prepare_run(
        output,
        protocol_path=protocol_path,
        source_run=source,
        root=tmp_path,
    )
    return output, manifest


def _client(response_text=None, error=None):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=response_text or _rating_response()),
                finish_reason="stop",
            )],
            usage={
                "prompt_tokens": 12,
                "completion_tokens": 34,
                "total_tokens": 46,
            },
            model="gpt-5.6-luna-2026-07-09",
        )

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ), calls


def test_prepare_freezes_all_source_cases_and_method_blind_inputs(tmp_path):
    output, manifest = _prepare(tmp_path)
    assert manifest["case_count"] == 8
    assert manifest["eligible_count"] == 7
    assert manifest["ready_counts"] == {
        "V1": 2, "V2": 2, "V3": 2, "PIPELINE": 1,
    }
    inputs = [
        json.loads(line)
        for line in (output / "inputs.jsonl").read_text().splitlines()
    ]
    assert len(inputs) == 8
    assert sum(item["calibration_selected"] for item in inputs) == 4
    for item in inputs:
        if item["eligible"]:
            assert item["user_prompt_sha256"]
            assert "PIPELINE" not in item["user_prompt"]
            assert item["attempt_id"] not in item["user_prompt"]
            payload = json.loads(item["user_prompt"])
            assert payload["learner_context"]["learning_target"] == (
                "Recognize proportional relationships."
            )
            assert payload["learner_context"]["grade"] == 7
        else:
            assert item["source_generation_status"] == "review_blocked"
            assert item["user_prompt"] is None
            rating = json.loads(
                (output / "ratings" / f"{item['attempt_id']}.json").read_text()
            )
            assert rating["status"] == "not_eligible"
    with pytest.raises(FileExistsError):
        rerate.prepare_run(
            output,
            protocol_path=tmp_path / "protocol.json",
            source_run=tmp_path / "source",
            root=tmp_path,
        )


def test_balanced_calibration_then_full_run_resumes_without_duplicate_calls(tmp_path):
    output, manifest = _prepare(tmp_path)
    fake_client, calls = _client()
    def loader(selector):
        return fake_client, "gpt-5.6-luna"

    calibration = rerate.run_calibration(output, client_loader=loader)
    assert calibration["status"] == "passed"
    assert calibration["balanced_case_count"] == 4
    assert calibration["scores_deliberately_omitted"] is True
    assert all("scores" not in item for item in calibration["outcomes"])
    assert len(calls) == 4
    assert {item["condition"] for item in calibration["outcomes"]} == set(
        rerate.CONDITIONS
    )
    for call in calls:
        assert call["response_format"] == {"type": "json_object"}
        assert call["max_completion_tokens"] == 4000
        assert "temperature" not in call
        assert "PIPELINE" not in call["messages"][1]["content"]

    summary = rerate.run_full(output, client_loader=loader)
    assert len(calls) == 7
    assert summary["overall_denominators"] == {
        "scheduled": 8,
        "ready": 7,
        "not_ready": 1,
        "complete_five_dimension_scores": 7,
    }
    assert summary["conditions"]["PIPELINE"]["denominators"]["scheduled"] == 2
    assert summary["conditions"]["PIPELINE"]["denominators"]["ready"] == 1
    assert summary["conditions"]["PIPELINE"]["scores"]["TOTAL"]["mean"] == 10
    assert summary["conditions"]["PIPELINE"]["model_calls"]["usage_tokens_when_returned"][
        "total_tokens"
    ] == 46
    rerun = rerate.run_full(output, client_loader=lambda _: pytest.fail("must not call model"))
    assert len(calls) == 7
    assert rerun["overall_denominators"]["complete_five_dimension_scores"] == 7


def test_transport_and_schema_failures_are_explicit_and_block_full_run(
    tmp_path, monkeypatch
):
    output, _ = _prepare(tmp_path)
    monkeypatch.setattr(rerate.time, "sleep", lambda _: None)
    fake_client, calls = _client(error=APIConnectionError(
        request=httpx.Request("POST", "https://example.invalid")
    ))
    calibration = rerate.run_calibration(
        output, client_loader=lambda selector: (fake_client, "gpt-5.6-luna")
    )
    assert calibration["status"] == "failed"
    assert len(calls) == 3
    results = [
        json.loads((output / "ratings" / f"{case_id}.json").read_text())
        for case_id in json.loads((output / "manifest.json").read_text())[
            "calibration"
        ]["case_ids"]
    ]
    assert results[0]["status"] == "api_error"
    assert all(
        result["status"] == "not_attempted_calibration_blocked"
        for result in results[1:]
    )
    with pytest.raises(RuntimeError, match="calibration passes"):
        rerate.run_full(output)


def test_invalid_json_schema_is_not_repaired_or_scored(tmp_path):
    output, _ = _prepare(tmp_path)
    fake_client, _ = _client(response_text='{"unexpected": true}')
    calibration = rerate.run_calibration(
        output, client_loader=lambda selector: (fake_client, "gpt-5.6-luna")
    )
    assert calibration["status"] == "failed"
    results = [
        json.loads((output / "ratings" / f"{case_id}.json").read_text())
        for case_id in json.loads((output / "manifest.json").read_text())[
            "calibration"
        ]["case_ids"]
    ]
    assert results[0]["status"] == "invalid_response"
    assert all(result["scores"] is None for result in results)
    assert results[0]["raw_response"] == '{"unexpected": true}'
    assert all(
        result["status"] == "not_attempted_calibration_blocked"
        for result in results[1:]
    )
