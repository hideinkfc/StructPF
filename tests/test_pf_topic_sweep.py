import json

import pytest

from scripts import run_pf_topic_sweep as sweep


def test_prepare_freezes_twenty_topics_and_rejects_changes(tmp_path):
    config = sweep.ROOT / "experiments/configs/pf_topic_sweep_20261011.json"
    output = tmp_path / "run"
    manifest = sweep.prepare(config, output)
    cases = manifest["config"]["cases"]
    assert len(cases) == len({case["id"] for case in cases}) == 20
    assert manifest["protocol"]["fresh_D1_D2a_D2b_D3"]
    assert not manifest["protocol"]["old_outputs_reused"]
    for source in (
        "src/generation/prompts/situation_skeletons.yaml",
        "src/utils/llm_client.py",
        "src/utils/config.py",
    ):
        assert manifest["source_hashes"][source] == sweep.diagnostic._compute_sha256(
            sweep.ROOT / source
        )
    assert sweep.prepare(config, output) == manifest
    manifest["source_hashes"]["scripts/design_data_stage.py"] = "changed"
    (output / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Frozen inputs or pipeline changed"):
        sweep.prepare(config, output)


def test_render_shows_all_topics_and_failed_attempt(tmp_path):
    config = sweep.ROOT / "experiments/configs/pf_topic_sweep_20261011.json"
    output = tmp_path / "run"
    sweep.prepare(config, output)
    directory = output / "fraction_equivalence"
    directory.mkdir()
    (directory / "result.json").write_text(
        json.dumps({"status": "D1_failed", "error": "API failure <not hidden>", "stages": {}})
    )
    sweep.render(output)
    text = (output / "tasks.html").read_text()
    assert text.count("<section ") == 20
    assert "No student task: D1_failed" in text
    assert "API failure &lt;not hidden&gt;" in text
    assert "not a human rating" in text


def test_run_preserves_failed_attempt_without_call(tmp_path, monkeypatch):
    config = sweep.ROOT / "experiments/configs/pf_topic_sweep_20261011.json"
    output = tmp_path / "run"
    sweep.prepare(config, output)
    directory = output / "fraction_equivalence"
    directory.mkdir()
    result = {"status": "D1_failed", "error": "API failure", "model_call_count": 1}
    (directory / "result.json").write_text(json.dumps(result))

    def unexpected(*args, **kwargs):
        pytest.fail("An existing failed attempt must not be regenerated")

    monkeypatch.setattr(sweep.diagnostic, "run_case_worker", unexpected)
    manifest = sweep.run(config, output, ["fraction_equivalence"], workers=1)
    assert manifest["attempts"]["fraction_equivalence"]["status"] == "D1_failed"
    assert manifest["source_integrity_unchanged"]


def test_run_rejects_unknown_cases_before_call(tmp_path):
    config = sweep.ROOT / "experiments/configs/pf_topic_sweep_20261011.json"
    with pytest.raises(ValueError, match="Requested case IDs"):
        sweep.run(config, tmp_path / "run", ["not_a_topic"], workers=1)


def test_prepare_validates_and_freezes_official_packets(tmp_path, monkeypatch):
    config = sweep.ROOT / "experiments/configs/pf_topic_sweep_20261011.json"
    ids = [case["id"] for case in json.loads(config.read_text())["cases"]]
    evidence = [
        {
            "standard_id": "test-standard",
            "label": "Illustrative test evidence, not a real standard",
            "source_url": "https://example.org/test",
            "text": "Illustrative prerequisite excerpt for a software test.",
        }
    ]
    packets = {"cases": {case_id: {"grounding_evidence": evidence} for case_id in ids}}
    grounding = tmp_path / "grounding.json"
    grounding.write_text(json.dumps(packets))
    original = sweep.source_hashes
    monkeypatch.setattr(sweep, "source_hashes", lambda config, grounding=None: original(config))
    manifest = sweep.prepare(config, tmp_path / "run", grounding)
    assert manifest["grounding"] == packets
    assert "retrieval accuracy is not tested" in manifest["protocol"]["prior_source"]
    packets["cases"][ids[0]]["grounding_evidence"] = []
    grounding.write_text(json.dumps(packets))
    with pytest.raises(ValueError, match="non-empty list"):
        sweep.prepare(config, tmp_path / "invalid", grounding)
