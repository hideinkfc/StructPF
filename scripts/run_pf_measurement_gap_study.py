"""Freeze and run a bounded, paired PF evidence study or a generic task catalog."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAIError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prior_methods.common import load_client  # noqa: E402
from src.evaluation import pf_evidence_audit as audit  # noqa: E402
from src.evaluation.pf_rubric import parse_rating  # noqa: E402

DEFAULT_CONFIG = ROOT / "experiments/configs/pf_measurement_gap_study_20261013.json"
DEFAULT_BENCHMARK = ROOT / "experiments/results/pf_paper_benchmark/20260923_luna_v4"
DEFAULT_OUTPUT = ROOT / "experiments/results/pf_measurement_gap_study_20261013"
RUNTIME_VERSION = "pf-evidence-runner/v1.3"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path):
    return json.loads(path.read_text())


def path_name(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _stratified(records: list[dict], per_tertile: int, rng: random.Random) -> list[dict]:
    selected = []
    for lower in (1, 11, 21):
        stratum = [row for row in records if lower <= row["number"] < lower + 10]
        if len(stratum) < per_tertile:
            raise ValueError(f"Not enough ready tasks in attempt stratum {lower}")
        selected.extend(rng.sample(stratum, per_tertile))
    return selected


def freeze_benchmark(output: Path, benchmark: Path, config: dict) -> tuple[list[dict], dict]:
    """Select by attempt/ready metadata, seal IDs/hashes, then extract task/rating text."""
    rng = random.Random(config["seed"])
    pool = {}
    read_records = []
    for arm in ("V1", "V2", "V3", "PIPELINE"):
        records = []
        for source in sorted((benchmark / "attempts" / arm).glob("*/result.json")):
            raw = source.read_bytes()
            record = json.loads(raw)
            metadata = {
                "task_id": record["attempt_id"], "number": record["number"],
                "arm": arm, "status": record["status"],
                "source_path": path_name(source), "source_sha256": audit.sha256(raw),
            }
            records.append(metadata)
            read_records.append({**metadata, "read_purpose": "Availability and attempt strata only"})
        pool[arm] = records
    ready = {arm: [row for row in records if row["status"] == "ready"] for arm, records in pool.items()}
    if any(len(pool[arm]) != 30 for arm in pool) or len(ready["V1"]) != 30:
        raise ValueError("Historical pool does not match the predefined 30-per-arm condition")
    selected = [
        *ready["V1"],
        *_stratified(ready["V2"], 2, rng),
        *_stratified(ready["V3"], 2, rng),
        *_stratified(ready["PIPELINE"], 4, rng),
    ]
    rng.shuffle(selected)
    frozen = {
        "sealed_at": now(),
        "selection_rule": config["sampling"],
        "seed": config["seed"],
        "selection_independent_of_old_score_and_faults": True,
        "selection_scope": "Proportional relationships, Grade 7, fictional basketball/Curry; no cross-topic inference",
        "pool": {
            arm: {"attempts": len(records), "ready": len(ready[arm]),
                  "status_counts": dict(Counter(row["status"] for row in records))}
            for arm, records in pool.items()
        },
        "selected": selected,
        "selection_sha256": audit.sha256(json.dumps(selected, sort_keys=True)),
    }
    write_json(output / "selection_frozen.json", frozen)
    write_json(output / "selection_read_records.json", read_records)
    historical_config = read_json(benchmark / "config.json")
    catalog = []
    snapshot = output / "saved_task_snapshot"
    snapshot.mkdir()
    for row in selected:
        source = resolve_path(row["source_path"])
        if audit.sha256(source.read_bytes()) != row["source_sha256"]:
            raise ValueError("Task source changed after selection was sealed")
        record = read_json(source)
        judgment_path = source.parent / "judgment.json"
        judgment_bytes = judgment_path.read_bytes()
        judgment = json.loads(judgment_bytes)
        original = parse_rating(judgment["raw_response"])
        if original["scores"] != judgment["scores"]:
            raise ValueError(f"Saved scores do not match exact raw rating: {judgment_path}")
        entry = {
            **row,
            "task": {key: record["task"][key] for key in ("title", "body", "question")},
            "learner_context": historical_config["learner_context"],
            "learning_target": historical_config["case"]["target_concept"],
            "case": historical_config["case"]["id"],
            "original_rating": {
                **original, "raw_response": judgment["raw_response"],
                "source_path": path_name(judgment_path),
                "source_sha256": audit.sha256(judgment_bytes),
                "saved_judgment_status": judgment["status"],
                "rubric": "rahimi-table1/v1",
            },
        }
        directory = snapshot / entry["task_id"]
        directory.mkdir()
        shutil.copy2(source, directory / "result.json")
        shutil.copy2(judgment_path, directory / "judgment.json")
        catalog.append(entry)
    for name in ("config.json", "manifest.json", "prompt.yaml", "source_hashes.json"):
        shutil.copy2(benchmark / name, snapshot / name)
    return catalog, frozen


def read_catalog(path: Path) -> list[dict]:
    payload = read_json(path)
    catalog = payload["tasks"] if isinstance(payload, dict) else payload
    if not isinstance(catalog, list) or not catalog:
        raise ValueError("Catalog must be a nonempty array or {'tasks': [...]} object")
    ids = [entry.get("task_id") for entry in catalog]
    if not all(isinstance(value, str) and value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("Catalog task IDs must be nonempty and unique")
    for entry in catalog:
        # Input errors are retained as unknown rather than erasing a catalog task.
        for key in ("source_path", "source_sha256", "learning_target", "learner_context"):
            if key not in entry:
                raise ValueError(f"Catalog entry {entry['task_id']} is missing {key}")
        entry.setdefault("task", None)
    return catalog


def control_catalog(config: dict, config_path: Path = DEFAULT_CONFIG) -> list[dict]:
    return [
        {
            **control, "source_path": path_name(config_path),
            "source_sha256": audit.sha256(config_path.read_bytes()), "arm": "synthetic_control",
        }
        for control in config["controls"]
    ]


def catalog_source_provenance(catalog: list[dict], output: Path) -> list[dict]:
    records = []
    directory = output / "catalog_source_snapshot"
    directory.mkdir()
    for index, entry in enumerate(catalog):
        source = resolve_path(entry["source_path"])
        record = {
            "task_id": entry["task_id"], "source_path": entry["source_path"],
            "declared_sha256": entry["source_sha256"],
        }
        if source.is_file():
            raw = source.read_bytes()
            actual = audit.sha256(raw)
            destination = directory / f"{index:03d}-{source.name}"
            destination.write_bytes(raw)
            record.update(
                status="verified_bytes" if actual == entry["source_sha256"] else "hash_mismatch",
                actual_sha256=actual, snapshot_path=path_name(destination),
            )
        else:
            record.update(status="unknown_missing_source_path", actual_sha256=None)
        records.append(record)
        entry["source_provenance"] = record
    write_json(output / "catalog_source_provenance.json", records)
    return records


def prepare_run(
    output: Path, config_path: Path, catalog_path: Path | None, benchmark: Path,
    judges: list[str], max_calls: int,
) -> dict:
    if len(judges) != 2 or set(judges) != {"gpt41", "gpt54"}:
        raise ValueError("This frozen study requires gpt41 and gpt54, two distinct model series")
    config = read_json(config_path)
    output.mkdir(parents=True, exist_ok=False)
    prompt = audit.load_prompt()
    if catalog_path:
        catalog = read_catalog(catalog_path)
        selection = {
            "selection_scope": "Caller-supplied frozen task catalog; no historical sampling inference",
            "catalog_source": path_name(catalog_path),
            "catalog_source_sha256": audit.sha256(catalog_path.read_bytes()),
            "selected_task_ids": [entry["task_id"] for entry in catalog],
        }
        write_json(output / "selection_frozen.json", selection)
        shutil.copy2(catalog_path, output / "catalog_original.json")
        catalog_source_provenance(catalog, output)
        controls = []
    else:
        catalog, selection = freeze_benchmark(output, benchmark, config)
        controls = control_catalog(config, config_path)
    requested_calls = 2 * (len(catalog) + len(controls))
    if requested_calls > min(max_calls, 200):
        raise ValueError(f"Requested {requested_calls} calls exceeds fixed cap {min(max_calls, 200)}")
    write_json(output / "catalog.json", {"tasks": catalog})
    write_json(output / "controls.json", {"tasks": controls})
    sources = (
        Path(__file__), ROOT / "scripts/report_pf_measurement_gap_study.py",
        ROOT / "src/evaluation/pf_evidence_audit.py", audit.PROMPT_PATH,
        ROOT / "src/evaluation/pf_rubric.py", ROOT / "src/evaluation/prompts/pf_rubric.yaml",
        ROOT / "scripts/prior_methods/common.py", config_path,
    )
    hashes = {}
    snapshot = output / "source_snapshot"
    for source in sources:
        name = path_name(source)
        hashes[name] = audit.sha256(source.read_bytes())
        relative_name = (
            Path(name) if not Path(name).is_absolute()
            else Path("external") / f"{hashes[name][:12]}-{source.name}"
        )
        destination = snapshot / relative_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    rng = random.Random(config["seed"])
    mappings = {}
    for judge in judges:
        mappings[judge] = {}
        for phase, entries in (("calibration", controls), ("main", catalog)):
            shuffled = list(entries)
            rng.shuffle(shuffled)
            for index, entry in enumerate(shuffled, 1):
                blind_id = f"{phase[0]}-{rng.getrandbits(48):012x}"
                mappings[judge][blind_id] = {
                    "task_id": entry["task_id"], "phase": phase, "order": index,
                }
    write_json(output / "blind_mapping_private.json", mappings)
    manifest = {
        "study_version": config["study_version"],
        "runtime_version": RUNTIME_VERSION,
        "instrument_version": audit.VERSION, "status": "prepared", "prepared_at": now(),
        "hypothesis": config["hypothesis"], "null_result": config["null_result"],
        "claim_policy": config["claim_policy"], "calibration_policy": config["calibration_policy"],
        "sampling": selection, "judges": judges, "settings": config["settings"],
        "requested_calls": requested_calls, "max_calls": min(max_calls, 200),
        "source_hashes": hashes,
        "catalog_sha256": audit.sha256((output / "catalog.json").read_bytes()),
        "controls_sha256": audit.sha256((output / "controls.json").read_bytes()),
        "blind_mapping_sha256": audit.sha256((output / "blind_mapping_private.json").read_bytes()),
        "system_prompt": prompt["system"],
        "input_allowlist": ["learning_target", "learner_context", "student_task"],
        "old_scores_and_arm_sent_to_judges": False,
        "judge_independence": "Distinct GPT-4.1 / GPT-5.4 series, same OpenAI family, not human or vendor-independent",
        "source_reads": [
            {"path": entry["source_path"], "sha256": entry["source_sha256"]}
            for entry in catalog
        ],
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def verify_frozen(output: Path, manifest: dict) -> None:
    for filename, field in (
        ("catalog.json", "catalog_sha256"), ("controls.json", "controls_sha256"),
        ("blind_mapping_private.json", "blind_mapping_sha256"),
    ):
        if audit.sha256((output / filename).read_bytes()) != manifest[field]:
            raise ValueError(f"Frozen {filename} changed")
    for source, expected in manifest["source_hashes"].items():
        if audit.sha256(resolve_path(source).read_bytes()) != expected:
            raise ValueError(f"Instrument source changed after freezing: {source}")


def judge_one(entry: dict, judge: str, blind_id: str, manifest: dict, output: Path, client, model: str) -> dict:
    destination = output / "judgments" / judge / f"{blind_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task_id": entry["task_id"], "judge": judge, "blind_id": blind_id,
        "model_name": model, "started_at": now(), "status": "request_started",
        "response_id": None, "usage": None, "raw_response": None,
        "model_calls": 0, "max_retries": 0,
    }
    try:
        user_input = audit.evidence_audit_input(entry)
    except (ValueError, KeyError, TypeError) as error:
        record.update(status="input_error", error={"type": type(error).__name__, "message": str(error)})
        write_json(destination, record)
        return record
    settings = manifest["settings"]
    request = {
        "model": model,
        "messages": [
            {"role": "system", "content": manifest["system_prompt"]},
            {"role": "user", "content": user_input},
        ],
        "response_format": {"type": "json_object"},
        "timeout": settings["timeout_seconds"],
    }
    if judge == "gpt54":
        request["max_completion_tokens"] = settings["max_completion_tokens"]
        request["reasoning_effort"] = settings["gpt54_reasoning_effort"]
    else:
        request["max_tokens"] = settings["max_completion_tokens"]
        request["temperature"] = settings["gpt41_temperature"]
    record.update(
        user_input=user_input, input_sha256=audit.sha256(user_input),
        request_sha256=audit.sha256(json.dumps(request, sort_keys=True)),
        effective_settings={key: value for key, value in request.items() if key != "messages"},
        model_calls=1,
    )
    write_json(destination, record)
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(**request)
    except OpenAIError as error:
        record.update(
            status="api_error",
            error={"type": type(error).__name__, "message": str(error)},
        )
    else:
        raw = response.choices[0].message.content or ""
        record.update(
            response_id=response.id, returned_model=response.model,
            usage=response.usage.model_dump() if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
            raw_response=raw,
        )
        try:
            record.update(audit.parse_evidence_audit(raw, audit.student_text(entry["task"])))
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            record.update(
                status="parse_error",
                error={"type": type(error).__name__, "message": str(error)},
            )
    record.update(latency_seconds=time.perf_counter() - started, finished_at=now())
    write_json(destination, record)
    return record


def control_performance(catalog: list[dict], results: list[dict], judges: list[str]) -> dict:
    indexed = {(result["task_id"], result["judge"]): result for result in results}
    rows = []
    for entry in catalog:
        for judge in judges:
            result = indexed.get((entry["task_id"], judge))
            for name, allowed in entry["expected"].items():
                observed = None
                field = "mathematics" if name == "math_status" else name
                validation_error = (result or {}).get("field_errors", {}).get(field)
                if result and result.get("status") in audit.PARSED_STATUSES and not validation_error:
                    observed = (
                        result["math_status"] if name == "math_status" else result["audit"][name]["status"]
                    )
                quote_verified = (
                    observed == "unknown" or bool(
                        result and result.get("quote_fidelity", {}).get(field, {}).get("all_verified")
                    )
                )
                rows.append({
                    "task_id": entry["task_id"], "role": entry["role"],
                    "judge": judge, "property": name, "expected_allowed": allowed,
                    "observed": observed, "matches": observed in allowed and quote_verified,
                    "field_validation_error": validation_error,
                    "quote_fidelity_valid": quote_verified,
                    "human_gold": False,
                })
    return {
        "interpretation": (
            "Frozen illustrative controls, not human gold or benchmark tuning. "
            "Two distinct held-out controls were not used to change this instrument. "
            "Label matches require usable field schemas and exact quotations, except legitimate unknowns."
        ),
        "by_role_and_judge": {
            f"{role}:{judge}": {
                "matching_property_checks": sum(row["matches"] for row in rows if row["role"] == role and row["judge"] == judge),
                "expected_property_checks": sum(row["role"] == role and row["judge"] == judge for row in rows),
            }
            for role in ("development_control", "holdout_control") for judge in judges
        },
        "rows": rows,
    }


def run_prepared(output: Path, phase: str, workers: int) -> dict:
    manifest = read_json(output / "manifest.json")
    if manifest.get("analysis_only"):
        raise ValueError("Parser sidecars are analysis-only; they cannot schedule model calls")
    verify_frozen(output, manifest)
    catalog = read_json(output / "catalog.json")["tasks"]
    controls = read_json(output / "controls.json")["tasks"]
    mappings = read_json(output / "blind_mapping_private.json")
    clients = {}
    for judge in manifest["judges"]:
        client, model = load_client(judge)
        clients[judge] = (client.with_options(max_retries=0), model)
    manifest.update(status="running", model_names={judge: value[1] for judge, value in clients.items()})
    write_json(output / "manifest.json", manifest)
    phases = ["calibration", "main"] if phase == "all" else [phase]
    for current in phases:
        entries = controls if current == "calibration" else catalog
        if not entries:
            continue
        indexed = {entry["task_id"]: entry for entry in entries}
        jobs = []
        for judge in manifest["judges"]:
            for blind_id, mapping in mappings[judge].items():
                if mapping["phase"] == current:
                    destination = output / "judgments" / judge / f"{blind_id}.json"
                    if not destination.exists():
                        jobs.append((indexed[mapping["task_id"]], judge, blind_id))
        existing_calls = sum(
            read_json(path).get("model_calls", 0)
            for path in (output / "judgments").glob("*/*.json")
        )
        if existing_calls + len(jobs) > manifest["max_calls"]:
            raise ValueError("Execution would exceed frozen request budget")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    judge_one, entry, judge, blind_id, manifest, output, *clients[judge]
                ): (entry["task_id"], judge)
                for entry, judge, blind_id in jobs
            }
            for future in as_completed(futures):
                result = future.result()
                print(f"{current} {result['judge']} {result['blind_id']}: {result['status']}", flush=True)
        if current == "calibration":
            results = [
                read_json(path) for path in (output / "judgments").glob("*/*.json")
                if read_json(path)["task_id"] in indexed
            ]
            performance = control_performance(controls, results, manifest["judges"])
            write_json(output / "calibration_summary.json", performance)
            parsed = Counter(
                result["judge"] for result in results if result["status"] in audit.PARSED_STATUSES
            )
            manifest["calibration_decision"] = {
                "parsed_by_judge": dict(parsed),
                "instrument_retuned": False,
                "proceed_rationale": (
                    "Paired task-evidence collection is executable; control misses and uncertainty "
                    "remain reported. No misclassification-triggered prompt tuning."
                ),
            }
            write_json(output / "manifest.json", manifest)
            if controls and any(parsed[judge] == 0 for judge in manifest["judges"]):
                manifest.update(status="blocked_no_parseable_calibration", finished_at=now())
                write_json(output / "manifest.json", manifest)
                return manifest
    verify_frozen(output, manifest)
    all_results = [read_json(path) for path in sorted((output / "judgments").glob("*/*.json"))]
    main_ids = {entry["task_id"] for entry in catalog}
    results = [result for result in all_results if result["task_id"] in main_ids]
    with (output / "judgments.jsonl").open("w") as stream:
        for result in all_results:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    summary = audit.aggregate_audits(catalog, results, manifest["judges"])
    summary["execution"] = {
        "actual_model_requests": sum(result.get("model_calls", 0) for result in all_results),
        "request_cap": manifest["max_calls"],
        "phase_status": phase,
        "calibration": read_json(output / "calibration_summary.json") if (output / "calibration_summary.json").exists() else None,
        "total_prompt_tokens": sum((result.get("usage") or {}).get("prompt_tokens", 0) for result in all_results),
        "total_completion_tokens": sum((result.get("usage") or {}).get("completion_tokens", 0) for result in all_results),
        "summed_request_latency_seconds": sum(result.get("latency_seconds", 0) for result in all_results),
    }
    write_json(output / "summary.json", summary)
    manifest.update(
        status=(
            "partial" if len(results) != len(catalog) * 2
            else "completed_with_errors" if any(result["status"] != "parsed" for result in all_results)
            else "completed"
        ),
        finished_at=now(), actual_calls=summary["execution"]["actual_model_requests"],
        source_integrity_unchanged=True,
    )
    write_json(output / "manifest.json", manifest)
    from scripts.report_pf_measurement_gap_study import report_run
    report_run(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--judges", nargs=2, default=["gpt41", "gpt54"])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-calls", type=int, default=200)
    parser.add_argument("--phase", choices=["calibration", "main", "all"], default="all")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    if not args.resume:
        manifest = prepare_run(
            args.output, args.config, args.catalog, args.benchmark, args.judges, args.max_calls
        )
        print(f"Frozen {manifest['requested_calls']} requested judgments in {args.output}", flush=True)
    if not args.prepare:
        run_prepared(args.output, args.phase, args.workers)


if __name__ == "__main__":
    main()
