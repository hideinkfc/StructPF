import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.learning_commons_context import (
    format_selected_references,
    prompt_candidates,
    record_selection,
    retrieve_context,
    selected_references,
)


def _record(identifier="source-one", description="Calculate a rate", code="7.RP.A.1"):
    return {
        "caseIdentifierUUID": identifier,
        "statementCode": code,
        "description": description,
        "author": "Test author",
        "provider": "Learning Commons",
        "jurisdiction": "Multi-State",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "attributionStatement": "Test attribution",
        "score": 0.7,
    }


def _context(tmp_path, response=None, subject="mathematics"):
    client = Mock()
    client.search_standards.return_value = [_record()] if response is None else response
    context = retrieve_context(
        {"topic": "average speed", "subject": subject, "grade": 7, "jurisdiction": "Singapore"},
        client=client,
        cache_dir=tmp_path,
    )
    return context, client


def test_one_grade_unfiltered_search_saves_complete_response(tmp_path):
    context, client = _context(tmp_path)
    client.search_standards.assert_called_once_with(
        query="average speed",
        academic_subject="Mathematics",
        grade_levels=[],
        jurisdiction=None,
        limit=10,
    )
    saved = json.loads(Path(context["evidence_file"]).read_text())
    assert saved["response"] == [_record()]
    assert "Test attribution" in json.dumps(saved)
    assert "api_key" not in saved
    assert context["cache_hit"] is False


def test_cache_reuse_needs_no_key_or_api_call(tmp_path, monkeypatch):
    original, client = _context(tmp_path)
    monkeypatch.delenv("LEARNING_COMMONS_API_KEY", raising=False)
    cached = retrieve_context(
        {"topic": "average speed", "subject": "mathematics", "grade": 10},
        cache_dir=tmp_path,
    )
    assert cached["cache_hit"] is True
    assert cached["evidence_file"] == original["evidence_file"]
    assert cached["retrieved_at_utc"] == original["retrieved_at_utc"]
    client.search_standards.assert_called_once()


def test_refresh_preserves_earlier_snapshot(tmp_path):
    original, client = _context(tmp_path)
    refreshed = retrieve_context(
        {"topic": "average speed", "subject": "mathematics"},
        client=client,
        cache_dir=tmp_path,
        refresh=True,
    )
    assert client.search_standards.call_count == 2
    assert refreshed["cache_hit"] is False
    assert refreshed["evidence_file"] != original["evidence_file"]
    assert len(list(tmp_path.glob("*/response_*.json"))) == 2


def test_physics_uses_science_filter(tmp_path):
    _, client = _context(tmp_path, subject="physics")
    assert client.search_standards.call_args.kwargs["academic_subject"] == "Science"


def test_prompt_uses_short_labels_and_unchanged_descriptions_not_metadata(tmp_path):
    context, _ = _context(tmp_path, [_record(), _record("source-two", code=None)])
    records = json.loads(prompt_candidates(context))
    assert [record["source_label"] for record in records] == ["S1", "S2"]
    assert records[0]["description"] == "Calculate a rate"
    assert records[1]["statement_code"] is None
    assert "caseIdentifierUUID" not in prompt_candidates(context)
    assert "license" not in prompt_candidates(context)
    assert "score" not in prompt_candidates(context)


def test_selection_resolves_verbatim_text_and_keeps_source_mapping(tmp_path):
    context, _ = _context(tmp_path, [_record(), _record("source-two", "Compare ratios")])
    record_selection(context, {"selected_sources": ["S2"]})
    assert selected_references(context)[0]["description"] == "Compare ratios"
    assert context["source_label_to_id"] == {"S1": "source-one", "S2": "source-two"}
    assert "not assumed prior knowledge" in format_selected_references(context)


@pytest.mark.parametrize("selection", [None, "S1", [1], ["S9"], ["S1", "S1"], ["S1"] * 4])
def test_invalid_selection_is_rejected(tmp_path, selection):
    context, _ = _context(tmp_path)
    with pytest.raises(ValueError, match="Learning Commons"):
        record_selection(context, {"selected_sources": selection})


def test_empty_response_and_selection_are_valid_but_not_a_failure_fallback(tmp_path):
    context, _ = _context(tmp_path, [])
    assert json.loads(prompt_candidates(context)) == []
    record_selection(context, {"selected_sources": []})
    assert selected_references(context) == []
    assert format_selected_references(context) == ""


def test_api_failure_is_propagated_and_not_cached(tmp_path):
    client = Mock()
    client.search_standards.side_effect = RuntimeError("HTTP 451")
    with pytest.raises(RuntimeError, match="HTTP 451"):
        retrieve_context(
            {"topic": "rates", "subject": "mathematics"}, client=client, cache_dir=tmp_path
        )
    assert not list(tmp_path.glob("*/response_*.json"))


def test_corrupt_cache_is_not_silently_refetched(tmp_path):
    context, client = _context(tmp_path)
    Path(context["evidence_file"]).write_text("invalid JSON")
    with pytest.raises(json.JSONDecodeError):
        retrieve_context(
            {"topic": "average speed", "subject": "mathematics"},
            client=client,
            cache_dir=tmp_path,
        )
    client.search_standards.assert_called_once()


def test_modified_selected_text_is_rejected(tmp_path):
    context, _ = _context(tmp_path)
    record_selection(context, {"selected_sources": ["S1"]})
    context["selected_references"][0] = {
        **context["selected_references"][0],
        "description": "Invented",
    }
    with pytest.raises(ValueError, match="selected_references"):
        selected_references(context)


def test_duplicate_records_do_not_produce_duplicate_candidates(tmp_path):
    context, _ = _context(tmp_path, [_record(), _record(), _record("source-two")])
    assert [r["source_label"] for r in json.loads(prompt_candidates(context))] == ["S1", "S3"]
    record_selection(context, {"selected_sources": ["S3"]})
    assert context["source_label_to_id"] == {"S1": "source-one", "S3": "source-two"}


@pytest.mark.parametrize(
    "response",
    [{"data": []}, [{}], [_record()] * 11, [{**_record(), "license": None}]],
)
def test_invalid_response_is_rejected_before_caching(tmp_path, response):
    with pytest.raises(ValueError, match="Learning Commons"):
        _context(tmp_path, response)
    assert not list(tmp_path.glob("*/response_*.json"))


def test_conflicting_duplicate_source_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Conflicting"):
        _context(tmp_path, [_record(), _record(description="Conflicting source text")])


def test_cached_request_must_match_requested_search(tmp_path):
    context, client = _context(tmp_path)
    path = Path(context["evidence_file"])
    saved = json.loads(path.read_text())
    saved["request"]["query"] = "a different request"
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="cached request does not match"):
        retrieve_context(
            {"topic": "average speed", "subject": "mathematics"},
            client=client,
            cache_dir=tmp_path,
        )
    client.search_standards.assert_called_once()


def test_unknown_subject_is_not_silently_changed_to_other(tmp_path):
    with pytest.raises(ValueError, match="Unsupported Learning Commons subject"):
        _context(tmp_path, subject="unknown subject")


def test_query_override_and_subject_are_part_of_cache_identity(tmp_path):
    _, client = _context(tmp_path)
    custom = retrieve_context(
        {"topic": "average speed", "subject": "physics"},
        query="stopping distance",
        client=client,
        cache_dir=tmp_path,
    )
    assert client.search_standards.call_count == 2
    assert custom["request"]["query"] == "stopping distance"
    assert custom["request"]["academic_subject"] == "Science"
    assert len(list(tmp_path.glob("*/response_*.json"))) == 2
