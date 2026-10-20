import json
from copy import deepcopy
from dataclasses import replace

import pytest

from scripts import design_data_stage as stage
from scripts import run_situation_skeletons as runner
from src.generation.design_briefs import design_brief_from_payload
from src.generation.design_data import proposal_from_payload, validate_values
from src.generation.situation_skeletons import JudgedCandidate


def proposal_payload():
    return {
        "quantities": {
            "distance": {"description": "Section distances", "unit": "km", "role": "given"},
            "minutes": {"description": "Section times", "unit": "min", "role": "given"},
        },
        "values": {"distance": [2, 2, 2], "minutes": [20, 20, 40]},
        "conditions": [
            {
                "statement": "All section times are positive.",
                "requirement_indices": [0],
                "essential": True,
                "calculation": {"expressions": {}, "predicate": "min(minutes) > 0"},
                "judgment": None,
                "reasoning": "Positive times make all section speeds defined.",
            }
        ],
    }


def test_proposal_retains_requirements_and_signed_data():
    proposal = proposal_payload()
    proposal["values"]["distance"][0] = -2
    assert proposal_from_payload(proposal, ["All section times are positive."]) is proposal


def test_computed_condition_does_not_need_a_redundant_null_judgment():
    proposal = proposal_payload()
    del proposal["conditions"][0]["judgment"]
    assert proposal_from_payload(proposal, ["Positive times"]) == proposal


@pytest.mark.parametrize("role", [None, "", "answer", 1, [], {}])
def test_quantity_roles_reject_invalid_labels(role):
    proposal = proposal_payload()
    proposal["quantities"]["distance"]["role"] = role
    with pytest.raises(ValueError, match="role must be"):
        proposal_from_payload(proposal, ["Positive times"])


def test_historical_unlabeled_data_remain_readable_but_new_proposals_require_roles():
    proposal = proposal_payload()
    for metadata in proposal["quantities"].values():
        del metadata["role"]
    assert proposal_from_payload(proposal, ["Positive times"]) is proposal
    with pytest.raises(ValueError, match="role is required"):
        proposal_from_payload(proposal, ["Positive times"], require_roles=True)


def test_new_unlabeled_proposal_consumes_retry_budget(monkeypatch):
    original = proposal_payload()
    del original["quantities"]["distance"]["role"]
    result, requests = run_loop(monkeypatch, [original, proposal_payload()])
    assert result["accepted"] and len(requests) == 2
    assert "role is required" in result["attempts"][0]["error"]


def test_model_opinion_does_not_override_a_calculated_condition(monkeypatch):
    original = proposal_payload()
    original["conditions"][0]["judgment"] = "fails"
    result, _ = run_loop(monkeypatch, [original])
    assert result["accepted"]
    assert result["check"]["conditions"][0]["status"] == "holds"


def test_missing_requirement_is_not_silently_ignored():
    with pytest.raises(ValueError, match="omit original requirements"):
        proposal_from_payload(proposal_payload(), ["Positive times", "Distinct winners"])


def test_cannot_mark_original_requirement_nonessential():
    proposal = proposal_payload()
    proposal["conditions"][0]["essential"] = False
    with pytest.raises(ValueError, match="must be essential"):
        proposal_from_payload(proposal, ["Positive times"])


@pytest.mark.parametrize("value", [True, "2/3", float("nan"), [], [float("inf")]])
def test_invalid_numeric_input(value):
    proposal = proposal_payload()
    proposal["values"]["minutes"] = value
    with pytest.raises(ValueError):
        proposal_from_payload(proposal, ["Positive times"])


def test_repairs_preserve_names_and_data_sizes():
    proposal = proposal_payload()
    repaired = deepcopy(proposal["values"])
    repaired["minutes"] = [25, 25, 25]
    assert validate_values(repaired, proposal["quantities"], proposal["values"]) == repaired
    repaired["minutes"] = [25, 25]
    with pytest.raises(ValueError, match="number of entries"):
        validate_values(repaired, proposal["quantities"], proposal["values"])
    with pytest.raises(ValueError, match="exactly"):
        validate_values({"minutes": [25, 25, 25]}, proposal["quantities"])


def loop_inputs():
    brief = design_brief_from_payload(
        {
            "goal": "Compare journeys",
            "situation_and_rules": "Teams traverse equal routes.",
            "student_question": "Which journey was faster?",
            "approaches": [
                {
                    "resources": ["Arithmetic"],
                    "first_action": "Compare the times.",
                    "what_it_establishes": "A useful comparison.",
                }
            ],
            "successful_route": "Account for the whole journey.",
            "learning_opportunity": "Relate time and distance.",
            "number_requirements": ["All section times are positive."],
        }
    )
    return (
        {"target_concept": "Average speed", "grade": 7},
        JudgedCandidate(
            candidate_id=0,
            skeleton=brief.skeleton(()),
            verdicts=(),
            practice_item=False,
            target_named=False,
            activation_count=1,
            design_brief=brief,
        ),
        {"recommendations": [{"resource": "Arithmetic"}]},
    )


def test_v2_notes_are_internal_writer_evidence_not_student_draft():
    case, winner, context = loop_inputs()
    brief = replace(
        winner.design_brief,
        schema_version="design-brief/v2",
        key_idea="Whole-journey distance divided by whole-journey time.",
        naive_answer="Average the section speeds equally.",
    )
    winner = replace(winner, design_brief=brief)
    request = stage._writer_request(
        case, winner, {"payload": proposal_payload(), "check": {}}, context
    )
    sources = stage._writer_sources(winner, proposal_payload())
    assert sources["design_brief.key_idea"] == brief.key_idea
    assert sources["design_brief.naive_answer"] == brief.naive_answer
    assert '"source": "design_brief.key_idea"' in request["user"]
    assert '"source": "design_brief.naive_answer"' in request["user"]
    assert "Do not state or imply" in request["user"]
    legacy_sources = stage._writer_sources(loop_inputs()[1], proposal_payload())
    assert "design_brief.key_idea" not in legacy_sources
    assert "design_brief.naive_answer" not in legacy_sources


def run_loop(monkeypatch, responses, *, initial_proposal=None):
    requests = []
    responses = iter(responses)

    def fake_chat(client, model, system, user, **kwargs):
        requests.append((system, user))
        return next(responses), "saved raw response"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    case, winner, context = loop_inputs()
    return stage.run_design_data(
        None, "test", case, winner, context, initial_proposal=initial_proposal
    ), requests


def test_exact_feedback_repairs_only_numbers(monkeypatch):
    original = proposal_payload()
    original["values"]["minutes"] = [20, 20, -40]
    repaired = {"values": {"distance": [2, 2, 2], "minutes": [20, 20, 40]}}
    result, requests = run_loop(monkeypatch, [original, repaired])
    assert result["accepted"]
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["check"]["conditions"][0]["status"] == "fails"
    assert '"computed"' in requests[1][1]
    assert result["payload"]["conditions"] == original["conditions"]
    assert result["payload"]["quantities"] == original["quantities"]
    assert result["payload"]["values"] == repaired["values"]
    assert result["attempts"][0]["payload"]["values"]["minutes"][2] == -40
    assert result["source_hashes"] and result["prompt_snapshot"]
    assert result["source_integrity_verified"]


def test_failed_values_exhaust_the_same_three_call_budget(monkeypatch):
    original = proposal_payload()
    original["values"]["minutes"] = [-20, 20, 40]
    result, requests = run_loop(
        monkeypatch, [original, {"values": original["values"]}, {"values": original["values"]}]
    )
    assert result["status"] == "rejected"
    assert len(requests) == 3
    assert result["attempts"][-1]["check"]["conditions"][0]["status"] == "fails"
    assert result["proceed"]
    assert result["quality_findings"] == ["All section times are positive."]


def test_bad_json_and_omitted_requirement_consume_budget(monkeypatch):
    omitted = proposal_payload()
    omitted["conditions"][0]["requirement_indices"] = []
    result, requests = run_loop(monkeypatch, [None, omitted, proposal_payload()])
    assert result["accepted"] and len(requests) == 3
    assert "omit original requirements" in result["attempts"][1]["error"]


def test_repair_cannot_change_formulas_or_drop_values(monkeypatch):
    original = proposal_payload()
    original["values"]["minutes"] = [-20, 20, 40]
    changed = deepcopy(original)
    changed["conditions"][0]["calculation"]["predicate"] = "1 == 1"
    result, requests = run_loop(monkeypatch, [original, changed, {"values": {"minutes": [1]}}])
    assert not result["accepted"] and result["status"] == "invalid"
    assert len(requests) == 3
    assert result["payload"]["conditions"] == original["conditions"]
    assert "conditions remain frozen" in result["attempts"][1]["error"]


@pytest.mark.parametrize("judgment", ["holds", "uncertain"])
def test_uncomputed_essential_condition_continues_without_pointless_repairs(monkeypatch, judgment):
    original = proposal_payload()
    original["conditions"][0].update(
        calculation=None,
        judgment=judgment,
        reasoning=(
            'Original requirement says "All section times are positive."; '
            "this asserts the desired conclusion but does not establish it."
            if judgment == "uncertain"
            else 'Context rule says "Elapsed times are positive". This explicitly defines a rule.'
        ),
    )
    result, requests = run_loop(monkeypatch, [original])
    assert result["accepted"] and len(requests) == 1
    check = result["check"]
    assert check["conditions"][0]["status"] == (
        "model_judged" if judgment == "holds" else "unverified"
    )
    assert bool(check["warnings"]) is (judgment == "uncertain")
    assert check["warnings"] == check["unresolved"]
    assert "computed conditions hold" not in check["reason"]


@pytest.mark.parametrize("numeric_failure", [False, True])
def test_textual_failure_requires_design_correction_not_numbers_only_repair(
    monkeypatch, numeric_failure
):
    original = proposal_payload()
    original["conditions"].append(
        {
            "statement": "Subdivision is allowed.",
            "requirement_indices": [],
            "essential": True,
            "calculation": None,
            "judgment": "fails",
            "reasoning": 'Design rules say "No subdivision" and "Subdivision is allowed".',
        }
    )
    if numeric_failure:
        original["values"]["minutes"][0] = -20
    responses = [original] + ([{"values": proposal_payload()["values"]}] if numeric_failure else [])
    result, requests = run_loop(monkeypatch, responses)
    assert result["status"] == "review_needed"
    assert len(requests) == (2 if numeric_failure else 1)
    assert result["proceed"] and result["quality_findings"]
    assert result["check"]["textual_failures"]
    assert not result["check"]["failures"]
    assert result["check"]["conditions"][1]["judgment"] == "fails"
    assert result["error"] == result["check"]["reason"]


def test_uncertainty_does_not_hide_a_repairable_numerical_failure(monkeypatch):
    original = proposal_payload()
    original["values"]["minutes"][0] = -20
    original["conditions"].append(
        {
            "statement": "The task invites different methods.",
            "requirement_indices": [],
            "essential": True,
            "calculation": None,
            "judgment": "uncertain",
            "reasoning": "Needs student response evidence.",
        }
    )
    result, requests = run_loop(monkeypatch, [original, {"values": proposal_payload()["values"]}])
    assert result["accepted"] and len(requests) == 2
    assert result["attempts"][0]["check"]["status"] == "rejected"
    assert result["check"]["warnings"] == result["check"]["unresolved"]
    assert result["check"]["warnings"] and not result["check"]["failures"]
    assert result["payload"]["conditions"] == original["conditions"]


def test_optional_textual_failure_warns_without_blocking(monkeypatch):
    original = proposal_payload()
    original["conditions"].append(
        {
            "statement": "The context is everyday.",
            "requirement_indices": [],
            "essential": False,
            "calculation": None,
            "judgment": "fails",
            "reasoning": "The setting uses imaginary units.",
        }
    )
    result, _ = run_loop(monkeypatch, [original])
    assert result["accepted"] and result["check"]["warnings"]
    assert not result["check"]["textual_failures"]


def test_optional_student_prediction_is_not_mathematical_evidence(monkeypatch):
    original = proposal_payload()
    original["conditions"].append(
        {
            "statement": "Students may compare section times.",
            "requirement_indices": [],
            "essential": False,
            "calculation": None,
            "judgment": "uncertain",
            "reasoning": "Needs student response evidence.",
        }
    )
    result, _ = run_loop(monkeypatch, [original])
    assert result["accepted"]
    assert result["check"]["conditions"][1]["status"] == "unverified"
    assert result["check"]["warnings"]


def test_given_unit_metadata_can_be_checked_without_a_model_review(monkeypatch):
    original = proposal_payload()
    original["conditions"].append(
        {
            "statement": "Distances use kilometres and times use minutes.",
            "requirement_indices": [],
            "essential": True,
            "calculation": {
                "expressions": {},
                "predicate": 'unit(distance) == "km" and unit(minutes) == "min"',
            },
            "reasoning": "Check the fixed unit declarations directly.",
        }
    )
    result, requests = run_loop(monkeypatch, [original])
    assert result["accepted"] and len(requests) == 1
    assert result["check"]["conditions"][1]["status"] == "holds"


@pytest.mark.parametrize(
    ("calculation", "status"),
    [
        ({"expressions": {}, "predicate": "magic(minutes) > 0"}, "unsupported"),
        ({"expressions": {}, "predicate": "missing > 0"}, "unknown"),
        ({"expressions": {}, "predicate": "k > 0", "symbols": {"k": "real"}}, "unknown"),
    ],
)
def test_unresolved_calculation_warns_without_claiming_bad_numbers(
    monkeypatch, calculation, status
):
    original = proposal_payload()
    original["conditions"][0]["calculation"] = calculation
    result, requests = run_loop(monkeypatch, [original])
    assert result["accepted"] and len(requests) == 1
    assert result["check"]["conditions"][0]["status"] == status
    assert result["check"]["warnings"] and not result["check"]["failures"]
    assert result["error"] is None


def test_resume_rechecks_accepted_data_without_regenerating(monkeypatch):
    original = proposal_payload()
    result, requests = run_loop(monkeypatch, [], initial_proposal=original)
    assert result["accepted"] and requests == []
    assert result["attempts"] == []
    assert result["initial_proposal"] == original
    assert result["initial_check"]["accepted"]


def test_resume_retains_initial_failed_values_after_repair(monkeypatch):
    original = proposal_payload()
    original["values"]["minutes"][0] = -20
    repair = {"values": proposal_payload()["values"]}
    result, requests = run_loop(monkeypatch, [repair], initial_proposal=original)
    assert result["accepted"] and len(requests) == 1
    assert result["initial_proposal"] == original
    assert result["initial_check"]["status"] == "rejected"
    assert result["payload"]["values"] == repair["values"]
    assert result["initial_proposal"]["values"]["minutes"][0] == -20


def test_source_changes_are_recorded_not_hidden(monkeypatch):
    snapshots = iter([{"calculator": "before"}, {"calculator": "after"}])
    monkeypatch.setattr(stage, "_source_hashes", lambda: next(snapshots))
    result, _ = run_loop(monkeypatch, [proposal_payload()])
    assert result["source_hashes"] == {"calculator": "before"}
    assert result["source_hashes_after"] == {"calculator": "after"}
    assert result["source_integrity_verified"] is False


@pytest.mark.parametrize("uncertain", [False, True])
def test_writer_receives_fixed_data_and_evidence_not_old_math_plan(monkeypatch, uncertain):
    case, winner, context = loop_inputs()
    proposal = proposal_payload()
    if uncertain:
        proposal["conditions"].append(
            {
                "statement": "The context is realistic.",
                "requirement_indices": [],
                "essential": True,
                "calculation": None,
                "judgment": "uncertain",
                "reasoning": "No supporting wording found.",
            }
        )
    result, _ = run_loop(monkeypatch, [proposal])
    requests = []

    def fake_chat(client, model, system, user, **kwargs):
        requests.append((system, user))
        return {
            "status": "ready",
            "blocking_issues": [],
            "title": "Compare journeys",
            "body": "Section distances: 2, 2, 2 km.",
            "question": "Explain your comparison.",
            "withheld": [],
        }, "writer raw"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    task, raw = stage.write_design_data_task(None, "test", case, winner, result, context)
    assert task["status"] == "ready" and raw == "writer raw"
    assert '"minutes": [20, 20, 40]' in requests[0][1]
    assert '"status": "holds"' in requests[0][1]
    assert "Do not disclose" in requests[0][0]
    assert "math_plan" not in requests[0][1]
    assert "evidence alone is not a reason to stop writing" in requests[0][0]
    if uncertain:
        assert (
            '"warnings": ["The context is realistic.: No supporting wording found."]'
            in requests[0][1]
        )
        assert "present an unsupported conclusion as established" in requests[0][0]


def test_writer_separates_candidate_wording_from_teacher_evidence():
    case, winner, context = loop_inputs()
    request = stage._writer_request(
        case, winner, {"payload": proposal_payload(), "check": {"accepted": True}}, context
    )
    assert "FIXED GIVEN DATA AND CONDITIONS" not in request["user"]
    assert "TEACHER-ONLY TASK-SPECIFIC DO-NOT-STATE EVIDENCE" in request["user"]
    assert "design_brief.approaches[0].what_it_establishes" in request["user"]
    assert "design_brief.successful_route" in request["user"]
    assert "proposal.conditions[0].statement" in request["user"]
    assert "Rahimi" not in request["system"]
    assert "WITHHOLD computed properties" in request["system"]
    assert 'Keep an answer-form criterion such as "one number"' in request["system"]
    assert "This overrides copying the" in request["system"]
    assert "including zero" in request["system"]
    assert "NOT properties the target method" in request["system"]
    assert "without an extra" in request["system"]
    assert "output requirements in the goal" in request["system"]
    assert "design_brief.goal" in request["user"]


@pytest.mark.parametrize("all_examples", [False, True])
def test_teacher_examples_are_checked_but_excluded_from_student_data(all_examples):
    from src.generation.design_data import check_proposal

    case, winner, context = loop_inputs()
    proposal = proposal_payload()
    proposal["quantities"]["minutes"]["role"] = "teacher_example"
    if all_examples:
        proposal["quantities"]["distance"]["role"] = "teacher_example"
    checked = check_proposal(proposal)
    assert checked["conditions"][0]["status"] == "holds"
    request = stage._writer_request(case, winner, {"payload": proposal, "check": checked}, context)
    user = request["user"]
    data = json.loads(
        user.split(
            "STUDENT-DATA CANDIDATES (GIVEN OR HISTORICAL UNLABELED; TEACHER EXAMPLES EXCLUDED):\n"
        )[1].split("\nTEACHER-ONLY TASK-SPECIFIC")[0]
    )
    assert "minutes" not in data["values"]
    assert "minutes" not in data["quantities"]
    assert data["values"] == ({} if all_examples else {"distance": [2, 2, 2]})
    evidence = json.loads(
        user.split("TEACHER-ONLY TASK-SPECIFIC DO-NOT-STATE EVIDENCE:\n")[1].split(
            "\nTEACHER-ONLY CHECK"
        )[0]
    )
    example = next(item for item in evidence if item.get("role") == "teacher_example")
    assert example["values"] == ([2, 2, 2] if all_examples else [20, 20, 40])
    assert "check that the open" in stage._prompts()["PROPOSE_DATA_SYSTEM"]
    assert "empty student-data object is not missing information" in request["system"]


def test_historical_unlabeled_writer_data_are_not_silently_hidden():
    case, winner, context = loop_inputs()
    proposal = proposal_payload()
    for metadata in proposal["quantities"].values():
        del metadata["role"]
    request = stage._writer_request(case, winner, {"payload": proposal, "check": {}}, context)
    assert '"minutes": [20, 20, 40]' in request["user"].split("\nTEACHER-ONLY")[0]


def writer_payload():
    return {
        "status": "ready",
        "blocking_issues": [],
        "title": "Journeys",
        "body": "Compare the journey records.",
        "question": "Explain your reasoning.",
        "withheld": [],
    }


@pytest.mark.parametrize(
    ("body", "warning_count"),
    [("Use 20, 20, 40.", 1), ("Use 20, 40.", 0), ("Choose your own lengths.", 0)],
)
def test_teacher_example_screen_counts_repetitions_without_blocking(body, warning_count):
    _, winner, _ = loop_inputs()
    proposal = proposal_payload()
    proposal["quantities"]["minutes"]["role"] = "teacher_example"
    payload = {**writer_payload(), "body": body}
    task = stage._validate_writer_payload(payload, winner, proposal)
    assert task["status"] == "ready"
    assert len(task["teacher_example_warnings"]) == warning_count
    if warning_count:
        assert "nonblocking screen" in task["teacher_example_warnings"][0]["reason"]
        assert task["teacher_example_warnings"][0]["source"].endswith("minutes.description")


def test_teacher_example_screen_handles_nested_signed_zero_and_decimal_values():
    _, winner, _ = loop_inputs()
    proposal = proposal_payload()
    proposal["quantities"]["minutes"]["role"] = "teacher_example"
    proposal["values"]["minutes"] = [[0, -2], [0.5, 0.5]]
    task = stage._validate_writer_payload(
        {**writer_payload(), "body": "0, -2, 5e-1, .5"}, winner, proposal
    )
    assert len(task["teacher_example_warnings"]) == 1


def test_blocked_writer_does_not_run_a_success_shaped_leak_screen():
    _, winner, _ = loop_inputs()
    proposal = proposal_payload()
    proposal["quantities"]["minutes"]["role"] = "teacher_example"
    payload = {"status": "blocked", "blocking_issues": ["Conflicting rules."], "withheld": []}
    assert stage._validate_writer_payload(payload, winner, proposal) == payload


def test_writer_retains_grounded_withheld_records():
    _, winner, _ = loop_inputs()
    payload = writer_payload()
    payload["withheld"] = [
        {
            "kind": "discovery",
            "source": "design_brief.successful_route",
            "quote": "Account for the whole journey.",
            "reason": "Students choose how to combine records.",
        },
        {
            "kind": "quantity",
            "source": "proposal.quantities.distance.description",
            "quote": "Section distances",
            "reason": "Synthetic schema test, not a valid withholding judgment.",
        },
    ]
    assert stage._validate_writer_payload(payload, winner, proposal_payload()) == payload


@pytest.mark.parametrize(
    "defect", ["missing", "invented_source", "invented_quote", "partial_quantity", "wrong_kind"]
)
def test_writer_revises_invalid_withheld_records_then_returns_flagged_draft(monkeypatch, defect):
    case, winner, context = loop_inputs()
    payload = writer_payload()
    payload["withheld"] = [
        {
            "kind": "quantity",
            "source": "proposal.quantities.distance.description",
            "quote": "Section distances",
            "reason": "Teacher evidence.",
        }
    ]
    if defect == "missing":
        del payload["withheld"]
    elif defect == "invented_source":
        payload["withheld"][0]["source"] = "invented"
    elif defect == "invented_quote":
        payload["withheld"][0]["quote"] = "An absent result."
    elif defect == "partial_quantity":
        payload["withheld"][0]["quote"] = "distances"
    else:
        payload["withheld"][0]["kind"] = "guess"
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "raw"))
    task, raw = stage.write_design_data_task(
        None, "test", case, winner, {"payload": proposal_payload(), "check": {}}, context
    )
    assert task["status"] == "ready" and not task["blocking_issues"]
    assert task["quality_status"] == "review_needed" and task["quality_findings"]
    assert task["withheld_validation_status"] == "unverified"
    assert len(task["writer_attempts"]) == 3
    assert task["writer_attempts"][0]["payload"] == payload
    assert raw == "raw"


def test_writer_quote_mismatch_is_repaired_without_losing_history(monkeypatch):
    case, winner, context = loop_inputs()
    original = writer_payload()
    original["withheld"] = [
        {
            "kind": "discovery",
            "source": "design_brief.successful_route",
            "quote": "Invented quote",
            "reason": "Internal method.",
        }
    ]
    repaired = deepcopy(original)
    repaired["withheld"][0]["quote"] = winner.design_brief.successful_route
    responses = iter([original, repaired])
    requests = []

    def chat(*args, **kwargs):
        requests.append(args[3])
        return next(responses), "raw"

    monkeypatch.setattr(runner, "chat_json", chat)
    task, _ = stage.write_design_data_task(
        None, "test", case, winner, {"payload": proposal_payload(), "check": {}}, context
    )
    assert task["status"] == "ready" and task["quality_findings"] == []
    assert len(task["writer_attempts"]) == 2
    assert task["writer_selected_attempt"] == 1
    assert "withheld quote must occur verbatim" in requests[1]
    assert task["writer_attempts"][0]["payload"] == original


def test_writer_retries_refusal_and_keeps_unresolved_data_findings(monkeypatch):
    case, winner, context = loop_inputs()
    responses = iter(
        [
            {"status": "blocked", "blocking_issues": ["Unresolved data"], "withheld": []},
            writer_payload(),
        ]
    )
    requests = []

    def chat(*args, **kwargs):
        requests.append(args[3])
        return next(responses), "raw"

    monkeypatch.setattr(runner, "chat_json", chat)
    task, _ = stage.write_design_data_task(
        None,
        "test",
        case,
        winner,
        {"payload": proposal_payload(), "check": {}, "quality_findings": ["Failed condition"]},
        context,
    )
    assert task["status"] == "ready" and len(task["writer_attempts"]) == 2
    assert task["quality_findings"] == ["Failed condition"]
    assert "Failed condition" in requests[0]
    assert "INTERNAL UNRESOLVED FINDINGS" in requests[0]


def test_writer_with_no_usable_text_raises_real_error_after_retries(monkeypatch):
    case, winner, context = loop_inputs()
    monkeypatch.setattr(runner, "chat_json", lambda *a, **kw: (None, "unparseable"))
    with pytest.raises(ValueError, match="no usable task after 3 calls"):
        stage.write_design_data_task(
            None, "test", case, winner, {"payload": proposal_payload(), "check": {}}, context
        )


def test_writer_does_not_hide_api_errors_as_drafts(monkeypatch):
    case, winner, context = loop_inputs()

    def chat(*args, **kwargs):
        raise RuntimeError("API unavailable")

    monkeypatch.setattr(runner, "chat_json", chat)
    with pytest.raises(RuntimeError, match="API unavailable"):
        stage.write_design_data_task(
            None, "test", case, winner, {"payload": proposal_payload(), "check": {}}, context
        )


def test_writer_keeps_last_usable_draft_when_later_reply_is_unusable(monkeypatch):
    case, winner, context = loop_inputs()
    original = writer_payload()
    del original["withheld"]
    responses = iter([(original, "draft raw"), (None, "bad raw"), (None, "bad raw")])
    monkeypatch.setattr(runner, "chat_json", lambda *a, **kw: next(responses))
    task, raw = stage.write_design_data_task(
        None, "test", case, winner, {"payload": proposal_payload(), "check": {}}, context
    )
    assert task["status"] == "ready" and raw == "draft raw"
    assert task["writer_selected_attempt"] == 0
    assert len(task["writer_attempts"]) == 3
    assert "writer response must be a JSON object" in task["quality_findings"]


def test_textual_prompt_requires_grounded_quotes_and_distinguishes_absent_support():
    prompt = stage._prompts()["PROPOSE_DATA_SYSTEM"]
    assert "Quote the relevant wording from the supplied design or context" in prompt
    assert "Copy short, contiguous fragments verbatim" in prompt
    assert "Assess a stated rule separately from any" in prompt
    assert "No supporting wording found." in prompt
    assert "Repeating a mathematical conclusion is not justification" in prompt
    assert "Do not invent missing assumptions" in prompt
    assert "invented 0/1 flag" in prompt
    assert "Split mixed numerical and textual requirements into separate conditions" in prompt
    assert '"uncertain" for missing, ambiguous, or insufficient support' in prompt
    assert "not independently verified proofs" in prompt


def test_all_active_prompts_explicitly_request_json():
    prompts = stage._prompts()
    for key in ("PROPOSE_DATA_SYSTEM", "REPAIR_DATA_SYSTEM", "WRITE_DATA_TASK_SYSTEM"):
        assert "JSON" in prompts[key]


@pytest.mark.parametrize("saved_data", [False, True])
@pytest.mark.parametrize("container", ["direct", "diagnostic", "benchmark"])
@pytest.mark.parametrize("resume_mode", ["resume", "replan", "no_fill"])
def test_cli_resumes_new_design_with_frozen_case_and_optional_data(
    tmp_path, monkeypatch, saved_data, container, resume_mode
):
    case, winner, context = loop_inputs()
    data_run = None
    if saved_data:
        data_run, _ = run_loop(monkeypatch, [proposal_payload()])
        data_run["check"].pop("warnings")
        data_run["check"].pop("textual_failures")
    source = tmp_path / "source.json"
    previous = {"status": "review_needed", "attempts": [{"raw_text": "earlier run"}]}
    saved = {
        "schema_version": "pf-design-data/v1",
        "case": "example",
        "case_input": case,
        "prior_context": context,
        "winner": winner.to_dict(),
        "design_data": data_run,
        "design_data_history": [previous],
    }
    if container != "direct":
        source_stage = {
            key: saved.pop(key) for key in ("winner", "design_data", "design_data_history")
        }
        saved["schema_version"] = "pf-diagnostic/v2" if container == "diagnostic" else "benchmark"
        if container == "diagnostic":
            saved["stages"] = {"D2_D3": source_stage}
        else:
            saved["d2"] = source_stage
    original = json.dumps(saved)
    source.write_text(original)
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
            "--output",
            str(output),
        ]
        + (["--replan"] if resume_mode == "replan" else [])
        + (["--no-fill"] if resume_mode == "no_fill" else []),
    )
    monkeypatch.setattr(
        runner, "_load_case", lambda _: pytest.fail("Replay must use the frozen case snapshot")
    )
    monkeypatch.setattr(runner, "load_client", lambda _: (None, "test"))
    calls = []

    def fake_chat(client, model, system, user, **kwargs):
        calls.append(system)
        assert "Changed config" not in user
        return proposal_payload(), "new data"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    monkeypatch.setattr(
        runner,
        "_write_design_data_task",
        lambda *a: (
            {
                "status": "ready",
                "title": "Task",
                "body": "Data",
                "question": "Explain",
                "blocking_issues": [],
            },
            "writer",
        ),
    )
    monkeypatch.setattr(
        runner, "_plan_until_reviewed", lambda *a: pytest.fail("Do not use the legacy plan")
    )
    runner.main()
    result = json.loads(output.read_text())
    assert result["case_input"] == case
    assert source.read_text() == original
    if resume_mode == "no_fill":
        assert result["design_data"] == data_run
        assert result["task"] is None and calls == []
    else:
        assert result["design_data"]["accepted"]
        assert len(calls) == (0 if saved_data and resume_mode == "resume" else 1)
        assert result["task"]["status"] == "ready"
    assert result["design_data_history"] == [previous] + (
        [data_run] if saved_data and resume_mode != "no_fill" else []
    )
