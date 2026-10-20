"""Final bounded design-level feedback experiment with operational path audits."""

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

from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_path_coverage_final_20261012.json"


def source_input(config: dict, spec: dict) -> tuple[dict, dict, dict]:
    root = ROOT / config["source_root"] / spec["family"]
    manifest = json.loads((root / "manifest.json").read_text())
    record = json.loads((root / spec["number"] / "pipeline/result.json").read_text())
    return manifest, record, record["stages"]["D2_D3"]["brief_selection"]["selected_brief"]


def feedback_text(config: dict, spec: dict, arm: str, coverage: dict) -> str:
    manifest, record, brief = source_input(config, spec)
    value = {
        "instruction": config["design_instruction"],
        "original_design_brief": brief,
        "original_student_task": {
            field: record["stages"]["D2_D3"]["task"][field]
            for field in ("title", "body", "question")
        },
    }
    assessment_path = ROOT / config["source_root"] / "assessment.json"
    task_review = json.loads(assessment_path.read_text())["tasks"][
        f"{spec['family']}/{spec['number']}/pipeline"
    ]
    value["shared_task_only_review"] = task_review
    if arm == "coverage_feedback":
        # Case identifiers in a retrospective audit are metadata, never learner input.
        matches = [
            task for task in coverage["tasks"].values()
            if f"{spec['family']}/{spec['number']}/pipeline/result.json" in task["source"]
        ]
        if len(matches) != 1:
            raise ValueError("Coverage feedback must match exactly one saved design")
        audit = matches[0]
        value["coverage_instruction"] = config["coverage_instruction"]
        value["path_diagnosis"] = {
            "denominator": audit["denominator"],
            "paths": [{
                "design_quote": path["design_quote"],
                "kind": path["kind"],
                "operational_definition": path["operational_definition"],
                "reached_count": path["reached_count"],
                "not_observed_count": path["not_observed_count"],
                "unknown_count": path["unknown_count"],
                "observations": [{
                    "status": row["status"], "evidence": row["evidence"], "reason": row["reasons"],
                } for row in path["attempts"].values()],
            } for path in audit["paths"]],
            "diagnosis": audit["diagnosis"],
        }
    return json.dumps(value, ensure_ascii=False, indent=2)


def run(output: Path, phase: str) -> dict:
    config = json.loads(CONFIG.read_text())
    coverage = json.loads((output / "baseline_coverage.json").read_text())
    directory = output / phase
    directory.mkdir(parents=True, exist_ok=False)
    selected = [config["calibration"]] if phase == "calibration" else config["cases"]
    schedule = [(spec, arm) for spec in selected for arm in ("design_review", "coverage_feedback")]
    random.Random(config["seed"]).shuffle(schedule)
    sources = [CONFIG, Path(__file__), output / "baseline_coverage.json"]
    sources.append(ROOT / config["source_root"] / "assessment.json")
    sources += [ROOT / relative for relative in diagnostic.compute_source_hashes()]
    for spec in config["cases"] + [config["calibration"]]:
        sources += [
            ROOT / config["source_root"] / spec["family"] / "manifest.json",
            ROOT / config["source_root"] / spec["family"] / "fixed_d1.json",
            ROOT / config["source_root"] / spec["family"] / spec["number"] / "pipeline/result.json",
        ]
    hashes = {}
    for source in dict.fromkeys(sources):
        relative = str(source.relative_to(ROOT))
        data = source.read_bytes()
        hashes[relative] = hashlib.sha256(data).hexdigest()
        snapshot = directory / "source_snapshot" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
    if phase == "fresh":
        prior = json.loads((output / "calibration/manifest.json").read_text())
        if prior["status"] != "completed" or prior["source_hashes"] != hashes:
            raise ValueError("Source/protocol must remain frozen after calibration")
    manifest = {
        "status": "running", "protocol": config, "source_hashes": hashes,
        "schedule": [{"id": spec["id"], "arm": arm} for spec, arm in schedule], "results": [],
    }
    benchmark._write_json(directory / "manifest.json", manifest)
    for spec, arm in schedule:
        original, _, _ = source_input(config, spec)
        source_d1 = ROOT / config["source_root"] / spec["family"] / "fixed_d1.json"
        feedback = feedback_text(config, spec, arm, coverage)
        attempt_dir = directory / spec["id"] / arm
        benchmark._write_json(attempt_dir.parent / f"{arm}_input.json", {
            "design_feedback": feedback, "case": original["case"],
            "shared_context": original["shared_context"],
            "source_d1": str(source_d1.relative_to(ROOT)),
        })
        result = diagnostic.run_case_worker(
            original["case"]["id"], str(attempt_dir), config["generation"]["model"],
            1, str(source_d1), case_override=original["case"],
            shared_context=original["shared_context"], design_feedback=feedback,
        )
        if result["model_call_count"] > config["generation"]["per_attempt_max_calls"]:
            raise ValueError("Pipeline exceeded its derived bounded stage-request count")
        manifest["results"].append({
            "id": spec["id"], "arm": arm, "status": result["status"],
            "model_calls": result["model_call_count"],
            "result_path": str((attempt_dir / "result.json").relative_to(directory)),
        })
        benchmark._write_json(directory / "manifest.json", manifest)
        print(phase, spec["id"], arm, result["status"], result["model_call_count"], flush=True)
    manifest["status"] = "completed"
    benchmark._write_json(directory / "manifest.json", manifest)
    return manifest


def prepare_evaluation(output: Path) -> dict:
    config = json.loads(CONFIG.read_text())
    run = json.loads((output / "fresh/manifest.json").read_text())
    if run["status"] != "completed":
        raise ValueError("Design runs must finish before fresh evaluation")
    variants = output / "variants"
    variants.mkdir(parents=True, exist_ok=False)
    tasks, review, keys, designs, unavailable = [], {}, {}, {}, []
    entries = []
    for spec in config["cases"]:
        manifest, original, brief = source_input(config, spec)
        benchmark._write_json(variants / spec["family"] / "manifest.json", manifest)
        for arm in config["arms"]:
            record = original if arm == "original" else json.loads(
                (output / "fresh" / spec["id"] / arm / "result.json").read_text()
            )
            stage = record.get("stages", {}).get("D2_D3", {})
            task = stage.get("task")
            design = (stage.get("brief_selection") or {}).get("selected_brief")
            identifier = f"{spec['id']}_{arm}"
            path = f"{spec['family']}/{identifier}/result.json"
            benchmark._write_json(variants / path, record)
            if isinstance(task, dict) and task.get("status") == "ready":
                tasks.append({"id": identifier, "family": spec["family"], "path": path})
            else:
                unavailable.append(identifier)
            entries.append((identifier, {
                "student_task": ({field: task[field] for field in ("title", "body", "question")}
                                 if isinstance(task, dict) else None),
                "target": manifest["case"]["target_concept"],
                "learner_context": manifest["shared_context"]["learner_context"],
            }, design))
    random.Random(config["seed"]).shuffle(entries)
    for index, (identifier, value, design) in enumerate(entries, 1):
        label = f"task_{index:02d}"
        review[label] = value
        designs[label] = {
            **value,
            "design_brief": design,
            "path_freeze_rule": "Define exact mathematical actions before opening attempts. "
                                "Do not count diagram/ratio displays as different algorithms.",
        }
        keys[label] = identifier
    benchmark._write_json(output / "task_review_packet.json", review)
    benchmark._write_json(output / "design_codebook_packet.json", designs)
    benchmark._write_json(output / "review_key.json", keys)
    evaluation = config["evaluation"]
    probe = {
        "schema_version": "pf-student-probe/v1",
        "question": config["question"], "task_root": str(variants.relative_to(ROOT)),
        "tasks": tasks, "models": evaluation["models"], "profiles": evaluation["profiles"],
        "repeats": 2, "workers": 4, "seed": config["seed"],
        "settings": {"temperature": 0.7, "max_tokens": 2400, "timeout_seconds": 180,
                     "sdk_retries": 0},
        "budget": {"calibration_calls": 12, "fresh_calls": len(tasks) * 18,
                   "max_calls_total": 12 + len(tasks) * 18},
        "limitations": config["limits"],
    }
    benchmark._write_json(output / "evaluation_config.json", probe)
    benchmark._write_json(output / "unavailable_variants.json", unavailable)
    return probe


def freeze_codebook(output: Path) -> dict:
    codebook_path = output / "path_codebook.json"
    packet = json.loads((output / "design_codebook_packet.json").read_text())
    codebook = json.loads(codebook_path.read_text())
    if set(codebook["tasks"]) != set(packet):
        raise ValueError("Prospective codebook must cover every scheduled task variant")
    for label, row in codebook["tasks"].items():
        brief = packet[label]["design_brief"]
        design = "\n".join(
            [path["first_action"] for path in brief["approaches"]] + [brief["successful_route"]]
        )
        if not row["paths"]:
            raise ValueError("An available design needs at least one operational path")
        for path in row["paths"]:
            if path["design_quote"] not in design:
                raise ValueError("Prospective path quote does not match frozen design")
            if "attempts" in path:
                raise ValueError("Prospective path codebook cannot contain evaluated attempts")
    config_path = output / "evaluation_config.json"
    config = json.loads(config_path.read_text())
    config["path_codebook"] = {
        "path": str(codebook_path.relative_to(ROOT)),
        "sha256": hashlib.sha256(codebook_path.read_bytes()).hexdigest(),
    }
    benchmark._write_json(config_path, config)
    benchmark._write_json(output / "codebook_freeze.json", {
        "phase": "before_student_requests",
        "codebook": config["path_codebook"],
        "design_packet_sha256": hashlib.sha256(
            (output / "design_codebook_packet.json").read_bytes()
        ).hexdigest(),
    })
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("calibration", "fresh", "prepare_evaluation",
                                           "freeze_codebook"),
                        required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.phase == "prepare_evaluation":
        prepare_evaluation(output)
    elif args.phase == "freeze_codebook":
        freeze_codebook(output)
    else:
        run(output, args.phase)
