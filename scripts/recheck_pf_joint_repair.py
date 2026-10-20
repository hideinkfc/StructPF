#!/usr/bin/env python3
"""Recheck Productive Failure generalized bounded joint repair on saved diagnostic cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_situation_skeletons as d2_runner  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.run_pf_diagnostic import (  # noqa: E402
    DiagnosticTracer,
    _traced_chat,
    compute_source_hashes,
    trace_summary,
)
from src.generation.situation_skeletons import (  # noqa: E402
    judge_selection_from_payload,
    number_requirements_from_payload,
    rank_candidates,
    selected_candidate,
    verdicts_from_payload,
)


def _compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _matches_filter(case_dir: Path, filter_term: str) -> bool:
    term = filter_term.strip().lower()
    if not term:
        return False
    norm_term = term.replace(" ", "_")
    dir_name = case_dir.name.lower()
    if norm_term in dir_name or norm_term.rstrip("s") in dir_name:
        return True
    if term in dir_name or term.rstrip("s") in dir_name:
        return True
    for json_file in ("input.json", "result.json"):
        fp = case_dir / json_file
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Saved case metadata must be an object: {fp}")
            case_input = data.get("case_input")
            if not isinstance(case_input, dict):
                case_input = {}
            cid = str(data.get("case_id") or data.get("id") or "").lower()
            topic = str(data.get("topic") or case_input.get("topic") or "").lower()
            target_concept = str(
                data.get("target_concept") or case_input.get("target_concept") or ""
            ).lower()
            if (
                norm_term in cid
                or norm_term.rstrip("s") in cid
                or term in topic
                or term.rstrip("s") in topic
                or term in target_concept
                or term.rstrip("s") in target_concept
            ):
                return True
    return False


def _parse_saved_chat_json(raw_text: object) -> object:
    """Match common.chat_json's direct and embedded-object parsing."""
    if not isinstance(raw_text, str) or not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start, end = raw_text.find("{"), raw_text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _saved_proposal_input(proposal: object) -> tuple[object, object, bool]:
    """Recover a saved proposal without changing its raw provenance."""
    if not isinstance(proposal, dict):
        raise ValueError("Saved proposal record must be an object")
    raw_text = proposal.get("raw_text", "")
    is_empty = not isinstance(raw_text, str) or not raw_text.strip()
    if "payload" in proposal:
        return proposal["payload"], raw_text, is_empty
    if "skeleton" in proposal:
        return proposal["skeleton"], raw_text, is_empty
    payload = _parse_saved_chat_json(raw_text)
    return payload, raw_text, is_empty


def _select_saved_candidates(
    judge_payload: object,
    skeletons: list[Any],
    prior_context: dict[str, Any],
) -> list[Any]:
    """Convert either current compact or legacy judge output to candidates."""
    if not isinstance(judge_payload, dict):
        raise ValueError("unparseable judge response")
    selection = judge_selection_from_payload(judge_payload, set(range(len(skeletons))))
    if selection is not None:
        return selected_candidate(skeletons, selection)
    if not isinstance(judge_payload.get("candidates"), list):
        raise ValueError("judge response must contain recommended_id or candidates")
    approach_ids = {
        idx: {app.id for app in skeleton.approaches} for idx, skeleton in enumerate(skeletons)
    }
    verdicts = verdicts_from_payload(
        judge_payload,
        d2_runner._method_names(prior_context),
        approach_ids,
    )
    requirements = number_requirements_from_payload(judge_payload)
    return rank_candidates(skeletons, verdicts, requirements)


def find_case_dirs(source_root: Path, case_filters: list[str] | None = None) -> list[Path]:
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")

    candidates = [
        p
        for p in sorted(source_root.iterdir())
        if p.is_dir() and not p.name.startswith(".") and (p / "result.json").exists()
    ]
    if not case_filters:
        return candidates

    return [cand for cand in candidates if any(_matches_filter(cand, f) for f in case_filters)]


def _run_planning_fill_task(
    client: Any,
    model_name: str,
    prompts: dict[str, str],
    case: dict[str, Any],
    winner: Any,
    prior_context: dict[str, Any],
    initial_plan_payload: dict[str, Any] | None,
    stage: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    planning = d2_runner._plan_until_reviewed(
        client,
        model_name,
        prompts,
        case,
        winner,
        prior_context,
        require_v2=True,
        initial_plan_payload=initial_plan_payload,
    )
    plan = planning.get("plan")
    original_winner_obj = (
        planning.get("original_winner") if planning.get("original_winner") is not None else winner
    )
    effective_winner = planning.get("winner") if planning.get("winner") is not None else winner
    review = planning.get("plan_review")
    stage.update(
        original_winner=(
            original_winner_obj.to_dict()
            if hasattr(original_winner_obj, "to_dict")
            else original_winner_obj
        ),
        design_repair_attempts=list(planning.get("design_repair_attempts", [])),
        math_plan=None if plan is None else plan.to_dict(),
        plan_payload=planning.get("plan_payload"),
        plan_raw_text=planning.get("plan_raw_text", ""),
        plan_review=planning.get("plan_review"),
        plan_review_raw_text=planning.get("plan_review_raw_text", ""),
        plan_review_prompts=planning.get("plan_review_prompts"),
        plan_attempts=planning.get("attempts", []),
        plan_error=planning.get("error"),
    )
    effective_winner_dict = (
        effective_winner.to_dict() if hasattr(effective_winner, "to_dict") else effective_winner
    )
    stage["winners"] = [effective_winner_dict]

    if stage["plan_attempts"]:
        stage["plan_stop_stage"] = stage["plan_attempts"][-1].get("stage")

    if plan is None:
        result["status"] = {
            "structure": "plan_blocked",
            "expression": "expression_blocked",
            "meaning_review": "review_blocked",
        }.get(stage.get("plan_stop_stage"), "plan_blocked")
        stage["status"] = result["status"]
        result["error"] = stage["plan_error"]
        return result

    if not d2_runner._review_passes(review):
        stage["status"] = "review_blocked"
        result["status"] = "review_blocked"
        result["error"] = stage["plan_error"] or "plan review did not pass"
        return result

    fill = d2_runner._fill_until_accepted(
        client,
        model_name,
        prompts,
        case,
        effective_winner,
        plan,
        prior_context,
        plan_review=review,
    )
    stage["fill"] = fill
    if not fill.get("accepted"):
        stage["status"] = "fill_not_accepted"
        result["status"] = "fill_not_accepted"
        result["error"] = fill.get("error")
        return result

    task, task_raw = d2_runner._write_task(
        client,
        model_name,
        prompts,
        case,
        effective_winner,
        plan,
        fill["payload"],
        prior_context,
        review,
    )
    stage["task"] = task
    stage["task_raw_text"] = task_raw
    if not isinstance(task, dict) or task.get("status") != "ready":
        stage["status"] = "task_blocked"
        result["status"] = "task_blocked"
        result["error"] = (
            task.get("error") if isinstance(task, dict) else "Task payload was not an object"
        )
        return result

    stage["status"] = "completed"
    result["status"] = "completed"
    return result


def recheck_case(
    case_dir: Path,
    out_case_dir: Path,
    client: Any,
    model_selector: str,
    model_name: str,
    prompts: dict[str, str],
    source_root: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    if hasattr(client, "with_options"):
        client = client.with_options(max_retries=0)
    source_result_path = case_dir / "result.json"
    source_result_sha256 = _compute_sha256(source_result_path)
    source_result = json.loads(source_result_path.read_text(encoding="utf-8"))

    input_path = case_dir / "input.json"
    if not input_path.is_file():
        raise ValueError(f"Saved input artifact is missing: {input_path}")
    case = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(case, dict):
        raise ValueError(f"Saved input artifact must be an object: {input_path}")
    case_id = case["id"]
    saved_case_id = source_result.get("case_id")
    if saved_case_id is not None and saved_case_id != case_id:
        raise ValueError(
            f"Saved result case_id {saved_case_id!r} disagrees with input id {case_id!r}"
        )

    d1_path = case_dir / "d1.json"
    if not d1_path.is_file():
        raise ValueError(f"Saved D1 artifact is missing: {d1_path}")
    if "prior_context" not in source_result:
        raise ValueError("Saved result is missing frozen prior_context")
    prior_context = source_result["prior_context"]
    if not isinstance(prior_context, dict):
        raise ValueError("Saved result prior_context must be an object")

    # recheck_case may have created this directory before a later
    # validation/tracing failure; this output root was just created.
    out_case_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(input_path, out_case_dir / "input.json")
    shutil.copy2(d1_path, out_case_dir / "d1.json")
    shutil.copy2(source_result_path, out_case_dir / "source_result.json")

    trace_file = out_case_dir / "model_calls.jsonl"
    tracer = DiagnosticTracer(trace_file, case_id, default_model=model_name)

    source_d2 = source_result.get("stages", {}).get("D2_D3")
    if not isinstance(source_d2, dict):
        source_d2 = source_result.get("d2")
    if not isinstance(source_d2, dict):
        raise ValueError("Saved result is missing D2_D3 stage")
    source_status = source_result.get("status")

    is_no_valid_proposals = source_status == "no_valid_proposals" or (
        not source_d2.get("winners")
        and not source_d2.get("winner")
        and bool(source_d2.get("proposals"))
    )

    mode = "no_valid_proposals" if is_no_valid_proposals else "saved_winner_plan"
    stage: dict[str, Any] = {
        "model": model_name,
        "mode": mode,
        "proposals": source_d2.get("proposals", []),
        "judged_candidates": source_d2.get("judged_candidates", []),
    }
    result: dict[str, Any] = {
        "schema_version": "pf-recheck-diagnostic/v1",
        "case_id": case_id,
        "model_selector": model_selector,
        "status": "running",
        "error": None,
        "source_provenance": {
            "source_root": str(source_root.resolve()),
            "source_dir": case_dir.name,
            "source_result_sha256": source_result_sha256,
            "source_status": source_status,
            "source_error": source_result.get("error"),
            "source_artifact_sha256": {
                "input.json": _compute_sha256(input_path),
                "d1.json": _compute_sha256(d1_path),
                "result.json": source_result_sha256,
            },
        },
        "prior_context": prior_context,
        "stages": {
            "D1": source_result.get("stages", {}).get(
                "D1",
                {
                    "status": "completed",
                    "source": "frozen_from_source",
                },
            ),
            "D2_D3": stage,
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(out_case_dir / "result.json", result)

    d2_original = d2_runner.chat_json
    d2_runner.chat_json = _traced_chat(tracer, "run_situation_skeletons", d1_prompt=False)
    try:
        if mode == "saved_winner_plan":
            winner = d2_runner._winner_from_result(source_result_path, expected_case_id=case_id)
            if "plan_payload" not in source_d2 or source_d2["plan_payload"] is None:
                raise ValueError("Saved result is missing D2_D3.plan_payload")
            initial_plan_payload = source_d2["plan_payload"]

            stage.update(
                source_winner=winner.to_dict(),
                initial_plan_payload=initial_plan_payload,
            )
            _run_planning_fill_task(
                client,
                model_name,
                prompts,
                case,
                winner,
                prior_context,
                initial_plan_payload,
                stage,
                result,
            )
        else:
            saved_proposals = source_d2.get("proposals", [])
            if not isinstance(saved_proposals, list):
                raise ValueError("Saved D2_D3.proposals must be a list")
            stage["saved_proposals"] = saved_proposals
            repaired_proposals = []
            for prop in saved_proposals:
                init_prop, init_raw, empty_saved = _saved_proposal_input(prop)
                repaired = d2_runner._propose_one(
                    client,
                    model_name,
                    prompts,
                    case,
                    prior_context,
                    initial_proposal={"payload": init_prop, "raw_text": init_raw},
                    initial_proposal_raw=init_raw,
                )
                repaired["saved_input_empty"] = empty_saved
                repaired["saved_input_had_payload"] = isinstance(prop, dict) and (
                    "payload" in prop or "skeleton" in prop
                )
                repaired_raw = repaired.get("raw_text", "")
                repaired["empty_response"] = (
                    not isinstance(repaired_raw, str) or not repaired_raw.strip()
                )
                repaired_proposals.append(repaired)

            stage["proposals"] = [
                {k: v for k, v in item.items() if k != "skeleton_obj"}
                for item in repaired_proposals
            ]
            skeletons = [
                p["skeleton_obj"] for p in repaired_proposals if p.get("skeleton_obj") is not None
            ]
            if not skeletons:
                stage["status"] = "no_valid_proposals"
                result["status"] = "no_valid_proposals"
                result["error"] = "no valid proposals after repair"
            else:
                judge_payload, judge_raw = d2_runner._judge_all(
                    client, model_name, prompts, case, prior_context, skeletons
                )
                stage["judge_payload"] = judge_payload
                stage["judge_raw_text"] = judge_raw
                judged: list[Any] = []
                try:
                    judged = _select_saved_candidates(judge_payload, skeletons, prior_context)
                except (TypeError, ValueError) as exc:
                    stage["judge_error"] = str(exc)
                    stage["status"] = "judge_error"
                    result["status"] = "judge_error"
                    result["error"] = str(exc)
                stage["judged_candidates"] = [item.to_dict() for item in judged]
                winners = [c for c in judged if c.accepted] if judged else []
                if not winners:
                    if stage.get("status") != "judge_error":
                        stage["status"] = "no_winner"
                        result["status"] = "no_winner"
                else:
                    winner = winners[0]
                    _run_planning_fill_task(
                        client,
                        model_name,
                        prompts,
                        case,
                        winner,
                        prior_context,
                        None,
                        stage,
                        result,
                    )
    except Exception as exc:
        error_trace = traceback.format_exc()
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = error_trace
        stage["status"] = "failed"
        stage["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        d2_runner.chat_json = d2_original
        counts = trace_summary(trace_file)
        result["trace_counts"] = counts
        result["model_call_count"] = counts["finished"]
        stage["model_calls"] = counts["finished"]
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["stages"]["D2_D3"] = stage
        _write_json(out_case_dir / "result.json", result)

    return result


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recheck PF generalized bounded joint repair on saved diagnostic cases."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Path to saved diagnostic results directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to new output directory (must not exist).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="luna",
        help="Model selector (default: 'luna').",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=None,
        help="Case IDs, directory names, or keywords (e.g. fractions, kinematics).",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    ns = parse_args(args)
    source_root = ns.source_root
    output_dir = ns.output
    model_selector = ns.model

    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    case_dirs = find_case_dirs(source_root, ns.cases)
    if not case_dirs:
        raise ValueError(f"No matching cases found in {source_root} for filter {ns.cases}")

    t0 = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    client, model_name = load_client(model_selector)
    client = client.with_options(max_retries=0)

    prompts = d2_runner._prompts()
    source_result_hashes: dict[str, str] = {}
    source_artifact_hashes: dict[str, dict[str, str]] = {}
    case_summaries: list[dict[str, Any]] = []
    source_hashes_before = compute_source_hashes()
    manifest = {
        "schema_version": "pf-recheck-manifest/v1",
        "label": "development-calibration",
        "source_root": str(source_root.resolve()),
        "source_hashes_before": source_hashes_before,
        "source_hashes": source_hashes_before,
        "source_result_hashes": source_result_hashes,
        "source_artifact_hashes_before": source_artifact_hashes,
        "source_artifact_hashes": source_artifact_hashes,
        "model_selector": model_selector,
        "model_name": model_name,
        "budgets": {
            "proposal_retry_max": d2_runner.PROPOSAL_RETRY_MAX,
            "plan_retry_max": d2_runner.PLAN_RETRY_MAX,
            "fill_max_tries": d2_runner.FILL_MAX_TRIES,
        },
        "settings": {
            "sdk_max_retries": 0,
            "proposal_temperature": d2_runner.PROPOSE_TEMPERATURE,
            "proposal_max_tokens": d2_runner.PROPOSE_MAX_TOKENS,
            "judge_temperature": d2_runner.JUDGE_TEMPERATURE,
            "judge_max_tokens": d2_runner.JUDGE_MAX_TOKENS,
            "fill_temperature": 0.7,
            "fill_max_tokens": d2_runner.PROPOSE_MAX_TOKENS,
            "writer_temperature": 0.7,
            "writer_max_tokens": d2_runner.PROPOSE_MAX_TOKENS,
        },
        "cases": case_summaries,
        "status": "running",
        "started_at": started_at,
    }
    _write_json(output_dir / "manifest.json", manifest)

    for case_dir in case_dirs:
        out_case_dir = output_dir / case_dir.name
        source_artifacts = {
            name: _compute_sha256(case_dir / name)
            for name in ("input.json", "d1.json", "result.json")
            if (case_dir / name).is_file()
        }
        source_artifact_hashes[case_dir.name] = source_artifacts
        if "result.json" in source_artifacts:
            source_result_hashes[case_dir.name] = source_artifacts["result.json"]
        if len(source_artifacts) != 3:
            missing = sorted({"input.json", "d1.json", "result.json"} - source_artifacts.keys())
            error = f"ValueError: Saved case {case_dir.name} is missing artifacts: {missing}"
            case_res = {"case_id": case_dir.name, "status": "failed", "error": error}
            out_case_dir.mkdir(parents=True, exist_ok=False)
            _write_json(
                out_case_dir / "result.json",
                {
                    "schema_version": "pf-recheck-diagnostic/v1",
                    "case_id": case_dir.name,
                    "status": "failed",
                    "error": error,
                    "source_provenance": {
                        "source_root": str(source_root.resolve()),
                        "source_dir": case_dir.name,
                        "source_artifact_sha256": source_artifacts,
                    },
                },
            )
            case_summaries.append(case_res)
            continue
        try:
            case_res = recheck_case(
                case_dir=case_dir,
                out_case_dir=out_case_dir,
                client=client,
                model_selector=model_selector,
                model_name=model_name,
                prompts=prompts,
                source_root=source_root,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            error_trace = traceback.format_exc()
            case_res = {
                "case_id": case_dir.name,
                "status": "failed",
                "error": error,
            }
            # recheck_case may have created this directory before a later
            # validation/tracing failure; this output root was just created.
            out_case_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                out_case_dir / "result.json",
                {
                    "schema_version": "pf-recheck-diagnostic/v1",
                    "case_id": case_dir.name,
                    "status": "failed",
                    "error": error,
                    "traceback": error_trace,
                    "source_provenance": {
                        "source_root": str(source_root.resolve()),
                        "source_dir": case_dir.name,
                        "source_artifact_sha256": source_artifacts,
                    },
                },
            )
        case_summaries.append(
            {
                "case_id": case_res.get("case_id"),
                "source_dir": case_dir.name,
                "status": case_res.get("status"),
                "error": case_res.get("error"),
                "model_calls": case_res.get("model_call_count", 0),
                "trace_counts": case_res.get("trace_counts"),
                "elapsed_seconds": case_res.get("elapsed_seconds"),
            }
        )

    elapsed = round(time.perf_counter() - t0, 3)
    finished_at = datetime.now(timezone.utc).isoformat()
    source_hashes_after = compute_source_hashes()
    source_artifact_hashes_before = {
        case_id: dict(hashes) for case_id, hashes in source_artifact_hashes.items()
    }
    source_artifact_hashes_after = {
        case_dir.name: {
            name: _compute_sha256(case_dir / name)
            for name in ("input.json", "d1.json", "result.json")
            if (case_dir / name).is_file()
        }
        for case_dir in case_dirs
    }
    manifest["source_hashes_after"] = source_hashes_after
    manifest["source_hashes"] = source_hashes_after
    manifest["source_result_hashes"] = source_result_hashes
    manifest["source_artifact_hashes_before"] = source_artifact_hashes_before
    manifest["source_artifact_hashes_after"] = source_artifact_hashes_after
    manifest["source_artifact_hashes"] = source_artifact_hashes_after
    manifest["cases"] = case_summaries
    manifest["total_live_model_calls"] = sum(item.get("model_calls", 0) for item in case_summaries)
    manifest["source_integrity_unchanged"] = (
        source_hashes_before == source_hashes_after
        and source_artifact_hashes_before == source_artifact_hashes_after
    )
    manifest["status"] = (
        "completed"
        if manifest["source_integrity_unchanged"]
        and not any(item.get("status") == "failed" for item in case_summaries)
        else "failed"
    )
    manifest["finished_at"] = finished_at
    manifest["elapsed_seconds"] = elapsed
    _write_json(output_dir / "manifest.json", manifest)
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
