import json

import pytest

from scripts import report_pf_method_comparison as reporting
from scripts import run_pf_fresh_comparison as comparison


@pytest.mark.parametrize("name", comparison.CASES)
def test_fixed_inputs_keep_teacher_repertoire_without_expert_task_or_misconceptions(name):
    case, packet, shared = comparison.fixed_inputs(name)
    resources = packet["records"][0]["result"]["recommendations"]
    assert [
        {"resource": item["resource"], "taught_as": item["taught_as"]} for item in resources
    ] == shared["learner_context"]["assumed_prior_knowledge"]
    assert packet["origin"] == "fixed_teacher_context_not_generated_D1"
    assert "misconceptions" not in case
    assert "pilot_protocol" not in case
    assert all(item["provenance"]["type"] == "teacher" for item in resources)
    assert comparison.REFERENCES[name]["path"] not in json.dumps((case, packet, shared))


def test_direct_receives_identical_opportunity_guidance_and_not_brief_response_schema():
    system = comparison.direct_system()
    proposal = comparison.briefs._prompts()["PROPOSE_BRIEF_SYSTEM"]
    guidance = proposal.split("DESIGN OPPORTUNITY CHECK\n", 1)[1].split(
        "SELF-AUTHORED FORMAT EXAMPLE", 1
    )[0]
    assert guidance in system
    assert system.endswith("Return only status, title, body, question.")
    assert "NOT A VALIDATED PF TASK" in system


def test_comparison_preserves_failed_attempts_and_shared_inputs(tmp_path, monkeypatch):
    requests = []

    class Client:
        def with_options(self, **kwargs):
            assert kwargs == {"max_retries": 0}
            return self

    monkeypatch.setattr(comparison, "load_client", lambda model: (Client(), "test-model"))

    def fake_call(client, model, system, user, **kwargs):
        requests.append(user)
        return {"status": "ready"}, "invalid reply", None, None

    def fake_pipeline(case_id, path, model, count, d1_path, **kwargs):
        assert count == 2
        case, _, shared = comparison.fixed_inputs("loibl_variance")
        assert kwargs["case_override"] == case
        assert kwargs["shared_context"] == shared
        record = {"status": "review_needed", "error": "Essential condition unresolved"}
        comparison.save(comparison.Path(path) / "result.json", record)
        return record

    monkeypatch.setattr(comparison.benchmark, "_call_json", fake_call)
    monkeypatch.setattr(comparison.diagnostic, "run_case_worker", fake_pipeline)
    output = tmp_path / "loibl_variance"
    manifest = comparison.run("loibl_variance", output, 1, "calibration")
    assert {item["status"] for item in manifest["attempts"]} == {
        "invalid_response",
        "review_needed",
    }
    assert manifest["status"] == "completed"
    assert manifest["protocol"]["pipeline_max_calls_per_attempt"] == 17
    assert manifest["protocol"]["resolved_model"] == "test-model"
    assert (
        output / "source_snapshot/scripts/run_pf_fresh_comparison.py"
    ).read_bytes() == comparison.Path(comparison.__file__).read_bytes()
    assert (
        "experiments/configs/pf_expert_direction_pilot_20260929/direct_prompt_no_examples.yaml"
    ) in manifest["source_hashes"]
    assert json.dumps(manifest["shared_context"], indent=2) in requests[0]
    assert len(list(output.glob("001/*/result.json"))) == 2
    with pytest.raises(FileExistsError):
        comparison.run("loibl_variance", output, 1, "calibration")
    comparison.render(tmp_path)
    page = (tmp_path / "side_by_side.html").read_text()
    assert "review_needed" in page
    assert "invalid_response" in page
    assert "not a complete original numerical table" in page
    packet = comparison.prepare_review(tmp_path)
    assert len(packet) == 2
    assert all("method" not in entry for entry in packet.values())
    assert all("status" not in entry for entry in packet.values())
    assert len(json.loads((tmp_path / "review_key.json").read_text())) == 2


def test_independent_math_uses_exact_values_and_enumerates_allocations(tmp_path):
    comparison.save(tmp_path / "source.json", {"source": "illustrative software test"})
    comparison.save(
        tmp_path / "numeric_inputs.json",
        {
            "spread": {"kind": "spread", "source": "source.json", "values": {"A": [1, 2, 3]}},
            "speed": {
                "kind": "speed",
                "source": "source.json",
                "values": {
                    "A": {
                        "distances_km": ["0.1", "0.2"],
                        "moving_minutes": [1, 2],
                        "waiting_minutes": 3,
                    }
                },
            },
            "allocation": {
                "kind": "indivisible_allocation",
                "source": "source.json",
                "values": [[3, 1], [1, 3]],
            },
        },
    )
    results = comparison.verify_math(tmp_path)["results"]
    assert results["spread"]["computed"]["A"]["population_variance"] == "2/3"
    assert results["speed"]["computed"]["A"]["overall_km_per_hour"] == "3"
    assert results["allocation"]["computed"]["fair_allocations"] == 1
    assert results["allocation"]["computed"]["allocations_enumerated"] == 4
    assert (tmp_path / "independent_math.json").is_file()


def test_produced_flagged_pipeline_task_is_counted_and_rendered(tmp_path):
    output = tmp_path / "fresh" / "loibl_variance"
    task = {
        "status": "ready",
        "title": "Illustrative test task",
        "body": "Use the supplied data.",
        "question": "Invent a measure.",
        "quality_status": "review_needed",
        "quality_findings": ["Unresolved <condition>"],
        "writer_attempts": [],
        "withheld": [],
    }
    comparison.save(output / "001/pipeline/result.json", {
        "status": "completed", "stages": {"D2_D3": {"task": task}},
    })
    comparison.save(output / "manifest.json", {
        "case_name": "loibl_variance",
        "attempts": [{
            "number": 1, "method": "pipeline", "status": "completed",
            "path": "001/pipeline/result.json",
        }],
    })
    assert comparison.task_is_produced(task)
    assert not comparison.task_is_produced({**task, "body": " "})
    assert not comparison.task_is_produced({**task, "status": "blocked"})
    report = comparison.summarize(tmp_path)
    assert report["phases"]["fresh"]["outcomes"]["pipeline/delivered"] == 1
    comparison.render(tmp_path / "fresh")
    page = (tmp_path / "fresh/side_by_side.html").read_text()
    assert task["title"] in page
    assert "Unresolved &lt;condition&gt;" in page


def test_review_counts_keep_unknown_separate_from_supported_choice():
    supported = {
        "mathematics_status": "supported", "target": "preserved",
        "accessible_start": "yes", "disclosure": "none", "consequential_choice": "yes",
    }
    counts = reporting.outcome_counts({
        "first": supported, "second": {**supported, "mathematics_status": "unknown"},
        "third": {**supported, "target": "narrowed"},
    })
    assert counts["attempted"] == 3
    assert counts["mathematics_status/unknown"] == 1
    assert counts["supported_undisclosed_choice"] == 1
    with pytest.raises(ValueError, match="Unknown mathematics_status"):
        reporting.outcome_counts({"bad": {**supported, "mathematics_status": "accepted"}})
