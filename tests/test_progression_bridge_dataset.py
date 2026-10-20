"""Tests for the 10-case Learning Commons Progression Bridge dataset."""

from __future__ import annotations

import json

from scripts.build_progression_bridge_dataset import (
    ALLOWED_LICENSES,
    DEFAULT_DATASET_PATH,
    DEFAULT_SLICE_DIR,
    SCHEMA_VERSION,
    load_progression_bridge_dataset,
    progression_bridge_bundle,
)


def test_dataset_schema_and_case_count() -> None:
    dataset = load_progression_bridge_dataset(DEFAULT_DATASET_PATH)
    assert dataset["schema_version"] == SCHEMA_VERSION
    assert dataset["n_cases"] == 30
    assert len(dataset["cases"]) == 30
    measure = dataset["evaluation_measure"]
    assert measure["name"] == "progression_bridge_fit"
    assert measure["scale"] == [0, 1, 2]


def test_each_case_has_prereqs_components_and_rubric() -> None:
    dataset = load_progression_bridge_dataset(DEFAULT_DATASET_PATH)
    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    for case in dataset["cases"]:
        cid = case["id"]
        assert cid not in seen_ids
        seen_ids.add(cid)
        assert case["grade"] in {5, 6, 7, 8, 9, 10}
        assert case["subject"] == "mathematics"
        assert case["topic"].strip()
        assert case["target_concept"].strip()

        bridge = case["progression_bridge"]
        target = bridge["target_standard"]
        code = target["statementCode"]
        assert code not in seen_codes
        seen_codes.add(code)
        assert target["license"] in ALLOWED_LICENSES
        assert target["attributionStatement"].strip()

        prereqs = bridge["prerequisite_standards_builds_towards"]
        assert len(prereqs) >= 1
        for p in prereqs:
            assert p["statementCode"] != code
            assert p["description"].strip()
            assert p["license"] in ALLOWED_LICENSES
            assert p["attributionStatement"].strip()

        assert len(bridge["prerequisite_learning_components"]) >= 1
        assert len(bridge["target_learning_components"]) >= 1

        anchor = case["bridge_rubric_anchor"]
        for key in (
            "s_prior_summary",
            "s_target_summary",
            "score_0_boundary_miss",
            "score_1_loose_match",
            "score_2_exact_bridge",
        ):
            assert isinstance(anchor.get(key), str) and anchor[key].strip()

        bundle = progression_bridge_bundle(cid)
        assert bundle["case_id"] == cid
        assert len(bundle["target_standards"]) == 1
        assert len(bundle["prerequisite_standards_builds_towards"]) == len(prereqs)
        assert len(bundle["supporting_learning_components"]) == len(
            bridge["prerequisite_learning_components"]
        )


def test_slice_files_and_manifest_match_dataset() -> None:
    manifest = json.loads((DEFAULT_SLICE_DIR / "manifest.json").read_text(encoding="utf-8"))
    nodes = [
        json.loads(line)
        for line in (DEFAULT_SLICE_DIR / "nodes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    edges = [
        json.loads(line)
        for line in (DEFAULT_SLICE_DIR / "relationships.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert manifest["n_cases"] == 30
    assert manifest["n_nodes"] == len(nodes) == 315
    assert manifest["n_relationships"] == len(edges) == 317
    node_ids = {n["identifier"] for n in nodes}
    for edge in edges:
        assert edge["source_identifier"] in node_ids
        assert edge["target_identifier"] in node_ids
        assert edge["label"] in {"buildsTowards", "supports"}
