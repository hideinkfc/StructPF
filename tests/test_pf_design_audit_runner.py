import hashlib
import json
import shutil
import uuid
from pathlib import Path

import pytest

from scripts.run_pf_design_audit import (
    CONDITIONS,
    _potential_disagreements,
    _trace_evidence,
    load_calibration_cases,
    load_synthetic_controls,
    run_cases,
)
from src.evaluation.pf_rubric import DIMENSIONS, parse_rating

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workdir():
    path = ROOT / "tests" / f".pf-design-audit-test-{uuid.uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path)


def table1_response(score=2, concerns=None):
    return json.dumps(
        {
            **{
                key: {"evidence": "Synthetic baseline evidence.", "score": score}
                for key in DIMENSIONS
            },
            "mathematical_concerns": concerns or [],
        }
    )


def audit_response(profile="positive"):
    if profile == "unknown":
        status = "unknown"
        approaches = []
    else:
        status = "supported" if profile == "positive" else "not_evidenced"
        approaches = (
            [
                {
                    "route": "Compare a unit rate.",
                    "starting_resource": "Unit rates.",
                    "mathematical_difference": "Compare per-unit quantities.",
                },
                {
                    "route": "Compare total quantities over the interval.",
                    "starting_resource": "Ratio reasoning.",
                    "mathematical_difference": "Compare totals before normalizing.",
                },
            ]
            if profile == "positive"
            else []
        )
    concerns = ["Synthetic possible ambiguity."] if profile == "concern" else []
    math_status = "concern" if concerns else "unknown"
    return json.dumps(
        {
            "target_relevance": {"status": status, "evidence": "Synthetic finding."},
            "prior_resource_start": {"status": status, "evidence": "Synthetic finding."},
            "useful_contrast": {"status": status, "evidence": "Synthetic finding."},
            "approach_diversity": {
                "status": status,
                "evidence": "Synthetic finding.",
                "approaches": approaches,
            },
            "task_openness": {"status": status, "evidence": "Synthetic finding."},
            "mathematics_review": {
                "status": math_status,
                "evidence": "Synthetic math review.",
                "concerns": concerns,
            },
        }
    )


def write_table1_judgment(path, *, score=2, concerns=None):
    raw = table1_response(score, concerns)
    parsed = parse_rating(raw)
    path.write_text(
        json.dumps(
            {
                **parsed,
                "raw_response": raw,
                "attempt_id": path.parent.name,
            }
        )
    )


BENCHMARK_STANDARD_IDS = (
    "CCSS.Math.Content.7.RP.A.1",
    "CCSS.Math.Content.7.NS.A.1",
)


def pipeline_record(
    task,
    *,
    prior_contrast=None,
    check_accepted=True,
    evidence_ids=None,
):
    if evidence_ids is None:
        evidence_ids = [f"official:{identifier}" for identifier in BENCHMARK_STANDARD_IDS]
    return {
        "status": "ready",
        "task": task,
        "pipeline_result": {
            "stages": {
                "D1": {"output": {"retrieval": {"evidence_ids": evidence_ids}}},
                "D2_D3": {
                    "math_plan": {"prior_contrast": prior_contrast},
                    "fill": {
                        "check": {
                            "accepted": check_accepted,
                            "status": "accepted" if check_accepted else "rejected",
                            "reason": "Synthetic checker record.",
                        }
                    },
                },
            }
        },
    }


@pytest.fixture
def saved_inputs(workdir):
    context = {
        "grade": 7,
        "subject": "mathematics",
        "jurisdiction": "USA",
        "assumed_prior_knowledge": [{"resource": "Unit rates", "taught_as": "Compute unit rates."}],
    }
    config = {
        "case": {"target_concept": "Shared target."},
        "learner_context": context,
        "grounding_evidence": [
            {"standard_id": identifier} for identifier in BENCHMARK_STANDARD_IDS
        ],
    }
    benchmark = workdir / "v4"
    benchmark.mkdir()
    (benchmark / "config.json").write_text(json.dumps(config))
    source_paths = (
        "src/evaluation/prompts/pf_rubric.yaml",
        "src/evaluation/pf_rubric.py",
    )
    hashes = {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in source_paths
    }
    manifest = {
        "conditions": list(CONDITIONS),
        "source_integrity_unchanged": True,
        "source_hashes": hashes,
        "source_hashes_after": hashes,
    }
    (benchmark / "manifest.json").write_text(json.dumps(manifest))

    for condition in CONDITIONS:
        for attempt_number in (1, 2, 3, 4):
            attempt_dir = benchmark / "attempts" / condition / f"{attempt_number:03d}"
            attempt_dir.mkdir(parents=True)
            task = {
                "status": "ready",
                "title": "Synthetic saved task",
                "body": (
                    "A short missing-information control task."
                    if condition == "V1" and attempt_number == 1
                    else "A short student-facing task."
                ),
                "question": "Explain your reasoning.",
            }
            attempt = (
                pipeline_record(task, prior_contrast={"kind": "numeric"})
                if condition == "PIPELINE"
                else {"status": "ready", "task": task}
            )
            attempt.update(
                {
                    "attempt_id": f"{condition}-{attempt_number:03d}",
                    "condition": condition,
                }
            )
            attempt_path = attempt_dir / "attempt.json"
            attempt_path.write_text(json.dumps(attempt))
            write_table1_judgment(attempt_dir / "judgment.json")

    pilot = workdir / "pilot"
    (pilot / "input").mkdir(parents=True)
    (pilot / "judge_run").mkdir()
    pilot_task = {
        "status": "ready",
        "title": "Synthetic checked pilot",
        "body": "The same fixed learner context.",
        "question": "Compare and explain.",
    }
    replay = {
        "case_id": "checked-pilot-source-id",
        "task": pilot_task,
        "new_writer_context": {"student_context": context},
    }
    replay_bytes = json.dumps(replay).encode()
    replay_path = pilot / "input/grade7_replay.json"
    replay_path.write_bytes(replay_bytes)
    source_attempt = workdir / "checked_pilot_source.json"
    source_bytes = json.dumps(
        pipeline_record(pilot_task, prior_contrast={"kind": "numeric"})
    ).encode()
    source_attempt.write_bytes(source_bytes)
    provenance = {
        "learner_context_identical_to_frozen_config": True,
        "replay_input_sha256": hashlib.sha256(replay_bytes).hexdigest(),
        "source_attempt": str(source_attempt),
        "source_attempt_sha256": hashlib.sha256(source_bytes).hexdigest(),
    }
    (pilot / "input/provenance.json").write_text(json.dumps(provenance))
    raw = table1_response()
    baseline = parse_rating(raw)
    rating = {
        **baseline,
        "case_id": replay["case_id"],
        "rubric_version": "rahimi-table1/v1",
        "source_sha256": hashlib.sha256(replay_bytes).hexdigest(),
        "raw_response": raw,
    }
    (pilot / "judge_run/ratings.jsonl").write_text(json.dumps(rating) + "\n")
    return benchmark, pilot, context


def test_selects_ready_cases_from_each_condition_and_checked_pilot_blindly(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(
        benchmark,
        pilot,
        offset_per_condition=0,
        include_checked_pilot=True,
        seed=18,
    )
    assert len(cases) == 5
    assert {case["condition"] for case in cases} == {*CONDITIONS, "calibration_pilot"}
    for case in cases:
        user = json.loads(case["user_prompt"])
        assert set(user) == {"learning_target", "learner_context", "student_task"}
        assert "condition" not in case["user_prompt"]
        assert case["source_sha256"]
        assert case["user_input_sha256"]
        assert case["frozen_table1_baseline"]["rubric_version"] == "rahimi-table1/v1"
    direct = next(case for case in cases if case["condition"] == "V1")
    assert direct["trace_evidence"]["availability"] == "unavailable"
    assert "not a task failure" in direct["trace_evidence"]["interpretation"]
    pipeline = next(case for case in cases if case["condition"] == "PIPELINE")
    assert pipeline["trace_evidence"]["availability"] == "available"
    assert pipeline["trace_evidence"]["selected_prior_contrast"] == (
        "provided_not_independently_reverified"
    )
    trace = pipeline["trace_evidence"]
    assert trace["verification"] == "trace_present_not_independently_verified"
    assert trace["recorded_math_check"]["status"] == "accepted_recorded"
    assert "not independently verified" in trace["recorded_math_check"]["scope"]
    assert "or proof" in trace["recorded_math_check"]["scope"]
    assert trace["curriculum_id_check"]["status"] == "checked"
    assert trace["mapped_curriculum_standard_ids"] == sorted(BENCHMARK_STANDARD_IDS)


def test_trace_ids_use_exact_official_mapping_and_flag_unrelated_ids(saved_inputs, workdir):
    _, _, _ = saved_inputs
    expected = set(BENCHMARK_STANDARD_IDS)
    task = {"status": "ready", "title": "Trace test", "body": "Values", "question": "Explain"}
    valid_record = pipeline_record(task)
    source_path = workdir / "valid_trace.json"
    source_bytes = json.dumps(valid_record).encode()
    source_path.write_bytes(source_bytes)
    valid = _trace_evidence(valid_record, source_path, source_bytes, expected)
    assert valid["curriculum_id_check"]["status"] == "checked"
    assert valid["mapped_curriculum_standard_ids"] == sorted(BENCHMARK_STANDARD_IDS)

    invalid_record = pipeline_record(
        task,
        evidence_ids=[
            f"official:{BENCHMARK_STANDARD_IDS[0]}",
            f"unrelated:{BENCHMARK_STANDARD_IDS[1]}",
            BENCHMARK_STANDARD_IDS[1],
        ],
    )
    invalid_path = workdir / "unrelated_trace.json"
    invalid_bytes = json.dumps(invalid_record).encode()
    invalid_path.write_bytes(invalid_bytes)
    invalid = _trace_evidence(invalid_record, invalid_path, invalid_bytes, expected)
    assert invalid["curriculum_id_check"]["status"] == "concern"
    assert invalid["mapped_curriculum_standard_ids"] == [BENCHMARK_STANDARD_IDS[0]]
    assert invalid["curriculum_id_check"]["unexpected_ids"] == sorted(
        [f"unrelated:{BENCHMARK_STANDARD_IDS[1]}", BENCHMARK_STANDARD_IDS[1]]
    )


def test_calibration_selection_is_capped_at_two_per_condition(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    with pytest.raises(ValueError, match="capped"):
        load_calibration_cases(
            benchmark,
            pilot,
            per_condition=3,
            offset_per_condition=0,
            include_checked_pilot=True,
        )
    cases = load_calibration_cases(
        benchmark,
        pilot,
        per_condition=2,
        offset_per_condition=0,
        include_checked_pilot=True,
    )
    assert len(cases) == 9
    for condition in CONDITIONS:
        assert sum(case["condition"] == condition for case in cases) == 2


def test_v5_default_uses_third_ready_cases_without_reusing_prior_calibrations(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(benchmark, pilot)
    assert len(cases) == len(CONDITIONS)
    assert {case["case_id"] for case in cases} == {f"{condition}-003" for condition in CONDITIONS}
    assert all(case["kind"] == "saved_benchmark_task" for case in cases)


def test_v5_offset_three_selects_the_fourth_ready_case_per_condition(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(benchmark, pilot, offset_per_condition=3)
    assert {case["case_id"] for case in cases} == {f"{condition}-004" for condition in CONDITIONS}
    assert all(case["kind"] == "saved_benchmark_task" for case in cases)
    assert all(case["user_input_sha256"] for case in cases)


def test_offset_above_three_is_rejected(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    with pytest.raises(ValueError, match="0, 1, 2, or 3"):
        load_calibration_cases(benchmark, pilot, offset_per_condition=4)


def test_topic_diverse_controls_are_bounded_and_their_labels_stay_out_of_inputs(workdir):
    controls = load_synthetic_controls()
    assert len(controls) == 6
    assert (
        sum(
            item["illustrative_signals"].get("approach_diversity") == "not_evidenced"
            for item in controls
        )
        == 3
    )
    for control in controls:
        payload = json.loads(control["user_prompt"])
        assert set(payload) == {"learning_target", "learner_context", "student_task"}
        assert control["case_id"] not in control["user_prompt"]
        assert control["control_purpose"] not in control["user_prompt"]
        assert json.dumps(control["illustrative_signals"]) not in control["user_prompt"]


def test_runner_saves_control_rationales_without_table1_disagreement_claims(saved_inputs, workdir):
    benchmark, pilot, _ = saved_inputs
    benchmark_cases = load_calibration_cases(benchmark, pilot)
    cases = benchmark_cases + load_synthetic_controls()
    summary = run_cases(
        cases,
        workdir / "controls_run",
        client_loader=lambda _: (object(), "gpt-5.6-luna"),
        chat=lambda *args, **kwargs: ({}, audit_response("positive")),
    )
    assert summary["attempted"] == summary["model_calls"] == 10
    assert summary["scored"] == 10
    assert summary["case_counts_by_kind"] == {
        "saved_benchmark_task": 4,
        "synthetic_control_not_human_rated": 6,
    }
    assert summary["synthetic_control_use"]["included"] is True
    assert len(summary["synthetic_control_use"]["case_ids"]) == 6
    assert "not independent validation" in summary["synthetic_control_use"]["interpretation"]
    assert any("reused across runs" in value for value in summary["limitations"])
    assert summary["blind_input_verification"]["passed"] is True
    assert summary["blind_input_verification"]["benchmark_target_and_context_shared"] is True
    assert summary["frozen_judge_comparison"]["cases_with_assessable_findings"] == 4
    controls = [
        item for item in summary["ratings"] if item["kind"] == "synthetic_control_not_human_rated"
    ]
    assert all(item["frozen_table1_scores"] is None for item in controls)
    assert all(item["model_rationale"] for item in controls)


def test_missing_or_changed_frozen_sources_are_rejected(saved_inputs):
    benchmark, pilot, _ = saved_inputs
    manifest = json.loads((benchmark / "manifest.json").read_text())
    manifest["source_integrity_unchanged"] = False
    (benchmark / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="integrity"):
        load_calibration_cases(benchmark, pilot)


def test_dry_run_stores_blinded_inputs_and_does_not_load_a_client(saved_inputs, workdir):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(benchmark, pilot)

    def forbidden(_):
        pytest.fail("Dry run must not load a model client")

    output = workdir / "prepared"
    manifest = run_cases(cases, output, dry_run=True, client_loader=forbidden)
    assert manifest["condition_blind"] is True
    assert manifest["case_count"] == len(CONDITIONS)
    assert manifest["synthetic_control_use"]["included"] is False
    assert not (output / "ratings.jsonl").exists()


def test_run_records_responses_counts_unknowns_and_frozen_disagreement_flags(saved_inputs, workdir):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(
        benchmark, pilot, offset_per_condition=0, include_checked_pilot=True
    )
    calls = []

    def loader(selector):
        assert selector == "luna"
        return object(), "gpt-5.6-luna"

    def chat(_client, _model, _system, user, **_settings):
        calls.append(user)
        profile = "unknown" if "missing-information control" in user else "positive"
        return {}, audit_response(profile)

    output = workdir / "rated"
    summary = run_cases(
        cases,
        output,
        client_loader=loader,
        chat=chat,
    )
    assert summary["attempted"] == summary["model_calls"] == 5
    assert summary["scored"] == 4
    assert summary["unknown"] == 1
    assert summary["failed"] == 0
    assert summary["condition_blind"] is True
    assert len(calls) == 5
    assert summary["frozen_judge_comparison"]["comparable_total"] is False
    assert summary["frozen_judge_comparison"]["status"] == "partial"
    rating_lines = (output / "ratings.jsonl").read_text().splitlines()
    assert len(rating_lines) == 5
    saved = json.loads(rating_lines[0])
    assert "raw_response" in saved
    assert "trace_evidence" in saved
    assert saved["user_input_sha256"]


def test_invalid_secondary_responses_do_not_report_zero_disagreements(saved_inputs, workdir):
    benchmark, pilot, _ = saved_inputs
    cases = load_calibration_cases(benchmark, pilot)
    result = run_cases(
        cases[:1],
        workdir / "invalid",
        client_loader=lambda _: (object(), "gpt-5.6-luna"),
        chat=lambda *args, **kwargs: ({}, "not JSON"),
    )
    comparison = result["frozen_judge_comparison"]
    assert result["failed"] == 1
    assert comparison["status"] == "not_assessable"
    assert comparison["cases_with_assessable_findings"] == 0
    assert comparison["cases_without_assessable_findings"] == 1
    assert comparison["potential_disagreement_count"] is None


def test_cross_protocol_flags_are_review_candidates_not_score_conversions():
    baseline = {
        "scores": {"MR": 3, "OE": 1},
        "mathematical_concerns": ["Frozen concern."],
    }
    audit = {
        "approach_diversity": {"status": "not_evidenced"},
        "task_openness": {"status": "supported"},
        "mathematics_review": {"status": "model_recomputed", "concerns": []},
    }
    flags = _potential_disagreements(baseline, audit)
    assert {flag["kind"] for flag in flags} == {
        "directional_extreme_review",
        "mathematics_concern_presence_review",
    }
    assert "not a score equivalence" in flags[0]["interpretation"]
    assert "not an adjudicated disagreement" in flags[2]["interpretation"]
    audit["mathematics_review"]["status"] = "unknown"
    flags = _potential_disagreements(baseline, audit)
    assert all(flag["kind"] != "mathematics_concern_presence_review" for flag in flags)
