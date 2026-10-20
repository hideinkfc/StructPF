"""Offline unit tests for the 20-case 2-arm Progression Bridge runner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.build_progression_bridge_dataset import load_progression_bridge_dataset
from scripts.run_pf_diagnostic import _frozen_grounding_records
from scripts.run_progression_bridge_study import (
    build_generation_case_input,
    build_lc_grounding_records,
    build_official_learner_context,
    evaluate_gate1_prior_set,
    evaluate_two_gate_arm,
    extract_d1_resources,
    extract_student_task,
    run_direct_case_worker,
    score_blinded_pair,
    score_bridge_fit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_grounding_records_adapt_to_d1_evidence_contract() -> None:
    dataset = load_progression_bridge_dataset()
    for case in dataset["cases"]:
        inp = build_generation_case_input(case)
        assert inp["exclude_resource_terms"] == []
        assert inp["teacher_skills"] == []
        recs = build_lc_grounding_records(case)
        assert len(recs) >= 2
        adapted = _frozen_grounding_records(recs)
        assert adapted is not None
        assert len(adapted) == len(recs)
        ctx = build_official_learner_context(case)
        assert len(ctx["assumed_prior_knowledge"]) >= 2


def test_extract_d1_and_student_task_from_real_saved_result() -> None:
    sample_path = (
        ROOT
        / "experiments/results/pf_pipeline_lc_impasse_v3_20261015"
        / "generation/kapur_average_speed/001/result.json"
    )
    saved = json.loads(sample_path.read_text(encoding="utf-8"))
    d1 = extract_d1_resources(saved)
    task = extract_student_task(saved)
    assert len(d1) >= 1
    assert "speed" in task.lower() or "route" in task.lower()


def test_bridge_fit_and_pairwise_judge_parsing() -> None:
    case = load_progression_bridge_dataset()["cases"][0]
    fake_bridge = {
        "score": 2,
        "d1_target_leak": False,
        "d3_target_leak": False,
        "activates_s_prior": True,
        "s_prior_hits_bridge_impasse": True,
        "d1_quote": "like denominators",
        "task_quote": "equal strips",
        "rationale": "Exact bridge.",
    }
    with patch(
        "scripts.run_progression_bridge_study.chat_json",
        return_value=(fake_bridge, json.dumps(fake_bridge)),
    ):
        res = score_bridge_fit(None, "luna", case, [{"resource": "like fractions"}], "Task text")
        assert res["score"] == 2
        assert res["activates_s_prior"] is True

    calls = [
        ({"winner": "option_2", "rationale": "Option 2 is grounded."}, "{}"),
        ({"winner": "option_1", "rationale": "Option 1 in swapped order is grounded."}, "{}"),
    ]
    with patch("scripts.run_progression_bridge_study.chat_json", side_effect=calls):
        pair = score_blinded_pair(
            None,
            "luna",
            case,
            {"d1_prior_resources": [], "d3_student_task": "A"},
            {"d1_prior_resources": [], "d3_student_task": "B"},
        )
        assert pair["consensus_winner"] == "lc_grounded"


def test_direct_worker_and_two_gate_evaluator(tmp_path: Path) -> None:
    case = load_progression_bridge_dataset()["cases"][0]
    inp = build_generation_case_input(case)
    fake_direct = {
        "status": "ready",
        "proposed_prior_knowledge": [
            {
                "resource": "Adding fractions with like denominators",
                "taught_as": "Combine numerators over a shared denominator",
                "student_move": "Try adding the given strips directly",
            },
            {
                "resource": "Equivalent fractions by visual splitting",
                "taught_as": "Split each part into equal smaller pieces",
                "student_move": "Subdivide strips to compare lengths",
            },
        ],
        "title": "Trail Mix Strips",
        "body": "Group A has 1/2 meter and 1/3 meter strips.",
        "question": "How can they combine and compare the total lengths?",
    }
    with (
        patch("scripts.run_progression_bridge_study.load_client", return_value=(None, "luna")),
        patch(
            "scripts.run_progression_bridge_study.chat_json",
            return_value=(fake_direct, json.dumps(fake_direct)),
        ),
    ):
        res = run_direct_case_worker(inp, tmp_path / "direct_case", "luna")
        assert res["status"] == "completed"
        k_prior = extract_d1_resources(res)
        task = extract_student_task(res)
        assert len(k_prior) == 2
        assert "Trail Mix" in task

    fake_gate1 = {
        "items": [
            {
                "index": 0,
                "resource": "Adding fractions with like denominators",
                "classification": "valid",
                "has_left_to_right_arrow": True,
                "helpful_to_start_task": True,
                "is_spoiler": False,
                "reason": "4.NF.B.3 builds towards 5.NF.A.1.",
            },
            {
                "index": 1,
                "resource": "Equivalent fractions by visual splitting",
                "classification": "valid",
                "has_left_to_right_arrow": True,
                "helpful_to_start_task": True,
                "is_spoiler": False,
                "reason": "4.NF.A.1 builds towards 5.NF.A.1.",
            },
        ],
        "combination_is_spoiler": False,
        "set_summary": "Both skills are valid left-to-right prerequisites.",
    }
    fake_solver = {
        "skill_attempts": [
            {
                "resource": "Adding fractions with like denominators",
                "calculation": "1/2 and 1/3 have different denominators (2 != 3)",
                "result_or_winner": "Cannot add numerators directly",
                "hits_limitation_on_task": True,
                "limitation_description": "Unequal unit sizes prevent direct addition.",
            }
        ],
        "combined_attempt_summary": "Students must subdivide units to find a shared partition.",
        "solves_task_without_new_concept": False,
    }
    fake_gate2 = {
        "gate2_score": 2,
        "outcome": "productive_trap",
        "any_k_valid_bypasses_trap": False,
        "task_text_leaks_target": False,
        "hits_productive_trap_toward_target": True,
        "rationale": "Like-denominator addition hits unequal unit sizes.",
    }
    with patch(
        "scripts.run_progression_bridge_study.chat_json",
        side_effect=[
            (fake_gate1, "{}"),
            (fake_solver, "{}"),
            (fake_gate2, "{}"),
        ],
    ):
        two_gate = evaluate_two_gate_arm(None, "luna", case, k_prior, task)
        assert two_gate["score"] == 2
        assert two_gate["gate1"]["gate1_passed"] is True
        assert two_gate["gate1"]["valid_ratio"] == 1.0
        assert two_gate["gate2"]["outcome"] == "productive_trap"

    # Also verify Score 0 when any k_i is a spoiler
    fake_gate1_spoiler = {
        "items": [
            {
                "index": 0,
                "resource": "Common denominator formula",
                "classification": "spoiler",
                "has_left_to_right_arrow": False,
                "helpful_to_start_task": True,
                "is_spoiler": True,
                "reason": "Already is the 5.NF.A.1 target procedure.",
            }
        ],
        "combination_is_spoiler": True,
        "set_summary": "Leaks target concept.",
    }
    with patch(
        "scripts.run_progression_bridge_study.chat_json",
        return_value=(fake_gate1_spoiler, "{}"),
    ):
        g1 = evaluate_gate1_prior_set(None, "luna", case, k_prior[:1], task)
        assert g1["gate1_passed"] is False
        assert g1["any_spoiler"] is True

