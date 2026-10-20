"""Keyword screen for learning-record adherence in saved PF attempts.

A screen flags attempts for reading; it does not decide whether a procedure was
recalled, constructed or only mentioned.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

PATTERNS = {
    "loibl_variance": {
        "untaught_named": r"standard deviation|variance|σ|interquartile|coefficient of variation",
        "omitted_resource": r"\bmean\b|\baverage\b",
        "mean_calculation": (
            r"(mean|average)\s*(=|:|is|of)\s*[\(\d]|\bsum\b[^.]{0,60}divided by|÷\s*\d"
        ),
    },
    "kapur_average_speed": {
        "untaught_named": r"harmonic mean|weighted (average|mean)",
        "omitted_resource": r"\bratio|proportion",
    },
    "kerrigan_fair_division": {
        "untaught_named": (
            r"lone[- ]divider|last[- ]diminisher|sealed[- ]bid|steinhaus|banach|knaster"
            r"|envy[- ]free"
        ),
        "omitted_resource": r"divider|chooser|cut[- ]and[- ]choose|one cuts",
    },
}
RECORD_STATEMENT = (
    r"not (yet )?(been )?(learned|learnt|taught)|haven't (yet )?(learned|been taught)"
    r"|have not (yet )?(learned|been taught)|not (directly )?instructed|not allowed"
    r"|with my current knowledge|outside (my|the) (listed )?(resources|record)"
)


def screen(panel: Path) -> dict:
    manifest = json.loads((panel / "manifest.json").read_text())
    requests = {request["id"]: request for request in manifest["requests"]}
    families = {task["id"]: task["family"] for task in manifest["protocol"]["tasks"]}
    counts: dict[str, Counter] = {}
    record_statements = []
    for item in manifest["attempts"]:
        if item["phase"] != "fresh":
            continue
        request = requests[item["id"]]
        record = json.loads((panel / item["result_path"]).read_text())
        attempt = record["attempt"]
        text = (
            attempt["written_work"] + " " + attempt["answer"]
            if attempt
            else record["raw_text"] or ""
        )
        family = families[request["task_id"]]
        group = counts.setdefault(f"{family}/{request['profile_id']}", Counter())
        group["attempted"] += 1
        for name, pattern in PATTERNS[family].items():
            group[name] += int(bool(re.search(pattern, text, re.IGNORECASE)))
        match = re.search(RECORD_STATEMENT, text, re.IGNORECASE)
        if match:
            group["record_statement"] += 1
            start = max(0, match.start() - 160)
            record_statements.append(
                {
                    "id": request["id"],
                    "excerpt": text[start : match.end() + 120],
                }
            )
    return {
        "method": (
            "Post-hoc keyword screen of saved attempts; flags for reading, not a coding "
            "verdict. A hit can be an application, an everyday word or a mention of "
            "something the record excludes. Task text can itself reintroduce a resource."
        ),
        "patterns": {"families": PATTERNS, "record_statement": RECORD_STATEMENT},
        "counts": {key: dict(value) for key, value in sorted(counts.items())},
        "record_statements": record_statements,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = screen(args.panel)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["counts"], indent=2))
