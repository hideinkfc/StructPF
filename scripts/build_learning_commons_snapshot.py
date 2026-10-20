"""Build a small, licensed Learning Commons snapshot from the full JSONL exports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = (
    Path.home() / "Library" / "Caches" / "learning-commons" / "knowledge-graph" / "v1.14.0"
)
DEFAULT_SELECTION = ROOT / "data" / "learning_commons" / "target_selection.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "learning_commons" / "v1.14.0"
PROGRESSION_LABELS = {"buildsTowards", "relatesTo"}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
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
            yield record


def load_selection(path: Path) -> dict[str, Any]:
    selection = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(selection, dict) or not isinstance(selection.get("targets"), list):
        raise ValueError(f"Selection file must contain a targets list: {path}")
    return selection


def _target_ids(selection: dict[str, Any], field: str) -> set[str]:
    identifiers: set[str] = set()
    for target in selection["targets"]:
        values = target.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"Each target's {field} must be a list of identifiers")
        identifiers.update(values)
    return identifiers


def _validate_license(record: dict[str, Any], allowed: set[str], record_type: str) -> str:
    properties = record.get("properties", {})
    license_url = properties.get("license") if isinstance(properties, dict) else None
    if license_url not in allowed:
        raise ValueError(
            f"{record_type} {record.get('identifier')} has an unapproved or missing license: "
            f"{license_url!r}"
        )
    if "/licenses/by/4.0/" in license_url and not properties.get("attributionStatement"):
        raise ValueError(
            f"{record_type} {record.get('identifier')} is CC BY 4.0 but lacks attribution"
        )
    return license_url


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    contents = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records
    )
    path.write_text(contents, encoding="utf-8")


def build_snapshot(
    source_dir: Path,
    output_dir: Path,
    selection: dict[str, Any],
) -> dict[str, Any]:
    standard_ids = _target_ids(selection, "standard_node_ids")
    component_ids = _target_ids(selection, "learning_component_node_ids")
    progression_ids = set(selection.get("progression_standard_node_ids", []))
    allowed_licenses = set(selection.get("allowed_licenses", []))
    if not standard_ids or not allowed_licenses:
        raise ValueError("Selection must define standard_node_ids and allowed_licenses")
    if not progression_ids.issubset(standard_ids):
        raise ValueError("Progression seeds must be included in target standard_node_ids")

    seed_ids = standard_ids | component_ids
    relationships: list[dict[str, Any]] = []
    for edge in read_jsonl(source_dir / "relationships.jsonl"):
        if edge.get("type") != "relationship":
            raise ValueError("Expected only relationship records in relationships.jsonl")
        label = edge.get("label")
        source = edge.get("source_identifier")
        target = edge.get("target_identifier")
        endpoints = {source, target}
        keep = (
            (label == "supports" and target in standard_ids)
            or (label in PROGRESSION_LABELS and bool(endpoints & progression_ids))
            or (label == "hasChild" and bool(endpoints & standard_ids))
        )
        if keep:
            _validate_license(edge, allowed_licenses, "relationship")
            relationships.append(edge)
            seed_ids.update(endpoints)

    nodes: dict[str, dict[str, Any]] = {}
    for node in read_jsonl(source_dir / "nodes.jsonl"):
        if node.get("type") != "node":
            raise ValueError("Expected only node records in nodes.jsonl")
        identifier = node.get("identifier")
        if identifier in seed_ids:
            if identifier in nodes:
                raise ValueError(f"Duplicate node identifier in source export: {identifier}")
            _validate_license(node, allowed_licenses, "node")
            nodes[identifier] = node

    missing_ids = seed_ids - nodes.keys()
    if missing_ids:
        raise ValueError(f"Selected graph identifiers were not found: {sorted(missing_ids)}")
    for identifier in standard_ids:
        if "StandardsFrameworkItem" not in nodes[identifier].get("labels", []):
            raise ValueError(f"Expected a StandardsFrameworkItem for {identifier}")
    for identifier in component_ids:
        if "LearningComponent" not in nodes[identifier].get("labels", []):
            raise ValueError(f"Expected a LearningComponent for {identifier}")

    node_records = [nodes[identifier] for identifier in sorted(nodes)]
    relationships.sort(key=lambda edge: edge["identifier"])
    for edge in relationships:
        if edge["source_identifier"] not in nodes or edge["target_identifier"] not in nodes:
            raise ValueError(f"Relationship endpoints missing from snapshot: {edge['identifier']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "nodes.jsonl"
    relationships_path = output_dir / "relationships.jsonl"
    _write_jsonl(nodes_path, node_records)
    _write_jsonl(relationships_path, relationships)

    node_labels = Counter(label for node in node_records for label in node.get("labels", []))
    node_licenses = Counter(node["properties"]["license"] for node in node_records)
    relationship_licenses = Counter(edge["properties"]["license"] for edge in relationships)
    relationship_labels = Counter(edge["label"] for edge in relationships)
    manifest = {
        "source_version": selection["source_version"],
        "retrieved_on": selection["retrieved_on"],
        "nodes_export_url": selection["nodes_export_url"],
        "relationships_export_url": selection["relationships_export_url"],
        "source_files": {
            "nodes.jsonl": (source_dir / "nodes.jsonl").stat().st_size,
            "relationships.jsonl": (source_dir / "relationships.jsonl").stat().st_size,
        },
        "snapshot_files": {
            "nodes.jsonl": {
                "bytes": nodes_path.stat().st_size,
                "records": len(node_records),
                "labels": dict(sorted(node_labels.items())),
                "licenses": dict(sorted(node_licenses.items())),
            },
            "relationships.jsonl": {
                "bytes": relationships_path.stat().st_size,
                "records": len(relationships),
                "labels": dict(sorted(relationship_labels.items())),
                "licenses": dict(sorted(relationship_licenses.items())),
            },
        },
        "target_ids": [target["id"] for target in selection["targets"]],
        "selection_file": "data/learning_commons/target_selection.json",
        "scope_note": "Curated candidates and one-hop links; not a complete graph export.",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    selection = load_selection(args.selection)
    manifest = build_snapshot(args.source_dir, args.output_dir, selection)
    print(json.dumps(manifest["snapshot_files"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
