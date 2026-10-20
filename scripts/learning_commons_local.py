"""Search the curated Learning Commons JSONL snapshot without API access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_DIR = ROOT / "data" / "learning_commons" / "v1.14.0"
DEFAULT_SELECTION = ROOT / "data" / "learning_commons" / "target_selection.json"


def load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object in {path} at line {line_number}")
            records.append(record)
    return records


def load_snapshot(
    snapshot_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    nodes = load_records(snapshot_dir / "nodes.jsonl")
    relationships = load_records(snapshot_dir / "relationships.jsonl")
    by_identifier: dict[str, dict[str, Any]] = {}
    by_case_uuid: dict[str, dict[str, Any]] = {}
    for node in nodes:
        identifier = node.get("identifier")
        if not isinstance(identifier, str) or identifier in by_identifier:
            raise ValueError(f"Missing or duplicate graph node identifier: {identifier!r}")
        by_identifier[identifier] = node
        properties = node.get("properties", {})
        case_uuid = properties.get("caseIdentifierUUID")
        if isinstance(case_uuid, str):
            if case_uuid in by_case_uuid:
                raise ValueError(f"Duplicate CASE UUID in snapshot: {case_uuid}")
            by_case_uuid[case_uuid] = node
    for edge in relationships:
        if (
            edge.get("source_identifier") not in by_identifier
            or edge.get("target_identifier") not in by_identifier
        ):
            raise ValueError(
                f"Snapshot relationship has a missing endpoint: {edge.get('identifier')}"
            )
    return by_identifier, by_case_uuid, relationships


def summarize_node(node: dict[str, Any]) -> dict[str, Any]:
    properties = node.get("properties", {})
    return {
        "identifier": node["identifier"],
        "caseIdentifierUUID": properties.get("caseIdentifierUUID"),
        "labels": node.get("labels", []),
        "statementCode": properties.get("statementCode"),
        "name": properties.get("name"),
        "description": properties.get("description"),
        "jurisdiction": properties.get("jurisdiction"),
        "gradeLevel": properties.get("gradeLevel"),
        "academicSubject": properties.get("academicSubject"),
        "author": properties.get("author"),
        "provider": properties.get("provider"),
        "license": properties.get("license"),
        "attributionStatement": properties.get("attributionStatement"),
    }


def search_nodes(
    nodes: dict[str, dict[str, Any]], query: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1:
        raise ValueError("limit must be positive")
    terms = list(dict.fromkeys(query.casefold().split()))
    phrase = query.casefold()
    matches = []
    for node in nodes.values():
        searchable = json.dumps(node.get("properties", {}), ensure_ascii=False).casefold()
        matched_terms = [term for term in terms if term in searchable]
        if phrase in searchable and phrase not in matched_terms:
            matched_terms.append(phrase)
        if matched_terms:
            matches.append((len(matched_terms), summarize_node(node), matched_terms))
    matches.sort(
        key=lambda item: (
            -item[0],
            item[1].get("statementCode") or "",
            item[1]["identifier"],
        )
    )
    return [
        {**summary, "matchedTerms": matched_terms} for _, summary, matched_terms in matches[:limit]
    ]


def inspect_node(
    identifier: str,
    by_identifier: dict[str, dict[str, Any]],
    by_case_uuid: dict[str, dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    node = by_identifier.get(identifier) or by_case_uuid.get(identifier)
    if node is None:
        raise ValueError(
            f"{identifier} is not in this curated snapshot; that does not mean it is "
            "absent from the full Learning Commons graph"
        )
    graph_id = node["identifier"]
    links = []
    for edge in relationships:
        source = edge["source_identifier"]
        target = edge["target_identifier"]
        if graph_id not in {source, target}:
            continue
        other_id = target if source == graph_id else source
        links.append(
            {
                "relationship": edge,
                "otherNode": summarize_node(by_identifier[other_id]),
            }
        )
    return {"node": node, "links": links}


def load_selection(path: Path) -> dict[str, Any]:
    selection = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(selection, dict) or not isinstance(selection.get("targets"), list):
        raise ValueError(f"Selection file must contain a targets list: {path}")
    return selection


def target_view(
    target_id: str,
    selection: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    target = next(
        (item for item in selection["targets"] if item.get("id") == target_id),
        None,
    )
    if target is None:
        raise ValueError(f"Unknown target id: {target_id}")
    record_ids = [
        *target.get("standard_node_ids", []),
        *target.get("learning_component_node_ids", []),
    ]
    missing = [identifier for identifier in record_ids if identifier not in nodes]
    if missing:
        raise ValueError(f"Target records missing from snapshot: {missing}")
    return {
        key: value
        for key, value in target.items()
        if key not in {"standard_node_ids", "learning_component_node_ids"}
    } | {"candidateRecords": [summarize_node(nodes[identifier]) for identifier in record_ids]}


def graph_progression_bundle(
    target_id: str,
    *,
    snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR,
    selection_path: Path = DEFAULT_SELECTION,
) -> dict[str, Any] | None:
    """Return structured target standards, Coherence Map prerequisites, and learning components."""
    if not snapshot_dir.exists() or not selection_path.exists():
        return None
    selection = load_selection(selection_path)
    normalized_id = target_id.removeprefix("expert_")
    target = next(
        (
            item
            for item in selection["targets"]
            if item.get("id") in {target_id, normalized_id}
            or str(item.get("id", "")).startswith(target_id)
        ),
        None,
    )
    if target is None:
        return None
    nodes, _, relationships = load_snapshot(snapshot_dir)
    standard_ids = [nid for nid in target.get("standard_node_ids", []) if nid in nodes]
    component_ids = [nid for nid in target.get("learning_component_node_ids", []) if nid in nodes]
    prereq_ids: list[str] = []
    seen_prereq: set[str] = set()
    seen_comp: set[str] = set(component_ids)
    for edge in relationships:
        label = edge.get("label")
        src = edge.get("source_identifier")
        dst = edge.get("target_identifier")
        if dst in standard_ids and src in nodes:
            if label == "buildsTowards" and src not in seen_prereq and src not in standard_ids:
                seen_prereq.add(src)
                prereq_ids.append(src)
            elif label == "supports" and src not in seen_comp:
                seen_comp.add(src)
                component_ids.append(src)

    def _compact(nid: str) -> dict[str, Any]:
        info = summarize_node(nodes[nid])
        return {
            "statementCode": info.get("statementCode"),
            "description": info.get("description"),
            "jurisdiction": info.get("jurisdiction"),
        }

    return {
        "source_version": selection.get("source_version", "v1.14.0"),
        "target_id": target_id,
        "mapping_note": target.get("mapping_note", ""),
        "target_standards": [_compact(nid) for nid in standard_ids],
        "prerequisite_standards_builds_towards": [_compact(nid) for nid in prereq_ids],
        "supporting_learning_components": [
            summarize_node(nodes[nid]).get("description")
            for nid in component_ids
            if summarize_node(nodes[nid]).get("description")
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("targets", help="List the three curated expert-task lookups")
    search = subparsers.add_parser("search", help="Literal text search over snapshot records")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    target = subparsers.add_parser("target", help="Show candidate records for an expert task")
    target.add_argument("target_id")
    show = subparsers.add_parser("show", help="Show a record and its included graph links")
    show.add_argument("identifier", help="Graph identifier or CASE UUID")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        selection = load_selection(args.selection)
        if args.command == "targets":
            result = [
                {
                    "id": target["id"],
                    "learning_target": target["learning_target"],
                    "context": target["context"],
                    "mapping_status": target["mapping_status"],
                }
                for target in selection["targets"]
            ]
        else:
            nodes, case_uuids, relationships = load_snapshot(args.snapshot_dir)
            if args.command == "search":
                result = {
                    "scope": "curated local snapshot, not the complete graph",
                    "results": search_nodes(nodes, args.query, limit=args.limit),
                }
            elif args.command == "target":
                result = target_view(args.target_id, selection, nodes)
            else:
                result = inspect_node(args.identifier, nodes, case_uuids, relationships)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
