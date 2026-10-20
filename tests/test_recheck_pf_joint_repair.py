"""Tests for scripts/recheck_pf_joint_repair.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import scripts.recheck_pf_joint_repair as recheck_module
import scripts.run_situation_skeletons as d2_runner
from src.generation.situation_skeletons import (
    JudgedCandidate,
    NumberRequirement,
    ProposedApproach,
    Quantity,
    Skeleton,
)


def _make_skeleton(question: str = "Which fraction is larger?") -> Skeleton:
    return Skeleton(
        quantities=[
            Quantity(
                name="c1",
                role="count",
                description="first count",
                value_source="given",
                unit="units",
                list_length=None,
                value_domain="positive",
            )
        ],
        question=question,
        why_methods_start="Fractions start.",
        why_target_needed="Target needed.",
        why_each_resource_can_activate="Resource can activate.",
        why_none_settles_the_question="None settles question.",
        why_the_target_is_needed="Target needed.",
        number_constraints=["Use positive numbers."],
        approaches=[
            ProposedApproach(
                id="app_1",
                resources=["Fractions as parts"],
                procedure="Compare parts directly.",
                why_plausible="Natural idea.",
                anticipated_limitation="Fails without common base.",
            )
        ],
    )


def _make_judged_candidate(
    candidate_id: int = 0, question: str = "Which fraction is larger?"
) -> JudgedCandidate:
    skeleton = _make_skeleton(question)
    req = NumberRequirement(
        condition="Use positive numbers.",
        purpose="Ensure positivity.",
    )
    return JudgedCandidate(
        candidate_id=candidate_id,
        skeleton=skeleton,
        verdicts=(),
        practice_item=False,
        target_named=False,
        activation_count=1,
        number_requirements=(req,),
        selection_reason="Clear comparison.",
        main_concern="None.",
        selection_approaches=("Compare parts directly.",),
    )


def _setup_saved_source_case(
    source_root: Path,
    case_id: str,
    status: str = "completed",
    winner: JudgedCandidate | None = None,
    plan_payload: dict | None = None,
    proposals: list[dict] | None = None,
    topic: str | None = None,
) -> Path:
    case_dir = source_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    if topic is None:
        if "kinematics" in case_id:
            topic = "kinematics"
        elif "fair_division" in case_id:
            topic = "fair division"
        elif "fraction" in case_id:
            topic = "fraction equivalence"
        else:
            topic = case_id
    input_data = {
        "id": case_id,
        "target_concept": f"Concept for {case_id}",
        "topic": topic,
        "grade": 5,
        "subject": "mathematics",
    }
    (case_dir / "input.json").write_text(json.dumps(input_data), encoding="utf-8")
    d1_data = {
        "schema_version": "prior-method-recommendations/v1",
        "records": [
            {
                "case_id": case_id,
                "condition": "grounded",
                "result": {
                    "resource_candidates": [
                        {
                            "resource": "Fractions as parts of a whole",
                            "taught_as": "Parts of whole.",
                            "relevance": "Directly relevant.",
                        }
                    ]
                },
            }
        ],
    }
    (case_dir / "d1.json").write_text(json.dumps(d1_data), encoding="utf-8")

    stage_d2: dict = {
        "status": status,
        "proposals": proposals or [],
        "winners": [winner.to_dict()] if winner else [],
        "winner": winner.to_dict() if winner else None,
        "plan_payload": plan_payload,
    }
    result_data = {
        "schema_version": "pf-diagnostic/v2",
        "case_id": case_id,
        "status": status,
        "error": None,
        "prior_context": {
            "source": "d1_recommendations",
            "recommendations": [
                {
                    "resource": "Fractions as parts of a whole",
                    "taught_as": "Parts of a whole.",
                    "relevance": "Directly relevant.",
                }
            ],
        },
        "stages": {
            "D1": {"status": "completed"},
            "D2_D3": stage_d2,
        },
    }
    (case_dir / "result.json").write_text(json.dumps(result_data), encoding="utf-8")
    return case_dir


def test_find_case_dirs_filters(tmp_path: Path):
    source_root = tmp_path / "source"
    _setup_saved_source_case(source_root, "mazziotti_fraction_g5_nrw")
    _setup_saved_source_case(source_root, "kapur_kinematics_g11_cbse")
    _setup_saved_source_case(source_root, "kerrigan_fair_division_undergrad_usa")

    matched_fractions = recheck_module.find_case_dirs(source_root, ["fractions"])
    assert len(matched_fractions) == 1
    assert matched_fractions[0].name == "mazziotti_fraction_g5_nrw"

    matched_two = recheck_module.find_case_dirs(source_root, ["fractions", "kinematics"])
    assert len(matched_two) == 2
    names = {p.name for p in matched_two}
    assert names == {"mazziotti_fraction_g5_nrw", "kapur_kinematics_g11_cbse"}

    matched_fd = recheck_module.find_case_dirs(source_root, ["fair division"])
    assert len(matched_fd) == 1
    assert matched_fd[0].name == "kerrigan_fair_division_undergrad_usa"


def test_saved_winner_plan_repaired_winner_flows_to_fill_and_task(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "mazziotti_fraction_g5_nrw"
    original_winner = _make_judged_candidate(candidate_id=0, question="Original question")
    repaired_winner = _make_judged_candidate(candidate_id=0, question="Repaired question")

    plan_payload = {"schema_version": "math-plan/v2", "target": {"name": "target"}}
    _setup_saved_source_case(
        source_root,
        case_id,
        winner=original_winner,
        plan_payload=plan_payload,
    )

    mock_plan = MagicMock()
    mock_plan.to_dict.return_value = {"schema_version": "math-plan/v2"}
    mock_client = MagicMock()

    planning_result = {
        "winner": repaired_winner,
        "original_winner": original_winner,
        "plan": mock_plan,
        "plan_payload": plan_payload,
        "plan_raw_text": "{}",
        "plan_review": {
            "status": "pass",
            "distinct_approaches": True,
            "constraints_covered": True,
            "issues": [],
        },
        "plan_review_raw_text": "{}",
        "plan_review_prompts": {},
        "attempts": [{"attempt": 1, "source": "saved_plan", "stage": None}],
        "design_repair_attempts": [{"attempt": 1, "status": "accepted"}],
        "error": None,
    }

    fill_result = {"accepted": True, "payload": {"values": {"c1": 10}}, "attempts": []}
    task_result = {"status": "ready", "title": "PF Task", "body": "...", "question": "?"}

    with (
        patch.object(
            d2_runner, "_plan_until_reviewed", return_value=planning_result
        ) as mock_plan_fn,
        patch.object(d2_runner, "_fill_until_accepted", return_value=fill_result) as mock_fill,
        patch.object(d2_runner, "_write_task", return_value=(task_result, "{}")) as mock_write,
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(mock_client, "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        ret = recheck_module.main(
            [
                "--source-root",
                str(source_root),
                "--output",
                str(output_dir),
                "--cases",
                "fractions",
            ]
        )
        assert ret == 0

    mock_plan_fn.assert_called_once()
    assert mock_plan_fn.call_args.kwargs.get("initial_plan_payload") == plan_payload

    mock_fill.assert_called_once()
    assert mock_fill.call_args.args[4].skeleton.question == "Repaired question"

    mock_write.assert_called_once()
    assert mock_write.call_args.args[4].skeleton.question == "Repaired question"

    case_result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    assert case_result["status"] == "completed"
    stage = case_result["stages"]["D2_D3"]
    assert stage["original_winner"]["skeleton"]["question"] == "Original question"
    assert stage["winners"][0]["skeleton"]["question"] == "Repaired question"
    assert len(stage["design_repair_attempts"]) == 1

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["budgets"]["proposal_retry_max"] == 1
    assert manifest["budgets"]["plan_retry_max"] == 1
    assert manifest["budgets"]["fill_max_tries"] == 3
    assert case_id in manifest["source_result_hashes"]
    assert manifest["source_hashes_before"] == manifest["source_hashes_after"]
    assert manifest["source_integrity_unchanged"] is True
    assert set(manifest["source_artifact_hashes_after"][case_id]) == {
        "input.json",
        "d1.json",
        "result.json",
    }


def test_saved_winner_plan_genuine_stop_blocks_fill_and_writer(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "kapur_kinematics_g11_cbse"
    original_winner = _make_judged_candidate(candidate_id=0, question="Kinematics Winner")

    plan_payload = {"schema_version": "math-plan/v2"}
    _setup_saved_source_case(
        source_root,
        case_id,
        winner=original_winner,
        plan_payload=plan_payload,
    )

    mock_client = MagicMock()
    planning_result = {
        "winner": original_winner,
        "original_winner": original_winner,
        "plan": None,
        "plan_payload": plan_payload,
        "plan_raw_text": "{}",
        "plan_review": {
            "passed": False,
            "status": "revise",
            "issues": ["unresolvable contradiction"],
        },
        "plan_review_raw_text": "{}",
        "plan_review_prompts": {},
        "attempts": [{"attempt": 1, "source": "saved_plan", "stage": "meaning_review"}],
        "design_repair_attempts": [],
        "error": "unresolvable contradiction",
    }

    with (
        patch.object(d2_runner, "_plan_until_reviewed", return_value=planning_result),
        patch.object(d2_runner, "_fill_until_accepted") as mock_fill,
        patch.object(d2_runner, "_write_task") as mock_write,
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(mock_client, "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        ret = recheck_module.main(
            [
                "--source-root",
                str(source_root),
                "--output",
                str(output_dir),
                "--cases",
                "kinematics",
            ]
        )
        assert ret == 0

    mock_fill.assert_not_called()
    mock_write.assert_not_called()

    case_result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    assert case_result["status"] == "review_blocked"
    assert case_result["error"] == "unresolvable contradiction"


def test_no_valid_proposals_repaired_and_empty_labeled(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "kapur_average_speed_g7_singapore"
    saved_proposals = [
        {"raw_text": "broken 1", "skeleton": None},
        {"raw_text": "", "payload": None, "error": "empty proposal response"},
    ]
    _setup_saved_source_case(
        source_root,
        case_id,
        status="no_valid_proposals",
        proposals=saved_proposals,
    )

    valid_skeleton = _make_skeleton("Repaired Proposal")
    repaired_prop_1 = {
        "skeleton_obj": valid_skeleton,
        "skeleton": valid_skeleton.to_dict(),
        "raw_text": '{"valid": true}',
        "attempts": [{"attempt": 2, "raw_text": '{"valid": true}'}],
    }
    repaired_prop_2 = {
        "skeleton_obj": None,
        "skeleton": None,
        "raw_text": "",
        "attempts": [{"attempt": 2, "raw_text": ""}],
    }

    mock_client = MagicMock()
    candidate = _make_judged_candidate(0, "Repaired Proposal")
    judge_payload = {
        "recommended_id": 0,
        "approaches": ["app_1"],
        "reason": "Good.",
        "main_concern": "None.",
        "number_requirements": [{"condition": "x > 0", "purpose": "positivity"}],
    }
    mock_plan = MagicMock()
    mock_plan.to_dict.return_value = {"schema_version": "math-plan/v2"}
    planning_result = {
        "winner": candidate,
        "original_winner": candidate,
        "plan": mock_plan,
        "plan_payload": {"schema_version": "math-plan/v2"},
        "plan_raw_text": "{}",
        "plan_review": {
            "status": "pass",
            "distinct_approaches": True,
            "constraints_covered": True,
            "issues": [],
        },
        "plan_review_raw_text": "{}",
        "plan_review_prompts": {},
        "attempts": [{"attempt": 1, "source": "generated", "stage": None}],
        "design_repair_attempts": [],
        "error": None,
    }
    fill_result = {"accepted": True, "payload": {"values": {}}, "attempts": []}
    task_result = {"status": "ready", "title": "PF Task", "body": "...", "question": "?"}
    proposal_calls: list[dict] = []
    proposal_results = [repaired_prop_1, repaired_prop_2]

    def fake_propose(*_args, **kwargs):
        proposal_calls.append(kwargs)
        return proposal_results.pop(0)

    with (
        patch.object(d2_runner, "_propose_one", side_effect=fake_propose),
        patch.object(d2_runner, "_judge_all", return_value=(judge_payload, "{}")),
        patch.object(d2_runner, "_plan_until_reviewed", return_value=planning_result) as mock_plan,
        patch.object(d2_runner, "_fill_until_accepted", return_value=fill_result),
        patch.object(d2_runner, "_write_task", return_value=(task_result, "{}")),
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(mock_client, "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        ret = recheck_module.main(
            [
                "--source-root",
                str(source_root),
                "--output",
                str(output_dir),
                "--cases",
                case_id,
            ]
        )
        assert ret == 0

    case_result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    assert case_result["status"] == "completed"
    stage = case_result["stages"]["D2_D3"]
    assert stage["mode"] == "no_valid_proposals"
    assert len(stage["proposals"]) == 2
    assert stage["proposals"][1]["empty_response"] is True
    assert all(set(call["initial_proposal"]) == {"payload", "raw_text"} for call in proposal_calls)
    mock_plan.assert_called_once()
    selected = mock_plan.call_args.args[4]
    assert selected.selection_reason == "Good."
    assert selected.selection_approaches == ("app_1",)
    assert selected.number_requirements[0].condition == "x > 0"


def test_saved_modern_selection_null_recommendation_is_no_winner():
    payload = {
        "recommended_id": None,
        "approaches": [],
        "reason": "No candidate is suitable.",
        "main_concern": "All candidates remain incomplete.",
        "number_requirements": [],
    }
    assert recheck_module._select_saved_candidates(payload, [_make_skeleton()], {}) == []


def test_saved_modern_selection_malformed_response_is_explicit():
    with pytest.raises(ValueError, match="recommended_id must be an integer or null"):
        recheck_module._select_saved_candidates(
            {
                "recommended_id": "0",
                "approaches": ["app_1"],
                "reason": "bad id type",
                "main_concern": None,
                "number_requirements": [],
            },
            [_make_skeleton()],
            {},
        )


def test_saved_raw_proposal_is_parsed_and_sent_as_exact_envelope(tmp_path: Path):
    skeleton = _make_skeleton("Raw saved proposal")
    raw = json.dumps(skeleton.to_dict())
    payload, preserved_raw, empty = recheck_module._saved_proposal_input(
        {"raw_text": raw, "error": "saved validation error"}
    )
    assert payload == skeleton.to_dict()
    assert preserved_raw == raw
    assert empty is False


def test_empty_saved_proposal_preserves_empty_raw_and_payload_none():
    payload, raw, empty = recheck_module._saved_proposal_input(
        {"raw_text": "", "error": "unparseable proposal"}
    )
    assert payload is None
    assert raw == ""
    assert empty is True


def test_saved_empty_proposal_payload_none_yields_one_repair_request(monkeypatch):
    case = {"target_concept": "fairness", "topic": "ratios", "grade": 7, "subject": "math"}
    prior_context = {"recommendations": [{"resource": "Fractions as parts"}]}
    saved_prop = {"payload": None, "raw_text": "", "error": "empty proposal response"}

    init_prop, init_raw, empty_saved = recheck_module._saved_proposal_input(saved_prop)
    assert init_prop is None
    assert init_raw == ""
    assert empty_saved is True

    envelope = {"payload": init_prop, "raw_text": init_raw}
    repair_calls = []

    def fake_chat_json(client, model, system_prompt, user_prompt, **kwargs):
        repair_calls.append({"system": system_prompt, "user": user_prompt})
        valid_skel = _make_skeleton("Repaired From Empty")
        return valid_skel.to_dict(), json.dumps(valid_skel.to_dict())

    monkeypatch.setattr(d2_runner, "chat_json", fake_chat_json)

    result = d2_runner._propose_one(
        None,
        "model",
        d2_runner._prompts(),
        case,
        prior_context,
        initial_proposal=envelope,
        initial_proposal_raw=init_raw,
    )

    assert len(repair_calls) == 1
    repair_prompt_text = repair_calls[0]["user"]
    assert '"original_payload": null' in repair_prompt_text
    assert '"original_raw_text": ""' in repair_prompt_text

    attempts = result["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["source"] == "saved_proposal"
    assert attempts[0]["payload"] is None
    assert attempts[0]["raw_text"] == ""

    assert attempts[1]["attempt"] == 2
    assert result["skeleton_obj"] is not None


def test_missing_saved_input_is_recorded_as_failed_case(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "mazziotti_fraction_g5_nrw"
    _setup_saved_source_case(source_root, case_id, winner=_make_judged_candidate())
    (source_root / case_id / "input.json").unlink()

    with (
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(MagicMock(), "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        assert (
            recheck_module.main(["--source-root", str(source_root), "--output", str(output_dir)])
            == 1
        )
    result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert "missing artifacts" in result["error"]


def test_missing_d2_stage_after_output_creation_is_persisted(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "mazziotti_fraction_g5_nrw"
    case_dir = _setup_saved_source_case(
        source_root,
        case_id,
        winner=_make_judged_candidate(),
        plan_payload={"schema_version": "math-plan/v2"},
    )
    source_result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    del source_result["stages"]["D2_D3"]
    (case_dir / "result.json").write_text(json.dumps(source_result), encoding="utf-8")

    with (
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(MagicMock(), "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        assert (
            recheck_module.main(["--source-root", str(source_root), "--output", str(output_dir)])
            == 1
        )

    result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert "missing D2_D3 stage" in result["error"]
    assert "Traceback" in result["traceback"]
    assert manifest["status"] == "failed"
    assert manifest["cases"][0]["status"] == "failed"


def test_trace_summary_failure_after_creation_is_persisted(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "mazziotti_fraction_g5_nrw"
    _setup_saved_source_case(
        source_root,
        case_id,
        winner=_make_judged_candidate(),
        plan_payload={"schema_version": "math-plan/v2"},
    )
    mock_client = MagicMock()

    with (
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(mock_client, "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
        patch.object(
            recheck_module,
            "_run_planning_fill_task",
            return_value=None,
        ),
        patch.object(
            recheck_module,
            "trace_summary",
            side_effect=ValueError("trace pairing failed"),
        ),
    ):
        assert (
            recheck_module.main(["--source-root", str(source_root), "--output", str(output_dir)])
            == 1
        )

    result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert "trace pairing failed" in result["error"]
    assert "Traceback" in result["traceback"]
    assert manifest["status"] == "failed"


def test_malformed_saved_proposal_record_is_rejected():
    with pytest.raises(ValueError, match="proposal record must be an object"):
        recheck_module._saved_proposal_input([])


def test_cli_output_dir_exists_raises(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _setup_saved_source_case(source_root, "mazziotti_fraction_g5_nrw")

    with pytest.raises(FileExistsError, match="Output directory already exists"):
        recheck_module.main(
            [
                "--source-root",
                str(source_root),
                "--output",
                str(output_dir),
            ]
        )


def test_api_exception_surfaces_with_trace_and_failed_status(tmp_path: Path):
    source_root = tmp_path / "source"
    output_dir = tmp_path / "output"
    case_id = "mazziotti_fraction_g5_nrw"
    winner = _make_judged_candidate()
    _setup_saved_source_case(source_root, case_id, winner=winner, plan_payload={"v": 1})

    mock_client = MagicMock()
    with (
        patch.object(
            d2_runner,
            "_plan_until_reviewed",
            side_effect=RuntimeError("API service timeout"),
        ),
        patch(
            "scripts.recheck_pf_joint_repair.load_client",
            return_value=(mock_client, "gpt-5.6-luna"),
        ),
        patch.object(d2_runner, "_prompts", return_value={}),
    ):
        recheck_module.main(
            [
                "--source-root",
                str(source_root),
                "--output",
                str(output_dir),
            ]
        )

    case_result = json.loads((output_dir / case_id / "result.json").read_text(encoding="utf-8"))
    assert case_result["status"] == "failed"
    assert "API service timeout" in case_result["error"]
    assert "RuntimeError" in case_result["traceback"]
