"""Export the grounding study's immutable attempts into the shared audit catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_grounding_study as study  # noqa: E402

CATALOG_FIELDS = (
    "task_id",
    "task",
    "learner_context",
    "learning_target",
    "source_path",
    "source_sha256",
    "arm",
    "case_id",
    "repeat",
)
EVALUATOR_FIELDS = ("task_id", "task", "learner_context", "learning_target")
REPORTING_BOUNDARY = {
    "design": "Three arms; five targets with four repeats, giving twenty matched slots per arm.",
    "independent_blocks": 5,
    "matched_slots_per_arm": 20,
    "uncertainty_unit": "Target; repetitions are nested within targets.",
    "primary_contrast": "B-A",
    "secondary_contrast": "C-B",
    "package_contrast": "C-A",
    "interpretation": "Bounded pilot: descriptive effects, uncertainty and per-target consistency.",
    "prohibited_analysis": [
        "Treating twenty matched slots as independent pairs in a sign test",
        "Requiring fifteen out of twenty slot wins for significance",
    ],
    "five_target_two_sided_sign_test_minimum_p": 0.0625,
    "statistics_owner": "Parent shared reporting implementation",
    "additional_generation_or_simulated_attempts": False,
}


def catalog_record(output: Path, item: dict, cases: dict) -> dict:
    directory = output / item["attempt_path"]
    source = directory / "result.json"
    if (directory / "completed.json").is_file():
        result = study.existing_result(directory)
        status = result["status"]
        candidate = result.get("stages", {}).get("D2_D3", {}).get("task")
        produced = study.task_produced(candidate)
        task = (
            {field: candidate[field] for field in ("title", "body", "question")}
            if produced
            else None
        )
        error = result.get("error")
        source_sha256 = study.digest(source)
    else:
        status = "running" if directory.exists() else "not_run"
        task, produced, source_sha256 = None, False, None
        error = None
    shared = study.read_json(output / "inputs" / item["case_id"] / f"context_{item['arm']}.json")
    return {
        "task_id": item["task_id"],
        "task": task,
        "learner_context": shared["learner_context"],
        "learning_target": cases[item["case_id"]]["target_concept"],
        "source_path": study.relative(source),
        "source_sha256": source_sha256,
        "arm": item["arm"],
        "case_id": item["case_id"],
        "repeat": item["repeat"],
        "status": status,
        "produced": produced,
        "error": error,
    }


def preserve_legacy_lists(output: Path) -> dict:
    preserved = {}
    for name in ("all_tasks", "calibration_tasks", "evaluator_input"):
        path = output / f"{name}.json"
        legacy = output / f"{name}_legacy_list.json"
        if path.is_file() and isinstance(study.read_json(path), list):
            if legacy.exists() and study.digest(path) != study.digest(legacy):
                raise ValueError(f"Cannot overwrite a different historical legacy export: {legacy}")
            if not legacy.exists():
                legacy.write_bytes(path.read_bytes())
        if legacy.is_file():
            preserved[legacy.name] = study.digest(legacy)
    return preserved


def export_catalog(output: Path) -> dict:
    manifest_path = output / "manifest.json"
    manifest = study.read_json(manifest_path)
    study.verify_inputs(output, manifest)
    cases = {
        case["id"]: case
        for case in manifest["config"]["cases"] + manifest["config"]["calibration_cases"]
    }
    by_phase = {
        phase: [
            catalog_record(output, item, cases)
            for item in manifest["schedule"]
            if item["phase"] == phase
        ]
        for phase in ("main", "calibration")
    }
    legacy = preserve_legacy_lists(output)
    study.save_json(output / "all_tasks.json", {"tasks": by_phase["main"]})
    study.save_json(output / "calibration_tasks.json", {"tasks": by_phase["calibration"]})
    evaluator = [
        {field: record[field] for field in EVALUATOR_FIELDS}
        for record in by_phase["main"]
        if record["produced"]
    ]
    study.save_json(output / "evaluator_input.json", {"tasks": evaluator})
    source = Path(__file__).resolve()
    snapshot = output / "export_source_snapshot" / study.relative(source)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(source.read_bytes())
    interface = {
        "schema_version": "pf-grounding-shared-catalog/v1",
        "exported_at_utc": study.diagnostic._now(),
        "generation_manifest_sha256": study.digest(manifest_path),
        "exporter_source_sha256": study.digest(source),
        "catalog": "all_tasks.json",
        "catalog_fields": list(CATALOG_FIELDS),
        "missing_or_failed_task": (
            "Task is null, produced is false, and status remains explicit; never blank task text."
        ),
        "main_scheduled_records": len(by_phase["main"]),
        "main_produced_records": len(evaluator),
        "calibration_scheduled_records": len(by_phase["calibration"]),
        "evaluator_input": "evaluator_input.json",
        "evaluator_fields": list(EVALUATOR_FIELDS),
        "evaluator_arm_labels": False,
        "evaluator_missing_or_failed_records": "Excluded; retained explicitly in all_tasks.json.",
        "preserved_original_list_exports": legacy,
        "reporting_boundary": REPORTING_BOUNDARY,
        "provenance_boundary": (
            "Post-generation interface adaptation and pre-evaluation reporting instructions. "
            "The original generation manifest, inputs, source snapshots and attempts are unchanged."
        ),
    }
    study.save_json(output / "catalog_interface.json", interface)
    return interface


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=study.DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(export_catalog(args.output_dir.resolve()), indent=2))


if __name__ == "__main__":
    main()
