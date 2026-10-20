import hashlib
import json
from copy import deepcopy

import pytest
from openai import OpenAIError

from src.evaluation import pf_task_measures as measures
from src.utils.llm_client import LLMResponse

TASK = (
    "Two groups have scores A=[4,5,6] and B=[0,5,10]. "
    "Invent a consistency measure using all scores."
)
QUOTE = "Invent a consistency measure using all scores."
TARGET = "UNTAUGHT_TARGET: variability and spread"
CONTEXT = {
    "grade": 7,
    "subject": "mathematics",
    "assumed_prior_knowledge": [
        {"resource": "Mean", "taught_as": "Sum values and divide by their count."},
        {
            "resource": "Arithmetic",
            "taught_as": "Add, subtract, divide and take absolute differences.",
        },
    ],
}


def finding(status="supported", ids=None, verification="argument"):
    return {
        "status": status,
        "argument": "Explicit illustrative mathematical argument.",
        "verification": verification,
        "calculator_ids": ids or [],
    }


def approach(identifier, idea):
    return {
        "id": identifier,
        "method": idea,
        "mathematical_idea": idea,
        "worked_start": "The first mean is (4+5+6)/3=5.",
        "resource_indices": [0, 1],
        "support_argument": "Uses the declared arithmetic and mean.",
        "distinction_argument": "The underlying quantity differs from the alternative.",
        "task_quotes": [QUOTE],
    }


def judgments():
    base = {"verdict": "yes", "task_quotes": [QUOTE], "reasoning": "Illustrative test evidence."}
    return {
        "target_alignment": {
            **base,
            "target_quotes": ["variability and spread"],
            "addressed_elements": ["Compare variation"],
            "missing_elements": [],
        },
        "mathematical_validity": {
            **base,
            "interpretation": "Construct a consistency measure for the two lists.",
            "assumptions": [],
            "calculator_coverage": "Direct arguments in this software fixture.",
            "consistency": finding(),
            "feasibility": finding(),
            "justification": finding(),
        },
        "prior_knowledge_accessibility": {
            **base,
            "approaches": [
                approach("mean", "Central tendency"),
                approach("deviations", "Aggregate distances from a baseline"),
            ],
            "missing_knowledge": [],
            "inaccessibility_argument": "",
        },
        "familiar_approach_limits": {
            **base,
            "approach_reviews": [
                {
                    "approach_id": "mean",
                    "outcome": "limit",
                    "worked_attempt": "Both means equal 5.",
                    "reasoning": "Cannot distinguish spread.",
                    "limitation": "Equal means obscure variation.",
                    "target_resolution": "Compare distances from the mean.",
                    "task_quotes": [QUOTE],
                    "calculator_ids": [],
                },
                {
                    "approach_id": "deviations",
                    "outcome": "meets_demands",
                    "worked_attempt": "The absolute deviations total 2 and 10.",
                    "reasoning": "Uses all observations.",
                    "limitation": "",
                    "target_resolution": "",
                    "task_quotes": [QUOTE],
                    "calculator_ids": [],
                },
            ],
        },
        "room_for_invention": {
            **base,
            "supplied_construction": [],
            "remaining_construction": "A measure of spread.",
            "consequence_argument": "Different measures change what is compared.",
        },
    }


def final(judgment):
    return json.dumps({"action": "final", "judgment": judgment})


def calculation(expression="(4+5+6)/3", predicate="mean == 5", identifier="mean_check"):
    return json.dumps(
        {
            "action": "calculate",
            "checks": [
                {
                    "id": identifier,
                    "statement": "Check the candidate mean.",
                    "interpretation": "The first group's arithmetic mean.",
                    "task_quotes": [QUOTE],
                    "values": {},
                    "units": {},
                    "calculation": {
                        "expressions": {"mean": expression},
                        "predicate": predicate,
                        "symbols": {},
                    },
                }
            ],
        }
    )


class FakeChat:
    def __init__(self, responses=None):
        self.responses = responses or {
            name: [final(judgment)] for name, judgment in judgments().items()
        }
        self.calls = []

    def __call__(self, messages):
        self.calls.append(deepcopy(messages))
        name = next(
            role
            for role, contract in measures.load_rubric()["measures"].items()
            if messages[0]["content"].startswith(f"Measure: {contract['name']}.")
        )
        response = self.responses[name].pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, LLMResponse):
            return response
        return LLMResponse(text=response, model="mock-not-a-learner", finish_reason="stop")


def role_payload(role):
    prepared = measures.prepare_input(TASK, TARGET, CONTEXT)
    starts = judgments()["prior_knowledge_accessibility"]["approaches"]
    return measures.role_input(
        role, prepared, starts if role == "familiar_approach_limits" else None
    )


def test_frozen_value_sets_dependencies_and_prompts():
    rubric = measures.load_rubric()
    assert hashlib.sha256(measures.PROMPT_PATH.read_bytes()).hexdigest() == (
        "dced22cbab1a9659f7966dac1a5ca12d9d1b7c57d511cefe3e8f5682825d8c61"
    )
    assert rubric["status"] == "frozen-initial-not-calibrated"
    assert rubric["version"] == measures.VERSION
    for role, contract in rubric["measures"].items():
        assert set(contract["values"]) == set(contract["definitions"])
        assert ("partly" in contract["values"]) == (
            role in {"target_alignment", "room_for_invention"}
        )
        assert ("not_assessed" in contract["values"]) == (
            role in {"mathematical_validity", "familiar_approach_limits"}
        )
        assert contract["name"] in measures.system_prompt(role)
    assert rubric["measures"]["mathematical_validity"]["requires"] == {
        "measure": "target_alignment",
        "value": "yes",
    }
    assert rubric["measures"]["familiar_approach_limits"]["requires"] == {
        "measure": "prior_knowledge_accessibility",
        "value": "yes",
    }


def test_full_pipeline_preserves_mixed_outcomes_and_descriptive_counts():
    chat = FakeChat()
    result = measures.PFTaskMeasuresEvaluator(chat).evaluate(TASK, TARGET, CONTEXT)
    assert all(record["status"] == "assessed" for record in result["measures"].values())
    assert result["measures"]["familiar_approach_limits"]["value"] == "yes"
    assert result["approach_counts"] | {"scope": ""} == {
        "identified_starts": 2,
        "reviewed": 2,
        "with_limits": 1,
        "meets_demands": 1,
        "unresolved": 0,
        "scope": "",
    }
    assert len(chat.calls) == 5
    assert result["calibrated"] is False
    assert len(result["rubric_sha256"]) == len(result["input_sha256"]) == 64
    assert "TOTAL" not in result


@pytest.mark.parametrize("value", ["partly", "no", "unclear"])
def test_alignment_dependency_skips_only_mathematics(value):
    responses = judgments()
    responses["target_alignment"]["verdict"] = value
    if value == "partly":
        responses["target_alignment"]["missing_elements"] = ["Another explicitly required element"]
    chat = FakeChat({name: [final(item)] for name, item in responses.items()})
    result = measures.PFTaskMeasuresEvaluator(chat).evaluate(TASK, TARGET, CONTEXT)
    math = result["measures"]["mathematical_validity"]
    assert math["value"] == math["status"] == "not_assessed"
    assert math["prerequisite"]["value"] == value
    assert math["calls"] == []
    assert result["measures"]["familiar_approach_limits"]["status"] == "assessed"
    assert result["measures"]["room_for_invention"]["status"] == "assessed"
    assert len(chat.calls) == 4


@pytest.mark.parametrize("value", ["no", "unclear"])
def test_accessibility_dependency_skips_only_approach_limits(value):
    responses = judgments()
    responses["prior_knowledge_accessibility"].update(
        {
            "verdict": value,
            "approaches": [],
            "missing_knowledge": ["An unavailable skill"] if value == "no" else [],
            "inaccessibility_argument": "Even a meaningful start needs that skill."
            if value == "no"
            else "",
        }
    )
    chat = FakeChat({name: [final(item)] for name, item in responses.items()})
    result = measures.PFTaskMeasuresEvaluator(chat).evaluate(TASK, TARGET, CONTEXT)
    assert result["measures"]["familiar_approach_limits"]["status"] == "not_assessed"
    assert result["measures"]["mathematical_validity"]["status"] == "assessed"
    assert result["measures"]["room_for_invention"]["status"] == "assessed"
    assert result["approach_counts"]["identified_starts"] == 0
    assert result["approach_counts"]["reviewed"] is None
    assert len(chat.calls) == 4


def test_allowlisting_and_prior_solver_target_boundary():
    context = deepcopy(CONTEXT)
    context["expected_errors"] = "SECRET_ERRORS"
    context["assumed_prior_knowledge"][0]["student_move"] = "SECRET_MOVE"
    task = {
        "title": "A task",
        "body": TASK,
        "question": QUOTE,
        "internal_example": "SECRET_SOLUTION",
    }
    chat = FakeChat()
    result = measures.PFTaskMeasuresEvaluator(chat).evaluate(task, TARGET, context)
    assert "SECRET" not in json.dumps(result["measures"])
    calls = [
        call
        for call in chat.calls
        if call[0]["content"].startswith("Measure: Prior-knowledge accessibility.")
    ]
    assert len(calls) == 1
    assert TARGET not in json.dumps(calls)
    assert "learning_target" not in json.loads(calls[0][1]["content"])
    for name, record in result["measures"].items():
        assert "verdict" not in record["input"]
        if name != "familiar_approach_limits":
            assert "approaches" not in record["input"]


def test_standalone_role_rejects_target_or_hidden_fields_before_calls():
    chat = FakeChat()
    payload = role_payload("prior_knowledge_accessibility") | {"learning_target": TARGET}
    with pytest.raises(ValueError, match="input must contain exactly"):
        measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
            "prior_knowledge_accessibility", payload
        )
    assert chat.calls == []


def test_history_that_would_be_lost_is_rejected():
    chat = FakeChat()
    with pytest.raises(ValueError, match="recently_taught would be discarded"):
        measures.PFTaskMeasuresEvaluator(chat).evaluate(
            TASK, TARGET, {"recently_taught": [{"resource": "Arithmetic"}]}
        )
    assert chat.calls == []


@pytest.mark.parametrize("verdict", ["yes", "no", "unclear"])
def test_mathematical_values_require_matching_findings(verdict):
    judgment = judgments()["mathematical_validity"]
    judgment["verdict"] = verdict
    if verdict == "no":
        judgment["consistency"] = finding("concern")
    elif verdict == "unclear":
        judgment["feasibility"] = finding("unresolved")
    chat = FakeChat({"mathematical_validity": [final(judgment)]})
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["value"] == verdict
    assert record["status"] == "assessed"


@pytest.mark.parametrize("verdict", ["yes", "partly", "no", "unclear"])
def test_invention_values(verdict):
    judgment = judgments()["room_for_invention"]
    judgment["verdict"] = verdict
    if verdict in {"partly", "no"}:
        judgment["supplied_construction"] = ["A stated central step"]
    chat = FakeChat({"room_for_invention": [final(judgment)]})
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "room_for_invention", role_payload("room_for_invention")
    )
    assert record["status"] == "assessed" and record["value"] == verdict


@pytest.mark.parametrize("verdict", ["yes", "no", "unclear"])
def test_approach_limit_values(verdict):
    judgment = judgments()["familiar_approach_limits"]
    judgment["verdict"] = verdict
    if verdict != "yes":
        for review in judgment["approach_reviews"]:
            review.update(
                {
                    "outcome": "meets_demands" if verdict == "no" else "unresolved",
                    "limitation": "",
                    "target_resolution": "",
                }
            )
    chat = FakeChat({"familiar_approach_limits": [final(judgment)]})
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "familiar_approach_limits", role_payload("familiar_approach_limits")
    )
    assert record["status"] == "assessed" and record["value"] == verdict


def test_math_calculator_exchange_preserves_requests_results_and_usage():
    judgment = judgments()["mathematical_validity"]
    judgment["consistency"] = finding(ids=["mean_check"], verification="calculator")
    chat = FakeChat({"mathematical_validity": [calculation(), final(judgment)]})
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["status"] == "assessed"
    assert len(chat.calls) == 2
    assert record["calculations"][0]["result"]["computed"]["mean"] == "5"
    assert record["calculations"][0]["result"]["status"] == "holds"
    returned = json.loads(chat.calls[1][-1]["content"])["calculator_results"]
    assert returned == record["calculations"]
    assert all(call["response"]["model"] == "mock-not-a-learner" for call in record["calls"])


@pytest.mark.parametrize(
    "expression,status", [("floor(3.08)", "unsupported"), ("missing", "unknown")]
)
def test_unsupported_or_missing_calculations_remain_unclear(expression, status):
    judgment = judgments()["mathematical_validity"]
    judgment.update(
        {"verdict": "unclear", "consistency": finding("unresolved", ["mean_check"], "calculator")}
    )
    chat = FakeChat(
        {
            "mathematical_validity": [
                calculation(expression=expression),
                final(judgment),
            ]
        }
    )
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["value"] == "unclear"
    assert record["calculations"][0]["result"]["status"] == status


def test_unsupported_calculator_alone_cannot_claim_validity():
    judgment = judgments()["mathematical_validity"]
    judgment["consistency"] = finding(ids=["mean_check"], verification="calculator")
    chat = FakeChat(
        {
            "mathematical_validity": [
                calculation(expression="floor(3.08)"),
                final(judgment),
            ]
        }
    )
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["status"] == "invalid_response" and record["value"] is None
    assert len(record["calls"]) == 2


def test_false_candidate_predicate_does_not_automatically_invalidate_task():
    chat = FakeChat(
        {
            "mathematical_validity": [
                calculation(predicate="mean == 7"),
                final(judgments()["mathematical_validity"]),
            ]
        }
    )
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["calculations"][0]["result"]["status"] == "fails"
    assert record["value"] == "yes"


def test_model_budget_is_explicit_without_retries():
    chat = FakeChat({"mathematical_validity": [calculation()]})
    record = measures.PFTaskMeasuresEvaluator(chat, max_calls=1).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["status"] == "budget_exhausted" and record["value"] is None
    assert len(chat.calls) == len(record["calculations"]) == 1


def test_calculator_budget_is_cumulative():
    chat = FakeChat(
        {
            "mathematical_validity": [
                calculation(),
                calculation(identifier="second"),
            ]
        }
    )
    record = measures.PFTaskMeasuresEvaluator(chat, max_calculations=1).evaluate_role(
        "mathematical_validity", role_payload("mathematical_validity")
    )
    assert record["status"] == "budget_exhausted"
    assert len(record["calculations"]) == 1
    assert len(chat.calls) == 2


@pytest.mark.parametrize("bad", ["not JSON", json.dumps([])])
def test_parse_failure_is_execution_failure_not_unclear(bad):
    responses = {name: [final(item)] for name, item in judgments().items()}
    responses["target_alignment"] = [bad]
    chat = FakeChat(responses)
    result = measures.PFTaskMeasuresEvaluator(chat).evaluate(TASK, TARGET, CONTEXT)
    alignment = result["measures"]["target_alignment"]
    assert alignment["status"] == "invalid_response" and alignment["value"] is None
    assert alignment["calls"][0]["response"]["text"] == bad
    assert result["measures"]["mathematical_validity"]["value"] == "not_assessed"
    assert result["measures"]["room_for_invention"]["status"] == "assessed"


def test_api_failure_retains_other_roles_and_explicit_skip_reason(caplog):
    responses = {name: [final(item)] for name, item in judgments().items()}
    responses["target_alignment"] = [OpenAIError("Connection failed")]
    result = measures.PFTaskMeasuresEvaluator(FakeChat(responses)).evaluate(TASK, TARGET, CONTEXT)
    assert result["measures"]["target_alignment"]["status"] == "api_error"
    assert result["measures"]["target_alignment"]["value"] is None
    assert result["measures"]["mathematical_validity"]["prerequisite"]["status"] == "api_error"
    assert result["measures"]["prior_knowledge_accessibility"]["status"] == "assessed"
    assert "Connection failed" in caplog.text


def test_truncated_even_parseable_output_is_an_execution_limit():
    chat = FakeChat(
        {
            "target_alignment": [
                LLMResponse(text=final(judgments()["target_alignment"]), finish_reason="length")
            ]
        }
    )
    record = measures.PFTaskMeasuresEvaluator(chat).evaluate_role(
        "target_alignment", role_payload("target_alignment")
    )
    assert record["status"] == "truncated" and record["value"] is None


@pytest.mark.parametrize("role", measures.MEASURES)
def test_unanchored_quotes_are_rejected(role):
    judgment = judgments()[role]
    judgment["task_quotes"] = ["This quotation does not exist."]
    record = measures.PFTaskMeasuresEvaluator(FakeChat({role: [final(judgment)]})).evaluate_role(
        role, role_payload(role)
    )
    assert record["status"] == "invalid_response" and record["value"] is None


def test_limits_must_preserve_successful_approach():
    judgment = judgments()["familiar_approach_limits"]
    judgment["approach_reviews"].pop()
    record = measures.PFTaskMeasuresEvaluator(
        FakeChat({"familiar_approach_limits": [final(judgment)]})
    ).evaluate_role("familiar_approach_limits", role_payload("familiar_approach_limits"))
    assert record["status"] == "invalid_response"


@pytest.mark.parametrize("change", ["resource", "duplicate", "missing_history"])
def test_accessibility_evidence_boundaries(change):
    judgment = judgments()["prior_knowledge_accessibility"]
    payload = role_payload("prior_knowledge_accessibility")
    if change == "resource":
        judgment["approaches"][0]["resource_indices"] = [99]
    elif change == "duplicate":
        judgment["approaches"][1]["mathematical_idea"] = judgment["approaches"][0][
            "mathematical_idea"
        ]
    else:
        payload["learner_context"]["assumed_prior_knowledge"] = None
    record = measures.PFTaskMeasuresEvaluator(
        FakeChat({"prior_knowledge_accessibility": [final(judgment)]})
    ).evaluate_role("prior_knowledge_accessibility", payload)
    assert record["status"] == "invalid_response" and record["value"] is None


@pytest.mark.parametrize(
    "role", ["mathematical_validity", "prior_knowledge_accessibility", "familiar_approach_limits"]
)
def test_partly_is_not_available_for_other_measures(role):
    judgment = judgments()[role]
    judgment["verdict"] = "partly"
    record = measures.PFTaskMeasuresEvaluator(FakeChat({role: [final(judgment)]})).evaluate_role(
        role, role_payload(role)
    )
    assert record["status"] == "invalid_response"


def test_non_math_role_cannot_request_calculator():
    record = measures.PFTaskMeasuresEvaluator(
        FakeChat({"target_alignment": [calculation()]})
    ).evaluate_role("target_alignment", role_payload("target_alignment"))
    assert record["status"] == "invalid_response"
    assert record["calculations"] == []


def test_summary_keeps_conditional_denominators_and_errors_separate():
    first = measures.PFTaskMeasuresEvaluator(FakeChat()).evaluate(TASK, TARGET, CONTEXT)
    responses = {name: [final(item)] for name, item in judgments().items()}
    responses["target_alignment"] = [OpenAIError("Connection failed")]
    responses["prior_knowledge_accessibility"] = ["not JSON"]
    second = measures.PFTaskMeasuresEvaluator(FakeChat(responses)).evaluate(TASK, TARGET, CONTEXT)
    summary = measures.summarize([first, second])
    assert summary["tasks"] == 2 and summary["failed_role_executions"] == 2
    assert summary["measures"]["target_alignment"]["eligible_tasks"] == 2
    assert summary["measures"]["mathematical_validity"]["eligible_tasks"] == 1
    assert summary["measures"]["familiar_approach_limits"]["eligible_tasks"] == 1
    assert summary["measures"]["room_for_invention"]["assessed_tasks"] == 2
    assert summary["measures"]["target_alignment"]["value_counts"]["unclear"] == 0
    assert summary["measures"]["mathematical_validity"]["not_assessed_reasons"] == {
        "api_error:no_verdict": 1
    }
    assert second["approach_counts"]["identified_starts"] is None
    assert "TOTAL" not in summary


def test_saved_case_dry_run_makes_no_client_and_preserves_rubric(tmp_path):
    from scripts.run_pf_task_measures import run_cases

    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "private-id",
                        "student_task": TASK,
                        "learning_target": TARGET,
                        "learner_context": CONTEXT,
                        "reference_judgments": {"SECRET_LABEL": "yes"},
                    }
                ]
            }
        )
    )
    output = tmp_path / "prepared"

    def no_client(_):
        pytest.fail("Dry run must not load a model client")

    manifest = run_cases(source, output, dry_run=True, client_loader=no_client)
    assert manifest["status"] == "prepared" and manifest["calibrated"] is False
    assert "SECRET_LABEL" not in json.dumps(manifest["cases"])
    assert (output / "rubric_snapshot.yaml").read_bytes() == measures.PROMPT_PATH.read_bytes()
    assert not (output / "summary.json").exists()
    with pytest.raises(FileExistsError):
        run_cases(source, output, dry_run=True, client_loader=no_client)


def test_case_loader_rejects_duplicates_and_leaky_history(tmp_path):
    from scripts.run_pf_task_measures import load_cases

    source = tmp_path / "cases.json"
    entry = {
        "case_id": "one",
        "student_task": TASK,
        "learning_target": TARGET,
        "learner_context": CONTEXT,
    }
    source.write_text(json.dumps([entry, entry]))
    with pytest.raises(ValueError, match="unique"):
        load_cases(source)
    entry["learner_context"] = {"recently_taught": [{"resource": "Mean"}]}
    source.write_text(json.dumps([entry]))
    with pytest.raises(ValueError, match="recently_taught"):
        load_cases(source)


def test_runner_retains_failure_and_uses_zero_retry_adapter(tmp_path):
    from types import SimpleNamespace

    from scripts.run_pf_task_measures import run_cases

    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            [
                {
                    "case_id": "one",
                    "task": {"title": "Task", "body": TASK, "question": QUOTE},
                    "learning_target": TARGET,
                    "learner_context": CONTEXT,
                }
            ]
        )
    )
    replies = {name: [final(item)] for name, item in judgments().items()}
    replies["target_alignment"] = [OpenAIError("API failed")]
    fake = FakeChat(replies)

    class API:
        def __init__(self):
            self.chat = SimpleNamespace(completions=self)
            self.options = None
            self.settings = []

        def with_options(self, **kwargs):
            self.options = kwargs
            return self

        def create(self, **kwargs):
            self.settings.append(kwargs)
            response = fake(kwargs["messages"])
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=response.text),
                        finish_reason=response.finish_reason,
                    )
                ],
                model=response.model,
                usage=None,
            )

    api = API()
    output = tmp_path / "run"
    summary = run_cases(source, output, client_loader=lambda _: (api, "gpt-5.6-luna"))
    assert api.options == {"max_retries": 0, "timeout": 180}
    assert summary["failed_role_executions"] == 1
    assert summary["measures"]["mathematical_validity"]["eligible_tasks"] == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed_with_failures"
    record = json.loads((output / "case_0001.json").read_text())
    assert record["measures"]["target_alignment"]["error"]["message"] == "API failed"
    assert record["measures"]["room_for_invention"]["calls"][0]["response"]["usage"] == {
        "prompt_tokens": None,
        "completion_tokens": None,
    }
    assert all("temperature" not in settings for settings in api.settings)
    assert all(settings["max_completion_tokens"] == 6000 for settings in api.settings)


@pytest.mark.parametrize(
    "kwargs", [{"max_calls": 0}, {"max_calls": 4}, {"max_calls": True}, {"max_calculations": 17}]
)
def test_execution_budgets_are_strict_and_bounded(kwargs):
    with pytest.raises(ValueError):
        measures.PFTaskMeasuresEvaluator(FakeChat(), **kwargs)


def test_frozen_rubric_cannot_be_edited_in_place(tmp_path, monkeypatch):
    path = tmp_path / "changed.yaml"
    path.write_bytes(measures.PROMPT_PATH.read_bytes() + b"\n# changed\n")
    monkeypatch.setattr(measures, "PROMPT_PATH", path)
    with pytest.raises(ValueError, match="new instrument version"):
        measures.load_rubric()


def test_cli_exit_code_reports_execution_failures(monkeypatch, capsys):
    from scripts import run_pf_task_measures as runner

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_pf_task_measures",
            "--cases",
            "cases.json",
            "--output",
            "unused",
        ],
    )
    monkeypatch.setattr(
        runner,
        "run_cases",
        lambda *args, **kwargs: {
            "failed_role_executions": 1,
        },
    )
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 1
    assert "completed_with_failures" in capsys.readouterr().out
