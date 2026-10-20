import pytest

from src.evaluation.pf_grounding_statistics import exact_sign_test, paired_block_summary


def rows(case, pairs):
    return [
        {"case_id": case, "repeat": index, "arm": arm, "outcome": values[index]}
        for arm, values in zip(("grounded", "none"), zip(*pairs))
        for index in range(len(pairs))
    ]


def test_exact_sign_test_uses_decisive_case_counts():
    assert exact_sign_test(15, 5) == pytest.approx(0.04138946533203125)
    assert exact_sign_test(5, 0) == pytest.approx(0.0625)
    assert exact_sign_test(0, 0) is None
    assert exact_sign_test(1, 1) == 1


@pytest.mark.parametrize("wins,losses", [(-1, 0), (True, 0), (1.5, 0)])
def test_sign_test_rejects_invalid_counts(wins, losses):
    with pytest.raises(ValueError):
        exact_sign_test(wins, losses)


def test_unknowns_are_not_collapsed_into_concerns():
    result = paired_block_summary(
        rows("a", [(True, None), (False, True), (None, False), (True, True)]),
        treatment="grounded",
        baseline="none",
        bootstrap_samples=100,
    )
    case = result["per_case"][0]
    assert case["unresolved_pairs"] == 2
    assert case["baseline_only"] == 1
    assert case["treatment_only"] == 0
    assert case["both_supported"] == 1
    assert case["unknown_sensitivity_bounds"] == [-0.25, 0.25]
    assert case["arms"]["grounded"] == {
        "supported": 2, "not_supported": 1, "unknown": 1,
        "task_unavailable": 0, "audit_unavailable": 0,
    }


def test_bootstrap_resamples_cases_with_equal_weights():
    records = rows("a", [(True, False)] * 4) + rows("b", [(False, True)])
    result = paired_block_summary(
        records, treatment="grounded", baseline="none", bootstrap_samples=1000
    )
    assert result["scheduled_pairs"] == 5
    assert result["task_specifications"] == 2
    assert result["equal_case_weighted_supported_rate_difference"] == 0
    assert result["target_block_bootstrap"]["interval_95"] == [-1, 1]
    assert result["case_signs"]["descriptive_two_sided_p"] == 1


def test_twenty_generations_are_only_five_case_signs():
    records = [row for case in range(5) for row in rows(str(case), [(True, False)] * 4)]
    result = paired_block_summary(
        records, treatment="grounded", baseline="none", bootstrap_samples=10
    )
    assert result["scheduled_pairs"] == 20
    assert result["case_signs"]["positive"] == 5
    assert result["case_signs"]["descriptive_two_sided_p"] == 0.0625


def test_bootstrap_is_reproducible():
    records = rows("a", [(True, False)]) + rows("b", [(True, True)])
    kwargs = {"treatment": "grounded", "baseline": "none", "bootstrap_samples": 100}
    assert paired_block_summary(records, **kwargs) == paired_block_summary(records, **kwargs)


def test_duplicate_or_missing_arm_is_an_error():
    records = rows("a", [(True, False)])
    with pytest.raises(ValueError, match="Duplicate"):
        paired_block_summary(
            records + records[:1], treatment="grounded", baseline="none"
        )
    with pytest.raises(ValueError, match="Missing scheduled"):
        paired_block_summary(records[:1], treatment="grounded", baseline="none")


@pytest.mark.parametrize("changes", [
    {"outcome": 0}, {"case_id": ""}, {"repeat": True}, {"repeat": -1}
])
def test_invalid_outcome_and_slot_metadata_are_rejected(changes):
    records = rows("a", [(True, False)])
    records[0].update(changes)
    with pytest.raises(ValueError):
        paired_block_summary(records, treatment="grounded", baseline="none")


def test_outcome_requires_explicit_null():
    records = rows("a", [(True, False)])
    del records[0]["outcome"]
    with pytest.raises(ValueError, match="explicitly null"):
        paired_block_summary(records, treatment="grounded", baseline="none")


def test_task_failure_is_separate_from_judge_failure_and_unknown():
    records = rows("a", [(None, None), (None, False)])
    records[0].update(
        availability="task_unavailable", unavailability_reason="Generation API failed"
    )
    records[2].update(
        availability="audit_unavailable", unavailability_reason="Rating was malformed"
    )
    case = paired_block_summary(
        records, treatment="grounded", baseline="none", bootstrap_samples=10
    )["per_case"][0]
    assert case["arms"]["grounded"]["task_unavailable"] == 1
    assert case["arms"]["grounded"]["unknown"] == 1
    assert case["arms"]["none"]["audit_unavailable"] == 1
    assert case["arms"]["none"]["unknown"] == 0
    assert len(case["unavailability_records"]) == 2
    assert case["unknown_sensitivity_bounds"] == [-0.5, 0.5]


def test_unavailable_requires_null_and_reason():
    records = rows("a", [(True, False)])
    records[0]["availability"] = "task_unavailable"
    with pytest.raises(ValueError, match="null outcome"):
        paired_block_summary(records, treatment="grounded", baseline="none")
