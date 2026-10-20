import csv
import json
from pathlib import Path

import yaml

from src.evaluation.pf_rubric import learner_context

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/configs/pf_paper_benchmark.json"
PROMPT = ROOT / "src/generation/prompts/pf_paper_benchmark.yaml"


def test_fixed_paper_setting_and_attempt_counts():
    config = json.loads(CONFIG.read_text())
    assert config["conditions"] == ["V1", "V2", "V3", "PIPELINE"]
    assert config["n_per_condition"] == 30
    assert config["model_selector"] == "luna"
    assert config["case"]["grade"] == config["learner_context"]["grade"] == 7
    assert "7.RP.A.2" in config["case"]["target_concept"]
    assert config["case"]["benchmark_context"]["interest"] == "basketball and Stephen Curry"
    assert len(config["learner_context"]["assumed_prior_knowledge"]) == 2
    assert learner_context(config["learner_context"]) == config["learner_context"]
    assert {entry["standard_id"] for entry in config["grounding_evidence"]} == {
        "CCSS.Math.Content.7.RP.A.1",
        "CCSS.Math.Content.7.NS.A.1",
    }


def test_fixed_paper_pipeline_defaults_to_checked_design_data_without_translation():
    from scripts.design_data_stage import MAX_CALLS, MAX_TOKENS
    from scripts.run_pf_paper_benchmark import _frozen_settings, load_config

    config = load_config(CONFIG)
    settings = _frozen_settings(config)["pipeline"]
    assert settings["design_brief"] is True
    assert settings["proposal_k"] == config["pipeline"]["k"]
    assert settings["design_data_settings"] == {
        "max_calls": MAX_CALLS,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.0,
    }
    assert not {"plan_retry_max", "fill_max_tries", "fill_temperature"} & settings.keys()
    assert (
        not {"translation_temperature", "translation_retry_max"}
        & settings["design_brief_settings"].keys()
    )


def test_grounded_misconceptions_are_exact_eedi_entries():
    config = json.loads(CONFIG.read_text())
    provenance = config["misconception_provenance"]
    with (ROOT / provenance["source"]).open() as stream:
        entries = {
            int(row["MisconceptionId"]): row["MisconceptionName"] for row in csv.DictReader(stream)
        }
    assert len(config["misconceptions"]) == 6
    assert [entries[identifier] for identifier in provenance["ids_in_order"]] == config[
        "misconceptions"
    ]


def test_direct_prompt_uses_all_fifteen_frozen_rubric_anchors():
    direct = yaml.safe_load(PROMPT.read_text())
    rubric = yaml.safe_load((ROOT / "src/evaluation/prompts/pf_rubric.yaml").read_text())
    anchors = [
        line.strip()
        for line in rubric["system"].splitlines()
        if line.strip().startswith(("1 (Low):", "2 (Moderate):", "3 (High):"))
    ]
    assert len(anchors) == 15
    assert all(anchor in direct["system"] for anchor in anchors)


def test_five_examples_have_source_ids_and_reconstruction_disclosure():
    prompt = yaml.safe_load(PROMPT.read_text())
    source = yaml.safe_load((ROOT / prompt["example_file"]).read_text())
    known = {entry["id"] for entry in source["exercises"]}
    assert len(prompt["example_ids"]) == len(set(prompt["example_ids"])) == 5
    assert set(prompt["example_ids"]) <= known
    assert "not asserted to be Rahimi's exact five examples" in prompt["example_note"]
    assert "CC-BY-4.0" in prompt["example_source"]
