"""Run a solution-blind, source-normalized reference pathway check."""

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
from scripts import run_pf_student_probe as students  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from src.simulation.pf_student import attempt_prompt  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_kapur_reference_20261011.json"


def schedule(config: dict) -> list[dict]:
    rows = []
    for model in config["models"]:
        for profile in (
            {"id": "ordinary_solver", "condition": "solver"},
            config["learner_profiles"][0],
        ):
            task = {
                "status": "ready",
                "title": "Execution check",
                "body": "Travel at a constant speed.",
                "question": "A walker covers 300 metres at 50 metres per minute. How long is this?",
            }
            context = {
                "assumed_prior_knowledge": [
                    {"resource": "Speed and division", "taught_as": "Divide distance by speed."},
                ]
            }
            rows.append(
                {
                    "id": f"calibration-{model}-{profile['id']}",
                    "phase": "calibration",
                    "kind": "calibration",
                    "model": model,
                    "profile": profile["id"],
                    "repeat": 1,
                    "expected_answer": "6",
                    "prompt": attempt_prompt(task, context, profile),
                }
            )
        profiles = config["learner_profiles"] + [{"id": "ordinary_solver", "condition": "solver"}]
        for profile in profiles:
            kind = "solver" if profile["condition"] == "solver" else "learner"
            for repeat in range(1, config["repetitions"][kind] + 1):
                rows.append(
                    {
                        "id": f"fresh-{model}-{profile['id']}-{repeat}",
                        "phase": "fresh",
                        "kind": kind,
                        "model": model,
                        "profile": profile["id"],
                        "repeat": repeat,
                        "prompt": attempt_prompt(
                            config["task"], config["learner_context"], profile
                        ),
                    }
                )
        rows.append(
            {
                "id": f"prediction-{model}",
                "phase": "fresh",
                "kind": "prediction",
                "model": model,
                "profile": "prediction_only",
                "repeat": 1,
                "prompt": {
                    "system": config["prediction_prompt"],
                    "user": json.dumps(
                        {
                            "student_task": {
                                key: config["task"][key] for key in ("title", "body", "question")
                            },
                            "learner_record": config["learner_context"],
                        },
                        indent=2,
                    ),
                },
            }
        )
    random.Random(config["seed"]).shuffle(rows)
    if len(rows) != config["budget"]["total_calls"]:
        raise ValueError("Reference schedule exceeds or misses its frozen budget")
    return rows


def prediction_call(row: dict, output: Path, clients: dict, settings: dict) -> dict:
    client, model = clients[row["model"]]
    directory = output / "fresh" / row["id"]
    directory.mkdir(parents=True, exist_ok=False)
    payload, raw, metadata, error = benchmark._call_json(
        client,
        model,
        row["prompt"]["system"],
        row["prompt"]["user"],
        max_tokens=settings["max_tokens"],
        temperature=settings["temperature"],
        timeout_seconds=settings["timeout_seconds"],
        retries=0,
        trace_path=directory / "model_calls.jsonl",
        stage="pathway.prediction",
    )
    status = "api_error" if error else "parsed"
    if error is None:
        if not isinstance(payload, dict) or not isinstance(payload.get("approaches"), list):
            status, error = "invalid_response", "Prediction requires a list of approaches"
        elif any(
            not isinstance(item, dict)
            or not isinstance(item.get("description"), str)
            or not item["description"].strip()
            or not isinstance(item.get("possible_limitation"), str)
            for item in payload["approaches"]
        ):
            status, error = "invalid_response", "Prediction approaches require text fields"
    benchmark._write_json(
        directory / "result.json",
        {
            "status": status,
            "payload": payload,
            "raw_text": raw,
            "error": error,
            "model_metadata": metadata,
        },
    )
    return {
        "id": row["id"],
        "phase": row["phase"],
        "status": status,
        "result_path": str((directory / "result.json").relative_to(output)),
    }


def run(output: Path, phase: str) -> dict:
    config = json.loads(CONFIG.read_text())
    rows = schedule(config)
    if phase == "calibration":
        output.mkdir(parents=True, exist_ok=False)
        sources = [
            CONFIG,
            Path(__file__),
            ROOT / "scripts/run_pf_student_probe.py",
            ROOT / "scripts/run_pf_paper_benchmark.py",
            ROOT / "src/simulation/pf_student.py",
            ROOT / "src/evaluation/pf_rubric.py",
            ROOT / "scripts/prior_methods/common.py",
            ROOT / config["source"]["pdf"],
            ROOT / config["source"]["notes"],
            ROOT / config["source"]["normalized_record"],
        ]
        hashes = {}
        for source in sources:
            relative = str(source.relative_to(ROOT))
            data = source.read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            snapshot = output / "source_snapshot" / relative
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(data)
        manifest = {
            "status": "running",
            "protocol": config,
            "source_hashes": hashes,
            "requests": rows,
            "results": [],
        }
    else:
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest["status"] != "calibration_completed":
            raise ValueError("Reference run requires a completed calibration without replacement")
        if manifest["requests"] != rows or manifest["protocol"] != config:
            raise ValueError("Reference requests or protocol changed after calibration")
        for relative, digest in manifest["source_hashes"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Reference source changed after calibration: {relative}")
    manifest["status"] = f"{phase}_running"
    benchmark._write_json(output / "manifest.json", manifest)
    clients = {}
    for model in config["models"]:
        client, resolved = load_client(model)
        clients[model] = (client.with_options(max_retries=0), resolved)
    with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        futures = []
        for row in rows:
            if row["phase"] != phase:
                continue
            fn = prediction_call if row["kind"] == "prediction" else students._execute_request
            futures.append(pool.submit(fn, row, output, clients, config["settings"]))
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            manifest["results"].append(result)
            benchmark._write_json(output / "manifest.json", manifest)
            print(phase, result["id"], result["status"], flush=True)
    manifest["status"] = "calibration_completed" if phase == "calibration" else "completed"
    benchmark._write_json(output / "manifest.json", manifest)
    return manifest


def prepare_review(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Only completed reference requests can be reviewed")
    result_map = {item["id"]: item for item in manifest["results"]}
    rows = [row for row in manifest["requests"] if row["phase"] == "fresh"]
    random.Random(20261012).shuffle(rows)
    packet, key = {}, {}
    for index, row in enumerate(rows, 1):
        result = json.loads((output / result_map[row["id"]]["result_path"]).read_text())
        label = f"response_{index:02d}"
        packet[label] = {
            "response_type": "prediction" if row["kind"] == "prediction" else "attempt",
            "student_task": manifest["protocol"]["task"],
            "status": result["status"],
            "output": result.get("attempt") if row["kind"] != "prediction" else result["payload"],
            "raw_text": result["raw_text"],
        }
        key[label] = row["id"]
    benchmark._write_json(output / "review_packet.json", packet)
    benchmark._write_json(output / "review_key.json", key)
    return packet


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=("calibration", "fresh", "prepare_review"),
        required=True,
    )
    args = parser.parse_args()
    if args.phase == "prepare_review":
        prepare_review(args.output.resolve())
    else:
        run(args.output.resolve(), args.phase)
