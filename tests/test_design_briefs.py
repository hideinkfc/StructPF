import json

import pytest

from scripts import design_brief_stage as stage
from scripts import run_situation_skeletons as runner
from src.generation.design_briefs import design_brief_from_payload
from src.generation.situation_skeletons import Quantity, quantity_schema_contract


def brief_payload():
    return {
        "schema_version": "design-brief/v2",
        "key_idea": "Amounts determine pigment contributions.",
        "naive_answer": "Use equal volumes and average the fractions.",
        "goal": "Choose stock amounts to meet volume and composition requirements.",
        "situation_and_rules": "Stock volumes and pigment amounts add without losses.",
        "student_question": "How much of each stock makes the required blend?",
        "approaches": [
            {
                "resources": ["Arithmetic mean"],
                "first_action": "Try equal volumes and average the stock fractions.",
                "what_it_establishes": "The composition of an equal-volume blend.",
                "limitation": "It need not meet the required fraction.",
            }
        ],
        "successful_route": "Adjust the stock amounts while accounting for pigment.",
        "learning_opportunity": "Contributions depend on amounts, not just fractions.",
        "number_requirements": ["The required fraction lies between the stock fractions."],
    }


def test_brief_round_trip_and_projection_preserve_design():
    brief = design_brief_from_payload(brief_payload(), ["Arithmetic mean"])
    assert design_brief_from_payload(brief.to_dict()) == brief
    quantity = Quantity("volume", "whole", "Required volume", unit="mL")
    skeleton = brief.skeleton((quantity,))
    assert skeleton.question == brief.student_question
    assert skeleton.number_constraints == brief.number_requirements
    assert skeleton.approaches[0].id == "brief_0"
    assert skeleton.approaches[0].procedure == brief.approaches[0].first_action


def test_discovery_notes_round_trip_without_becoming_student_question():
    payload = {
        **brief_payload(),
        "schema_version": "design-brief/v2",
        "key_idea": "Different amounts contribute different amounts of pigment.",
        "naive_answer": "Use equal volumes because their fractions average correctly.",
    }
    brief = design_brief_from_payload(payload)
    assert brief.to_dict() == payload
    assert design_brief_from_payload(brief.to_dict()) == brief
    skeleton = brief.skeleton(()).to_dict()
    assert skeleton["question"] == payload["student_question"]
    assert "key_idea" not in skeleton and "naive_answer" not in skeleton


@pytest.mark.parametrize("field", ["key_idea", "naive_answer"])
@pytest.mark.parametrize("value", [None, "", [], 7])
def test_v2_requires_substantive_discovery_notes(field, value):
    payload = {
        **brief_payload(), "schema_version": "design-brief/v2",
        "key_idea": "Amounts matter.", "naive_answer": "Use equal amounts.",
    }
    payload[field] = value
    with pytest.raises(ValueError, match=field):
        design_brief_from_payload(payload)


def test_v1_remains_unchanged_and_rejects_unversioned_discovery_notes():
    payload = brief_payload()
    for key in ("schema_version", "key_idea", "naive_answer"):
        payload.pop(key)
    brief = design_brief_from_payload(payload)
    assert brief.to_dict() == {"schema_version": "design-brief/v1", **payload}
    payload["key_idea"] = "Amounts matter."
    with pytest.raises(ValueError, match="unsupported fields"):
        design_brief_from_payload(payload)


def test_search_rejects_missing_v2_notes_instead_of_silent_legacy_fallback(monkeypatch):
    payload = brief_payload()
    for key in ("schema_version", "key_idea", "naive_answer"):
        payload.pop(key)
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (payload, "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context)
    assert result["n_valid_proposals"] == 0
    assert "requires schema_version=design-brief/v2" in result["proposals"][0]["error"]


def test_explicit_v1_search_keeps_baseline_brief_shape(monkeypatch):
    payload = brief_payload()
    for key in ("schema_version", "key_idea", "naive_answer"):
        payload.pop(key)
    responses = iter([payload, selection_payload()])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(
        None, "test", case, context, brief_schema_version="design-brief/v1"
    )
    assert len(result["winners"]) == 1
    assert result["brief_schema_version"] == "design-brief/v1"
    assert result["winners"][0].design_brief.to_dict() == {
        "schema_version": "design-brief/v1", **payload,
    }


def test_prompt_checks_discoveries_and_not_only_named_methods():
    prompts = stage._prompts()
    assert "BEFORE writing that job" in prompts["PROPOSE_BRIEF_SYSTEM"]
    assert "not observed student behaviour" in prompts["PROPOSE_BRIEF_SYSTEM"]
    assert "If all candidates disclose the idea" in prompts["SELECT_BRIEF_SYSTEM"]
    assert "both accepting and rejecting it remain open" in prompts["SELECT_BRIEF_SYSTEM"]

@pytest.mark.parametrize(
    "key",
    [
        "goal",
        "situation_and_rules",
        "student_question",
        "successful_route",
        "learning_opportunity",
    ],
)
def test_brief_requires_substantive_fields(key):
    payload = brief_payload()
    payload[key] = ""
    with pytest.raises(ValueError, match=key):
        design_brief_from_payload(payload)


def test_brief_does_not_promote_reference_material_to_prior_knowledge():
    payload = brief_payload()
    payload["approaches"][0]["resources"] = ["Weighted average reference"]
    with pytest.raises(ValueError, match="unsupported prior resources"):
        design_brief_from_payload(payload, ["Arithmetic mean"])


def test_brief_rejects_technical_fields_and_numbered_student_question():
    payload = brief_payload()
    payload["quantities"] = []
    with pytest.raises(ValueError, match="unsupported fields"):
        design_brief_from_payload(payload)
    payload.pop("quantities")
    payload["student_question"] = "Make 100 mL."
    with pytest.raises(ValueError, match="concrete numbers"):
        design_brief_from_payload(payload)


def search_inputs():
    return (
        {
            "target_concept": "Weighted averages",
            "topic": "averages",
            "grade": 7,
            "subject": "mathematics",
        },
        {"recommendations": [{"resource": "Arithmetic mean", "taught_as": "Average values."}]},
    )


def selection_payload():
    return {
        "recommended_id": 0,
        "approaches": ["brief_0"],
        "reason": "A viable comparison.",
        "main_concern": None,
        "number_requirements": [],
        "prior_contrast": None,
    }


def quantity_payload():
    return {
        "status": "translated",
        "quantities": [
            {
                "name": "required_volume",
                "role": "whole",
                "description": "Required blend volume",
                "value_source": "given",
                "unit": "mL",
                "list_length": None,
                "value_domain": "positive",
            },
        ],
    }


def test_search_moves_technical_contract_to_translation_and_preserves_brief(monkeypatch):
    responses = iter([brief_payload(), selection_payload(), quantity_payload()])
    requests = []

    def fake_chat(client, model, system, user, **kwargs):
        requests.append((system, user))
        payload = next(responses)
        return payload, "raw"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context, translate=True)
    assert result["n_valid_proposals"] == 1
    assert len(result["winners"]) == 1
    winner = result["winners"][0]
    assert winner.skeleton.question == brief_payload()["student_question"]
    assert winner.skeleton.number_constraints == tuple(brief_payload()["number_requirements"])
    assert (
        winner.to_dict()["design_brief"]["successful_route"] == brief_payload()["successful_route"]
    )
    assert "SKELETON SCHEMA (authoritative)" not in requests[0][0]
    assert "SKELETON SCHEMA (authoritative)" not in requests[1][0]
    assert "QUANTITY METADATA (authoritative)" in requests[2][0]
    assert "- approaches:" not in requests[2][0]
    assert '"id": "brief_0"' in requests[1][1]
    assert stage._rubric_guidance() in requests[0][0]


def test_quantity_only_contract_uses_shared_metadata_not_whole_skeleton():
    contract = quantity_schema_contract()
    assert "QUANTITY METADATA (authoritative)" in contract
    assert "value_source" in contract
    assert "list_length" in contract
    assert "- approaches:" not in contract


def test_brief_prompts_check_opportunity_without_forcing_familiar_methods_to_fail():
    prompts = stage._prompts()
    proposal = runner._render(
        prompts["PROPOSE_BRIEF_SYSTEM"], {"rubric_guidance": stage._rubric_guidance()}
    )
    selection = runner._render(
        prompts["SELECT_BRIEF_SYSTEM"], {"rubric_guidance": stage._rubric_guidance()}
    )
    assert "DESIGN OPPORTUNITY CHECK" in proposal
    assert "Different displays of the same calculation" in proposal
    assert "Encode any numerical relationship essential" in proposal
    assert "A successful familiar route can be useful" in proposal
    assert "routine work" in selection
    assert "neither universal failure nor a named target formula is required" in selection


def test_brief_keeps_method_success_criteria_out_of_student_wording():
    proposal = stage._prompts()["PROPOSE_BRIEF_SYSTEM"]
    assert "output-form criteria, not a checklist of properties" in proposal
    assert "target-procedure action menu" in proposal
    assert "not announcements in situation_and_rules" in proposal
    assert "criteria for judging an invented method in situation_and_rules" not in proposal


def test_search_reports_unsupported_without_narrowing_goal(monkeypatch):
    responses = iter(
        [
            brief_payload(),
            selection_payload(),
            {"status": "unsupported", "reason": "Cannot encode a whole allocation."},
        ]
    )
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context, translate=True)
    assert result["winners"] == []
    assert result["translation"]["status"] == "unsupported"
    assert "whole allocation" in result["translation"]["error"]
    assert result["brief_selection"]["selected_brief"]["goal"] == brief_payload()["goal"]


def test_translation_cannot_replace_question_or_requirements(monkeypatch):
    changed = {**quantity_payload(), "student_question": "Who gets one piece?"}
    responses = iter([brief_payload(), selection_payload(), changed, changed])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context, translate=True)
    assert result["winners"] == []
    assert result["translation"]["status"] == "invalid"
    assert len(result["translation"]["attempts"]) == 2


def test_translation_carries_central_numerical_contrast_to_existing_plan(monkeypatch):
    intent = {
        "approach_id": "brief_0",
        "operational_move": "Choose half the required blend volume as the stronger-stock amount.",
        "checkability": "numerical",
        "reason": "The brief depends on equal volumes not meeting the requested composition.",
    }
    translated = {**quantity_payload(), "prior_contrast": intent}
    responses = iter([brief_payload(), selection_payload(), translated])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context, translate=True)
    winner = result["winners"][0]
    assert winner.prior_contrast.approach_id == "brief_0"
    assert runner._design_context(winner)["prior_contrast"]["checkability"] == "numerical"


def test_translation_rejects_unknown_contrast_approach(monkeypatch):
    translated = {
        **quantity_payload(),
        "prior_contrast": {
            "approach_id": "missing",
            "operational_move": "Unlisted operation.",
            "checkability": "numerical",
            "reason": "Not supported by the selected brief.",
        },
    }
    responses = iter([brief_payload(), selection_payload(), translated, translated])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context, translate=True)
    assert result["winners"] == []
    assert "unknown brief approach" in result["translation"]["error"]


def test_reference_context_reaches_all_design_brief_calls(monkeypatch):
    responses = iter([brief_payload(), selection_payload(), quantity_payload()])
    requests = []
    monkeypatch.setattr(runner, "_format_prior_context", lambda context: "PRIOR\nLC REFERENCES")

    def fake_chat(client, model, system, user, **kwargs):
        requests.append(user)
        return next(responses), "raw"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    case, context = search_inputs()
    stage.run_design_brief_search(None, "test", case, context, translate=True)
    assert len(requests) == 3
    assert all("LC REFERENCES" in user for user in requests)


def test_saved_winner_keeps_original_design_context(tmp_path, monkeypatch):
    responses = iter([brief_payload(), selection_payload(), quantity_payload()])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    winner = stage.run_design_brief_search(None, "test", case, context)["winners"][0]
    saved = tmp_path / "result.json"
    saved.write_text(json.dumps({"case": "example", "winner": winner.to_dict()}))
    restored = runner._winner_from_result(saved, "example")
    assert restored.design_brief == winner.design_brief
    assert (
        runner._design_context(restored)["original_design_brief"] == winner.design_brief.to_dict()
    )


def test_no_valid_brief_is_explicit_and_repeated_rejection_returns_flagged_brief(monkeypatch):
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (None, ""))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context)
    assert result["n_valid_proposals"] == 0
    assert result["judge_error"] == "no valid design briefs to select"
    assert len(result["proposals"][0]["attempts"]) == 2
    rejected = {
        "recommended_id": None, "approaches": [], "reason": "The goal is not attainable.",
        "main_concern": "Feasibility", "number_requirements": [], "prior_contrast": None,
    }
    responses = iter([brief_payload(), rejected] * 3)
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    result = stage.run_design_brief_search(None, "test", case, context)
    assert len(result["winners"]) == 1
    assert result["winners"][0].candidate_id == 2
    assert result["quality_status"] == "review_needed"
    assert result["quality_findings"] == ["The goal is not attainable."]
    assert len(result["selection_attempts"]) == 3
    assert result["brief_selection"]["continuation"] == "latest_usable_brief"
    assert result["translation"] is None
    assert "attainable" in result["brief_selection"]["payload"]["reason"]


def test_selection_concern_is_revised_and_kept_in_history(monkeypatch):
    concern = {**selection_payload(), "main_concern": "Student question reveals the method."}
    revised = {**brief_payload(), "student_question": "What stock amounts would you choose?"}
    responses = iter([
        brief_payload(), concern, revised, {**selection_payload(), "recommended_id": 1},
    ])
    requests = []

    def chat(*args, **kwargs):
        requests.append(args[3])
        return next(responses), "raw"

    monkeypatch.setattr(runner, "chat_json", chat)
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context)
    assert result["quality_status"] == "no_selection_concern"
    assert result["quality_findings"] == []
    assert result["winners"][0].design_brief.student_question == revised["student_question"]
    assert "Student question reveals the method." in requests[2]
    assert result["selection_attempts"][0]["payload"] == concern


def test_unparseable_selector_does_not_discard_usable_brief(monkeypatch):
    responses = iter([brief_payload(), None] * 3)
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context)
    assert len(result["winners"]) == 1
    assert result["quality_findings"] == ["unparseable design brief selection"]
    assert result["selection_attempts"][-1]["error"] == "unparseable design brief selection"


def test_default_search_stops_at_selected_brief(monkeypatch):
    responses = iter([brief_payload(), selection_payload()])
    monkeypatch.setattr(runner, "chat_json", lambda *args, **kwargs: (next(responses), "raw"))
    case, context = search_inputs()
    result = stage.run_design_brief_search(None, "test", case, context)
    winner = result["winners"][0]
    assert winner.design_brief.to_dict()["goal"] == brief_payload()["goal"]
    assert winner.skeleton.quantities == ()
    assert result["translation"] is None
    assert winner.skeleton.number_constraints == tuple(brief_payload()["number_requirements"])


def test_external_feedback_stays_paired_with_the_selected_design(monkeypatch):
    first = {**brief_payload(), "goal": "Selected original design"}
    second = {**brief_payload(), "goal": "Other newer design"}
    concern = {**selection_payload(), "recommended_id": 0, "main_concern": "Revise selected goal."}
    responses = iter([first, second, concern, first, selection_payload()])
    requests = []

    def chat(*args, **kwargs):
        requests.append(args[3])
        return next(responses), "raw"

    monkeypatch.setattr(runner, "chat_json", chat)
    case, context = search_inputs()
    result = stage.run_design_brief_search(
        None, "test", case, context, k=2, design_feedback="Frozen coverage evidence",
    )
    assert "Frozen coverage evidence" in requests[0]
    assert "Frozen coverage evidence" in requests[1]
    assert "Selected original design" in requests[3]
    assert "Other newer design" not in requests[3]
    assert "Frozen coverage evidence" in requests[3]
    assert result["design_feedback"] == "Frozen coverage evidence"
