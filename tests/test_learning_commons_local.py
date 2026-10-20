import json
from pathlib import Path

import pytest

from scripts.build_learning_commons_snapshot import build_snapshot
from scripts.learning_commons_local import inspect_node, load_snapshot, search_nodes, target_view

CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


def _record(record_type, identifier, labels, properties):
    return {
        "type": record_type,
        "identifier": identifier,
        "labels": labels,
        "properties": properties,
    }


def _properties(**overrides):
    return {
        "license": CC_BY,
        "attributionStatement": "Attribution text",
        **overrides,
    }


def _write_jsonl(path: Path, records):
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_snapshot_builder_keeps_curated_records_and_one_hop_links(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "snapshot"
    source.mkdir()
    standard = _record(
        "node",
        "standard-id",
        ["StandardsFrameworkItem"],
        _properties(
            statementCode="6.RP.A.2",
            description="Understand unit rates.",
            jurisdiction="Multi-State",
            caseIdentifierUUID="case-standard",
        ),
    )
    component = _record(
        "node",
        "component-id",
        ["LearningComponent"],
        _properties(description="Write a ratio as a unit rate."),
    )
    neighbor = _record(
        "node",
        "neighbor-id",
        ["StandardsFrameworkItem"],
        _properties(description="A related prior standard."),
    )
    parent = _record(
        "node",
        "parent-id",
        ["StandardsFramework"],
        _properties(name="Mathematics"),
    )
    unrelated = _record(
        "node",
        "unrelated-id",
        ["LearningComponent"],
        _properties(description="Unrelated skill"),
    )
    support = _record(
        "relationship",
        "support-id",
        [],
        _properties(relationshipType="supports"),
    ) | {
        "label": "supports",
        "source_identifier": "component-id",
        "target_identifier": "standard-id",
    }
    progression = _record(
        "relationship",
        "progression-id",
        [],
        {"license": CC0, "relationshipType": "buildsTowards"},
    ) | {
        "label": "buildsTowards",
        "source_identifier": "standard-id",
        "target_identifier": "neighbor-id",
    }
    hierarchy = _record(
        "relationship",
        "hierarchy-id",
        [],
        _properties(relationshipType="hasChild"),
    ) | {
        "label": "hasChild",
        "source_identifier": "parent-id",
        "target_identifier": "standard-id",
    }
    unrelated_edge = _record(
        "relationship",
        "unrelated-edge-id",
        [],
        _properties(relationshipType="supports"),
    ) | {
        "label": "supports",
        "source_identifier": "unrelated-id",
        "target_identifier": "unrelated-id",
    }
    _write_jsonl(
        source / "nodes.jsonl",
        [standard, component, neighbor, parent, unrelated],
    )
    _write_jsonl(
        source / "relationships.jsonl",
        [support, progression, hierarchy, unrelated_edge],
    )
    selection = {
        "source_version": "test",
        "retrieved_on": "2026-09-29",
        "nodes_export_url": "https://example.test/nodes.jsonl",
        "relationships_export_url": "https://example.test/relationships.jsonl",
        "allowed_licenses": [CC_BY, CC0],
        "targets": [
            {
                "id": "test-target",
                "learning_target": "Unit rate",
                "context": "Test",
                "mapping_status": "test proxy",
                "standard_node_ids": ["standard-id"],
                "learning_component_node_ids": ["component-id"],
            }
        ],
        "progression_standard_node_ids": ["standard-id"],
    }

    manifest = build_snapshot(source, output, selection)
    nodes, case_uuids, relationships = load_snapshot(output)

    assert set(nodes) == {"standard-id", "component-id", "neighbor-id", "parent-id"}
    assert {edge["label"] for edge in relationships} == {
        "supports",
        "buildsTowards",
        "hasChild",
    }
    assert manifest["snapshot_files"]["nodes.jsonl"]["records"] == 4
    assert "unrelated-id" not in nodes
    assert case_uuids["case-standard"]["identifier"] == "standard-id"


def test_local_search_and_inspect_return_provenance_and_edges(tmp_path):
    node = _record(
        "node",
        "standard-id",
        ["StandardsFrameworkItem"],
        _properties(
            statementCode="6.RP.A.2",
            description="Understand the concept of a unit rate.",
            jurisdiction="Multi-State",
            caseIdentifierUUID="case-standard",
        ),
    )
    neighbor = _record(
        "node",
        "component-id",
        ["LearningComponent"],
        _properties(description="Calculate a unit rate.", author="Achievement Network"),
    )
    edge = {
        "type": "relationship",
        "identifier": "edge-id",
        "label": "supports",
        "properties": _properties(relationshipType="supports"),
        "source_identifier": "component-id",
        "source_labels": ["LearningComponent"],
        "target_identifier": "standard-id",
        "target_labels": ["StandardsFrameworkItem"],
    }
    _write_jsonl(tmp_path / "nodes.jsonl", [node, neighbor])
    _write_jsonl(tmp_path / "relationships.jsonl", [edge])
    nodes, case_uuids, relationships = load_snapshot(tmp_path)

    results = search_nodes(nodes, "unit rate")
    inspected = inspect_node("case-standard", nodes, case_uuids, relationships)

    assert results[0]["identifier"] == "component-id"
    assert results[0]["license"] == CC_BY
    assert inspected["node"]["identifier"] == "standard-id"
    assert inspected["links"][0]["otherNode"]["identifier"] == "component-id"


def test_target_view_requires_every_curated_record_to_exist():
    selection = {
        "targets": [
            {
                "id": "missing-target",
                "learning_target": "Example",
                "context": "Test",
                "mapping_status": "proxy",
                "standard_node_ids": ["missing-id"],
                "learning_component_node_ids": [],
            }
        ]
    }

    with pytest.raises(ValueError, match="missing from snapshot"):
        target_view("missing-target", selection, {})


def test_snapshot_builder_rejects_non_open_selected_data(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    node = _record(
        "node",
        "standard-id",
        ["StandardsFrameworkItem"],
        {"license": "restricted"},
    )
    _write_jsonl(source / "nodes.jsonl", [node])
    _write_jsonl(source / "relationships.jsonl", [])
    selection = {
        "source_version": "test",
        "retrieved_on": "2026-09-29",
        "nodes_export_url": "https://example.test/nodes.jsonl",
        "relationships_export_url": "https://example.test/relationships.jsonl",
        "allowed_licenses": [CC_BY, CC0],
        "targets": [
            {
                "id": "test-target",
                "standard_node_ids": ["standard-id"],
                "learning_component_node_ids": [],
            }
        ],
        "progression_standard_node_ids": ["standard-id"],
    }

    with pytest.raises(ValueError, match="unapproved or missing license"):
        build_snapshot(source, tmp_path / "output", selection)
