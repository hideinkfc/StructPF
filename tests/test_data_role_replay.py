import json
from types import SimpleNamespace

import pytest

from scripts import replay_pf_data_roles as replay
from tests.test_design_data import loop_inputs, proposal_payload, writer_payload


def inputs(tmp_path, monkeypatch):
    case, winner, context = loop_inputs()
    source_dir = tmp_path / "sources"
    source = source_dir / "example" / "result.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "case_id": "example",
                "case_input": case,
                "prior_context": context,
                "model": "test",
                "stages": {"D2_D3": {"winner": winner.to_dict(), "task": writer_payload()}},
            }
        )
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "source_directory": "sources",
                "model_selector": "luna",
                "protocol": {"calibration_cases": ["example"], "evidence_kind": "test"},
                "cases": [
                    {
                        "id": "example",
                        "expected_given": "Journey records",
                        "expected_teacher_example": "None",
                        "expected_student_job": "Compare journeys",
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(replay, "ROOT", tmp_path)
    monkeypatch.setattr(replay, "source_hashes", lambda path: {"config": path.read_text()})
    return config_path, source


def test_predictions_are_persisted_before_calls_and_sources_are_frozen(tmp_path, monkeypatch):
    config, source = inputs(tmp_path, monkeypatch)
    output = tmp_path / "output"
    manifest = replay.prepare(config, output)
    assert json.loads((output / "manifest.json").read_text()) == manifest
    assert manifest["config"]["cases"][0]["expected_given"] == "Journey records"
    assert replay.prepare(config, output) == manifest
    source.write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        replay.prepare(config, output)


@pytest.mark.parametrize("accepted", [True, False])
def test_live_replay_traces_calls_and_preserves_failures(tmp_path, monkeypatch, accepted):
    config, source = inputs(tmp_path, monkeypatch)
    original = source.read_bytes()
    responses = iter(
        [proposal_payload(), {**writer_payload(), "body": "2, 2, 2 km; 20, 20, 40 min."}]
        if accepted
        else [{}, {}, {}]
    )
    monkeypatch.setattr(
        replay.diagnostic,
        "chat_json",
        lambda *args, **kwargs: (next(responses), "raw"),
    )
    options = []
    monkeypatch.setattr(
        replay,
        "load_client",
        lambda _: (SimpleNamespace(with_options=lambda **kwargs: options.append(kwargs)), "test"),
    )
    output = tmp_path / "output"
    result = replay.run(config, output, ["example"])
    record = json.loads((output / "example" / "result.json").read_text())
    assert record["status"] == ("ready" if accepted else "data_invalid")
    assert record["model_calls"] == (2 if accepted else 3)
    assert record["trace_summary"]["started"] == record["model_calls"]
    assert record["source_integrity_verified"] and record["source_artifact_unchanged"]
    assert source.read_bytes() == original
    assert options == [{"max_retries": 0}]
    assert result["source_integrity_unchanged"]
    replay.render(output)
    assert "Not fresh end-to-end" in (output / "tasks.html").read_text()
    with pytest.raises(ValueError, match="Refusing to replace"):
        replay.run(config, output, ["example"])


def test_api_error_is_persisted_and_propagated(tmp_path, monkeypatch):
    config, _ = inputs(tmp_path, monkeypatch)

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic API failure")

    monkeypatch.setattr(replay.diagnostic, "chat_json", fail)
    output = tmp_path / "output"
    manifest = replay.prepare(config, output)
    with pytest.raises(RuntimeError, match="Synthetic API failure"):
        replay.replay_case("example", output, manifest, client=None, model="test")
    record = json.loads((output / "example" / "result.json").read_text())
    assert record["status"] == "error" and record["model_calls"] == 1
    assert record["trace_summary"]["errors"] == 1
    assert record["source_artifact_unchanged"]
