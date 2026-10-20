"""Run one frozen, solution-blind diagnostic of PF attempts by LLM learners."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from src.simulation.pf_student import attempt_prompt, parse_attempt  # noqa: E402

DEFAULT_CONFIG = ROOT / "experiments/configs/pf_student_probe_20261011.json"


def _execute_request(request: dict, output: Path, clients: dict, settings: dict) -> dict:
    client, model = clients[request["model"]]
    attempt_dir = output / request["phase"] / request["id"]
    attempt_dir.mkdir(parents=True, exist_ok=False)
    payload, raw, metadata, api_error = benchmark._call_json(
        client,
        model,
        request["prompt"]["system"],
        request["prompt"]["user"],
        max_tokens=settings["max_tokens"],
        retries=0,
        trace_path=attempt_dir / "model_calls.jsonl",
        stage="student.attempt",
        temperature=settings["temperature"],
        timeout_seconds=settings["timeout_seconds"],
    )
    attempt, error = None, api_error
    status = "api_error" if api_error else "parsed"
    if not api_error:
        try:
            attempt = parse_attempt(payload)
        except ValueError as exc:
            status, error = "invalid_response", str(exc)
    benchmark._write_json(
        attempt_dir / "result.json",
        {
            "id": request["id"],
            "status": status,
            "error": error,
            "attempt": attempt,
            "payload": payload,
            "raw_text": raw,
            "model_metadata": metadata,
        },
    )
    return {
        "id": request["id"],
        "status": status,
        "phase": request["phase"],
        "result_path": str((attempt_dir / "result.json").relative_to(output)),
    }


def build_requests(config: dict) -> list[dict]:
    if config.get("path_codebook"):
        source = ROOT / config["path_codebook"]["path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != config["path_codebook"]["sha256"]:
            raise ValueError("Prospective path codebook changed before student evaluation")
    requests = []
    controls = [
        ("sum", "Calculate 6 + 4 + 2.", "12"),
        ("share", "What is one third of 12?", "4"),
    ]
    basic_context = {
        "subject": "mathematics",
        "assumed_prior_knowledge": [
            {"resource": "Basic arithmetic", "taught_as": "Add and divide simple numbers."}
        ],
    }
    for model in config["models"]:
        for control_id, question, answer in controls:
            for profile in config["profiles"][:2]:
                task = {
                    "status": "ready",
                    "title": "Arithmetic check",
                    "body": "Work independently.",
                    "question": question,
                }
                requests.append(
                    {
                        "id": f"calibration-{model}-{control_id}-{profile['id']}",
                        "phase": "calibration",
                        "model": model,
                        "task_id": control_id,
                        "profile_id": profile["id"],
                        "repeat": 1,
                        "expected_answer": answer,
                        "prompt": attempt_prompt(task, basic_context, profile),
                    }
                )
    for spec in config["tasks"]:
        path = ROOT / config["task_root"] / spec["path"]
        record = json.loads(path.read_text())
        task = record.get("task") or record.get("stages", {}).get("D2_D3", {}).get("task")
        manifest_path = ROOT / config["task_root"] / spec["family"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        context = manifest["shared_context"]["learner_context"]
        for model in config["models"]:
            for profile in config["profiles"]:
                effective_profile = {**profile}
                if profile.get("omit_resources"):
                    effective_profile["omit_resource"] = profile["omit_resources"][spec["family"]]
                if profile.get("add_resources_by_family"):
                    effective_profile["add_resources"] = profile["add_resources_by_family"][
                        spec["family"]
                    ]
                prompt = attempt_prompt(task, context, effective_profile)
                for repeat in range(1, config["repeats"] + 1):
                    requests.append(
                        {
                            "id": f"fresh-{spec['id']}-{model}-{profile['id']}-{repeat}",
                            "phase": "fresh",
                            "model": model,
                            "task_id": spec["id"],
                            "profile_id": profile["id"],
                            "repeat": repeat,
                            "source": str(path.relative_to(ROOT)),
                            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "learner_manifest": str(manifest_path.relative_to(ROOT)),
                            "learner_manifest_sha256": hashlib.sha256(
                                manifest_path.read_bytes()
                            ).hexdigest(),
                            "prompt": prompt,
                        }
                    )
    rng = random.Random(config["seed"])
    calibration = [item for item in requests if item["phase"] == "calibration"]
    fresh = [item for item in requests if item["phase"] == "fresh"]
    rng.shuffle(calibration)
    rng.shuffle(fresh)
    if len(calibration) != config["budget"]["calibration_calls"]:
        raise ValueError("Calibration schedule does not match its frozen budget")
    if len(fresh) != config["budget"]["fresh_calls"]:
        raise ValueError("Fresh schedule does not match its frozen budget")
    if len(requests) > config["budget"]["max_calls_total"]:
        raise ValueError("Schedule exceeds the frozen request budget")
    return calibration + fresh


def run(
    config_path: Path, output: Path, *, dry_run: bool = False, phase: str = "calibration"
) -> dict:
    config_path = config_path.resolve()
    output = output.resolve()
    config = json.loads(config_path.read_text())
    requests = build_requests(config)
    if phase not in {"calibration", "fresh"}:
        raise ValueError("Probe phase must be calibration or fresh")
    if phase == "fresh" and not dry_run:
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest["status"] != "calibration_completed":
            raise ValueError("Fresh probe requires a completed calibration, without replacement")
        if manifest["protocol"] != config or manifest["requests"] != requests:
            raise ValueError("Probe protocol or task inputs changed after calibration")
        for relative, digest in manifest["source_hashes"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Source changed after calibration: {relative}")
    else:
        output.mkdir(parents=True, exist_ok=False)
    sources = [
        config_path,
        Path(__file__),
        ROOT / "src/simulation/pf_student.py",
        ROOT / "src/evaluation/pf_rubric.py",
        ROOT / "scripts/run_pf_paper_benchmark.py",
        ROOT / "scripts/prior_methods/common.py",
    ]
    sources.extend(ROOT / item["source"] for item in requests if "source" in item)
    sources.extend(
        ROOT / item["learner_manifest"] for item in requests if "learner_manifest" in item
    )
    if config.get("path_codebook"):
        sources.append(ROOT / config["path_codebook"]["path"])
    if phase != "fresh" or dry_run:
        hashes = {}
        for source in dict.fromkeys(sources):
            relative = str(source.relative_to(ROOT))
            data = source.read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            snapshot = output / "source_snapshot" / relative
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(data)
        manifest = {
            "schema_version": "pf-student-probe-run/v1",
            "status": "dry_run" if dry_run else "running",
            "protocol": config,
            "source_hashes": hashes,
            "requests": requests,
            "attempts": [],
        }
    manifest["status"] = "dry_run" if dry_run else f"{phase}_running"
    benchmark._write_json(output / "manifest.json", manifest)
    if dry_run:
        return manifest
    clients = {}
    settings = config["settings"]
    active = [request for request in requests if request["phase"] == phase]
    workers = config.get("workers", 1)
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("Probe workers must be a positive integer")
    for request in active:
        model_selector = request["model"]
        if model_selector not in clients:
            client, model = load_client(model_selector)
            clients[model_selector] = (client.with_options(max_retries=0), model)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_execute_request, request, output, clients, settings) for request in active
        ]
        for future in concurrent.futures.as_completed(futures):
            item = future.result()
            manifest["attempts"].append(item)
            benchmark._write_json(output / "manifest.json", manifest)
            print(item["phase"], item["id"], item["status"], flush=True)
    manifest["status"] = "completed" if phase == "fresh" else "calibration_completed"
    benchmark._write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase", choices=("calibration", "fresh"), default="calibration")
    args = parser.parse_args()
    run(args.config, args.output, dry_run=args.dry_run, phase=args.phase)
