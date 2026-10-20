import pytest

from src.generation.situation_skeletons import (
    ALLOWED_ROLES,
    ALLOWED_VALUE_DOMAINS,
    ALLOWED_VALUE_SOURCES,
    MathPlan,
    MethodVerdict,
    best_candidates,
    judge_selection_from_payload,
    number_requirements_from_payload,
    rank_candidates,
    selected_candidate,
    skeleton_from_payload,
    skeleton_from_proposal_payload,
    skeleton_schema_contract,
    verdicts_from_payload,
)

PRIOR_METHODS = ["Ratio and proportion", "LCM and HCF", "Trial and error"]


def test_skeleton_schema_contract_uses_authoritative_enums():
    contract = skeleton_schema_contract()
    assert f'"{"|".join(sorted(ALLOWED_ROLES))}"' in contract
    assert f'"{"|".join(sorted(ALLOWED_VALUE_SOURCES))}"' in contract
    assert f'"{"|".join(sorted(ALLOWED_VALUE_DOMAINS))}"' in contract
    assert "Given list quantities require a fixed positive integer list_length" in contract
    assert 'only value_source="given" quantities bind later checker inputs' in contract


def _payload(**overrides):
    base = {
        "quantities": [
            {"name": "remaining_distance", "role": "whole", "description": "distance left"},
            {"name": "slow_rate", "role": "rate", "description": "slow mode rate"},
            {"name": "fast_rate", "role": "rate", "description": "fast mode rate"},
            {"name": "split", "role": "unknown", "description": "unknown split point"},
        ],
        "question": "Where should the whole be split so both sides take the same time?",
    }
    base.update(overrides)
    return base


def test_skeleton_requires_quantities_and_question():
    with pytest.raises(ValueError, match="quantities"):
        skeleton_from_payload({"question": "q"})
    with pytest.raises(ValueError, match="question"):
        skeleton_from_payload(_payload(question=" "))


def test_skeleton_rejects_numbers_and_bad_roles():
    with pytest.raises(ValueError, match="number"):
        skeleton_from_payload(_payload(question="Split 5000 into two parts"))
    bad = _payload()
    bad["quantities"] = [{"name": "x", "role": "speed", "description": "not an allowed role"}]
    with pytest.raises(ValueError, match="role"):
        skeleton_from_payload(bad)


def test_skeleton_rejects_duplicate_and_non_snake_names():
    dup = _payload()
    dup["quantities"] = dup["quantities"][:1] * 2
    with pytest.raises(ValueError, match="duplicate"):
        skeleton_from_payload(dup)
    ugly = _payload()
    ugly["quantities"] = [{"name": "Remaining Distance", "role": "whole"}]
    with pytest.raises(ValueError, match="snake_case"):
        skeleton_from_payload(ugly)


def _verdicts_payload():
    return {
        "candidates": [
            {
                "id": 0,
                "target_named": False,
                "methods": [
                    {"method": m, "can_start": True, "settles_question": False}
                    for m in PRIOR_METHODS
                ],
            },
            {
                "id": 1,
                "target_named": False,
                "methods": [
                    {"method": "Ratio and proportion", "can_start": True, "settles_question": True},
                    {"method": "LCM and HCF", "can_start": True, "settles_question": False},
                    {"method": "Trial and error", "can_start": True, "settles_question": False},
                ],
            },
        ]
    }


def test_judge_payload_validates_methods_ids_and_target_named():
    verdicts = verdicts_from_payload(_verdicts_payload(), PRIOR_METHODS)
    assert set(verdicts) == {0, 1}
    target_named, method_verdicts = verdicts[0]
    assert target_named is False
    assert len(method_verdicts) == 3

    bad = _verdicts_payload()
    bad["candidates"][0]["methods"][0]["method"] = "Not a method"
    with pytest.raises(ValueError, match="unknown method"):
        verdicts_from_payload(bad, PRIOR_METHODS)

    missing = {"candidates": [_verdicts_payload()["candidates"][0]]}
    missing["candidates"][0]["methods"] = missing["candidates"][0]["methods"][:2]
    with pytest.raises(ValueError, match="covers"):
        verdicts_from_payload(missing, PRIOR_METHODS)

    no_flag = _verdicts_payload()
    del no_flag["candidates"][0]["target_named"]
    with pytest.raises(ValueError, match="target_named"):
        verdicts_from_payload(no_flag, PRIOR_METHODS)

    unknown_approach = _verdicts_payload()
    unknown_approach["candidates"][0]["methods"][0]["approach_ids"] = ["missing"]
    with pytest.raises(ValueError, match="unknown approaches"):
        verdicts_from_payload(
            unknown_approach,
            PRIOR_METHODS,
            {0: {"known"}, 1: {"known"}},
        )


def test_judge_payload_preserves_number_requirements():
    payload = _verdicts_payload()
    payload["candidates"][0]["number_requirements"] = [
        {
            "condition": "Both data sets have the same mean.",
            "purpose": "Average performance alone should not decide the comparison.",
        }
    ]
    requirements = number_requirements_from_payload(payload)
    assert requirements[0][0].condition == "Both data sets have the same mean."
    assert (
        requirements[0][0].purpose == "Average performance alone should not decide the comparison."
    )

    bad = _verdicts_payload()
    bad["candidates"][0]["number_requirements"] = [{"condition": "missing purpose"}]
    with pytest.raises(ValueError, match="needs non-empty"):
        number_requirements_from_payload(bad)

    bad["candidates"][0]["number_requirements"] = [{"condition": None, "purpose": ["not text"]}]
    with pytest.raises(ValueError, match="needs non-empty"):
        number_requirements_from_payload(bad)


def test_compact_judge_selection_preserves_reason_and_requirements():
    selection = judge_selection_from_payload(
        {
            "recommended_id": 1,
            "approaches": [
                "Compare familiar summaries.",
                "Plot the observations and inspect their spread.",
            ],
            "reason": "The comparison creates a clear unresolved learning opportunity.",
            "main_concern": "The number constraints still need checking.",
            "number_requirements": [
                {
                    "condition": "The two means match.",
                    "purpose": "Mean alone should not decide the comparison.",
                }
            ],
        },
        {0, 1},
    )
    assert selection is not None
    assert selection.recommended_id == 1
    assert len(selection.approaches) == 2
    assert (
        selection.number_requirements[0].purpose == "Mean alone should not decide the comparison."
    )

    winner = selected_candidate(
        [skeleton_from_payload(_payload()), skeleton_from_payload(_payload())],
        selection,
    )[0]
    assert winner.candidate_id == 1
    assert winner.selection_reason.startswith("The comparison")
    assert winner.to_dict()["selection_approaches"] == list(selection.approaches)
    assert winner.number_requirements[0].condition == "The two means match."

    with pytest.raises(ValueError, match="not a candidate"):
        judge_selection_from_payload(
            {
                "recommended_id": 3,
                "approaches": ["One approach"],
                "reason": "reason",
                "main_concern": None,
                "number_requirements": [],
            },
            {0, 1},
        )


def test_compact_selection_records_operational_prior_contrast_and_checkability():
    skeleton = skeleton_from_payload(
        _payload(
            approaches=[
                {
                    "id": "compare_differences",
                    "resources": ["Ratio and proportion"],
                    "procedure": "Compare the absolute changes between each input and output.",
                    "why_plausible": "The paired quantities invite subtraction.",
                }
            ]
        )
    )
    payload = {
        "recommended_id": 0,
        "approaches": ["Compare the paired quantities by subtracting."],
        "reason": "The task depends on comparing additive and multiplicative views.",
        "main_concern": None,
        "number_requirements": [],
        "prior_contrast": {
            "approach_id": "compare_differences",
            "operational_move": (
                "Subtract each input from its paired output, then compare the changes."
            ),
            "checkability": "numerical",
            "reason": (
                "The design depends on the change comparison differing from the rate comparison."
            ),
        },
    }
    selection = judge_selection_from_payload(
        payload,
        {0},
        require_prior_contrast=True,
    )
    assert selection is not None
    winner = selected_candidate([skeleton], selection)[0]
    assert winner.prior_contrast is not None
    assert winner.prior_contrast.approach_id == "compare_differences"
    assert winner.to_dict()["prior_contrast"]["checkability"] == "numerical"

    with pytest.raises(ValueError, match="missing prior_contrast"):
        judge_selection_from_payload(
            {key: value for key, value in payload.items() if key != "prior_contrast"},
            {0},
            require_prior_contrast=True,
        )
    with pytest.raises(ValueError, match="compact-selection recommended_id"):
        judge_selection_from_payload(
            {key: value for key, value in payload.items() if key != "recommended_id"},
            {0},
            require_prior_contrast=True,
        )

    bad = {**payload, "prior_contrast": {**payload["prior_contrast"], "approach_id": "missing"}}
    with pytest.raises(ValueError, match="unknown approach"):
        selected_candidate(
            [skeleton],
            judge_selection_from_payload(bad, {0}),
        )


def test_compact_selection_carries_opposite_equal_contrast_outcomes():
    skeleton = skeleton_from_payload(
        _payload(
            approaches=[
                {
                    "id": "steady_additive_steps",
                    "resources": ["Addition"],
                    "procedure": "Compare each consecutive increase in makes.",
                    "why_plausible": "The attempts have equal steps.",
                }
            ]
        )
    )
    payload = {
        "recommended_id": 0,
        "approaches": ["Compare consecutive increases in makes."],
        "reason": "The additive pattern is tempting but may not settle proportionality.",
        "main_concern": None,
        "number_requirements": [],
        "prior_contrast": {
            "approach_id": "steady_additive_steps",
            "operational_move": "Compare both consecutive increases in makes.",
            "checkability": "numerical",
            "reason": "The selected design contrasts equal changes with unequal unit rates.",
            "expected_target_equal": False,
            "expected_prior_equal": True,
        },
    }

    selection = judge_selection_from_payload(payload, {0}, require_prior_contrast=True)
    assert selection is not None
    winner = selected_candidate([skeleton], selection)[0]
    assert winner.prior_contrast is not None
    assert winner.prior_contrast.expected_target_equal is False
    assert winner.prior_contrast.expected_prior_equal is True
    assert winner.to_dict()["prior_contrast"]["expected_prior_equal"] is True

    same_outcomes = {
        **payload,
        "prior_contrast": {
            **payload["prior_contrast"],
            "expected_prior_equal": False,
        },
    }
    with pytest.raises(ValueError, match="outcomes must differ"):
        judge_selection_from_payload(same_outcomes, {0}, require_prior_contrast=True)


def test_ranking_rejects_practice_items_and_ranks_activation():
    skeletons = [
        skeleton_from_payload(_payload()),
        skeleton_from_payload(_payload(question="Find the missing part of a given ratio.")),
    ]
    verdicts = verdicts_from_payload(_verdicts_payload(), PRIOR_METHODS)
    requirements = number_requirements_from_payload(
        {
            "candidates": [
                {
                    "id": 0,
                    "number_requirements": [
                        {
                            "condition": "The means match.",
                            "purpose": "Mean alone should not decide.",
                        }
                    ],
                },
                {"id": 1, "number_requirements": []},
            ]
        }
    )
    judged = rank_candidates(skeletons, verdicts, requirements)

    assert judged[0].candidate_id == 0
    assert judged[0].activation_count == 3
    assert judged[0].number_requirements[0].condition == "The means match."
    assert not judged[0].practice_item
    assert judged[0].accepted
    assert judged[1].practice_item
    assert not judged[1].accepted

    winners = best_candidates(judged)
    assert [c.candidate_id for c in winners] == [0]


def test_target_named_is_rejected():
    skeletons = [skeleton_from_payload(_payload())]
    verdicts = {
        0: (
            True,  # target_named
            verdicts_from_payload(_verdicts_payload(), PRIOR_METHODS)[0][1],
        )
    }
    judged = rank_candidates(skeletons, verdicts)
    assert judged[0].target_named
    assert not judged[0].accepted
    assert best_candidates(judged) == []


def test_best_candidates_empty_when_all_practice_or_none_activate():
    skeleton = skeleton_from_payload(_payload())
    verdicts = {0: (False, verdicts_from_payload(_verdicts_payload(), PRIOR_METHODS)[1][1])}
    judged = rank_candidates([skeleton], verdicts)
    assert best_candidates(judged) == []


def test_skeleton_preserves_typed_quantities_and_approaches():
    skeleton = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "segment_distances",
                    "role": "list",
                    "description": "distances for each segment",
                    "value_source": "given",
                    "unit": "km",
                    "list_length": 2,
                },
                {
                    "name": "overall_rate",
                    "role": "unknown",
                    "description": "rate for the whole journey",
                    "value_source": "derived",
                    "unit": "km/h",
                },
            ],
            "question": "Which journey is faster overall?",
            "approaches": [
                {
                    "id": "part_rate_mean",
                    "resources": ["Ratio and proportion"],
                    "procedure": "Compare each segment rate and average those rates.",
                    "why_plausible": "Each segment supplies a distance and time pair.",
                    "anticipated_limitation": "The segment rates are not equally weighted.",
                }
            ],
        }
    )
    assert skeleton.quantities[0].value_source == "given"
    assert skeleton.quantities[1].value_source == "derived"
    assert skeleton.quantities[0].list_length == 2
    assert skeleton.approaches[0].id == "part_rate_mean"


def test_historical_skeletons_may_omit_list_length_but_new_proposals_may_not():
    payload = _payload(
        quantities=[
            {
                "name": "scores",
                "role": "list",
                "description": "observed scores",
                "value_source": "given",
            }
        ]
    )
    historical = skeleton_from_payload(payload)
    assert historical.quantities[0].list_length is None
    with pytest.raises(ValueError, match="fixed.*list_length"):
        skeleton_from_proposal_payload(payload)


def test_new_proposals_validate_value_domain_and_fixed_list_length():
    skeleton = skeleton_from_proposal_payload(
        _payload(
            quantities=[
                {
                    "name": "counts",
                    "role": "list",
                    "description": "counts by group",
                    "value_source": "given",
                    "list_length": 3,
                    "value_domain": "positive_integer",
                }
            ],
            approaches=[
                {
                    "id": "count_groups",
                    "resources": ["Counting"],
                    "procedure": "Compare the group counts.",
                    "why_plausible": "Students can count each group.",
                }
            ],
        )
    )
    assert skeleton.quantities[0].value_domain == "positive_integer"
    bad = _payload(
        quantities=[
            {
                "name": "counts",
                "role": "count",
                "description": "number of items",
                "value_domain": "integer",
            }
        ],
        approaches=[
            {
                "id": "count",
                "resources": ["Counting"],
                "procedure": "Count the items.",
                "why_plausible": "Counting is familiar.",
            }
        ],
    )
    with pytest.raises(ValueError, match="value_domain"):
        skeleton_from_proposal_payload(bad)

    missing_domain = _payload(
        quantities=[
            {
                "name": "amount",
                "role": "amount",
                "description": "an amount",
                "value_source": "given",
            }
        ],
        approaches=[
            {
                "id": "amount",
                "resources": ["Comparison"],
                "procedure": "Compare the amount.",
                "why_plausible": "The amount is visible.",
            }
        ],
    )
    with pytest.raises(ValueError, match="value_domain metadata"):
        skeleton_from_payload(missing_domain, require_complete_metadata=True)


def test_new_proposals_allow_absent_list_length_on_derived_scalar():
    skeleton = skeleton_from_proposal_payload(
        _payload(
            quantities=[
                {
                    "name": "parts",
                    "role": "list",
                    "description": "parts in the ratio",
                    "value_source": "given",
                    "list_length": 2,
                    "value_domain": "positive_integer",
                },
                {
                    "name": "combined_parts",
                    "role": "whole",
                    "description": "combined number of parts",
                    "value_source": "derived",
                    "list_length": None,
                    "value_domain": "positive_integer",
                },
            ],
            approaches=[
                {
                    "id": "combine",
                    "resources": ["Equivalent ratios"],
                    "procedure": "Combine the parts.",
                    "why_plausible": "The parts form one whole.",
                }
            ],
        )
    )
    assert skeleton.quantities[1].list_length is None


@pytest.mark.parametrize("list_length", [0, 1])
def test_new_proposals_reject_scalar_list_length_metadata(list_length):
    payload = _payload(
        quantities=[
            {
                "name": "combined_parts",
                "role": "whole",
                "description": "combined number of parts",
                "value_source": "derived",
                "list_length": list_length,
                "value_domain": "positive_integer",
            }
        ],
        approaches=[
            {
                "id": "combine",
                "resources": ["Equivalent ratios"],
                "procedure": "Combine the parts.",
                "why_plausible": "The parts form one whole.",
            }
        ],
    )
    with pytest.raises(ValueError, match="list_length"):
        skeleton_from_proposal_payload(payload)


@pytest.mark.parametrize("invalid_domain", [None, "", False, 0])
def test_fresh_given_domain_must_be_an_allowed_string(invalid_domain):
    payload = _payload(
        quantities=[
            {
                "name": "amount",
                "role": "amount",
                "description": "an amount",
                "value_source": "given",
                "value_domain": invalid_domain,
            }
        ],
        approaches=[
            {
                "id": "compare",
                "resources": ["Comparison"],
                "procedure": "Compare the amount.",
                "why_plausible": "The amount is visible.",
            }
        ],
    )
    with pytest.raises(ValueError, match="value_domain"):
        skeleton_from_proposal_payload(payload)


def test_fresh_proposals_reject_malformed_requirements_and_missing_approaches():
    valid_quantity = [
        {
            "name": "amount",
            "role": "amount",
            "description": "an amount",
            "value_source": "given",
            "value_domain": "positive",
        }
    ]
    for malformed in ({"condition": "not a string"}, "not a list"):
        with pytest.raises(ValueError, match="number_constraints"):
            skeleton_from_proposal_payload(
                _payload(
                    quantities=valid_quantity,
                    number_constraints=malformed,
                    approaches=[
                        {
                            "id": "compare",
                            "resources": ["Comparison"],
                            "procedure": "Compare the amount.",
                            "why_plausible": "The amount is visible.",
                        }
                    ],
                )
            )

    with pytest.raises(ValueError, match="non-empty approaches"):
        skeleton_from_proposal_payload(
            _payload(quantities=valid_quantity, prior_resources=[{"resource": "Comparison"}])
        )


def test_legacy_parser_keeps_permissive_requirement_and_approach_fallbacks():
    skeleton = skeleton_from_payload(
        _payload(
            number_constraints={"condition": "not a string"},
            prior_resources=[{"resource": "Comparison"}],
        )
    )
    assert skeleton.number_constraints == ()
    assert len(skeleton.approaches) == 1


def test_math_plan_requires_prior_labels_to_match_answer_rule():
    skeleton = skeleton_from_payload(_payload())
    with pytest.raises(ValueError, match="labels"):
        MathPlan.from_payload(
            {
                "target": {"expressions": {"A": "remaining_distance"}},
                "priors": [
                    {
                        "name": "prior",
                        "approach_id": "approach_one",
                        "expressions": {"B": "remaining_distance"},
                    }
                ],
                "answer_rule": {
                    "kind": "scalar",
                    "labels": ["A"],
                },
            },
            skeleton.quantities,
            approach_ids={"approach_one"},
        )


def test_successful_prior_route_is_not_a_routine_item_without_direct_routine_flag():
    skeletons = [skeleton_from_payload(_payload())]
    verdicts = {
        0: (
            False,
            (
                MethodVerdict(
                    method=PRIOR_METHODS[0],
                    can_start=True,
                    settles_question=True,
                    direct_routine=False,
                    approach_ids=("exploratory_route",),
                ),
                *(
                    MethodVerdict(
                        method=method,
                        can_start=False,
                        settles_question=False,
                        direct_routine=False,
                        approach_ids=(),
                    )
                    for method in PRIOR_METHODS[1:]
                ),
            ),
        )
    }
    judged = rank_candidates(skeletons, verdicts)
    assert not judged[0].practice_item
    assert judged[0].accepted


def test_non_numerical_prior_cannot_hide_formula_text():
    skeleton = skeleton_from_payload(_payload())
    with pytest.raises(ValueError, match="empty expressions"):
        MathPlan.from_payload(
            {
                "target": {"expressions": {"A": "remaining_distance"}},
                "priors": [
                    {
                        "name": "drawing",
                        "approach_id": "approach_one",
                        "checkability": "qualitative",
                        "expressions": {"A": "remaining_distance"},
                    }
                ],
                "answer_rule": {"kind": "scalar", "labels": ["A"]},
            },
            skeleton.quantities,
            approach_ids={"approach_one"},
        )
