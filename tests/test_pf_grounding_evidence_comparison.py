from __future__ import annotations

import inspect
import json
import threading
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_pf_grounding_evidence_comparison as study


CONFIG = study.read_json(study.DEFAULT_CONFIG)


def _normalized_context(context: dict) -> dict:
    normalized = json.loads(json.dumps(context))
    inventory = normalized[study.INVENTORY_KEY]
    inventory["local_curriculum"] = []
    inventory["learning_commons_standard_descriptions"] = []
    return normalized


def test_frozen_design_has_exact_three_arm_schedule_and_cap():
    study.validate_config(CONFIG)
    plan = study.schedule(CONFIG)

    assert len(plan) == 63
    assert sum(item["phase"] == "main" for item in plan) == 60
    assert sum(item["phase"] == "calibration" for item in plan) == 3
    main_counts = Counter(item["arm"] for item in plan if item["phase"] == "main")
    assert main_counts == {"A": 20, "B": 20, "C": 20}
    per_topic = Counter(
        (item["case_id"], item["repeat"], item["arm"])
        for item in plan if item["phase"] == "main"
    )
    assert len(per_topic) == 60
    assert all(count == 1 for count in per_topic.values())
    assert CONFIG["request_cap"] == 800
    assert CONFIG["max_workers"] == 3
    assert CONFIG["model_id"] == study.STUDY_MODEL_ID == "gpt-6-luna"
    assert CONFIG["preconsumed_request_reserve"] == 12
    assert sum(
        value for key, value in CONFIG["preconsumed_request_breakdown"].items()
        if key != "source"
    ) == 12


def test_each_case_freezes_one_d1_and_only_varies_evidence_arrays():
    cases = CONFIG["cases"] + CONFIG["calibration_cases"]
    plan = study.schedule(CONFIG)

    for case in cases:
        frozen = study.build_case_inputs(CONFIG, case)
        contexts = frozen["shared_contexts"]
        assert frozen["case"]["id"] == case["id"]
        assert frozen["fixed_d1"]["origin"] == "fixed_stipulated_context_not_generated_D1"
        assert [
            item["resource"]
            for item in frozen["fixed_d1"]["records"][0]["result"]["recommendations"]
        ] == case["teacher_recently_taught"]
        assert contexts["A"][study.INVENTORY_KEY]["local_curriculum"] == []
        assert contexts["A"][study.INVENTORY_KEY]["learning_commons_standard_descriptions"] == []
        assert contexts["B"][study.INVENTORY_KEY]["local_curriculum"]
        assert contexts["B"][study.INVENTORY_KEY]["learning_commons_standard_descriptions"] == []
        assert contexts["C"][study.INVENTORY_KEY]["local_curriculum"] == []
        assert contexts["C"][study.INVENTORY_KEY]["learning_commons_standard_descriptions"]
        normalized = [_normalized_context(context) for context in contexts.values()]
        assert all(context == normalized[0] for context in normalized[1:])
        assert len({
            context[study.INVENTORY_KEY]["instruction"] for context in contexts.values()
        }) == 1
        assert "not learner prior knowledge" in contexts["A"][study.INVENTORY_KEY]["instruction"]
        assert "Do not override the selected task request" in contexts["A"][study.INVENTORY_KEY][
            "instruction"
        ]
        assert frozen["learning_commons"]["study_provenance"]["api_requests_for_this_study"] == 0
        assert frozen["local_retrieval"]["provenance"]["api_requests_for_this_study"] == 0
        assert all(
            record["source_url"].startswith(("https://", "http://"))
            for record in frozen["local_retrieval"]["records"]
        )
        assert all(
            record["source_url"].startswith("https://")
            and record.get("author")
            and record.get("provider")
            and record.get("license")
            and record.get("attributionStatement")
            for record in contexts["C"][study.INVENTORY_KEY][
                "learning_commons_standard_descriptions"
            ]
        )
        attempts = [
            item for item in plan
            if item["case_id"] == case["id"]
        ]
        assert attempts
        assert all(
            item["attempt_path"].startswith(f"attempts/{item['phase']}/{case['id']}/")
            for item in attempts
        )


def test_every_generation_call_uses_the_frozen_common_prompt_wrapper():
    diagnostic_source = inspect.getsource(study.diagnostic._traced_chat)
    assert r"\n\nSHARED BENCHMARK CONTEXT (use throughout this design stage):\n" in (
        diagnostic_source
    )
    assert study.SHARED_PROMPT_WRAPPER == (
        "\n\nSHARED BENCHMARK CONTEXT (use throughout this design stage):\n"
    )
    assert study.INVENTORY_KEY == "mathematical_reference_inventory"
    assert "reused_d1_path_str=str(inputs / \"fixed_d1.json\")" in inspect.getsource(
        study.attempt_worker
    )


def test_frozen_source_hashes_cover_runner_config_corpus_and_lc_snapshots():
    hashes = study.source_hashes(study.DEFAULT_CONFIG)
    required = {
        study.relative(study.DEFAULT_CONFIG),
        study.relative(Path(study.__file__)),
        study.relative(study.curriculum.CORPUS_PATH),
        study.relative(study.ROOT / "experiments/configs/pf_grounding_study_20261013.json"),
        study.relative(
            study.ROOT / "experiments/results/pf_grounding_study_20261013/manifest.json"
        ),
        *(
            study.relative(study.ROOT / case["learning_commons_snapshot"])
            for case in CONFIG["cases"] + CONFIG["calibration_cases"]
        ),
        *(
            study.relative(path)
            for path in (
                study.ROOT / "experiments/results/pf_grounding_study_20261013/inputs"
            ).glob("*/learning_commons.json")
        ),
    }

    assert required <= hashes.keys()
    for path in required:
        assert hashes[path] == study.digest(study.ROOT / path)


class _FakeResponse:
    id = "fake-response"
    model = "gpt-6-luna"
    usage = None
    choices = [SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content='{"ok":true}'))]


class _FakeCompletions:
    def __init__(self):
        self.calls = []
        self.options = []
        self.fail = False
        self.chat = SimpleNamespace(completions=self)

    def with_options(self, **options):
        self.options.append(options)
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("simulated transport failure")
        return _FakeResponse()


def test_gpt6_settings_and_request_cap_count_failures_without_retries():
    fake = _FakeCompletions()
    payload, _ = study.gpt6_chat_json(
        fake, study.STUDY_MODEL_ID, "system", "user", temperature=0.7, max_tokens=91
    )
    assert payload == {"ok": True}
    assert fake.calls[0]["model"] == "gpt-6-luna"
    assert fake.calls[0]["max_completion_tokens"] == 91
    assert "temperature" not in fake.calls[0]
    assert study.effective_settings(
        "gpt-6-luna", {"temperature": 0.7, "max_tokens": 91}
    ) == {"max_completion_tokens": 91}

    counter = SimpleNamespace(value=CONFIG["preconsumed_request_reserve"])
    wrapped_client = _FakeCompletions()
    observed = study.ObservedClient(
        wrapped_client, Path("/dev/null"), counter, threading.Lock(),
        cap=CONFIG["preconsumed_request_reserve"] + 1,
        attempt_cap=study.max_calls_per_attempt(),
    )
    observed.with_options(max_retries=0)
    observed.chat.completions.create(model="gpt-6-luna")
    assert wrapped_client.options == [{"max_retries": 0}]
    assert counter.value == CONFIG["preconsumed_request_reserve"] + 1
    assert len(wrapped_client.calls) == 1
    with pytest.raises(study.RequestBudgetExceededError):
        observed.chat.completions.create(model="gpt-6-luna")
    assert counter.value == CONFIG["preconsumed_request_reserve"] + 1
    assert len(wrapped_client.calls) == 1

    failed_counter = SimpleNamespace(value=CONFIG["preconsumed_request_reserve"])
    failed_client = _FakeCompletions()
    failed_client.fail = True
    failed_observed = study.ObservedClient(
        failed_client, Path("/dev/null"), failed_counter, threading.Lock(),
        cap=CONFIG["request_cap"], attempt_cap=study.max_calls_per_attempt(),
    )
    with pytest.raises(RuntimeError, match="simulated transport failure"):
        failed_observed.chat.completions.create(model="gpt-6-luna")
    assert failed_counter.value == CONFIG["preconsumed_request_reserve"] + 1
    assert len(failed_client.calls) == 1
