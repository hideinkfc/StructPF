"""Run frozen topic specifications through the current diagnostic pipeline."""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts.render_pf_writer_comparison import task_panel  # noqa: E402
from scripts.run_pf_paper_benchmark import _write_json  # noqa: E402


def source_hashes(config_path: Path, grounding_path: Path | None = None) -> dict[str, str]:
    hashes = diagnostic.compute_source_hashes()
    for path in (
        config_path,
        Path(__file__),
        ROOT / "data/curriculum_grounding/corpus_chunks.json",
        ROOT / "scripts/retrieve_prior_knowledge.py",
        ROOT / "src/utils/llm_client.py",
        ROOT / "src/utils/config.py",
    ):
        if path.is_file():
            hashes[str(path.resolve().relative_to(ROOT))] = diagnostic._compute_sha256(path)
    if grounding_path is not None:
        hashes[str(grounding_path.resolve().relative_to(ROOT))] = diagnostic._compute_sha256(
            grounding_path
        )
    return hashes


def prepare(
    config_path: Path, output: Path, grounding_path: Path | None = None
) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cases = config["cases"]
    ids = [case["id"] for case in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Cases must be nonempty and have unique IDs")
    for case in cases:
        for key in ("topic", "target_concept", "grade", "teacher_recently_taught"):
            if not case.get(key):
                raise ValueError(f"{case['id']} is missing {key}")
    grounding = (
        json.loads(grounding_path.read_text(encoding="utf-8"))
        if grounding_path is not None
        else None
    )
    if grounding is not None:
        for case_id in ids:
            diagnostic._frozen_grounding_records(grounding["cases"][case_id]["grounding_evidence"])
    hashes = source_hashes(config_path, grounding_path)
    path = output / "manifest.json"
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["config"] != config or manifest["source_hashes"] != hashes:
            raise ValueError("Frozen inputs or pipeline changed; use a new output directory")
        return manifest
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "pf-topic-sweep/v1",
        "created_at": diagnostic._now(),
        "config": config,
        "grounding": grounding,
        "source_hashes": hashes,
        "attempts": {},
        "protocol": {
            "fresh_D1_D2a_D2b_D3": True,
            "learning_commons": False,
            "old_outputs_reused": False,
            "attempts_per_topic": 1,
            "sdk_max_retries": 0,
            "failed_attempts_replaced": False,
            "prompt_tuning_during_sweep": False,
            "manual_inspection": "Assistant reading, not human ratings or student evidence.",
            "prior_source": (
                "Fresh D1 mapping and expansion of frozen official prerequisite excerpts; "
                "curriculum retrieval accuracy is not tested."
                if grounding is not None
                else "Fresh D1 curriculum retrieval, mapping and expansion."
            ),
        },
    }
    _write_json(path, manifest)
    return manifest


def run(
    config_path: Path,
    output: Path,
    case_ids: list[str],
    workers: int,
    grounding_path: Path | None = None,
) -> dict:
    if workers < 1:
        raise ValueError("workers must be positive")
    manifest = prepare(config_path, output, grounding_path)
    config = manifest["config"]
    cases = {case["id"]: case for case in config["cases"]}
    chosen = case_ids or list(cases)
    if len(chosen) != len(set(chosen)) or set(chosen) - cases.keys():
        raise ValueError("Requested case IDs must be unique and present in the frozen config")
    pending = []
    for case_id in chosen:
        directory = output / case_id
        if directory.exists():
            result_path = directory / "result.json"
            if not result_path.is_file():
                raise ValueError(f"Existing attempt lacks a result: {directory}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["status"] == "running":
                raise ValueError(f"Attempt still running or interrupted: {case_id}")
            print(f"{case_id}: preserving existing {result['status']}", flush=True)
            manifest["attempts"][case_id] = {
                "status": result["status"],
                "error": result.get("error"),
                "model_calls": result["model_call_count"],
            }
        else:
            pending.append(case_id)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for case_id in pending:
            case = {**config["shared_context"], **cases[case_id]}
            future = executor.submit(
                diagnostic.run_case_worker,
                case_id,
                str(output / case_id),
                config["model_selector"],
                config["proposal_k"],
                case_override=case,
                shared_context=config["shared_context"],
                evidence_k=config["evidence_k"],
                max_resources=config["max_resources"],
                d1_condition=config["d1_condition"],
                grounding_evidence=(
                    manifest["grounding"]["cases"][case_id]["grounding_evidence"]
                    if manifest["grounding"] is not None
                    else None
                ),
            )
            futures[future] = case_id
        for future in concurrent.futures.as_completed(futures):
            case_id = futures[future]
            result = future.result()
            manifest["attempts"][case_id] = {
                "status": result["status"],
                "error": result.get("error"),
                "model_calls": result["model_call_count"],
            }
            _write_json(output / "manifest.json", manifest)
            print(f"{case_id}: {result['status']} ({result['model_call_count']} calls)", flush=True)
    manifest["source_integrity_unchanged"] = (
        manifest["source_hashes"] == source_hashes(config_path, grounding_path)
    )
    manifest["status_counts"] = dict(
        Counter(item["status"] for item in manifest["attempts"].values())
    )
    manifest["updated_at"] = diagnostic._now()
    _write_json(output / "manifest.json", manifest)
    return manifest


def render(output: Path) -> None:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    inspection_path = output / "inspection.json"
    inspection = (
        json.loads(inspection_path.read_text(encoding="utf-8")) if inspection_path.exists() else {}
    )
    notes = {item["case_id"]: item for item in inspection.get("cases", [])}
    sections = []
    for case in manifest["config"]["cases"]:
        path = (output / case["id"] / "result.json").resolve()
        if path.exists():
            result = json.loads(path.read_text(encoding="utf-8"))
            task = result.get("stages", {}).get("D2_D3", {}).get("task")
            status = result["status"]
            content = (
                task_panel(task, "Exact fresh task", path)
                if task is not None
                else f"<p>No student task: {html.escape(status)}. "
                f"{html.escape(result.get('error') or '')}</p>"
            )
        else:
            status, content = "not_run", "<p>Not run yet.</p>"
        note = notes.get(case["id"])
        detail = (
            "<aside><h3>Assistant inspection (not student evidence)</h3>"
            + "".join(
                f"<p><strong>{html.escape(key.replace('_', ' '))}:</strong> "
                f"{html.escape(str(value))}</p>"
                for key, value in note.items()
                if key != "case_id"
            )
            + "</aside>"
            if note
            else "<aside>Manual inspection pending.</aside>"
        )
        sections.append(
            f'<section id="{html.escape(case["id"], quote=True)}">'
            f"<h2>{html.escape(case['topic'])} - {html.escape(status)}</h2>"
            f"<p>Target: {html.escape(case['target_concept'])}</p>{content}{detail}</section>"
        )
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fresh PF tasks: twenty-topic inspection</title><style>
body{font-family:system-ui,sans-serif;line-height:1.55;max-width:1050px;margin:30px auto;
padding:0 20px;color:#24372e;background:#f4f6f3}section{background:white;padding:24px;
border:1px solid #d5ddd5;border-radius:10px;margin:22px 0}article{padding:10px}
.prose,.question{white-space:pre-wrap}.question,aside{padding:16px;background:#edf3e9}
table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd}
aside{margin-top:15px;background:#f8f3e7}a{color:#245f47}.source,.label{font-size:13px}
</style></head><body><h1>Twenty fresh PF topic attempts</h1>
<p>Current full pipeline; one attempt per topic. Prompts frozen throughout.
Exact model wording is unedited. Blocked and failed attempts remain visible.
Inspection is assistant reading, not a human rating, student response or learning result.</p>"""
    (output / "tasks.html").write_text(
        page + "".join(sections) + "</body></html>", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", nargs="+", default=[])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--grounding", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    if args.render_only:
        render(args.output_dir)
        return
    if args.prepare_only:
        prepare(args.config, args.output_dir, args.grounding)
    else:
        run(args.config, args.output_dir, args.case, args.workers, args.grounding)
    render(args.output_dir)


if __name__ == "__main__":
    main()
