"""PF Diagnostic benchmark runner.

Executes a full-pipeline diagnostic across benchmark cases (or a subset)
generating fresh D1 prior-resource context, D2 briefs and checked concrete data,
and D3 task writing, with process-isolated execution and structured JSONL call tracing.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_situation_skeletons as d2_runner  # noqa: E402
from scripts.learning_commons_context import DEFAULT_CACHE_DIR, retrieve_context  # noqa: E402
from scripts.prior_methods.common import MODEL_ENVS, chat_json, load_client  # noqa: E402
from scripts.run_prior_recommendations import (  # noqa: E402
    _load_cases as _load_d1_cases,
)
from scripts.run_prior_recommendations import (  # noqa: E402
    _prompts as _d1_prompts,
)
from scripts.run_prior_recommendations import (  # noqa: E402
    _run_condition as _run_d1_condition,
)
from src.generation.prior_recommendations import Provenance  # noqa: E402
from src.generation.situation_skeletons import (  # noqa: E402
    best_candidates,
    judge_selection_from_payload,
    number_requirements_from_payload,
    rank_candidates,
    selected_candidate,
    verdicts_from_payload,
)

ALL8_CASES: list[str] = [
    "kapur_average_speed_g7_singapore",
    "loibl_variance_g10_nrw",
    "kerrigan_fair_division_undergrad_usa",
    "mazziotti_fraction_g5_nrw",
    "ratio_part_whole_g7_singapore",
    "weighted_combined_rate_g7_singapore",
    "kapur_kinematics_g11_cbse",
    "additive_vs_multiplicative_g7_singapore",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _case_by_id(case_id: str) -> dict[str, Any]:
    cases = _load_d1_cases()
    if not isinstance(cases, list):
        raise ValueError("D1 case loader must return a list")
    for case in cases:
        if isinstance(case, dict) and case.get("id") == case_id:
            return case
    raise KeyError(case_id)


def _frozen_grounding_records(
    records: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Adapt a small official-source packet to the D1 evidence contract."""
    if records is None:
        return None
    if not isinstance(records, list) or not records:
        raise ValueError("grounding_evidence must be a non-empty list")
    adapted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"grounding_evidence[{index}] must be an object")
        values = {key: record.get(key) for key in ("source_url", "standard_id", "text", "label")}
        if not all(isinstance(value, str) and value.strip() for value in values.values()):
            raise ValueError(
                "Each grounding evidence record requires non-empty "
                "source_url, standard_id, text, and label"
            )
        source_url = values["source_url"].strip()
        if not source_url.startswith(("http://", "https://")):
            raise ValueError(f"grounding_evidence[{index}].source_url must be an HTTP(S) URL")
        standard_id = values["standard_id"].strip()
        if standard_id in seen_ids:
            raise ValueError(f"Duplicate grounding standard_id: {standard_id}")
        seen_ids.add(standard_id)
        text = values["text"].strip()
        label = values["label"].strip()
        evidence_id = f"official:{standard_id}"
        adapted.append(
            {
                "evidence_id": evidence_id,
                "resource": "",
                "taught_as": "",
                "relevance": "",
                "provenance": Provenance(
                    type="curriculum",
                    source=label,
                    document=standard_id,
                    source_url=source_url,
                    evidence=f"{standard_id}: {text}",
                ),
                "excerpt": text,
            }
        )
    return adapted


def _stage_from_prompt(system: str, *, d1_prompt: bool) -> str:
    first = system.strip().splitlines()[0].strip() if system.strip() else ""
    prefixes = (
        (
            ("You list prior resources", "D1.ungrounded_inventory"),
            ("You map curriculum", "D1.grounded_mapping"),
            ("You add two short notes", "D1.resource_expansion"),
        )
        if d1_prompt
        else (
            ("Design one mathematical challenge", "D2.brief_proposal"),
            ("Select one promising mathematical design brief", "D2.brief_selection"),
            ("Translate the selected mathematical design brief", "D2.brief_translation"),
            ("Choose concrete data", "D2.data_proposal"),
            ("Repair only the numerical values", "D2.data_repair"),
            ("Design one grade-level", "D2.proposal"),
            ("Repair the proposed", "D2.proposal_repair"),
            ("You are selecting", "D2.selection"),
            ("Freeze the mathematical", "D2.plan"),
            ("Repair the selected", "D2.design_repair"),
            ("Review whether", "D2.review"),
            ("Fill values", "D2.fill"),
            ("Write the student-facing", "D3.writer"),
            ("Write a student-facing", "D3.writer"),
        )
    )
    for prefix, stage in prefixes:
        if first.startswith(prefix):
            return stage
    return "D1.unknown" if d1_prompt else "D2.unknown"


def _traced_chat(
    tracer: DiagnosticTracer,
    module: str,
    *,
    d1_prompt: bool,
    shared_context: dict[str, Any] | str | None = None,
    api_semaphore=None,
):
    def traced(client, model, system, user, temperature, max_tokens):
        stage = _stage_from_prompt(system, d1_prompt=d1_prompt)
        traced_user = user
        if shared_context is not None:
            context_text = (
                shared_context
                if isinstance(shared_context, str)
                else json.dumps(shared_context, ensure_ascii=False, indent=2)
            )
            traced_user = (
                f"{user}\n\nSHARED BENCHMARK CONTEXT (use throughout this design stage):\n"
                f"{context_text}"
            )

        def call():
            if api_semaphore is None:
                return chat_json(client, model, system, traced_user, temperature, max_tokens)
            api_semaphore.acquire()
            try:
                return chat_json(client, model, system, traced_user, temperature, max_tokens)
            finally:
                api_semaphore.release()

        return tracer.log_call(
            module=module,
            stage=stage,
            model=model,
            requested_settings={"temperature": temperature, "max_tokens": max_tokens},
            system_prompt=system,
            user_prompt=traced_user,
            fn=call,
        )

    return traced


TRACKED_SOURCE_FILES: list[Path] = [
    Path("scripts/run_pf_diagnostic.py"),
    Path("scripts/recheck_pf_joint_repair.py"),
    Path("scripts/design_brief_stage.py"),
    Path("scripts/design_data_stage.py"),
    Path("scripts/run_situation_skeletons.py"),
    Path("scripts/run_prior_recommendations.py"),
    Path("scripts/learning_commons_context.py"),
    Path("scripts/learning_commons_api.py"),
    Path("scripts/learning_commons_guided_search.py"),
    Path("scripts/prior_methods/common.py"),
    Path("src/generation/design_briefs.py"),
    Path("src/generation/design_data.py"),
    Path("src/generation/design_calculator.py"),
    Path("src/generation/situation_skeletons.py"),
    Path("src/generation/fill_check.py"),
    Path("src/generation/prompts/prior_recommendations.yaml"),
    Path("src/generation/prompts/design_briefs.yaml"),
    Path("src/generation/prompts/design_data.yaml"),
    Path("src/generation/prompts/situation_skeletons.yaml"),
    Path("experiments/configs/prior_recommendation_cases.json"),
]


def _compute_sha256(filepath: Path) -> str:
    """Compute sha256 hex digest for a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_source_hashes(root_dir: Path | None = None) -> dict[str, str]:
    """Compute source file hashes for reproducibility manifest, ignoring .env."""
    base = root_dir if root_dir is not None else ROOT
    hashes: dict[str, str] = {}
    for rel_path in TRACKED_SOURCE_FILES:
        full_path = base / rel_path
        if full_path.exists() and full_path.is_file():
            hashes[str(rel_path)] = _compute_sha256(full_path)
    return hashes


def _determine_effective_settings(model_name: str, requested: dict[str, Any]) -> dict[str, Any]:
    """Determine effective settings sent to OpenAI API given model quirks."""
    is_new = any(model_name.startswith(p) for p in ("gpt-5", "o1", "o3"))
    effective: dict[str, Any] = {}
    if not is_new:
        if "temperature" in requested:
            effective["temperature"] = requested["temperature"]
        if "max_tokens" in requested:
            effective["max_tokens"] = requested["max_tokens"]
    else:
        # GPT-5 and reasoning models omit temperature and map max_tokens -> max_completion_tokens
        if "max_tokens" in requested:
            effective["max_completion_tokens"] = requested["max_tokens"]
        elif "max_completion_tokens" in requested:
            effective["max_completion_tokens"] = requested["max_completion_tokens"]
    return effective


class DiagnosticTracer:
    """Thread-safe JSONL tracer for model calls within a single case execution."""

    def __init__(self, trace_file: Path, case_id: str, default_model: str):
        self.trace_file = trace_file
        self.case_id = case_id
        self.default_model = default_model
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def _next_call_number(self, module: str) -> int:
        with self._lock:
            val = self._counters.get(module, 0) + 1
            self._counters[module] = val
            return val

    def log_call(
        self,
        module: str,
        stage: str,
        model: str,
        requested_settings: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        fn,
    ) -> tuple[dict[str, Any] | None, str]:
        call_number = self._next_call_number(module)
        call_id = f"{self.case_id}:{module}:{call_number}"
        started_at = datetime.now(timezone.utc).isoformat()
        effective_settings = _determine_effective_settings(model, requested_settings)

        started_record = {
            "event": "model_call_started",
            "case_id": self.case_id,
            "module": module,
            "call_number": call_number,
            "call_id": call_id,
            "stage": stage,
            "started_at": started_at,
            "model": model,
            "requested_settings": requested_settings,
            "effective_settings": effective_settings,
            "settings_provenance": ("inferred from common.chat_json; usage metadata unavailable"),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        with self._lock:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(started_record) + "\n")

        t0 = time.perf_counter()
        error_msg = None
        payload = None
        raw_text = ""
        try:
            payload, raw_text = fn()
            return payload, raw_text
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = round(time.perf_counter() - t0, 3)
            finished_at = datetime.now(timezone.utc).isoformat()
            finished_record: dict[str, Any] = {
                "event": "model_call_finished",
                "case_id": self.case_id,
                "module": module,
                "call_number": call_number,
                "call_id": call_id,
                "stage": stage,
                "started_at": started_at,
                "model": model,
                "requested_settings": requested_settings,
                "effective_settings": effective_settings,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "finished_at": finished_at,
                "elapsed_seconds": elapsed,
            }
            if error_msg is not None:
                finished_record["error"] = error_msg
            else:
                finished_record["payload"] = payload
                finished_record["raw_text"] = raw_text

            with self._lock:
                with open(self.trace_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(finished_record) + "\n")


def trace_summary(trace_file: Path) -> dict[str, Any]:
    """Validate start/finish pairing and count only traced live calls."""
    if not trace_file.is_file():
        return {"started": 0, "finished": 0, "errors": 0, "call_ids": []}
    records = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    started_records = [record for record in records if record.get("event") == "model_call_started"]
    finished_records = [
        record for record in records if record.get("event") == "model_call_finished"
    ]
    started = {record["call_id"]: record for record in started_records}
    finished = {record["call_id"]: record for record in finished_records}
    if len(started) != len(started_records) or len(finished) != len(finished_records):
        raise ValueError("Tracer contains duplicate call_id records")
    if set(started) != set(finished):
        raise ValueError(
            f"Tracer call pairing mismatch: started={sorted(started)} finished={sorted(finished)}"
        )
    errors = sum(1 for record in finished.values() if "error" in record)
    return {
        "started": len(started),
        "finished": len(finished),
        "errors": errors,
        "call_ids": sorted(finished),
    }


def run_case_worker(
    case_id: str,
    case_dir_str: str,
    model_name: str,
    proposal_k: int,
    reused_d1_path_str: str | None = None,
    *,
    case_override: dict[str, Any] | None = None,
    shared_context: dict[str, Any] | str | None = None,
    evidence_k: int = 6,
    max_resources: int = 4,
    d1_condition: str = "grounded",
    grounding_evidence: list[dict[str, Any]] | None = None,
    learning_commons: bool = False,
    learning_commons_cache_dir: str | None = None,
    refresh_learning_commons: bool = False,
    design_brief: bool = True,
    api_semaphore=None,
    trace_filename: str = "model_calls.jsonl",
    design_feedback: str = "",
) -> dict[str, Any]:
    """Run one case while persisting the complete saved-case shape on failure."""
    if model_name not in MODEL_ENVS:
        raise ValueError(
            f"Unknown model selector {model_name!r}; choose one of {sorted(MODEL_ENVS)}"
        )
    if proposal_k < 1:
        raise ValueError("proposal_k must be positive")
    if not isinstance(design_brief, bool):
        raise ValueError("design_brief must be a boolean")
    if d1_condition not in {"grounded", "ungrounded"}:
        raise ValueError("d1_condition must be grounded or ungrounded")
    if reused_d1_path_str and (learning_commons or refresh_learning_commons):
        raise ValueError("Reused D1 already freezes its references; do not request fresh retrieval")
    if refresh_learning_commons and not learning_commons:
        raise ValueError("Learning Commons refresh requires learning_commons=True")
    case_dir = Path(case_dir_str)
    case_dir.mkdir(parents=True, exist_ok=False)
    trace_file = case_dir / trace_filename
    started = time.perf_counter()
    result: dict[str, Any] = {
        "schema_version": "pf-diagnostic/v2",
        "case_id": case_id,
        "model_selector": model_name,
        "status": "running",
        "error": None,
        "stages": {},
        "started_at": _now(),
    }
    _write_json(case_dir / "result.json", result)
    try:
        case = dict(case_override) if case_override is not None else _case_by_id(case_id)
        if case.get("id") not in {None, case_id}:
            raise ValueError(
                f"case_override id {case.get('id')!r} does not match worker case {case_id!r}"
            )
        case.setdefault("id", case_id)
    except KeyError:
        result.update(
            status="case_not_found",
            error=f"Case {case_id!r} not found in prior recommendation cases configuration.",
        )
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(case_dir / "result.json", result)
        return result
    result["case_input"] = case
    _write_json(case_dir / "input.json", case)
    d1_path = case_dir / "d1.json"
    d1_payload: dict[str, Any]
    client = None
    model = None
    tracer = None
    d1_original = None
    d1_curriculum_original = None
    d1_curated_original = None
    d2_original = None
    d1_result: dict[str, Any]
    d1_started = time.perf_counter()
    d2_started: float | None = None
    try:
        client, model = load_client(model_name)
        client = client.with_options(max_retries=0)
        tracer = DiagnosticTracer(trace_file, case_id, model)
        import scripts.run_prior_recommendations as d1_runner

        if reused_d1_path_str:
            source = Path(reused_d1_path_str)
            if not source.is_file():
                raise ValueError(f"reused D1 file does not exist: {source}")
            raw = json.loads(source.read_text())
            if not isinstance(raw, dict):
                raise ValueError("reused D1 payload must be an object")
            raw = dict(raw)
            raw["origin"] = "diagnostic_reused_d1"
            d2_runner._d1_result_for(raw, source, case_id, d1_condition)
            d1_payload = raw
            _, d1_result = d2_runner._d1_result_for(raw, source, case_id, d1_condition)
        else:
            d1_original = d1_runner.chat_json
            d1_runner.chat_json = _traced_chat(
                tracer,
                "run_prior_recommendations",
                d1_prompt=True,
                shared_context=shared_context,
                api_semaphore=api_semaphore,
            )
            if grounding_evidence is not None and d1_condition == "grounded":
                frozen_records = _frozen_grounding_records(grounding_evidence)
                d1_curriculum_original = d1_runner._curriculum_evidence
                d1_curated_original = d1_runner._curated_evidence
                d1_runner._curriculum_evidence = lambda _case, _k: frozen_records
                d1_runner._curated_evidence = lambda _case: []
            reference_kwargs = {}
            if learning_commons:
                reference_kwargs["learning_commons"] = retrieve_context(
                    case,
                    cache_dir=(
                        Path(learning_commons_cache_dir)
                        if learning_commons_cache_dir is not None
                        else DEFAULT_CACHE_DIR
                    ),
                    refresh=refresh_learning_commons,
                )
            d1_result = _run_d1_condition(
                client,
                model,
                _d1_prompts(),
                case,
                d1_condition,
                evidence_k=evidence_k,
                max_resources=max_resources,
                **reference_kwargs,
            )
            d1_payload = {
                "schema_version": d1_result["schema_version"],
                "created_at": _now(),
                "model": model,
                "origin": "fresh",
                "records": [{"case_id": case_id, "condition": d1_condition, "result": d1_result}],
            }
        _write_json(d1_path, d1_payload)
        prior_context = d2_runner._prior_context_from_d1(d1_path, case_id, d1_condition)
        result["prior_context"] = prior_context
        result["stages"]["D1"] = {
            "status": "completed",
            "elapsed_seconds": round(time.perf_counter() - d1_started, 3),
            "model_calls": 0,
            "output": d1_result,
            "output_path": str(d1_path),
        }
        _write_json(case_dir / "result.json", result)

        d2_original = d2_runner.chat_json
        d2_runner.chat_json = _traced_chat(
            tracer,
            "run_situation_skeletons",
            d1_prompt=False,
            shared_context=shared_context,
            api_semaphore=api_semaphore,
        )
        prompts = d2_runner._prompts()
        d2_started = time.perf_counter()
        stage: dict[str, Any] = {
            "model": model,
            "proposal_k": proposal_k,
            "proposal_status": "running",
            "status": "pending",
            "proposals": [],
            "selection": None,
            "winners": [],
            "original_winner": None,
            "design_repair_attempts": [],
            "plan": None,
            "plan_payload": None,
            "plan_raw_text": "",
            "plan_review": None,
            "plan_review_raw_text": "",
            "plan_review_prompts": None,
            "plan_attempts": [],
            "plan_stop_stage": None,
            "plan_error": None,
            "fill": None,
            "task": None,
            "task_raw_text": "",
        }
        if design_brief:
            stage.update(
                design_brief=True, brief_selection=None, translation=None, design_data=None
            )
        result["stages"]["D2_D3"] = stage
        _write_json(case_dir / "result.json", result)
        if design_brief:
            import scripts.design_brief_stage as brief_runner

            search_kwargs = {"design_feedback": design_feedback} if design_feedback else {}
            search = brief_runner.run_design_brief_search(
                client,
                model,
                case,
                prior_context,
                k=proposal_k,
                **search_kwargs,
            )
            stage.update(
                proposals=search["proposals"],
                proposal_status="completed",
                valid_proposal_count=search["n_valid_proposals"],
                judge_payload=search["judge_payload"],
                judge_raw_text=search["judge_raw_text"],
                judge_error=search["judge_error"],
                brief_selection=search["brief_selection"],
                selection_attempts=search.get("selection_attempts", []),
                design_quality_status=search.get("quality_status"),
                design_quality_findings=search.get("quality_findings", []),
                translation=search["translation"],
                external_design_feedback=design_feedback,
                design_brief_source_hashes=search["source_hashes"],
                design_brief_prompt_snapshot=search["prompt_snapshot"],
            )
            judged = search["judged"]
            winners = search["winners"]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=proposal_k) as pool:
                futures = [
                    pool.submit(d2_runner._propose_one, client, model, prompts, case, prior_context)
                    for _ in range(proposal_k)
                ]
                proposals = [future.result() for future in futures]
            stage["proposals"] = [
                {key: value for key, value in item.items() if key != "skeleton_obj"}
                for item in proposals
            ]
            skeletons = [
                item["skeleton_obj"]
                for item in proposals
                if isinstance(item, dict) and item.get("skeleton_obj") is not None
            ]
            stage["proposal_status"] = "completed"
            stage["valid_proposal_count"] = len(skeletons)
            if not skeletons:
                stage["status"] = "no_valid_proposals"
                result["status"] = "no_valid_proposals"
                return result
            judge_payload, judge_raw = d2_runner._judge_all(
                client, model, prompts, case, prior_context, skeletons
            )
            stage["judge_payload"] = judge_payload
            stage["judge_raw_text"] = judge_raw
            judged: list[Any] = []
            if isinstance(judge_payload, dict):
                selection = judge_selection_from_payload(
                    judge_payload,
                    set(range(len(skeletons))),
                    require_prior_contrast=True,
                )
                if selection is not None:
                    stage["selection"] = {
                        "recommended_id": selection.recommended_id,
                        "approaches": list(selection.approaches),
                        "reason": selection.reason,
                        "main_concern": selection.main_concern,
                        "prior_contrast": (
                            None
                            if selection.prior_contrast is None
                            else selection.prior_contrast.to_dict()
                        ),
                        "number_requirements": [
                            item.to_dict() for item in selection.number_requirements
                        ],
                    }
                    judged = selected_candidate(skeletons, selection)
                else:
                    approach_ids = {
                        index: {approach.id for approach in skeleton.approaches}
                        for index, skeleton in enumerate(skeletons)
                    }
                    verdicts = verdicts_from_payload(
                        judge_payload,
                        d2_runner._method_names(prior_context),
                        approach_ids,
                    )
                    requirements = number_requirements_from_payload(judge_payload)
                    judged = rank_candidates(skeletons, verdicts, requirements)
            winners = best_candidates(judged) if judged and not stage["selection"] else judged
        stage["judged_candidates"] = [item.to_dict() for item in judged]
        stage["winners"] = [item.to_dict() for item in winners]
        if not stage["valid_proposal_count"]:
            stage["status"] = "no_valid_proposals"
            result["status"] = "no_valid_proposals"
            if design_brief:
                result["error"] = stage["judge_error"]
            return result
        if not winners:
            stage["status"] = "no_winner"
            result["status"] = "no_winner"
            if design_brief:
                translation = stage["translation"]
                if isinstance(translation, dict):
                    reason = translation.get("error") or "No translated winner was produced."
                    result["error"] = (
                        f"D2b translation {translation.get('status', 'unknown')}: {reason}"
                    )
                else:
                    result["error"] = stage["judge_error"]
            return result
        winner = winners[0]
        if design_brief:
            stage["original_winner"] = winner.to_dict()
            data_run = d2_runner._run_design_data(client, model, case, winner, prior_context)
            stage["design_data"] = data_run
            stage["fill"] = data_run
            stage["design_data_source_hashes"] = data_run["source_hashes"]
            stage["design_data_prompt_snapshot"] = data_run["prompt_snapshot"]
            if data_run["payload"] is None:
                result["status"] = (
                    "data_review_needed"
                    if data_run["status"] == "review_needed"
                    else "data_not_accepted"
                )
                stage["status"] = result["status"]
                result["error"] = data_run["error"]
                return result
            task, task_raw = d2_runner._write_design_data_task(
                client, model, case, winner, data_run, prior_context
            )
        else:
            planning = d2_runner._plan_until_reviewed(
                client, model, prompts, case, winner, prior_context, require_v2=True
            )
            plan = planning.get("plan")
            original_winner_obj = (
                planning.get("original_winner")
                if planning.get("original_winner") is not None
                else winner
            )
            effective_winner = (
                planning.get("winner") if planning.get("winner") is not None else winner
            )
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
                effective_winner.to_dict()
                if hasattr(effective_winner, "to_dict")
                else effective_winner
            )
            stage["winners"] = [effective_winner_dict] + [
                item.to_dict() if hasattr(item, "to_dict") else item for item in winners[1:]
            ]
            if stage["plan_attempts"]:
                stage["plan_stop_stage"] = stage["plan_attempts"][-1].get("stage")
            if plan is None:
                result["status"] = {
                    "structure": "plan_blocked",
                    "expression": "expression_blocked",
                    "meaning_review": "review_blocked",
                }.get(stage["plan_stop_stage"], "plan_blocked")
                stage["status"] = result["status"]
                result["error"] = stage["plan_error"]
                return result
            review = planning.get("plan_review")
            if not d2_runner._review_passes(review):
                stage["status"] = "review_blocked"
                result["status"] = "review_blocked"
                result["error"] = stage["plan_error"] or "plan review did not pass"
                return result
            fill = d2_runner._fill_until_accepted(
                client,
                model,
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
                result["error"] = "Number fill could not satisfy mathematical constraints."
                return result
            task, task_raw = d2_runner._write_task(
                client,
                model,
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
            stage["status"] = "D3_blocked"
            result["status"] = "D3_blocked"
            result["error"] = (
                "; ".join(task.get("blocking_issues", []))
                if isinstance(task, dict)
                else "writer returned no ready task"
            )
            return result
        stage["status"] = "completed"
        result["status"] = "completed"
        return result
    except Exception as exc:
        result["status"] = "D2_D3_failed" if result["stages"].get("D2_D3") else "D1_failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        if result["stages"].get("D2_D3") is not None:
            result["stages"]["D2_D3"]["status"] = result["status"]
        else:
            result["stages"]["D1"] = {
                "status": "failed",
                "error": result["error"],
            }
        return result
    finally:
        if d1_original is not None:
            d1_runner.chat_json = d1_original
        if d1_curriculum_original is not None:
            d1_runner._curriculum_evidence = d1_curriculum_original
        if d1_curated_original is not None:
            d1_runner._curated_evidence = d1_curated_original
        if d2_original is not None:
            d2_runner.chat_json = d2_original
        result["finished_at"] = _now()
        if result["stages"].get("D1") is not None and tracer:
            counts = trace_summary(trace_file)
            result["stages"]["D1"]["model_calls"] = sum(
                1 for call_id in counts["call_ids"] if ":run_prior_recommendations:" in call_id
            )
        if result["stages"].get("D2_D3") is not None and d2_started is not None:
            result["stages"]["D2_D3"]["elapsed_seconds"] = round(
                time.perf_counter() - d2_started, 3
            )
            counts = trace_summary(trace_file) if tracer else {"call_ids": []}
            result["stages"]["D2_D3"]["model_calls"] = sum(
                1 for call_id in counts["call_ids"] if ":run_situation_skeletons:" in call_id
            )
        result["model"] = model if "model" in locals() else None
        trace_counts = (
            trace_summary(trace_file)
            if tracer
            else {
                "started": 0,
                "finished": 0,
                "errors": 0,
                "call_ids": [],
            }
        )
        result["trace_counts"] = trace_counts
        result["model_call_count"] = trace_counts["finished"]
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(case_dir / "result.json", result)


def run_benchmark(
    cases: list[str],
    model: str = "luna",
    max_workers: int = 3,
    proposal_k: int = 4,
    reuse_d1_root: Path | None = None,
    output_dir: Path | None = None,
    *,
    learning_commons: bool = False,
    learning_commons_cache_dir: Path = DEFAULT_CACHE_DIR,
    refresh_learning_commons: bool = False,
    design_brief: bool = True,
) -> dict[str, Any]:
    """Orchestrate diagnostic benchmark across selected cases with isolated processes."""
    if not cases:
        raise ValueError("No cases specified for benchmark.")
    if model not in MODEL_ENVS:
        raise ValueError(f"Unknown model selector {model!r}; choose one of {sorted(MODEL_ENVS)}")
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    if proposal_k < 1:
        raise ValueError("proposal_k must be positive")
    if not isinstance(design_brief, bool):
        raise ValueError("design_brief must be a boolean")
    if reuse_d1_root is not None and (learning_commons or refresh_learning_commons):
        raise ValueError("Reused D1 already freezes its references; do not request fresh retrieval")
    if refresh_learning_commons and not learning_commons:
        raise ValueError("Learning Commons refresh requires --learning-commons")
    known_cases = {
        item.get("id")
        for item in _load_d1_cases()
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    duplicates = sorted({case for case in cases if cases.count(case) > 1})
    unknown = sorted(set(cases) - known_cases)
    if duplicates:
        raise ValueError(f"Duplicate case IDs: {duplicates}")
    if unknown:
        raise ValueError(f"Unknown case IDs: {unknown}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_dir is None:
        run_name = f"{timestamp}_full_pipeline_diagnostic_{model}"
        output_dir = Path("experiments/results/validation") / run_name

    if reuse_d1_root is not None:
        reuse_d1_root = Path(reuse_d1_root)
        missing = [
            str(reuse_d1_root / case_id / "d1.json")
            for case_id in cases
            if not (reuse_d1_root / case_id / "d1.json").is_file()
        ]
        if missing:
            raise ValueError(f"Reuse D1 requires every case file; missing: {missing}")

    # Create root run directory with exist_ok=False to avoid accidental overwrites
    output_dir.mkdir(parents=True, exist_ok=False)

    source_hashes = compute_source_hashes()
    manifest: dict[str, Any] = {
        "benchmark": "pf_diagnostic",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "max_workers": max_workers,
        "proposal_k": proposal_k,
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
        "d1_mode": "diagnostic_reused_d1" if reuse_d1_root else "fresh",
        "settings_provenance": ("known runner settings; API usage metadata is not captured"),
        "cases": cases,
        "source_hashes": source_hashes,
        "case_summaries": {},
        "errors": {},
    }
    if learning_commons:
        manifest["learning_commons"] = {
            "enabled": True,
            "cache_dir": str(learning_commons_cache_dir.resolve()),
            "refresh": refresh_learning_commons,
            "selection_in_existing_d1_call": True,
        }
    if design_brief:
        from scripts.design_brief_stage import MAX_TOKENS
        from scripts.design_data_stage import MAX_CALLS
        from scripts.design_data_stage import MAX_TOKENS as DATA_MAX_TOKENS

        manifest["design_brief"] = True
        manifest["settings"] = {
            "sdk_max_retries": 0,
            "design_brief": {
                "max_tokens": MAX_TOKENS,
                "proposal_temperature": d2_runner.PROPOSE_TEMPERATURE,
                "selection_temperature": 0.0,
            },
            "design_data": {"max_tokens": DATA_MAX_TOKENS, "temperature": 0.0},
            "writer_temperature": 0.7,
            "writer_max_tokens": d2_runner.PROPOSE_MAX_TOKENS,
        }
        manifest["budgets"] = {
            "proposal_retry_max": d2_runner.PROPOSAL_RETRY_MAX,
            "design_data_max_calls": MAX_CALLS,
        }

    _write_json(output_dir / "manifest.json", manifest)

    futures_map: dict[concurrent.futures.Future, str] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for cid in cases:
            case_dir = output_dir / cid
            reused_d1_file = None
            if reuse_d1_root is not None:
                candidate_d1 = reuse_d1_root / cid / "d1.json"
                reused_d1_file = str(candidate_d1)

            reference_kwargs = {}
            if learning_commons:
                reference_kwargs = {
                    "learning_commons": True,
                    "learning_commons_cache_dir": str(learning_commons_cache_dir.resolve()),
                    "refresh_learning_commons": refresh_learning_commons,
                }
            if not design_brief:
                reference_kwargs["design_brief"] = False
            fut = executor.submit(
                run_case_worker,
                cid,
                str(case_dir),
                model,
                proposal_k,
                reused_d1_file,
                **reference_kwargs,
            )
            futures_map[fut] = cid

        for fut in concurrent.futures.as_completed(futures_map):
            cid = futures_map[fut]
            try:
                res = fut.result()
                manifest["case_summaries"][cid] = res
                if res.get("error"):
                    manifest["errors"][cid] = res["error"]
            except Exception as exc:
                err_str = f"Worker exception for {cid}: {type(exc).__name__}: {exc}"
                manifest["case_summaries"][cid] = {
                    "case_id": cid,
                    "status": "worker_failed",
                    "error": err_str,
                }
                manifest["errors"][cid] = err_str
            _write_json(output_dir / "manifest.json", manifest)

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["source_hashes_after"] = compute_source_hashes()
    manifest["source_integrity_unchanged"] = (
        manifest["source_hashes"] == manifest["source_hashes_after"]
    )
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PF full-pipeline diagnostic benchmark.")
    parser.add_argument(
        "--cases",
        nargs="+",
        default=ALL8_CASES,
        help="List of case IDs to run (default: all 8 benchmark cases).",
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=sorted(MODEL_ENVS),
        default="luna",
        help="Model choice (e.g., luna, gpt-5.6-luna, gpt-4o). Default: luna.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum isolated worker processes for concurrent cases (default: 4).",
    )
    parser.add_argument(
        "--proposal-k",
        type=int,
        default=4,
        help="Number of proposals to generate per case in parallel threads (default: 4).",
    )
    parser.add_argument(
        "--reuse-d1-root",
        type=Path,
        default=None,
        help="Optional path to a prior diagnostic run directory to reuse D1 results cheaply.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional destination run directory.",
    )
    parser.add_argument(
        "--learning-commons",
        dest="learning_commons",
        action="store_true",
        help="Select mathematical references in the D1 call (default; kept for explicitness).",
    )
    parser.add_argument(
        "--no-learning-commons",
        dest="learning_commons",
        action="store_false",
        help="Run D1 without Learning Commons references.",
    )
    parser.set_defaults(learning_commons=True)
    parser.add_argument("--learning-commons-cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--refresh-learning-commons", action="store_true")
    return parser.parse_args(args)


def main() -> int:
    args = parse_args()
    # A reused D1 already freezes its references, so fresh retrieval is switched off.
    use_learning_commons = args.learning_commons and args.reuse_d1_root is None
    manifest = run_benchmark(
        cases=args.cases,
        model=args.model,
        max_workers=args.max_workers,
        proposal_k=args.proposal_k,
        reuse_d1_root=args.reuse_d1_root,
        output_dir=args.output,
        learning_commons=use_learning_commons,
        learning_commons_cache_dir=args.learning_commons_cache_dir,
        refresh_learning_commons=args.refresh_learning_commons,
    )
    return 0 if not manifest["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
