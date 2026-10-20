"""Rate frozen PF writer outputs; never regenerate exercises or student responses."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAIError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prior_methods.common import MODEL_ENVS, chat_json, load_client  # noqa: E402
from scripts.run_pf_diagnostic import _determine_effective_settings  # noqa: E402
from src.evaluation.pf_rubric import (  # noqa: E402
    PROMPT_PATH,
    judge_input,
    load_prompt,
    parse_rating,
    student_task_text,
)

SETTINGS = {"temperature": 0.0, "max_tokens": 4000}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_saved_cases(audit_path: Path, case_ids: list[str], root: Path = ROOT) -> list[dict]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not case_ids or len(set(case_ids)) != len(case_ids):
        raise ValueError("Select at least one case, without duplicate case IDs")
    cases = []
    for case_id in case_ids:
        matches = [entry for entry in audit["cases"] if entry["case_id"] == case_id]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one saved comparison case: {case_id}")
        source = (root / matches[0]["replay_result"]).resolve()
        source_bytes = source.read_bytes()
        record = json.loads(source_bytes)
        if record["case_id"] != case_id:
            raise ValueError(f"Saved result case ID mismatch: {source}")
        cases.append(
            {
                "case_id": case_id,
                "kind": "saved_pipeline_task",
                "source": str(source),
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "user_prompt": judge_input(
                    student_task_text(record["task"]),
                    record["new_writer_context"]["student_context"],
                ),
            }
        )
    return cases


def load_controls(path: Path) -> list[dict]:
    source_bytes = path.read_bytes()
    controls = json.loads(source_bytes)
    return [
        {
            "case_id": entry["case_id"],
            "kind": "synthetic_control_not_human_rated",
            "source": str(path.resolve()),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "control_purpose": entry["purpose"],
            "user_prompt": judge_input(entry["student_task"], entry["learner_context"]),
        }
        for entry in controls
    ]


def rate_case(client, model: str, system: str, user: str, *, chat=chat_json) -> dict:
    """Return explicit failures, retaining raw responses rather than assigning zero."""
    try:
        _, raw = chat(client, model, system, user, **SETTINGS)
    except OpenAIError as exc:
        return {
            "status": "api_error",
            "scores": None,
            "raw_response": None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    try:
        return {**parse_rating(raw), "raw_response": raw}
    except ValidationError as exc:
        return {
            "status": "invalid_response",
            "scores": None,
            "raw_response": raw,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }


def run_cases(
    cases: list[dict],
    output: Path,
    *,
    selector: str = "luna",
    dry_run: bool = False,
    client_loader=load_client,
    chat=chat_json,
) -> dict:
    if selector not in MODEL_ENVS:
        raise ValueError(f"Unknown model selector: {selector}")
    case_ids = [case["case_id"] for case in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise ValueError("Case IDs must be nonempty and unique")
    prompt = load_prompt()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "pf-judge-run/v1",
        "status": "prepared" if dry_run else "starting",
        "scope": "Automated smoke check; not human calibration or a full benchmark.",
        "rubric_version": prompt["version"],
        "rubric_source": prompt["source"],
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                PROMPT_PATH,
                ROOT / "src/evaluation/pf_rubric.py",
                Path(__file__).resolve(),
                ROOT / "scripts/prior_methods/common.py",
                ROOT / "scripts/run_pf_diagnostic.py",
            )
        },
        "system_prompt": prompt["system"],
        "model_selector": selector,
        "requested_settings": SETTINGS,
        "case_count": len(cases),
        "created_at": _now(),
        "cases": cases,
    }
    _write_json(output / "manifest.json", manifest)
    if dry_run:
        return manifest
    client, model = client_loader(selector)
    manifest.update(
        {
            "status": "running",
            "model_name": model,
            "effective_settings": {
                **_determine_effective_settings(model, SETTINGS),
                "response_format": {"type": "json_object"},
                "timeout": 180,
            },
            "settings_note": "GPT-5 adapter omits temperature. API usage metadata unavailable.",
        }
    )
    _write_json(output / "manifest.json", manifest)
    results = []
    with (output / "ratings.jsonl").open("x", encoding="utf-8") as stream:
        for case in cases:
            started = _now()
            rating = rate_case(client, model, prompt["system"], case["user_prompt"], chat=chat)
            result = {
                **case,
                "started_at": started,
                "finished_at": _now(),
                "model_name": model,
                "rubric_version": prompt["version"],
                **rating,
            }
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            results.append(result)
            print(f"{case['case_id']}: {rating['status']} {rating['scores']}", flush=True)
            if "error" in rating:
                print(f"  {rating['error']['type']}: {rating['error']['message']}", flush=True)
    summary = {
        "attempted": len(results),
        "scored": sum(result["status"] == "scored" for result in results),
        "insufficient_evidence": sum(
            result["status"] == "insufficient_evidence" for result in results
        ),
        "failed": sum(result["scores"] is None for result in results),
        "ratings": [
            {
                "case_id": result["case_id"],
                "kind": result["kind"],
                "status": result["status"],
                "scores": result["scores"],
            }
            for result in results
        ],
        "limitation": (
            "One rating per task; controls are synthetic and not human-rated. "
            "No agreement, repeatability, student outcomes, or comparison with paper means tested."
        ),
    }
    manifest["status"] = "completed_with_failures" if summary["failed"] else "completed"
    manifest["finished_at"] = _now()
    _write_json(output / "summary.json", summary)
    _write_json(output / "manifest.json", manifest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--model", choices=sorted(MODEL_ENVS), default="luna")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cases = load_saved_cases(args.audit, args.cases)
    if args.controls:
        cases.extend(load_controls(args.controls))
    result = run_cases(cases, args.output, selector=args.model, dry_run=args.dry_run)
    if result.get("failed", 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
