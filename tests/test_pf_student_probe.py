import json

import pytest

from scripts import report_pf_student_probe as report
from scripts import run_pf_student_probe as probe
from src.simulation.pf_student import attempt_prompt, parse_attempt


def context():
    return {
        "grade": 10,
        "subject": "mathematics",
        "target": "PRIVATE_TARGET",
        "assumed_prior_knowledge": [
            {
                "resource": "Arithmetic mean",
                "taught_as": "Calculate an average.",
                "student_move": "PRIVATE_ERROR",
            },
            {"resource": "Basic arithmetic", "taught_as": "Add and divide."},
        ],
    }


def task():
    return {
        "status": "ready",
        "title": "Compare readings",
        "body": "A: 1, 2; B: 1, 3.",
        "question": "Invent a comparison.",
        "quality_findings": ["PRIVATE_FINDING"],
        "teacher_example": "PRIVATE_SOLUTION",
        "approaches": ["PRIVATE_METHOD"],
    }


def test_student_prompt_excludes_target_solution_method_and_feedback():
    prompt = attempt_prompt(task(), context(), {"condition": "learner"})
    assert "PRIVATE" not in json.dumps(prompt)
    assert set(json.loads(prompt["user"])) == {"student_task", "learner_record"}
    assert "Arithmetic mean" in prompt["user"]


def test_prerequisite_omission_does_not_inject_a_wrong_method():
    prompt = attempt_prompt(
        task(),
        context(),
        {
            "condition": "learner",
            "omit_resource": "Arithmetic mean",
        },
    )
    assert "Arithmetic mean" not in prompt["user"]
    assert "Basic arithmetic" in prompt["user"]
    with pytest.raises(ValueError, match="exactly one resource"):
        attempt_prompt(task(), context(), {"condition": "learner", "omit_resource": "missing"})


def test_solver_receives_task_only_and_response_preserves_unfinished():
    prompt = attempt_prompt(task(), context(), {"condition": "solver"})
    assert set(json.loads(prompt["user"])) == {"student_task"}
    payload = {"written_work": "I tried comparing totals.", "answer": "", "unfinished": True}
    assert parse_attempt(payload) == payload
    with pytest.raises(ValueError, match="boolean"):
        parse_attempt({**payload, "unfinished": "true"})
    with pytest.raises(ValueError, match="exactly"):
        parse_attempt({**payload, "quality_score": 3})


def test_added_learned_resource_changes_record_not_student_instruction_or_task():
    base = attempt_prompt(task(), context(), {"condition": "learner"})
    added = attempt_prompt(
        task(),
        context(),
        {
            "condition": "learner",
            "add_resources": [
                {"resource": "Standard deviation", "taught_as": "Used a spread measure."},
            ],
        },
    )
    assert base["system"] == added["system"]
    assert json.loads(base["user"])["student_task"] == json.loads(added["user"])["student_task"]
    resources = json.loads(added["user"])["learner_record"]["assumed_prior_knowledge"]
    assert resources[-1]["resource"] == "Standard deviation"
    assert len(context()["assumed_prior_knowledge"]) == 2
    with pytest.raises(ValueError, match="duplicates"):
        attempt_prompt(
            task(),
            context(),
            {
                "condition": "learner",
                "add_resources": [{"resource": "Arithmetic mean", "taught_as": "Already listed."}],
            },
        )
    with pytest.raises(ValueError, match="nonempty"):
        attempt_prompt(
            task(),
            context(),
            {
                "condition": "learner",
                "add_resources": [{"resource": "Incomplete"}],
            },
        )


def test_frozen_schedule_has_matched_inputs_and_fixed_budget():
    config = json.loads(probe.DEFAULT_CONFIG.read_text())
    requests = probe.build_requests(config)
    assert len(requests) == 56
    assert len({item["id"] for item in requests}) == 56
    assert sum(item["phase"] == "fresh" for item in requests) == 48
    for item in requests:
        text = json.loads(item["prompt"]["user"])
        assert set(text) <= {"student_task", "learner_record"}
        assert "target_concept" not in text
    first = [item for item in requests if item["task_id"] == "consistency_direct"]
    assert len({json.loads(item["prompt"]["user"])["student_task"] for item in first}) == 1


def test_learning_record_study_manipulates_only_resource_records():
    config = json.loads(
        (probe.ROOT / "experiments/configs/pf_learning_record_20261011.json").read_text()
    )
    requests = probe.build_requests(config)
    assert len(requests) == 104
    fresh = [request for request in requests if request["phase"] == "fresh"]
    assert len(fresh) == 96
    for family in ("consistency_direct", "division_direct"):
        rows = [request for request in fresh if request["task_id"] == family]
        assert len({json.loads(row["prompt"]["user"])["student_task"] for row in rows}) == 1
        learners = [row for row in rows if row["profile_id"] != "ordinary_solver"]
        assert len({row["prompt"]["system"] for row in learners}) == 1
        additional = next(
            row for row in learners if row["profile_id"] == "additional_learned_method"
        )
        prior = json.loads(additional["prompt"]["user"])["learner_record"]
        assert len(prior["assumed_prior_knowledge"]) == 4


@pytest.mark.parametrize(
    "config_path",
    [
        probe.DEFAULT_CONFIG,
        probe.ROOT / "experiments/configs/pf_student_diagnosis_20261011.json",
    ],
)
def test_run_retains_invalid_attempts_without_replacements(tmp_path, monkeypatch, config_path):
    config = json.loads(config_path.read_text())
    requests = probe.build_requests(config)[:2]
    monkeypatch.setattr(probe, "build_requests", lambda _: requests)

    class Client:
        def with_options(self, **kwargs):
            assert kwargs == {"max_retries": 0}
            return self

    monkeypatch.setattr(probe, "load_client", lambda _: (Client(), "test-model"))
    calls = []

    def call(*args, **kwargs):
        calls.append(kwargs)
        return {"answer": "12"}, "original invalid output", {"model": "test-model"}, None

    monkeypatch.setattr(probe.benchmark, "_call_json", call)
    output = tmp_path / "probe"
    manifest = probe.run(config_path, output)
    assert len(calls) == 2
    assert all(call["temperature"] == 0.7 and call["timeout_seconds"] == 180 for call in calls)
    assert manifest["status"] == "calibration_completed"
    assert all(item["status"] == "invalid_response" for item in manifest["attempts"])
    record = json.loads((output / manifest["attempts"][0]["result_path"]).read_text())
    assert record["raw_text"] == "original invalid output"
    with pytest.raises(FileExistsError):
        probe.run(config_path, output)


def completed_probe(tmp_path):
    output = tmp_path / "completed"
    requests = [
        {
            "id": "control",
            "phase": "calibration",
            "expected_answer": "12",
            "model": "test-model",
            "profile_id": "learner",
            "task_id": "control",
        },
        {
            "id": "first",
            "phase": "fresh",
            "model": "test-model",
            "profile_id": "learner",
            "task_id": "comparison",
        },
        {
            "id": "second",
            "phase": "fresh",
            "model": "test-model",
            "profile_id": "solver",
            "task_id": "comparison",
        },
    ]
    attempts = []
    for request in requests:
        request.update(
            prompt={"user": json.dumps({"student_task": "Illustrative software-test task"})},
            repeat=1,
        )
        relative = f"{request['phase']}/{request['id']}/result.json"
        invalid = request["id"] == "second"
        result = {
            "id": request["id"],
            "status": "invalid_response" if invalid else "parsed",
            "attempt": None
            if invalid
            else {
                "written_work": "6 + 4 + 2 = 12",
                "answer": "12",
                "unfinished": False,
            },
            "raw_text": "Partial response <retained>" if invalid else "original reply",
            "model_metadata": {"finish_reason": "length" if invalid else "stop"},
        }
        probe.benchmark._write_json(output / relative, result)
        trace = output / relative.replace("result.json", "model_calls.jsonl")
        trace.write_text(
            "\n".join(
                json.dumps(row)
                for row in (
                    {"event": "model_call_started", "call_id": request["id"]},
                    {
                        "event": "model_call_finished",
                        "call_id": request["id"],
                        "elapsed_seconds": 1,
                        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                    },
                )
            )
        )
        attempts.append({"id": request["id"], "result_path": relative})
    probe.benchmark._write_json(
        output / "manifest.json",
        {
            "status": "completed",
            "requests": requests,
            "attempts": attempts,
            "protocol": {"limitations": ["Illustrative software test, not observed learners"]},
        },
    )
    return output


def test_report_keeps_truncation_separate_and_anonymizes_metadata(tmp_path):
    output = completed_probe(tmp_path)
    packet = report.prepare_review(output)
    assert len(packet) == 2
    assert all(
        set(row) == {"student_task", "response_status", "attempt", "unparsed_raw_text"}
        for row in packet.values()
    )
    summary = report.summarize(output)
    assert summary["phases"]["calibration"]["exact_arithmetic_answer"] == 1
    assert summary["phases"]["fresh"]["attempted"] == 2
    assert summary["phases"]["fresh"]["parsed"] == 1
    assert summary["phases"]["fresh"]["invalid_response"] == 1
    assert summary["phases"]["fresh"]["finish_reason/length"] == 1
    report.render(output)
    assert "Partial response &lt;retained&gt;" in (output / "attempts.html").read_text()


def test_report_rejects_duplicate_attempts_and_keeps_unknown_math(tmp_path):
    output = completed_probe(tmp_path)
    packet = report.prepare_review(output)
    probe.benchmark._write_json(
        output / "review_coding.json",
        {
            "provenance": "Illustrative software test",
            "attempts": {
                label: {
                    "mathematics_status": "unknown",
                    "named_advanced_procedure": False,
                    "approaches": ["unknown"],
                    "rationale": "Not evaluated in this software test.",
                }
                for label in packet
            },
        },
    )
    summary = report.summarize(output)
    assert all(counts["math/unknown"] == 1 for counts in summary["task_profile_groups"].values())
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["attempts"].append(manifest["attempts"][0])
    probe.benchmark._write_json(output / "manifest.json", manifest)
    with pytest.raises(ValueError, match="missing or repeated"):
        report.load_results(output)


def test_fresh_phase_requires_unchanged_completed_calibration(tmp_path, monkeypatch):
    requests = probe.build_requests(json.loads(probe.DEFAULT_CONFIG.read_text()))[:1]
    monkeypatch.setattr(probe, "build_requests", lambda _: requests)

    class Client:
        def with_options(self, **kwargs):
            return self

    monkeypatch.setattr(probe, "load_client", lambda _: (Client(), "test-model"))
    monkeypatch.setattr(
        probe.benchmark,
        "_call_json",
        lambda *args, **kwargs: (
            {"written_work": "6 + 4 + 2 = 12", "answer": "12", "unfinished": False},
            "original",
            {"model": "test-model"},
            None,
        ),
    )
    output = tmp_path / "resume"
    probe.run(probe.DEFAULT_CONFIG, output)
    manifest_path = output / "manifest.json"
    original = json.loads(manifest_path.read_text())
    changed = {**original, "protocol": {**original["protocol"], "seed": 1}}
    probe.benchmark._write_json(manifest_path, changed)
    with pytest.raises(ValueError, match="protocol or task inputs changed"):
        probe.run(probe.DEFAULT_CONFIG, output, phase="fresh")
    changed = {
        **original,
        "source_hashes": {
            **original["source_hashes"],
            "src/simulation/pf_student.py": "wrong-hash",
        },
    }
    probe.benchmark._write_json(manifest_path, changed)
    with pytest.raises(ValueError, match="Source changed"):
        probe.run(probe.DEFAULT_CONFIG, output, phase="fresh")
    probe.benchmark._write_json(manifest_path, original)
    final = probe.run(probe.DEFAULT_CONFIG, output, phase="fresh")
    assert final["status"] == "completed"
    assert len(final["attempts"]) == 1
    with pytest.raises(ValueError, match="completed calibration"):
        probe.run(probe.DEFAULT_CONFIG, output, phase="fresh")
