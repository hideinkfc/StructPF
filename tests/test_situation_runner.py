import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import scripts.run_situation_skeletons as runner
from scripts.learning_commons_context import record_selection, retrieve_context
from src.generation.situation_skeletons import (
    ConstraintSpec,
    JudgeSelection,
    MathPlan,
    NumberRequirement,
    PriorContrastIntent,
    selected_candidate,
    skeleton_from_payload,
    skeleton_schema_contract,
)


def _skeleton():
    return skeleton_from_payload(
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
            "approaches": [
                {
                    "id": "compare_parts",
                    "resources": ["Ratio"],
                    "procedure": "Compare the two amounts directly.",
                    "why_plausible": "Both amounts are visible.",
                    "anticipated_limitation": (
                        "The intended comparison may require a different rule."
                    ),
                }
            ],
        }
    )


def _plan(skeleton):
    return MathPlan.from_payload(
        {
            "target": {"name": "target", "expressions": {"A": "a", "B": "b"}},
            "priors": [
                {
                    "name": "prior",
                    "approach_id": "compare_parts",
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
        },
        skeleton.quantities,
        approach_ids={"compare_parts"},
    )


def test_d1_loader_selects_case_and_condition_and_preserves_context(tmp_path):
    path = tmp_path / "d1.json"
    path.write_text(
        """
        {
          "records": [
            {
              "case_id": "case-a",
              "conditions": {
                "grounded": {
                  "condition": "grounded",
                  "recommendations": [
                    {
                      "resource": "Ratio",
                      "taught_as": "compare quantities",
                      "student_move": "form a ratio",
                      "falls_short_because": "does not answer the whole question",
                      "evidence_ids": ["curriculum:p1"],
                      "provenance": {"source": "syllabus", "page": 2}
                    }
                  ]
                },
                "ungrounded": {
                  "condition": "ungrounded",
                  "recommendations": [
                    {"resource": "Guessing", "taught_as": "try values"}
                  ]
                }
              }
            }
          ]
        }
        """
    )
    context = runner._prior_context_from_d1(path, "case-a", "grounded")
    assert context["condition"] == "grounded"
    assert context["recommendations"][0]["taught_as"] == "compare quantities"
    assert context["recommendations"][0]["evidence_ids"] == ["curriculum:p1"]


def test_d1_loader_rejects_ambiguous_case(tmp_path):
    path = tmp_path / "d1.json"
    path.write_text('{"records": [{"case_id": "case-a"}, {"case_id": "case-a"}]}')
    with pytest.raises(ValueError, match="exactly one"):
        runner._prior_context_from_d1(path, "case-a")


def _mathematical_context(tmp_path):
    client = Mock()
    client.search_standards.return_value = [
        {
            "caseIdentifierUUID": f"saved-id-{rank}",
            "statementCode": f"CODE-{rank}",
            "description": description,
            "author": "Test author",
            "provider": "Learning Commons",
            "jurisdiction": "Multi-State",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "attributionStatement": "Test attribution",
        }
        for rank, description in enumerate(
            ["Selected mathematical text", "Unselected mathematical text"], 1
        )
    ]
    context = retrieve_context(
        {"topic": "ratio", "subject": "mathematics"}, client=client, cache_dir=tmp_path
    )
    record_selection(context, {"selected_sources": ["S1"]})
    return context


def test_d1_loader_keeps_selected_reference_context_separate(tmp_path):
    context = _mathematical_context(tmp_path / "cache")
    path = tmp_path / "d1.json"
    path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "case_id": "case-a",
                        "condition": "ungrounded",
                        "result": {
                            "condition": "ungrounded",
                            "recommendations": [
                                {"resource": "Ratio", "taught_as": "Compare quantities"}
                            ],
                            "learning_commons": context,
                        },
                    }
                ],
            }
        )
    )
    loaded = runner._prior_context_from_d1(path, "case-a", "ungrounded")
    assert loaded["learning_commons"] == context
    assert runner._method_names(loaded) == ["Ratio"]
    rendered = runner._format_prior_context(loaded)
    assert "Selected mathematical text" in rendered
    assert "Unselected mathematical text" not in rendered
    assert "saved-id-" not in rendered
    assert "not assumed prior knowledge" in rendered


def test_selected_references_reach_design_plan_fill_writer_and_replay(tmp_path, monkeypatch):
    import scripts.replay_pf_writer as replay

    context = {
        "recommendations": [{"resource": "Ratio", "taught_as": "Compare quantities"}],
        "learning_commons": _mathematical_context(tmp_path),
    }
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)
    case = {"target_concept": "comparison", "topic": "ratio", "grade": 7, "subject": "math"}
    prompts = runner._prompts()
    requests = []

    def fake_chat(_client, _model, system, user, **kwargs):
        requests.append(user)
        if system.startswith("Design one"):
            return skeleton.to_dict(), "proposal"
        return {
            "status": "ready",
            "blocking_issues": [],
            "title": "Task",
            "body": "Compare the quantities.",
            "question": "Explain.",
        }, "response"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    runner._propose_one(None, "model", prompts, case, context)
    plan_request = runner._plan_request(prompts, case, winner, context)
    assert "Selected mathematical text" in plan_request["user"]
    runner._fill_winner(None, "model", prompts, case, winner, plan, context)
    writer = runner._writer_context(case, context, winner, plan, {"values": {"a": 2, "b": 3}}, None)
    assert "mathematical_references" not in writer["student_context"]
    assert writer["mathematical_references"][0]["source_label"] == "S1"
    runner._write_task(
        None, "model", prompts, case, winner, plan, {"values": {"a": 2, "b": 3}}, context, None
    )
    for request in requests:
        assert "Selected mathematical text" in request
        assert "Unselected mathematical text" not in request
        assert "saved-id-" not in request
    recovered = replay._original_context({"started": {"user_prompt": requests[-1]}})
    replay._assert_context_unchanged(writer, recovered)
    altered = {**writer, "mathematical_references": []}
    with pytest.raises(ValueError, match="mathematical_references"):
        replay._assert_context_unchanged(altered, recovered)


def test_empty_reference_selection_does_not_change_baseline_context(tmp_path):
    references = _mathematical_context(tmp_path)
    record_selection(references, {"selected_sources": []})
    baseline = {"recommendations": [{"resource": "Ratio"}]}
    assert runner._format_prior_context(
        {
            **baseline,
            "learning_commons": references,
        }
    ) == runner._format_prior_context(baseline)
    case = {"target_concept": "comparison", "grade": 7}
    winner = SimpleNamespace(skeleton=_skeleton())
    writer = runner._writer_context(
        case,
        {**baseline, "learning_commons": references},
        winner,
        _plan(winner.skeleton),
        {"values": {}},
        None,
    )
    assert "mathematical_references" not in writer


def test_render_does_not_reinterpret_reference_text_as_template_values():
    rendered = runner._render(
        "{prior_context}\n{fill_feedback}",
        {"prior_context": "Source literally says {fill_feedback}", "fill_feedback": "Next fill"},
    )
    assert rendered == "Source literally says {fill_feedback}\nNext fill"


def test_proposal_and_selection_receive_the_authoritative_checker_contract(monkeypatch):
    proposal = {
        "quantities": [
            {
                "name": "amount",
                "role": "amount",
                "description": "an amount",
                "value_source": "given",
                "value_domain": "positive",
            }
        ],
        "question": "How should the amount be compared?",
        "approaches": [
            {
                "id": "compare",
                "resources": ["Comparison"],
                "procedure": "Compare the amount with a reference.",
                "why_plausible": "The amount is directly available.",
            }
        ],
    }
    selection = {
        "recommended_id": 0,
        "approaches": ["Compare the amount with a reference."],
        "reason": "The comparison remains open.",
        "main_concern": None,
        "prior_contrast": None,
        "number_requirements": [],
    }
    captured = []
    responses = iter([(proposal, "proposal"), (selection, "selection")])

    def fake_chat(*args, **kwargs):
        captured.append({"system": args[2], "user": args[3]})
        return next(responses)

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    prompts = runner._prompts()
    record = runner._propose_one(
        None,
        "model",
        prompts,
        {"target_concept": "comparison", "topic": "number", "grade": 7, "subject": "math"},
        {"recommendations": [{"resource": "Comparison"}]},
    )
    assert "skeleton_obj" in record
    runner._judge_all(
        None,
        "model",
        prompts,
        {"target_concept": "comparison", "topic": "number", "grade": 7},
        {"recommendations": [{"resource": "Comparison"}]},
        [record["skeleton_obj"]],
    )
    contract = runner.checker_capability_contract()
    schema_contract = skeleton_schema_contract()
    assert contract in captured[0]["system"]
    assert contract in captured[1]["system"]
    assert schema_contract in captured[0]["system"]
    for stage in captured[:2]:
        system = stage["system"]
        assert "FUTURE numerical planning" in system
        assert "math-plan/v2 fields or frozen formulas" in system
        assert "absence" in system and "not a rejection reason" in system
        assert "representability" in system and "schema completeness" in system
    assert "prior_contrast" in captured[1]["user"]
    assert "operational_move" in captured[1]["user"]


def test_repair_prompts_render_authoritative_schema_contract(monkeypatch):
    winner, plan, _ = _consistency_example()
    captured = []
    repaired = {"skeleton": winner.skeleton.to_dict(), "math_plan": plan.to_dict()}

    def fake_chat(*args, **kwargs):
        captured.append({"system": args[2], "user": args[3]})
        return repaired, "repair"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    runner._joint_repair(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability"},
        winner,
        plan,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        {"route": "design", "reason": "repair the question"},
    )
    schema_contract = skeleton_schema_contract()
    assert schema_contract in captured[0]["system"]
    assert "preserve every original quantity name" in captured[0]["system"]
    assert "math-plan/v2" in captured[0]["system"]
    assert '"constraints"' in captured[0]["system"]


def test_plan_and_review_receive_the_same_authoritative_checker_contract(monkeypatch):
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)
    contract = runner.checker_capability_contract()
    plan_request = runner._plan_request(
        {
            "PLAN_SKELETON_SYSTEM": "{checker_contract}",
            "PLAN_SKELETON_USER": "{checker_contract}",
        },
        {"target_concept": "comparison"},
        winner,
        {"recommendations": [{"resource": "Comparison"}]},
    )
    assert plan_request["system"] == contract
    assert plan_request["user"] == contract

    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "pass",
                "distinct_approaches": True,
                "constraints_covered": True,
                "issues": [],
            },
            "review",
        ),
    )
    _, _, review_request = runner._review_plan(
        None,
        "model",
        {
            "REVIEW_PLAN_SYSTEM": "{checker_contract}",
            "REVIEW_PLAN_USER": "{checker_contract}",
        },
        {"target_concept": "comparison"},
        winner,
        plan,
    )
    assert review_request["system"] == contract
    assert review_request["user"] == contract


def test_proposal_repair_prompt_renders_authoritative_schema_contract(monkeypatch):
    invalid_proposal = {
        "quantities": [
            {
                "name": "amount",
                "role": "amount",
                "description": "an amount",
                "value_source": "invalid_source",
                "value_domain": "positive",
            }
        ],
        "question": "How should the amount be compared?",
        "approaches": [
            {
                "id": "compare",
                "resources": ["Comparison"],
                "procedure": "Compare the amount with a reference.",
                "why_plausible": "The amount is directly available.",
            }
        ],
        "number_constraints": ["The amount is positive."],
    }
    repaired_proposal = {
        **invalid_proposal,
        "quantities": [{**invalid_proposal["quantities"][0], "value_source": "given"}],
    }
    captured = []
    responses = [(invalid_proposal, "invalid metadata"), (repaired_proposal, "repaired")]

    def fake_chat(*args, **kwargs):
        captured.append({"system": args[2], "user": args[3]})
        return responses.pop(0)

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    record = runner._propose_one(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "comparison", "topic": "number", "grade": 7, "subject": "math"},
        {"recommendations": [{"resource": "Comparison"}]},
    )
    assert "skeleton_obj" in record
    assert len(captured) == 2
    assert skeleton_schema_contract() in captured[1]["system"]
    assert "correct that diagnosed field" in captured[1]["system"]
    assert '"value_source"' in captured[1]["user"]
    assert "invalid_source" in captured[1]["user"]


def test_saved_winner_loader_validates_root_case_provenance(tmp_path):
    path = tmp_path / "saved.json"
    path.write_text('{"case_id": "case-a", "case_input": {"id": "case-b"}}')
    with pytest.raises(ValueError, match="disagrees"):
        runner._winner_from_result(path, "case-a")


def test_saved_case_input_is_loaded_without_mixing_current_config(tmp_path):
    path = tmp_path / "saved.json"
    path.write_text(
        json.dumps(
            {
                "case_id": "case-a",
                "case_input": {"id": "case-a", "grade": 7, "target_concept": "old"},
            }
        )
    )
    assert runner._stored_case_input(path, "case-a")["target_concept"] == "old"


def test_replan_flag_is_rejected_before_loading_case_or_client(monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_situation_skeletons.py", "--case", "case-a", "--replan"],
    )
    monkeypatch.setattr(
        runner,
        "_load_case",
        lambda _: pytest.fail("flag validation must precede case loading"),
    )
    monkeypatch.setattr(
        runner,
        "load_client",
        lambda _: pytest.fail("flag validation must precede client loading"),
    )
    with pytest.raises(ValueError, match="requires --from-result"):
        runner.main()


def test_fill_retries_values_without_accepting_plan_changes(monkeypatch):
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)
    responses = iter(
        [
            ({"values": {"a": 1, "b": 5}}, "bad values", {}),
            ({"values": {"a": 4, "b": 5}}, "valid values", {}),
        ]
    )

    def fake_fill(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(runner, "_fill_winner", fake_fill)
    result = runner._fill_until_accepted(
        None,
        "model",
        {},
        {"target_concept": "comparison", "grade": 7},
        winner,
        plan,
        {"recommendations": [{"resource": "Ratio"}]},
    )
    assert result["accepted"]
    assert len(result["attempts"]) == 2
    assert result["payload"] == {"values": {"a": 4, "b": 5}}
    assert "agrees" in result["attempts"][0]["check"]["reason"]


def test_fill_stops_for_a_response_that_changes_the_frozen_plan(monkeypatch):
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)

    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *args, **kwargs: (
            {"values": {"a": 4, "b": 5}, "target": {"expressions": {}}},
            "changed plan",
            {},
        ),
    )
    result = runner._fill_until_accepted(
        None,
        "model",
        {},
        {"target_concept": "comparison", "grade": 7},
        winner,
        plan,
        {"recommendations": [{"resource": "Ratio"}]},
    )
    assert not result["accepted"]
    assert result["check"]["status"] == "needs_review"
    assert len(result["attempts"]) == 1


def test_plan_review_requires_meaning_and_constraint_flags(monkeypatch):
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)
    prompts = {
        "REVIEW_PLAN_SYSTEM": "review {question}",
        "REVIEW_PLAN_USER": "plan {math_plan}",
    }
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "pass",
                "question_answer_alignment": "aligned",
                "approach_formula_alignment": "aligned",
                "distinct_approaches": True,
                "constraints_covered": True,
                "issues": [],
            },
            "raw review",
        ),
    )
    review, raw, request = runner._review_plan(
        None,
        "model",
        prompts,
        {"target_concept": "comparison"},
        winner,
        plan,
    )
    assert runner._review_passes(review)
    assert raw == "raw review"
    assert request["system"] == "review Which amount is larger?"


@pytest.mark.parametrize("bad_status", [[], {}])
def test_plan_review_malformed_status_is_explicit_invalid_review(monkeypatch, bad_status):
    skeleton = _skeleton()
    winner = SimpleNamespace(skeleton=skeleton)
    plan = _plan(skeleton)
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: ({"status": bad_status}, "raw review"),
    )
    review, _, _ = runner._review_plan(
        None,
        "model",
        {"REVIEW_PLAN_SYSTEM": "review", "REVIEW_PLAN_USER": "plan"},
        {"target_concept": "comparison"},
        winner,
        plan,
    )
    assert review["status"] == "unknown"
    assert review["retryable"] is True
    assert runner._review_retryable(review)


def test_writer_receives_complete_context_and_preserves_fixed_design(monkeypatch):
    winner, plan, review = _consistency_example()
    prompts = runner._prompts()
    case = {
        "target_concept": "Variability as a measure of spread",
        "grade": 7,
        "subject": "mathematics",
        "topic": "data",
        "jurisdiction": "test curriculum",
    }
    prior_context = {
        "recommendations": [
            {
                "resource": "Mean",
                "taught_as": "summarize scores",
                "student_move": "calculate an average",
                "falls_short_because": "does not describe spread",
                "evidence_ids": ["curriculum:mean"],
            }
        ]
    }
    fill = {"values": {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}}
    response = {
        "status": "ready",
        "blocking_issues": [],
        "title": "Comparing performances",
        "body": "Develop and justify a comparison.",
        "question": "How can you compare the performances?",
    }
    captured = {}

    def fake_chat(client, model, system, user, **kwargs):
        captured["system"] = system
        captured["user"] = user
        return response, "raw writer response"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    task, raw = runner._write_task(
        None, "model", prompts, case, winner, plan, fill, prior_context, review
    )

    assert task == response
    assert raw == "raw writer response"
    assert "Variability as a measure of spread" in captured["user"]
    assert '"grade": "7"' in captured["user"]
    assert '"resource": "Mean"' in captured["user"]
    assert '"scores_a": [\n      4,\n      6,\n      6,\n      8\n    ]' in captured["user"]
    assert "Comparing plots with matching summaries" in captured["user"]
    assert "The concentration difference must be visible" in captured["user"]
    assert '"answer_rule"' in captured["user"]
    assert "teacher-facing solutions" in captured["system"]
    assert "{task_design}" not in captured["user"]


def test_writer_context_includes_full_structured_approaches():
    winner, plan, review = _consistency_example()
    context = runner._writer_context(
        {"target_concept": "Variability", "grade": 7},
        {"recommendations": []},
        winner,
        plan,
        {"values": {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}},
        review,
    )
    assert context["approaches"][0]["id"] == "mean"
    assert context["approaches"][1]["procedure"].startswith("Plot")


def test_intended_student_output_invites_comparison_without_prescribing_method():
    winner, plan, _ = _consistency_example()
    output = runner._intended_student_output(winner, plan)

    assert "different solution approaches or representations" in output["student_work"]
    assert "When useful for this design" in output["student_work"]
    assert "show how you worked" in output["student_work"]
    assert "explain why your approach" in output["student_work"]
    assert "partial" not in output["student_work"].lower()
    assert "unfinished" not in output["student_work"].lower()
    assert "Do not require students to be wrong" in output["student_work"]
    assert "invent a second method" in output["student_work"]
    assert output["question"] == winner.skeleton.question
    assert output["answer_rule"] == plan.answer_rule.to_dict()
    assert "anticipated equality, winner, or target procedure" in output["exploration_guidance"]
    assert "selected operational prior move" in output["exploration_guidance"]


def test_writer_prompt_contract_applies_three_writing_rules_and_fixed_design_safeguards():
    prompts = runner._prompts()
    system = prompts["WRITE_TASK_SYSTEM"]

    assert "Use plain, precise language" in system
    assert "Make the goal clear; leave the method open" in system
    assert "Ask students to show and explain their thinking" in system
    assert "Briefly clarify task terms" in system
    assert "who or what each condition or competing claim applies to" in " ".join(system.split())
    assert "announce why an anticipated student approach will fail" in system
    assert "selected operational prior move" in system
    assert "not as a compulsory extra task" in " ".join(system.split())
    assert "partial" not in system.lower()
    assert "unfinished" not in system.lower()
    assert "Never require students to be wrong" in system
    assert "invent a second method" in system
    assert "anticipated equality, winner, or" in system
    assert "target procedure before students explore" in system
    assert "Preserve the numbers, units, relationships, assumptions, scope, requested" in system
    assert "silently remove a genuinely required competing method or subquestion" in system
    assert "Helpful representation suggestions are allowed, not required" in system
    assert "The body and question are displayed together" in system
    assert "restated" not in prompts["WRITE_TASK_USER"]


def test_writer_prompt_does_not_disclose_multiplicative_target_by_default():
    system = " ".join(runner._prompts()["WRITE_TASK_SYSTEM"].split())

    assert (
        "Keep the student goal meaningful and method-open, while making the factual "
        "question no broader than the property checked by the target answer_rule"
    ) in system
    assert "Scope the decision using a familiar contextual quantity or property" in system
    assert "Do not prescribe the computation or reveal a target-method sequence" in system
    assert (
        "Keep the exact target relationship in the teacher-facing target, "
        "expressions, and answer_rule"
    ) in system
    assert 'Never replace missing scope with an unqualified "constant rule"' in system


def test_proposal_selection_and_review_prompts_keep_target_and_contrast_claims_consistent():
    prompts = runner._prompts()
    proposal = " ".join(prompts["PROPOSE_SKELETON_SYSTEM"].split())
    selector = " ".join(prompts["JUDGE_SKELETONS_SYSTEM"].split())
    reviewer = " ".join(prompts["REVIEW_PLAN_SYSTEM"].split())
    writer = " ".join(prompts["WRITE_TASK_SYSTEM"].split())

    assert "Do not reveal the target formula, algorithm, or answer in the question" in proposal
    assert (
        'Do not ask whether an unspecified "constant rule" fits: it does not identify '
        "which property is meant"
    ) in proposal
    assert (
        "Keep the exact mathematical relationship in the teacher-facing target and "
        "mathematical plan/answer_rule"
    ) in proposal
    assert "Name the class of relationship precisely in the question" not in proposal
    assert (
        "A prior move is central when the selection reason, main_concern, or a number requirement"
    ) in selector
    assert "If central, prior_contrast must be an object" in selector
    assert (
        "If no one move is central, use null and do not claim in the reason or main_concern"
    ) in selector
    assert ("is the selection rationale consistent with its selected prior_contrast?") in reviewer
    assert (
        "Report an inconsistency rather than silently converting prose into a checked path"
    ) in reviewer
    assert "Do not prescribe the computation or reveal a target-method sequence" in writer
    assert (
        "Keep the exact target relationship in the teacher-facing target, expressions, "
        "and answer_rule"
    ) in writer


def test_prompt_contract_scopes_checked_property_and_numeric_change_contrasts():
    prompts = runner._prompts()
    proposal = " ".join(prompts["PROPOSE_SKELETON_SYSTEM"].split())
    selector = " ".join(prompts["JUDGE_SKELETONS_SYSTEM"].split())
    planner = " ".join(prompts["PLAN_SKELETON_SYSTEM"].split())
    reviewer = " ".join(prompts["REVIEW_PLAN_SYSTEM"].split())
    writer = " ".join(prompts["WRITE_TASK_SYSTEM"].split())

    assert 'unqualified "one rule" or "prediction rule" is too broad' in proposal
    assert "same made-shots-per-attempt pace describes all listed records" in proposal
    assert "These phrases specify what claim is being judged, not how to calculate it" in proposal
    assert "supplied D1/prior context supports a concrete familiar operation" in proposal
    assert "plausible but incomplete starting conclusion" in proposal
    assert "For this particular contrast, do not require the first two rates to match" in proposal
    assert "equal increments alone do not imply equal ratios" in proposal
    assert "Do not call an exact arithmetic comparison qualitative" in selector
    assert "at least three ordered paired rows" in selector
    assert "equal consecutive input steps" in selector
    assert "two or more adjacent output changes" in selector
    assert "include the needed equal-input-step condition in number_requirements" in selector
    assert "Reject a candidate with incompatible fixed conditions" in selector
    assert "do not force prior contrasts into otherwise valid tasks" in selector
    assert "preserve that requirement as an exact constraint" in planner
    assert "a semantic counterexample test" in reviewer
    assert "other functions can fit finite points" in reviewer
    assert "reject the scope mismatch" in reviewer
    assert "Scope the decision using a familiar contextual" in writer
    assert "without telling students how to compute it" in writer


def test_shared_plan_retry_revalidates_and_keeps_winner(monkeypatch):
    winner, _, review = _consistency_example()
    valid_payload = {
        "schema_version": "math-plan/v2",
        "target": {
            "name": "variance",
            "unit": "points squared",
            "expressions": {"A": "scores_a[0]", "B": "scores_b[0]"},
        },
        "answer_rule": {"kind": "smallest", "labels": ["A", "B"], "unit": "points squared"},
        "constraints": [],
    }
    responses = iter([({"schema_version": "math-plan/v9"}, "bad"), (valid_payload, "good")])
    calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args: calls.append(args[4]) or next(responses),
    )
    monkeypatch.setattr(
        runner,
        "_review_plan",
        lambda *args: (
            {
                "status": "pass",
                "distinct_approaches": True,
                "constraints_covered": True,
                "requirement_coverage": [],
                "issues": [],
            },
            "review",
            {"system": "s", "user": "u"},
        ),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "variance", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}]},
    )
    assert result["plan"].schema_version == "math-plan/v2"
    assert len(result["attempts"]) == 2
    assert [attempt["stage"] for attempt in result["attempts"]] == ["structure", "accepted"]
    assert calls[0] is winner and calls[1] is winner


def test_review_coverage_revise_gets_one_real_correction(monkeypatch):
    winner, _, _ = _consistency_example()
    winner = replace(
        winner,
        skeleton=replace(winner.skeleton, number_constraints=()),
        number_requirements=(NumberRequirement("A must exceed B.", "separate the outcomes"),),
    )
    first = {
        "schema_version": "math-plan/v2",
        "target": {"expressions": {"A": "scores_a[0]", "B": "scores_b[0]"}},
        "answer_rule": {"kind": "largest", "labels": ["A", "B"]},
        "constraints": [],
    }
    second = {
        **first,
        "constraints": [{"left": "scores_a[0]", "operator": ">", "right": "scores_b[0]"}],
    }
    plans = iter([(first, "first"), (second, "second")])
    reviews = iter(
        [
            {
                "status": "revise",
                "distinct_approaches": True,
                "constraints_covered": False,
                "requirement_coverage": [],
                "issues": ["Missing a > b; add it"],
            },
            {
                "status": "pass",
                "distinct_approaches": True,
                "constraints_covered": True,
                "requirement_coverage": [
                    {
                        "requirement_id": "judge_0",
                        "status": "numerical",
                        "constraint_indices": [0],
                        "reason": "The inequality is explicit.",
                    }
                ],
                "issues": [],
            },
        ]
    )
    monkeypatch.setattr(runner, "_plan_winner", lambda *args: next(plans))
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (next(reviews), "review"),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "variance", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}]},
    )
    assert result["plan"] is not None
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["review"]["status"] == "revise"
    assert result["attempts"][1]["stage"] == "accepted"


def test_plan_retry_exhaustion_and_unknown_do_not_loop(monkeypatch):
    winner, _, _ = _consistency_example()
    payload = {
        "schema_version": "math-plan/v2",
        "target": {"expressions": {"A": "scores_a[0]", "B": "scores_b[0]"}},
        "answer_rule": {"kind": "largest", "labels": ["A", "B"]},
        "constraints": [],
    }
    calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args: calls.append(1) or (payload, "plan"),
    )
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "unknown",
                "distinct_approaches": True,
                "constraints_covered": False,
                "requirement_coverage": [],
                "issues": ["insufficient evidence"],
            },
            "review",
        ),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "variance", "grade": 7},
        winner,
        {"recommendations": []},
    )
    assert len(calls) == 1
    assert result["plan"] is None


def test_revise_retry_is_capped_at_one_correction(monkeypatch):
    winner, _, _ = _consistency_example()
    payload = {
        "schema_version": "math-plan/v2",
        "target": {"expressions": {"A": "scores_a[0]", "B": "scores_b[0]"}},
        "answer_rule": {"kind": "largest", "labels": ["A", "B"]},
        "constraints": [],
    }
    calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args: calls.append(1) or (payload, "plan"),
    )
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "revise",
                "distinct_approaches": True,
                "constraints_covered": False,
                "requirement_coverage": [],
                "issues": ["Missing a concrete condition"],
            },
            "review",
        ),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "variance", "grade": 7},
        winner,
        {"recommendations": []},
    )
    assert len(calls) == 2
    assert len(result["attempts"]) == 2
    assert result["plan"] is None


def test_new_generation_rejects_v1_even_when_review_passes(monkeypatch):
    winner, _, _ = _consistency_example()
    # Build a legacy payload explicitly so the test covers the generation gate.
    legacy_payload = {
        "schema_version": "math-plan/v1",
        "target": {"expressions": {"A": "scores_a[0]", "B": "scores_b[0]"}},
        "priors": [
            {
                "name": "mean",
                "approach_id": "mean",
                "expressions": {"A": "scores_a[0]", "B": "scores_b[0]"},
            }
        ],
        "answer_rule": {"kind": "largest", "labels": ["A", "B"]},
        "required_checks": ["at_least_one_prior_disagrees"],
        "constraints": [],
    }
    calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args: calls.append(1) or (legacy_payload, "legacy"),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "variance", "grade": 7},
        winner,
        {"recommendations": []},
    )
    assert result["plan"] is None
    assert len(calls) == 2
    assert "math-plan/v2" in result["error"]


@pytest.mark.parametrize(
    "response, issue",
    [
        (None, "writer response was not valid JSON"),
        (
            {"status": "ready", "blocking_issues": [], "title": "", "body": "", "question": ""},
            "writer title",
        ),
        (
            {"status": "blocked", "blocking_issues": [], "title": "", "body": "", "question": ""},
            "blocked writer task",
        ),
    ],
)
def test_writer_invalid_or_blocked_output_is_not_presented_as_ready(monkeypatch, response, issue):
    winner, plan, review = _consistency_example()
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (response, "raw"))
    task, raw = runner._write_task(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        plan,
        {"values": {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}},
        {"recommendations": []},
        review,
    )
    assert raw == "raw"
    assert task["status"] == "blocked"
    assert any(issue in item for item in task["blocking_issues"])


def _consistency_example():
    skeleton = skeleton_from_payload(
        {
            "quantities": [
                {"name": name, "role": "list", "list_length": 4}
                for name in ("scores_a", "scores_b")
            ],
            "question": "Develop a way to compare how consistent the performances are.",
            "number_constraints": ["The two score lists have the same mean."],
            "approaches": [
                {
                    "id": "mean",
                    "resources": ["Mean"],
                    "procedure": "Calculate each player's average score.",
                    "why_plausible": "Students know how to summarize scores.",
                },
                {
                    "id": "plot",
                    "resources": ["Number-line plots"],
                    "procedure": "Plot the scores and compare their concentration.",
                    "why_plausible": "Students can compare positions on a number line.",
                },
            ],
        }
    )
    selection = JudgeSelection(
        recommended_id=0,
        approaches=tuple(a.procedure for a in skeleton.approaches),
        reason="Comparing plots with matching summaries reveals information the summaries miss.",
        main_concern="The concentration difference must be visible in a small plot.",
        number_requirements=(
            NumberRequirement("The ranges match.", "Extremes alone should not decide."),
            NumberRequirement("The variances differ.", "There is a difference in spread."),
            NumberRequirement(
                "The plots invite a useful comparison.", "Support graphical reasoning."
            ),
        ),
    )
    winner = selected_candidate([skeleton], selection)[0]
    variances = {
        label: "("
        + " + ".join(f"({name}[{i}]-sum({name})/4)*({name}[{i}]-sum({name})/4)" for i in range(4))
        + ")/4"
        for label, name in (("A", "scores_a"), ("B", "scores_b"))
    }
    constraints = [
        {
            "left": "sum(scores_a)/4",
            "operator": "==",
            "right": "sum(scores_b)/4",
            "description": "means match",
        },
        {
            "left": "scores_a[3]-scores_a[0]",
            "operator": "==",
            "right": "scores_b[3]-scores_b[0]",
            "description": "ranges match for sorted lists",
        },
        {
            "left": variances["A"],
            "operator": "!=",
            "right": variances["B"],
            "description": "variances differ",
        },
    ]
    constraints.extend(
        {"left": f"{name}[{i}]", "operator": "<=", "right": f"{name}[{i + 1}]"}
        for name in ("scores_a", "scores_b")
        for i in range(3)
    )
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"name": "variance", "expressions": variances},
            "answer_rule": {"kind": "smallest", "labels": ["A", "B"]},
            "constraints": constraints,
        },
        skeleton.quantities,
    )
    review = {
        "status": "pass",
        "question_answer_alignment": "Variance provides one measure, not the only valid answer.",
        "approach_formula_alignment": "The mean is numerical; the drawing remains qualitative.",
        "distinct_approaches": True,
        "constraints_covered": True,
        "issues": [],
        "requirement_coverage": [
            {
                "requirement_id": requirement_id,
                "status": "numerical",
                "constraint_indices": indices,
                "reason": reason,
            }
            for requirement_id, indices, reason in (
                ("original_0", [0], "The means are constrained equal."),
                ("judge_0", [1, 3, 4, 5, 6, 7, 8], "Sorted endpoints give the equal ranges."),
                ("judge_1", [2], "The variances are constrained unequal."),
            )
        ]
        + [
            {
                "requirement_id": "judge_2",
                "status": "qualitative",
                "constraint_indices": [],
                "reason": "Visual usefulness remains unverified on the eventual values.",
            }
        ],
    }
    return winner, plan, review


def test_runner_requires_plan_to_match_selected_numerical_prior_contrast():
    winner, plan, _ = _consistency_example()
    selected = replace(
        winner,
        prior_contrast=PriorContrastIntent(
            approach_id="mean",
            operational_move="Calculate each score list's mean and compare them.",
            checkability="numerical",
            reason="This move is central to the comparison.",
        ),
    )
    payload = plan.to_dict()
    with pytest.raises(ValueError, match="missing from the math plan"):
        runner._math_plan_from_payload(payload, selected)

    payload["prior_contrast"] = {
        "name": "compare the means",
        "approach_id": "mean",
        "expressions": {
            "A": "sum(scores_a)/4",
            "B": "sum(scores_b)/4",
        },
    }
    parsed = runner._math_plan_from_payload(payload, selected)
    assert parsed.prior_contrast is not None
    assert parsed.prior_contrast.approach_id == "mean"

    payload["prior_contrast"]["approach_id"] = "plot"
    with pytest.raises(ValueError, match="does not match the selected approach_id"):
        runner._math_plan_from_payload(payload, selected)

    with pytest.raises(ValueError, match="not selected in the design"):
        runner._math_plan_from_payload(payload, winner)


def test_runner_generates_and_checks_selected_equal_prior_contrast():
    skeleton = skeleton_from_payload(
        {
            "quantities": [
                {"name": "attempts", "role": "list", "list_length": 3},
                {"name": "makes", "role": "list", "list_length": 3},
            ],
            "question": "Do the rows show a constant proportional rate?",
            "approaches": [
                {
                    "id": "steady_additive_steps",
                    "resources": ["Addition"],
                    "procedure": "Compare the consecutive increases in makes.",
                    "why_plausible": "The rows have equally spaced attempt totals.",
                }
            ],
        }
    )
    selection = JudgeSelection(
        recommended_id=0,
        approaches=("Compare consecutive increases.",),
        reason="The additive pattern can be tempting even when unit rates differ.",
        main_concern=None,
        number_requirements=(
            NumberRequirement(
                "Attempts increase by equal amounts in the three records.",
                "This makes consecutive make changes comparable over equal intervals.",
            ),
        ),
        prior_contrast=PriorContrastIntent(
            approach_id="steady_additive_steps",
            operational_move="Compare each consecutive increase in makes.",
            checkability="numerical",
            reason="The intended design contrasts steady changes with proportional rates.",
            expected_target_equal=False,
            expected_prior_equal=True,
        ),
    )
    winner = selected_candidate([skeleton], selection)[0]
    prompts = runner._prompts()
    assert "expected_target_equal and expected_prior_equal" in prompts["JUDGE_SKELETONS_SYSTEM"]
    assert '"expected_target_equal": null' in prompts["JUDGE_SKELETONS_USER"]
    plan_request = runner._plan_request(
        prompts,
        {"target_concept": "proportional rate"},
        winner,
        {},
    )
    assert '"expected_target_equal": false' in plan_request["user"]
    assert '"expected_prior_equal": true' in plan_request["user"]
    assert "Attempts increase by equal amounts in the three records." in plan_request["user"]
    assert "Copy expected_target_equal and expected_prior_equal from" in plan_request["system"]
    assert "the selected design" in plan_request["system"]
    payload = {
        "schema_version": "math-plan/v2",
        "target": {
            "name": "unit_rates",
            "expressions": {
                label: f"makes[{index}]/attempts[{index}]"
                for index, label in enumerate(("A", "B", "C"))
            },
        },
        "answer_rule": {"kind": "equal", "labels": ["A", "B", "C"]},
        "constraints": [
            {
                "left": "attempts[1]-attempts[0]",
                "operator": "==",
                "right": "attempts[2]-attempts[1]",
                "description": "attempt totals have equal steps",
            }
        ],
        "prior_contrast": {
            "name": "consecutive make increments",
            "approach_id": "steady_additive_steps",
            "expressions": {
                "step_1": "makes[1]-makes[0]",
                "step_2": "makes[2]-makes[1]",
            },
            "expected_target_equal": False,
            "expected_prior_equal": True,
        },
    }
    plan = runner._math_plan_from_payload(payload, winner)
    result = runner.check_fill(plan, {"attempts": [10, 20, 30], "makes": [4, 10, 16]})
    assert result.accepted
    assert result.contrast_decisions == {
        "target_equal": False,
        "prior_equal": True,
        "expected_target_equal": False,
        "expected_prior_equal": True,
    }

    wrong_selection = replace(
        winner,
        prior_contrast=replace(
            winner.prior_contrast,
            expected_target_equal=True,
            expected_prior_equal=False,
        ),
    )
    with pytest.raises(ValueError, match="do not match the selected design"):
        runner._math_plan_from_payload(payload, wrong_selection)


def test_equal_contrast_outcomes_survive_repair_fill_and_final_serialization(monkeypatch, tmp_path):
    skeleton = skeleton_from_payload(
        {
            "quantities": [
                {"name": "attempts", "role": "list", "list_length": 3},
                {"name": "makes", "role": "list", "list_length": 3},
            ],
            "question": "Compare the relationship across the three records.",
            "approaches": [
                {
                    "id": "steady_additive_steps",
                    "resources": ["Addition"],
                    "procedure": "Compare consecutive increases in makes.",
                    "why_plausible": "The attempt totals are equally spaced.",
                }
            ],
        }
    )
    selection = JudgeSelection(
        recommended_id=0,
        approaches=("Compare consecutive increases in makes.",),
        reason="A steady additive pattern can differ from proportionality.",
        main_concern=None,
        prior_contrast=PriorContrastIntent(
            approach_id="steady_additive_steps",
            operational_move="Compare each consecutive increase in makes.",
            checkability="numerical",
            reason="The selected design contrasts rates with additive steps.",
            expected_target_equal=False,
            expected_prior_equal=True,
        ),
    )
    winner = selected_candidate([skeleton], selection)[0]
    plan_payload = {
        "schema_version": "math-plan/v2",
        "target": {
            "name": "unit_rates",
            "expressions": {
                label: f"makes[{index}]/attempts[{index}]"
                for index, label in enumerate(("A", "B", "C"))
            },
        },
        "answer_rule": {"kind": "equal", "labels": ["A", "B", "C"]},
        "constraints": [
            {
                "left": "attempts[1]-attempts[0]",
                "operator": "==",
                "right": "attempts[2]-attempts[1]",
                "description": "attempt totals have equal steps",
            }
        ],
        "prior_contrast": {
            "name": "consecutive make increments",
            "approach_id": "steady_additive_steps",
            "expressions": {
                "step_1": "makes[1]-makes[0]",
                "step_2": "makes[2]-makes[1]",
            },
            "expected_target_equal": False,
            "expected_prior_equal": True,
        },
    }

    source = tmp_path / "selected.json"
    source.write_text(json.dumps({"winner": winner.to_dict()}))
    restored = runner._winner_from_result(source, "equal-case")
    plan = runner._math_plan_from_payload(plan_payload, restored)
    assert restored.prior_contrast.expected_target_equal is False
    assert restored.prior_contrast.expected_prior_equal is True

    repaired_skeleton = json.loads(json.dumps(restored.skeleton.to_dict()))
    repaired_skeleton["question"] = "Compare the evidence in the three records."
    repair_payload = {"skeleton": repaired_skeleton, "math_plan": plan.to_dict()}
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (repair_payload, "joint repair response"),
    )
    prior_context = {"recommendations": [{"resource": "Addition"}]}
    repaired_winner, repaired_plan, repair_record = runner._joint_repair(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "proportionality", "grade": 7},
        restored,
        plan,
        prior_context,
        {"route": "design", "reason": "clarify the question"},
    )
    assert repaired_winner is not None, repair_record["validation"]
    assert repaired_plan is not None
    assert repair_record["structure_valid"]
    assert repaired_winner.prior_contrast.expected_target_equal is False
    assert repaired_winner.prior_contrast.expected_prior_equal is True
    assert repaired_plan.prior_contrast_expected_target_equal is False
    assert repaired_plan.prior_contrast_expected_prior_equal is True

    repaired_source = tmp_path / "repaired.json"
    repaired_source.write_text(
        json.dumps(
            {
                "case": "equal-case",
                "original_winner": restored.to_dict(),
                "winner": repaired_winner.to_dict(),
                "math_plan": repaired_plan.to_dict(),
                "design_repair_attempts": [repair_record],
            }
        )
    )
    output = tmp_path / "final.json"
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_situation_skeletons.py",
            "--case",
            "equal-case",
            "--from-result",
            str(repaired_source),
            "--use-expert-resources",
            "--output",
            str(output),
        ],
    )
    monkeypatch.setattr(
        runner,
        "_load_case",
        lambda _: {
            "id": "equal-case",
            "target_concept": "proportionality",
            "grade": 7,
            "topic": "rates",
            "subject": "mathematics",
        },
    )
    monkeypatch.setattr(runner, "_expert_prior_context", lambda _: prior_context)
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    monkeypatch.setattr(
        runner,
        "_review_plan",
        lambda *args, **kwargs: (
            {
                "status": "pass",
                "distinct_approaches": True,
                "constraints_covered": True,
                "issues": [],
            },
            "review response",
            {},
        ),
    )
    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *args, **kwargs: (
            {"values": {"attempts": [10, 20, 30], "makes": [4, 10, 16]}},
            "fill response",
            {},
        ),
    )
    monkeypatch.setattr(
        runner,
        "_write_task",
        lambda *args, **kwargs: (
            {
                "status": "ready",
                "blocking_issues": [],
                "title": "Three records",
                "body": "Compare the records.",
                "question": "Which relationship do they support?",
            },
            "writer response",
        ),
    )
    runner.main()

    result = json.loads(output.read_text())
    assert result["fill_accepted"]
    assert result["winner"]["prior_contrast"]["expected_target_equal"] is False
    assert result["winner"]["prior_contrast"]["expected_prior_equal"] is True
    assert result["original_winner"]["prior_contrast"]["expected_target_equal"] is False
    assert result["math_plan"]["prior_contrast"]["expected_target_equal"] is False
    assert result["math_plan"]["prior_contrast"]["expected_prior_equal"] is True
    assert result["fill_check"]["contrast_decisions"] == {
        "target_equal": False,
        "prior_equal": True,
        "expected_target_equal": False,
        "expected_prior_equal": True,
    }
    assert (
        result["design_repair_attempts"][0]["proposed"]["math_plan"]["prior_contrast"][
            "expected_prior_equal"
        ]
        is True
    )
    assert result["task"]["status"] == "ready"


@pytest.mark.parametrize("checkability", ["qualitative", "unsupported"])
def test_uncheckable_selected_prior_is_reported_unverified_not_as_checked(
    monkeypatch, checkability
):
    winner, plan, review = _consistency_example()
    winner = replace(
        winner,
        prior_contrast=PriorContrastIntent(
            approach_id="plot",
            operational_move="Plot the scores and compare their concentration.",
            checkability=checkability,
            reason="This move is not an executable numerical path.",
        ),
    )
    values = {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}
    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *args, **kwargs: ({"values": values}, "raw", {}),
    )
    result = runner._fill_until_accepted(
        None,
        "model",
        {},
        {},
        winner,
        plan,
        {},
        plan_review=review,
    )
    assert result["accepted"]
    status = next(
        item
        for item in result["check"]["unverified_requirements"]
        if item["requirement_id"] == "selected_prior_contrast"
    )
    assert status["status"] == "unverified"
    assert status["checkability"] == checkability
    assert result["check"]["priors"] == []


def test_design_insights_reach_planner_review_and_every_fill_attempt(monkeypatch):
    winner, plan, review = _consistency_example()
    prompts = runner._prompts()
    context = json.dumps(runner._design_context(winner), ensure_ascii=False, indent=2)
    case = {"target_concept": "Variability", "grade": 7}
    prior_context = {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]}
    bad = {"scores_a": [6, 6, 10, 10], "scores_b": [6, 7, 8, 10]}
    good = {"scores_a": [6, 6, 10, 10], "scores_b": [6, 8, 8, 10]}
    responses = iter([plan.to_dict(), review, {"values": bad}, {"values": good}])
    requests = []

    def fake_chat(client, model, system, user, **kwargs):
        assert context in user
        assert winner.skeleton.question in user
        assert "{design_context}" not in user
        requests.append({"system": system, "user": user})
        payload = next(responses)
        return payload, json.dumps(payload)

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    planned, _ = runner._plan_winner(None, "model", prompts, case, winner, prior_context)
    frozen_plan = runner._math_plan_from_payload(planned, winner)
    reviewed, _, _ = runner._review_plan(None, "model", prompts, case, winner, frozen_plan)
    assert runner._review_passes(reviewed)
    result = runner._fill_until_accepted(
        None, "model", prompts, case, winner, frozen_plan, prior_context, plan_review=reviewed
    )
    assert result["accepted"]
    assert result["payload"]["values"] == good
    assert len(result["attempts"]) == 2
    assert "means match" in result["attempts"][0]["check"]["failures"]
    feedback = requests[-1]["user"].split("PREVIOUS VALUES AND CHECK FEEDBACK:\n", 1)[1]
    feedback = json.loads(feedback.split("\n\nReturn JSON", 1)[0])
    assert feedback["previous_values"] == bad
    assert "means match" in requests[-1]["user"]
    assert result["attempts"][0]["prompts"] == requests[2]
    assert result["attempts"][1]["prompts"] == requests[3]
    assert result["check"]["unverified_requirements"] == [review["requirement_coverage"][-1]]
    assert frozen_plan.to_dict() == plan.to_dict()


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "duplicate",
        "unknown",
        "invalid-index",
        "no-constraint",
        "unresolved",
        "no-reason",
        "invalid-status",
    ],
)
def test_requirement_coverage_blocks_incomplete_or_invalid_review(monkeypatch, defect):
    winner, plan, review = _consistency_example()
    coverage = review["requirement_coverage"]
    if defect == "missing":
        coverage.pop(0)
    elif defect == "duplicate":
        coverage.append(coverage[0])
    elif defect == "unknown":
        coverage[0]["requirement_id"] = "unknown"
    elif defect == "invalid-index":
        coverage[0]["constraint_indices"] = [len(plan.constraints)]
    elif defect == "no-constraint":
        coverage[0]["constraint_indices"] = []
    elif defect == "unresolved":
        coverage[0].update(status="unresolved", constraint_indices=[])
    elif defect == "no-reason":
        coverage[0]["reason"] = ""
    else:
        coverage[0]["status"] = []
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (review, "raw"))
    reviewed, _, _ = runner._review_plan(
        None, "model", runner._prompts(), {"target_concept": "Variability"}, winner, plan
    )
    assert not runner._review_passes(reviewed)
    assert reviewed["status"] == "unknown"
    assert reviewed["issues"]
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: pytest.fail("fill must not be called"))
    result = runner._fill_until_accepted(
        None, "model", {}, {}, winner, plan, {}, plan_review=reviewed
    )
    assert not result["accepted"]
    assert result["check"]["status"] == "needs_review"
    assert result["attempts"] == []


def test_requirement_coverage_never_defaults_to_pass(monkeypatch):
    winner, plan, review = _consistency_example()
    del review["requirement_coverage"]
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: pytest.fail("fill must not be called"))
    for supplied_review in (None, review):
        result = runner._fill_until_accepted(
            None, "model", {}, {}, winner, plan, {}, plan_review=supplied_review
        )
        assert not result["accepted"]
        assert "missing requirement coverage" in result["check"]["failures"][0]


def test_requirement_coverage_accepts_enforced_quantity_facts():
    skeleton = skeleton_from_payload(
        {
            "quantities": [
                {
                    "name": "counts",
                    "role": "list",
                    "unit": "items",
                    "list_length": 3,
                    "value_domain": "positive_integer",
                }
            ],
            "question": "How should the groups be compared?",
            "approaches": [
                {
                    "id": "count",
                    "resources": ["Counting"],
                    "procedure": "Compare the group counts.",
                    "why_plausible": "Students can count each group.",
                }
            ],
        }
    )
    winner = selected_candidate(
        [skeleton],
        JudgeSelection(
            recommended_id=0,
            approaches=("Compare the group counts.",),
            reason="The count comparison leaves room for justification.",
            main_concern=None,
            number_requirements=(
                NumberRequirement(
                    "Each group has the declared number of items.",
                    "Keep the comparison focused on the intended groups.",
                ),
            ),
        ),
    )[0]
    plan = MathPlan.from_payload(
        {
            "schema_version": "math-plan/v2",
            "target": {"expressions": {"answer": "sum(counts)"}, "unit": "items"},
            "answer_rule": {"kind": "scalar", "labels": ["answer"], "unit": "items"},
            "constraints": [],
        },
        skeleton.quantities,
    )
    review = {
        "status": "pass",
        "distinct_approaches": True,
        "constraints_covered": True,
        "issues": [],
        "requirement_coverage": [
            {
                "requirement_id": "judge_0",
                "status": "numerical",
                "constraint_indices": [],
                "quantity_fact_refs": [
                    {"quantity": "counts", "fact": "list_length"},
                    {"quantity": "counts", "fact": "value_domain"},
                    {"quantity": "counts", "fact": "unit"},
                ],
                "reason": "The frozen quantity contract enforces these facts.",
            }
        ],
    }
    assert runner._requirement_coverage_errors(review, winner, plan) == []
    assert runner._review_passes(review)


def test_requirement_coverage_accepts_unique_answer_rule_fact():
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = ["require_unique"]
    assert plan.answer_rule.kind == "smallest"
    assert plan.answer_rule.require_unique is True
    assert runner._requirement_coverage_errors(review, winner, plan) == []


def test_requirement_coverage_accepts_non_value_dependent_plan_facts():
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = []
    entry["plan_fact_refs"] = ["quantities", "target", "answer_rule"]
    assert runner._requirement_coverage_errors(review, winner, plan) == []


@pytest.mark.parametrize(
    "plan_fact_refs, expected",
    [
        (["missing"], "must be one of"),
        (["target", "target"], "duplicate plan fact"),
        ([{"fact": "target"}], "must be a string"),
    ],
)
def test_requirement_coverage_rejects_invalid_plan_facts(plan_fact_refs, expected):
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = []
    entry["plan_fact_refs"] = plan_fact_refs
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any(expected in error for error in errors)


def test_requirement_coverage_rejects_empty_plan_fact_section():
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = []
    entry["plan_fact_refs"] = ["quantities"]
    empty_quantities_plan = replace(plan, quantities=())
    errors = runner._requirement_coverage_errors(review, winner, empty_quantities_plan)
    assert any("non-empty MathPlan.to_dict section" in error for error in errors)


@pytest.mark.parametrize("status", ["qualitative", "unresolved"])
def test_requirement_coverage_rejects_plan_facts_for_non_numerical_entries(status):
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["status"] = status
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = []
    entry["plan_fact_refs"] = ["target"]
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any("non-numerical coverage must not cite plan facts" in error for error in errors)


@pytest.mark.parametrize("rule_change", [{"kind": "equal"}, {"require_unique": False}])
def test_requirement_coverage_rejects_inapplicable_unique_answer_rule_fact(rule_change):
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = ["require_unique"]
    plan = replace(plan, answer_rule=replace(plan.answer_rule, **rule_change))
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any(
        ("require_unique" in error and "only enforced" in error) or "not enabled" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "fact_refs, status, expected",
    [
        (["other"], "numerical", "must be exactly"),
        ([{"fact": "require_unique"}], "numerical", "must be a string"),
        (["require_unique"], "qualitative", "non-numerical"),
    ],
)
def test_requirement_coverage_rejects_invalid_answer_rule_facts(fact_refs, status, expected):
    winner, plan, review = _consistency_example()
    entry = review["requirement_coverage"][0]
    entry["status"] = status
    entry["constraint_indices"] = []
    entry["quantity_fact_refs"] = []
    entry["answer_rule_fact_refs"] = fact_refs
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any(expected in error for error in errors)


def test_review_prompt_exposes_authoritative_indexed_constraints_and_output(monkeypatch):
    winner, plan, _ = _consistency_example()
    captured = {}

    def fake_chat_json(*args, **kwargs):
        captured["system"] = args[2]
        captured["user"] = args[3]
        return (
            {
                "status": "pass",
                "question_answer_alignment": "aligned",
                "approach_formula_alignment": "aligned",
                "distinct_approaches": True,
                "constraints_covered": True,
                "issues": [],
                "requirement_coverage": [
                    {
                        "requirement_id": item["requirement_id"],
                        "status": "numerical",
                        "constraint_indices": item["constraint_indices"],
                        "reason": "covered",
                    }
                    for item in []
                ],
            },
            "raw",
        )

    monkeypatch.setattr(runner, "chat_json", fake_chat_json)
    runner._review_plan(
        None,
        "model",
        {
            "REVIEW_PLAN_SYSTEM": "{indexed_constraints}",
            "REVIEW_PLAN_USER": "{intended_student_output}",
        },
        {"target_concept": "spread"},
        winner,
        plan,
    )
    indexed = json.loads(captured["system"])
    assert indexed[0]["index"] == 0
    assert indexed[0]["left"] == plan.constraints[0].left
    output = json.loads(captured["user"])
    assert output["answer_rule"] == plan.answer_rule.to_dict()
    assert output["question"] == winner.skeleton.question
    assert "different solution approaches or representations" in output["student_work"]
    assert "exploration_guidance" in output


def test_review_prompt_contract_declares_indexed_context_and_string_fact_refs():
    prompts = runner._prompts()
    assert "{indexed_constraints}" in prompts["REVIEW_PLAN_USER"]
    assert "{intended_student_output}" in prompts["REVIEW_PLAN_USER"]
    assert '["require_unique"]' in prompts["REVIEW_PLAN_USER"]
    assert '"plan_fact_refs"' in prompts["REVIEW_PLAN_USER"]
    assert '{"quantities", "target", "answer_rule"}' in prompts["REVIEW_PLAN_SYSTEM"]
    assert 'value_source="given"' in prompts["REVIEW_PLAN_SYSTEM"]
    assert "given_quantities" not in prompts["REVIEW_PLAN_SYSTEM"]
    assert "value-independent" in prompts["REVIEW_PLAN_SYSTEM"]
    assert "does not solve equations" in prompts["REVIEW_PLAN_SYSTEM"]
    assert "target's inline arithmetic" in prompts["REVIEW_PLAN_SYSTEM"]
    assert "the plan rather than waiving" in prompts["REVIEW_PLAN_SYSTEM"]
    assert "not restate quantity" in prompts["PROPOSE_SKELETON_SYSTEM"]


@pytest.mark.parametrize(
    "fact_ref, expected",
    [
        ({"quantity": "counts", "fact": "missing"}, "must be one of"),
        ({"quantity": "unknown", "fact": "list_length"}, "unknown given quantity"),
    ],
)
def test_requirement_coverage_rejects_unenforced_quantity_facts(fact_ref, expected):
    winner, plan, review = _consistency_example()
    review["requirement_coverage"][0]["quantity_fact_refs"] = [fact_ref]
    review["requirement_coverage"][0]["constraint_indices"] = []
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any(expected in error for error in errors)


def test_requirement_coverage_rejects_structural_tautology_constraint():
    winner, plan, review = _consistency_example()
    tautology = ConstraintSpec(
        left="scores_a[0]",
        operator="==",
        right="(scores_a[0])",
    )
    plan = replace(plan, constraints=(tautology, *plan.constraints[1:]))
    review["requirement_coverage"][0]["constraint_indices"] = [0]
    errors = runner._requirement_coverage_errors(review, winner, plan)
    assert any("tautology" in error for error in errors)


def test_new_proposal_route_rejects_missing_given_list_length(monkeypatch):
    payload = {
        "quantities": [{"name": "scores", "role": "list", "description": "scores"}],
        "question": "Which group is more consistent?",
    }
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "raw"))
    record = runner._propose_one(
        None,
        "model",
        {"PROPOSE_SKELETON_SYSTEM": "", "PROPOSE_SKELETON_USER": ""},
        {
            "target_concept": "spread",
            "topic": "data",
            "grade": 7,
            "subject": "mathematics",
        },
        {"recommendations": [{"resource": "Mean"}]},
    )
    assert "fixed positive list_length" in record["error"]


def test_saved_winner_with_null_list_length_is_blocked_before_filling(tmp_path):
    skeleton = skeleton_from_payload(
        {
            "quantities": [{"name": "scores", "role": "list"}],
            "question": "Which group is more consistent?",
        }
    )
    winner = selected_candidate(
        [skeleton],
        JudgeSelection(
            recommended_id=0,
            approaches=("Compare the groups.",),
            reason="A comparison is open.",
            main_concern=None,
        ),
    )[0]
    path = tmp_path / "saved.json"
    path.write_text(
        json.dumps(
            {
                "winner": winner.to_dict(),
                "math_plan": {
                    "schema_version": "math-plan/v2",
                    "target": {"expressions": {"answer": "sum(scores)"}},
                    "answer_rule": {"kind": "scalar", "labels": ["answer"]},
                },
            }
        )
    )
    with pytest.raises(ValueError, match="incomplete quantity metadata"):
        runner._stored_math_plan(path, winner)


@pytest.mark.parametrize("shape", ["winners", "winner"])
def test_saved_winner_preserves_design_insights(tmp_path, shape):
    winner, _, _ = _consistency_example()
    path = tmp_path / "result.json"
    value = [winner.to_dict()] if shape == "winners" else winner.to_dict()
    path.write_text(json.dumps({shape: value}))
    restored = runner._winner_from_result(path)
    assert restored.to_dict() == winner.to_dict()
    assert runner._design_context(restored) == runner._design_context(winner)


def test_saved_winner_round_trips_selected_prior_contrast(tmp_path):
    winner, _, _ = _consistency_example()
    winner = replace(
        winner,
        prior_contrast=PriorContrastIntent(
            approach_id="mean",
            operational_move="Compare the group means.",
            checkability="numerical",
            reason="This is the selected tempting move.",
        ),
    )
    path = tmp_path / "selected-contrast.json"
    path.write_text(json.dumps({"winner": winner.to_dict()}))

    restored = runner._winner_from_result(path)
    assert restored.prior_contrast == winner.prior_contrast
    assert runner._design_context(restored)["prior_contrast"] == winner.prior_contrast.to_dict()


def test_legacy_saved_winner_still_loads_without_judge_insights(tmp_path):
    winner, _, _ = _consistency_example()
    legacy = replace(winner, skeleton=replace(winner.skeleton, number_constraints=())).to_dict()
    for key in (
        "selection_approaches",
        "selection_reason",
        "main_concern",
        "number_requirements",
        "prior_contrast",
    ):
        legacy.pop(key)
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"winners": [legacy]}))
    assert runner._design_context(runner._winner_from_result(path)) == {
        "selection_reason": "",
        "selected_approaches": [],
        "main_concern": None,
        "prior_contrast": None,
        "requirements": [],
    }


def _mock_default_brief_search(monkeypatch, winner):
    from scripts import design_brief_stage

    monkeypatch.setattr(
        design_brief_stage,
        "run_design_brief_search",
        lambda *args, **kwargs: {
            "proposals": [{"brief": {"student_question": winner.skeleton.question}}],
            "n_valid_proposals": 1,
            "judged": [winner],
            "winners": [winner],
            "judge_raw_text": "selection",
            "judge_error": None,
            "brief_selection": {},
            "translation": {"status": "translated"},
            "source_hashes": {},
            "prompt_snapshot": {},
        },
    )


def test_situation_cli_no_longer_requires_design_brief_flag(monkeypatch, capsys):
    monkeypatch.setattr(
        runner.sys, "argv", ["run_situation_skeletons.py", "--case", "example", "--help"]
    )
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 0
    assert "--design-brief" not in capsys.readouterr().out


def test_historical_cli_blocks_fill_when_a_requirement_is_omitted(monkeypatch, tmp_path):
    winner, plan, review = _consistency_example()
    review["requirement_coverage"].pop(0)
    output = tmp_path / "output.json"
    args = [
        "run_situation_skeletons.py",
        "--case",
        "example",
        "--k",
        "1",
        "--from-d1",
        "unused.json",
        "--output",
        str(output),
    ]
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"winner": winner.to_dict(), "math_plan": plan.to_dict()}))
    args.extend(["--from-result", str(source)])
    monkeypatch.setattr(runner.sys, "argv", args)
    monkeypatch.setattr(
        runner, "_load_case", lambda _: {"target_concept": "Variability", "grade": 7}
    )
    monkeypatch.setattr(
        runner,
        "_prior_context_from_d1",
        lambda *a: {"recommendations": [{"resource": "Mean"}]},
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    _mock_default_brief_search(monkeypatch, winner)
    monkeypatch.setattr(runner, "_plan_winner", lambda *a: (plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (review, "review"))
    monkeypatch.setattr(
        runner, "_fill_winner", lambda *a, **k: pytest.fail("CLI must not generate values")
    )
    runner.main()
    result = json.loads(output.read_text())
    assert result["fill_blocked_reason"] == "plan review did not pass"
    assert result["plan_review"]["status"] == "unknown"
    assert "missing requirement coverage" in result["plan_review"]["issues"][0]


def test_fresh_cli_uses_design_data_without_legacy_planning(monkeypatch, tmp_path):
    winner, plan, review = _consistency_example()
    output = tmp_path / "output.json"
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_situation_skeletons.py",
            "--case",
            "example",
            "--k",
            "1",
            "--from-d1",
            "unused.json",
            "--output",
            str(output),
        ],
    )
    monkeypatch.setattr(
        runner,
        "_load_case",
        lambda _: {
            "target_concept": "Variability",
            "grade": 7,
            "subject": "mathematics",
            "topic": "data",
        },
    )
    monkeypatch.setattr(
        runner,
        "_prior_context_from_d1",
        lambda *a: {"recommendations": [{"resource": "Mean"}]},
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    _mock_default_brief_search(monkeypatch, winner)
    monkeypatch.setattr(
        runner, "_plan_until_reviewed", lambda *a: pytest.fail("No legacy planning")
    )
    monkeypatch.setattr(
        runner,
        "_run_design_data",
        lambda *a, **k: {
            "status": "accepted",
            "accepted": True,
            "error": None,
            "payload": {"values": {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}},
            "check": {"accepted": True, "reason": "accepted"},
            "attempts": [],
        },
    )
    captured = {}

    def fake_write(*args):
        captured["args"] = args
        return (
            {
                "status": "ready",
                "blocking_issues": [],
                "title": "Comparing performances",
                "body": "Explore and justify a comparison.",
                "question": winner.skeleton.question,
            },
            "writer",
        )

    monkeypatch.setattr(runner, "_write_design_data_task", fake_write)
    runner.main()

    result = json.loads(output.read_text())
    assert result["task"]["status"] == "ready"
    assert result["task_raw_text"] == "writer"
    assert captured["args"][4]["payload"]["values"]["scores_a"] == [4, 6, 6, 8]
    assert captured["args"][5] == {"recommendations": [{"resource": "Mean"}]}
    assert result["design_data"]["status"] == "accepted"
    assert "math_plan" not in result


@pytest.mark.parametrize("status", ["review_needed", "rejected", "invalid"])
def test_fresh_cli_does_not_write_unaccepted_data(monkeypatch, tmp_path, status):
    winner, _, _ = _consistency_example()
    output = tmp_path / "output.json"
    monkeypatch.setattr(
        runner.sys, "argv",
        ["run_situation_skeletons.py", "--case", "example",
         "--use-expert-resources", "--output", str(output)],
    )
    monkeypatch.setattr(
        runner, "_load_case", lambda _: {"target_concept": "Variability", "grade": 7}
    )
    monkeypatch.setattr(
        runner, "_expert_prior_context", lambda _: {"recommendations": [{"resource": "Mean"}]}
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    _mock_default_brief_search(monkeypatch, winner)
    monkeypatch.setattr(
        runner, "_run_design_data",
        lambda *a: {"status": status, "accepted": False, "error": "Exact reason",
                    "payload": None, "check": None, "attempts": []},
    )
    monkeypatch.setattr(
        runner, "_write_design_data_task", lambda *a: pytest.fail("Do not write unchecked data")
    )
    runner.main()
    result = json.loads(output.read_text())
    assert result["design_data"]["status"] == status
    assert result["fill_blocked_reason"] == "Exact reason"
    assert result["task"] is None


@pytest.mark.parametrize("flags", [[], ["--plan-only"], ["--no-fill"]])
@pytest.mark.parametrize("failure_stage", [None, "structure", "expression", "meaning_review"])
def test_nested_saved_replan_cli_preserves_context_and_gates(
    monkeypatch, tmp_path, flags, failure_stage
):
    winner, plan, review = _consistency_example()
    case = {"id": "example", "target_concept": "Variability", "grade": 7}
    prior_context = {"case_id": "example", "recommendations": [{"resource": "Mean"}]}
    source = tmp_path / "diagnostic.json"
    original = json.dumps(
        {
            "case_id": "example",
            "case_input": case,
            "prior_context": prior_context,
            "stages": {"D2_D3": {"winners": [winner.to_dict()], "math_plan": None}},
        }
    )
    source.write_text(original)
    output = tmp_path / "replanned.json"
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_situation_skeletons.py",
            "--case",
            "example",
            "--from-result",
            str(source),
            "--replan",
            "--output",
            str(output),
            *flags,
        ],
    )
    monkeypatch.setattr(
        runner, "_load_case", lambda _: {**case, "target_concept": "Changed configuration"}
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    monkeypatch.setattr(
        runner, "_propose_one", lambda *a: pytest.fail("Replanning must reuse the winner")
    )
    monkeypatch.setattr(
        runner, "_judge_all", lambda *a: pytest.fail("Replanning must not reselect")
    )
    calls = []

    def fake_chat(client, model, system, user, **kwargs):
        assert "Changed configuration" not in user
        if system.startswith("Freeze"):
            calls.append("plan")
            payload = plan.to_dict()
            if failure_stage == "structure":
                payload["unresolved"] = ["Do not silently ignore this"]
            elif failure_stage == "expression":
                payload["target"]["expressions"]["A"] = "invented_name"
            return payload, "raw plan"
        if system.startswith("Review"):
            calls.append("review")
            assert "GRADE: 7" in user and "Mean" in user
            response = review
            if failure_stage == "meaning_review":
                response = {**review, "requirement_coverage": []}
            return response, "raw review"
        if system.startswith("Fill"):
            calls.append("fill")
            return {"values": {"scores_a": [4, 6, 6, 8], "scores_b": [4, 4, 8, 8]}}, "raw fill"
        if system.startswith("Write"):
            calls.append("write")
            assert '"procedure"' in user and "Plot the scores" in user
            return {
                "status": "ready",
                "blocking_issues": [],
                "title": "Comparing performances",
                "body": "A: 4, 6, 6, 8. B: 4, 4, 8, 8.",
                "question": winner.skeleton.question,
            }, "raw task"
        pytest.fail(f"Unexpected model call: {system[:40]}")

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    runner.main()
    result = json.loads(output.read_text())
    assert source.read_text() == original
    assert result["case_input"] == case
    assert result["case_input_provenance"] == "saved_snapshot"
    assert result["prior_context"] == prior_context
    assert result["winner"] == json.loads(original)["stages"]["D2_D3"]["winners"][0]
    assert result["plan_stop_stage"] == (failure_stage or "accepted")
    assert result["plan_review_error"] is None
    if failure_stage in {"structure", "expression"}:
        assert calls == ["plan", "plan"]
        assert result["plan_review"] is None
    elif failure_stage == "meaning_review":
        assert calls == ["plan", "review", "plan", "review"]
        assert result["plan_review"]["status"] == "unknown"
    elif flags:
        assert calls == ["plan", "review"]
    else:
        assert calls == ["plan", "review", "fill", "write"]
        assert result["fill_accepted"]
        assert result["task"]["status"] == "ready"
    if failure_stage or flags:
        assert result["filled_values"] is None
        assert result["task"] is None


@pytest.mark.parametrize("bad_expression", [False, True])
def test_legacy_cli_resume_preserves_contract_and_review_provenance(
    monkeypatch, tmp_path, bad_expression
):
    winner, plan, review = _consistency_example()
    legacy = {
        **plan.to_dict(),
        "schema_version": "math-plan/v1",
        "priors": [
            {
                "name": "mean",
                "approach_id": "mean",
                "expressions": {"A": "sum(scores_a)/4", "B": "sum(scores_b)/4"},
            }
        ],
    }
    if bad_expression:
        legacy["target"]["expressions"]["A"] = "invented_name"
    source = tmp_path / "legacy.json"
    source.write_text(
        json.dumps(
            {
                "case": "example",
                "winner": winner.to_dict(),
                "math_plan": legacy,
                "prior_context": {"recommendations": [{"resource": "Mean"}]},
            }
        )
    )
    output = tmp_path / "resumed.json"
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_situation_skeletons.py",
            "--case",
            "example",
            "--from-result",
            str(source),
            "--no-fill",
            "--output",
            str(output),
        ],
    )
    monkeypatch.setattr(
        runner, "_load_case", lambda _: {"target_concept": "Variability", "grade": 7}
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "model"))
    calls = []

    def fake_chat(client, model, system, user, **kwargs):
        assert system.startswith("Review")
        calls.append("review")
        assert "math-plan/v1" in user
        return review, "raw review"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    runner.main()
    result = json.loads(output.read_text())
    assert result["math_plan"]["schema_version"] == "math-plan/v1"
    assert result["case_input_provenance"] == "legacy_source_without_snapshot"
    assert result["plan_attempts"] == []
    assert result["task"] is None
    assert result["plan_review_error"] is None
    if bad_expression:
        assert calls == []
        assert result["plan_stop_stage"] == "expression"
        assert result["plan_review"] is None
        assert "invented_name" in result["math_plan_error"]
    else:
        assert calls == ["review"]
        assert result["plan_stop_stage"] == "accepted"


def test_review_retry_uses_status_not_issue_keywords():
    assert runner._review_retryable(
        {"status": "revise", "issues": ["Correct the unknown variable reference"]}
    )


def test_pass_with_invalid_coverage_gets_one_correction_then_accepts(monkeypatch):
    winner, plan, review = _consistency_example()
    v2_plan = replace(plan, schema_version="math-plan/v2", priors=(), required_checks=())
    bad_review = json.loads(json.dumps(review))
    bad_review["requirement_coverage"][0]["quantity_fact_refs"] = [
        {"quantity": "unknown_quantity", "fact": "value_domain"}
    ]
    responses = iter([bad_review, review])
    monkeypatch.setattr(runner, "_plan_winner", lambda *a, **k: (v2_plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (next(responses), "review"))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {},
    )
    assert result["plan"] is not None
    assert result["plan_review"]["status"] == "pass"
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["stage"] == "meaning_review"
    assert result["attempts"][1]["stage"] == "accepted"
    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *a, **k: (
            {"values": {"scores_a": [6, 6, 10, 10], "scores_b": [6, 8, 8, 10]}},
            "fill",
            {},
        ),
    )
    filled = runner._fill_until_accepted(
        None,
        "model",
        {},
        {"target_concept": "Variability", "grade": 7},
        winner,
        result["plan"],
        {},
        plan_review=result["plan_review"],
    )
    assert filled["accepted"]


def test_repeated_pass_coverage_errors_end_after_one_correction(monkeypatch):
    winner, plan, review = _consistency_example()
    v2_plan = replace(plan, schema_version="math-plan/v2", priors=(), required_checks=())
    bad_review = json.loads(json.dumps(review))
    bad_review["requirement_coverage"][0]["quantity_fact_refs"] = [
        {"quantity": "unknown_quantity", "fact": "value_domain"}
    ]
    monkeypatch.setattr(runner, "_plan_winner", lambda *a, **k: (v2_plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (bad_review, "review"))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {},
    )
    assert result["plan"] is None
    assert len(result["attempts"]) == 2
    assert result["attempts"][-1]["stage"] == "meaning_review"


def test_unknown_review_never_gets_correction_permission():
    assert not runner._review_retryable(
        {"status": "unknown", "retryable": True, "_retryable_correction": "unknown"}
    )


def test_pass_with_issues_is_retryable_only_for_bounded_correction(monkeypatch):
    winner, plan, review = _consistency_example()
    review["issues"] = ["This is a blocker despite pass."]
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (review, "raw"))
    checked, _, _ = runner._review_plan(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability"},
        winner,
        plan,
    )
    assert checked["status"] == "unknown"
    assert checked["_retryable_correction"] == "pass"
    assert "empty issues list" in checked["issues"][-1]
    assert runner._review_retryable(checked)


def test_unknown_review_cannot_supply_retry_permission(monkeypatch):
    winner, plan, review = _consistency_example()
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *a, **k: (
            {**review, "status": "unknown", "issues": ["Conflicting design"], "retryable": True},
            "raw",
        ),
    )
    checked, _, _ = runner._review_plan(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        plan,
    )
    assert not runner._review_retryable(checked)


def test_unknown_review_forged_retry_markers_stop_after_one_real_review(monkeypatch):
    winner, plan, review = _consistency_example()
    v2_plan = replace(plan, schema_version="math-plan/v2", priors=(), required_checks=())
    forged = json.loads(json.dumps(review))
    forged.update(
        {
            "status": "unknown",
            "issues": ["The design is unresolved."],
            "retryable": True,
            "_retryable_correction": "pass",
            "_retryable_source": "pass",
        }
    )
    forged["requirement_coverage"][0]["quantity_fact_refs"] = [
        {"quantity": "unknown_quantity", "fact": "value_domain"}
    ]
    responses = iter([forged])
    monkeypatch.setattr(runner, "_plan_winner", lambda *a, **k: (v2_plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (next(responses), "raw review"))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {},
    )
    assert result["plan"] is None
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["review_raw_text"] == "raw review"
    assert result["attempts"][0]["stage"] == "meaning_review"


def test_pass_with_issues_correction_is_bounded_before_fill(monkeypatch):
    winner, plan, review = _consistency_example()
    v2_plan = replace(plan, schema_version="math-plan/v2", priors=(), required_checks=())
    bad_review = json.loads(json.dumps(review))
    bad_review["issues"] = ["A blocker was incorrectly reported with pass."]
    responses = iter([bad_review, review])
    fill_calls = []
    monkeypatch.setattr(runner, "_plan_winner", lambda *a, **k: (v2_plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (next(responses), "review"))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {},
    )
    assert len(result["attempts"]) == 2
    assert result["plan_review"]["status"] == "pass"
    assert fill_calls == []

    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *a, **k: (
            fill_calls.append(True)
            or (
                {"values": {"scores_a": [6, 6, 10, 10], "scores_b": [6, 8, 8, 10]}},
                "fill",
                {},
            )
        ),
    )
    filled = runner._fill_until_accepted(
        None,
        "model",
        {},
        {"target_concept": "Variability", "grade": 7},
        winner,
        result["plan"],
        {},
        plan_review=result["plan_review"],
    )
    assert fill_calls == [True]
    assert filled["accepted"]


def test_repeated_pass_with_issues_stops_without_fill(monkeypatch):
    winner, plan, review = _consistency_example()
    v2_plan = replace(plan, schema_version="math-plan/v2", priors=(), required_checks=())
    bad_review = json.loads(json.dumps(review))
    bad_review["issues"] = ["A blocker was incorrectly reported with pass."]
    monkeypatch.setattr(runner, "_plan_winner", lambda *a, **k: (v2_plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *a, **k: (bad_review, "review"))
    fill_calls = []
    monkeypatch.setattr(
        runner,
        "_fill_winner",
        lambda *a, **k: fill_calls.append(True),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {},
    )
    assert result["plan"] is None
    assert len(result["attempts"]) == 2
    assert fill_calls == []


def test_invalid_proposal_gets_one_targeted_correction_and_preserves_attempts(monkeypatch):
    valid = {
        "quantities": [{"name": "amount", "role": "amount", "value_domain": "positive"}],
        "question": "Which amount is larger?",
        "approaches": [
            {
                "id": "compare",
                "resources": ["Mean"],
                "procedure": "Compare the amounts.",
                "why_plausible": "Both amounts are visible.",
            }
        ],
    }
    invalid = {**valid, "approaches": [{**valid["approaches"][0], "resources": ["Invented"]}]}
    responses = iter([(invalid, "raw invalid"), (valid, "raw repaired")])
    users = []
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: users.append(args[3]) or next(responses),
    )
    record = runner._propose_one(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "comparison", "topic": "number", "grade": 7, "subject": "math"},
        {"recommendations": [{"resource": "Mean"}]},
    )
    assert "skeleton_obj" in record
    assert len(record["attempts"]) == 2
    assert "Invented" in record["attempts"][0]["error"]
    assert users[1].startswith("Repair the proposed")
    assert "raw invalid" in users[1]


def test_unknown_review_without_diagnosis_is_blocked_even_with_retry_flag():
    assert not runner._review_retryable(
        {
            "status": "unknown",
            "issues": ["insufficient evidence"],
            "retryable": True,
        }
    )


def test_joint_design_repair_propagates_effective_winner_and_preserves_original(monkeypatch):
    winner, plan, review = _consistency_example()
    repaired_skeleton = json.loads(json.dumps(winner.skeleton.to_dict()))
    repaired_skeleton["question"] = "Compare the performances in a new way."
    repaired_plan = plan.to_dict()
    initial_review = {
        "status": "unknown",
        "distinct_approaches": True,
        "constraints_covered": False,
        "requirement_coverage": [],
        "issues": ["The selected question needs an upstream design repair."],
        "repair_diagnosis": {"route": "design", "reason": "question and plan disagree"},
    }
    repaired_review = {
        **review,
        "repair_diagnosis": {"route": "none", "reason": "resolved"},
        "target_preserved": True,
        "approaches_preserved": True,
        "requirements_preserved": True,
        "repair_resolved": True,
    }
    monkeypatch.setattr(runner, "_plan_winner", lambda *args, **kwargs: (plan.to_dict(), "plan"))
    responses = iter(
        [
            (initial_review, "initial review"),
            ({"skeleton": repaired_skeleton, "math_plan": repaired_plan}, "joint repair"),
            (repaired_review, "repaired review"),
        ]
    )
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: next(responses))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
    )
    assert result["plan"] is not None
    assert result["winner"].skeleton.question == repaired_skeleton["question"]
    assert result["original_winner"].skeleton.question == winner.skeleton.question
    assert result["design_repair_attempts"][0]["accepted"]


def test_plan_correction_consumes_shared_budget_before_design_repair(monkeypatch):
    winner, plan, _ = _consistency_example()
    invalid_payload = {**plan.to_dict(), "schema_version": "math-plan/v1"}
    plan_payloads = iter([(invalid_payload, "invalid"), (plan.to_dict(), "corrected")])
    plan_calls = []
    joint_calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args, **kwargs: plan_calls.append(True) or next(plan_payloads),
    )
    monkeypatch.setattr(
        runner,
        "_joint_repair",
        lambda *args, **kwargs: joint_calls.append(True),
    )
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "unknown",
                "distinct_approaches": True,
                "constraints_covered": False,
                "requirement_coverage": [],
                "issues": ["the design still needs repair"],
                "repair_diagnosis": {"route": "design", "reason": "repair the question"},
            },
            "design diagnosis",
        ),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}]},
    )
    assert len(plan_calls) == 2
    assert joint_calls == []
    assert result["plan"] is None
    assert result["winner"] is winner


def test_rejected_joint_repair_does_not_leak_effective_winner(monkeypatch):
    winner, plan, review = _consistency_example()
    repaired_skeleton = json.loads(json.dumps(winner.skeleton.to_dict()))
    repaired_skeleton["question"] = "Compare the performances in a revised way."
    initial_review = {
        "status": "unknown",
        "distinct_approaches": True,
        "constraints_covered": False,
        "requirement_coverage": [],
        "issues": ["the selected question needs repair"],
        "repair_diagnosis": {"route": "design", "reason": "repair the question"},
    }
    rejected_review = {
        **review,
        "status": "revise",
        "constraints_covered": False,
        "issues": ["the repaired design remains unresolved"],
        "target_preserved": True,
        "approaches_preserved": True,
        "requirements_preserved": True,
        "repair_resolved": True,
    }
    responses = iter(
        [
            (initial_review, "initial review"),
            ({"skeleton": repaired_skeleton, "math_plan": plan.to_dict()}, "joint repair"),
            (rejected_review, "rejected repair review"),
        ]
    )
    monkeypatch.setattr(runner, "_plan_winner", lambda *args, **kwargs: (plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: next(responses))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
    )
    assert result["winner"] is winner
    assert result["original_winner"] is winner
    assert result["plan"] is None
    assert result["design_repair_attempts"][0]["accepted"] is False


@pytest.mark.parametrize("replacement_constraints", [[], ["The score lists have different means."]])
def test_joint_repair_rejects_altered_or_removed_original_requirement(
    monkeypatch, replacement_constraints
):
    winner, plan, _ = _consistency_example()
    repaired_skeleton = json.loads(json.dumps(winner.skeleton.to_dict()))
    repaired_skeleton["number_constraints"] = replacement_constraints
    payload = {"skeleton": repaired_skeleton, "math_plan": plan.to_dict()}
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "joint repair"))
    repaired_winner, repaired_plan, record = runner._joint_repair(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        plan,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        {"route": "design", "reason": "repair the question"},
    )
    assert repaired_winner is None
    assert repaired_plan is None
    assert "original number_constraints" in record["validation"][0]


def test_failed_preservation_review_rejects_structurally_valid_repair(monkeypatch):
    winner, plan, review = _consistency_example()
    repaired_skeleton = json.loads(json.dumps(winner.skeleton.to_dict()))
    repaired_skeleton["question"] = "Compare the performances after revising the wording."
    initial_review = {
        "status": "unknown",
        "distinct_approaches": True,
        "constraints_covered": False,
        "requirement_coverage": [],
        "issues": ["the selected question needs repair"],
        "repair_diagnosis": {"route": "design", "reason": "repair the question"},
    }
    preservation_failure = {
        **review,
        "target_preserved": True,
        "approaches_preserved": True,
        "requirements_preserved": False,
        "repair_resolved": True,
    }
    responses = iter(
        [
            (initial_review, "initial review"),
            ({"skeleton": repaired_skeleton, "math_plan": plan.to_dict()}, "joint repair"),
            (preservation_failure, "preservation failure"),
        ]
    )
    monkeypatch.setattr(runner, "_plan_winner", lambda *args, **kwargs: (plan.to_dict(), "plan"))
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: next(responses))
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
    )
    assert result["winner"] is winner
    assert result["plan"] is None
    assert result["design_repair_attempts"][0]["accepted"] is False
    assert result["attempts"][-1]["review"]["status"] == "unknown"
    assert "preservation" in result["attempts"][-1]["errors"][0]


def test_saved_initial_plan_is_reviewed_without_generation(monkeypatch):
    winner, plan, review = _consistency_example()
    generation_calls = []
    monkeypatch.setattr(
        runner,
        "_plan_winner",
        lambda *args, **kwargs: generation_calls.append(True),
    )
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (review, "reviewed saved plan"),
    )
    result = runner._plan_until_reviewed(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        initial_plan_payload=plan.to_dict(),
    )
    assert generation_calls == []
    assert result["plan"] is not None
    assert result["attempts"][0]["source"] == "saved_plan"
    assert result["attempts"][0]["prompts"] is None
    assert result["attempts"][0]["raw_text"] == ""


def test_saved_initial_proposal_is_rechecked_without_generation(monkeypatch):
    winner, _, _ = _consistency_example()
    saved_payload = json.loads(json.dumps(winner.skeleton.to_dict()))
    calls = []
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: calls.append(True),
    )
    result = runner._propose_one(
        None,
        "model",
        runner._prompts(),
        {
            "target_concept": "Variability",
            "topic": "data",
            "grade": 7,
            "subject": "mathematics",
        },
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        initial_proposal=saved_payload,
        initial_proposal_raw="saved proposal",
    )
    assert calls == []
    assert json.loads(json.dumps(result["skeleton_obj"].to_dict())) == saved_payload
    assert result["attempts"][0]["source"] == "saved_proposal"
    assert result["attempts"][0]["raw_text"] == "saved proposal"


@pytest.mark.parametrize("diagnosis", [[], {}, {"route": []}, {"route": {}}])
def test_malformed_repair_diagnosis_is_blocking_not_unhashable(diagnosis):
    errors = runner._repair_diagnosis_errors(diagnosis)
    assert errors
    assert not runner._review_retryable(
        {"status": "unknown", "repair_diagnosis": diagnosis, "issues": ["blocked"]}
    )


def test_unknown_review_cannot_inject_internal_retry_permission(monkeypatch):
    winner, plan, _ = _consistency_example()
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            {
                "status": "unknown",
                "issues": ["uncertain"],
                "distinct_approaches": True,
                "constraints_covered": True,
                "requirement_coverage": [],
                "_internal_retryable": True,
            },
            "raw",
        ),
    )
    checked, _, _ = runner._review_plan(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability"},
        winner,
        plan,
    )
    assert "_internal_retryable" not in checked
    assert not runner._review_retryable(checked)


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "unknown", "issues": [], "constraints_covered": True},
        {"status": "unknown", "distinct_approaches": True, "constraints_covered": True},
    ],
)
def test_unknown_malformed_review_stays_blocked(monkeypatch, payload):
    winner, plan, _ = _consistency_example()
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "raw"))
    checked, _, _ = runner._review_plan(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability"},
        winner,
        plan,
    )
    assert checked["status"] == "unknown"
    assert checked.get("_internal_retryable") is not True
    assert not runner._review_retryable(checked)


def test_empty_saved_proposal_envelope_gets_one_repair_call(monkeypatch):
    winner, _, _ = _consistency_example()
    calls = []
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (
            calls.append(True) or (json.loads(json.dumps(winner.skeleton.to_dict())), "repaired")
        ),
    )
    result = runner._propose_one(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "topic": "data", "grade": 7, "subject": "math"},
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        initial_proposal={"payload": None, "raw_text": ""},
    )
    assert len(calls) == 1
    assert result["attempts"][0]["payload"] is None
    assert result["attempts"][0]["raw_text"] == ""
    assert result["attempts"][0]["source"] == "saved_proposal"
    assert len(result["attempts"]) == 2


def test_proposal_transport_error_propagates(monkeypatch):
    monkeypatch.setattr(
        runner,
        "chat_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("transport")),
    )
    with pytest.raises(RuntimeError, match="transport"):
        runner._propose_one(
            None,
            "model",
            runner._prompts(),
            {"target_concept": "comparison", "topic": "number", "grade": 7, "subject": "math"},
            {"recommendations": [{"resource": "Mean"}]},
        )


def test_joint_repair_marks_structure_valid_but_not_accepted_before_review(monkeypatch):
    winner, plan, _ = _consistency_example()
    payload = {
        "skeleton": json.loads(json.dumps(winner.skeleton.to_dict())),
        "math_plan": json.loads(json.dumps(plan.to_dict())),
    }
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "joint"))
    repaired_winner, repaired_plan, record = runner._joint_repair(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        plan,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        {"route": "design", "reason": "repair the question"},
    )
    assert repaired_winner is not None and repaired_plan is not None
    assert record["structure_valid"] is True
    assert record["accepted"] is False


def test_joint_repair_rejects_non_v2_math_plan(monkeypatch):
    winner, plan, _ = _consistency_example()
    payload = {
        "skeleton": json.loads(json.dumps(winner.skeleton.to_dict())),
        "math_plan": json.loads(json.dumps(plan.to_dict())),
    }
    payload["math_plan"]["schema_version"] = "math-plan/v1"
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "joint"))
    repaired_winner, repaired_plan, record = runner._joint_repair(
        None,
        "model",
        runner._prompts(),
        {"target_concept": "Variability", "grade": 7},
        winner,
        plan,
        {"recommendations": [{"resource": "Mean"}, {"resource": "Number-line plots"}]},
        {"route": "design", "reason": "repair the question"},
    )
    assert repaired_winner is None
    assert repaired_plan is None
    assert record["accepted"] is False
    assert "math-plan/v2" in record["validation"][0]
