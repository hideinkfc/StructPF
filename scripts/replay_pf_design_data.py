#!/usr/bin/env python3
"""Recheck saved D2b data and replay recorded replies without model calls.

Optional stress inputs deliberately alter saved numbers. They are software
checks, not fresh generation or evidence of student learning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import design_data_stage as stage  # noqa: E402
from scripts import run_situation_skeletons as runner  # noqa: E402
from src.generation.design_data import check_proposal, proposal_from_payload  # noqa: E402


class SavedRepliesExhaustedError(RuntimeError):
    pass


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise ValueError(f"Refusing to overwrite replay output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _negative_first(value):
    if isinstance(value, list):
        return [_negative_first(value[0]), *deepcopy(value[1:])]
    return -abs(value) - 1


def replay_result(path: Path, *, stress_dir: Path | None = None) -> dict:
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    saved = json.loads(path.read_text())
    source = saved
    if isinstance(saved.get("stages"), dict) and isinstance(saved["stages"].get("D2_D3"), dict):
        source = saved["stages"]["D2_D3"]
    elif isinstance(saved.get("d2"), dict):
        source = saved["d2"]
    case_id = saved.get("case") or saved.get("case_id")
    data = source.get("design_data")
    report = {
        "source": str(path),
        "source_sha256": before,
        "case_id": case_id,
        "evidence_kind": "offline_saved_input_replay",
        "model_calls": 0,
        "historical_status": None if data is None else data["status"],
        "historical_task_status": (source.get("task") or {}).get("status"),
        "recheck": None,
        "recorded_reply_replay": None,
        "writer_schema_replay": None,
        "stress": None,
    }
    if data is None:
        report["unavailable_reason"] = "No saved D2b run; cannot replay an API failure as a reply."
    else:
        case = runner._stored_case_input(path, case_id)
        context = runner._stored_prior_context(path, case_id)
        if case is None or context is None:
            raise ValueError(f"Replay requires frozen case_input and prior_context: {path}")
        winner = runner._winner_from_result(path, case_id)
        replies = iter(data["attempts"])
        requests = []

        def saved_reply(client, model, system, user, **kwargs):
            try:
                reply = next(replies)
            except StopIteration as exc:
                raise SavedRepliesExhaustedError(
                    "Current loop needs a reply not present in the trace."
                ) from exc
            actual_stage = "repair" if system.startswith("Repair only") else "propose"
            if reply["stage"] != actual_stage:
                raise ValueError(
                    f"Saved {reply['stage']} reply cannot answer {actual_stage}: {path}"
                )
            requests.append({"system": system, "user": user})
            return deepcopy(reply["payload"]), reply["raw_text"]

        with patch.object(runner, "chat_json", saved_reply):
            try:
                replay = stage.run_design_data(
                    None, saved.get("model", "saved"), case, winner, context,
                    require_roles=False,
                )
            except SavedRepliesExhaustedError as exc:
                report["recorded_reply_replay"] = {
                    "status": "unavailable",
                    "reason": str(exc),
                    "requests": requests,
                }
            else:
                report["recorded_reply_replay"] = replay
                report["recorded_replies_consumed"] = len(requests)
                report["recorded_replies_unused"] = len(data["attempts"]) - len(requests)

        proposal = data["payload"]
        if proposal is not None:
            proposal = proposal_from_payload(proposal, stage._requirements(winner))
            report["recheck"] = check_proposal(proposal)
            if report["recheck"]["accepted"]:
                task = source.get("task")
                if task is not None:
                    with patch.object(
                        runner,
                        "chat_json",
                        return_value=(deepcopy(task), source.get("task_raw_text", "")),
                    ):
                        writer_task, _ = stage.write_design_data_task(
                            None,
                            saved.get("model", "saved"),
                            case,
                            winner,
                            {"payload": proposal, "check": report["recheck"]},
                            context,
                        )
                    report["writer_schema_replay"] = {
                        "status": writer_task["status"],
                        "blocking_issues": writer_task["blocking_issues"],
                        "evidence_kind": "saved_reply_schema_check_not_prose_evaluation",
                    }
                if stress_dir is not None:
                    for name, value in proposal["values"].items():
                        altered = deepcopy(proposal)
                        altered["values"][name] = _negative_first(value)
                        initial_check = check_proposal(altered)
                        if initial_check["status"] == "rejected":
                            break
                    if initial_check["status"] != "rejected":
                        report["stress"] = {
                            "status": "unavailable",
                            "reason": "This perturbation does not isolate a numerical failure.",
                            "initial_check": initial_check,
                        }
                    else:
                        stress_path = stress_dir / f"{case_id}_{before[:12]}.json"
                        _write_json(
                            stress_path,
                            {
                                "schema_version": "pf-design-data/v1",
                                "case": case_id,
                                "case_input": case,
                                "prior_context": context,
                                "winner": winner.to_dict(),
                                "reused_from": str(path),
                                "input_provenance": "controlled_negative_value_perturbation",
                                "design_data_history": [data],
                                "design_data": {
                                    "status": "rejected",
                                    "accepted": False,
                                    "payload": altered,
                                    "check": initial_check,
                                    "attempts": [],
                                    "error": initial_check["reason"],
                                },
                            },
                        )
                        with patch.object(
                            runner,
                            "chat_json",
                            return_value=(
                                {"values": deepcopy(proposal["values"])},
                                "Controlled restoration of saved values",
                            ),
                        ):
                            repaired = stage.run_design_data(
                                None,
                                saved.get("model", "saved"),
                                case,
                                winner,
                                context,
                                initial_proposal=altered,
                            )
                        report["stress"] = {
                            "evidence_kind": "controlled_perturbation_with_mock_repair",
                            "input": str(stress_path),
                            "changed_quantity": name,
                            "run": repaired,
                            "frozen_conditions_preserved": repaired["payload"]["conditions"]
                            == proposal["conditions"],
                            "frozen_quantities_preserved": repaired["payload"]["quantities"]
                            == proposal["quantities"],
                        }
    report["source_sha256_after"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report["source_unchanged"] = before == report["source_sha256_after"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path, help="saved result files or directories")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--stress", action="store_true", help="save clearly labelled altered-number inputs"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f"Refusing to overwrite replay output: {args.output}")
    paths = sorted(
        {
            path
            for source in args.sources
            for path in (source.rglob("result.json") if source.is_dir() else [source])
        }
    )
    if not paths:
        raise ValueError("No saved result files found.")
    hashes = stage._source_hashes()
    records = [
        replay_result(
            path, stress_dir=args.output.parent / "stress_inputs" if args.stress else None
        )
        for path in paths
    ]
    after = stage._source_hashes()
    result = {
        "schema_version": "pf-design-data-replay/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_kind": "offline_software_replay_not_fresh_generation",
        "model_calls": 0,
        "source_hashes": hashes,
        "source_hashes_after": after,
        "source_integrity_verified": hashes == after,
        "counts": {
            "saved_results": len(records),
            "accepted_rechecks": sum(
                (r["recheck"] or {}).get("status") == "accepted" for r in records
            ),
            "accepted_with_warnings": sum(
                (r["recheck"] or {}).get("accepted", False)
                and bool(r["recheck"]["warnings"])
                for r in records
            ),
            "warning_conditions": sum(
                len((r["recheck"] or {}).get("warnings", [])) for r in records
            ),
            "rejected_rechecks": sum(
                (r["recheck"] or {}).get("status") == "rejected" for r in records
            ),
            "review_needed_rechecks": sum(
                (r["recheck"] or {}).get("status") == "review_needed" for r in records
            ),
            "unavailable_rechecks": sum(r["recheck"] is None for r in records),
            "accepted_mock_repairs": sum(
                (r["stress"] or {}).get("run", {}).get("accepted", False) for r in records
            ),
        },
        "records": records,
    }
    _write_json(args.output, result)
    print(json.dumps(result["counts"]))
    print(f"saved: {args.output}")


if __name__ == "__main__":
    main()
