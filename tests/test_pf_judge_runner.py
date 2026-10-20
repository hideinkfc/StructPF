import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from openai import APIConnectionError

from scripts.run_pf_judge import load_controls, load_saved_cases, rate_case, run_cases
from src.evaluation.pf_rubric import DIMENSIONS


def response(score=2):
    return json.dumps(
        {
            **{key: {"evidence": "Specific evidence.", "score": score} for key in DIMENSIONS},
            "mathematical_concerns": [],
        }
    )


def case():
    return {
        "case_id": "case",
        "kind": "saved_pipeline_task",
        "user_prompt": '{"student_task": "Compare."}',
    }


def test_saved_case_uses_current_task_and_sanitized_context(tmp_path):
    source = {
        "case_id": "example",
        "task": {"status": "ready", "title": "New", "body": "Values", "question": "Explain"},
        "source_task": {"body": "SECRET_OLD_TASK"},
        "new_writer_context": {
            "student_context": {
                "grade": "7",
                "target_concept": "SECRET_TARGET",
                "assumed_prior_knowledge": [
                    {
                        "resource": "Division",
                        "taught_as": "Divide whole numbers",
                        "falls_short_because": "SECRET_FAILURE",
                    }
                ],
            }
        },
    }
    (tmp_path / "result.json").write_text(json.dumps(source))
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "cases": [{"case_id": "example", "replay_result": "result.json"}],
            }
        )
    )
    saved = load_saved_cases(audit_path, ["example"], tmp_path)[0]
    assert "SECRET" not in saved["user_prompt"]
    assert "New" in saved["user_prompt"]
    assert len(saved["source_sha256"]) == 64
    with pytest.raises(ValueError):
        load_saved_cases(audit_path, ["missing"], tmp_path)
    with pytest.raises(ValueError):
        load_saved_cases(audit_path, ["example", "example"], tmp_path)


def test_controls_labelled_in_artifact_not_judge_input(tmp_path):
    path = tmp_path / "controls.json"
    path.write_text(
        json.dumps(
            [
                {
                    "case_id": "control",
                    "purpose": "SECRET_EXPECTATION",
                    "student_task": "24 / 6",
                    "learner_context": {"grade": "7"},
                }
            ]
        )
    )
    control = load_controls(path)[0]
    assert control["kind"] == "synthetic_control_not_human_rated"
    assert "SECRET" not in control["user_prompt"]


def test_invalid_response_preserves_raw_without_zero():
    raw = response(9)
    result = rate_case(None, "gpt-5.6-luna", "system", "user", chat=lambda *a, **k: ({}, raw))
    assert result["status"] == "invalid_response"
    assert result["scores"] is None
    assert result["raw_response"] == raw


def test_api_failure_is_explicit():
    import httpx

    def unavailable(*args, **kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))

    result = rate_case(None, "gpt-5.6-luna", "system", "user", chat=unavailable)
    assert result["status"] == "api_error"
    assert result["scores"] is None


def test_dry_run_never_loads_client_and_refuses_overwrite(tmp_path):
    def forbidden(*args):
        pytest.fail("Dry run must not load a model client")

    output = tmp_path / "run"
    result = run_cases([case()], output, dry_run=True, client_loader=forbidden)
    assert result["status"] == "prepared"
    assert result["model_selector"] == "luna"
    assert not (output / "ratings.jsonl").exists()
    with pytest.raises(FileExistsError):
        run_cases([case()], output, dry_run=True, client_loader=forbidden)


def test_luna_run_saves_prompt_response_settings_and_computed_total(tmp_path):
    calls = []

    def loader(selector):
        assert selector == "luna"
        return object(), "gpt-5.6-luna"

    def chat(client, model, system, user, **settings):
        calls.append((model, system, user, settings))
        return {}, response()

    output = tmp_path / "run"
    summary = run_cases([case()], output, client_loader=loader, chat=chat)
    assert summary["scored"] == summary["attempted"] == 1
    assert summary["failed"] == 0
    assert summary["ratings"][0]["scores"]["TOTAL"] == 10
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["model_name"] == "gpt-5.6-luna"
    assert manifest["effective_settings"]["max_completion_tokens"] == 4000
    assert "temperature" not in manifest["effective_settings"]
    assert manifest["system_prompt"] == calls[0][1]
    rating = json.loads((output / "ratings.jsonl").read_text())
    assert rating["raw_response"] == response()
    assert rating["user_prompt"] == calls[0][2]


def test_failed_run_not_success_shaped(tmp_path):
    summary = run_cases(
        [case()],
        tmp_path / "run",
        client_loader=lambda _: (None, "gpt-5.6-luna"),
        chat=lambda *a, **k: (None, "not JSON"),
    )
    assert summary["failed"] == 1
    assert summary["scored"] == 0
    manifest = json.loads((tmp_path / "run/manifest.json").read_text())
    assert manifest["status"] == "completed_with_failures"


def test_notebook_wires_shared_judge_without_generating_or_sending_teacher_notes():
    path = Path(__file__).resolve().parents[1] / "notebooks/05_pf_evaluation_round1.ipynb"
    notebook = json.loads(path.read_text())
    sources = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    for source in sources:
        compile(source, str(path), "exec")
    assert any('load_client("luna")' in source for source in sources)
    exercises = [
        SimpleNamespace(
            version="V2",
            grade="7",
            raw_output="SECRET_RAW",
            sections={
                "TOPIC": "SECRET_TARGET",
                "NARRATIVE": "Student context.",
                "TASK": "Compare.",
                "CONSOLIDATION NOTE": "SECRET_SOLUTION",
            },
        )
    ]
    scope = {"exercises": exercises, "judge_client": None, "judge_model": "gpt-5.6-luna"}
    exec(next(source for source in sources if "def judge_input_for" in source), scope)
    seen = []

    def fake_rate(client, model, system, user):
        seen.append((model, user))
        return {"status": "invalid_response", "scores": None, "raw_response": "bad"}

    scope["rate_case"] = fake_rate
    exec(next(source for source in sources if "results = []" in source), scope)
    assert seen[0][0] == "gpt-5.6-luna"
    assert "SECRET" not in seen[0][1]
    assert scope["results"][0]["TOTAL"] is None
    exec(next(source for source in sources if "# Per-version means" in source), scope)
