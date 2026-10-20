import json
from copy import deepcopy

import pytest

from scripts import replay_pf_design_data as replay
from tests.test_design_data import loop_inputs, proposal_payload


def save_result(tmp_path, proposal=None, replies=None):
    case, winner, context = loop_inputs()
    source = tmp_path / "result.json"
    proposal = proposal_payload() if proposal is None else proposal
    source.write_text(
        json.dumps(
            {
                "schema_version": "pf-design-data/v1",
                "case": "example",
                "case_input": case,
                "prior_context": context,
                "winner": winner.to_dict(),
                "design_data": {
                    "status": "accepted",
                    "payload": proposal,
                    "attempts": replies
                    if replies is not None
                    else [
                        {
                            "stage": "propose",
                            "payload": proposal,
                            "raw_text": "saved proposal",
                        }
                    ],
                },
                "task": {
                    "status": "ready",
                    "blocking_issues": [],
                    "title": "Task",
                    "body": "Distances are 2, 2, 2 km.",
                    "question": "Explain your comparison.",
                    "withheld": [],
                },
            }
        )
    )
    return source


def test_offline_replay_rechecks_saved_replies_and_repairs_perturbed_values(tmp_path):
    source = save_result(tmp_path)
    original = source.read_bytes()
    report = replay.replay_result(source, stress_dir=tmp_path / "stress")
    assert report["model_calls"] == 0
    assert report["recheck"]["accepted"]
    assert report["recorded_reply_replay"]["accepted"]
    assert report["writer_schema_replay"]["status"] == "ready"
    stress = report["stress"]
    assert stress["run"]["initial_check"]["status"] == "rejected"
    assert stress["run"]["accepted"]
    assert len(stress["run"]["attempts"]) == 1
    assert stress["frozen_conditions_preserved"] and stress["frozen_quantities_preserved"]
    altered = json.loads(replay.Path(stress["input"]).read_text())
    assert altered["input_provenance"] == "controlled_negative_value_perturbation"
    assert source.read_bytes() == original and report["source_unchanged"]


def test_offline_replay_records_missing_replies_instead_of_inventing_them(tmp_path):
    source = save_result(
        tmp_path,
        replies=[
            {
                "stage": "propose",
                "payload": None,
                "raw_text": "bad JSON",
            }
        ],
    )
    report = replay.replay_result(source)
    assert report["recorded_reply_replay"]["status"] == "unavailable"
    assert report["recheck"]["accepted"]


def test_offline_replay_preserves_historical_unlabeled_proposal(tmp_path):
    proposal = proposal_payload()
    for metadata in proposal["quantities"].values():
        del metadata["role"]
    source = save_result(tmp_path, proposal=proposal)
    original = source.read_bytes()
    report = replay.replay_result(source)
    assert report["recorded_reply_replay"]["accepted"]
    assert report["recorded_reply_replay"]["new_proposal_roles_required"] is False
    assert report["writer_schema_replay"]["status"] == "ready"
    assert source.read_bytes() == original


@pytest.mark.parametrize("judgment", ["holds", "uncertain"])
def test_offline_replay_continues_uncomputed_conditions_without_promoting_evidence(
    tmp_path, judgment
):
    proposal = deepcopy(proposal_payload())
    proposal["conditions"][0].update(calculation=None, judgment=judgment)
    source = save_result(tmp_path, proposal=proposal)
    report = replay.replay_result(source)
    assert report["recheck"]["accepted"]
    assert report["recorded_reply_replay"]["accepted"]
    assert bool(report["recheck"]["warnings"]) is (judgment == "uncertain")
    assert report["writer_schema_replay"]["status"] == "ready"
    assert report["source_unchanged"] and report["model_calls"] == 0


def test_offline_replay_keeps_textual_failure_out_of_numerical_repair(tmp_path):
    proposal = deepcopy(proposal_payload())
    proposal["conditions"][0].update(
        calculation=None, judgment="fails", reasoning="Explicit conflicting task rules."
    )
    source = save_result(tmp_path, proposal=proposal)
    report = replay.replay_result(source, stress_dir=tmp_path / "stress")
    assert report["recheck"]["status"] == "review_needed"
    assert report["recorded_reply_replay"]["status"] == "review_needed"
    assert report["recheck"]["textual_failures"]
    assert report["writer_schema_replay"] is None and report["stress"] is None


def test_offline_replay_does_not_overwrite_stress_inputs(tmp_path):
    source = save_result(tmp_path)
    replay.replay_result(source, stress_dir=tmp_path / "stress")
    with pytest.raises(ValueError, match="overwrite"):
        replay.replay_result(source, stress_dir=tmp_path / "stress")
