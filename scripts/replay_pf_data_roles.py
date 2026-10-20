#!/usr/bin/env python3
"""Regenerate D2b and D3 from frozen briefs with predeclared data-role expectations."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import design_data_stage as stage  # noqa: E402
from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts import run_situation_skeletons as runner  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.render_pf_writer_comparison import task_panel  # noqa: E402
from scripts.replay_pf_discovery_writer import numeric_coverage  # noqa: E402


def source_hashes(config_path: Path) -> dict[str, str]:
    paths = (
        Path(__file__),
        config_path,
        ROOT / "scripts/replay_pf_discovery_writer.py",
        ROOT / "scripts/prior_methods/common.py",
    )
    return {
        **stage._source_hashes(),
        **{str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
    }


def prepare(config_path: Path, output: Path) -> dict:
    config = json.loads(config_path.read_text())
    cases = config["cases"]
    ids = [case["id"] for case in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Test-set cases must be nonempty and unique")
    inputs = {}
    for case in cases:
        for field in ("expected_given", "expected_teacher_example", "expected_student_job"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"{case['id']} requires {field}")
        path = ROOT / config["source_directory"] / case["id"] / "result.json"
        inputs[case["id"]] = {
            "source": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    hashes = source_hashes(config_path)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if (
            manifest["config"] != config
            or manifest["inputs"] != inputs
            or manifest["source_hashes"] != hashes
        ):
            raise ValueError("Frozen inputs or implementation changed; use a new output directory")
        return manifest
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "pf-data-role-replay/v1",
        "created_at": diagnostic._now(),
        "config": config,
        "inputs": inputs,
        "source_hashes": hashes,
        "attempts": {},
    }
    diagnostic._write_json(manifest_path, manifest)
    return manifest


def replay_case(case_id: str, output: Path, manifest: dict, *, client, model: str) -> dict:
    item = next(case for case in manifest["config"]["cases"] if case["id"] == case_id)
    source = ROOT / manifest["inputs"][case_id]["source"]
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != manifest["inputs"][case_id]["sha256"]:
        raise ValueError(f"Frozen source changed: {source}")
    saved = json.loads(original)
    if model != saved["model"]:
        raise ValueError("Use the historical model for this fixed-model development comparison")
    case = runner._stored_case_input(source, case_id)
    context = runner._stored_prior_context(source, case_id)
    winner = runner._winner_from_result(source, case_id)
    if case is None or context is None or winner.design_brief is None:
        raise ValueError("Frozen case, prior context and selected brief are required")
    directory = output / case_id
    directory.mkdir(exist_ok=False)
    destination = directory / "result.json"
    trace_path = directory / "model_calls.jsonl"
    tracer = diagnostic.DiagnosticTracer(trace_path, case_id, model)
    record = {
        "schema_version": "pf-data-role-case/v1",
        "case_id": case_id,
        "model": model,
        "phase": (
            "calibration"
            if case_id in manifest["config"]["protocol"]["calibration_cases"]
            else "prespecified_development"
        ),
        "evidence_kind": manifest["config"]["protocol"]["evidence_kind"],
        "source_result": manifest["inputs"][case_id]["source"],
        "source_sha256": manifest["inputs"][case_id]["sha256"],
        "started_at": diagnostic._now(),
        "status": "running",
        "expectations": item,
        "case_input": case,
        "prior_context": context,
        "winner": winner.to_dict(),
        "historical_task": saved["stages"]["D2_D3"]["task"],
        "design_data": None,
        "task": None,
        "source_hashes": stage._source_hashes(),
    }
    diagnostic._write_json(destination, record)
    try:
        with patch.object(
            runner,
            "chat_json",
            diagnostic._traced_chat(tracer, "D2_D3", d1_prompt=False),
        ):
            data = stage.run_design_data(client, model, case, winner, context)
            record["design_data"] = data
            diagnostic._write_json(destination, record)
            if data["payload"] is not None:
                record["writer_request"] = stage._writer_request(case, winner, data, context)
                task, raw = stage.write_design_data_task(client, model, case, winner, data, context)
                record.update(task=task, task_raw_text=raw, status=task["status"])
                given = [
                    name
                    for name, metadata in data["payload"]["quantities"].items()
                    if metadata["role"] == "given"
                ]
                record["numeric_coverage"] = numeric_coverage(
                    task, data["payload"], raw_quantities=given
                )
            else:
                record.update(status=f"data_{data['status']}", error=data["error"])
    finally:
        error = sys.exc_info()[1]
        if error is not None:
            record.update(status="error", error=f"{type(error).__name__}: {error}")
        trace = diagnostic.trace_summary(trace_path)
        record.update(
            finished_at=diagnostic._now(),
            model_calls=trace["finished"],
            trace_summary=trace,
            source_hashes_after=stage._source_hashes(),
            source_artifact_unchanged=source.read_bytes() == original,
        )
        record["source_integrity_verified"] = (
            record["source_hashes"] == record["source_hashes_after"]
        )
        diagnostic._write_json(destination, record)
    return record


def run(config_path: Path, output: Path, case_ids: list[str]) -> dict:
    manifest = prepare(config_path, output)
    ids = [case["id"] for case in manifest["config"]["cases"]]
    chosen = case_ids or ids
    if len(chosen) != len(set(chosen)) or set(chosen) - set(ids):
        raise ValueError("Requested cases must be unique members of the test set")
    for case_id in chosen:
        if (output / case_id).exists():
            raise ValueError(f"Refusing to replace existing attempt: {case_id}")
    client, model = load_client(manifest["config"]["model_selector"])
    client = client.with_options(max_retries=0)
    for case_id in chosen:
        record = replay_case(case_id, output, manifest, client=client, model=model)
        manifest["attempts"][case_id] = {
            "status": record["status"],
            "model_calls": record["model_calls"],
        }
        manifest["source_integrity_unchanged"] = manifest["source_hashes"] == source_hashes(
            config_path
        )
        manifest["updated_at"] = diagnostic._now()
        diagnostic._write_json(output / "manifest.json", manifest)
        print(f"{case_id}: {record['status']} ({record['model_calls']} calls)", flush=True)
    return manifest


def render(output: Path) -> None:
    manifest = json.loads((output / "manifest.json").read_text())
    inspection_path = output / "inspection.json"
    notes = (
        {item["case_id"]: item for item in json.loads(inspection_path.read_text())["cases"]}
        if inspection_path.exists()
        else {}
    )
    sections = []
    for case in manifest["config"]["cases"]:
        path = output / case["id"] / "result.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        new_task = record["task"] or {
            "status": "blocked",
            "blocking_issues": [record.get("error") or record["status"]],
        }
        roles = Counter(
            metadata["role"]
            for metadata in ((record.get("design_data") or {}).get("payload") or {})
            .get("quantities", {})
            .values()
        )
        note = notes.get(case["id"], {}).get("finding", "Not yet directly inspected.")
        coverage = record.get("numeric_coverage", {}).get("status", "unavailable")
        sections.append(
            f"<section><h2>{html.escape(case['id'])}</h2>"
            f"<p>Predicted student job: {html.escape(case['expected_student_job'])}</p>"
            f"<p>Quantity roles: {html.escape(str(dict(roles)))}. "
            f"Numeral coverage: {html.escape(coverage)}."
            "</p><div class='pair'>"
            + task_panel(
                record["historical_task"], "Before: saved task", ROOT / record["source_result"]
            )
            + task_panel(new_task, "After: fresh data and writer", path.resolve())
            + f"</div><p class='inspection'>Assistant inspection: {html.escape(note)}</p></section>"
        )
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PF data roles: eight fixed-brief comparisons</title><style>
body{font:16px/1.55 system-ui,sans-serif;background:#f3f5f1;color:#23392f;margin:24px}
main{max-width:1400px;margin:auto}section{background:white;padding:24px;margin:20px 0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}
article{border:1px solid #ccc;padding:20px}
.prose,.question{white-space:pre-wrap}.question{background:#eef3ed;padding:16px}
table{border-collapse:collapse}th,td{border:1px solid #ddd;padding:7px}
.label,.source{font-size:13px}.inspection{border-left:4px solid #65846d;padding-left:14px}
@media(max-width:850px){.pair{grid-template-columns:1fr}}
</style></head><body><main><h1>Preserving the student's construction</h1>
<p>Selected development cases: frozen designs and prior context, fresh D2b data and D3 writing.
Not fresh end-to-end generation, human ratings, or student-outcome evidence.
Both data and writing change; the comparison does not isolate their causal effects.</p>
"""
        + "".join(sections)
        + "</main></body></html>"
    )
    (output / "tasks.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    if args.render_only:
        render(args.output)
    elif args.prepare_only:
        prepare(args.config, args.output)
    else:
        run(args.config, args.output, args.cases)
        render(args.output)


if __name__ == "__main__":
    main()
