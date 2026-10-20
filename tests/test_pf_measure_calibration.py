"""Credential-free checks of frozen inputs and provisional reference controls."""

from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction

import pytest

from scripts import build_pf_measure_calibration as calibration


@pytest.fixture(scope="module")
def pack():
    return calibration.build_pack()


@pytest.fixture
def cases(pack):
    return {case["case_id"]: case for case in calibration.all_cases(pack)}


def test_saved_artifact_matches_reproducible_build(pack):
    saved = json.loads((calibration.ROOT / calibration.OUTPUT).read_text(encoding="utf-8"))
    assert saved == pack
    assert calibration.validate_pack(saved)["passed"]


def test_exact_splits_and_origins(pack):
    assert [len(pack[key]) for key in ("development", "transfer", "controls")] == [13, 9, 7]
    development = pack["development"]
    assert sum(case["origin"] == "expert_task" for case in development) == 7
    assert sum(case["origin"] == "saved_generated_task" for case in development) == 5
    assert sum(case["origin"] == "synthetic_contrast" for case in development) == 1
    assert sum(case["origin"] == "expert_task" for case in pack["transfer"]) == 7
    assert sum(case["origin"] == "saved_generated_task" for case in pack["transfer"]) == 2
    assert pack["verification"]["counts"]["constructed_attempts"] == 14


def test_disjoint_ids_families_and_exact_task_texts(pack):
    development = pack["development"]
    transfer = pack["transfer"]
    assert {case["case_id"] for case in development}.isdisjoint(
        {case["case_id"] for case in transfer}
    )
    assert {case["family"] for case in development}.isdisjoint(
        {case["family"] for case in transfer}
    )
    assert {case["student_task_sha256"] for case in development}.isdisjoint(
        {case["student_task_sha256"] for case in transfer}
    )
    by_id = {case["case_id"]: case for case in development}
    assert by_id["synthetic_consistency_formula"]["family"] == by_id["expert_consistency"]["family"]
    assert all(
        "Not an untouched-topic" in case["expert_exposure"]
        for case in development + transfer
        if case["origin"] == "expert_task"
    )


def test_original_expert_student_text_excludes_every_source_solution(pack):
    for case in calibration.all_cases(pack):
        if case["origin"] != "expert_task":
            continue
        task_source = next(source for source in case["sources"] if source["student_fields"])
        original = calibration.exercise(task_source["path"], case["source_exercise_id"])
        assert case["student_task"] == original["problem"]
        assert task_source["student_fields"] == ["problem"]
        for key in ("solution", "canonical_solution", "solution_notes"):
            if original.get(key):
                assert original[key] not in case["student_task"]
                assert original[key] not in json.dumps(case["solver_input"])


def test_generated_task_parts_are_exact_source_projection(pack):
    for case in calibration.all_cases(pack):
        if case["origin"] != "saved_generated_task":
            continue
        task_source = next(source for source in case["sources"] if source["student_fields"])
        data = calibration.read_json(task_source["path"])
        task = data["stages"]["D2_D3"]["task"] if "grounding_" in case["case_id"] else data["task"]
        assert case["student_task"] == "\n\n".join(
            task[key] for key in ("title", "body", "question")
        )
        assert task_source["student_fields"] == ["title", "body", "question"]
        assert set(case["solver_input"]) == {"student_task", "learner_context"}


def test_no_target_reference_or_desired_errors_in_solver_inputs(pack):
    for case in calibration.all_cases(pack):
        solver = case["solver_input"]
        assert solver == {
            "student_task": case["student_task"],
            "learner_context": case["learner_context"],
        }
        assert set(solver["learner_context"]) == {"assumed_prior_knowledge"}
        for key in (
            "learning_target",
            "target_concept",
            "references",
            "expected_reviews",
            "expected_familiar_approaches",
            "critical_features",
            "target_not_taught",
            "canonical_solution",
            "source_phase",
            "origin",
        ):
            assert key not in solver
            assert key not in solver["learner_context"]
        assert "provenance" not in solver["learner_context"]


def test_source_hashes_are_real_source_byte_hashes(pack):
    for case in calibration.all_cases(pack):
        for source in case["sources"]:
            path = calibration.ROOT / source["path"]
            assert source["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_changed_source_hash_is_rejected(pack, monkeypatch):
    monkeypatch.setattr(calibration, "file_digest", lambda _: "0" * 64)
    with pytest.raises(ValueError, match="Source changed"):
        calibration.validate_pack(pack, check_sources=True)


def test_frozen_input_change_is_rejected(pack):
    changed = copy.deepcopy(pack)
    changed["development"][0]["student_task"] += "\nchanged"
    with pytest.raises(ValueError, match="Frozen input changed"):
        calibration.validate_pack(changed, check_sources=False)


def test_target_contamination_is_rejected(pack):
    changed = copy.deepcopy(pack)
    changed["development"][0]["solver_input"]["learning_target"] = "injected target"
    with pytest.raises(ValueError, match="strict task/history projection"):
        calibration.validate_pack(changed, check_sources=False)


def test_reference_changes_do_not_rewrite_frozen_inputs(pack, monkeypatch):
    original_annotations = calibration.annotations

    def changed_annotations():
        notes = original_annotations()
        notes["expert_bicycle"]["references"]["room_for_invention"]["evidence"] += (
            " Provisional clarification."
        )
        return notes

    monkeypatch.setattr(calibration, "annotations", changed_annotations)
    changed = calibration.build_pack()
    assert changed["freeze"]["inputs_sha256"] == pack["freeze"]["inputs_sha256"]
    assert changed["development"][0]["references"] != pack["development"][0]["references"]


def test_references_explicitly_not_human_gold(pack):
    assert pack["reference_policy"]["not_human_ratings"]
    assert pack["reference_policy"]["not_validated_gold"]
    assert not pack["human_review_available"]
    assert pack["model_calls"] == 0
    assert not pack["freeze"]["model_judgments_executed"]
    for case in calibration.all_cases(pack):
        for metric, reference in case["references"].items():
            assert reference["provenance"] == "assistant_provisional"
            assert reference["label_confidence"] in {"high", "medium", "low"}
            assert reference["evidence"]
            assert reference["value"] in calibration.METRIC_VALUES[metric]
            assert reference["value"] in reference["acceptable_values"]
            assert not reference["human_reviewed"]
            assert not reference["validated_gold"]


@pytest.mark.parametrize("metric", list(calibration.METRIC_VALUES))
def test_every_categorical_value_has_an_explicit_case_or_control(pack, metric):
    values = {case["references"][metric]["value"] for case in calibration.all_cases(pack)}
    assert values == set(calibration.METRIC_VALUES[metric])


def test_only_genuine_ambiguity_has_alternative_reference_values(pack, cases):
    ambiguous = [
        (case["case_id"], metric)
        for case in calibration.all_cases(pack)
        for metric, reference in case["references"].items()
        if len(reference["acceptable_values"]) > 1
    ]
    assert ambiguous == [("expert_hummingbird", "mathematical_validity")]
    reason = cases["expert_hummingbird"]["references"]["mathematical_validity"]["evidence"]
    assert "overlap" in reason and "conditional" in reason


def test_metric_dependencies_are_conditional_not_failures(pack):
    for case in calibration.all_cases(pack):
        refs = case["references"]
        assert (refs["mathematical_validity"]["value"] != "not_assessed") == (
            refs["target_alignment"]["value"] == "yes"
        )
        assert (refs["familiar_approach_limits"]["value"] != "not_assessed") == (
            refs["prior_knowledge_accessibility"]["value"] == "yes"
        )


@pytest.mark.parametrize(
    ("case_id", "metric", "bad_value", "message"),
    [
        (
            "music_compare_distributions__gpt41__016",
            "mathematical_validity",
            "yes",
            "Mathematical-validity",
        ),
        ("control_inaccessible", "familiar_approach_limits", "no", "Familiar-limit"),
        ("expert_ship", "target_alignment", "maybe", "Invalid value"),
    ],
)
def test_invalid_references_are_rejected(pack, case_id, metric, bad_value, message):
    changed = copy.deepcopy(pack)
    case = next(case for case in calibration.all_cases(changed) if case["case_id"] == case_id)
    case["references"][metric]["value"] = bad_value
    case["references"][metric]["acceptable_values"] = [bad_value]
    with pytest.raises(ValueError, match=message):
        calibration.validate_pack(changed, check_sources=False)


def test_history_provenance_not_desired_mistakes(pack, cases):
    for case in calibration.all_cases(pack):
        assert case["prerequisite_provenance"]["independent_of_desired_errors"]
    assert (
        cases["expert_bicycle"]["prerequisite_provenance"]["kind"]
        == "existing_curated_expert_history"
    )
    assert (
        cases["expert_land"]["prerequisite_provenance"]["kind"] == "existing_curated_expert_history"
    )
    assert (
        cases["expert_furniture"]["prerequisite_provenance"]["kind"]
        == "existing_curated_expert_history"
    )
    for case_id in ("expert_consistency", "expert_country", "expert_time_sharing"):
        assert cases[case_id]["prerequisite_provenance"]["kind"] == "assistant_specified_history"
    source_context = calibration.read_json(
        f"{calibration.GROUNDING}/inputs/signed_product_ledger/context_A.json"
    )["learner_context"]
    assert (
        cases["grounding_signed_product_ledger_r01_A"]["learner_context"]["assumed_prior_knowledge"]
        == source_context["recently_taught"]
    )


def test_multitheme_target_and_history_match_frozen_config(pack):
    assert calibration.file_digest(calibration.SETTING) == calibration.SETTING_SHA256
    config = calibration.read_json(calibration.SETTING)
    for case in pack["development"]:
        if case["origin"] != "saved_generated_task":
            continue
        record = calibration.read_json(case["sources"][0]["path"])
        cell = next(cell for cell in config["cells"] if cell["cell_id"] == record["cell_id"])
        assert case["learning_target"] == cell["case"]["target_concept"]
        assert (
            case["learner_context"]["assumed_prior_knowledge"]
            == cell["learner_context"]["assumed_prior_knowledge"]
        )


def test_missing_target_context_and_history_stay_explicit(cases):
    missing_context = cases["control_missing_task_context"]
    assert missing_context["learning_target"] is None
    assert missing_context["references"]["target_alignment"]["value"] == "unclear"
    assert missing_context["references"]["prior_knowledge_accessibility"]["value"] == "unclear"
    missing_history = cases["control_missing_history"]
    assert missing_history["learner_context"]["assumed_prior_knowledge"] == []
    assert missing_history["references"]["target_alignment"]["value"] == "yes"
    assert missing_history["references"]["mathematical_validity"]["value"] == "yes"
    assert missing_history["references"]["prior_knowledge_accessibility"]["value"] == "unclear"


def test_current_source_answer_errors_do_not_mark_task_invalid(cases):
    time_case = cases["expert_time_sharing"]
    assert time_case["references"]["mathematical_validity"]["value"] == "yes"
    assert any("mid-July" in note and "wrong" in note for note in time_case["limitations"])
    assert "mid-July" not in time_case["student_task"]
    assert 6 * 6000 + Fraction(1, 2) * 12000 == 42000
    consistency = cases["expert_consistency"]
    assert consistency["references"]["mathematical_validity"]["value"] == "yes"
    assert any("all match is false" in note for note in consistency["limitations"])


def test_invention_is_not_a_keyword_no_hints_test(cases):
    proportional = cases["sports_basketball_ratio__gpt5mini__002"]
    assert "proportional" in proportional["student_task"]
    assert proportional["references"]["room_for_invention"]["value"] == "yes"
    assert cases["expert_bicycle"]["references"]["room_for_invention"]["value"] == "yes"
    assert (
        cases["synthetic_consistency_formula"]["references"]["room_for_invention"]["value"] == "no"
    )
    assert (
        cases["garden_composite_area__gpt5mini__028"]["references"]["room_for_invention"]["value"]
        == "partly"
    )


def test_no_every_expert_pass_assumption(cases):
    assert cases["expert_ship"]["references"]["room_for_invention"]["value"] == "no"
    assert cases["expert_walkcycle"]["references"]["familiar_approach_limits"]["value"] == "no"
    assert cases["expert_hummingbird"]["references"]["mathematical_validity"]["value"] == "unclear"


def test_fixture_states_and_provenance_are_complete(pack):
    observed = set()
    for group in pack["attempt_fixture_groups"]:
        assert group["provenance"] == "constructed_diagnostic_attempts"
        assert group["not_actual_student_work"]
        assert group["not_model_solver_output"]
        assert group["label_confidence"] == "high"
        assert calibration.fixture_verdicts(group) == group["expected_verdicts"]
        observed.update(review["status"] for review in group["expected_reviews"])
        for attempt in group["attempts"]:
            assert set(attempt) == {"idea", "work"}
    assert observed == set(calibration.ATTEMPT_STATUSES)


@pytest.mark.parametrize(
    ("fixture_id", "statuses", "accessibility", "limits"),
    [
        ("imported_formula_only", ["not_supported"], "unclear", "not_assessed"),
        ("trivial_restatement", ["not_supported"], "unclear", "not_assessed"),
        ("misread_data", ["not_supported"], "unclear", "not_assessed"),
        ("unverifiable_start", ["start_unresolved"], "unclear", "not_assessed"),
        ("supported_start_then_giving_up", ["unresolved"], "yes", "unclear"),
        (
            "target_limit_with_successful_alternative",
            ["target_limit", "meets_demands"],
            "yes",
            "yes",
        ),
        ("routine_meets_demands", ["meets_demands"], "yes", "no"),
        ("unrelated_missing_skill", ["unrelated_shortfall"], "yes", "no"),
        ("inconsistent_givens_not_target_limit", ["unrelated_shortfall"], "yes", "no"),
        ("unsupported_universal_proof", ["unresolved"], "yes", "unclear"),
        ("concrete_no_start", ["not_supported"], "no", "not_assessed"),
        (
            "success_and_unresolved_remain_unclear",
            ["meets_demands", "unresolved"],
            "yes",
            "unclear",
        ),
    ],
)
def test_fixed_fixture_judge_replies(pack, fixture_id, statuses, accessibility, limits):
    group = next(group for group in pack["attempt_fixture_groups"] if group["id"] == fixture_id)
    assert [review["status"] for review in group["expected_reviews"]] == statuses
    assert group["expected_verdicts"] == {
        "prior_knowledge_accessibility": accessibility,
        "familiar_approach_limits": limits,
    }
    assert calibration.fixture_verdicts(group) == group["expected_verdicts"]


def test_success_does_not_cancel_a_limit_or_resolve_another_outcome(pack):
    groups = {group["id"]: group for group in pack["attempt_fixture_groups"]}
    assert (
        groups["target_limit_with_successful_alternative"]["expected_verdicts"][
            "familiar_approach_limits"
        ]
        == "yes"
    )
    assert (
        groups["success_and_unresolved_remain_unclear"]["expected_verdicts"][
            "familiar_approach_limits"
        ]
        == "unclear"
    )


def test_unclear_proof_control_is_genuinely_unproved_not_a_solvable_task(cases):
    case = cases["control_unproved_universal_claim"]
    assert "every even integer" in case["student_task"]
    assert "Goldbach" in case["references"]["mathematical_validity"]["evidence"]
    assert case["references"]["mathematical_validity"]["value"] == "unclear"
    assert "unsuitable classroom task" in case["limitations"][0]


def test_all_executed_exact_checks_pass_and_are_not_whole_task_validation(pack):
    assert len(pack["deterministic_checks"]) == 25
    assert all(check["holds"] for check in pack["deterministic_checks"])
    assert all(
        check["evidence_level"] == "deterministic_arithmetic_only"
        for check in pack["deterministic_checks"]
    )
    assert calibration.mathematical_checks() == pack["deterministic_checks"]


def test_cli_verifies_saved_artifact_without_new_calls(capsys):
    assert calibration.main(["--verify"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["passed"]
    assert report["counts"]["development"] == 13


def test_cli_refuses_different_existing_artifact(pack, monkeypatch):
    changed = copy.deepcopy(pack)
    changed["status"] = "changed"
    monkeypatch.setattr(calibration, "build_pack", lambda: changed)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        calibration.main([])
    with pytest.raises(ValueError, match="differs from reproducible build"):
        calibration.main(["--verify"])
