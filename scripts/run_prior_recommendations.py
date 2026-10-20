"""Generate grounded and ungrounded prior-knowledge recommendations.

The two conditions receive the same target input. The ungrounded condition
free-lists resources from the target, grade, and subject. The grounded
condition retrieves curriculum or textbook pages and maps those excerpts to
taught-skill labels. Curated expert-resource lists are held out of the prompt
and used only for later comparison. Each kept label is then expanded into a
short activation note, not a full student solution.

With --learning-commons, the same inventory/mapping call also selects cached
mathematical references. They are saved separately from prior resources and
carried into task design without an extra ranking call.

Usage:
    ./.venv/bin/python scripts/run_prior_recommendations.py --list-cases
    ./.venv/bin/python scripts/run_prior_recommendations.py \
        --case kapur_average_speed_g7_singapore --condition both
    ./.venv/bin/python scripts/run_prior_recommendations.py --compare-expert
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.learning_commons_context import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    prompt_candidates,
    record_selection,
    retrieve_context,
)
from scripts.learning_commons_guided_search import save_run  # noqa: E402
from scripts.prior_methods.common import chat_json, load_client  # noqa: E402
from scripts.retrieve_prior_knowledge import retrieve_chunks  # noqa: E402
from src.generation.prior_recommendations import (  # noqa: E402
    Condition,
    Confidence,
    PriorMethodRecommendation,
    Provenance,
    ResourceCandidate,
)

PROMPTS_PATH = ROOT / "src" / "generation" / "prompts" / "prior_recommendations.yaml"
CASES_PATH = ROOT / "experiments" / "configs" / "prior_recommendation_cases.json"
GROUNDING_DIR = ROOT / "data" / "curriculum_grounding"
RESULTS_DIR = ROOT / "experiments" / "results" / "prior_recommendations"

DEFAULT_MAX_RESOURCES = 5
PROVENANCE_RANK = {"paper": 0, "curriculum": 1, "model": 2}
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def _prompts() -> dict[str, str]:
    prompts = yaml.safe_load(PROMPTS_PATH.read_text())
    if not isinstance(prompts, dict):
        raise ValueError(f"Prompt file must contain an object: {PROMPTS_PATH}")
    required = {
        "UNGROUNDED_INVENTORY_SYSTEM",
        "UNGROUNDED_INVENTORY_USER",
        "GROUNDED_MAPPING_SYSTEM",
        "GROUNDED_MAPPING_USER",
        "EXPAND_RESOURCE_SYSTEM",
        "EXPAND_RESOURCE_USER",
        "LEARNING_COMMONS_SELECTION_SYSTEM",
        "LEARNING_COMMONS_SELECTION_USER",
    }
    missing = required - prompts.keys()
    if missing:
        raise ValueError(f"Missing prompts: {sorted(missing)}")
    return prompts


def _render(template: str, values: dict[str, str]) -> str:
    """Substitute once, without interpreting placeholders inside source text."""
    return re.sub(
        r"\{([A-Za-z_][A-Za-z_0-9]*)\}",
        lambda match: values.get(match[1], match[0]),
        template,
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Model payload is missing non-empty {key!r}")
    return value.strip()


def _confidence(payload: dict[str, Any]) -> Confidence:
    value = payload.get("confidence", "medium")
    if value == "high":
        return "high"
    if value == "medium":
        return "medium"
    if value == "low":
        return "low"
    else:
        raise ValueError(f"confidence must be high, medium, or low; got {value!r}")


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _comparison_tokens(value: str) -> set[str]:
    tokens = set(_normalise(value).split())
    aliases = {
        "maximum": "max",
        "minimum": "min",
        "average": "mean",
        "dividing": "division",
        "divide": "division",
    }
    return tokens | {aliases[token] for token in tokens if token in aliases}


def _page_number(value: object) -> int | str | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _numeric_grade(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _teacher_skills(case: dict[str, Any]) -> str:
    skills = case.get("teacher_skills", [])
    if isinstance(skills, str):
        return skills.strip() or "(none supplied)"
    if not isinstance(skills, list):
        raise ValueError("teacher_skills must be a list or string")
    values = [str(skill).strip() for skill in skills if str(skill).strip()]
    return "\n".join(f"- {skill}" for skill in values) or "(none supplied)"


def _excluded_resources(case: dict[str, Any]) -> list[str]:
    values = case.get("exclude_resource_terms", [])
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("exclude_resource_terms must be a list of strings")
    return [value.strip() for value in values if value.strip()]


def _excluded_resources_text(case: dict[str, Any]) -> str:
    values = _excluded_resources(case)
    return "\n".join(f"- {value}" for value in values) or "(none specified)"


def _input_values(case: dict[str, Any]) -> dict[str, str]:
    return {
        "target_concept": _required_string(case, "target_concept"),
        "topic": _required_string(case, "topic"),
        "grade": str(case.get("grade", "unspecified")),
        "jurisdiction": str(case.get("jurisdiction", "unspecified")),
        "subject": str(case.get("subject", "mathematics")),
        "excluded_resources": _excluded_resources_text(case),
        "teacher_skills": _teacher_skills(case),
    }


def _cell_matches(case: dict[str, Any], cell: dict[str, Any]) -> bool:
    grade = case.get("grade")
    cell_grade = str(cell.get("grade", ""))
    if grade is not None and str(grade).strip():
        grade_text = str(grade).lower()
        cell_grade_text = cell_grade.lower()
        if grade_text not in cell_grade_text and cell_grade_text not in grade_text:
            return False

    jurisdiction = str(case.get("jurisdiction", "")).strip().lower()
    cell_country = str(cell.get("country", "")).lower()
    if jurisdiction and jurisdiction not in cell_country and cell_country not in jurisdiction:
        return False

    query_terms = set(
        re.findall(
            r"[a-z0-9]+", _normalise(f"{case.get('topic', '')} {case.get('target_concept', '')}")
        )
    )
    cell_terms = set(
        re.findall(
            r"[a-z0-9]+", _normalise(f"{cell.get('id', '')} {cell.get('target_concept', '')}")
        )
    )
    useful_terms = {term for term in query_terms if len(term) > 2}
    return not useful_terms or bool(useful_terms & cell_terms)


def _cell_is_usable(cell: dict[str, Any]) -> bool:
    caveats = " ".join(str(item) for item in cell.get("caveats", []))
    return "placeholder" not in caveats.lower() and "do not cite" not in caveats.lower()


def _source_for_resource(cell: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    sources = cell.get("sources", [])
    if not isinstance(sources, list):
        sources = []
    resource_source = str(resource.get("source", "")).lower()
    for source in sources:
        if isinstance(source, dict):
            name = str(source.get("name", "")).lower()
            if resource_source and (resource_source in name or name in resource_source):
                return source
    return next((source for source in sources if isinstance(source, dict)), {})


def _curated_evidence(case: dict[str, Any]) -> list[dict[str, Any]]:
    exercise_ids = set(case.get("exercise_ids", []))
    records: list[dict[str, Any]] = []
    for path in sorted(GROUNDING_DIR.glob("*.yaml")):
        cell = yaml.safe_load(path.read_text())
        if not isinstance(cell, dict) or not _cell_is_usable(cell):
            continue
        if exercise_ids:
            if not exercise_ids.intersection(cell.get("expert_tasks_grounded", [])):
                continue
        elif not _cell_matches(case, cell):
            continue

        resources = cell.get("prior_resources_taught_before_target", [])
        if not isinstance(resources, list):
            raise ValueError(f"prior_resources must be a list in {path}")
        for index, resource in enumerate(resources):
            if not isinstance(resource, dict):
                raise ValueError(f"Invalid prior resource at {path}:{index}")
            applies_to = resource.get("applies_to")
            if applies_to is not None:
                if not isinstance(applies_to, list) or not all(
                    isinstance(value, str) for value in applies_to
                ):
                    raise ValueError(f"applies_to must be a list of strings at {path}:{index}")
                if exercise_ids and not exercise_ids.intersection(applies_to):
                    continue
            name = _required_string(resource, "resource")
            source = _source_for_resource(cell, resource)
            source_name = str(resource.get("source") or source.get("name") or path.name)
            source_type = (
                "curriculum"
                if re.search(
                    r"moe|curriculum|syllabus|kernlehrplan|cbse|nrw|"
                    r"textbook|open textbook|oer|common core|standards",
                    source_name,
                    re.I,
                )
                else "paper"
            )
            paper_crosscheck = resource.get("paper_crosscheck")
            evidence = f"Curated grounding cell: {cell['id']}"
            if paper_crosscheck:
                evidence += f"; {paper_crosscheck}"
            source_url = source.get("url")
            if isinstance(source_url, list):
                source_url = source_url[0] if source_url else None
            if not isinstance(source_url, str):
                source_url = None
            pages = resource.get("pages")
            if not isinstance(pages, (str, int)):
                pages = None
            provenance = Provenance(
                type=source_type,
                source=source_name,
                page=pages,
                document=path.name,
                source_url=source_url,
                evidence=evidence,
            )
            evidence_id = f"curated:{cell['id']}:{index}"
            records.append(
                {
                    "evidence_id": evidence_id,
                    "resource": name,
                    "taught_as": str(resource.get("taught_as") or name),
                    "relevance": str(resource.get("relevance") or ""),
                    "provenance": provenance,
                    "excerpt": str(
                        resource.get("section_text") or resource.get("paper_crosscheck") or ""
                    ),
                }
            )
    return records


def _curriculum_evidence(case: dict[str, Any], k: int) -> list[dict[str, Any]]:
    target = _input_values(case)
    query = (
        f"{target['jurisdiction']} grade {target['grade']} {target['subject']} "
        f"skills taught before {target['topic']}"
    )
    chunks = retrieve_chunks(
        query,
        k=max(k * 3, 12),
        grade=_numeric_grade(case.get("grade")),
        jurisdiction=str(case.get("jurisdiction", "")).strip() or None,
        subject=str(case.get("subject", "")).strip() or None,
    )
    # Keep one page per document and prefer the English translation when both
    # language variants were retrieved.
    by_page: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks:
        key = (str(chunk["doc"]), str(chunk["page"]))
        current = by_page.get(key)
        if current is None or (chunk.get("language") == "en" and current.get("language") != "en"):
            by_page[key] = chunk

    records = []
    for chunk in by_page.values():
        evidence_id = f"curriculum:{chunk['chunk_id']}"
        page = chunk["page"]
        records.append(
            {
                "evidence_id": evidence_id,
                "resource": "",
                "taught_as": "",
                "relevance": "",
                "provenance": Provenance(
                    type="curriculum",
                    source=str(chunk["doc_title"]),
                    page=page,
                    document=str(chunk["doc"]),
                    source_url=chunk.get("source_url"),
                    evidence=f"{chunk['jurisdiction']} {chunk.get('language', 'unknown')} page chunk",
                ),
                "excerpt": str(chunk["text"])[:1800],
            }
        )
    return records[:k]


def _prompt_evidence(records: list[dict[str, Any]]) -> str:
    if not records:
        return "(none)"
    rendered = []
    for record in records:
        provenance = record["provenance"]
        rendered.append(
            {
                "evidence_id": record["evidence_id"],
                "source": provenance.source,
                "page": provenance.page,
                "excerpt": record["excerpt"],
            }
        )
    return json.dumps(rendered, indent=2, ensure_ascii=False)


def _deduplicate_candidates(candidates: list[ResourceCandidate]) -> list[ResourceCandidate]:
    unique: dict[str, ResourceCandidate] = {}
    for candidate in candidates:
        key = _normalise(candidate.resource)
        if not key:
            raise ValueError("Resource name cannot be empty")
        if key not in unique:
            unique[key] = candidate
            continue
        previous = unique[key]
        evidence_ids = tuple(dict.fromkeys(previous.evidence_ids + candidate.evidence_ids))
        unique[key] = ResourceCandidate(
            resource=previous.resource,
            taught_as=previous.taught_as,
            relevance=previous.relevance or candidate.relevance,
            provenance=previous.provenance,
            confidence=previous.confidence,
            evidence_ids=evidence_ids,
        )
    return list(unique.values())


def _is_excluded_candidate(candidate: ResourceCandidate, case: dict[str, Any]) -> bool:
    haystack = _normalise(f"{candidate.resource} {candidate.taught_as}")
    return any(_normalise(term) in haystack for term in _excluded_resources(case))


def _filter_excluded_candidates(
    candidates: list[ResourceCandidate],
    case: dict[str, Any],
) -> tuple[list[ResourceCandidate], int]:
    kept = [candidate for candidate in candidates if not _is_excluded_candidate(candidate, case)]
    return kept, len(candidates) - len(kept)


def _cap_candidates(
    candidates: list[ResourceCandidate],
    max_resources: int,
) -> list[ResourceCandidate]:
    """Truncate to at most max_resources, keeping the strongest evidence first.

    Order: provenance strength (paper > curriculum > model), then confidence
    (high > medium > low), then insertion order (stable sort).
    """
    if max_resources < 1:
        raise ValueError("max_resources must be positive")
    ranked = sorted(
        enumerate(candidates),
        key=lambda pair: (
            PROVENANCE_RANK.get(pair[1].provenance.type, 3),
            CONFIDENCE_RANK.get(pair[1].confidence, 3),
            pair[0],
        ),
    )
    return [candidate for _, candidate in ranked[:max_resources]]


def _reference_selection_prompts(
    system: str,
    user: str,
    prompts: dict[str, str],
    learning_commons: dict[str, Any] | None,
) -> tuple[str, str]:
    if learning_commons is None:
        return system, user
    return (
        system + "\n\n" + prompts["LEARNING_COMMONS_SELECTION_SYSTEM"],
        user
        + "\n\n"
        + _render(
            prompts["LEARNING_COMMONS_SELECTION_USER"],
            {"learning_commons_references": prompt_candidates(learning_commons)},
        ),
    )


def _ungrounded_resources(
    client: Any,
    model: str,
    prompts: dict[str, str],
    case: dict[str, Any],
    *,
    learning_commons: dict[str, Any] | None = None,
) -> list[ResourceCandidate]:
    system, user = _reference_selection_prompts(
        prompts["UNGROUNDED_INVENTORY_SYSTEM"],
        _render(prompts["UNGROUNDED_INVENTORY_USER"], _input_values(case)),
        prompts,
        learning_commons,
    )
    payload, raw = chat_json(
        client,
        model,
        system,
        user,
        temperature=0.7,
        max_tokens=1600,
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("resources"), list):
        raise ValueError(f"Ungrounded inventory failed; raw response: {raw[:500]}")
    if learning_commons is not None:
        record_selection(learning_commons, payload)

    provenance = Provenance(
        type="model",
        source=f"{model} ungrounded inventory",
        evidence=(
            "Mathematical references were supplied, but no curriculum or paper "
            "evidence of prior teaching was supplied."
            if learning_commons is not None
            else "No curriculum or paper evidence was supplied to this condition."
        ),
    )
    candidates = []
    for item in payload["resources"]:
        if not isinstance(item, dict):
            raise ValueError("Ungrounded resources must be objects")
        candidates.append(
            ResourceCandidate(
                resource=_required_string(item, "resource"),
                taught_as=_required_string(item, "taught_as"),
                relevance=_required_string(item, "relevance"),
                provenance=provenance,
                confidence=_confidence(item),
            )
        )
    candidates = _deduplicate_candidates(candidates)
    candidates, _ = _filter_excluded_candidates(candidates, case)
    return candidates


def _grounded_resources(
    client: Any,
    model: str,
    prompts: dict[str, str],
    case: dict[str, Any],
    evidence_k: int,
    *,
    learning_commons: dict[str, Any] | None = None,
) -> tuple[list[ResourceCandidate], dict[str, Any]]:
    curriculum = _curriculum_evidence(case, evidence_k)
    evidence_by_id = {record["evidence_id"]: record for record in curriculum}
    retrieval = {
        "curated_records_held_out": len(_curated_evidence(case)),
        "curriculum_pages": len(curriculum),
        "evidence_ids": list(evidence_by_id),
    }
    if not curriculum and (learning_commons is None or not learning_commons.get("response")):
        if learning_commons is not None:
            record_selection(learning_commons, {"selected_sources": []})
        retrieval["status"] = "no_evidence"
        return [], retrieval

    values = _input_values(case) | {
        "curriculum_evidence": _prompt_evidence(curriculum),
    }
    system, user = _reference_selection_prompts(
        prompts["GROUNDED_MAPPING_SYSTEM"],
        _render(prompts["GROUNDED_MAPPING_USER"], values),
        prompts,
        learning_commons,
    )
    payload, raw = chat_json(
        client,
        model,
        system,
        user,
        temperature=0.2,
        max_tokens=2200,
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("resources"), list):
        raise ValueError(f"Grounded mapping failed; raw response: {raw[:500]}")
    if learning_commons is not None:
        record_selection(learning_commons, payload)

    mapped_candidates = []
    for item in payload["resources"]:
        if not isinstance(item, dict):
            raise ValueError("Grounded resources must be objects")
        ids = item.get("evidence_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(value, str) for value in ids):
            raise ValueError("Every grounded resource needs non-empty evidence_ids")
        unknown = sorted(set(ids) - evidence_by_id.keys())
        if unknown:
            raise ValueError(f"Grounded resource cited unknown evidence IDs: {unknown}")
        cited = [evidence_by_id[value] for value in ids]
        cited.sort(
            key=lambda record: {"paper": 0, "curriculum": 1, "model": 2}[record["provenance"].type]
        )
        primary = cited[0]
        primary_provenance = primary["provenance"]
        provenance = Provenance(
            type=primary_provenance.type,
            source=primary_provenance.source,
            page=primary_provenance.page,
            document=primary_provenance.document,
            source_url=primary_provenance.source_url,
            evidence=(f"{primary_provenance.evidence or ''}; evidence_ids={','.join(ids)}").strip(
                "; "
            ),
        )
        mapped_candidates.append(
            ResourceCandidate(
                resource=_required_string(item, "resource"),
                taught_as=_required_string(item, "taught_as"),
                relevance=_required_string(item, "relevance"),
                provenance=provenance,
                confidence=_confidence(item),
                evidence_ids=tuple(ids),
            )
        )
    retrieval["status"] = "mapped"
    retrieval["preserved_curated_records"] = 0
    candidates = _deduplicate_candidates(mapped_candidates)
    candidates, excluded_count = _filter_excluded_candidates(candidates, case)
    retrieval["excluded_resource_count"] = excluded_count
    return candidates, retrieval


def _expand_candidate(
    client: Any,
    model: str,
    prompts: dict[str, str],
    case: dict[str, Any],
    candidate: ResourceCandidate,
    condition: Condition,
) -> PriorMethodRecommendation:
    values = _input_values(case) | {
        "resource": candidate.resource,
        "taught_as": candidate.taught_as,
    }
    payload, raw = chat_json(
        client,
        model,
        prompts["EXPAND_RESOURCE_SYSTEM"],
        _render(prompts["EXPAND_RESOURCE_USER"], values),
        temperature=0.4,
        max_tokens=1100,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Resource expansion failed; raw response: {raw[:500]}")
    recommendation = PriorMethodRecommendation.from_payload(
        payload,
        provenance=candidate.provenance,
        condition=condition,
        default_resource=candidate.resource,
        default_taught_as=candidate.taught_as,
        default_relevance=candidate.relevance,
        default_confidence=candidate.confidence,
    )
    if recommendation.kind != "builds_on":
        raise ValueError(
            f"Expansion returned unsupported recommendation kind: {recommendation.kind}"
        )
    return recommendation


def _run_condition(
    client: Any,
    model: str,
    prompts: dict[str, str],
    case: dict[str, Any],
    condition: Condition,
    evidence_k: int,
    max_resources: int,
    *,
    learning_commons: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference_context = copy.deepcopy(learning_commons)
    retrieval: dict[str, Any] | None = None
    if condition == "grounded":
        candidates, retrieval = _grounded_resources(
            client, model, prompts, case, evidence_k, learning_commons=reference_context
        )
    else:
        candidates = _ungrounded_resources(
            client, model, prompts, case, learning_commons=reference_context
        )

    uncapped_count = len(candidates)
    candidates = _cap_candidates(candidates, max_resources)
    if retrieval is not None:
        retrieval["uncapped_resource_count"] = uncapped_count
        retrieval["capped_to"] = len(candidates)

    recommendations: list[PriorMethodRecommendation] = []
    if candidates:
        with ThreadPoolExecutor(max_workers=min(4, len(candidates))) as pool:
            futures = [
                pool.submit(
                    _expand_candidate,
                    client,
                    model,
                    prompts,
                    case,
                    candidate,
                    condition,
                )
                for candidate in candidates
            ]
            recommendations = [future.result() for future in futures]

    result = {
        "schema_version": (
            "prior-method-recommendations/v2"
            if reference_context is not None
            else "prior-method-recommendations/v1"
        ),
        "condition": condition,
        "model": model,
        "input": {
            key: case.get(key)
            for key in (
                "target_concept",
                "topic",
                "grade",
                "jurisdiction",
                "subject",
                "teacher_skills",
                "exercise_ids",
            )
            if key in case
        },
        "retrieval": retrieval,
        "resource_candidates": [candidate.to_dict() for candidate in candidates],
        "recommendations": [recommendation.to_dict() for recommendation in recommendations],
    }
    if reference_context is not None:
        result["learning_commons"] = reference_context
    return result


def _load_cases() -> list[dict[str, Any]]:
    cases = json.loads(CASES_PATH.read_text())
    if not isinstance(cases, list):
        raise ValueError(f"Cases must be a list: {CASES_PATH}")
    return cases


def _possible_matches(
    expected: list[str],
    candidates: list[dict[str, Any]],
) -> dict[str, list[str]]:
    output = {}
    for target in expected:
        target_tokens = _comparison_tokens(target)
        matches = []
        for candidate in candidates:
            resource = str(candidate.get("resource", ""))
            description = f"{resource} {candidate.get('taught_as', '')}"
            candidate_tokens = _comparison_tokens(description)
            if target_tokens and (
                _normalise(target) in _normalise(description)
                or len(target_tokens & candidate_tokens) / len(target_tokens) >= 0.5
            ):
                matches.append(resource)
        output[target] = matches
    return output


def _comparison_record(
    case: dict[str, Any],
    conditions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected = case.get("expected_resources", [])
    return {
        "case_id": case["id"],
        "gold_status": case.get("gold_status"),
        "gold_source": case.get("gold_source"),
        "gold_note": case.get("evaluation_note"),
        "expected_resources": expected,
        "conditions": {
            name: {
                **result,
                "possible_lexical_matches": _possible_matches(
                    expected,
                    result["resource_candidates"],
                ),
            }
            for name, result in conditions.items()
        },
    }


def _output_path(requested: str | None, label: str, model: str) -> Path:
    if requested:
        path = Path(requested)
        return path if path.is_absolute() else ROOT / path
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_")
    return RESULTS_DIR / f"{label}_{model_slug}_{stamp}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="Configured case ID; repeatable")
    parser.add_argument("--compare-expert", action="store_true")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--condition", choices=("grounded", "ungrounded", "both"), default="both")
    parser.add_argument(
        "--model", default="gpt41mini", choices=("gpt41mini", "gpt41", "gpt54", "luna")
    )
    parser.add_argument("--evidence-k", type=int, default=6)
    parser.add_argument(
        "--max-resources",
        type=int,
        default=DEFAULT_MAX_RESOURCES,
        help=(
            "Cap on distinct prior resources per condition after dedup "
            f"(default: {DEFAULT_MAX_RESOURCES}). Applied to both conditions "
            "so the comparison stays fair; strongest provenance/confidence kept first."
        ),
    )
    parser.add_argument("--output")
    parser.add_argument(
        "--learning-commons",
        action="store_true",
        help="Select mathematical references in the existing call; not evidence of prior teaching.",
    )
    parser.add_argument(
        "--learning-commons-query",
        help="Plain-language query override for one case (default: case topic).",
    )
    parser.add_argument("--learning-commons-cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--refresh-learning-commons",
        action="store_true",
        help="Fetch a fresh snapshot without overwriting earlier cached responses.",
    )
    parser.add_argument("--target-concept")
    parser.add_argument("--topic")
    parser.add_argument("--grade")
    parser.add_argument("--jurisdiction", default="")
    parser.add_argument("--subject", default="mathematics")
    parser.add_argument("--teacher-skill", action="append", default=[])
    args = parser.parse_args()
    if (args.learning_commons_query or args.refresh_learning_commons) and not args.learning_commons:
        parser.error("Learning Commons query/refresh requires --learning-commons")

    cases = _load_cases()
    if args.list_cases:
        for case in cases:
            print(f"{case['id']}: {case['grade']} / {case['jurisdiction']} / {case['topic']}")
        return
    if args.evidence_k < 1:
        raise ValueError("--evidence-k must be positive")
    if args.max_resources < 1:
        raise ValueError("--max-resources must be positive")

    if args.compare_expert:
        selected = [case for case in cases if case.get("run_in_comparison", False)]
        label = "expert_comparison"
    elif args.case:
        by_id = {case["id"]: case for case in cases}
        missing = sorted(set(args.case) - by_id.keys())
        if missing:
            raise ValueError(f"Unknown case IDs: {missing}")
        selected = [by_id[case_id] for case_id in args.case]
        label = "cases"
    else:
        if not args.target_concept or not args.topic:
            raise ValueError("Provide --case, --compare-expert, or direct target/topic arguments")
        selected = [
            {
                "id": "ad_hoc",
                "target_concept": args.target_concept,
                "topic": args.topic,
                "grade": int(args.grade) if args.grade and args.grade.isdigit() else args.grade,
                "jurisdiction": args.jurisdiction,
                "subject": args.subject,
                "teacher_skills": args.teacher_skill,
            }
        ]
        label = "ad_hoc"
    if args.learning_commons_query and len(selected) != 1:
        parser.error("--learning-commons-query requires exactly one selected case")
    reference_output_path = (
        _output_path(args.output, label, args.model) if args.learning_commons else None
    )
    if reference_output_path is not None and reference_output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite Learning Commons run: {reference_output_path}"
        )

    prompts = _prompts()
    client, model = load_client(args.model)
    output_records = []
    for case in selected:
        print(f"=== {case['id']} ===")
        reference_context = None
        if args.learning_commons:
            reference_context = retrieve_context(
                case,
                cache_dir=args.learning_commons_cache_dir,
                query=args.learning_commons_query,
                refresh=args.refresh_learning_commons,
            )
            print(
                "  Learning Commons: "
                f"{len(reference_context['response'])} results; "
                f"cache_hit={reference_context['cache_hit']}"
            )
        if args.condition == "both":
            condition_names = ("ungrounded", "grounded")
        else:
            condition_names = (args.condition,)
        results = {}
        for condition in condition_names:
            print(f"  running {condition}")
            results[condition] = _run_condition(
                client,
                model,
                prompts,
                case,
                condition,
                args.evidence_k,
                args.max_resources,
                learning_commons=reference_context,
            )
            print(
                f"  {condition}: {len(results[condition]['resource_candidates'])} resources, "
                f"{len(results[condition]['recommendations'])} recommendations"
            )
        if args.compare_expert or len(condition_names) == 2:
            output_records.append(_comparison_record(case, results))
        else:
            output_records.append(
                {
                    "case_id": case["id"],
                    "condition": condition_names[0],
                    "result": results[condition_names[0]],
                }
            )

    path = reference_output_path or _output_path(args.output, label, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": (
            "prior-method-recommendations/v2"
            if args.learning_commons
            else "prior-method-recommendations/v1"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "records": output_records,
    }
    if args.learning_commons:
        save_run(payload, path)
    else:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    display_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"saved -> {display_path}")


if __name__ == "__main__":
    main()
