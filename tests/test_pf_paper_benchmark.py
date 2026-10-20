from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import scripts.run_pf_paper_benchmark as bench
from scripts.run_situation_skeletons import _prompts as load_pipeline_prompts


def _config() -> dict:
    return {
        "schema_version": "paper/v1",
        "conditions": ["V1", "V2", "V3", "PIPELINE"],
        "n_per_condition": 1,
        "model_selector": "luna",
        "workers": 1,
        "shuffle_seed": 20260923,
        "generation_max_tokens": 6000,
        "inference_max_tokens": 2000,
        "case": {
            "id": "case",
            "target_concept": "rate",
            "topic": "basketball",
            "grade": "7",
            "jurisdiction": "test",
            "subject": "mathematics",
            "teacher_recently_taught": "unit rate",
            "benchmark_context": {"player": "Stephen Curry"},
        },
        "learner_context": {
            "grade": "7",
            "subject": "mathematics",
            "jurisdiction": "test",
            "assumed_prior_knowledge": [{"resource": "multiplication", "taught_as": "multiply"}],
        },
        "misconceptions": ["Compare totals instead of rates."],
        "grounding_evidence": [
            {
                "standard_id": "TEST.1",
                "label": "Test standard",
                "source_url": "https://example.test/standard",
                "text": "A fixed test standard.",
            }
        ],
    }


def _prompt() -> dict:
    return {
        "version": "paper-v1",
        "system": "Return only task JSON.",
        "infer_system": "Return a JSON misconception list.",
        "infer_user": "{case_json}\n{learner_context_json}",
        "user": "{case_json}\n{learner_context_json}\n{misconceptions_json}",
    }


def test_pipeline_generation_receives_direct_rubric_anchors():
    direct = bench.load_prompt()["system"]
    pipeline = load_pipeline_prompts()

    def anchors(text: str) -> list[str]:
        start = text.index("1. Activation of Prior Knowledge (APK)")
        last_anchor = (
            "3 (High): Highly complex, requiring integration of multiple variables "
            "and representations"
        )
        end = text.index(last_anchor) + len(last_anchor)
        return [line.strip() for line in text[start:end].splitlines()]

    expected = anchors(direct)
    assert anchors(pipeline["PROPOSE_SKELETON_SYSTEM"]) == expected
    assert anchors(pipeline["WRITE_TASK_SYSTEM"]) == expected
    assert "something to decide or interpret beyond" in pipeline["PROPOSE_SKELETON_SYSTEM"]
    assert "explicit pairwise inequality constraints" in pipeline["PROPOSE_SKELETON_SYSTEM"]
    assert (
        "mixture of outcomes across different generated tasks"
        in pipeline["PROPOSE_SKELETON_SYSTEM"]
    )
    assert "single task" in pipeline["JUDGE_SKELETONS_SYSTEM"]
    assert 'Do not turn "use all rows"' in pipeline["JUDGE_SKELETONS_SYSTEM"]
    assert "checker to decide a student's recommendation" in pipeline["REVIEW_PLAN_SYSTEM"]
    assert 'unqualified "constant rule"' in pipeline["WRITE_TASK_SYSTEM"]


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    config = tmp_path / "config.json"
    prompt = tmp_path / "prompt.yaml"
    config.write_text(json.dumps(_config()), encoding="utf-8")
    prompt.write_text(yaml.safe_dump(_prompt()), encoding="utf-8")
    return config, prompt


def _response(payload: object, model: str = "gpt-5.6-luna"):
    return SimpleNamespace(
        model=model,
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload)),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


class _FakeCompletions:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _response(next(self.payloads))


class _FakeClient:
    def __init__(self, payloads):
        self.chat = SimpleNamespace(completions=_FakeCompletions(payloads))

    def with_options(self, **kwargs):
        assert kwargs == {"max_retries": 0}
        return self


def test_prepare_is_offline_and_resume_freezes_inputs(tmp_path):
    config, prompt = _write_inputs(tmp_path)
    output = tmp_path / "run"
    manifest, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt)
    assert manifest["status"] == "prepared"
    assert "execution_scope" not in manifest
    assert len(manifest["attempts"]) == 4
    assert manifest["frozen_settings"]["pipeline"]["proposal_k"] == 6
    assert manifest["frozen_settings"]["pipeline"]["design_brief"] is True
    assert manifest["frozen_settings"]["pipeline"]["design_brief_settings"]["max_tokens"] == 6000
    assert "plan_retry_max" not in manifest["frozen_settings"]["pipeline"]
    assert manifest["frozen_settings"]["pipeline"]["design_data_settings"]["max_calls"] == 3
    assert manifest["frozen_settings"]["sdk_max_retries"] == 0
    assert manifest["frozen_settings"]["transport_retries"] == 2
    assert "src/generation/prompts/prior_recommendations.yaml" in manifest["source_hashes"]
    assert "src/generation/prompts/situation_skeletons.yaml" in manifest["source_hashes"]
    assert "src/generation/prior_recommendations.py" in manifest["source_hashes"]
    for relative in (
        "scripts/design_brief_stage.py",
        "src/generation/design_briefs.py",
        "src/generation/prompts/design_briefs.yaml",
        "scripts/design_data_stage.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/prompts/design_data.yaml",
    ):
        assert relative in manifest["source_hashes"]
        snapshot = output / "source_snapshot" / relative
        assert snapshot.read_bytes() == (bench.ROOT / relative).read_bytes()
        assert bench._sha256(snapshot) == manifest["source_hashes"][relative]
    assert (output / "config.json").is_file()
    assert (output / "prompt.yaml").is_file()
    with pytest.raises(FileExistsError):
        bench.prepare_run(output, config_path=config, prompt_path=prompt)
    resumed, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)
    assert resumed["judge_order"] == manifest["judge_order"]
    config.write_text(json.dumps({**_config(), "shuffle_seed": 7}), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen"):
        bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)


def test_only_condition_calibration_keeps_full_schedule_and_freezes_scope(tmp_path):
    config, prompt = _write_inputs(tmp_path)
    output = tmp_path / "calibration"
    manifest, _, _ = bench.prepare_run(
        output,
        config_path=config,
        prompt_path=prompt,
        only_condition="PIPELINE",
        limit_per_condition=1,
    )

    assert len(manifest["attempts"]) == 4
    assert {item["condition"] for item in manifest["attempts"].values()} == set(bench.CONDITIONS)
    assert manifest["execution_scope"] == {
        "kind": "single_condition_calibration",
        "condition": "PIPELINE",
        "limit_per_condition": 1,
        "benchmark_status": "not_a_benchmark",
    }
    assert manifest["benchmark_status"] == "not_a_benchmark"
    resumed, _, _ = bench.prepare_run(
        output,
        config_path=config,
        prompt_path=prompt,
        resume=True,
        only_condition="PIPELINE",
        limit_per_condition=1,
    )
    assert resumed["execution_scope"] == manifest["execution_scope"]

    with pytest.raises(ValueError, match="execution_scope changed"):
        bench.prepare_run(
            output,
            config_path=config,
            prompt_path=prompt,
            resume=True,
            only_condition="V1",
            limit_per_condition=1,
        )


def test_only_condition_runs_no_other_arm_and_skips_judging_or_comparison(tmp_path, monkeypatch):
    config, prompt = _write_inputs(tmp_path)
    output = tmp_path / "calibration"
    attempted = []

    def fake_attempt_worker(spec, attempt_path_str, *args):
        attempted.append(spec["attempt_id"])
        result = {
            **spec,
            "status": "blocked",
            "model_name": "gpt-5.6-luna",
            "finished_at": bench._now(),
        }
        bench._write_json(Path(attempt_path_str) / "attempt.json", result)
        return result

    class InlineFuture:
        def __init__(self, result):
            self.result_value = result

        def result(self):
            return self.result_value

    class InlinePool:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, function, *args, **kwargs):
            return InlineFuture(function(*args, **kwargs))

    monkeypatch.setattr(bench, "_run_attempt_worker", fake_attempt_worker)
    monkeypatch.setattr(bench.concurrent.futures, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(bench.concurrent.futures, "as_completed", lambda futures: futures)
    monkeypatch.setattr(
        bench.multiprocessing,
        "Manager",
        lambda: SimpleNamespace(BoundedSemaphore=lambda _max_api: None, shutdown=lambda: None),
    )
    monkeypatch.setattr(
        bench,
        "_judge_one",
        lambda *args, **kwargs: pytest.fail("single-condition calibration must not judge"),
    )

    manifest = bench.run_benchmark(
        output,
        config_path=config,
        prompt_path=prompt,
        limit_per_condition=1,
        only_condition="PIPELINE",
    )
    summary = json.loads((output / "summary.json").read_text())

    assert attempted == ["PIPELINE-001"]
    assert manifest["status"] == "incomplete"
    assert manifest["benchmark_status"] == "not_a_benchmark"
    assert manifest["execution_scope"]["condition"] == "PIPELINE"
    assert manifest["judging_status"] == "skipped_single_condition_calibration"
    assert manifest["source_integrity_unchanged"] is True
    assert all(
        item["status"] == "pending"
        for key, item in manifest["attempts"].items()
        if not key.startswith("PIPELINE-")
    )
    assert summary["benchmark_status"] == "not_a_benchmark"
    assert summary["comparisons"]["status"] == "not_computed"
    assert summary["judging"]["status"] == "skipped"
    assert all("differences_vs_V1" not in item for item in summary["conditions"].values())


def test_only_condition_cli_selector_is_opt_in():
    default = bench.parse_args([])
    calibration = bench.parse_args(["--only-condition", "PIPELINE"])

    assert default.only_condition is None
    assert not hasattr(default, "design_brief")
    assert calibration.only_condition == "PIPELINE"
    with pytest.raises(SystemExit):
        bench.parse_args(["--design-brief"])


@pytest.mark.parametrize(
    "mutated_source",
    [
        "src/generation/prompts/prior_recommendations.yaml",
        "scripts/design_brief_stage.py",
        "src/generation/design_briefs.py",
        "src/generation/prompts/design_briefs.yaml",
        "scripts/design_data_stage.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/prompts/design_data.yaml",
    ],
)
def test_pipeline_prompt_mutation_blocks_resume(tmp_path, monkeypatch, mutated_source):
    config, prompt = _write_inputs(tmp_path)
    fake_root = tmp_path / "root"
    tracked_prompt = fake_root / mutated_source
    for relative in (
        "scripts/run_pf_paper_benchmark.py",
        "scripts/run_pf_diagnostic.py",
        "scripts/run_pf_judge.py",
        "scripts/prior_methods/common.py",
        "scripts/design_brief_stage.py",
        "scripts/design_data_stage.py",
        "scripts/run_situation_skeletons.py",
        "scripts/run_prior_recommendations.py",
        "src/evaluation/pf_rubric.py",
        "src/evaluation/prompts/pf_rubric.yaml",
        "src/generation/fill_check.py",
        "src/generation/prompts/prior_recommendations.yaml",
        "src/generation/prompts/design_briefs.yaml",
        "src/generation/prompts/design_data.yaml",
        "src/generation/prompts/situation_skeletons.yaml",
        "src/generation/prior_recommendations.py",
        "src/generation/design_briefs.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/situation_skeletons.py",
    ):
        path = fake_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen source\n", encoding="utf-8")
    tracked_prompt.write_text("version: one\n", encoding="utf-8")
    monkeypatch.setattr(bench, "ROOT", fake_root)

    output = tmp_path / "run"
    bench.prepare_run(output, config_path=config, prompt_path=prompt)
    tracked_prompt.write_text("version: two\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Frozen source_hashes"):
        bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)


def test_direct_v2_records_usage_and_ready_task(tmp_path, monkeypatch):
    config, prompt_path = _write_inputs(tmp_path)
    config_value = bench.load_config(config)
    prompt = bench.load_prompt(prompt_path)
    client = _FakeClient(
        [
            {
                "status": "ready",
                "title": "Compare",
                "body": "Use any method.",
                "question": "Which rate?",
            }
        ]
    )
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))
    result = bench._run_direct_attempt(
        config_value,
        prompt,
        "V2",
        tmp_path / "trace.jsonl",
    )
    assert result["status"] == "ready"
    assert result["response_metadata"]["usage"]["total_tokens"] == 30
    assert len(client.chat.completions.calls) == 1
    assert "V2" not in client.chat.completions.calls[0]["messages"][1]["content"]


def test_v1_request_is_blind_to_misconception_list(tmp_path, monkeypatch):
    config, prompt_path = _write_inputs(tmp_path)
    client = _FakeClient(
        [
            {
                "status": "blocked",
                "blocking_issues": ["not enough information"],
            }
        ]
    )
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))
    result = bench._run_direct_attempt(
        bench.load_config(config),
        bench.load_prompt(prompt_path),
        "V1",
        tmp_path / "trace.jsonl",
    )
    assert result["status"] == "blocked"
    user = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "Compare totals instead of rates." not in user


def test_v3_inference_schema_failure_is_explicit(tmp_path, monkeypatch):
    config, prompt_path = _write_inputs(tmp_path)
    client = _FakeClient([{"not_misconceptions": []}])
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))
    result = bench._run_direct_attempt(
        bench.load_config(config),
        bench.load_prompt(prompt_path),
        "V3",
        tmp_path / "trace.jsonl",
    )
    assert result["status"] == "invalid_response"
    assert len(client.chat.completions.calls) == 1


@pytest.mark.parametrize(
    "misconceptions",
    [
        ["Only five"],
        ["Same"] * 6,
        ["", "one", "two", "three", "four", "five"],
    ],
)
def test_v3_inference_requires_six_distinct_nonempty_misconceptions(
    tmp_path, monkeypatch, misconceptions
):
    config, prompt_path = _write_inputs(tmp_path)
    client = _FakeClient([{"misconceptions": misconceptions}])
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))

    result = bench._run_direct_attempt(
        bench.load_config(config),
        bench.load_prompt(prompt_path),
        "V3",
        tmp_path / "trace.jsonl",
    )

    assert result["status"] == "invalid_response"
    assert "exactly six" in result["error"]
    assert len(client.chat.completions.calls) == 1


def test_v3_literal_infer_prompt_receives_case_and_learner_context(tmp_path, monkeypatch):
    config, prompt_path = _write_inputs(tmp_path)
    import yaml

    prompt = _prompt()
    prompt["infer_user"] = "Infer six misconceptions for the supplied target and learner context."
    prompt_path.write_text(
        yaml.safe_dump(prompt),
        encoding="utf-8",
    )
    client = _FakeClient(
        [
            {"misconceptions": [f"Misconception {index}" for index in range(6)]},
            {
                "status": "ready",
                "title": "Compare",
                "body": "Use any method.",
                "question": "Which rate?",
            },
        ]
    )
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))

    result = bench._run_direct_attempt(
        bench.load_config(config),
        bench.load_prompt(prompt_path),
        "V3",
        tmp_path / "trace.jsonl",
    )

    assert result["status"] == "ready"
    infer_user = client.chat.completions.calls[0]["messages"][1]["content"]
    assert json.dumps(_config()["case"], ensure_ascii=False, indent=2) in infer_user
    assert json.dumps(_config()["learner_context"], ensure_ascii=False, indent=2) in infer_user


def test_production_infer_prompt_receives_case_and_learner_context(monkeypatch, tmp_path):
    client = _FakeClient(
        [
            {"misconceptions": [f"Misconception {index}" for index in range(6)]},
            {
                "status": "ready",
                "title": "Compare",
                "body": "Use any method.",
                "question": "Which rate?",
            },
        ]
    )
    monkeypatch.setattr(bench, "load_client", lambda selector: (client, "gpt-5.6-luna"))

    config = bench.load_config(bench.CONFIG_PATH)
    prompt = bench.load_prompt(bench.PROMPT_PATH)
    result = bench._run_direct_attempt(config, prompt, "V3", tmp_path / "trace.jsonl")

    assert result["status"] == "ready"
    infer_user = client.chat.completions.calls[0]["messages"][1]["content"]
    assert json.dumps(config["case"], ensure_ascii=False, indent=2) in infer_user
    assert json.dumps(config["learner_context"], ensure_ascii=False, indent=2) in infer_user


def test_started_attempt_is_not_resubmitted_and_blocked_is_explicit(tmp_path):
    config, prompt = _write_inputs(tmp_path)
    output = tmp_path / "run"
    manifest, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt)
    item = manifest["attempts"]["V1-001"]
    started = output / item["path"] / "attempt.json"
    started.write_text(json.dumps({**item, "status": "started"}), encoding="utf-8")
    resumed, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)
    pending = [
        item["attempt_id"]
        for item in resumed["attempts"].values()
        if bench._read_attempt(output / item["path"]).get("status") == "pending"
    ]
    assert "V1-001" not in pending
    assert resumed["attempts"]["V1-001"]["status"] == "interrupted"


def test_judge_client_setup_failure_is_persisted(tmp_path, monkeypatch):
    attempt_path = tmp_path / "attempt"
    attempt_path.mkdir()
    attempt = {
        "attempt_id": "V1-0001",
        "status": "ready",
        "task": {
            "status": "ready",
            "title": "A task",
            "body": "Explore the situation.",
            "question": "What could you try?",
        },
    }

    def fail_load(_selector):
        raise RuntimeError("credentials unavailable")

    monkeypatch.setattr(bench, "load_client", fail_load)
    result = bench._judge_one(
        attempt,
        attempt_path,
        _config()["learner_context"],
        {"system": "Judge this task."},
        {"transport_retries": 0},
    )

    assert result["status"] == "api_error"
    assert "credentials unavailable" in result["error"]
    assert json.loads((attempt_path / "judgment.json").read_text())["status"] == "api_error"
    assert (attempt_path / "judge_trace.jsonl").is_file()


@pytest.mark.parametrize("design_brief", [None, False, True])
def test_pipeline_worker_uses_shared_context_without_reimplementing_pipeline(
    tmp_path, monkeypatch, design_brief
):
    config, prompt_path = _write_inputs(tmp_path)
    if design_brief is not None:
        config_value = _config()
        config_value["pipeline"] = {"design_brief": design_brief}
        config.write_text(json.dumps(config_value), encoding="utf-8")
    config_value = bench.load_config(config)
    prompt = bench.load_prompt(prompt_path)
    seen = {}

    def fake_worker(case_id, case_dir, model, proposal_k, reused, **kwargs):
        seen.update(case=kwargs["case_override"], context=kwargs["shared_context"], kwargs=kwargs)
        return {
            "status": "completed",
            "model": "gpt-5.6-luna",
            "stages": {
                "D2_D3": {
                    "task": {
                        "status": "blocked",
                        "blocking_issues": ["no valid plan"],
                    }
                }
            },
        }

    monkeypatch.setattr(bench, "run_case_worker", fake_worker)
    spec = {"attempt_id": "PIPELINE-001", "condition": "PIPELINE", "number": 1}
    result = bench._run_attempt_worker(
        spec,
        str(tmp_path / "attempt"),
        config_value,
        prompt,
    )
    assert result["status"] == "blocked"
    expected_mode = design_brief is not False
    assert seen["kwargs"].get("design_brief", True) is expected_mode
    assert ("design_brief" in seen["kwargs"]) is (design_brief is False)
    frozen = bench._frozen_settings(config_value)["pipeline"]
    assert frozen["design_brief"] is expected_mode
    assert ("design_brief_settings" in frozen) is expected_mode
    assert seen["context"]["benchmark_context"]["player"] == "Stephen Curry"
    assert seen["case"]["id"] == "paper_PIPELINE-001"
    assert seen["case"]["teacher_skills"] == "unit rate"
    assert seen["context"]["teacher_context"]["taught_resources"] == [
        {
            "standard_id": "TEST.1",
            "label": "Test standard",
        }
    ]


@pytest.mark.parametrize("status", ["data_review_needed", "data_not_accepted"])
def test_pipeline_attempt_retains_unaccepted_data_status_and_reason(tmp_path, monkeypatch, status):
    config = _config()
    error = "Essential condition has no exact verification."
    data_run = {
        "status": "review_needed" if status == "data_review_needed" else "rejected",
        "accepted": False,
        "payload": {"values": {"time": 2}},
        "attempts": [{"error": error}],
        "error": error,
    }
    pipeline_result = {
        "status": status,
        "error": error,
        "model": "gpt-5.6-luna",
        "stages": {"D2_D3": {"design_data": data_run, "fill": data_run, "task": None}},
    }
    monkeypatch.setattr(bench, "run_case_worker", lambda *args, **kwargs: pipeline_result)
    spec = {"attempt_id": "PIPELINE-001", "condition": "PIPELINE", "number": 1}
    result = bench._run_attempt_worker(spec, str(tmp_path / "attempt"), config, _prompt())
    assert result["status"] == status
    assert result["error"] == error
    assert result["task"] is None
    assert result["pipeline_result"]["stages"]["D2_D3"]["design_data"] == data_run
    saved = json.loads((tmp_path / "attempt" / "attempt.json").read_text())
    assert saved == result


def test_unaccepted_data_attempts_count_as_blocked_without_fabricated_scores():
    summary = bench._condition_summary(
        "PIPELINE",
        [
            {"attempt_id": "PIPELINE-001", "status": "data_review_needed"},
            {"attempt_id": "PIPELINE-002", "status": "data_not_accepted"},
        ],
        {},
    )
    assert summary["counts"]["attempted"] == summary["counts"]["blocked"] == 2
    assert summary["counts"]["failed"] == summary["counts"]["rated"] == 0
    assert summary["completion_rate"] == 0.0
    assert all(score["n"] == 0 and score["mean"] is None for score in summary["scores"].values())


def test_judge_interruption_is_not_rated_again(tmp_path, monkeypatch):
    attempt = {
        "attempt_id": "V1-001",
        "status": "ready",
        "task": {"status": "ready", "title": "Title", "body": "Body", "question": "Question?"},
    }

    def unavailable(_selector):
        raise AssertionError("interrupted judgment must not request a client")

    monkeypatch.setattr(bench, "load_client", unavailable)
    (tmp_path / "judge_trace.jsonl").write_text('{"event":"model_call_started"}\n')
    result = bench._judge_one(attempt, tmp_path, _config()["learner_context"], _prompt(), _config())
    assert result["status"] == "interrupted"
    assert json.loads((tmp_path / "judgment.json").read_text())["status"] == "interrupted"


def test_programming_errors_are_not_transport_retries(tmp_path):
    client = _FakeClient([])
    with pytest.raises(StopIteration):
        bench._call_json(
            client,
            "luna",
            "system",
            "user",
            max_tokens=10,
            retries=2,
            trace_path=tmp_path / "trace.jsonl",
            stage="test",
        )
    assert len(client.chat.completions.calls) == 1
    assert bench._bootstrap_difference_interval([5], [6], seed=1) is None


def test_resume_rejects_runtime_prompt_change(tmp_path, monkeypatch):
    config, prompt = _write_inputs(tmp_path)
    dependency = tmp_path / "runtime_prompt.yaml"
    dependency.write_text("before")
    tracked = bench._tracked_files(config, prompt) + [dependency]
    monkeypatch.setattr(bench, "_tracked_files", lambda *_args: tracked)
    output = tmp_path / "run"
    bench.prepare_run(output, config_path=config, prompt_path=prompt)
    dependency.write_text("after")
    with pytest.raises(ValueError, match="Frozen source_hashes"):
        bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)


def test_summary_preserves_denominators_and_partial_usage(tmp_path):
    trace = tmp_path / "model_trace.jsonl"
    trace.write_text(
        '{"event":"model_call_started"}\n'
        '{"event":"model_call_finished","usage":{"total_tokens":30}}\n'
        '{"event":"model_call_started"}\n'
        '{"event":"model_call_finished"}\n'
        '{"partial"\n'
    )
    stats = bench._trace_stats(trace)
    assert stats["calls_with_usage"] == 1
    assert stats["malformed_lines"] == 1
    summary = bench._condition_summary(
        "V1",
        [
            {"attempt_id": "V1-001", "status": "ready", "_absolute_path": str(tmp_path)},
            {"attempt_id": "V1-002", "status": "interrupted"},
            {"attempt_id": "V1-003", "status": "pending"},
        ],
        {},
    )
    assert summary["counts"]["attempted"] == 2
    assert summary["counts"]["ready_without_complete_rating"] == 1
    assert summary["completion_rate"] == 1 / 3


@pytest.mark.parametrize("invalid", [None, 0, 1, "false", [], {}])
def test_config_design_brief_requires_actual_boolean(tmp_path, invalid):
    config, _ = _write_inputs(tmp_path)
    value = _config()
    value["pipeline"] = {"design_brief": invalid}
    config.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match=r"pipeline\.design_brief must be a boolean"):
        bench.load_config(config)


@pytest.mark.parametrize("design_brief", [None, True, False])
def test_design_brief_mode_and_budgets_are_frozen_and_resume_cannot_change_them(
    tmp_path, design_brief
):
    config, prompt = _write_inputs(tmp_path)
    value = _config()
    if design_brief is not None:
        value["pipeline"] = {"design_brief": design_brief}
    config.write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "run"
    manifest, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt)
    pipeline = manifest["frozen_settings"]["pipeline"]
    expected_mode = design_brief is not False
    assert pipeline["design_brief"] is expected_mode
    assert ("design_brief_settings" in pipeline) is expected_mode
    if expected_mode:
        from scripts.design_data_stage import MAX_CALLS, MAX_TOKENS

        assert pipeline["design_brief_settings"]["max_tokens"] == 6000
        assert (
            not {"translation_temperature", "translation_retry_max"}
            & pipeline["design_brief_settings"].keys()
        )
        assert pipeline["design_data_settings"] == {
            "max_calls": MAX_CALLS,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
        }
        assert not {"plan_retry_max", "fill_max_tries", "fill_temperature"} & pipeline.keys()
    else:
        assert pipeline["plan_retry_max"] == bench.d2_settings.PLAN_RETRY_MAX
        assert pipeline["fill_max_tries"] == bench.d2_settings.FILL_MAX_TRIES
        assert "design_data_settings" not in pipeline
    resumed, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)
    assert resumed["frozen_settings"] == manifest["frozen_settings"]
    value.setdefault("pipeline", {})["design_brief"] = not expected_mode
    config.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen config_sha256"):
        bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)


def test_resume_rejects_changed_frozen_design_brief_mode(tmp_path):
    config, prompt = _write_inputs(tmp_path)
    output = tmp_path / "run"
    manifest, _, _ = bench.prepare_run(output, config_path=config, prompt_path=prompt)
    manifest["frozen_settings"]["pipeline"]["design_brief"] = False
    bench._write_json(output / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Frozen frozen_settings"):
        bench.prepare_run(output, config_path=config, prompt_path=prompt, resume=True)
