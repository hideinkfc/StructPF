"""Resumable, bounded computational calibration and all-saved-task PF evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from scripts.prior_methods.common import load_client
from scripts.run_pf_task_measures import make_chat
from src.evaluation import pf_three_role as pf
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "experiments/results/pf_measure_campaign_20261014"
MODELS = {"luna": "gpt-5.6-luna", "gpt41": "gpt-4.1"}


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def digest(value: object):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class Jobs:
    def __init__(self, output: Path, *, workers=16, tokens=12000):
        self.output, self.workers, self.tokens = output, workers, tokens
        self.clients = {}
        for label, model in MODELS.items():
            client, _ = load_client("luna" if label == "luna" else "gpt41")
            settings = (
                {"max_completion_tokens": tokens, "reasoning_effort": "high"}
                if model.startswith("gpt-5")
                else {"max_tokens": tokens, "temperature": 0}
            )
            self.clients[label] = make_chat(client, model, settings)
        self.signature = digest(
            {
                "prompts": pf.fingerprint(),
                "models": MODELS,
                "tokens": tokens,
                "code": hashlib.sha256(
                    (ROOT / "src/evaluation/pf_three_role.py").read_bytes()
                ).hexdigest(),
                "budget": {"calls": 3, "checks": 16},
            }
        )

    def one(self, key: str, role: str, model: str, payload: dict):
        path = self.output / "jobs" / f"{key}.json"
        signature = digest(
            {"campaign": self.signature, "role": role, "model": model, "input": payload}
        )
        if path.exists():
            record = json.loads(path.read_text())
            if record.get("signature") != signature:
                raise ValueError(f"Job inputs or code changed in-place: {path}")
            return record
        record = {
            "job_key": key,
            "signature": signature,
            "model_requested": MODELS[model],
            "started_at": now(),
            **pf.run_role(role, payload, self.clients[model]),
            "finished_at": now(),
        }
        write(path, record)
        return record

    def batch(self, jobs: list[tuple]):
        results = {}
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.one, *job): job[0] for job in jobs}
            for index, future in enumerate(as_completed(futures), 1):
                key = futures[future]
                result = future.result()
                results[key] = result
                if index % 20 == 0 or index == len(jobs) or result["status"] != "completed":
                    print(
                        f"{self.output.name}: {index}/{len(jobs)} {key}: {result['status']}",
                        flush=True,
                    )
        return results


def case_inputs(case):
    context = case["learner_context"]
    if context is None:
        logging.warning(
            "%s has no saved learner context; history remains unavailable", case["case_id"]
        )
        context = {}
    context = dict(context)
    resources = context.get("assumed_prior_knowledge")
    if isinstance(resources, list):
        normalized = []
        for resource in resources:
            if isinstance(resource, str) and resource.strip():
                normalized.append({"resource": resource, "taught_as": resource})
            elif isinstance(resource, dict) and isinstance(resource.get("resource"), str):
                label = resource["resource"]
                if not label.strip():
                    raise ValueError(f"{case['case_id']} has an empty saved resource label")
                description = resource.get("taught_as")
                if not isinstance(description, str) or not description.strip():
                    logging.warning(
                        "%s: name-only resource %r; no taught depth inferred",
                        case["case_id"],
                        label,
                    )
                    description = label
                normalized.append({"resource": label, "taught_as": description})
            else:
                raise ValueError(f"{case['case_id']} has an unusable saved prerequisite record")
        context["assumed_prior_knowledge"] = normalized
    target = case["learning_target"]
    if not isinstance(target, str) or not target.strip():
        logging.warning("%s has no saved target; alignment remains unclear", case["case_id"])
        target = None
    return pf.prepare_input(case["student_task"], target, context)


def phase(cases, output, *, repeats=1, sensitivity=False, workers=16):
    output.mkdir(parents=True, exist_ok=True)
    manager = Jobs(output, workers=workers)
    manifest_path = output / "manifest.json"
    manifest = {
        "version": pf.VERSION,
        "status": "started",
        "created_at": now(),
        "computational_only": True,
        "human_validated": False,
        "model_independence": "Two OpenAI series, not independent model families.",
        "models": MODELS,
        "tokens_per_call": manager.tokens,
        "signature": manager.signature,
        "repeats": repeats,
        "solver_sensitivity": sensitivity,
        "case_count": len(cases),
        "cases_sha256": digest(cases),
        "prompt_snapshot": pf.PROMPT_PATH.read_text(),
        "source_hashes": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                pf.PROMPT_PATH,
                ROOT / "src/evaluation/prompts/pf_three_role_v2_1.yaml",
                ROOT / "src/evaluation/pf_three_role.py",
                Path(__file__),
            ]
        },
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        for field in ("signature", "cases_sha256", "repeats", "solver_sensitivity"):
            if previous[field] != manifest[field]:
                raise ValueError(f"Frozen phase changed: {field}")
    else:
        write(manifest_path, manifest)
    prepared = {case["case_id"]: case_inputs(case) for case in cases}
    first = []
    for identifier, payload in prepared.items():
        for model in MODELS:
            for repeat in range(repeats):
                first.append(
                    (
                        f"{identifier}__task__{model}__{repeat}",
                        "task_judge",
                        model,
                        pf.role_input("task_judge", payload),
                    )
                )
        if payload["learner_context"].get("assumed_prior_knowledge"):
            for model in MODELS if sensitivity else ["luna"]:
                first.append(
                    (
                        f"{identifier}__solver__{model}",
                        "solver",
                        model,
                        pf.role_input("solver", payload),
                    )
                )
    completed = manager.batch(first)
    second = []
    for identifier, payload in prepared.items():
        for solver_model in MODELS if sensitivity else ["luna"]:
            solver = completed.get(f"{identifier}__solver__{solver_model}")
            if solver is None or solver["status"] != "completed":
                continue
            for judge_model in MODELS if solver_model == "luna" else ["luna"]:
                for repeat in range(repeats if solver_model == "luna" else 1):
                    second.append(
                        (
                            f"{identifier}__attempt__{solver_model}__{judge_model}__{repeat}",
                            "attempt_judge",
                            judge_model,
                            pf.role_input("attempt_judge", payload, solver["output"]["attempts"]),
                        )
                    )
    completed.update(manager.batch(second) if second else {})
    results = []
    for case in cases:
        identifier, payload = case["case_id"], prepared[case["case_id"]]
        for solver_model in MODELS if sensitivity else ["luna"]:
            solver = completed.get(
                f"{identifier}__solver__{solver_model}",
                {
                    "status": "input_unavailable",
                    "error": None,
                    "output": None,
                    "calls": [],
                },
            )
            for judge_model in MODELS if solver_model == "luna" else ["luna"]:
                for repeat in range(repeats if solver_model == "luna" else 1):
                    task = completed[f"{identifier}__task__{judge_model}__{repeat}"]
                    attempt = completed.get(
                        f"{identifier}__attempt__{solver_model}__{judge_model}__{repeat}"
                    )
                    result = pf.assemble(payload, solver, task, attempt)
                    results.append(
                        {
                            "case_id": identifier,
                            "judge_model": judge_model,
                            "solver_model": solver_model,
                            "repeat": repeat,
                            **result,
                        }
                    )
    summary = summarize(results, cases, completed)
    if not (output / "results.json").exists():
        write(output / "results.json", results)
        write(output / "summary.json", summary)
        write(output / "completed.json", {"finished_at": now(), **summary["execution"]})
    else:
        if json.loads((output / "results.json").read_text()) != results:
            raise ValueError("Assembled results changed during resume")
    return results, summary


def summarize(results, cases, jobs):
    tables = {}
    for judge in MODELS:
        selected = [
            r
            for r in results
            if r["judge_model"] == judge and r["solver_model"] == "luna" and r["repeat"] == 0
        ]
        tables[judge] = {}
        for measure in MEASURES:
            rows = [r["measures"][measure] for r in selected]
            tables[judge][measure] = {
                "tasks": len(rows),
                "values": dict(Counter(row["value"] for row in rows)),
                "statuses": dict(Counter(row["status"] for row in rows)),
                "assessed": sum(row["status"] == "assessed" for row in rows),
                "skipped": sum(row["status"] == "not_assessed" for row in rows),
            }
    agreement = {}
    for measure in MEASURES:
        pairs = []
        for case in cases:
            matched = {
                r["judge_model"]: r
                for r in results
                if r["case_id"] == case["case_id"]
                and r["solver_model"] == "luna"
                and r["repeat"] == 0
            }
            if set(matched) == set(MODELS):
                a, b = [matched[m]["measures"][measure] for m in MODELS]
                if a["status"] in {"assessed", "not_assessed"} and b["status"] in {
                    "assessed",
                    "not_assessed",
                }:
                    pairs.append(a["value"] == b["value"])
        agreement[measure] = {"agree": sum(pairs), "usable_pairs": len(pairs)}
    agreement["scope"] = "Includes explicit skipped verdicts; report alongside assessed counts."
    execution = {
        "role_jobs": len(jobs),
        "status_counts": dict(Counter(job["status"] for job in jobs.values())),
        "model_calls": sum(len(job["calls"]) for job in jobs.values()),
        "calculator_checks": sum(len(job["calculations"]) for job in jobs.values()),
        "input_tokens": sum(
            call["response"]["usage"].get("prompt_tokens") or 0
            for job in jobs.values()
            for call in job["calls"]
            if call["response"]
        ),
        "output_tokens": sum(
            call["response"]["usage"].get("completion_tokens") or 0
            for job in jobs.values()
            for call in job["calls"]
            if call["response"]
        ),
        "missing_usage_calls": sum(
            not call["response"] or call["response"]["usage"].get("prompt_tokens") is None
            for job in jobs.values()
            for call in job["calls"]
        ),
        "invalid_measure_fields": sum(
            row["status"] == "invalid_response"
            for result in results
            for row in result["measures"].values()
        ),
        "token_totals_scope": "Sum of reported usage only; missing usage counted separately.",
    }
    return {
        "version": pf.VERSION,
        "tasks": len(cases),
        "human_validated": False,
        "by_judge": tables,
        "between_judge_agreement": agreement,
        "execution": execution,
    }


def calibration_diagnostics(cases, results):
    comparisons, disagreements = [], []
    reference_keys = {
        "alignment": "target_alignment",
        "validity": "mathematical_validity",
        "accessibility": "prior_knowledge_accessibility",
        "limits": "familiar_approach_limits",
        "invention": "room_for_invention",
    }
    by_case = {case["case_id"]: case for case in cases}
    for result in results:
        if result["solver_model"] != "luna":
            continue
        case = by_case[result["case_id"]]
        references = case.get("references", case.get("reference_judgments", {}))
        for key, reference in references.items():
            measure = reference_keys.get(key, key)
            if measure not in MEASURES:
                continue
            expected = (
                reference.get("value", reference.get("verdict"))
                if isinstance(reference, dict)
                else reference
            )
            accepted = (
                reference.get("acceptable_values", [expected])
                if isinstance(reference, dict)
                else [expected]
            )
            if expected is None:
                continue
            row = result["measures"][measure]
            item = {
                "case_id": case["case_id"],
                "measure": measure,
                "judge": result["judge_model"],
                "solver": result["solver_model"],
                "repeat": result["repeat"],
                "expected": accepted,
                "observed": row["value"],
                "status": row["status"],
                "matches_provisional_reference": row["value"] in accepted,
                "evidence": row["evidence"],
            }
            comparisons.append(item)
            if not item["matches_provisional_reference"]:
                disagreements.append(item)
    aggregates = defaultdict(lambda: {"matches": 0, "comparisons": 0})
    for item in comparisons:
        key = f"{item['judge']}:{item['measure']}"
        aggregates[key]["matches"] += item["matches_provisional_reference"]
        aggregates[key]["comparisons"] += 1
    repeats = {}
    sensitivity = {}
    for measure in MEASURES:
        repetitions, changes = [], []
        for identifier in by_case:
            own = [
                item
                for item in results
                if item["case_id"] == identifier and item["solver_model"] == "luna"
            ]
            for judge in MODELS:
                pair = sorted(
                    [item for item in own if item["judge_model"] == judge],
                    key=lambda item: item["repeat"],
                )
                if len(pair) >= 2:
                    left, right = [item["measures"][measure] for item in pair[:2]]
                    if left["value"] is not None and right["value"] is not None:
                        repetitions.append(left["value"] == right["value"])
            if measure not in {"prior_knowledge_accessibility", "familiar_approach_limits"}:
                continue
            primary = [
                item for item in own if item["judge_model"] == "luna" and item["repeat"] == 0
            ]
            alternative = [
                item
                for item in results
                if item["case_id"] == identifier
                and item["judge_model"] == "luna"
                and item["solver_model"] == "gpt41"
            ]
            if primary and alternative:
                left, right = primary[0]["measures"][measure], alternative[0]["measures"][measure]
                if left["value"] is not None and right["value"] is not None:
                    changes.append(
                        {
                            "case_id": identifier,
                            "primary": left["value"],
                            "alternative": right["value"],
                            "changed": left["value"] != right["value"],
                        }
                    )
        repeats[measure] = {"agree": sum(repetitions), "usable_pairs": len(repetitions)}
        if changes:
            sensitivity[measure] = {
                "changed": sum(item["changed"] for item in changes),
                "usable_pairs": len(changes),
                "cases": changes,
            }
    return {
        "reference_provenance": "Assistant-prepared, not human-reviewed or validated gold.",
        "by_model_measure": dict(aggregates),
        "comparisons": comparisons,
        "disagreements": disagreements,
        "repeat_agreement": repeats,
        "solver_sensitivity": sensitivity,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=["smoke", "development", "transfer", "all"], required=True
    )
    parser.add_argument("--pack", type=Path, default=CAMPAIGN / "calibration_pack.json")
    parser.add_argument("--catalog", type=Path, default=CAMPAIGN / "catalog.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if args.phase == "all":
        catalog = json.loads(args.catalog.read_text())
        cases = catalog["cases"]
        repeats, sensitivity = 1, False
    else:
        pack = json.loads(args.pack.read_text())
        cases = pack["development" if args.phase in {"smoke", "development"} else "transfer"]
        if args.phase == "development":
            cases = cases + pack.get("controls", [])
        if args.phase == "smoke":
            cases = cases[:2]
        repeats = 2 if args.phase == "development" else 1
        sensitivity = args.phase == "development"
    results, summary = phase(
        cases, args.output, repeats=repeats, sensitivity=sensitivity, workers=args.workers
    )
    if args.phase != "all":
        diagnostics = calibration_diagnostics(cases, results)
        if not (args.output / "diagnostics.json").exists():
            write(args.output / "diagnostics.json", diagnostics)
        print(json.dumps(diagnostics["by_model_measure"], indent=2), flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    if any(status != "completed" for status in summary["execution"]["status_counts"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
