"""Offline integration tests for the PF diagnostic benchmark harness."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import scripts.replay_pf_writer as replay
import scripts.run_pf_diagnostic as diag
import scripts.run_prior_recommendations as d1
import scripts.run_situation_skeletons as d2
from scripts.learning_commons_context import retrieve_context
from src.generation.design_briefs import design_brief_from_payload
from src.generation.situation_skeletons import skeleton_from_payload


def test_effective_settings_for_model_families():
    requested = {"temperature": 0.7, "max_tokens": 4000}
    assert diag._determine_effective_settings("gpt-5.6-luna", requested) == {
        "max_completion_tokens": 4000
    }
    assert diag._determine_effective_settings("gpt-4o", requested) == requested


def test_tracer_records_pair_return_and_exact_stages(tmp_path: Path):
    trace = tmp_path / "calls.jsonl"
    tracer = diag.DiagnosticTracer(trace, "case", "fake-model")
    payload, raw = tracer.log_call(
        "run_situation_skeletons",
        "D2.proposal",
        "fake-model",
        {},
        "Design one grade-level situation.",
        "user",
        lambda: ({"ok": True}, '{"ok": true}'),
    )
    assert payload == {"ok": True}
    assert raw == '{"ok": true}'
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "model_call_started",
        "model_call_finished",
    ]
    assert records[0]["stage"] == "D2.proposal"
    assert records[1]["payload"] == {"ok": True}
    assert records[0]["call_id"] == records[1]["call_id"]
    assert diag.trace_summary(trace) == {
        "started": 1,
        "finished": 1,
        "errors": 0,
        "call_ids": [records[0]["call_id"]],
    }


def test_tracer_persists_api_failure(tmp_path: Path):
    trace = tmp_path / "calls.jsonl"
    tracer = diag.DiagnosticTracer(trace, "case", "fake-model")
    with pytest.raises(RuntimeError, match="offline failure"):
        tracer.log_call(
            "run_situation_skeletons",
            "D2.plan",
            "fake-model",
            {},
            "Freeze the mathematical plan.",
            "user",
            lambda: (_ for _ in ()).throw(RuntimeError("offline failure")),
        )
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert records[-1]["error"] == "RuntimeError: offline failure"


def test_source_hashes_include_relevant_contract_files():
    hashes = diag.compute_source_hashes()
    assert "src/generation/fill_check.py" in hashes
    assert "src/generation/prompts/prior_recommendations.yaml" in hashes
    assert "scripts/recheck_pf_joint_repair.py" in hashes
    assert {
        "scripts/design_brief_stage.py",
        "src/generation/design_briefs.py",
        "src/generation/prompts/design_briefs.yaml",
        "scripts/design_data_stage.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/prompts/design_data.yaml",
    } <= hashes.keys()
    assert all(".env" not in path for path in hashes)


class _OfflineClient:
    def with_options(self, **kwargs):
        assert kwargs == {"max_retries": 0}
        return self


def _offline_chat(_client, _model, system, _user, temperature, max_tokens, *, failure=None):
    del temperature, max_tokens
    first = system.strip().splitlines()[0]
    if first.startswith(("You map curriculum", "You list prior resources")):
        return (
            {
                "resources": [
                    {
                        "resource": "Ratio",
                        "taught_as": "Compare quantities multiplicatively.",
                        "relevance": "The quantities invite comparison.",
                        "evidence_ids": ["curriculum:c1"],
                        "confidence": "high",
                    }
                ]
            },
            "mapping",
        )
    if first.startswith("You add two short notes"):
        return (
            {
                "kind": "builds_on",
                "student_move": "Compare the quantities.",
                "falls_short_because": "The target asks for a rate.",
            },
            "expansion",
        )
    if first.startswith("Design one grade-level"):
        return (
            {
                "quantities": [
                    {
                        "name": "distance",
                        "role": "amount",
                        "description": "a positive distance",
                        "value_source": "given",
                        "unit": "km",
                        "value_domain": "positive",
                    },
                    {
                        "name": "time",
                        "role": "amount",
                        "description": "a positive time",
                        "value_source": "given",
                        "unit": "h",
                        "value_domain": "positive",
                    },
                ],
                "question": "Which journey has the greater rate, and why?",
                "number_constraints": [],
                "approaches": [
                    {
                        "id": "approach_0",
                        "resources": ["Ratio"],
                        "procedure": "Compare distance per unit time.",
                        "why_plausible": "Both quantities are available.",
                    }
                ],
            },
            "proposal",
        )
    if first.startswith("You are selecting"):
        return (
            {
                "recommended_id": 0,
                "approaches": ["approach_0"],
                "reason": "The approach supports the question.",
                "main_concern": None,
                "prior_contrast": None,
                "number_requirements": [],
            },
            "selection",
        )
    if first.startswith("Freeze the mathematical"):
        if failure == "structure":
            return ({"schema_version": "math-plan/v2"}, "invalid structure")
        if failure == "expression":
            return (
                {
                    "schema_version": "math-plan/v2",
                    "target": {
                        "name": "target",
                        "unit": "km/h",
                        "expressions": {"rate": "distance / missing_quantity"},
                    },
                    "answer_rule": {
                        "kind": "scalar",
                        "labels": ["rate"],
                        "unit": "km/h",
                        "require_unique": True,
                    },
                    "constraints": [],
                },
                "invalid expression",
            )
        return (
            {
                "schema_version": "math-plan/v2",
                "target": {
                    "name": "target",
                    "unit": "km/h",
                    "expressions": {"rate": "distance / time"},
                },
                "answer_rule": {
                    "kind": "scalar",
                    "labels": ["rate"],
                    "unit": "km/h",
                    "require_unique": True,
                },
                "constraints": [],
            },
            "plan",
        )
    if first.startswith("Review whether"):
        if failure == "meaning_review":
            return (
                {
                    "status": "unknown",
                    "distinct_approaches": False,
                    "constraints_covered": False,
                    "issues": ["review rejected offline"],
                },
                "review failure",
            )
        return (
            {
                "status": "pass",
                "question_answer_alignment": True,
                "approach_formula_alignment": True,
                "distinct_approaches": True,
                "constraints_covered": True,
                "requirement_coverage": [],
                "issues": [],
            },
            "review",
        )
    if first.startswith("Fill values"):
        return ({"values": {"distance": 10, "time": 2}}, "fill")
    if first.startswith("Write the student-facing"):
        if failure == "writer_blocked":
            return (
                {
                    "status": "blocked",
                    "blocking_issues": ["writer found an issue"],
                },
                "blocked writer",
            )
        if failure == "writer_none":
            return None, "missing writer payload"
        return (
            {
                "status": "ready",
                "blocking_issues": [],
                "title": "Compare journeys",
                "body": "Compare the journeys and explain your method.",
                "question": "Which rate is greater?",
            },
            "writer",
        )
    raise AssertionError(f"unexpected prompt stage: {first}")


def _offline_chat_factory(failure=None):
    def chat(client, model, system, user, temperature, max_tokens):
        return _offline_chat(
            client,
            model,
            system,
            user,
            temperature,
            max_tokens,
            failure=failure,
        )

    return chat


def _prepare_worker(monkeypatch, failure=None):
    case = {
        "id": "case_speed",
        "target_concept": "average speed",
        "topic": "speed",
        "grade": 7,
        "subject": "mathematics",
        "jurisdiction": "test",
        "exercise_ids": [],
    }
    monkeypatch.setattr(diag, "_load_d1_cases", lambda: [case])
    monkeypatch.setattr(diag, "load_client", lambda selector: (_OfflineClient(), "fake-model"))
    monkeypatch.setattr(diag, "chat_json", _offline_chat_factory(failure))
    monkeypatch.setattr(
        d1,
        "retrieve_chunks",
        lambda *args, **kwargs: [
            {
                "doc": "doc",
                "page": 1,
                "language": "en",
                "chunk_id": "c1",
                "doc_title": "Math",
                "jurisdiction": "test",
                "source_url": None,
                "text": "Compare quantities.",
            }
        ],
    )
    return case


@pytest.mark.parametrize("condition", ["grounded", "ungrounded"])
def test_worker_runs_saved_shape_and_real_production_gates(tmp_path: Path, monkeypatch, condition):
    _prepare_worker(monkeypatch)
    monkeypatch.setitem(
        sys.modules,
        "scripts.design_brief_stage",
        SimpleNamespace(
            run_design_brief_search=lambda *args, **kwargs: pytest.fail(
                "baseline must not use design brief search"
            )
        ),
    )
    case_dir = tmp_path / "case_speed"
    summary = diag.run_case_worker(
        "case_speed", str(case_dir), "luna", 1, d1_condition=condition, design_brief=False
    )
    assert summary["status"] == "completed"
    assert json.loads((case_dir / "d1.json").read_text())["records"][0]["condition"] == condition
    saved = json.loads((case_dir / "result.json").read_text())
    d2_stage = saved["stages"]["D2_D3"]
    assert (
        not {
            "design_brief",
            "brief_selection",
            "translation",
            "design_brief_source_hashes",
            "design_brief_prompt_snapshot",
        }
        & d2_stage.keys()
    )
    assert d2_stage["winners"][0]["skeleton"]["question"].startswith("Which")
    assert d2_stage["math_plan"]["schema_version"] == "math-plan/v2"
    assert d2_stage["plan_review"]["status"] == "pass"
    assert d2_stage["fill"]["accepted"] is True
    assert d2_stage["task"]["status"] == "ready"
    assert saved["prior_context"]["source"] == "d1_recommendations"
    loaded_winner = d2._winner_from_result(case_dir / "result.json", "case_speed")
    assert loaded_winner.skeleton.question.startswith("Which")
    trace = [json.loads(line) for line in (case_dir / "model_calls.jsonl").read_text().splitlines()]
    assert saved["trace_counts"]["started"] == saved["trace_counts"]["finished"]
    assert saved["trace_counts"]["errors"] == 0
    assert saved["model_call_count"] == saved["trace_counts"]["finished"]
    stage_call_ids = {
        record["call_id"] for record in trace if record["event"] == "model_call_started"
    }
    assert stage_call_ids == {
        record["call_id"] for record in trace if record["event"] == "model_call_finished"
    }
    assert {item["stage"] for item in trace if item["event"] == "model_call_started"} == {
        "D1.grounded_mapping" if condition == "grounded" else "D1.ungrounded_inventory",
        "D1.resource_expansion",
        "D2.proposal",
        "D2.selection",
        "D2.plan",
        "D2.review",
        "D2.fill",
        "D3.writer",
    }


@pytest.mark.parametrize("condition", ["grounded", "ungrounded"])
def test_worker_carries_references_through_the_real_pipeline_without_extra_model_calls(
    tmp_path, monkeypatch, condition
):
    _prepare_worker(monkeypatch)
    base_chat = diag.chat_json
    api = Mock()
    api.search_standards.return_value = [
        {
            "caseIdentifierUUID": f"full-source-{rank}",
            "statementCode": f"CODE-{rank}",
            "description": f"Mathematical reference {rank}.",
            "author": "Test author",
            "provider": "Learning Commons",
            "jurisdiction": "Multi-State",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "attributionStatement": "Test attribution",
        }
        for rank in range(1, 11)
    ]

    def selecting_chat(client, model, system, user, temperature, max_tokens):
        payload, raw = base_chat(client, model, system, user, temperature, max_tokens)
        if system.startswith(("You map curriculum", "You list prior resources")):
            payload = {**payload, "selected_sources": ["S1", "S8"]}
        return payload, raw

    monkeypatch.setattr(diag, "chat_json", selecting_chat)
    monkeypatch.setattr(
        diag,
        "retrieve_context",
        lambda case, **kwargs: retrieve_context(case, client=api, **kwargs),
    )
    case_dir = tmp_path / "case_speed"
    summary = diag.run_case_worker(
        "case_speed",
        str(case_dir),
        "luna",
        1,
        d1_condition=condition,
        learning_commons=True,
        learning_commons_cache_dir=str(tmp_path / "cache"),
        design_brief=False,
    )
    assert summary["status"] == "completed"
    api.search_standards.assert_called_once()
    assert api.search_standards.call_args.kwargs["grade_levels"] == []
    d1_saved = json.loads((case_dir / "d1.json").read_text())
    assert d1_saved["schema_version"] == "prior-method-recommendations/v2"
    result = json.loads((case_dir / "result.json").read_text())
    references = result["prior_context"]["learning_commons"]
    assert references["selected_sources"] == ["S1", "S8"]
    assert len(references["response"]) == 10
    trace = [json.loads(line) for line in (case_dir / "model_calls.jsonl").read_text().splitlines()]
    started = [item for item in trace if item["event"] == "model_call_started"]
    assert len(started) == 8
    for call in started:
        user = call["user_prompt"]
        if call["stage"] in {"D1.grounded_mapping", "D1.ungrounded_inventory"}:
            assert "Mathematical reference 10." in user
        elif call["stage"].startswith(("D2.", "D3.")):
            assert "Mathematical reference 1." in user
            assert "Mathematical reference 8." in user
            assert "Mathematical reference 10." not in user
            assert "full-source-" not in user
    writer_call = next(call for call in started if call["stage"] == "D3.writer")
    writer_context = replay._original_context({"started": writer_call})
    assert len(writer_context["mathematical_references"]) == 2
    assert all(
        item["resource"] == "Ratio"
        for item in writer_context["student_context"]["assumed_prior_knowledge"]
    )


def test_reused_d1_does_not_allow_retrieval_to_change_frozen_context(tmp_path):
    with pytest.raises(ValueError, match="freezes its references"):
        diag.run_case_worker(
            "case_speed",
            str(tmp_path / "case"),
            "luna",
            1,
            reused_d1_path_str="saved.json",
            learning_commons=True,
        )
    assert not (tmp_path / "case").exists()


def test_diagnostic_reference_flags_are_default_on_with_opt_out_and_cache_options(tmp_path):
    baseline = diag.parse_args([])
    assert baseline.learning_commons is True
    assert not hasattr(baseline, "design_brief")
    assert baseline.refresh_learning_commons is False
    opted_out = diag.parse_args(["--no-learning-commons"])
    assert opted_out.learning_commons is False
    enabled = diag.parse_args(
        [
            "--learning-commons",
            "--refresh-learning-commons",
            "--learning-commons-cache-dir",
            str(tmp_path),
        ]
    )
    assert enabled.learning_commons is True
    assert enabled.refresh_learning_commons is True
    assert enabled.learning_commons_cache_dir == tmp_path
    with pytest.raises(SystemExit):
        diag.parse_args(["--design-brief"])


def test_worker_uses_frozen_grounding_packet_without_retrieval(tmp_path: Path, monkeypatch):
    _prepare_worker(monkeypatch)
    evidence = [
        {
            "source_url": "https://example.test/rp-a1",
            "standard_id": "CCSS.Math.Content.7.RP.A.1",
            "text": "Compute unit rates associated with ratios of fractions.",
            "label": "Unit rates",
        },
        {
            "source_url": "https://example.test/ns-a1",
            "standard_id": "CCSS.Math.Content.7.NS.A.1",
            "text": "Add and subtract rational numbers.",
            "label": "Rational-number addition and subtraction",
        },
    ]

    def frozen_chat(client, model, system, user, temperature, max_tokens):
        if system.strip().splitlines()[0].startswith("You map curriculum"):
            return (
                {
                    "resources": [
                        {
                            "resource": "Ratio",
                            "taught_as": "Compare a quantity per one unit.",
                            "relevance": "Supports the target.",
                            "evidence_ids": ["official:CCSS.Math.Content.7.RP.A.1"],
                            "confidence": "high",
                        }
                    ]
                },
                "mapping",
            )
        return _offline_chat(client, model, system, user, temperature, max_tokens)

    monkeypatch.setattr(
        d1,
        "retrieve_chunks",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("frozen grounding must not retrieve corpus evidence")
        ),
    )
    monkeypatch.setattr(diag, "chat_json", frozen_chat)
    case_dir = tmp_path / "case_speed"
    summary = diag.run_case_worker(
        "case_speed",
        str(case_dir),
        "luna",
        1,
        grounding_evidence=evidence,
        design_brief=False,
    )
    assert summary["status"] == "completed"
    d1_result = json.loads((case_dir / "d1.json").read_text())["records"][0]["result"]
    assert d1_result["retrieval"]["curated_records_held_out"] == 0
    assert d1_result["retrieval"]["evidence_ids"] == [
        "official:CCSS.Math.Content.7.RP.A.1",
        "official:CCSS.Math.Content.7.NS.A.1",
    ]
    assert d1_result["resource_candidates"][0]["provenance"]["source_url"] == (
        "https://example.test/rp-a1"
    )


@pytest.mark.parametrize(
    ("failure", "status", "stop_stage"),
    [
        ("structure", "plan_blocked", "structure"),
        ("expression", "expression_blocked", "expression"),
        ("meaning_review", "review_blocked", "meaning_review"),
    ],
)
def test_worker_persists_plan_failures_without_downstream_calls(
    tmp_path: Path, monkeypatch, failure, status, stop_stage
):
    _prepare_worker(monkeypatch, failure)
    case_dir = tmp_path / failure
    summary = diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=False)
    assert summary["status"] == status
    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    assert stage["plan_stop_stage"] == stop_stage
    assert stage["plan_attempts"][-1]["stage"] == stop_stage
    assert stage["plan_error"]
    assert stage["fill"] is None
    assert stage["task"] is None
    call_stages = {
        item["stage"]
        for item in (
            json.loads(line) for line in (case_dir / "model_calls.jsonl").read_text().splitlines()
        )
        if item["event"] == "model_call_started"
    }
    assert "D2.fill" not in call_stages
    assert "D3.writer" not in call_stages


@pytest.mark.parametrize(
    ("failure", "expected_task"),
    [("writer_blocked", "blocked"), ("writer_none", "blocked")],
)
def test_worker_persists_blocked_writer_without_claiming_completion(
    tmp_path: Path, monkeypatch, failure, expected_task
):
    _prepare_worker(monkeypatch, failure)
    case_dir = tmp_path / failure
    summary = diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=False)
    assert summary["status"] == "D3_blocked"
    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    assert stage["plan_stop_stage"] == "accepted"
    assert stage["fill"]["accepted"] is True
    assert stage["task"]["status"] == expected_task
    if failure == "writer_none":
        assert "valid JSON" in stage["task"]["blocking_issues"][0]
    assert stage["task_raw_text"]


def test_worker_missing_case_persists_partial_result(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diag, "_load_d1_cases", lambda: [])
    result = diag.run_case_worker("missing", str(tmp_path / "missing"), "luna", 1)
    assert result["status"] == "case_not_found"
    assert (tmp_path / "missing" / "result.json").exists()


def test_benchmark_validates_inputs_before_creating_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diag, "_load_d1_cases", lambda: [{"id": "case_a"}])
    with pytest.raises(ValueError, match="Duplicate"):
        diag.run_benchmark(["case_a", "case_a"], output_dir=tmp_path / "run")
    assert not (tmp_path / "run").exists()
    with pytest.raises(ValueError, match="Unknown model"):
        diag.run_benchmark(["case_a"], model="unknown", output_dir=tmp_path / "run")


def test_cli_defaults_and_model_validation():
    args = diag.parse_args([])
    assert args.cases == diag.ALL8_CASES
    assert args.model == "luna"
    assert args.max_workers == 4
    assert args.proposal_k == 4
    with pytest.raises(SystemExit):
        diag.parse_args(["--model", "not-a-model"])


def test_stage_from_prompt_repair_classifications(tmp_path: Path):
    assert (
        diag._stage_from_prompt(
            "Repair the proposed situation using only the original case",
            d1_prompt=False,
        )
        == "D2.proposal_repair"
    )
    assert (
        diag._stage_from_prompt(
            "Repair the selected situation and its mathematical plan together",
            d1_prompt=False,
        )
        == "D2.design_repair"
    )
    # Existing prefixes unchanged
    assert (
        diag._stage_from_prompt("Design one grade-level situation", d1_prompt=False)
        == "D2.proposal"
    )
    assert (
        diag._stage_from_prompt("You are selecting the best candidate", d1_prompt=False)
        == "D2.selection"
    )
    assert diag._stage_from_prompt("Freeze the mathematical plan", d1_prompt=False) == "D2.plan"
    assert diag._stage_from_prompt("Review whether the plan works", d1_prompt=False) == "D2.review"
    assert diag._stage_from_prompt("Fill values into the skeleton", d1_prompt=False) == "D2.fill"
    assert diag._stage_from_prompt("Write the student-facing task", d1_prompt=False) == "D3.writer"
    # Tracer records these stages correctly
    trace = tmp_path / "calls.jsonl"
    tracer = diag.DiagnosticTracer(trace, "case", "fake-model")
    for prompt_text, expected_stage in [
        ("Repair the proposed situation", "D2.proposal_repair"),
        ("Repair the selected situation", "D2.design_repair"),
    ]:
        tracer.log_call(
            "run_situation_skeletons",
            expected_stage,
            "fake-model",
            {},
            prompt_text,
            "user",
            lambda: ({"ok": True}, '{"ok": true}'),
        )
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    stages = [r["stage"] for r in records if r["event"] == "model_call_started"]
    assert stages == ["D2.proposal_repair", "D2.design_repair"]


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        ("PROPOSE_BRIEF_SYSTEM", "D2.brief_proposal"),
        ("SELECT_BRIEF_SYSTEM", "D2.brief_selection"),
        ("TRANSLATE_BRIEF_SYSTEM", "D2.brief_translation"),
    ],
)
def test_stage_from_actual_design_brief_prompts(section, expected):
    from scripts.design_brief_stage import _prompts

    system = _prompts()[section]
    assert diag._stage_from_prompt(system, d1_prompt=False) == expected
    assert diag._stage_from_prompt(f"\n  {system}", d1_prompt=False) == expected


def test_legacy_benchmark_manifest_records_core_budgets(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diag, "_load_d1_cases", lambda: [{"id": "case_test"}])
    monkeypatch.setattr(
        diag,
        "run_case_worker",
        lambda cid, cdir, model, pk, reused, **kwargs: {
            "case_id": cid,
            "status": "completed",
            "stages": {},
        },
    )
    run_dir = tmp_path / "run"
    manifest = diag.run_benchmark(["case_test"], output_dir=run_dir, design_brief=False)
    assert manifest["budgets"] == {
        "proposal_retry_max": d2.PROPOSAL_RETRY_MAX,
        "plan_retry_max": d2.PLAN_RETRY_MAX,
        "fill_max_tries": d2.FILL_MAX_TRIES,
    }
    assert manifest["proposal_k"] == 4
    assert manifest["model"] == "luna"
    # Verify written manifest.json has identical budgets
    saved_manifest = json.loads((run_dir / "manifest.json").read_text())
    assert saved_manifest["budgets"] == manifest["budgets"]


def test_worker_repaired_winner_flows_through_fill_write_and_preserves_provenance(
    tmp_path: Path, monkeypatch
):
    _prepare_worker(monkeypatch)

    real_plan_fn = d2._plan_until_reviewed
    seen_fill_winner = None
    seen_write_winner = None
    real_fill_fn = d2._fill_until_accepted
    real_write_fn = d2._write_task

    def mock_plan(*args, **kwargs):
        res = real_plan_fn(*args, **kwargs)
        orig_winner = args[4]
        repaired_sk = replace(orig_winner.skeleton, question="Repaired question: which is faster?")
        rep_winner = replace(orig_winner, skeleton=repaired_sk)
        return {
            **res,
            "winner": rep_winner,
            "original_winner": orig_winner,
            "design_repair_attempts": [{"attempt": 1, "status": "repaired", "stage": "repair"}],
        }

    def spy_fill(client, model, prompts, case, winner, plan, prior_context, plan_review=None):
        nonlocal seen_fill_winner
        seen_fill_winner = winner
        return real_fill_fn(
            client, model, prompts, case, winner, plan, prior_context, plan_review=plan_review
        )

    def spy_write(client, model, prompts, case, winner, plan, payload, prior_context, review):
        nonlocal seen_write_winner
        seen_write_winner = winner
        return real_write_fn(
            client, model, prompts, case, winner, plan, payload, prior_context, review
        )

    monkeypatch.setattr(d2, "_plan_until_reviewed", mock_plan)
    monkeypatch.setattr(d2, "_fill_until_accepted", spy_fill)
    monkeypatch.setattr(d2, "_write_task", spy_write)

    case_dir = tmp_path / "case_repaired"
    summary = diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=False)
    assert summary["status"] == "completed"

    # Fill and writer must both see the repaired effective winner
    assert seen_fill_winner is not None
    assert seen_fill_winner.skeleton.question == "Repaired question: which is faster?"
    assert seen_write_winner is not None
    assert seen_write_winner.skeleton.question == "Repaired question: which is faster?"
    assert seen_fill_winner is seen_write_winner

    # Stage results and provenance
    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    orig_q = stage["original_winner"]["skeleton"]["question"]
    assert orig_q.startswith("Which journey has the greater")
    assert stage["winners"][0]["skeleton"]["question"] == "Repaired question: which is faster?"
    assert stage["design_repair_attempts"] == [
        {"attempt": 1, "status": "repaired", "stage": "repair"}
    ]
    # Historical provenance preserved
    assert stage["selection"]["recommended_id"] == 0
    assert stage["judged_candidates"][0]["skeleton"]["question"].startswith(
        "Which journey has the greater"
    )
    # Downstream helper sees effective repaired winner
    loaded_winner = d2._winner_from_result(case_dir / "result.json", "case_speed")
    assert loaded_winner.skeleton.question == "Repaired question: which is faster?"


def test_worker_blocked_repair_does_not_fill(tmp_path: Path, monkeypatch):
    _prepare_worker(monkeypatch)

    fill_called = False
    write_called = False

    def mock_plan(*args, **kwargs):
        orig_winner = args[4]
        return {
            "plan": None,
            "winner": orig_winner,
            "original_winner": orig_winner,
            "design_repair_attempts": [{"attempt": 1, "status": "failed", "stage": "repair"}],
            "attempts": [
                {"attempt": 1, "stage": "meaning_review", "errors": ["joint repair failed"]}
            ],
            "error": "joint repair failed",
        }

    def mock_fill(*args, **kwargs):
        nonlocal fill_called
        fill_called = True
        return {"accepted": True}

    def mock_write(*args, **kwargs):
        nonlocal write_called
        write_called = True
        return {"status": "ready"}, "raw"

    monkeypatch.setattr(d2, "_plan_until_reviewed", mock_plan)
    monkeypatch.setattr(d2, "_fill_until_accepted", mock_fill)
    monkeypatch.setattr(d2, "_write_task", mock_write)

    case_dir = tmp_path / "case_blocked_repair"
    summary = diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=False)
    assert summary["status"] == "review_blocked"
    assert fill_called is False
    assert write_called is False

    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    assert stage["fill"] is None
    assert stage["task"] is None
    assert stage["original_winner"] is not None
    assert stage["design_repair_attempts"] == [
        {"attempt": 1, "status": "failed", "stage": "repair"}
    ]
    assert stage["plan_error"] == "joint repair failed"


def test_worker_legacy_planning_without_winner_fallback(tmp_path: Path, monkeypatch):
    _prepare_worker(monkeypatch)

    real_plan_fn = d2._plan_until_reviewed

    def legacy_plan(*args, **kwargs):
        res = real_plan_fn(*args, **kwargs)
        res.pop("winner", None)
        res.pop("original_winner", None)
        res.pop("design_repair_attempts", None)
        return res

    monkeypatch.setattr(d2, "_plan_until_reviewed", legacy_plan)

    case_dir = tmp_path / "case_legacy"
    summary = diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=False)
    assert summary["status"] == "completed"

    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    orig_q = stage["original_winner"]["skeleton"]["question"]
    assert orig_q.startswith("Which journey has the greater")
    assert stage["design_repair_attempts"] == []
    assert stage["winners"][0]["skeleton"]["question"].startswith("Which journey has the greater")
    assert stage["fill"]["accepted"] is True
    assert stage["task"]["status"] == "ready"


def _example_brief():
    return {
        "schema_version": "design-brief/v2",
        "key_idea": "A journey's pace depends on both distance and elapsed time.",
        "naive_answer": "Choose the longer distance without accounting for elapsed time.",
        "goal": "Compare journeys while accounting for distance and elapsed time.",
        "situation_and_rules": "Each journey has a distance and an elapsed time.",
        "student_question": "Which journey has the greater rate, and why?",
        "approaches": [
            {
                "resources": ["Ratio"],
                "first_action": "Compare distance per unit time.",
                "what_it_establishes": "The distance covered per unit time.",
                "limitation": "It does not describe changes in pace within a journey.",
            }
        ],
        "successful_route": "Divide each distance by its elapsed time and compare the rates.",
        "learning_opportunity": "Distance alone does not establish how quickly a journey finishes.",
        "number_requirements": [],
    }


def _stub_brief_search(monkeypatch, *, valid_count=1, selected=True):
    payload, _ = _offline_chat(None, "fake-model", "Design one grade-level", "", 0.0, 1)
    selection_payload, _ = _offline_chat(None, "fake-model", "You are selecting", "", 0.0, 1)
    winner = diag.selected_candidate(
        [skeleton_from_payload(payload)],
        diag.judge_selection_from_payload(selection_payload, {0}, require_prior_contrast=True),
    )[0]
    brief = design_brief_from_payload(_example_brief())
    winner = replace(winner, skeleton=brief.skeleton(()), design_brief=brief)
    searches = []
    search_result = {
        "proposals": [{"brief": {"goal": "Compare journeys"}, "attempts": []}],
        "n_valid_proposals": valid_count,
        "judged": [winner] if valid_count and selected else [],
        "winners": [winner] if valid_count and selected else [],
        "judge_error": (None if selected and valid_count else "no valid design briefs to select"),
        "judge_raw_text": "brief selection",
        "judge_payload": {"recommended_id": 0},
        "source_hashes": {"scripts/design_brief_stage.py": "frozen-source-hash"},
        "prompt_snapshot": {"PROPOSE_BRIEF_SYSTEM": "Design one mathematical challenge"},
        "brief_selection": (
            {"recommended_id": 0, "selected_brief": {"goal": "Compare journeys"}}
            if valid_count
            else None
        ),
        "translation": None,
    }
    helper = SimpleNamespace(MAX_TOKENS=6000)

    def search(client, model, case, prior_context, *, k=1):
        searches.append({"case": case, "prior_context": prior_context, "k": k})
        for system in (
            "Design one mathematical challenge",
            "Select one promising mathematical design brief",
        ):
            d2.chat_json(client, model, system, "brief context", 0.0, 6000)
        return search_result

    helper.run_design_brief_search = search
    monkeypatch.setitem(sys.modules, "scripts.design_brief_stage", helper)
    monkeypatch.setattr(sys.modules["scripts"], "design_brief_stage", helper, raising=False)
    base_chat = diag.chat_json

    def chat(client, model, system, user, temperature, max_tokens):
        if system.startswith(("Design one mathematical", "Select one promising", "Translate the")):
            return {"ok": True}, "brief"
        payload, raw = base_chat(client, model, system, user, temperature, max_tokens)
        if system.startswith(("You map curriculum", "You list prior resources")):
            payload = {**payload, "selected_sources": ["S1"]}
        return payload, raw

    monkeypatch.setattr(diag, "chat_json", chat)
    for name in (
        "_propose_one",
        "_judge_all",
        "_plan_until_reviewed",
        "_fill_until_accepted",
        "_write_task",
    ):
        monkeypatch.setattr(
            d2, name, lambda *args, **kwargs: pytest.fail("brief mode must replace baseline search")
        )
    return searches, search_result


def _stub_design_data(monkeypatch, *, status="accepted", failure=None):
    calls = []
    payload = {
        "quantities": {
            "distance": {"description": "Journey distance", "unit": "km", "role": "given"},
            "time": {"description": "Elapsed time", "unit": "h", "role": "given"},
        },
        "values": {"distance": 10, "time": 2},
        "conditions": [],
    }
    run = {
        "schema_version": "design-data-run/v1",
        "status": status,
        "accepted": status == "accepted",
        "payload": None if status == "invalid" else payload,
        "check": {"status": status, "conditions": []},
        "attempts": [
            {
                "payload": payload,
                "raw_text": "data",
                "prompts": {"system": "Choose concrete data", "user": "data context"},
                "check": {"status": status, "conditions": []},
                "error": None if status == "accepted" else "Data did not pass.",
            }
        ],
        "error": None if status == "accepted" else "Data did not pass.",
        "source_hashes": {"scripts/design_data_stage.py": "frozen-data-hash"},
        "prompt_snapshot": {"PROPOSE_DATA_SYSTEM": "Choose concrete data"},
    }

    def data(client, model, case, winner, prior_context):
        calls.append(("data", winner, prior_context))
        d2.chat_json(client, model, "Choose concrete data", "data context", 0.0, 6000)
        return run

    def writer(client, model, case, winner, data_run, prior_context):
        calls.append(("writer", winner, data_run, prior_context))
        if failure == "exception":
            raise RuntimeError("offline data writer failure")
        return d2.chat_json(
            client, model, "Write the student-facing task", "data writer context", 0.7, 6000
        )

    base_chat = diag.chat_json

    def chat(client, model, system, user, temperature, max_tokens):
        if system.startswith("Choose concrete data"):
            return payload, "data"
        if system.startswith("Write the student-facing"):
            return _offline_chat(
                client, model, system, user, temperature, max_tokens, failure=failure
            )
        return base_chat(client, model, system, user, temperature, max_tokens)

    monkeypatch.setattr(diag, "chat_json", chat)
    monkeypatch.setattr(d2, "_run_design_data", data, raising=False)
    monkeypatch.setattr(d2, "_write_design_data_task", writer, raising=False)
    return calls, run


@pytest.mark.parametrize("learning_commons", [False, True])
def test_default_design_brief_worker_preserves_context_and_uses_data_loop_and_writer(
    tmp_path, monkeypatch, learning_commons
):
    _prepare_worker(monkeypatch)
    searches, search_result = _stub_brief_search(monkeypatch)
    calls, data_run = _stub_design_data(monkeypatch)
    if learning_commons:
        api = Mock()
        api.search_standards.return_value = [
            {
                "caseIdentifierUUID": "official-source",
                "statementCode": "CODE-1",
                "description": "Compare mathematical quantities.",
                "author": "Test author",
                "provider": "Learning Commons",
                "jurisdiction": "Multi-State",
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "attributionStatement": "Test attribution",
            }
        ]
        monkeypatch.setattr(
            diag,
            "retrieve_context",
            lambda case, **kwargs: retrieve_context(case, client=api, **kwargs),
        )
    case_dir = tmp_path / "brief"
    result = diag.run_case_worker(
        "case_speed",
        str(case_dir),
        "luna",
        2,
        learning_commons=learning_commons,
        learning_commons_cache_dir=str(tmp_path / "cache"),
        shared_context={"marker": "frozen benchmark"},
    )
    assert result["status"] == "completed"
    assert searches[0]["k"] == 2
    saved = json.loads((case_dir / "result.json").read_text())
    assert searches[0]["prior_context"] == saved["prior_context"]
    if learning_commons:
        api.search_standards.assert_called_once()
        assert searches[0]["prior_context"]["learning_commons"]["selected_sources"] == ["S1"]
    stage = saved["stages"]["D2_D3"]
    assert stage["design_brief"] is True
    assert stage["proposals"] == search_result["proposals"]
    assert stage["valid_proposal_count"] == 1
    assert stage["brief_selection"] == search_result["brief_selection"]
    assert stage["translation"] == search_result["translation"]
    assert stage["design_brief_source_hashes"] == search_result["source_hashes"]
    assert stage["design_brief_prompt_snapshot"] == search_result["prompt_snapshot"]
    assert stage["selection"] is None
    assert stage["original_winner"] == json.loads(json.dumps(search_result["winners"][0].to_dict()))
    assert stage["fill"]["accepted"] is True
    assert stage["fill"] == stage["design_data"] == data_run
    assert stage["design_data_source_hashes"] == data_run["source_hashes"]
    assert stage["design_data_prompt_snapshot"] == data_run["prompt_snapshot"]
    assert stage["translation"] is None
    assert stage["winners"][0]["skeleton"]["quantities"] == []
    assert stage["plan_payload"] is None
    assert stage["plan_attempts"] == []
    assert stage["plan_review"] is None
    assert [call[0] for call in calls] == ["data", "writer"]
    assert calls[0][1] is calls[1][1] is search_result["winners"][0]
    assert calls[1][2] is data_run
    assert calls[0][2] == calls[1][3] == saved["prior_context"]
    assert stage["task"]["status"] == "ready"
    trace = [json.loads(line) for line in (case_dir / "model_calls.jsonl").read_text().splitlines()]
    started = [record for record in trace if record["event"] == "model_call_started"]
    brief_calls = [record for record in started if record["stage"].startswith("D2.brief_")]
    assert [record["stage"] for record in brief_calls] == [
        "D2.brief_proposal",
        "D2.brief_selection",
    ]
    assert all("frozen benchmark" in record["user_prompt"] for record in brief_calls)
    assert not {
        "D2.proposal",
        "D2.selection",
        "D2.brief_translation",
        "D2.plan",
        "D2.review",
        "D2.fill",
    } & {record["stage"] for record in started}
    assert stage["model_calls"] == 4
    assert saved["model_call_count"] == 6
    assert "D2.data_proposal" in {record["stage"] for record in started}
    assert d2._winner_from_result(case_dir / "result.json", "case_speed").skeleton.question == (
        search_result["winners"][0].skeleton.question
    )


@pytest.mark.parametrize(
    ("outcome", "expected_status", "expected_data_status", "data_calls"),
    [
        ("accepted", "completed", "accepted", 1),
        ("repaired", "completed", "accepted", 2),
        ("rejected", "completed", "rejected", 3),
        ("review_needed", "completed", "review_needed", 1),
        ("uncertain", "completed", "accepted", 1),
        ("unknown", "completed", "accepted", 1),
        ("selection_rejected", "completed", "accepted", 1),
        ("selection_concern", "completed", "accepted", 1),
        ("invalid", "data_not_accepted", "invalid", 3),
    ],
)
def test_default_worker_runs_actual_stages_with_fake_model_outputs(
    tmp_path, monkeypatch, outcome, expected_status, expected_data_status, data_calls
):
    _prepare_worker(monkeypatch)
    base_chat = diag.chat_json
    brief = _example_brief()
    brief["number_requirements"] = ["Elapsed time must be positive."]
    data_payload = {
        "quantities": {
            "distance": {"description": "Journey distance", "unit": "km", "role": "given"},
            "time": {"description": "Elapsed time", "unit": "h", "role": "given"},
        },
        "values": {
            "distance": 10,
            "time": -1 if outcome in {"repaired", "rejected"} else 2,
        },
        "conditions": [
            {
                "statement": "Elapsed time must be positive.",
                "requirement_indices": [0],
                "essential": True,
                "calculation": {
                    "expressions": {"rate": "distance / time"},
                    "predicate": "time > 0",
                    "symbols": {},
                },
                "judgment": None,
                "reasoning": "The elapsed time is positive and the rate can be calculated.",
            }
        ],
    }
    if outcome == "review_needed":
        data_payload["conditions"][0].update(
            calculation=None, judgment="fails", reasoning="Explicit conflicting task rules."
        )
    elif outcome == "uncertain":
        data_payload["conditions"][0].update(calculation=None, judgment="uncertain")
    elif outcome == "unknown":
        data_payload["conditions"][0]["calculation"]["predicate"] = "missing > 0"

    def chat(client, model, system, user, temperature, max_tokens):
        if system.startswith("Design one mathematical challenge"):
            payload = brief
        elif system.startswith("Select one promising mathematical design brief"):
            payload, _ = _offline_chat(client, model, "You are selecting", "", 0.0, 1)
            payload = {**payload, "approaches": ["brief_0"]}
            if outcome == "selection_rejected":
                payload.update(
                    recommended_id=None,
                    approaches=[],
                    reason="Every design gives away the discovery.",
                )
            elif outcome == "selection_concern":
                payload["main_concern"] = "The question gives away the discovery."
        elif system.startswith("Translate the selected mathematical design brief"):
            pytest.fail("default brief search must not translate")
        elif system.startswith("Choose concrete data"):
            payload = {} if outcome == "invalid" else data_payload
        elif system.startswith("Repair only the numerical values"):
            payload = {"values": {"distance": 10, "time": 2 if outcome == "repaired" else -1}}
        elif system.startswith("Write a student-facing"):
            assert outcome != "invalid"
            assert ('"time": -1' if outcome == "rejected" else '"time": 2') in user
            assert "Compare journeys" in user
            payload, _ = _offline_chat(
                client, model, "Write the student-facing", user, temperature, max_tokens
            )
            payload = {**payload, "withheld": []}
        else:
            return base_chat(client, model, system, user, temperature, max_tokens)
        return payload, json.dumps(payload)

    monkeypatch.setattr(diag, "chat_json", chat)
    for name in (
        "_propose_one",
        "_judge_all",
        "_plan_until_reviewed",
        "_fill_until_accepted",
        "_write_task",
    ):
        monkeypatch.setattr(
            d2, name, lambda *args, **kwargs: pytest.fail("default must not use legacy search")
        )
    case_dir = tmp_path / "default"
    result = diag.run_case_worker("case_speed", str(case_dir), "luna", 1)
    assert result["status"] == expected_status
    saved = json.loads((case_dir / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    assert stage["design_brief"] is True
    assert stage["valid_proposal_count"] == (
        3 if outcome in {"selection_rejected", "selection_concern"} else 1
    )
    assert stage["translation"] is None
    assert stage["winners"][0]["skeleton"]["quantities"] == []
    data_run = stage["design_data"]
    assert data_run["status"] == expected_data_status
    assert data_run["accepted"] is (outcome not in {"rejected", "review_needed", "invalid"})
    if outcome in {"uncertain", "unknown"}:
        assert data_run["check"]["warnings"] and not data_run["check"]["textual_failures"]
    assert data_run == stage["fill"]
    assert len(data_run["attempts"]) == data_calls
    assert {
        "scripts/design_data_stage.py",
        "src/generation/design_data.py",
        "src/generation/design_calculator.py",
        "src/generation/prompts/design_data.yaml",
    } <= data_run["source_hashes"].keys()
    if outcome == "invalid":
        assert data_run["payload"] is None
    else:
        assert data_run["payload"]["conditions"] == data_payload["conditions"]
    assert stage["brief_selection"]["selected_brief"] == {
        **brief,
        "schema_version": "design-brief/v2",
    }
    if data_run["payload"] is not None:
        assert stage["task"]["status"] == "ready"
        if outcome in {"rejected", "review_needed", "selection_rejected", "selection_concern"}:
            assert stage["task"]["quality_status"] == "review_needed"
            assert stage["task"]["quality_findings"]
        if outcome in {"selection_rejected", "selection_concern"}:
            assert len(stage["selection_attempts"]) == 3
            assert stage["design_quality_status"] == "review_needed"
    else:
        assert stage["task"] is None
        assert saved["error"] == data_run["error"]
    assert (
        d2._winner_from_result(case_dir / "result.json", "case_speed").design_brief.goal
        == (brief["goal"])
    )
    trace = [json.loads(line) for line in (case_dir / "model_calls.jsonl").read_text().splitlines()]
    started = [record for record in trace if record["event"] == "model_call_started"]
    stages = [record["stage"] for record in started]
    assert stages.count("D2.data_proposal") == (3 if outcome == "invalid" else 1)
    assert stages.count("D2.data_repair") == (
        data_calls - 1 if outcome in {"repaired", "rejected"} else 0
    )
    assert stages.count("D3.writer") == int(data_run["payload"] is not None)
    assert not {"D2.brief_translation", "D2.plan", "D2.review", "D2.fill"} & set(stages)
    assert saved["trace_counts"]["started"] == saved["trace_counts"]["finished"] == len(started)
    assert saved["finished_at"]


@pytest.mark.parametrize(
    ("valid_count", "selected", "status"),
    [(0, False, "no_valid_proposals"), (1, False, "no_winner")],
)
def test_design_brief_failures_stop_before_data_generation(
    tmp_path, monkeypatch, valid_count, selected, status
):
    _prepare_worker(monkeypatch)
    _, search_result = _stub_brief_search(monkeypatch, valid_count=valid_count, selected=selected)
    monkeypatch.setattr(
        d2,
        "_run_design_data",
        lambda *args, **kwargs: pytest.fail("a missing winner cannot generate data"),
        raising=False,
    )
    case_dir = tmp_path / "blocked"
    result = diag.run_case_worker("case_speed", str(case_dir), "luna", 1)
    assert result["status"] == status
    assert result["error"] == "no valid design briefs to select"
    saved = json.loads((case_dir / "result.json").read_text())
    assert saved["error"] == result["error"]
    stage = saved["stages"]["D2_D3"]
    assert stage["valid_proposal_count"] == valid_count
    assert stage["translation"] == search_result["translation"]
    assert stage["brief_selection"] == search_result["brief_selection"]
    assert stage["fill"] is None
    assert stage["design_data"] is None
    assert stage["task"] is None


@pytest.mark.parametrize(
    ("data_status", "expected"),
    [
        ("review_needed", "completed"),
        ("rejected", "completed"),
        ("invalid", "data_not_accepted"),
    ],
)
def test_default_worker_writes_available_data_without_marking_checks_accepted(
    tmp_path, monkeypatch, data_status, expected
):
    _prepare_worker(monkeypatch)
    _stub_brief_search(monkeypatch)
    calls, data_run = _stub_design_data(monkeypatch, status=data_status)
    original_chat = d2.chat_json
    result = diag.run_case_worker("case_speed", str(tmp_path / "data_stop"), "luna", 1)
    assert result["status"] == expected
    if data_status == "invalid":
        assert result["error"] == data_run["error"]
    saved = json.loads((tmp_path / "data_stop" / "result.json").read_text())
    stage = saved["stages"]["D2_D3"]
    assert stage["status"] == expected
    assert stage["design_data"] == stage["fill"] == data_run
    assert (stage["task"] is None) is (data_status == "invalid")
    assert [call[0] for call in calls] == (
        ["data"] if data_status == "invalid" else ["data", "writer"]
    )
    assert saved["finished_at"]
    assert saved["trace_counts"]["finished"] == (5 if data_status == "invalid" else 6)
    assert d2.chat_json is original_chat


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [("writer_blocked", "D3_blocked"), ("exception", "D2_D3_failed")],
)
def test_default_worker_writer_failure_still_persists_and_restores_tracing(
    tmp_path, monkeypatch, failure, expected_status
):
    _prepare_worker(monkeypatch)
    _stub_brief_search(monkeypatch)
    _stub_design_data(monkeypatch, failure=failure)
    original_chat = d2.chat_json
    result = diag.run_case_worker("case_speed", str(tmp_path / "writer_stop"), "luna", 1)
    assert result["status"] == expected_status
    saved = json.loads((tmp_path / "writer_stop" / "result.json").read_text())
    assert saved["status"] == expected_status
    assert saved["stages"]["D2_D3"]["design_data"]["accepted"] is True
    assert saved["finished_at"]
    assert saved["error"]
    assert d2.chat_json is original_chat


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        ("PROPOSE_DATA_SYSTEM", "D2.data_proposal"),
        ("REPAIR_DATA_SYSTEM", "D2.data_repair"),
        ("WRITE_DATA_TASK_SYSTEM", "D3.writer"),
    ],
)
def test_stage_from_actual_design_data_prompts(section, expected):
    from scripts.design_data_stage import _prompts

    system = _prompts()[section]
    assert diag._stage_from_prompt(system, d1_prompt=False) == expected
    assert diag._stage_from_prompt(f"\n  {system}", d1_prompt=False) == expected


@pytest.mark.parametrize(
    ("first_line", "expected"),
    [
        (
            "Choose concrete data that make the selected Productive Failure design work.",
            "D2.data_proposal",
        ),
        (
            "Repair only the numerical values using the exact calculation results.",
            "D2.data_repair",
        ),
        (
            "Write a student-facing Productive Failure exercise from the fixed design and",
            "D3.writer",
        ),
    ],
)
def test_new_design_data_first_lines_are_traced(tmp_path, monkeypatch, first_line, expected):
    monkeypatch.setattr(diag, "chat_json", lambda *args: ({"ok": True}, '{"ok": true}'))
    trace = tmp_path / "calls.jsonl"
    tracer = diag.DiagnosticTracer(trace, "case", "fake-model")
    traced = diag._traced_chat(tracer, "run_situation_skeletons", d1_prompt=False)
    system = f"\n  {first_line}\nReturn the requested JSON."
    assert traced(None, "fake-model", system, "user", 0.0, 6000) == (
        {"ok": True},
        '{"ok": true}',
    )
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len(records) == 2
    assert {record["stage"] for record in records} == {expected}
    assert {record["event"] for record in records} == {
        "model_call_started",
        "model_call_finished",
    }


@pytest.mark.parametrize("invalid", [None, 0, 1, "false", [], {}])
def test_design_brief_flag_requires_boolean_before_creating_outputs(tmp_path, invalid):
    case_dir = tmp_path / "case"
    with pytest.raises(ValueError, match="design_brief must be a boolean"):
        diag.run_case_worker("case_speed", str(case_dir), "luna", 1, design_brief=invalid)
    with pytest.raises(ValueError, match="design_brief must be a boolean"):
        diag.run_benchmark(["case_speed"], output_dir=case_dir, design_brief=invalid)
    assert not case_dir.exists()


@pytest.mark.parametrize(
    ("design_brief", "learning_commons"),
    [(None, False), (None, True), (False, False), (False, True), (True, False)],
)
def test_benchmark_defaults_to_briefs_and_forwards_only_legacy_optout(
    tmp_path, monkeypatch, design_brief, learning_commons
):
    seen = []

    def worker(case_id, case_dir, model, proposal_k, reused, **kwargs):
        seen.append(kwargs)
        return {"case_id": case_id, "status": "completed"}

    class InlinePool:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, function, *args, **kwargs):
            future = diag.concurrent.futures.Future()
            future.set_result(function(*args, **kwargs))
            return future

    monkeypatch.setattr(diag, "_load_d1_cases", lambda: [{"id": "case_speed"}])
    monkeypatch.setattr(diag, "run_case_worker", worker)
    monkeypatch.setattr(diag.concurrent.futures, "ProcessPoolExecutor", InlinePool)
    manifest = diag.run_benchmark(
        ["case_speed"],
        output_dir=tmp_path / "run",
        learning_commons=learning_commons,
        learning_commons_cache_dir=tmp_path / "cache",
        **({"design_brief": design_brief} if design_brief is not None else {}),
    )
    expected_mode = design_brief is not False
    assert seen[0].get("design_brief", True) is expected_mode
    assert ("design_brief" in seen[0]) is (design_brief is False)
    assert manifest.get("design_brief", False) is expected_mode
    if expected_mode:
        from scripts.design_data_stage import MAX_CALLS, MAX_TOKENS

        assert manifest["settings"]["design_brief"]["max_tokens"] == 6000
        assert "translation_temperature" not in manifest["settings"]["design_brief"]
        assert manifest["budgets"] == {
            "proposal_retry_max": d2.PROPOSAL_RETRY_MAX,
            "design_data_max_calls": MAX_CALLS,
        }
        assert manifest["settings"]["design_data"] == {
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
        }
        assert "fill_temperature" not in manifest["settings"]
    assert seen[0].get("learning_commons", False) is learning_commons
    if learning_commons:
        assert manifest["learning_commons"]["enabled"] is True


@pytest.mark.parametrize("learning_commons", [False, True])
def test_main_uses_default_brief_route_without_flag_kwargs(monkeypatch, learning_commons):
    args = diag.parse_args([] if learning_commons else ["--no-learning-commons"])
    seen = {}
    monkeypatch.setattr(diag, "parse_args", lambda: args)

    def benchmark(**kwargs):
        seen.update(kwargs)
        return {"errors": {}}

    monkeypatch.setattr(diag, "run_benchmark", benchmark)
    assert diag.main() == 0
    assert "design_brief" not in seen
    assert seen["learning_commons"] is learning_commons
