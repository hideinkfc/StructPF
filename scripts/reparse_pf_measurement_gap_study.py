"""Mechanically reparse immutable PF audit responses into a versioned sidecar."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_pf_measurement_gap_study import report_run  # noqa: E402
from scripts.run_pf_measurement_gap_study import control_performance  # noqa: E402
from src.evaluation import pf_evidence_audit as audit  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def reparse_record(record: dict, entry: dict) -> dict:
    result = copy.deepcopy(record)
    result["previous_parse_status"] = record["status"]
    if "error" in record:
        result["previous_parse_error"] = record["error"]
    raw = record.get("raw_response")
    if not isinstance(raw, str) or not raw.strip():
        result["reparse_status"] = "not_applicable_no_raw_response"
        return result
    result.pop("error", None)
    try:
        parsed = audit.parse_evidence_audit(raw, audit.student_text(entry.get("task")))
    except (ValueError, json.JSONDecodeError) as error:
        result.update(
            status="parse_error",
            error={"type": type(error).__name__, "message": str(error)},
        )
    else:
        result.update(parsed)
    result["reparse_status"] = "processed_without_model_call"
    return result


def reparse_run(source: Path, output: Path) -> dict:
    source = source.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = load(source / "manifest.json")
    old_summary = load(source / "summary.json")
    catalog = load(source / "catalog.json")["tasks"]
    controls = load(source / "controls.json")["tasks"]
    entries = {entry["task_id"]: entry for entry in [*catalog, *controls]}
    source_hashes = {
        name: audit.sha256((source / name).read_bytes())
        for name in (
            "manifest.json",
            "catalog.json",
            "controls.json",
            "judgments.jsonl",
            "summary.json",
        )
    }
    original_prompt_hash = manifest["source_hashes"].get(
        "src/evaluation/prompts/pf_evidence_audit_v1.yaml"
    )
    if audit.sha256(audit.PROMPT_PATH.read_bytes()) != original_prompt_hash:
        raise ValueError(
            "The frozen judge prompt changed; mechanical reparse requires identical prompt"
        )
    previous = output / "previous_analysis_v1_2"
    previous.mkdir()
    previous_files = {
        path
        for path in source.iterdir()
        if path.is_file()
        and (
            path.suffix in (".md", ".html")
            or path.name
            in {
                "summary.json",
                "calibration_summary.json",
                "arm_descriptive_rates.json",
                "gallery_index.json",
                "disagreement_gallery_index.json",
                "review_pack_labels_hidden.json",
                "review_pack_mapping_private.json",
            }
        )
    }
    for path in previous_files:
        shutil.copy2(path, previous / path.name)
    corrected = []
    records = [json.loads(line) for line in (source / "judgments.jsonl").read_text().splitlines()]
    for record in records:
        entry = entries[record["task_id"]]
        result = reparse_record(record, entry)
        original_path = source / "judgments" / record["judge"] / f"{record['blind_id']}.json"
        result["original_record_path"] = str(original_path)
        result["original_record_sha256"] = audit.sha256(original_path.read_bytes())
        if result.get("raw_response") != record.get("raw_response"):
            raise AssertionError("Raw response changed during mechanical parsing")
        destination = output / "judgments" / record["judge"] / f"{record['blind_id']}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        write(destination, result)
        corrected.append(result)
    for name in ("catalog.json", "controls.json", "selection_frozen.json"):
        shutil.copy2(source / name, output / name)
    with (output / "judgments.jsonl").open("x") as stream:
        for result in corrected:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    main_ids = {entry["task_id"] for entry in catalog}
    control_ids = {entry["task_id"] for entry in controls}
    main_results = [result for result in corrected if result["task_id"] in main_ids]
    control_results = [result for result in corrected if result["task_id"] in control_ids]
    summary = audit.aggregate_audits(catalog, main_results, manifest["judges"])
    calibration = control_performance(controls, control_results, manifest["judges"])
    write(output / "calibration_summary.json", calibration)
    summary["execution"] = {
        **old_summary["execution"],
        "calibration": calibration,
        "phase_status": "mechanical_parser_sidecar",
        "new_model_requests": 0,
    }
    correction = {
        "parser_version": audit.PARSER_VERSION,
        "analysis_version": audit.ANALYSIS_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_run": str(source),
        "source_file_hashes": source_hashes,
        "prompt_unchanged": True,
        "raw_responses_unchanged": True,
        "new_model_requests": 0,
        "changes": [
            "Validate findings independently; invalid fields retain raw values and explicit ValidationErrors.",
            "Accept strictly validated quoted ConcernWitness objects, without stringification.",
            "Retain valid sibling findings; failed fields are unavailable rather than substantive rejection.",
            "A math concern, including one attached to model_recomputed, never becomes a math support pass.",
        ],
        "parser_source_hashes": {
            str(path.relative_to(ROOT)): audit.sha256(path.read_bytes())
            for path in (
                ROOT / "src/evaluation/pf_evidence_audit.py",
                ROOT / "scripts/run_pf_measurement_gap_study.py",
                ROOT / "scripts/report_pf_measurement_gap_study.py",
                Path(__file__),
            )
        },
    }
    summary["parser_correction"] = correction
    new_manifest = {
        **manifest,
        "status": "completed_parser_reanalysis",
        "analysis_only": True,
        "parser_correction": correction,
    }
    write(output / "manifest.json", new_manifest)
    write(output / "summary.json", summary)
    write(output / "parser_correction.json", correction)
    old_calibration = old_summary["execution"].get("calibration")
    comparison = {
        "new_model_requests": 0,
        "old_parsed_judgments": old_summary["parsed_judgments"],
        "new_usable_json_audits": summary["parsed_judgments"],
        "new_fully_valid_judgments": summary["fully_valid_judgments"],
        "new_partially_valid_judgments": summary["partially_valid_judgments"],
        "old_high_score_findings": old_summary["same_task_high_score_findings"],
        "new_high_score_findings": summary["same_task_high_score_findings"],
        "outcome_count_comparison": {
            name: {
                "old": {key: values[key] for key in ("pass", "concern", "unknown")},
                "new": {key: summary["rates"][name][key] for key in ("pass", "concern", "unknown")},
            }
            for name, values in old_summary["rates"].items()
        },
        "old_control_checks": old_calibration["by_role_and_judge"] if old_calibration else None,
        "new_control_checks": calibration["by_role_and_judge"],
        "field_errors": summary["field_validation_error_counts"],
        "interpretation": (
            "Differences are consequences of field-local parsing of identical responses, not new model evidence "
            "or prompt tuning. Valid sibling fields recovered; invalid fields remain unknown."
        ),
    }
    write(output / "comparison_to_previous.json", comparison)
    report_run(output)
    for name, expected in source_hashes.items():
        if audit.sha256((source / name).read_bytes()) != expected:
            raise AssertionError(f"Original source changed during parsing: {name}")
    write(
        output / "verification.json",
        {
            "original_source_files_unchanged": True,
            "raw_response_identity_checks": len(records),
            "new_model_requests": 0,
            "previous_reports_archived": sorted(path.name for path in previous_files),
        },
    )
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.source / "analysis_v1_3"
    comparison = reparse_run(args.source, output)
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
