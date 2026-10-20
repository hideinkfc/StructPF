import json
from types import SimpleNamespace

import pytest

from scripts import replay_pf_discovery_writer as replay_stage
from scripts.replay_pf_discovery_writer import numeric_coverage


def task(body, withheld=None, status="ready"):
    return {
        "status": status,
        "title": "Records",
        "body": body,
        "question": "Explain.",
        "withheld": [] if withheld is None else withheld,
    }


def test_numeric_coverage_counts_repetitions_zero_and_negative_values():
    proposal = {"values": {"times": [0, -2, 2, 2]}}
    assert numeric_coverage(task("0, -2, 2, 2"), proposal)["status"] == "covered"
    result = numeric_coverage(task("0, -2, 2"), proposal)
    assert result["status"] == "missing_numerals" and result["missing"] == {"2": 1}


def test_numeric_coverage_excludes_only_whole_withheld_quantities():
    proposal = {"values": {"raw": [12, 12, 12], "answer": [4, 4, 4]}}
    withheld = [{"kind": "quantity", "source": "proposal.quantities.answer.description"}]
    result = numeric_coverage(task("12, 12, 12", withheld), proposal)
    assert result["status"] == "covered"
    assert result["withheld_quantities"] == ["answer"]
    assert result["retained_quantities"] == ["raw"]
    withheld[0]["kind"] = "discovery"
    assert numeric_coverage(task("12, 12, 12", withheld), proposal)["missing"] == {"4": 3}


def test_numeric_coverage_does_not_score_blocked_outputs():
    assert numeric_coverage(task("", status="blocked"), {})["status"] == "unavailable"


def test_numeric_coverage_excludes_explicit_teacher_examples_without_writer_omissions():
    proposal = {
        "quantities": {"raw": {"role": "given"}, "example": {"role": "teacher_example"}},
        "values": {"raw": [12], "example": [[2, 3], [4, 6]]},
    }
    result = numeric_coverage(task("12"), proposal, raw_quantities=["raw"])
    assert result["status"] == "covered"
    assert result["withheld_quantities"] == ["example"]
    assert result["quantity_selection_matches_expected"] is True


def test_external_raw_expectations_catch_incorrect_withholding():
    proposal = {"values": {"raw": [12, 12, 12], "answer": [4, 4, 4]}}
    withheld = [
        {"kind": "quantity", "source": f"proposal.quantities.{name}.description"}
        for name in proposal["values"]
    ]
    result = numeric_coverage(task("", withheld), proposal, raw_quantities=["raw"])
    assert result["status"] == "missing_numerals"
    assert result["missing"] == {"12": 3}
    assert result["quantity_selection_matches_expected"] is False


def test_external_expectations_flag_relabelled_teacher_results():
    proposal = {"values": {"raw": [12], "answer": [4]}}
    result = numeric_coverage(task("12, 4"), proposal, raw_quantities=["raw"])
    assert result["status"] == "quantity_selection_mismatch"
    assert result["quantity_selection_matches_expected"] is False


def test_replay_preserves_frozen_inputs_and_refuses_overwrite(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    saved = {
        "case": "example",
        "case_input": {"id": "example", "grade": 7},
        "prior_context": {"case_id": "example"},
        "model": "test",
        "task": task("12"),
        "design_data": {"accepted": True, "payload": {"values": {"raw": [12]}}},
    }
    original = json.dumps(saved)
    source.write_text(original)
    monkeypatch.setattr(replay_stage, "ROOT", tmp_path)
    monkeypatch.setattr(
        replay_stage.runner,
        "_winner_from_result",
        lambda *args: SimpleNamespace(to_dict=lambda: {"frozen": True}),
    )
    monkeypatch.setattr(
        replay_stage.stage, "_writer_request", lambda *args: {"system": "test", "user": "test"}
    )
    calls = []

    def write(client, model, case, winner, data, context):
        assert case == saved["case_input"] and context == saved["prior_context"]
        assert data == saved["design_data"]
        calls.append(model)
        return task("12"), "raw"

    monkeypatch.setattr(replay_stage.stage, "write_design_data_task", write)
    output_dir = tmp_path / "outputs"
    result = replay_stage.replay(source, output_dir, model="test", raw_quantities=["raw"])
    assert result["source_artifact_unchanged"] and result["source_integrity_verified"]
    assert result["numeric_coverage"]["status"] == "covered"
    assert source.read_text() == original and calls == ["test"]
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        replay_stage.replay(source, output_dir, model="test", raw_quantities=["raw"])
    assert calls == ["test"]


def test_replay_does_not_write_unaccepted_data(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "case": "example",
                "case_input": {"id": "example"},
                "prior_context": {},
                "design_data": {"accepted": False},
            }
        )
    )
    monkeypatch.setattr(replay_stage, "ROOT", tmp_path)
    monkeypatch.setattr(
        replay_stage.stage,
        "write_design_data_task",
        lambda *args: pytest.fail("Writer must not repair D2b or write unaccepted data"),
    )
    result = replay_stage.replay(source, tmp_path / "outputs")
    assert result["status"] == "unavailable" and result["model_calls"] == 0
