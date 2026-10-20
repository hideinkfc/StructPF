"""Offline verification of completed campaign coverage, dependencies and calculator replay."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.run_pf_measure_campaign import write
from src.evaluation.pf_task_measures import MEASURES
from src.generation.design_calculator import calculate_condition


def verify(root: Path, full: Path):
    catalog = json.loads((root / "catalog.json").read_text())
    results = json.loads((full / "results.json").read_text())
    expected = {case["case_id"] for case in catalog["cases"]}
    for model in ["luna", "gpt41"]:
        selected = [
            item
            for item in results
            if item["judge_model"] == model
            and item["solver_model"] == "luna"
            and item["repeat"] == 0
        ]
        assert len(selected) == len(expected)
        assert {item["case_id"] for item in selected} == expected
    quote_errors, execution_errors = 0, 0
    for result in results:
        assert tuple(result["measures"]) == MEASURES
        alignment = result["measures"]["target_alignment"]
        validity = result["measures"]["mathematical_validity"]
        accessibility = result["measures"]["prior_knowledge_accessibility"]
        limits = result["measures"]["familiar_approach_limits"]
        if alignment["status"] != "assessed" or alignment["value"] != "yes":
            assert validity["value"] == "not_assessed"
        if accessibility["status"] != "assessed" or accessibility["value"] != "yes":
            assert limits["value"] == "not_assessed"
        for row in result["measures"].values():
            if row["status"] == "assessed":
                assert row["value"] in {"yes", "partly", "no", "unclear"}
            elif row["status"] == "not_assessed":
                assert row["value"] == "not_assessed"
            else:
                assert row["value"] is None
                execution_errors += 1
            if row["error"] and "quotation" in str(row["error"]).lower():
                quote_errors += 1
        solver = result["solver"]
        if solver.get("input"):
            assert set(solver["input"]) == {"student_task", "learner_context"}
        counts = result["approach_counts"]
        if counts is not None:
            assert counts["supported_starts"] == sum(
                counts[key] for key in ["target_limits", "meets_demands", "unrelated_shortfalls"]
            ) + sum(
                item["status"] == "unresolved" for item in accessibility["evidence"]["attempts"]
            )
    job_statuses, replayed, usage_missing, calls, schema_repairs = Counter(), 0, 0, 0, 0
    for path in (full / "jobs").glob("*.json"):
        job = json.loads(path.read_text())
        job_statuses[job["status"]] += 1
        assert len(job["calls"]) <= (1 if job["role"] == "solver" else 3)
        assert len(job["calculations"]) <= 16
        assert "references" not in job["input"] and "occurrences" not in job["input"]
        calls += len(job["calls"])
        schema_repairs += len(job.get("schema_repairs", []))
        for call in job["calls"]:
            if not call["response"] or call["response"]["usage"].get("prompt_tokens") is None:
                usage_missing += 1
        for entry in job["calculations"]:
            request = entry["request"]
            observed = calculate_condition(
                {
                    "expressions": request["expressions"],
                    "predicate": request["predicate"],
                    "symbols": request.get("symbols", {}),
                },
                request["values"],
            )
            assert observed == entry["result"], (path, observed, entry["result"])
            replayed += 1
    decision = json.loads((root / "calibration_decision.json").read_text())
    assert (
        hashlib.sha256((root / "catalog.json").read_bytes()).hexdigest()
        == (decision["catalog_sha256"])
    )
    assert (
        hashlib.sha256((root / "calibration_pack.json").read_bytes()).hexdigest()
        == (decision["reference_sha256"])
    )
    frozen = root / "frozen_implementation"
    for source, digest in json.loads((frozen / "sha256.json").read_text()).items():
        assert hashlib.sha256((frozen / source).read_bytes()).hexdigest() == digest
    summary = json.loads((full / "summary.json").read_text())
    assert summary["tasks"] == len(expected)
    assert summary["execution"]["model_calls"] == calls
    assert summary["execution"]["calculator_checks"] == replayed
    assert summary["execution"]["missing_usage_calls"] == usage_missing
    return {
        "verified": True,
        "scope": "Coverage, software invariants and exact checks, not judge truth.",
        "input_conditions": len(expected),
        "judge_results": len(results),
        "role_jobs": sum(job_statuses.values()),
        "job_statuses": dict(job_statuses),
        "model_calls": calls,
        "calculator_checks_replayed": replayed,
        "schema_completion_requests": schema_repairs,
        "missing_usage_calls": usage_missing,
        "unavailable_measure_fields": execution_errors,
        "exact_quote_errors_preserved": quote_errors,
        "frozen_references_unchanged": True,
        "source_snapshots_verified": True,
        "human_validated": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = verify(args.root, args.full)
    write(args.output, evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
