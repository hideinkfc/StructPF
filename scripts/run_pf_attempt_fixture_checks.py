"""Judge constructed, frozen attempt fixtures separately from solver elicitation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.run_pf_measure_campaign import MODELS, Jobs, case_inputs, write
from src.evaluation import pf_three_role as pf


def run(pack_path: Path, output: Path, *, workers=12):
    pack = json.loads(pack_path.read_text())
    cases = {
        case["case_id"]: case
        for split in ["development", "transfer", "controls"]
        for case in pack[split]
    }
    manager = Jobs(output, workers=workers)
    jobs = []
    for group in pack["attempt_fixture_groups"]:
        payload = pf.role_input(
            "attempt_judge", case_inputs(cases[group["case_id"]]), group["attempts"]
        )
        for model in MODELS:
            jobs.append((f"{group['id']}__{model}", "attempt_judge", model, payload))
    records = manager.batch(jobs)
    comparisons = []
    for group in pack["attempt_fixture_groups"]:
        for model in MODELS:
            record = records[f"{group['id']}__{model}"]
            if record["status"] != "completed":
                comparisons.append(
                    {
                        "group": group["id"],
                        "model": model,
                        "execution": record["status"],
                        "matches": None,
                    }
                )
                continue
            parsed = pf.parse_attempts(record["output"], group["attempts"])
            for expected in group["expected_reviews"]:
                index = expected["attempt_index"]
                observed = parsed["measures"]["prior_knowledge_accessibility"]["evidence"][
                    "attempts"
                ][index]
                comparisons.append(
                    {
                        "group": group["id"],
                        "model": model,
                        "attempt": index,
                        "expected": expected["status"],
                        "observed": observed["status"],
                        "matches": expected["status"] == observed["status"],
                        "reason": observed["reason"],
                    }
                )
    result = {
        "purpose": "Constructed diagnostic work, not students or solver outputs.",
        "human_validated": False,
        "comparisons": comparisons,
        "by_model": {
            model: {
                "matches": sum(
                    item["matches"] is True for item in comparisons if item["model"] == model
                ),
                "usable": sum(
                    item["matches"] is not None for item in comparisons if item["model"] == model
                ),
            }
            for model in MODELS
        },
        "prompt_sha256": pf.fingerprint(),
    }
    write(output / "diagnostics.json", result)
    print(json.dumps(result["by_model"], indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    run(args.pack, args.output, workers=args.workers)


if __name__ == "__main__":
    main()
