"""Search and retrieve records from the Learning Commons Knowledge Graph API.

Set LEARNING_COMMONS_API_KEY before running this read-only client. Search scores
are discovery signals, not evidence that a record is equivalent to a target.

Examples:
    python scripts/learning_commons_api.py standards --query "average speed" --subject Mathematics
    python scripts/learning_commons_api.py standards --code "HSS-ID.A.2"
    python scripts/learning_commons_api.py search-components --query "mean absolute deviation"
    python scripts/learning_commons_api.py get-standard 6b9ee241-d7cc-11e8-824f-0242ac160002
    python scripts/learning_commons_api.py components-for-standard \
        6b9ee241-d7cc-11e8-824f-0242ac160002
    python scripts/learning_commons_api.py frameworks \
        --jurisdiction "Multi-State" --subject Mathematics
    python scripts/learning_commons_api.py standards-in-framework \
        FRAMEWORK_UUID --grade-level 6
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import certifi

BASE_URL = "https://api.learningcommons.org/knowledge-graph/v0"
SEARCH_LIMIT_MAX = 50
PAGINATED_LIMIT_MAX = 1000


class LearningCommonsAPIError(RuntimeError):
    """Raised when an API request fails or returns invalid JSON."""


class LearningCommonsClient:
    """Small read-only client for documented standards and learning-component routes."""

    def __init__(self, api_key: str, *, timeout: float = 30.0) -> None:
        if not api_key.strip():
            raise ValueError("LEARNING_COMMONS_API_KEY is empty")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._api_key = api_key.strip()
        self._timeout = timeout

    def search_standards(
        self,
        *,
        query: str | None = None,
        statement_code: str | None = None,
        grade_levels: Sequence[str] | None = None,
        academic_subject: str | None = None,
        normalized_statement_type: str | None = None,
        jurisdiction: str | None = None,
        limit: int = 5,
    ) -> Any:
        if bool(query) == bool(statement_code):
            raise ValueError("provide exactly one of query or statement_code")
        self._validate_limit(limit, SEARCH_LIMIT_MAX)
        return self._get(
            "/academic-standards/search",
            {
                "query": query,
                "statementCode": statement_code,
                "gradeLevel": grade_levels,
                "academicSubject": academic_subject,
                "normalizedStatementType": normalized_statement_type,
                "jurisdiction": jurisdiction,
                "limit": limit,
            },
        )

    def search_learning_components(
        self,
        query: str,
        *,
        academic_subject: str | None = None,
        limit: int = 5,
    ) -> Any:
        if not query.strip():
            raise ValueError("query must not be empty")
        self._validate_limit(limit, SEARCH_LIMIT_MAX)
        return self._get(
            "/learning-components/search",
            {"query": query, "academicSubject": academic_subject, "limit": limit},
        )

    def get_standard(self, case_identifier_uuid: str) -> Any:
        return self._get(f"/academic-standards/{quote(case_identifier_uuid, safe='')}")

    def learning_components_for_standard(
        self,
        case_identifier_uuid: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        identifier = quote(case_identifier_uuid, safe="")
        return self._get(
            f"/academic-standards/{identifier}/learning-components",
            {"limit": limit, "cursor": cursor},
        )

    def prerequisites_for_standard(
        self,
        case_identifier_uuid: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        identifier = quote(case_identifier_uuid, safe="")
        return self._get(
            f"/academic-standards/{identifier}/prerequisites",
            {"limit": limit, "cursor": cursor},
        )

    def standards_built_towards(
        self,
        case_identifier_uuid: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        identifier = quote(case_identifier_uuid, safe="")
        return self._get(
            f"/academic-standards/{identifier}/builds-towards",
            {"limit": limit, "cursor": cursor},
        )

    def related_standards_for_standard(
        self,
        case_identifier_uuid: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        identifier = quote(case_identifier_uuid, safe="")
        return self._get(
            f"/academic-standards/{identifier}/related-standards",
            {"limit": limit, "cursor": cursor},
        )

    def list_frameworks(
        self,
        *,
        jurisdiction: str | None = None,
        academic_subject: str | None = None,
        adoption_status: str | None = None,
        include_non_current: bool = False,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        return self._get(
            "/standards-frameworks",
            {
                "jurisdiction": jurisdiction,
                "academicSubject": academic_subject,
                "adoptionStatus": adoption_status,
                "includeNonCurrent": include_non_current,
                "limit": limit,
                "cursor": cursor,
            },
        )

    def list_standards_in_framework(
        self,
        framework_case_identifier_uuid: str,
        *,
        grade_levels: Sequence[str] | None = None,
        academic_subject: str | None = None,
        normalized_statement_type: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Any:
        self._validate_limit(limit, PAGINATED_LIMIT_MAX)
        return self._get(
            "/academic-standards",
            {
                "standardsFrameworkCaseIdentifierUUID": framework_case_identifier_uuid,
                "gradeLevel": grade_levels,
                "academicSubject": academic_subject,
                "normalizedStatementType": normalized_statement_type,
                "limit": limit,
                "cursor": cursor,
            },
        )

    @staticmethod
    def _validate_limit(limit: int, maximum: int) -> None:
        if not 1 <= limit <= maximum:
            raise ValueError(f"limit must be between 1 and {maximum}")

    def _get(self, path: str, params: Mapping[str, object] | None = None) -> Any:
        query: list[tuple[str, str]] = []
        for key, value in (params or {}).items():
            if value is None:
                continue
            values = value if isinstance(value, (list, tuple)) else [value]
            for item in values:
                if isinstance(item, bool):
                    rendered = "true" if item else "false"
                else:
                    rendered = str(item)
                query.append((key, rendered))
        suffix = f"?{urlencode(query)}" if query else ""
        url = f"{BASE_URL}{path}{suffix}"
        request = Request(url, headers={"Accept": "application/json", "x-api-key": self._api_key})
        ca_bundle = os.environ.get("SSL_CERT_FILE") or certifi.where()
        context = ssl.create_default_context(cafile=ca_bundle)

        try:
            with urlopen(request, timeout=self._timeout, context=context) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()[:1000]
            message = f"GET {path} failed with HTTP {exc.code}"
            if detail:
                message = f"{message}: {detail}"
            raise LearningCommonsAPIError(message) from exc
        except URLError as exc:
            raise LearningCommonsAPIError(f"GET {path} failed: {exc.reason}") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise LearningCommonsAPIError(f"GET {path} returned invalid JSON") from exc


def _add_subject_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--subject", dest="academic_subject")


def _add_pagination_arguments(parser: argparse.ArgumentParser, *, default_limit: int = 100) -> None:
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--cursor", help="Pagination cursor returned by the previous page")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    standards = subparsers.add_parser("standards", help="Search standards by text or exact code")
    selector = standards.add_mutually_exclusive_group(required=True)
    selector.add_argument("--query", help="Semantic search text")
    selector.add_argument(
        "--code", dest="statement_code", help="Exact, case-insensitive standard code"
    )
    standards.add_argument("--grade-level", dest="grade_levels", action="append")
    _add_subject_argument(standards)
    standards.add_argument("--statement-type", dest="normalized_statement_type")
    standards.add_argument("--jurisdiction")
    standards.add_argument("--limit", type=int, default=5)

    component_search = subparsers.add_parser(
        "search-components", help="Semantically search learning-component descriptions"
    )
    component_search.add_argument("--query", required=True)
    _add_subject_argument(component_search)
    component_search.add_argument("--limit", type=int, default=5)

    get_standard = subparsers.add_parser("get-standard", help="Retrieve a standard by CASE UUID")
    get_standard.add_argument("case_identifier_uuid")

    components = subparsers.add_parser(
        "components-for-standard", help="List learning components linked to a standard"
    )
    components.add_argument("case_identifier_uuid")
    _add_pagination_arguments(components)

    prerequisites = subparsers.add_parser(
        "prerequisites-for-standard", help="List Coherence Map prerequisites for a standard"
    )
    prerequisites.add_argument("case_identifier_uuid")
    _add_pagination_arguments(prerequisites)

    builds_towards = subparsers.add_parser(
        "builds-towards", help="List standards that a standard builds towards"
    )
    builds_towards.add_argument("case_identifier_uuid")
    _add_pagination_arguments(builds_towards)

    related = subparsers.add_parser(
        "related-standards", help="List related standards for a standard"
    )
    related.add_argument("case_identifier_uuid")
    _add_pagination_arguments(related)

    frameworks = subparsers.add_parser("frameworks", help="Browse standards frameworks")
    frameworks.add_argument("--jurisdiction")
    _add_subject_argument(frameworks)
    frameworks.add_argument("--adoption-status")
    frameworks.add_argument("--include-non-current", action="store_true")
    _add_pagination_arguments(frameworks)

    framework_standards = subparsers.add_parser(
        "standards-in-framework", help="List standards in a framework"
    )
    framework_standards.add_argument("framework_case_identifier_uuid")
    framework_standards.add_argument("--grade-level", dest="grade_levels", action="append")
    _add_subject_argument(framework_standards)
    framework_standards.add_argument("--statement-type", dest="normalized_statement_type")
    _add_pagination_arguments(framework_standards)

    return parser


def _dispatch(client: LearningCommonsClient, args: argparse.Namespace) -> Any:
    if args.command == "standards":
        return client.search_standards(
            query=args.query,
            statement_code=args.statement_code,
            grade_levels=args.grade_levels,
            academic_subject=args.academic_subject,
            normalized_statement_type=args.normalized_statement_type,
            jurisdiction=args.jurisdiction,
            limit=args.limit,
        )
    if args.command == "search-components":
        return client.search_learning_components(
            args.query,
            academic_subject=args.academic_subject,
            limit=args.limit,
        )
    if args.command == "get-standard":
        return client.get_standard(args.case_identifier_uuid)
    if args.command == "components-for-standard":
        return client.learning_components_for_standard(
            args.case_identifier_uuid, limit=args.limit, cursor=args.cursor
        )
    if args.command == "prerequisites-for-standard":
        return client.prerequisites_for_standard(
            args.case_identifier_uuid, limit=args.limit, cursor=args.cursor
        )
    if args.command == "builds-towards":
        return client.standards_built_towards(
            args.case_identifier_uuid, limit=args.limit, cursor=args.cursor
        )
    if args.command == "related-standards":
        return client.related_standards_for_standard(
            args.case_identifier_uuid, limit=args.limit, cursor=args.cursor
        )
    if args.command == "frameworks":
        return client.list_frameworks(
            jurisdiction=args.jurisdiction,
            academic_subject=args.academic_subject,
            adoption_status=args.adoption_status,
            include_non_current=args.include_non_current,
            limit=args.limit,
            cursor=args.cursor,
        )
    if args.command == "standards-in-framework":
        return client.list_standards_in_framework(
            args.framework_case_identifier_uuid,
            grade_levels=args.grade_levels,
            academic_subject=args.academic_subject,
            normalized_statement_type=args.normalized_statement_type,
            limit=args.limit,
            cursor=args.cursor,
        )
    raise ValueError(f"unsupported command: {args.command}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    api_key = os.environ.get("LEARNING_COMMONS_API_KEY", "").strip()
    if not api_key:
        parser.error("set LEARNING_COMMONS_API_KEY in the environment")

    try:
        result = _dispatch(LearningCommonsClient(api_key), args)
    except (LearningCommonsAPIError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
