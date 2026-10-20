"""Run the frozen five-measure evaluator on saved tasks, or prepare a no-call dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prior_methods.common import MODEL_ENVS, load_client  # noqa: E402
from scripts.run_pf_diagnostic import _determine_effective_settings  # noqa: E402
from src.evaluation.pf_task_measures import (  # noqa: E402
    MEASURES,
    PROMPT_PATH,
    VERSION,
    EvaluationLimits,
    PFTaskMeasuresEvaluator,
    prepare_input,
    summarize,
    system_prompt,
)
from src.utils.llm_client import LLMResponse  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list) or not cases:
        raise ValueError("Input must contain a nonempty list of saved cases")
    prepared = []
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each saved case must be an object")
        identifier = case.get("case_id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValueError("Case ids must be nonempty and unique")
        ids.add(identifier)
        if ("student_task" in case) == ("task" in case):
            raise ValueError("Each case requires exactly one of student_task or task")
        input_data = prepare_input(
            case.get("student_task", case.get("task")),
            case.get("learning_target"),
            case.get("learner_context"),
        )
        prepared.append({"case_id": identifier, "input": input_data})
    return prepared


def make_chat(client, model: str, settings: dict):
    api = client.with_options(max_retries=0, timeout=180)

    def chat(messages: list[dict[str, str]]) -> LLMResponse:
        response = api.chat.completions.create(
            model=model, messages=messages, response_format={"type": "json_object"}, **settings
        )
        choice = response.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason or "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
            },
        )

    return chat


def run_cases(
    source: Path,
    output: Path,
    *,
    selector: str = "luna",
    model: str | None = None,
    dry_run: bool = False,
    max_tokens: int = 6000,
    max_calls: int = 3,
    max_calculations: int = 16,
    reasoning_effort: str | None = None,
    client_loader=load_client,
) -> dict:
    if selector not in MODEL_ENVS:
        raise ValueError(f"Unknown model selector: {selector}")
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise ValueError("An explicit model override must be nonempty text")
    if reasoning_effort not in {None, "low", "medium", "high"}:
        raise ValueError("Unknown reasoning effort")
    limits = EvaluationLimits(max_calls=max_calls, max_calculations=max_calculations)
    cases = load_cases(source)
    output.mkdir(parents=True, exist_ok=False)
    source_paths = (
        PROMPT_PATH,
        ROOT / "src/evaluation/pf_task_measures.py",
        ROOT / "src/evaluation/pf_evidence_audit.py",
        ROOT / "src/evaluation/pf_rubric.py",
        ROOT / "src/generation/design_calculator.py",
        ROOT / "src/generation/fill_check.py",
        ROOT / "src/utils/llm_client.py",
        Path(__file__).resolve(),
        ROOT / "scripts/prior_methods/common.py",
        ROOT / "scripts/run_pf_diagnostic.py",
    )
    manifest = {
        "version": VERSION,
        "status": "prepared" if dry_run else "starting",
        "calibrated": False,
        "scope": "Task judgments only; no generation or learner study.",
        "source_file": str(source.resolve()),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "code_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        "judge_selector": selector,
        "model_requested": model,
        "requested_settings": {"max_tokens": max_tokens, "reasoning_effort": reasoning_effort},
        "execution_limits": limits.model_dump(),
        "api_retries": 0,
        "created_at": _now(),
        "cases": cases,
        "system_prompts": {role: system_prompt(role, **limits.model_dump()) for role in MEASURES},
    }
    (output / "rubric_snapshot.yaml").write_bytes(PROMPT_PATH.read_bytes())
    _write(output / "manifest.json", manifest)
    if dry_run:
        return manifest
    client, configured_model = client_loader(selector)
    deployment = model or configured_model
    settings = (
        {"max_completion_tokens": max_tokens}
        if deployment.startswith(("gpt-6", "o4"))
        else _determine_effective_settings(
            deployment, {"temperature": 0.0, "max_tokens": max_tokens}
        )
    )
    if reasoning_effort is not None:
        settings["reasoning_effort"] = reasoning_effort
    manifest.update(
        {
            "status": "running",
            "model_requested": deployment,
            "effective_settings": settings,
        }
    )
    _write(output / "manifest.json", manifest)
    evaluator = PFTaskMeasuresEvaluator(
        make_chat(client, deployment, settings), **limits.model_dump()
    )
    results = []
    for index, case in enumerate(cases, 1):
        inputs = case["input"]
        result = {
            "case_id": case["case_id"],
            "started_at": _now(),
            **evaluator.evaluate(
                inputs["student_task"], inputs["learning_target"], inputs["learner_context"]
            ),
            "finished_at": _now(),
        }
        _write(output / f"case_{index:04d}.json", result)
        results.append(result)
        print(
            f"{case['case_id']}: "
            + ", ".join(
                f"{role}={row['value'] or row['status']}"
                for role, row in result["measures"].items()
            ),
            flush=True,
        )
    summary = summarize(results)
    _write(output / "summary.json", summary)
    manifest.update(
        {
            "status": "completed_with_failures"
            if summary["failed_role_executions"]
            else "completed",
            "finished_at": _now(),
        }
    )
    _write(output / "manifest.json", manifest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--judge", choices=sorted(MODEL_ENVS), default="luna")
    parser.add_argument("--model", help="Optional explicit deployment override.")
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--max-calls", type=int, choices=range(1, 4), default=3)
    parser.add_argument("--max-calculations", type=int, choices=range(1, 17), default=16)
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    result = run_cases(
        args.cases,
        args.output,
        selector=args.judge,
        model=args.model,
        dry_run=args.dry_run,
        max_tokens=args.max_tokens,
        max_calls=args.max_calls,
        max_calculations=args.max_calculations,
        reasoning_effort=args.reasoning_effort,
    )
    print(
        json.dumps(
            {
                "status": result.get(
                    "status",
                    "completed_with_failures"
                    if result.get("failed_role_executions")
                    else "completed",
                ),
                "version": VERSION,
                "calibrated": False,
            },
            indent=2,
        )
    )
    if result.get("failed_role_executions"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
