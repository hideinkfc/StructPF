from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import scripts.replay_pf_writer as replay
import scripts.run_pf_diagnostic as diagnostic

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "experiments"
    / "results"
    / "validation"
    / "20260922_joint_repair_other3_v1"
    / "kapur_average_speed_g7_singapore"
)


def _copy_source(tmp_path: Path) -> Path:
    destination = tmp_path / "source"
    shutil.copytree(SOURCE, destination)
    return destination


def _run_prepare(source: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        replay,
        "load_client",
        lambda _: pytest.fail("prepare mode must not load a model client"),
    )
    assert (
        replay.main(
            [
                "--sources",
                str(source),
                "--output",
                str(output),
                "--model",
                "luna",
                "--prepare-only",
            ]
        )
        == 0
    )


def test_prepare_only_persists_request_without_upstream_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_source(tmp_path)
    output = tmp_path / "prepared"
    source_hashes = replay._artifact_hashes(source)

    _run_prepare(source, output, monkeypatch)

    result = json.loads((output / "kapur_average_speed_g7_singapore" / "result.json").read_text())
    assert result["status"] == "planned"
    assert result["new_trace_counts"]["finished"] == 0
    assert result["previous_task"] == result["before_after"]["before_task"]
    assert result["task"] == result["before_after"]["after_task"]
    assert set(result["length_comparison"]) == {"previous_task", "task", "delta"}
    assert (
        result["length_comparison"]["delta"]["characters"]
        == result["length_comparison"]["task"]["characters"]
        - result["length_comparison"]["previous_task"]["characters"]
    )
    assert (
        result["new_writer_context"]["student_context"]
        == result["original_writer_context"]["student_context"]
    )
    assert result["source_provenance"]["source_artifact_sha256_before"] == source_hashes
    assert result["source_provenance"]["source_artifact_sha256_after"] == source_hashes
    assert not (output / "kapur_average_speed_g7_singapore" / "model_calls.jsonl").exists()
    assert (output / "kapur_average_speed_g7_singapore" / "before_after.json").is_file()


def test_dry_run_alias_does_not_call_writer_or_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_source(tmp_path)
    output = tmp_path / "dry"
    monkeypatch.setattr(
        replay,
        "load_client",
        lambda _: pytest.fail("dry-run must not load a model client"),
    )
    monkeypatch.setattr(
        replay.runner,
        "_write_task",
        lambda *args, **kwargs: pytest.fail("dry-run must not call production writer"),
    )

    assert replay.main(["--sources", str(source), "--output", str(output), "--dry-run"]) == 0
    assert json.loads((output / "manifest.json").read_text())["status"] == "planned"


def test_rejects_invalid_source_and_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_source(tmp_path)
    result_path = source / "result.json"
    result = json.loads(result_path.read_text())
    result["stages"]["D2_D3"]["task"]["status"] = "blocked"
    result_path.write_text(json.dumps(result))

    with pytest.raises(ValueError, match="task is not ready"):
        replay.main(
            [
                "--sources",
                str(source),
                "--output",
                str(tmp_path / "invalid-output"),
                "--prepare-only",
            ]
        )

    valid_source = _copy_source(tmp_path / "second")
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        replay.main(
            [
                "--sources",
                str(valid_source),
                "--output",
                str(output),
                "--prepare-only",
            ]
        )


def test_rejects_missing_saved_input_or_writer_trace(tmp_path: Path) -> None:
    missing_input = _copy_source(tmp_path / "input-case")
    (missing_input / "input.json").unlink()
    with pytest.raises(ValueError, match="missing artifacts"):
        replay.main(
            [
                "--sources",
                str(missing_input),
                "--output",
                str(tmp_path / "missing-input-output"),
                "--prepare-only",
            ]
        )

    missing_trace = _copy_source(tmp_path / "trace-case")
    (missing_trace / "model_calls.jsonl").unlink()
    with pytest.raises(ValueError, match="missing artifacts"):
        replay.main(
            [
                "--sources",
                str(missing_trace),
                "--output",
                str(tmp_path / "missing-trace-output"),
                "--prepare-only",
            ]
        )


def test_rejects_duplicate_ids_and_mutated_fixed_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _copy_source(tmp_path)
    with pytest.raises(ValueError, match="Duplicate case IDs"):
        replay.main(
            [
                "--sources",
                str(source),
                str(source),
                "--output",
                str(tmp_path / "duplicates"),
                "--prepare-only",
            ]
        )

    trace = source / "model_calls.jsonl"
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    for record in records:
        if record.get("stage") == replay.WRITER_STAGE:
            record["user_prompt"] = record["user_prompt"].replace(
                '"Average speed as total distance divided by total time; '
                'students have not yet learned the new concept."',
                '"changed fixed concept"',
            )
    trace.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    with pytest.raises(ValueError, match="fixed section target_concept"):
        replay.main(
            [
                "--sources",
                str(source),
                "--output",
                str(tmp_path / "mutated"),
                "--prepare-only",
            ]
        )


def test_blocked_writer_output_is_retained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _copy_source(tmp_path)
    output = tmp_path / "blocked"
    monkeypatch.setattr(replay, "load_client", lambda _: (object(), "gpt-5.6-luna"))
    monkeypatch.setattr(
        diagnostic,
        "chat_json",
        lambda *args, **kwargs: (None, "not json"),
    )

    assert replay.main(["--sources", str(source), "--output", str(output)]) == 0
    result = json.loads((output / "kapur_average_speed_g7_singapore" / "result.json").read_text())
    assert result["status"] == "blocked"
    assert result["task_raw_text"] == "not json"
    assert result["previous_task"] == result["before_after"]["before_task"]
    assert result["task"] == result["before_after"]["after_task"]
    assert result["length_comparison"]["task"] == {
        "characters": 0,
        "words": 0,
    }
    assert result["before_after"]["after_task"]["status"] == "blocked"
    assert result["new_trace_counts"]["finished"] == 1


def test_live_replay_calls_only_writer_and_preserves_fixed_inputs(tmp_path, monkeypatch):
    source = _copy_source(tmp_path)
    output = tmp_path / "ready"
    monkeypatch.setattr(replay, "load_client", lambda _: (object(), "gpt-5.6-luna"))
    payload = {
        "status": "ready",
        "blocking_issues": [],
        "title": "Task",
        "body": "Frozen example data.",
        "question": "Explain your decision.",
    }
    monkeypatch.setattr(
        diagnostic, "chat_json", lambda *args, **kwargs: (payload, json.dumps(payload))
    )
    replay.main(["--sources", str(source), "--output", str(output)])
    result = json.loads((output / SOURCE.name / "result.json").read_text())
    trace = replay._read_trace(output / SOURCE.name / "model_calls.jsonl")
    assert result["task"] == payload
    assert result["new_trace_counts"]["finished"] == 1
    assert {record["stage"] for record in trace} == {"D3.writer"}
    assert (
        result["new_writer_request"]["user_prompt"]
        == (result["planned_writer_request"]["user_prompt"])
    )
    assert (
        result["source_provenance"]["source_artifact_sha256_before"]
        == (result["source_provenance"]["source_artifact_sha256_after"])
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert "scripts/replay_pf_writer.py" in manifest["runtime_source_sha256"]


def test_live_replay_refuses_a_different_model(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "load_client", lambda _: (object(), "other-model"))
    with pytest.raises(ValueError, match="differs from saved writer model"):
        replay.main(["--sources", str(SOURCE), "--output", str(tmp_path / "output")])
