import json
import ssl
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

import scripts.learning_commons_api as learning_commons_api
from scripts.learning_commons_api import LearningCommonsAPIError, LearningCommonsClient


def _mock_response(payload):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


def test_search_standards_encodes_exact_code_filters_and_repeated_grades(monkeypatch):
    response = _mock_response([{"statementCode": "6.RP.A.2"}])
    request_call = Mock(return_value=response)
    monkeypatch.setattr(learning_commons_api, "urlopen", request_call)
    client = LearningCommonsClient("example-key")

    result = client.search_standards(
        statement_code="6.RP.A.2",
        grade_levels=["6", "7"],
        academic_subject="Mathematics",
        jurisdiction="Multi-State",
        limit=10,
    )

    request = request_call.call_args.args[0]
    query = parse_qs(urlparse(request.full_url).query)
    assert result == [{"statementCode": "6.RP.A.2"}]
    assert urlparse(request.full_url).path.endswith("/academic-standards/search")
    assert query["statementCode"] == ["6.RP.A.2"]
    assert query["gradeLevel"] == ["6", "7"]
    assert request.get_header("X-api-key") == "example-key"
    call_kwargs = request_call.call_args.kwargs
    assert call_kwargs["timeout"] == 30.0
    assert isinstance(call_kwargs["context"], ssl.SSLContext)
    assert call_kwargs["context"].verify_mode == ssl.CERT_REQUIRED
    assert call_kwargs["context"].check_hostname


def test_search_standards_requires_exactly_one_mode():
    client = LearningCommonsClient("example-key")

    with pytest.raises(ValueError, match="exactly one"):
        client.search_standards()
    with pytest.raises(ValueError, match="exactly one"):
        client.search_standards(query="speed", statement_code="6.RP.A.2")


def test_learning_component_search_uses_semantic_query_endpoint(monkeypatch):
    response = _mock_response([{"description": "Use mean absolute deviation", "score": 0.8}])
    request_call = Mock(return_value=response)
    monkeypatch.setattr(learning_commons_api, "urlopen", request_call)
    client = LearningCommonsClient("example-key")

    result = client.search_learning_components(
        "measure spread around the mean", academic_subject="Mathematics", limit=3
    )

    request = request_call.call_args.args[0]
    query = parse_qs(urlparse(request.full_url).query)
    assert result[0]["score"] == 0.8
    assert urlparse(request.full_url).path.endswith("/learning-components/search")
    assert query == {
        "query": ["measure spread around the mean"],
        "academicSubject": ["Mathematics"],
        "limit": ["3"],
    }


def test_framework_and_relationship_routes_preserve_pagination(monkeypatch):
    response = _mock_response({"data": [], "pagination": {"nextCursor": "next"}})
    request_call = Mock(return_value=response)
    monkeypatch.setattr(learning_commons_api, "urlopen", request_call)
    client = LearningCommonsClient("example-key")

    client.list_frameworks(
        jurisdiction="Multi-State",
        academic_subject="Mathematics",
        include_non_current=True,
        cursor="page-2",
    )
    framework_request = request_call.call_args.args[0]
    framework_query = parse_qs(urlparse(framework_request.full_url).query)
    assert urlparse(framework_request.full_url).path.endswith("/standards-frameworks")
    assert framework_query["includeNonCurrent"] == ["true"]
    assert framework_query["cursor"] == ["page-2"]

    client.get_standard("standard-id")
    standard_request = request_call.call_args.args[0]
    assert urlparse(standard_request.full_url).path.endswith("/academic-standards/standard-id")

    client.list_standards_in_framework(
        "framework-id", grade_levels=["6"], normalized_statement_type="Standard"
    )
    standards_request = request_call.call_args.args[0]
    standards_query = parse_qs(urlparse(standards_request.full_url).query)
    assert urlparse(standards_request.full_url).path.endswith("/academic-standards")
    assert standards_query["standardsFrameworkCaseIdentifierUUID"] == ["framework-id"]
    assert standards_query["gradeLevel"] == ["6"]

    client.learning_components_for_standard("standard-id", cursor="component-page")
    components_request = request_call.call_args.args[0]
    components_query = parse_qs(urlparse(components_request.full_url).query)
    assert urlparse(components_request.full_url).path.endswith(
        "/academic-standards/standard-id/learning-components"
    )
    assert components_query["cursor"] == ["component-page"]

    client.prerequisites_for_standard("standard-id", limit=25, cursor="prereq-page")
    prereq_request = request_call.call_args.args[0]
    prereq_query = parse_qs(urlparse(prereq_request.full_url).query)
    assert urlparse(prereq_request.full_url).path.endswith(
        "/academic-standards/standard-id/prerequisites"
    )
    assert prereq_query == {"limit": ["25"], "cursor": ["prereq-page"]}

    client.standards_built_towards("standard-id")
    builds_request = request_call.call_args.args[0]
    assert urlparse(builds_request.full_url).path.endswith(
        "/academic-standards/standard-id/builds-towards"
    )

    client.related_standards_for_standard("standard-id")
    related_request = request_call.call_args.args[0]
    assert urlparse(related_request.full_url).path.endswith(
        "/academic-standards/standard-id/related-standards"
    )


def test_api_http_errors_are_reported_not_returned_as_empty_results(monkeypatch):
    error = HTTPError(
        "https://api.learningcommons.org/knowledge-graph/v0/academic-standards/search",
        401,
        "Unauthorized",
        {},
        None,
    )
    error.read = Mock(return_value=b'{"error":"Unauthorized","message":"Invalid API key"}')
    monkeypatch.setattr(learning_commons_api, "urlopen", Mock(side_effect=error))
    client = LearningCommonsClient("example-key")

    with pytest.raises(LearningCommonsAPIError, match="HTTP 401.*Invalid API key"):
        client.search_standards(query="average speed")


def test_search_limits_are_checked_before_request(monkeypatch):
    request_call = Mock()
    monkeypatch.setattr(learning_commons_api, "urlopen", request_call)
    client = LearningCommonsClient("example-key")

    with pytest.raises(ValueError, match="between 1 and 50"):
        client.search_learning_components("average speed", limit=51)
    request_call.assert_not_called()
