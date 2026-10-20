import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.run_prior_recommendations as runner
from scripts.learning_commons_context import retrieve_context
from scripts.run_prior_recommendations import (
    _cap_candidates,
    _curated_evidence,
    _possible_matches,
    _prompt_evidence,
)
from src.generation.prior_recommendations import (
    PriorMethodRecommendation,
    Provenance,
    ResourceCandidate,
)


def test_recommendation_schema_requires_a_specific_shortcoming():
    with pytest.raises(ValueError, match="falls_short_because"):
        PriorMethodRecommendation.from_payload(
            {
                "resource": "Range",
                "taught_as": "maximum minus minimum",
                "student_move": "subtract the extremes",
            },
            provenance=Provenance(type="paper", source="test"),
            condition="grounded",
        )


def test_prompt_evidence_omits_ready_made_resource_labels():
    rendered = _prompt_evidence([{
        "evidence_id": "curriculum:demo",
        "resource": "Ratio and proportion",
        "taught_as": "Ratio and proportion",
        "relevance": "students might scale a recipe",
        "provenance": Provenance(type="curriculum", source="MOE Secondary syllabus", page=19),
        "excerpt": "N2. Ratio and proportion; map scales; direct and inverse proportion",
    }])
    payload = json.loads(rendered)
    assert list(payload[0]) == ["evidence_id", "source", "page", "excerpt"]
    assert "resource_hint" not in payload[0]
    assert "taught_as_hint" not in payload[0]


def test_fair_division_curated_records_are_task_specific():
    records = _curated_evidence({
        "grade": "undergraduate",
        "jurisdiction": "USA",
        "exercise_ids": ["kerrigan2021_invention_1"],
        "topic": "fair division",
        "target_concept": "multi-player fair division",
    })
    names = [record["resource"] for record in records]
    assert "Divider-Chooser method (two-player fair division)" in names
    assert "Lone Divider method" not in names


def test_possible_matches_consider_the_taught_as_description():
    matches = _possible_matches(
        ["Range (max - min)"],
        [{
            "resource": "Range (Spannweite)",
            "taught_as": "subtract the minimum from the maximum",
        }],
    )
    assert matches["Range (max - min)"] == ["Range (Spannweite)"]


def test_page_corpus_has_stable_page_provenance():
    chunks = json.loads(Path("data/curriculum_grounding/corpus_chunks.json").read_text())
    assert chunks
    assert all(
        isinstance(chunk["page"], (int, str)) and str(chunk["page"]).strip()
        for chunk in chunks
    )
    assert len({chunk["chunk_id"] for chunk in chunks}) == len(chunks)


def _candidate(resource: str, provenance_type: str, confidence: str) -> ResourceCandidate:
    return ResourceCandidate(
        resource=resource,
        taught_as=f"{resource} taught as",
        relevance="relevant",
        provenance=Provenance(type=provenance_type, source="test"),
        confidence=confidence,
    )


def test_cap_candidates_truncates_and_prioritizes_strong_evidence():
    candidates = [
        _candidate("model-guess-1", "model", "high"),
        _candidate("model-guess-2", "model", "medium"),
        _candidate("curriculum-page", "curriculum", "medium"),
        _candidate("paper-verified", "paper", "high"),
        _candidate("model-guess-3", "model", "low"),
        _candidate("model-guess-4", "model", "low"),
    ]
    capped = _cap_candidates(candidates, max_resources=3)
    assert len(capped) == 3
    names = [c.resource for c in capped]
    # Strongest provenance/confidence kept first: paper, then curriculum,
    # then the highest-confidence model guess.
    assert names == ["paper-verified", "curriculum-page", "model-guess-1"]


def test_cap_candidates_rejects_nonpositive_limit():
    with pytest.raises(ValueError, match="positive"):
        _cap_candidates([_candidate("x", "model", "high")], max_resources=0)


def _reference_context(tmp_path):
    client = Mock()
    client.search_standards.return_value = [
        {
            "caseIdentifierUUID": f"reference-{rank}",
            "statementCode": f"CODE-{rank}",
            "description": f"Reference description {rank}",
            "author": "Test author",
            "provider": "Learning Commons",
            "jurisdiction": "Multi-State",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "attributionStatement": "Test attribution",
        }
        for rank in range(1, 11)
    ]
    return retrieve_context(
        {"topic": "variation", "subject": "mathematics"}, client=client, cache_dir=tmp_path
    )


@pytest.mark.parametrize("condition", ["grounded", "ungrounded"])
def test_context_selection_uses_existing_call_and_keeps_outputs_separate(
    tmp_path, monkeypatch, condition
):
    context = _reference_context(tmp_path)
    monkeypatch.setattr(runner, "_curated_evidence", lambda _: [])
    monkeypatch.setattr(
        runner, "_curriculum_evidence",
        lambda *_: [{
            "evidence_id": "curriculum:c1",
            "provenance": Provenance(type="curriculum", source="test syllabus"),
            "excerpt": "Summarize a set of values using its mean.",
        }],
    )
    calls = []

    def fake_chat(_client, _model, system, user, **kwargs):
        calls.append((system, user))
        if len(calls) == 1:
            return {
                "selected_sources": ["S8", "S2"],
                "resources": [{
                    "resource": "Mean",
                    "taught_as": "Sum values and divide by their count.",
                    "relevance": "Summarizes the data.",
                    "confidence": "medium",
                    "evidence_ids": ["curriculum:c1"],
                }],
            }, "inventory and selection"
        return {
            "kind": "builds_on",
            "student_move": "Given numerical values, calculate their mean.",
            "falls_short_because": "Their center alone does not describe their variation.",
        }, "expansion"

    monkeypatch.setattr(runner, "chat_json", fake_chat)
    result = runner._run_condition(
        None, "model", runner._prompts(),
        {"target_concept": "standard deviation", "topic": "variation", "grade": 10},
        condition, 6, 1, learning_commons=context,
    )
    assert len(calls) == 2
    assert "Reference description 10" in calls[0][1]
    assert "knowledge graph" in calls[0][0]
    assert "NOT to \"selected_sources\"" in calls[0][0]
    assert "caseIdentifierUUID" not in calls[0][1]
    assert "Reference description" not in calls[1][1]
    assert result["schema_version"] == "prior-method-recommendations/v2"
    assert [r["resource"] for r in result["recommendations"]] == ["Mean"]
    assert result["learning_commons"]["selected_sources"] == ["S8", "S2"]
    assert result["learning_commons"]["selected_references"][0]["description"] == (
        "Reference description 8"
    )
    assert result["learning_commons"]["response"] == context["response"]
    assert "selected_sources" not in context
    assert result["recommendations"][0]["provenance"]["type"] == (
        "curriculum" if condition == "grounded" else "model"
    )


def test_reference_selection_does_not_require_prior_curriculum(tmp_path, monkeypatch):
    context = _reference_context(tmp_path)
    monkeypatch.setattr(runner, "_curriculum_evidence", lambda *_: [])
    monkeypatch.setattr(runner, "_curated_evidence", lambda _: [])
    chat = Mock(return_value=({"resources": [], "selected_sources": ["S1"]}, "selection"))
    monkeypatch.setattr(runner, "chat_json", chat)
    result = runner._run_condition(
        None, "model", runner._prompts(),
        {"target_concept": "variation", "topic": "data"}, "grounded", 6, 1,
        learning_commons=context,
    )
    chat.assert_called_once()
    assert result["recommendations"] == []
    assert result["learning_commons"]["selected_sources"] == ["S1"]


def test_baseline_without_curriculum_still_makes_no_mapping_call(monkeypatch):
    monkeypatch.setattr(runner, "_curriculum_evidence", lambda *_: [])
    monkeypatch.setattr(runner, "_curated_evidence", lambda _: [])
    chat = Mock()
    monkeypatch.setattr(runner, "chat_json", chat)
    result = runner._run_condition(
        None, "model", runner._prompts(),
        {"target_concept": "variation", "topic": "data"}, "grounded", 6, 1,
    )
    chat.assert_not_called()
    assert result["schema_version"] == "prior-method-recommendations/v1"
    assert "learning_commons" not in result
    assert result["retrieval"]["status"] == "no_evidence"


def test_empty_curriculum_and_reference_search_do_not_add_a_model_call(tmp_path, monkeypatch):
    client = Mock()
    client.search_standards.return_value = []
    context = retrieve_context(
        {"topic": "variation", "subject": "mathematics"}, client=client, cache_dir=tmp_path
    )
    monkeypatch.setattr(runner, "_curriculum_evidence", lambda *_: [])
    monkeypatch.setattr(runner, "_curated_evidence", lambda _: [])
    chat = Mock()
    monkeypatch.setattr(runner, "chat_json", chat)
    result = runner._run_condition(
        None, "model", runner._prompts(),
        {"target_concept": "variation", "topic": "data"}, "grounded", 6, 1,
        learning_commons=context,
    )
    chat.assert_not_called()
    assert result["learning_commons"]["selected_sources"] == []
    assert result["learning_commons"]["selected_references"] == []
    assert result["retrieval"]["status"] == "no_evidence"


def test_graph_reference_cannot_be_cited_as_curriculum_evidence(tmp_path, monkeypatch):
    context = _reference_context(tmp_path)
    monkeypatch.setattr(runner, "_curriculum_evidence", lambda *_: [])
    monkeypatch.setattr(runner, "_curated_evidence", lambda _: [])
    monkeypatch.setattr(
        runner, "chat_json",
        Mock(return_value=({
            "selected_sources": ["S1"],
            "resources": [{
                "resource": "Variation",
                "taught_as": "Measure spread.",
                "relevance": "Relevant.",
                "evidence_ids": ["S1"],
            }],
        }, "wrong evidence")),
    )
    with pytest.raises(ValueError, match="unknown evidence IDs"):
        runner._run_condition(
            None, "model", runner._prompts(),
            {"target_concept": "variation", "topic": "data"}, "grounded", 6, 1,
            learning_commons=context,
        )


def test_opt_in_run_refuses_output_overwrite_before_any_model_call(tmp_path, monkeypatch):
    output = tmp_path / "existing.json"
    output.write_text("historical run")
    monkeypatch.setattr(
        "sys.argv",
        ["run_prior_recommendations", "--learning-commons", "--case",
         "kapur_average_speed_g7_singapore", "--output", str(output)],
    )
    monkeypatch.setattr(
        runner, "load_client", lambda *_: pytest.fail("must reject overwrite before client setup")
    )
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        runner.main()
    assert output.read_text() == "historical run"


def test_render_preserves_placeholder_text_inside_retrieved_data():
    rendered = runner._render(
        "{curriculum_evidence}\n{target_concept}",
        {"curriculum_evidence": "Source literally says {target_concept}", "target_concept": "Rate"},
    )
    assert rendered == "Source literally says {target_concept}\nRate"


def test_standalone_cli_persists_selection_and_raw_sources(tmp_path, monkeypatch):
    context = _reference_context(tmp_path / "cache")
    output = tmp_path / "d1.json"
    retrieve = Mock(return_value=context)
    monkeypatch.setattr(runner, "retrieve_context", retrieve)
    monkeypatch.setattr(runner, "load_client", lambda *_: (None, "fake-model"))
    chat = Mock(return_value=({"resources": [], "selected_sources": ["S8"]}, "selection"))
    monkeypatch.setattr(runner, "chat_json", chat)
    monkeypatch.setattr(
        "sys.argv",
        ["run_prior_recommendations", "--case", "kapur_average_speed_g7_singapore",
         "--condition", "ungrounded", "--learning-commons", "--output", str(output)],
    )
    runner.main()
    saved = json.loads(output.read_text())
    assert saved["schema_version"] == "prior-method-recommendations/v2"
    result = saved["records"][0]["result"]
    assert result["learning_commons"]["selected_sources"] == ["S8"]
    assert len(result["learning_commons"]["response"]) == 10
    retrieve.assert_called_once()
    chat.assert_called_once()
