"""Review anonymous attempt panels with a frozen, evidence-linked checklist."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import report_pf_student_probe as student_report  # noqa: E402
from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402
from scripts.prior_methods.common import load_client  # noqa: E402
from src.evaluation.pf_attempt_feedback import APPROACHES, retain_panel_review  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_student_diagnosis_20261011.json"


def prepare_panels(probe_output: Path, output: Path) -> dict:
    manifest, records = student_report.load_results(probe_output)
    groups = {}
    for request in manifest["requests"]:
        if request["phase"] != "fresh":
            continue
        groups.setdefault(request["task_id"], []).append(request)
    grouped = sorted(groups.items())
    rng = random.Random(20261012)
    rng.shuffle(grouped)
    panels, keys = {}, {}
    for number, (task_id, requests) in enumerate(grouped, 1):
        rng.shuffle(requests)
        label = f"panel_{number:02d}"
        task_text = json.loads(requests[0]["prompt"]["user"])["student_task"]
        entries, entry_keys = {}, {}
        for index, request in enumerate(requests, 1):
            if json.loads(request["prompt"]["user"])["student_task"] != task_text:
                raise ValueError("Task text differs within a learner panel")
            record = records[request["id"]]
            attempt_label = f"a{index:02d}"
            entries[attempt_label] = {
                "response_status": record["status"],
                "attempt": record["attempt"],
                "unparsed_raw_text": record["raw_text"] if record["attempt"] is None else None,
            }
            entry_keys[attempt_label] = request["id"]
        panels[label] = {"student_task": task_text, "attempts": entries}
        keys[label] = {"task_id": task_id, "attempts": entry_keys}
    output.mkdir(parents=True, exist_ok=True)
    benchmark._write_json(output / "panels.json", panels)
    benchmark._write_json(output / "panel_key.json", keys)
    return panels


def run(
    probe_output: Path,
    output: Path,
    *,
    phase: str,
    dry_run: bool = False,
) -> dict:
    config = json.loads(CONFIG.read_text())
    output.mkdir(parents=True, exist_ok=False)
    panels = prepare_panels(probe_output, output)
    limit = config["review"]["calibration_panels" if phase == "calibration" else "fresh_panels"]
    if len(panels) != limit:
        raise ValueError("Panel count does not match the frozen review budget")
    prompt_path = ROOT / config["review"]["prompt"]
    prompt = yaml.safe_load(prompt_path.read_text())
    system = prompt["system"] + "\nAPPROACH VOCABULARY:\n" + json.dumps(sorted(APPROACHES))
    requests = {
        label: {"system": system, "user": json.dumps(panel, ensure_ascii=False, indent=2)}
        for label, panel in panels.items()
    }
    sources = (
        CONFIG,
        Path(__file__),
        prompt_path,
        ROOT / "src/evaluation/pf_attempt_feedback.py",
        ROOT / "scripts/report_pf_student_probe.py",
        ROOT / "scripts/run_pf_paper_benchmark.py",
        ROOT / "scripts/prior_methods/common.py",
    )
    hashes = {}
    for source in sources:
        relative = str(source.relative_to(ROOT))
        data = source.read_bytes()
        hashes[relative] = hashlib.sha256(data).hexdigest()
        snapshot = output / "source_snapshot" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
    manifest = {
        "status": "dry_run" if dry_run else "running",
        "phase": phase,
        "protocol": config["review"],
        "prompt_version": prompt["version"],
        "source_hashes": hashes,
        "probe": str(probe_output),
        "probe_manifest_sha256": hashlib.sha256(
            (probe_output / "manifest.json").read_bytes()
        ).hexdigest(),
        "requests": requests,
        "results": [],
    }
    benchmark._write_json(output / "manifest.json", manifest)
    if dry_run:
        return manifest
    client, model = load_client(config["review"]["model"])
    client = client.with_options(max_retries=0)
    manifest["resolved_model"] = model
    for label, request in requests.items():
        result_path = output / label / "result.json"
        result_path.parent.mkdir(parents=True, exist_ok=False)
        payload, raw, metadata, api_error = benchmark._call_json(
            client,
            model,
            request["system"],
            request["user"],
            max_tokens=config["review"]["max_tokens"],
            retries=0,
            trace_path=result_path.parent / "model_calls.jsonl",
            stage="attempt_panel.review",
        )
        review, error = None, api_error
        status = "api_error" if api_error else "parsed"
        if not api_error:
            try:
                review = retain_panel_review(payload, panels[label])
                if review["evidence_errors"]:
                    status = "parsed_with_unverified_evidence"
            except ValueError as exc:
                status, error = "invalid_response", str(exc)
        benchmark._write_json(
            result_path,
            {
                "status": status,
                "review": review,
                "payload": payload,
                "raw_text": raw,
                "error": error,
                "model_metadata": metadata,
            },
        )
        manifest["results"].append(
            {
                "panel": label,
                "status": status,
                "result_path": str(result_path.relative_to(output)),
            }
        )
        benchmark._write_json(output / "manifest.json", manifest)
        print(phase, label, status, error or "", flush=True)
    manifest["status"] = "completed"
    benchmark._write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("calibration", "fresh"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.probe, args.output, phase=args.phase, dry_run=args.dry_run)
