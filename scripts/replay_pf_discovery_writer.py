#!/usr/bin/env python3
"""Replay the current design-data writer, preserving saved designs and numbers."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import design_data_stage as stage  # noqa: E402
from scripts import run_situation_skeletons as runner  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from scripts.render_pf_writer_comparison import task_panel  # noqa: E402
from scripts.replay_pf_writer import _stage  # noqa: E402
from src.generation.design_data import text_numerals, value_numerals  # noqa: E402


def numeric_coverage(
    task: dict, proposal: dict, *, raw_quantities: list[str] | None = None
) -> dict:
    """Check numeral multiplicity, not unit meaning or value-to-row associations."""
    if task["status"] != "ready":
        return {"status": "unavailable", "reason": "Writer did not produce a ready task."}
    withheld = {
        item["source"] for item in task.get("withheld", []) if item["kind"] == "quantity"
    }
    declared_retained = [
        name for name in proposal["values"]
        if f"proposal.quantities.{name}.description" not in withheld
        and proposal.get("quantities", {}).get(name, {}).get("role") != "teacher_example"
    ]
    retained = declared_retained if raw_quantities is None else raw_quantities
    if set(retained) - set(proposal["values"]):
        raise ValueError("Raw-quantity expectations reference missing quantities")

    expected = sum((value_numerals(proposal["values"][name]) for name in retained), Counter())
    text = "\n".join(task[field] for field in ("title", "body", "question"))
    observed = text_numerals(text)
    missing = expected - observed
    selection_matches = (
        None if raw_quantities is None else set(declared_retained) == set(raw_quantities)
    )
    return {
        "status": (
            "missing_numerals" if missing else
            "quantity_selection_mismatch" if selection_matches is False else "covered"
        ),
        "retained_quantities": retained,
        "withheld_quantities": [
            name for name in proposal["values"] if name not in declared_retained
        ],
        "quantity_selection_matches_expected": selection_matches,
        "expectation_source": (
            "writer_declaration_only"
            if raw_quantities is None else "external_raw_quantity_manifest"
        ),
        "missing": {str(number): count for number, count in sorted(missing.items())},
        "limitation": (
            "Token coverage does not establish units, ordering, associations or solvability."
        ),
    }


def replay(source_path: Path, output_dir: Path, *, client=None, model=None,
           prepare_only: bool = False, raw_quantities: list[str] | None = None) -> dict:
    source_path = source_path.resolve()
    source_bytes = source_path.read_bytes()
    saved = json.loads(source_bytes)
    source = _stage(saved) if "stages" in saved or "d2" in saved else saved
    case_id = saved.get("case") or saved.get("case_id")
    case = runner._stored_case_input(source_path, case_id)
    prior_context = runner._stored_prior_context(source_path, case_id)
    if case is None or prior_context is None:
        raise ValueError(f"Frozen case_input and prior_context required: {source_path}")
    record = {
        "schema_version": "pf-discovery-writer-replay/v1",
        "source_result": str(source_path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "case_id": case_id,
        "evidence_kind": "fixed_input_writer_replay_not_student_evidence",
        "historical_task": source.get("task"),
        "historical_reused_from": saved.get("reused_from"),
        "expected_raw_quantities": raw_quantities,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model_calls": 0,
    }
    destination = output_dir / f"{record['source_sha256'][:12]}.json"
    if destination.exists():
        raise ValueError(f"Refusing to overwrite replay output: {destination}")
    data_run = source.get("design_data")
    if not data_run or not data_run.get("accepted"):
        record.update(
            status="unavailable",
            reason="Saved D2b input is not accepted; writer-only replay cannot repair it.",
        )
    elif not source.get("task") or source["task"]["status"] != "ready":
        record.update(status="unavailable", reason="No historical ready task for comparison.")
    else:
        winner = runner._winner_from_result(source_path, case_id)
        proposal = data_run["payload"]
        request = stage._writer_request(case, winner, data_run, prior_context)
        record.update(
            model=model,
            requested_settings={"temperature": 0.7, "max_tokens": runner.PROPOSE_MAX_TOKENS},
            source_hashes=stage._source_hashes(),
            writer_request=request,
            frozen_inputs={
                "case_input": case, "prior_context": prior_context,
                "winner": winner.to_dict(), "design_data": data_run,
            },
            historical_numeric_coverage=numeric_coverage(
                source["task"], proposal, raw_quantities=raw_quantities
            ),
        )
        if prepare_only:
            record["status"] = "prepared"
        else:
            if model != saved.get("model"):
                raise ValueError("Use the historical model for a fixed-model writer comparison.")
            task, raw = stage.write_design_data_task(
                client, model, case, winner, data_run, prior_context
            )
            record.update(
                status=task["status"], task=task, raw_text=raw,
                model_calls=len(task.get("writer_attempts", [None])),
                numeric_coverage=numeric_coverage(task, proposal, raw_quantities=raw_quantities),
                source_hashes_after=stage._source_hashes(),
            )
            record["source_integrity_verified"] = (
                record["source_hashes"] == record["source_hashes_after"]
            )
    record["source_artifact_unchanged"] = source_bytes == source_path.read_bytes()
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(f"{record['status']}: {record['source_result']} -> {destination.name}", flush=True)
    return record


def render_results(output_dir: Path) -> None:
    sections = []
    for path in sorted(output_dir.glob("*.json")):
        record = json.loads(path.read_text())
        title = html.escape(record["source_result"])
        if record["status"] not in ("ready", "blocked"):
            reason = html.escape(record.get("reason", record["status"]))
            sections.append(f"<section><h2>{title}</h2><p>{reason}</p></section>")
            continue
        task = record["task"]
        withheld = "".join(
            f"<li><q>{html.escape(item['quote'])}</q> &mdash; "
            f"{html.escape(item['reason'])}</li>"
            for item in task["withheld"]
        )
        sections.append(
            f"<section><h2>{title}</h2><div class='pair'>"
            + task_panel(record["historical_task"], "Before: saved writer output",
                         ROOT / record["source_result"])
            + task_panel(task, "After: discovery-preserving writer", path.resolve())
            + "</div><details><summary>Teacher-only withheld material</summary><ul>"
            + withheld + "</ul></details>"
            + f"<p>Numeral coverage: {html.escape(record['numeric_coverage']['status'])}. "
            "Value-to-row associations and meaning still require reading.</p></section>"
        )
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>PF discovery writer: saved-input replay</title><style>
body{font:16px/1.5 system-ui;margin:30px;color:#24372e;background:#f5f7f3}
h1{font-size:27px}h2{font-size:15px;overflow-wrap:anywhere}
section{background:white;border:1px solid #ccd8ce;padding:20px;margin:20px 0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}
article{padding:18px;border:1px solid #ccd8ce;min-width:0}
.label{font-weight:600;color:#3c644b}.prose,.question{white-space:pre-wrap}
.question{background:#edf3e9;padding:12px}.table-wrap{overflow:auto}
table{border-collapse:collapse}th,td{padding:7px;border-bottom:1px solid #ddd}
@media(max-width:850px){.pair{grid-template-columns:1fr}}
</style><h1>Before and after: only the final writer rerun</h1>
<p>Same saved designs and values; exact model outputs. The baseline is historical,
not a repeated old-prompt run. Final-live cases continue fresh attempt 001 and are
not independent designs. No student responses or learning outcomes measured.</p>"""
    (output_dir / "side_by_side.html").write_text(
        page + "".join(sections) + "</html>\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", choices=("gpt41mini", "gpt41", "gpt54", "luna"), default="luna")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--checks", type=Path, help="JSON map: source path to expected raw quantities"
    )
    args = parser.parse_args()
    checks = None if args.checks is None else json.loads(args.checks.read_text())
    client, model = (None, None) if args.prepare_only else load_client(args.model)
    for source in args.source:
        raw_quantities = None
        if checks is not None:
            key = str(source.resolve().relative_to(ROOT))
            raw_quantities = checks[key]
            if not isinstance(raw_quantities, list) or any(
                not isinstance(name, str) for name in raw_quantities
            ):
                raise ValueError(f"Raw-quantity expectations must be a list of names: {key}")
        replay(
            source, args.output_dir, client=client, model=model,
            prepare_only=args.prepare_only, raw_quantities=raw_quantities,
        )
    render_results(args.output_dir)


if __name__ == "__main__":
    main()
