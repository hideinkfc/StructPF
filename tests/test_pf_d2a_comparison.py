import json
import shutil
import uuid
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_pf_d2a_comparison as comparison
from tests.test_design_briefs import selection_payload
from tests.test_design_data import loop_inputs, proposal_payload, writer_payload


@pytest.fixture
def work():
    directory = comparison.ROOT / ".pytest-d2a" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)
        if directory.parent.exists() and not any(directory.parent.iterdir()):
            directory.parent.rmdir()


def inputs(
    work,
    monkeypatch,
    *,
    ids=("area_perimeter", "weighted_mean"),
    repeats=3,
    total=468,
    per_attempt=9,
):
    case, winner, context = loop_inputs()
    case.update(topic="journeys", subject="mathematics")
    sources = work / "sources"
    for case_id in ids:
        source = sources / case_id / "result.json"
        source.parent.mkdir(parents=True)
        source.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "case_input": {**case, "id": case_id},
                    "model": "gpt-5.6-luna",
                    "prior_context": {**context, "case_id": case_id},
                    "stages": {
                        "D1": {"must_never_be_called": True},
                        "D2_D3": {
                            "winner": winner.to_dict(),
                            "task": writer_payload(),
                        },
                    },
                }
            )
        )
    baseline = work / "old_prompts.yaml"
    baseline.write_bytes(comparison.brief_stage.PROMPTS_PATH.read_bytes())
    config = {
        "schema_version": "pf-d2a-comparison/v1",
        "model_selector": "luna",
        "source_directory": str(sources),
        "baseline_prompts": str(baseline),
        "cases": [{"id": case_id} for case_id in ids],
        "proposal_k": 2,
        "repeats": repeats,
        "calibration_cases": list(ids[:2]),
        "protocol": {
            "max_calls_per_attempt": per_attempt,
            "max_calls_total": total,
            "max_completion_tokens_per_call": 6000,
            "sdk_max_retries": 0,
        },
    }
    path = work / "config.json"
    path.write_text(json.dumps(config))
    tracked = work / "implementation.py"
    tracked.write_text("VERSION = 1\n")
    monkeypatch.setattr(
        comparison,
        "source_hashes",
        lambda config_path, baseline_path: {
            str(path): comparison._sha(path) for path in (config_path, baseline_path, tracked)
        },
    )
    return path, work / "output", config, tracked


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.options = []
        self.before_create = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **kwargs):
        self.options.append(kwargs)
        return self

    def create(self, **kwargs):
        if self.before_create:
            self.before_create(kwargs)
        self.requests.append(kwargs)
        payload = next(self.responses)
        if isinstance(payload, BaseException):
            raise payload
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=20,
                completion_tokens_details=SimpleNamespace(reasoning_tokens=5),
            ),
        )


def fake_pipeline(monkeypatch, *, winner=True):
    _, selected, _ = loop_inputs()
    seen = []

    def search(client, model, case_input, prior_context, **kwargs):
        seen.append({"case": deepcopy(case_input), "context": deepcopy(prior_context), **kwargs})
        for _ in range(2):
            comparison.runner.chat_json(
                client, model, "Design one mathematical challenge", "Proposal input", 0.9, 10000
            )
        comparison.runner.chat_json(
            client,
            model,
            "Select one promising mathematical design brief",
            "Selection input",
            0.0,
            6000,
        )
        return {
            "winners": [selected] if winner else [],
            "judged": [selected] if winner else [],
            "proposals": [{"brief": selected.design_brief.to_dict()}],
            "judge_error": None,
            "brief_selection": {"selected_brief": selected.design_brief.to_dict()},
        }

    monkeypatch.setattr(comparison.brief_stage, "run_design_brief_search", search)
    return seen


def response_set():
    return [{}, {}, {}, proposal_payload(), writer_payload()]


def install_client(monkeypatch, client):
    monkeypatch.setattr(comparison, "load_client", lambda selector: (client, "gpt-5.6-luna"))


def record_for(output, attempt):
    return json.loads((output / "attempts" / attempt["attempt_id"] / "result.json").read_text())


def test_prepare_freezes_case_context_prompts_and_model_without_client(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    monkeypatch.setattr(comparison, "load_client", lambda *_: pytest.fail("Prepare loaded client"))
    manifest = comparison.prepare(config, output)
    assert comparison.prepare(config, output) == manifest
    assert manifest["model"] == "gpt-5.6-luna"
    assert manifest["inputs"]["area_perimeter"]["prior_context"]["recommendations"] == [
        {"resource": "Arithmetic"}
    ]
    assert (output / manifest["baseline_prompts_snapshot"]).read_bytes() == (
        work / "old_prompts.yaml"
    ).read_bytes()
    assert all((output / value).exists() for value in manifest["snapshots"].values())
    assert not (output / "ledger.jsonl").exists()


def test_prepare_preserves_precreated_baseline_and_refuses_other_existing_outputs(
    work, monkeypatch
):
    config, output, values, _ = inputs(work, monkeypatch)
    output.mkdir()
    baseline = output / "baseline_design_briefs.yaml"
    baseline.write_bytes(Path(values["baseline_prompts"]).read_bytes())
    original = baseline.read_bytes()
    values["baseline_prompts"] = str(baseline)
    config.write_text(json.dumps(values))
    comparison.prepare(config, output)
    assert baseline.read_bytes() == original
    other = work / "unknown-output"
    other.mkdir()
    (other / "untracked.txt").write_text("Do not overwrite")
    with pytest.raises(ValueError, match="unmanifested"):
        comparison.prepare(config, other)
    assert (other / "untracked.txt").read_text() == "Do not overwrite"


def test_production_source_hashes_include_transitive_math_and_all_stage_prompts(work):
    config = work / "config.json"
    config.write_text("{}")
    baseline = work / "baseline.yaml"
    baseline.write_text("baseline snapshot")
    hashes = comparison.source_hashes(config, baseline)
    expected = (
        "scripts/run_pf_d2a_comparison.py",
        "scripts/prior_methods/common.py",
        "scripts/run_situation_skeletons.py",
        "scripts/design_brief_stage.py",
        "scripts/design_data_stage.py",
        "src/generation/design_briefs.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/fill_check.py",
        "src/generation/situation_skeletons.py",
        "src/generation/prompts/design_briefs.yaml",
        "src/generation/prompts/design_data.yaml",
        "src/generation/prompts/situation_skeletons.yaml",
    )
    assert all(str(comparison.ROOT / path) in hashes for path in expected)
    assert hashes[str(baseline)] == comparison._sha(baseline)
    assert not any(".env" in path for path in hashes)


def test_prepare_refuses_missing_d1_without_starting_any_attempt(work, monkeypatch):
    config, output, values, _ = inputs(work, monkeypatch)
    source = Path(values["source_directory"]) / "area_perimeter" / "result.json"
    saved = json.loads(source.read_text())
    del saved["prior_context"]
    source.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="D1 prior_context"):
        comparison.prepare(config, output)
    assert not output.exists()


@pytest.mark.parametrize("changed", ["source", "implementation", "baseline", "config", "snapshot"])
def test_prepare_refuses_changed_frozen_material(work, monkeypatch, changed):
    config, output, values, tracked = inputs(work, monkeypatch)
    manifest = comparison.prepare(config, output)
    paths = {
        "source": Path(values["source_directory"]) / "area_perimeter" / "result.json",
        "implementation": tracked,
        "baseline": Path(values["baseline_prompts"]),
        "config": config,
        "snapshot": output / next(iter(manifest["snapshots"].values())),
    }
    path = paths[changed]
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="changed"):
        comparison.prepare(config, output)


def test_schedule_is_frozen_paired_and_calibration_is_separate(work, monkeypatch):
    ids = ("area_perimeter", "weighted_mean", "a", "b", "c", "d", "e", "f")
    config, output, values, _ = inputs(work, monkeypatch, ids=ids)
    schedule = comparison.prepare(config, output)["schedule"]
    assert schedule == comparison.make_schedule(values)
    calibration = [item for item in schedule if item["phase"] == "calibration"]
    development = [item for item in schedule if item["phase"] == "development"]
    assert len(calibration) == 4 and len(development) == 48
    assert set(item["repeat"] for item in calibration) == {1}
    assert set(item["case_id"] for item in calibration) == set(values["calibration_cases"])
    assert len({item["attempt_id"] for item in schedule}) == 52
    for first, second in zip(schedule[::2], schedule[1::2]):
        assert first["case_id"] == second["case_id"]
        assert first["repeat"] == second["repeat"]
        assert {first["arm"], second["arm"]} == set(comparison.ARMS)


def test_same_frozen_d1_and_correct_arm_schema_paths_and_overrides(work, monkeypatch):
    config, output, values, _ = inputs(work, monkeypatch)
    seen = fake_pipeline(monkeypatch)
    client = FakeClient(response_set() * 2)
    install_client(monkeypatch, client)

    def check_started(kwargs):
        ledger = comparison._rows(output / "ledger.jsonl")
        assert ledger[-1]["event"] == "api_request_started"
        assert ledger[-1]["attempted_count_total"] == len(client.requests) + 1
        assert kwargs["timeout"] == 120
        assert kwargs["max_completion_tokens"] <= 6000

    client.before_create = check_started
    manifest = comparison.run(config, output, "calibration", limit=2)
    assert len(client.requests) == 10
    assert client.options == [{"max_retries": 0, "timeout": 120}]
    assert len(seen) == 2
    by_schema = {item["brief_schema_version"]: item for item in seen}
    assert by_schema["design-brief/v1"]["prompts_path"] == Path(values["baseline_prompts"])
    assert by_schema["design-brief/v2"]["prompts_path"] is None
    assert seen[0]["case"] == seen[1]["case"]
    assert seen[0]["context"] == seen[1]["context"]
    assert all(item["k"] == 2 and item["translate"] is False for item in seen)
    assert manifest["usage"]["attempted_calls"] == 10
    assert manifest["usage"]["input_tokens"] == 100
    assert manifest["usage"]["output_tokens"] == 200
    assert manifest["usage"]["reasoning_tokens"] == 50
    assert manifest["phase_usage"]["development"]["attempted_calls"] == 0
    for item in manifest["schedule"][:2]:
        record = record_for(output, item)
        assert record["status"] == "ready" and record["d1_reused"]
        assert record["writer_request"]["user"]
        assert "judged" not in record["search"] and "winners" not in record["search"]
        assert record["case_input"] == manifest["inputs"][item["case_id"]]["case_input"]
        assert record["prior_context"] == manifest["inputs"][item["case_id"]]["prior_context"]
        requests = [row for row in record["traces"] if row["event"] == "api_request_started"]
        assert {row["module"] for row in requests} == {"D2a", "D2b", "D3"}
        assert requests[0]["requested_settings"]["max_tokens"] == 10000
        assert requests[0]["runtime_overrides"]["max_tokens"] == 6000
        assert requests[0]["effective_settings"]["max_completion_tokens"] == 6000
        assert len([row for row in record["traces"] if row["event"] == "stage_response"]) == 5


@pytest.mark.parametrize(("total", "per_attempt"), [(0, 9), (468, 0)])
def test_budget_exhaustion_is_persisted_before_any_dispatch(work, monkeypatch, total, per_attempt):
    config, output, _, _ = inputs(work, monkeypatch, total=total, per_attempt=per_attempt)
    fake_pipeline(monkeypatch)
    client = FakeClient([])
    monkeypatch.setattr(
        comparison, "load_client", lambda *_: pytest.fail("Exhausted budget loaded API client")
    )
    manifest = comparison.run(config, output, "calibration", limit=1)
    record = record_for(output, manifest["schedule"][0])
    assert client.requests == []
    assert record["status"] == "budget_stopped"
    assert record["task"] is None
    assert record["usage"]["attempted_calls"] == 0
    assert record["traces"][-1]["event"] == "budget_stopped"


def test_global_budget_counts_across_resumed_invocations(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch, total=6)
    fake_pipeline(monkeypatch)
    client = FakeClient(response_set() + [{}])
    install_client(monkeypatch, client)
    first = comparison.run(config, output, "calibration", limit=1)
    assert record_for(output, first["schedule"][0])["status"] == "ready"
    manifest = comparison.run(config, output, "calibration", limit=2)
    assert len(client.requests) == 6
    assert manifest["usage"]["attempted_calls"] == 6
    assert record_for(output, manifest["schedule"][1])["status"] == "budget_stopped"
    assert record_for(output, manifest["schedule"][2])["status"] == "budget_stopped"
    assert manifest["phase_usage"]["calibration"]["attempted_calls"] == 6


def test_attempt_cap_nine_including_failed_requests(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    manifest = comparison.prepare(config, output)
    budget = comparison.RequestBudget(output, manifest["limits"])
    attempt = manifest["schedule"][0]
    client = FakeClient([RuntimeError("Synthetic failure")] + [{}] * 8)

    def check_durable_start(kwargs):
        rows = comparison._rows(output / "ledger.jsonl")
        assert rows[-1]["event"] == "api_request_started"
        assert rows[-1]["attempted_count_total"] == len(client.requests) + 1
        assert kwargs["timeout"] == 120
        assert kwargs["max_completion_tokens"] == 6000

    client.before_create = check_durable_start
    chat = budget.traced_chat(client, attempt, output / "requests.jsonl", "D2a")
    with pytest.raises(RuntimeError, match="Synthetic failure"):
        chat(client, manifest["model"], "System", "User", 0.0, 6000)
    for _ in range(8):
        chat(client, manifest["model"], "System", "User", 0.0, 6000)
    with pytest.raises(comparison.BudgetStoppedError, match="max_calls_per_attempt"):
        chat(client, manifest["model"], "System", "User", 0.0, 6000)
    assert len(client.requests) == 9
    assert comparison.usage_summary(budget.rows)["attempted_calls"] == 9
    assert comparison.usage_summary(budget.rows)["error_calls"] == 1


def test_dispatch_disables_sdk_retries_and_overrides_common_timeout(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    manifest = comparison.prepare(config, output)
    limits = {**manifest["limits"], "timeout_seconds": 75}
    budget = comparison.RequestBudget(output, limits)
    client = FakeClient([{}])
    client.max_retries = 2
    chat = budget.traced_chat(client, manifest["schedule"][0], output / "requests.jsonl", "D2a")
    chat(client, manifest["model"], "System", "User", 0.9, 9000)
    assert client.options == [{"max_retries": 0}]
    assert client.requests[0]["timeout"] == 75
    assert client.requests[0]["max_completion_tokens"] == 6000
    assert "temperature" not in client.requests[0]
    assert budget.rows[0]["requested_settings"]["max_tokens"] == 9000
    assert budget.rows[0]["runtime_overrides"]["timeout_seconds"] == 75
    assert budget.rows[0]["effective_settings"]["timeout"] == 75
    usage = comparison.usage_summary(budget.rows)
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 20
    assert usage["reasoning_tokens"] == 5


def test_api_failure_persists_and_propagates_then_resume_does_not_replace(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch)
    client = FakeClient([RuntimeError("Synthetic API failure")] + response_set())
    install_client(monkeypatch, client)
    with pytest.raises(RuntimeError, match="Synthetic API failure"):
        comparison.run(config, output, "calibration", limit=1)
    manifest = json.loads((output / "manifest.json").read_text())
    failed_path = output / "attempts" / manifest["schedule"][0]["attempt_id"] / "result.json"
    original = failed_path.read_bytes()
    record = json.loads(original)
    assert record["status"] == "error"
    assert record["error"] == "RuntimeError: Synthetic API failure"
    assert record["usage"]["attempted_calls"] == 1 and record["usage"]["error_calls"] == 1
    assert record["usage"]["input_tokens"] is None
    assert manifest["attempts"][record["attempt_id"]]["status"] == "error"
    assert not (output / ".run-lock").exists()
    comparison.run(config, output, "calibration", limit=1)
    assert failed_path.read_bytes() == original
    assert len(client.requests) == 6


def test_failed_writer_keeps_search_data_request_and_completed_payloads(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch)
    client = FakeClient(response_set()[:-1] + [RuntimeError("Writer API failed")])
    install_client(monkeypatch, client)
    with pytest.raises(RuntimeError, match="Writer API failed"):
        comparison.run(config, output, "calibration", limit=1)
    manifest = json.loads((output / "manifest.json").read_text())
    record = record_for(output, manifest["schedule"][0])
    assert record["status"] == "error" and record["task"] is None
    assert record["search"] and record["winner"] and record["design_data"]["accepted"]
    assert record["writer_request"]["system"]
    assert record["usage"]["attempted_calls"] == 5
    assert record["usage"]["error_calls"] == 1
    assert len([row for row in record["traces"] if row["event"] == "stage_response"]) == 4


def test_resolved_model_mismatch_is_refused_before_dispatch(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    client = FakeClient([])
    monkeypatch.setattr(comparison, "load_client", lambda _: (client, "wrong-model"))
    with pytest.raises(ValueError, match="frozen model"):
        comparison.run(config, output, "calibration", limit=1)
    assert not client.requests
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["attempts"] == {} and manifest["usage"]["attempted_calls"] == 0


def test_keyboard_interrupt_is_recorded_and_cannot_be_replaced(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch)
    client = FakeClient([KeyboardInterrupt()])
    install_client(monkeypatch, client)
    with pytest.raises(KeyboardInterrupt):
        comparison.run(config, output, "calibration", limit=1)
    manifest = json.loads((output / "manifest.json").read_text())
    record = record_for(output, manifest["schedule"][0])
    assert record["status"] == "interrupted"
    assert record["usage"]["attempted_calls"] == record["usage"]["completed_calls"] == 1
    with pytest.raises(ValueError, match="running/interrupted"):
        comparison.run(config, output, "calibration", limit=1)
    assert len(client.requests) == 1


@pytest.mark.parametrize("selected", [False, True])
def test_no_selected_brief_or_invalid_data_never_falls_back_to_historical_task(
    work, monkeypatch, selected
):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch, winner=selected)
    client = FakeClient([{}] * (6 if selected else 3))
    install_client(monkeypatch, client)
    manifest = comparison.run(config, output, "calibration", limit=1)
    record = record_for(output, manifest["schedule"][0])
    assert record["status"] == ("data_invalid" if selected else "brief_not_selected")
    assert record["task"] is None and record["writer_request"] is None
    assert record["usage"]["attempted_calls"] == (6 if selected else 3)


def test_data_repair_exhaustion_produces_flagged_task_and_records_all_calls(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch)
    data = proposal_payload()
    data["values"]["minutes"][0] = -20
    client = FakeClient(
        [
            {},
            {},
            {},
            data,
            {"values": data["values"]},
            {"values": data["values"]},
            writer_payload(),
        ]
    )
    install_client(monkeypatch, client)
    manifest = comparison.run(config, output, "calibration", limit=1)
    record = record_for(output, manifest["schedule"][0])
    assert record["status"] == "ready"
    assert record["design_data"]["accepted"] is False
    assert record["design_data"]["proceed"] is True
    assert record["task"]["quality_status"] == "review_needed"
    assert record["task"]["quality_findings"] == ["All section times are positive."]
    assert record["usage"]["attempted_calls"] == 7


@pytest.mark.parametrize("status", ["running", "interrupted"])
def test_resume_refuses_unfinished_attempts(work, monkeypatch, status):
    config, output, _, _ = inputs(work, monkeypatch)
    manifest = comparison.prepare(config, output)
    path = output / "attempts" / manifest["schedule"][0]["attempt_id"] / "result.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"status": status, "finished_at": "not a recovery authorization"}))
    original = path.read_bytes()
    monkeypatch.setattr(comparison, "load_client", lambda *_: pytest.fail("Client loaded"))
    with pytest.raises(ValueError, match="running/interrupted"):
        comparison.run(config, output, "calibration")
    assert path.read_bytes() == original


def test_unpaired_started_ledger_refuses_new_dispatch(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    manifest = comparison.prepare(config, output)
    comparison._append(
        output / "ledger.jsonl",
        {
            **manifest["schedule"][0],
            "event": "api_request_started",
            "call_id": "request-000001",
        },
    )
    monkeypatch.setattr(comparison, "load_client", lambda *_: pytest.fail("Client loaded"))
    with pytest.raises(ValueError, match="Interrupted API requests"):
        comparison.run(config, output, "calibration")


def test_anonymized_gallery_has_supplied_target_and_task_text_only(work, monkeypatch):
    config, output, _, _ = inputs(work, monkeypatch)
    fake_pipeline(monkeypatch)
    client = FakeClient(response_set())
    install_client(monkeypatch, client)
    manifest = comparison.run(config, output, "calibration", limit=1)
    path = output / "attempts" / manifest["schedule"][0]["attempt_id"] / "result.json"
    record = json.loads(path.read_text())
    record["task"].update(
        model="must not show",
        arm="must not show",
        target_concept="generated target must not show",
        key_idea="hidden key idea",
        naive_answer="hidden naive answer",
        predicted_routes=["hidden route"],
        schema_version="hidden version",
        withheld=[{"source": "brief.secret", "quote": "do not show"}],
    )
    record["case_input"]["target_concept"] = "artifact target must not show"
    path.write_text(json.dumps(record))
    comparison.render(output, "calibration")
    gallery = output / "gallery" / "calibration"
    review_bytes = (gallery / "review.json").read_bytes()
    review = json.loads(review_bytes)
    assert len(review["tasks"]) == 4
    assert len([item for item in review["tasks"] if item["task"] is None]) == 3
    assert all(set(item) == {"task_id", "target_concept", "task"} for item in review["tasks"])
    assert all(
        item["target_concept"]
        == manifest["inputs"][manifest["schedule"][0]["case_id"]]["case_input"]["target_concept"]
        for item in review["tasks"]
    )
    present = next(item["task"] for item in review["tasks"] if item["task"] is not None)
    assert set(present) == {"title", "body", "question"}
    page = (gallery / "tasks.html").read_text()
    target = manifest["inputs"][manifest["schedule"][0]["case_id"]]["case_input"]["target_concept"]
    assert target in page
    for forbidden in (
        "baseline",
        "intervention",
        "gpt-5.6-luna",
        "brief.secret",
        "must not show",
        "hidden key idea",
        "hidden naive answer",
        "hidden route",
        "hidden version",
        "key_idea",
        "naive_answer",
        "predicted_routes",
        "result.json",
        "file://",
        "href=",
        "blind review",
    ):
        assert forbidden not in review_bytes.decode()
        assert forbidden not in page
    mapping = json.loads((output / "calibration_task_mapping.json").read_text())
    assert len(mapping["tasks"]) == 4
    assert all("arm" in item and "model" in item for item in mapping["tasks"])
    comparison.render(output, "calibration")
    assert (gallery / "review.json").read_bytes() == review_bytes
    comparison.render(output, "development")
    assert (gallery / "review.json").read_bytes() == review_bytes
    development = json.loads((output / "gallery" / "development" / "review.json").read_text())
    assert len(development["tasks"]) == 12
    assert not {item["task_id"] for item in review["tasks"]} & {
        item["task_id"] for item in development["tasks"]
    }


@pytest.mark.parametrize("arm", comparison.ARMS)
def test_actual_pipeline_uses_extended_api_and_never_generates_d1(work, monkeypatch, arm):
    config, output, _, _ = inputs(work, monkeypatch, ids=("area_perimeter",))
    manifest = comparison.prepare(config, output)
    attempt = next(item for item in manifest["schedule"] if item["arm"] == arm)
    payload = loop_inputs()[1].design_brief.to_dict()
    version = "design-brief/v1" if arm == "baseline" else "design-brief/v2"
    if arm == "intervention":
        payload.update(
            schema_version=version,
            key_idea="Whole-journey weighting",
            naive_answer="Compare sections without their durations",
        )
    client = FakeClient(
        [
            payload,
            payload,
            selection_payload(),
            proposal_payload(),
            writer_payload(),
        ]
    )
    budget = comparison.RequestBudget(output, manifest["limits"])
    record = comparison.run_attempt(
        attempt, output, manifest, client=client, model=manifest["model"], budget=budget
    )
    assert record["status"] == "ready"
    assert record["usage"]["attempted_calls"] == 5
    assert record["winner"]["design_brief"]["schema_version"] == version
    if arm == "baseline":
        assert "key_idea" not in record["winner"]["design_brief"]
        assert "naive_answer" not in record["winner"]["design_brief"]
        assert "design_brief.key_idea" not in record["writer_request"]["user"]
        assert "design_brief.naive_answer" not in record["writer_request"]["user"]
    else:
        assert record["winner"]["design_brief"]["key_idea"] == payload["key_idea"]
        assert record["winner"]["design_brief"]["naive_answer"] == payload["naive_answer"]
        assert "design_brief.key_idea" in record["writer_request"]["user"]
        assert "design_brief.naive_answer" in record["writer_request"]["user"]
    assert all(row.get("module") != "D1" for row in record["traces"])
