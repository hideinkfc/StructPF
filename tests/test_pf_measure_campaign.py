import json

import pytest

from scripts import run_pf_measure_campaign as runner
from src.evaluation import pf_three_role as pf
from src.utils.llm_client import LLMResponse


def cases():
    return [
        {
            "case_id": "test-case",
            "student_task": "Invent a measure of variation for A=[1,2,3] and B=[0,2,4].",
            "learning_target": "Variation",
            "learner_context": {
                "assumed_prior_knowledge": [
                    {"resource": "Arithmetic", "taught_as": "Add, subtract, divide."}
                ]
            },
            "references": {"alignment": {"value": "yes"}},
        }
    ]


def reply(messages):
    prompt = messages[0]["content"]
    quote = "Invent a measure of variation"
    if prompt == pf.system("solver"):
        output = {"attempts": [{"idea": "Range", "work": "Subtract min from max: 2 and 4."}]}
    elif prompt == pf.system("task_judge"):
        output = {
            "action": "final",
            "alignment": {"verdict": "yes", "quotes": [quote], "reason": "Compare variation."},
            "invention": {"verdict": "yes", "quotes": [quote], "reason": "Invent the measure."},
            "validity": {"verdict": "yes", "reason": "Both nonempty lists support range."},
        }
    else:
        output = {
            "action": "final",
            "attempts": [{"status": "meets_demands", "reason": "Range distinguishes the lists."}],
            "inaccessible_because": None,
        }
    return LLMResponse(
        text=json.dumps(output),
        model="mock",
        finish_reason="stop",
        usage={"prompt_tokens": 10, "completion_tokens": 10},
    )


def fake_jobs(monkeypatch):
    def init(self, output, *, workers=16, tokens=7000):
        self.output, self.workers, self.tokens = output, workers, tokens
        self.clients = {model: reply for model in runner.MODELS}
        self.signature = "test-version"

    monkeypatch.setattr(runner.Jobs, "__init__", init)


def test_phase_resume_and_shared_solver_evidence(tmp_path, monkeypatch):
    fake_jobs(monkeypatch)
    results, summary = runner.phase(cases(), tmp_path / "phase", repeats=2, sensitivity=True)
    assert len(results) == 5
    diagnostics = runner.calibration_diagnostics(cases(), results)
    assert diagnostics["by_model_measure"]["luna:target_alignment"]["comparisons"] == 2
    assert summary["execution"]["role_jobs"] == 11
    assert all(
        record["measures"]["prior_knowledge_accessibility"]["value"] == "yes" for record in results
    )
    again, _ = runner.phase(cases(), tmp_path / "phase", repeats=2, sensitivity=True)
    assert again == results
    jobs = list((tmp_path / "phase/jobs").glob("*attempt__luna*"))
    assert len(jobs) == 4
    inputs = [json.loads(path.read_text())["input"]["attempts"] for path in jobs]
    assert all(item == inputs[0] for item in inputs)


def test_resume_rejects_input_change(tmp_path, monkeypatch):
    fake_jobs(monkeypatch)
    runner.phase(cases(), tmp_path / "phase")
    changed = cases()
    changed[0]["student_task"] += " Changed."
    with pytest.raises(ValueError, match="Frozen phase"):
        runner.phase(changed, tmp_path / "phase")


def test_references_do_not_enter_api_payloads(tmp_path, monkeypatch):
    fake_jobs(monkeypatch)
    runner.phase(cases(), tmp_path / "phase")
    for path in (tmp_path / "phase/jobs").glob("*.json"):
        record = json.loads(path.read_text())
        assert "references" not in record["input"]
        if record["role"] == "solver":
            assert "learning_target" not in record["input"]
            assert "Variation" not in record["calls"][0]["messages"][1]["content"]


def test_calibration_diagnostics_report_provisional_matches(tmp_path, monkeypatch):
    fake_jobs(monkeypatch)
    results, _ = runner.phase(cases(), tmp_path / "phase")
    diag = runner.calibration_diagnostics(cases(), results)
    assert "not human-reviewed" in diag["reference_provenance"]
    assert diag["by_model_measure"]["luna:target_alignment"] == {"matches": 1, "comparisons": 1}
    assert diag["disagreements"] == []


def test_report_preserves_unique_conditions_and_occurrence_counts(tmp_path, monkeypatch):
    from scripts.report_pf_measure_campaign import generate

    fake_jobs(monkeypatch)
    case_list = cases()
    runner.phase(case_list, tmp_path / "full")
    case_list[0]["occurrences"] = [
        {"run": "example", "method": "DIRECT", "source": "one.json"},
        {"run": "example", "method": "DIRECT", "source": "two.json"},
    ]
    runner.write(tmp_path / "catalog.json", {"cases": case_list, "unassessable": [{}]})
    runner.write(tmp_path / "pack.json", {"development": case_list, "transfer": []})
    report = generate(
        tmp_path / "catalog.json",
        tmp_path / "pack.json",
        tmp_path / "full",
        tmp_path / "missing_dev",
        tmp_path / "missing_transfer",
        tmp_path / "report",
    )
    assert report["unique_input_conditions_evaluated"] == 1
    assert report["run_method_occurrences"]["example · DIRECT"]["luna"]["occurrences"] == 2
    assert report["unassessable_records"] == 1
    assert "not human-validated" in (tmp_path / "report/report.html").read_text()
    assert "Invent a measure of variation" in (tmp_path / "report/report.html").read_text()


def test_name_only_history_is_preserved_without_added_knowledge(caplog):
    case = cases()[0]
    case["learner_context"] = {"assumed_prior_knowledge": [{"resource": "Ratio"}]}
    normalized = runner.case_inputs(case)
    assert normalized["learner_context"]["assumed_prior_knowledge"] == [
        {
            "resource": "Ratio",
            "taught_as": "Ratio",
        }
    ]
    assert "no taught depth inferred" in caplog.text
    assert "taught_as" not in case["learner_context"]["assumed_prior_knowledge"][0]


def test_offline_campaign_verification_replays_software_invariants(tmp_path, monkeypatch):
    import hashlib

    from scripts.verify_pf_measure_campaign import verify

    fake_jobs(monkeypatch)
    entries = cases()
    runner.phase(entries, tmp_path / "full")
    runner.write(tmp_path / "catalog.json", {"cases": entries})
    runner.write(tmp_path / "calibration_pack.json", {"test_fixture": True})
    runner.write(
        tmp_path / "calibration_decision.json",
        {
            "catalog_sha256": hashlib.sha256((tmp_path / "catalog.json").read_bytes()).hexdigest(),
            "reference_sha256": hashlib.sha256(
                (tmp_path / "calibration_pack.json").read_bytes()
            ).hexdigest(),
        },
    )
    runner.write(tmp_path / "frozen_implementation/sha256.json", {})
    result = verify(tmp_path, tmp_path / "full")
    assert result["input_conditions"] == 1 and result["judge_results"] == 2
    assert result["role_jobs"] == 5 and result["model_calls"] == 5
    assert result["human_validated"] is False
