"""Matched original, ordinary-revision and learner-attempt revision pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_student_probe as student_report  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from src.evaluation.pf_rubric import learner_context, student_task_text  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_attempt_revision_20261011.json"
SYSTEM = """You are revising one mathematics Productive Failure task before instruction
on its target. Review its mathematical design, not merely its prose.
Preserve the target, learner prior-knowledge boundary, age appropriateness and
scenario purpose. Improve accessible starts, meaningful mathematical choices
or invention, and opportunities for distinct reasoning. Familiar methods may
succeed or fail; do not force failure or equate extra drawings with new methods.
Keep required comparison objects, definitions and permissions, while leaving
the central unknown for learners. Remove actual method/conclusion giveaways,
not all helpful support. Check quantities, units, feasibility, and valuation
rules. Clarify ambiguous inputs without supplying the target formula, answer,
ordered solution or requiring the intended conclusion.
You may change data, constraints or task structure when needed, but do not narrow
a requested invented measure/general allocation procedure to one routine answer.
Keep the problem compact and usable. If optional learner attempts are supplied,
consider their actual actions, but do not assume their arithmetic, interpretation
or guesses are valid. A repeated mistake is not automatically a task defect;
require support in task wording before fixing it. Do not optimise for any one
learner or give their solution to later students.
Return exactly JSON: {"status":"ready","title":"...","body":"...","question":"..."}.
The response is only the revised student exercise, not analysis or solutions."""


def save(path: Path, value: object) -> None:
    benchmark._write_json(path, value)


def inputs(config: dict, spec: dict) -> tuple[dict, dict, dict, list[dict]]:
    root = ROOT / config["source_root"]
    record = json.loads((root / spec["path"]).read_text())
    task = record.get("task") or record.get("stages", {}).get("D2_D3", {}).get("task")
    student_task_text(task)
    task = {"status": "ready", **{field: task[field] for field in ("title", "body", "question")}}
    manifest = json.loads((root / spec["family"] / "manifest.json").read_text())
    prior = learner_context(manifest["shared_context"]["learner_context"])
    previous = ROOT / config["previous_attempts"]
    old, records = student_report.load_results(previous)
    evidence = []
    for request in old["requests"]:
        if (
            request["phase"] != "fresh"
            or request["task_id"] != spec["previous_task_id"]
            or request["profile_id"] == "ordinary_solver"
        ):
            continue
        result = records[request["id"]]
        evidence.append(
            {
                "written_work": (
                    result["attempt"]["written_work"] if result["attempt"] else result["raw_text"]
                ),
                "answer": result["attempt"]["answer"] if result["attempt"] else None,
                "execution_status": result["status"],
                "unfinished": result["attempt"]["unfinished"] if result["attempt"] else None,
            }
        )
    if len(evidence) != 8:
        raise ValueError("Every selected task requires eight saved learner-role outputs")
    return task, prior, manifest["case"], evidence


def prepare(config: dict, output: Path, phase: str) -> list[dict]:
    selected = config["calibration_cases" if phase == "calibration" else "cases"]
    requests = []
    for spec in selected:
        task, prior, case, evidence = inputs(config, spec)
        common = {
            "student_task": task,
            "learner_context": prior,
            "internal_learning_target": case["target_concept"],
        }
        for arm in ("ordinary_revision", "attempt_revision"):
            user = dict(common)
            if arm == "attempt_revision":
                user["learner_attempts"] = evidence
            requests.append(
                {
                    "id": spec["id"],
                    "family": spec["family"],
                    "arm": arm,
                    "system": SYSTEM,
                    "user": json.dumps(user, ensure_ascii=False, indent=2),
                    "source": spec["path"],
                    "prior": prior,
                    "original": task,
                }
            )
    random.Random(config["seed"]).shuffle(requests)
    save(output / "requests.json", requests)
    return requests


def run(output: Path, phase: str) -> dict:
    config = json.loads(CONFIG.read_text())
    destination = output / phase
    destination.mkdir(parents=True, exist_ok=False)
    requests = prepare(config, destination, phase)
    expected = config["revision"]["calls_calibration" if phase == "calibration" else "calls_fresh"]
    if len(requests) != expected:
        raise ValueError("Revision schedule does not match the declared request cap")
    if phase == "fresh":
        old = json.loads((output / "calibration/manifest.json").read_text())
        if old["status"] != "completed":
            raise ValueError("Revision calibration must finish before the fresh run")
        for relative, digest in old["source_hashes"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Revision inputs changed after calibration: {relative}")
    sources = [
        CONFIG,
        Path(__file__),
        ROOT / "scripts/run_pf_paper_benchmark.py",
        ROOT / "scripts/prior_methods/common.py",
        ROOT / "src/evaluation/pf_rubric.py",
        ROOT / config["previous_attempts"] / "manifest.json",
    ]
    selected = config["calibration_cases" if phase == "calibration" else "cases"]
    for spec in selected:
        sources += [
            ROOT / config["source_root"] / spec["path"],
            ROOT / config["source_root"] / spec["family"] / "manifest.json",
        ]
    old = json.loads((ROOT / config["previous_attempts"] / "manifest.json").read_text())
    relevant = {spec["previous_task_id"] for spec in selected}
    ids = {
        request["id"]
        for request in old["requests"]
        if request["task_id"] in relevant and request["profile_id"] != "ordinary_solver"
    }
    sources += [
        ROOT / config["previous_attempts"] / item["result_path"]
        for item in old["attempts"]
        if item["id"] in ids
    ]
    hashes = {}
    for source in dict.fromkeys(sources):
        data = source.read_bytes()
        relative = str(source.relative_to(ROOT))
        hashes[relative] = hashlib.sha256(data).hexdigest()
        snapshot = destination / "source_snapshot" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
    manifest = {"status": "running", "protocol": config, "source_hashes": hashes, "results": []}
    save(destination / "manifest.json", manifest)
    client, model = load_client(config["revision"]["model"])
    client = client.with_options(max_retries=0)
    manifest["resolved_model"] = model
    for request in requests:
        attempt_dir = destination / request["id"] / request["arm"]
        attempt_dir.mkdir(parents=True, exist_ok=False)
        payload, raw, metadata, error = benchmark._call_json(
            client,
            model,
            request["system"],
            request["user"],
            max_tokens=config["revision"]["max_tokens"],
            retries=0,
            trace_path=attempt_dir / "model_calls.jsonl",
            stage="task.revision",
            timeout_seconds=config["revision"]["timeout_seconds"],
        )
        status, schema_error = ("api_error", error) if error else benchmark._validate_task(payload)
        usable = isinstance(payload, dict) and all(
            isinstance(payload.get(field), str) and payload[field].strip()
            for field in ("title", "body", "question")
        )
        task = (
            {
                "status": "ready",
                **{field: payload[field] for field in ("title", "body", "question")},
            }
            if usable
            else None
        )
        record = {
            "status": status,
            "task": task,
            "payload": payload,
            "raw_text": raw,
            "model_metadata": metadata,
            "error": schema_error,
            "quality_findings": [schema_error] if usable and schema_error else [],
        }
        save(attempt_dir / "result.json", record)
        manifest["results"].append(
            {
                "id": request["id"],
                "arm": request["arm"],
                "status": status,
                "result_path": str((attempt_dir / "result.json").relative_to(destination)),
            }
        )
        save(destination / "manifest.json", manifest)
        print(phase, request["id"], request["arm"], status, flush=True)
    manifest["status"] = "completed"
    save(destination / "manifest.json", manifest)
    return manifest


def prepare_evaluation(output: Path) -> dict:
    config = json.loads(CONFIG.read_text())
    manifest = json.loads((output / "fresh/manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Revisions must finish before evaluation")
    variants = output / "variants"
    variants.mkdir(parents=True, exist_ok=False)
    task_specs, unavailable = [], []
    blind, key = [], []
    for spec in config["cases"]:
        original, prior, case, _ = inputs(config, spec)
        save(
            variants / spec["family"] / "manifest.json",
            {
                "shared_context": {"learner_context": prior},
                "case": case,
            },
        )
        for arm in config["arms"]:
            record = (
                {"task": original, "status": "unchanged_original"}
                if arm == "original"
                else json.loads((output / "fresh" / spec["id"] / arm / "result.json").read_text())
            )
            path = f"{spec['family']}/{spec['id']}/{arm}/result.json"
            save(variants / path, record)
            task_id = f"{spec['id']}_{arm}"
            if record["task"] is None:
                unavailable.append(task_id)
            else:
                task_specs.append({"id": task_id, "family": spec["family"], "path": path})
            blind.append(
                {
                    "student_task": record["task"],
                    "learner_context": prior,
                    "target": case["target_concept"],
                }
            )
            key.append({"case_id": spec["id"], "arm": arm, "task_id": task_id})
    shuffled = list(zip(blind, key))
    random.Random(config["seed"] + 1).shuffle(shuffled)
    save(
        output / "task_review_packet.json",
        {f"task_{index:02d}": task for index, (task, _) in enumerate(shuffled, 1)},
    )
    save(
        output / "task_review_key.json",
        {f"task_{index:02d}": item for index, (_, item) in enumerate(shuffled, 1)},
    )
    evaluation = config["attempt_evaluation"]
    probe = {
        "schema_version": "pf-student-probe/v1",
        "question": config["question"],
        "task_root": str(variants.relative_to(ROOT)),
        "tasks": task_specs,
        "models": evaluation["models"],
        "profiles": evaluation["profiles"],
        "repeats": evaluation["repeats"],
        "workers": evaluation["workers"],
        "settings": evaluation["settings"],
        "seed": config["seed"],
        "budget": {
            "calibration_calls": 8,
            "fresh_calls": len(task_specs) * 12,
            "max_calls_total": 8 + len(task_specs) * 12,
        },
        "limitations": config["limits"],
    }
    save(output / "unavailable_variants.json", unavailable)
    save(output / "evaluation_config.json", probe)
    return probe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=("calibration", "fresh", "prepare_evaluation"),
        required=True,
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if args.phase == "prepare_evaluation":
        prepare_evaluation(output)
    else:
        run(output, args.phase)
