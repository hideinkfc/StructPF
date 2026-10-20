from fractions import Fraction

import pytest

from src.generation.fill_check import (
    check_fill,
    checker_capability_contract,
    evaluate_formula,
    validate_plan_expressions,
)
from src.generation.situation_skeletons import MathPlan, skeleton_from_payload


def test_evaluate_formula_uses_exact_rationals():
    value = evaluate_formula(
        "(a_d[0]/a_t[0] + a_d[1]/a_t[1]) / 2",
        {"a_d": [9, 10], "a_t": [9, 1]},
    )
    assert str(value) in {"11/2", "5.5"}


def test_checker_contract_describes_the_implemented_language():
    contract = checker_capability_contract()
    assert "value_source='given'" in contract
    assert "sum(named_list) only" in contract
    assert "abs(scalar_expression)" in contract
    assert "literal non-negative integer" in contract
    assert "unary negation (-x)" in contract
    assert "no equation solving" in contract
    assert "JSON integer values" in contract
    assert "x*x is supported" in contract
    assert "x**2 is rejected" in contract
    assert "missing named function alone does not prove impossibility" in contract
    assert "genuine parts of the stated calculation" in contract
    assert "placeholders used to force success or failure" in contract
    assert "==" in contract and "!=" in contract


def test_supported_bounded_arithmetic_evaluates_but_native_operation_is_rejected():
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "parts",
                    "role": "list",
                    "list_length": 2,
                    "value_source": "given",
                }
            ],
            "question": "What is the result?",
        }
    ).quantities
    supported = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {
                "expressions": {
                    "answer": "sum(parts)/2 + abs(parts[0]-parts[1])",
                }
            },
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert validate_plan_expressions(supported) == ()
    assert check_fill(supported, {"parts": [2, 5]}).accepted

    repeated_multiplication = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"answer": "parts[0]*parts[0]"}},
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert validate_plan_expressions(repeated_multiplication) == ()
    assert check_fill(repeated_multiplication, {"parts": [2, 5]}).accepted

    for formula in (
        "unsupported_fn(parts)",
        "parts[0] % 2",
        "parts[0] ** 2",
        "+parts[0]",
    ):
        unsupported = MathPlan.from_payload(
            {
                "schema_version": "math-plan/v2",
                "target": {"expressions": {"answer": formula}},
                "answer_rule": {"kind": "scalar", "labels": ["answer"]},
            },
            quantities,
        )
        rejected = check_fill(unsupported, {"parts": [2, 5]})
        assert not rejected.accepted
        assert rejected.status == "needs_review"

    negated = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"answer": "-parts[0]"}},
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert validate_plan_expressions(negated) == ()
    assert check_fill(negated, {"parts": [2, 5]}).accepted


def test_accepts_when_prior_ranking_disagrees():
    payload = {
        "values": {
            "journey_a_segment_distances": [9, 10],
            "journey_a_segment_times": [9, 1],
            "journey_b_segment_distances": [2, 2],
            "journey_b_segment_times": [1, 1],
        },
        "target": {
            "expressions": {
                "A": "sum(journey_a_segment_distances)/sum(journey_a_segment_times)",
                "B": "sum(journey_b_segment_distances)/sum(journey_b_segment_times)",
            }
        },
        "priors": [
            {
                "resource": "Speed = distance / time",
                "expressions": {
                    "A": (
                        "(journey_a_segment_distances[0]/journey_a_segment_times[0]"
                        "+journey_a_segment_distances[1]/journey_a_segment_times[1])/2"
                    ),
                    "B": (
                        "(journey_b_segment_distances[0]/journey_b_segment_times[0]"
                        "+journey_b_segment_distances[1]/journey_b_segment_times[1])/2"
                    ),
                },
            }
        ],
    }
    result = check_fill(payload)
    assert result.accepted
    assert result.target is not None
    assert result.target.argmax == ("B",)
    assert result.priors[0].argmax == ("A",)


def test_rejects_when_prior_agrees_with_target():
    payload = {
        "values": {
            "a": [4, 12],
            "ta": [4, 6],
            "b": [6, 4],
            "tb": [1, 4],
        },
        "target": {
            "expressions": {
                "A": "sum(a)/sum(ta)",
                "B": "sum(b)/sum(tb)",
            }
        },
        "priors": [
            {
                "resource": "mean of part speeds",
                "expressions": {
                    "A": "(a[0]/ta[0]+a[1]/ta[1])/2",
                    "B": "(b[0]/tb[0]+b[1]/tb[1])/2",
                },
            }
        ],
    }
    result = check_fill(payload)
    assert not result.accepted
    assert "agrees" in result.reason


def test_rejects_unknown_names_and_missing_target():
    bad = check_fill(
        {
            "values": {"x": 1},
            "target": {"expressions": {"A": "y"}},
            "priors": [{"resource": "r", "expressions": {"A": "x"}}],
        }
    )
    assert not bad.accepted
    missing = check_fill({"values": {"x": 1}, "target": {"expressions": {"A": "x"}}})
    assert not missing.accepted


def _frozen_plan(**overrides):
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "a",
                    "role": "amount",
                    "description": "first amount",
                    "value_source": "given",
                },
                {
                    "name": "b",
                    "role": "amount",
                    "description": "second amount",
                    "value_source": "given",
                },
            ],
            "question": "Which amount is larger?",
        }
    ).quantities
    payload = {
        "target": {
            "name": "target",
            "expressions": {"A": "a", "B": "b"},
        },
        "priors": [
            {
                "name": "prior",
                "approach_id": "approach_one",
                "expressions": {"A": "a + 1", "B": "b - 1"},
            }
        ],
        "answer_rule": {
            "kind": "largest",
            "labels": ["A", "B"],
            "unit": "units",
            "require_unique": True,
        },
        "required_checks": ["at_least_one_prior_disagrees"],
    }
    payload.update(overrides)
    return MathPlan.from_payload(
        payload,
        quantities,
        approach_ids={"approach_one"},
    )


def test_plan_checker_accepts_only_a_declared_answer_contrast():
    result = check_fill(_frozen_plan(), {"a": 4, "b": 5})
    assert result.accepted
    assert result.status == "accepted"
    assert result.target is not None
    assert result.target.argmax == ("B",)
    assert result.priors[0].argmax == ("A",)


def test_plan_checker_rejects_undefined_prior_instead_of_accepting_it():
    plan = _frozen_plan(
        priors=[
            {
                "name": "prior",
                "approach_id": "approach_one",
                "expressions": {"A": "a/(b-b)", "B": "b"},
            }
        ]
    )
    result = check_fill(plan, {"a": 2, "b": 5})
    assert not result.accepted
    assert result.status == "rejected"
    assert "undefined" in result.reason


def test_scalar_target_is_not_mistaken_for_a_tie():
    payload = {
        "target": {"name": "target", "expressions": {"answer": "a + 1"}},
        "priors": [
            {
                "name": "prior",
                "approach_id": "approach_one",
                "expressions": {"answer": "a + 2"},
            }
        ],
        "answer_rule": {
            "kind": "scalar",
            "labels": ["answer"],
            "require_unique": True,
        },
    }
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "a",
                    "role": "amount",
                    "description": "amount",
                    "value_source": "given",
                }
            ],
            "question": "What is the answer?",
        }
    ).quantities
    plan = MathPlan.from_payload(payload, quantities, approach_ids={"approach_one"})
    result = check_fill(plan, {"a": 3})
    assert result.accepted
    assert not result.target.tied


def test_checker_rejects_a_changed_nonwinning_value_when_the_answer_is_unchanged():
    plan = _frozen_plan()
    result = check_fill(plan, {"a": 1, "b": 5})
    assert not result.accepted
    assert "agrees" in result.reason


def test_unknown_required_check_requires_review():
    plan = _frozen_plan(required_checks=["invented_check"])
    result = check_fill(plan, {"a": 2, "b": 5})
    assert not result.accepted
    assert result.status == "needs_review"


def test_plan_requires_matching_labels():
    with pytest.raises(ValueError, match="labels"):
        _frozen_plan(
            priors=[
                {
                    "name": "prior",
                    "approach_id": "approach_one",
                    "expressions": {"A": "a"},
                }
            ]
        )


def test_plan_rejects_incompatible_path_units():
    with pytest.raises(ValueError, match="units"):
        _frozen_plan(
            target={
                "name": "target",
                "unit": "km/h",
                "expressions": {"A": "a", "B": "b"},
            },
            priors=[
                {
                    "name": "prior",
                    "approach_id": "approach_one",
                    "unit": "km",
                    "expressions": {"A": "a + 1", "B": "b - 1"},
                }
            ],
        )


def test_unsupported_prior_requires_review_instead_of_counting_as_failure():
    plan = _frozen_plan(
        priors=[
            {
                "name": "qualitative approach",
                "approach_id": "approach_one",
                "supported": False,
                "expressions": {},
            }
        ]
    )
    result = check_fill(plan, {"a": 4, "b": 5})
    assert not result.accepted
    assert result.status == "needs_review"


def test_qualitative_prior_does_not_block_a_valid_numerical_target():
    plan = _frozen_plan(
        priors=[
            {
                "name": "drawing approach",
                "approach_id": "approach_one",
                "checkability": "qualitative",
                "supported": False,
                "expressions": {},
            }
        ],
        required_checks=[],
    )
    result = check_fill(plan, {"a": 4, "b": 5})
    assert result.accepted
    assert result.priors[0].error == "not numerically checked"


def test_symbolic_index_is_rejected_before_number_search():
    plan = _frozen_plan(
        target={"name": "target", "expressions": {"A": "a[i]", "B": "b"}},
        required_checks=[],
    )
    result = check_fill(plan, {"a": 4, "b": 5})
    assert not result.accepted
    assert result.status == "needs_review"
    assert "cannot index scalar slot" in result.reason


def test_v2_target_only_checks_answer_and_essential_constraints():
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {"name": "a", "role": "amount", "value_source": "given"},
                {"name": "b", "role": "amount", "value_source": "given"},
            ],
            "question": "Which amount is larger?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"A": "a", "B": "b"}, "unit": "points squared"},
            "answer_rule": {
                "kind": "largest",
                "labels": ["A", "B"],
                "unit": "points squared",
            },
            "constraints": [
                {"left": "a", "operator": "==", "right": "4", "description": "fixed A"},
            ],
        },
        quantities,
    )
    assert "priors" not in plan.to_dict()
    assert check_fill(plan, {"a": 4, "b": 5}).accepted
    failed = check_fill(plan, {"a": 3, "b": 5})
    assert not failed.accepted
    assert "constraints" in failed.reason


def test_v2_does_not_require_compatible_prior_units_and_rejects_legacy_fields():
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    payload = {
        "schema_version": "math-plan/v2",
        "target": {"expressions": {"answer": "x"}, "unit": "points squared"},
        "answer_rule": {"kind": "scalar", "labels": ["answer"], "unit": "points squared"},
    }
    plan = MathPlan.from_payload(payload, quantities)
    assert check_fill(plan, {"x": 2}).accepted
    for field in ("priors", "required_checks"):
        with pytest.raises(ValueError, match="must not include"):
            MathPlan.from_payload({**payload, field: []}, quantities)
    with pytest.raises(ValueError, match="unsupported"):
        MathPlan.from_payload({**payload, "schema_version": "math-plan/v9"}, quantities)


def test_v2_rejects_extra_fields_and_mismatched_quantity_metadata():
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    payload = {
        "schema_version": "math-plan/v2",
        "quantities": [quantities[0].to_dict()],
        "target": {"expressions": {"answer": "x"}},
        "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        "constraints": [],
    }
    MathPlan.from_payload(payload, quantities)
    with pytest.raises(ValueError, match="unsupported fields"):
        MathPlan.from_payload({**payload, "unresolved": ["x"]}, quantities)
    with pytest.raises(ValueError, match="do not match"):
        MathPlan.from_payload(
            {**payload, "quantities": [{"name": "x", "role": "list"}]},
            quantities,
        )


def test_v2_variance_keeps_same_summary_constraints():
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {"name": "a", "role": "list", "list_length": 4},
                {"name": "b", "role": "list", "list_length": 4},
            ],
            "question": "Which list is less spread out?",
        }
    ).quantities

    def variance(name):
        return (
            f"(({name}[0]*{name}[0]+{name}[1]*{name}[1]+"
            f"{name}[2]*{name}[2]+{name}[3]*{name}[3])-"
            f"sum({name})*sum({name})/4)/4"
        )

    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {
                "expressions": {"A": variance("a"), "B": variance("b")},
                "unit": "points squared",
            },
            "answer_rule": {
                "kind": "smallest",
                "labels": ["A", "B"],
                "unit": "points squared",
            },
            "constraints": [
                {"left": "sum(a)/4", "operator": "==", "right": "sum(b)/4"},
                {"left": "a[3]-a[0]", "operator": "==", "right": "b[3]-b[0]"},
            ],
        },
        quantities,
    )
    assert check_fill(plan, {"a": [4, 6, 6, 8], "b": [4, 4, 8, 8]}).accepted
    changed = check_fill(plan, {"a": [4, 6, 6, 8], "b": [4, 4, 8, 9]})
    assert not changed.accepted
    assert "constraints" in changed.reason


@pytest.mark.parametrize(
    "target",
    [
        {"expressions": {"answer": "missing"}},
        {"expressions": {"answer": "x[0]"}},
        {"expressions": {"answer": "mean(x)"}},
    ],
)
def test_v2_rejects_invalid_target_expressions(target):
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": target,
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    result = check_fill(plan, {"x": 2})
    assert not result.accepted


@pytest.mark.parametrize("field", ["constraints", "quantities"])
@pytest.mark.parametrize("value", [None, {}, "", False, 0])
def test_v2_rejects_malformed_empty_lists(field, value):
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    with pytest.raises(ValueError, match="must be a list"):
        MathPlan.from_payload(
            {
                "schema_version": "math-plan/v2",
                "target": {"expressions": {"answer": "x"}},
                "answer_rule": {"kind": "scalar", "labels": ["answer"]},
                field: value,
            },
            quantities,
        )


@pytest.mark.parametrize(
    "formula, values",
    [
        ("x/(x-x)", {"x": 2}),
        ("x", {"x": 0}),
        ("x", {"x": -1}),
        ("x", {"x": True}),
        ("x", {"x": float("nan")}),
        ("x", {}),
        ("x", {"x": 2, "extra": 3}),
    ],
)
def test_v2_keeps_undefined_target_and_input_checks(formula, values):
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"answer": formula}},
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert not check_fill(plan, values).accepted


def test_positive_integer_domain_rejects_fractional_counts():
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "counts",
                    "role": "list",
                    "list_length": 2,
                    "value_domain": "positive_integer",
                }
            ],
            "question": "What is the count total?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"answer": "sum(counts)"}},
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert check_fill(plan, {"counts": [2, 3]}).accepted
    rejected = check_fill(plan, {"counts": [2, 3.5]})
    assert not rejected.accepted
    assert "whole numbers" in rejected.reason
    json_number = check_fill(plan, {"counts": [2.0, 3]})
    assert not json_number.accepted
    assert "whole numbers" in json_number.reason


def test_v2_accepts_historical_quantity_metadata_without_value_domain():
    quantities = skeleton_from_payload(
        {
            "quantities": [{"name": "x", "role": "amount"}],
            "question": "What is the result?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "quantities": [
                {
                    "name": "x",
                    "role": "amount",
                    "description": "",
                    "value_source": "given",
                    "unit": "",
                    "list_length": None,
                }
            ],
            "target": {"expressions": {"answer": "x"}},
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
        quantities,
    )
    assert check_fill(plan, {"x": 2}).accepted


def _prior_contrast_plan():
    """Use same-unit savings balances; subtraction is a dollar gain, not mixed units."""
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "starting_balances",
                    "role": "list",
                    "description": "account balances before the same savings period, in dollars",
                    "unit": "dollars",
                    "list_length": 2,
                },
                {
                    "name": "ending_balances",
                    "role": "list",
                    "description": "account balances after the savings period, in dollars",
                    "unit": "dollars",
                    "list_length": 2,
                },
            ],
            "question": "Compare the growth of two savings balances.",
        }
    ).quantities
    return MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {
                "name": "growth_factor",
                "expressions": {
                    "A": "ending_balances[0]/starting_balances[0]",
                    "B": "ending_balances[1]/starting_balances[1]",
                },
            },
            "answer_rule": {
                "kind": "largest",
                "labels": ["A", "B"],
                "require_unique": True,
            },
            "constraints": [],
            "prior_contrast": {
                "name": "compare absolute dollar gains",
                "approach_id": "compare_dollar_gains",
                "expressions": {
                    "A": "ending_balances[0]-starting_balances[0]",
                    "B": "ending_balances[1]-starting_balances[1]",
                },
            },
        },
        quantities,
        approach_ids={"compare_dollar_gains"},
    )


def _steady_rate_contrast_plan(expected_target_equal=False, expected_prior_equal=True):
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {"name": "attempts", "role": "list", "list_length": 3},
                {"name": "makes", "role": "list", "list_length": 3},
            ],
            "question": "Do the rows show a constant proportional rate?",
        }
    ).quantities
    return MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {
                "name": "unit_rates",
                "expressions": {
                    label: f"makes[{index}]/attempts[{index}]"
                    for index, label in enumerate(("A", "B", "C"))
                },
            },
            "answer_rule": {
                "kind": "equal",
                "labels": ["A", "B", "C"],
            },
            "constraints": [
                {
                    "left": "attempts[1]-attempts[0]",
                    "operator": "==",
                    "right": "attempts[2]-attempts[1]",
                    "description": "attempts rise by equal amounts",
                }
            ],
            "prior_contrast": {
                "name": "compare consecutive makes",
                "approach_id": "steady_additive_steps",
                "expressions": {
                    "step_1": "makes[1]-makes[0]",
                    "step_2": "makes[2]-makes[1]",
                },
                "expected_target_equal": expected_target_equal,
                "expected_prior_equal": expected_prior_equal,
            },
        },
        quantities,
        approach_ids={"steady_additive_steps"},
    )


def test_v2_checks_a_selected_prior_contrast_and_accepts_a_prior_tie():
    plan = _prior_contrast_plan()
    result = check_fill(
        plan,
        {"starting_balances": [10, 20], "ending_balances": [14, 24]},
    )
    assert result.accepted
    assert result.target is not None
    assert result.target.argmax == ("A",)
    assert result.target.values == {"A": "7/5", "B": "6/5"}
    assert len(result.priors) == 1
    assert result.priors[0].approach_id == "compare_dollar_gains"
    assert result.priors[0].values == {"A": "4", "B": "4"}
    assert result.priors[0].argmax == ("A", "B")
    assert result.priors[0].tied
    assert "selected prior contrast differs" in result.reason


def test_v2_rejects_a_prior_contrast_that_agrees_with_the_target():
    quantities = skeleton_from_payload(
        {
            "quantities": [
                {"name": "attempts", "role": "list", "list_length": 3},
                {"name": "made", "role": "list", "list_length": 3},
            ],
            "question": "Which group has the largest miss rate?",
        }
    ).quantities
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {
                "expressions": {
                    label: f"(attempts[{index}]-made[{index}])/attempts[{index}]"
                    for index, label in enumerate(("A", "B", "C"))
                }
            },
            "answer_rule": {
                "kind": "largest",
                "labels": ["A", "B", "C"],
                "require_unique": True,
            },
            "prior_contrast": {
                "name": "compare attempt totals",
                "approach_id": "compare_totals",
                "expressions": {
                    label: f"attempts[{index}]" for index, label in enumerate(("A", "B", "C"))
                },
            },
        },
        quantities,
        approach_ids={"compare_totals"},
    )
    result = check_fill(plan, {"attempts": [10, 20, 30], "made": [5, 10, 12]})
    assert not result.accepted
    assert "agrees with the target decision" in result.reason
    assert result.target is not None
    assert result.target.argmax == ("C",)
    assert result.priors[0].argmax == ("C",)
    assert "selected prior contrast agrees" in result.retry_feedback()
    assert "prior_contrast" in result.retry_feedback()


def test_v2_prior_contrast_rejects_unsupported_comparison_contracts():
    plan = _prior_contrast_plan().to_dict()
    quantities = _prior_contrast_plan().quantities
    for payload in (
        {
            **plan,
            "prior_contrast": {
                **plan["prior_contrast"],
                "approach_id": "missing",
            },
        },
        {
            **plan,
            "prior_contrast": {
                **plan["prior_contrast"],
                "expressions": {
                    "A": "ending_balances[0]-starting_balances[0]",
                },
            },
        },
        {
            **plan,
            "target": {
                "name": "answer",
                "expressions": {
                    "answer": "starting_balances[0]+ending_balances[0]",
                },
            },
            "answer_rule": {"kind": "scalar", "labels": ["answer"]},
        },
    ):
        with pytest.raises(ValueError, match="prior_contrast"):
            MathPlan.from_payload(
                payload,
                quantities,
                approach_ids={"compare_dollar_gains"},
            )


def test_v2_unsupported_prior_contrast_expression_needs_review():
    plan = _prior_contrast_plan().to_dict()
    plan["prior_contrast"]["expressions"]["A"] = "median(starting_balances)"
    parsed = MathPlan.from_payload(
        plan,
        _prior_contrast_plan().quantities,
        approach_ids={"compare_dollar_gains"},
    )
    result = check_fill(
        parsed,
        {"starting_balances": [10, 20], "ending_balances": [14, 24]},
    )
    assert not result.accepted
    assert result.status == "needs_review"
    assert "selected prior contrast" in result.reason


def test_v2_equal_steps_do_not_imply_equal_unit_rates():
    plan = _steady_rate_contrast_plan()
    result = check_fill(plan, {"attempts": [10, 20, 30], "makes": [4, 10, 16]})

    assert result.accepted
    assert result.target is not None
    assert result.target.values == {"A": "2/5", "B": "1/2", "C": "8/15"}
    assert len(set(result.target.values.values())) == 3
    assert result.priors[0].values == {"step_1": "6", "step_2": "6"}
    assert result.contrast_decisions == {
        "target_equal": False,
        "prior_equal": True,
        "expected_target_equal": False,
        "expected_prior_equal": True,
    }
    assert result.to_dict()["contrast_decisions"] == result.contrast_decisions


def test_equal_input_and_output_steps_with_first_two_equal_rates_force_the_third_equal():
    for first_attempts in range(1, 16):
        for attempt_step in range(1, 10):
            attempts = [
                first_attempts,
                first_attempts + attempt_step,
                first_attempts + 2 * attempt_step,
            ]
            for first_makes in range(1, first_attempts + 1):
                second_makes = Fraction(
                    first_makes * attempts[1],
                    attempts[0],
                )
                if second_makes.denominator != 1:
                    continue
                second_makes = int(second_makes)
                makes_step = second_makes - first_makes
                third_makes = second_makes + makes_step
                makes = [first_makes, second_makes, third_makes]
                if third_makes > attempts[2]:
                    continue

                rates = [Fraction(made, attempted) for made, attempted in zip(makes, attempts)]
                assert attempts[1] - attempts[0] == attempts[2] - attempts[1]
                assert makes[1] - makes[0] == makes[2] - makes[1]
                assert rates[0] == rates[1] == rates[2]


def test_v2_equal_contrast_accepts_the_selected_reverse_outcomes_too():
    plan = _steady_rate_contrast_plan(expected_target_equal=True, expected_prior_equal=False)
    payload = plan.to_dict()
    payload["constraints"] = []
    parsed = MathPlan.from_payload(
        payload,
        plan.quantities,
        approach_ids={"steady_additive_steps"},
    )
    result = check_fill(parsed, {"attempts": [10, 20, 40], "makes": [5, 10, 20]})

    assert result.accepted
    assert result.contrast_decisions == {
        "target_equal": True,
        "prior_equal": False,
        "expected_target_equal": True,
        "expected_prior_equal": False,
    }


def test_v2_equal_contrast_rejects_values_that_miss_selected_outcomes():
    plan = _steady_rate_contrast_plan(expected_target_equal=True, expected_prior_equal=False)
    result = check_fill(plan, {"attempts": [10, 20, 30], "makes": [4, 10, 16]})

    assert not result.accepted
    assert "target equality result differs" in result.reason
    assert result.contrast_decisions == {
        "target_equal": False,
        "prior_equal": True,
        "expected_target_equal": True,
        "expected_prior_equal": False,
    }


def test_v2_equal_contrast_rejects_prior_values_that_miss_selected_outcome():
    plan = _steady_rate_contrast_plan()
    result = check_fill(plan, {"attempts": [10, 20, 30], "makes": [4, 10, 17]})

    assert not result.accepted
    assert "prior equality result differs" in result.reason
    assert result.contrast_decisions == {
        "target_equal": False,
        "prior_equal": False,
        "expected_target_equal": False,
        "expected_prior_equal": True,
    }


def test_v2_equal_contrast_requires_selected_opposite_outcomes():
    plan = _steady_rate_contrast_plan().to_dict()
    quantities = _steady_rate_contrast_plan().quantities
    missing_outcome = {
        **plan,
        "prior_contrast": {
            **plan["prior_contrast"],
            "expected_prior_equal": None,
        },
    }
    with pytest.raises(ValueError, match="requires selected expected_target_equal"):
        MathPlan.from_payload(
            missing_outcome,
            quantities,
            approach_ids={"steady_additive_steps"},
        )

    same_outcomes = {
        **plan,
        "prior_contrast": {
            **plan["prior_contrast"],
            "expected_prior_equal": False,
        },
    }
    with pytest.raises(ValueError, match="expected outcomes must differ"):
        MathPlan.from_payload(
            same_outcomes,
            quantities,
            approach_ids={"steady_additive_steps"},
        )


def test_v2_equal_contrast_rejects_one_scalar_and_unsupported_prior_expressions():
    plan = _steady_rate_contrast_plan().to_dict()
    quantities = _steady_rate_contrast_plan().quantities
    one_scalar = {
        **plan,
        "prior_contrast": {
            **plan["prior_contrast"],
            "expressions": {"only_one": "makes[1]-makes[0]"},
        },
    }
    with pytest.raises(ValueError, match="at least two prior comparisons"):
        MathPlan.from_payload(
            one_scalar,
            quantities,
            approach_ids={"steady_additive_steps"},
        )

    unsupported = {
        **plan,
        "prior_contrast": {
            **plan["prior_contrast"],
            "expressions": {
                "step_1": "median(makes)",
                "step_2": "makes[2]-makes[1]",
            },
        },
    }
    parsed = MathPlan.from_payload(
        unsupported,
        quantities,
        approach_ids={"steady_additive_steps"},
    )
    result = check_fill(parsed, {"attempts": [10, 20, 30], "makes": [4, 10, 16]})
    assert not result.accepted
    assert result.status == "needs_review"
    assert "selected prior contrast" in result.reason
