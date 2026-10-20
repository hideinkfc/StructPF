"""Rahimi-style multi-cell direct generation and two-pass Table 1 rating.

Frozen design: experiments/configs/pf_rahimi_multi_theme_setting.json. Generation
uses API default sampling, because the source paper reports none. Judging uses
two blinded passes of the Luna deployment with high reasoning effort, each with
its own seeded shuffle and blind IDs. A call that fails with an API error is
deleted and logged in deleted_api_errors.jsonl; it is never retried or replaced.
Completed outputs that are malformed or not ready are kept as results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_paper_benchmark as bench  # noqa: E402
from src.evaluation import pf_rubric_setting  # noqa: E402

CONFIG = ROOT / "experiments/configs/pf_rahimi_multi_theme_setting.json"
GEN_PROMPT = ROOT / "src/generation/prompts/pf_paper_benchmark.yaml"
RESULT_ROOT = ROOT / "experiments/results/pf_rahimi_multi_theme_20261013"
SCHEMA_VERSION = "pf-rahimi-multi-theme/v1"
MODEL_TAGS = {"gpt-5-mini": "gpt5mini", "gpt-4.1": "gpt41"}
REQUEST_TIMEOUT = 240
JUDGE_TIMEOUT = 600


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    return read_json(CONFIG)


def cell_messages(cell: dict[str, Any], prompt: dict[str, Any]) -> tuple[str, str]:
    values = bench._direct_values(
        {"case": cell["case"], "learner_context": cell["learner_context"]}, []
    )
    return (
        bench._render(prompt["system"], values),
        bench._direct_user(prompt, values, include_misconceptions=False),
    )


def task_key(cell_id: str, model: str, index: int) -> str:
    return f"{cell_id}__{MODEL_TAGS[model]}__{index:03d}"


def blind_plan(judges: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, str]]:
    plan: dict[str, dict[str, str]] = {}
    for judge in judges:
        rng = random.Random(judge["shuffle_seed"])
        order = sorted(keys)
        rng.shuffle(order)
        ids: dict[str, str] = {}
        for key in order:
            blind = f"m-{rng.getrandbits(48):012x}"
            if blind in ids:
                raise ValueError("Blind ID collision; choose another shuffle seed")
            ids[blind] = key
        plan[judge["judge_id"]] = ids
    return plan


class Ledger:
    """Deleted API-error calls. Keys listed here are never called again."""

    def __init__(self, output: Path) -> None:
        self.path = output / "deleted_api_errors.jsonl"
        self.lock = threading.Lock()
        self.keys: set[str] = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                self.keys.add(json.loads(line)["key"])

    def delete(self, key: str, detail: dict[str, Any]) -> None:
        with self.lock:
            self.keys.add(key)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps({"key": key, "deleted_at": now(), **detail}, ensure_ascii=False)
                    + "\n"
                )


def generate_one(
    api: OpenAI,
    output: Path,
    ledger: Ledger,
    config: dict[str, Any],
    cell: dict[str, Any],
    model: str,
    index: int,
    system: str,
    user: str,
) -> None:
    key = task_key(cell["cell_id"], model, index)
    path = output / "attempts" / f"{key}.json"
    if path.exists() or key in ledger.keys:
        return
    settings = bench._determine_effective_settings(
        model, {"max_tokens": config["generation"]["max_completion_tokens"]}
    )
    started = now()
    try:
        response = api.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            timeout=REQUEST_TIMEOUT,
            **settings,
        )
    except OpenAIError as error:
        ledger.delete(key, {"stage": "generation", "error": f"{type(error).__name__}: {error}"})
        return
    raw = response.choices[0].message.content or ""
    payload = bench._json_payload(raw)
    status, schema_error = bench._validate_task(payload)
    finish = response.choices[0].finish_reason
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {
            "key": key,
            "cell_id": cell["cell_id"],
            "model_requested": model,
            "model_returned": getattr(response, "model", model),
            "index": index,
            "status": status,
            "error": schema_error,
            "task": payload,
            "raw_response": raw,
            "finish_reason": finish,
            "truncated": finish == "length",
            "settings_sent": settings,
            "started_at": started,
            "finished_at": now(),
        },
    )


def judge_one(
    api: OpenAI,
    output: Path,
    ledger: Ledger,
    judge: dict[str, Any],
    blind: str,
    key: str,
    cell: dict[str, Any],
    task: dict[str, Any],
    system: str,
    deployment: str,
    max_tokens: int,
) -> None:
    judgment_key = f"{judge['judge_id']}__{blind}"
    path = output / "judgments" / judge["judge_id"] / f"{blind}.json"
    if path.exists() or judgment_key in ledger.keys:
        return
    user = pf_rubric_setting.judge_input(
        pf_rubric_setting.student_task_text(task), cell["case"], cell["learner_context"]
    )
    started = now()
    try:
        response = api.chat.completions.create(
            model=deployment,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
            reasoning_effort=judge["reasoning_effort"],
            timeout=JUDGE_TIMEOUT,
        )
    except OpenAIError as error:
        ledger.delete(judgment_key, {"stage": "judge", "error": f"{type(error).__name__}: {error}"})
        return
    raw = response.choices[0].message.content or ""
    try:
        parsed = pf_rubric_setting.parse_rating(raw)
        fields: dict[str, Any] = {
            "status": parsed["status"],
            "scores": parsed["scores"],
            "rating": parsed["rating"],
            "parse_error": None,
        }
    except ValueError as error:
        fields = {
            "status": "parse_error",
            "scores": None,
            "rating": None,
            "parse_error": str(error)[:500],
        }
    finish = response.choices[0].finish_reason
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {
            "judge_id": judge["judge_id"],
            "blind_id": blind,
            "task_key": key,
            "deployment": deployment,
            "reasoning_effort": judge["reasoning_effort"],
            "user_input": user,
            "raw_response": raw,
            "finish_reason": finish,
            "truncated": finish == "length",
            "started_at": started,
            "finished_at": now(),
            **fields,
        },
    )


def ready_keys(output: Path) -> dict[str, dict[str, Any]]:
    ready: dict[str, dict[str, Any]] = {}
    for path in sorted((output / "attempts").glob("*.json")):
        record = read_json(path)
        if record["status"] == "ready":
            ready[record["key"]] = record
    return ready


def frozen_manifest(
    config: dict[str, Any], gen_prompt: dict[str, Any], attempts: int
) -> dict[str, Any]:
    cells = {}
    for cell in config["cells"]:
        system, user = cell_messages(cell, gen_prompt)
        cells[cell["cell_id"]] = {"system_sha256": sha(system), "user_sha256": sha(user)}
    return {
        "schema_version": SCHEMA_VERSION,
        "config_sha256": sha(CONFIG.read_text(encoding="utf-8")),
        "generation_prompt_sha256": sha(GEN_PROMPT.read_text(encoding="utf-8")),
        "judge_prompt_sha256": sha(pf_rubric_setting.PROMPT_PATH.read_text(encoding="utf-8")),
        "runner_sha256": sha(Path(__file__).read_text(encoding="utf-8")),
        "cell_messages": cells,
        "attempts_per_cell_per_model": attempts,
        "generation": {
            "models": list(config["models"]),
            "max_completion_tokens": config["generation"]["max_completion_tokens"],
            "sampling": "API default; no temperature sent",
            "workers": config["generation"]["workers"],
        },
        "rater": {
            "judges": config["rater"]["judges"],
            "max_completion_tokens": config["rater"]["max_completion_tokens"],
            "workers": config["rater"]["workers"],
            "sampling": "no temperature sent; reasoning_effort per judge",
        },
        "failure_policy": "API-error calls are deleted and logged, never retried or replaced",
        "created_at": now(),
    }


def check_or_write_manifest(output: Path, manifest: dict[str, Any]) -> None:
    path = output / "manifest.json"
    if not path.exists():
        write_json(path, manifest)
        return
    frozen = read_json(path)
    for field in (
        "config_sha256",
        "generation_prompt_sha256",
        "judge_prompt_sha256",
        "cell_messages",
        "attempts_per_cell_per_model",
    ):
        if frozen[field] != manifest[field]:
            raise ValueError(f"Frozen input changed since preparation: {field}")


def generation_stage(
    api: OpenAI, output: Path, config: dict[str, Any], gen_prompt: dict[str, Any], attempts: int
) -> None:
    ledger = Ledger(output)
    messages = {cell["cell_id"]: cell_messages(cell, gen_prompt) for cell in config["cells"]}
    jobs = [
        (cell, model, index)
        for cell in config["cells"]
        for model in config["models"]
        for index in range(1, attempts + 1)
    ]

    def run(job: tuple[dict[str, Any], str, int]) -> None:
        cell, model, index = job
        system, user = messages[cell["cell_id"]]
        generate_one(api, output, ledger, config, cell, model, index, system, user)

    with ThreadPoolExecutor(max_workers=config["generation"]["workers"]) as pool:
        list(pool.map(run, jobs))


def judge_stage(api: OpenAI, output: Path, config: dict[str, Any], deployment: str) -> None:
    rater = config["rater"]
    if len(rater["judges"]) != 2:
        raise ValueError("The adjudication rule expects exactly two judge passes")
    for judge in rater["judges"]:
        if judge["deployment"] != deployment:
            raise ValueError(f"Judge deployment {judge['deployment']} != env {deployment}")
    ready = ready_keys(output)
    plan_path = output / "blind_mapping_private.json"
    if plan_path.exists():
        plan = read_json(plan_path)
    else:
        plan = blind_plan(rater["judges"], list(ready))
        write_json(plan_path, plan)
    for judge_id, ids in plan.items():
        if set(ids.values()) != set(ready):
            raise ValueError(f"Blind mapping for {judge_id} does not match the ready tasks")

    cells = {cell["cell_id"]: cell for cell in config["cells"]}
    system = pf_rubric_setting.load_prompt()["system"]
    ledger = Ledger(output)
    jobs = [
        (judge, blind, key)
        for judge in rater["judges"]
        for blind, key in plan[judge["judge_id"]].items()
    ]

    def run(job: tuple[dict[str, Any], str, str]) -> None:
        judge, blind, key = job
        record = ready[key]
        judge_one(
            api,
            output,
            ledger,
            judge,
            blind,
            key,
            cells[record["cell_id"]],
            record["task"],
            system,
            deployment,
            rater["max_completion_tokens"],
        )

    with ThreadPoolExecutor(max_workers=rater["workers"]) as pool:
        list(pool.map(run, jobs))
    write_json(output / "scores.json", aggregate(output, config, plan, ready))


def aggregate(
    output: Path,
    config: dict[str, Any],
    plan: dict[str, dict[str, str]],
    ready: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ledger = Ledger(output)
    judges = [judge["judge_id"] for judge in config["rater"]["judges"]]
    blind_of = {
        judge_id: {key: blind for blind, key in plan[judge_id].items()} for judge_id in judges
    }
    tasks: dict[str, Any] = {}
    for key in sorted(ready):
        judged: dict[str, Any] = {}
        for judge_id in judges:
            blind = blind_of[judge_id][key]
            path = output / "judgments" / judge_id / f"{blind}.json"
            record = read_json(path) if path.exists() else None
            if record is None:
                deleted = f"{judge_id}__{blind}" in ledger.keys
                missing = "deleted_api_error" if deleted else "missing"
                judged[judge_id] = {
                    "blind_id": blind,
                    "status": missing,
                    "total": None,
                    "scores": None,
                }
            else:
                judged[judge_id] = {
                    "blind_id": blind,
                    "status": record["status"],
                    "total": record["scores"]["TOTAL"] if record["scores"] else None,
                    "scores": record["scores"],
                }
        totals = [judged[judge_id]["total"] for judge_id in judges]
        if all(total is not None for total in totals):
            gap = abs(totals[0] - totals[1])
            final, status = (totals[0] + totals[1]) / 2, "final"
        else:
            gap, final, status = None, None, "incomplete"
        tasks[key] = {
            "cell_id": ready[key]["cell_id"],
            "model": ready[key]["model_requested"],
            "judges": judged,
            "final": final,
            "gap": gap,
            "flag_gap_5": gap is not None and gap >= 5,
            "status": status,
        }
    return {
        "generated_at": now(),
        "adjudication": "final = mean of the two totals; gap >= 5 flagged; no third judge",
        "tasks": tasks,
    }


def summarize(output: Path, config: dict[str, Any]) -> dict[str, Any]:
    attempts = [read_json(path) for path in sorted((output / "attempts").glob("*.json"))]
    deleted = Ledger(output).keys
    scores = read_json(output / "scores.json")["tasks"] if (output / "scores.json").exists() else {}
    summary: dict[str, Any] = {
        "generated_at": now(),
        "deleted_judge_errors": sum(key.startswith("luna-judge") for key in deleted),
        "by_cell_model": {},
    }
    for cell in config["cells"]:
        for model in config["models"]:
            prefix = f"{cell['cell_id']}__{MODEL_TAGS[model]}__"
            rows = [row for row in attempts if row["key"].startswith(prefix)]
            statuses: dict[str, int] = {}
            for row in rows:
                statuses[row["status"]] = statuses.get(row["status"], 0) + 1
            finals = [
                task["final"]
                for key, task in scores.items()
                if key.startswith(prefix) and task["final"] is not None
            ]
            summary["by_cell_model"][f"{cell['cell_id']} | {model}"] = {
                "attempt_files": len(rows),
                "status_counts": statuses,
                "deleted_generation_errors": sum(key.startswith(prefix) for key in deleted),
                "final_scored": len(finals),
                "mean_final": round(sum(finals) / len(finals), 2) if finals else None,
                "flagged_gap_5": sum(
                    bool(task["flag_gap_5"])
                    for key, task in scores.items()
                    if key.startswith(prefix)
                ),
            }
    return summary


def client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["AZURE_OPENAI_BASE_URL"].strip(),
        api_key=os.environ["AZURE_OPENAI_API_KEY"].strip(),
        max_retries=0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--name", required=True, help="subdirectory under the result root")
    parser.add_argument("--stage", choices=["generate", "judge", "all"], default="all")
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build and print the frozen inputs without any API call",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=False)
    config = load_config()
    gen_prompt = bench.load_prompt(GEN_PROMPT)
    if args.dry_run:
        for cell in config["cells"]:
            system, user = cell_messages(cell, gen_prompt)
            print(f"{cell['cell_id']}: system {len(system)} chars, user {len(user)} chars")
        calls = len(config["cells"]) * len(config["models"]) * args.attempts
        print(f"generation requests: {calls}")
        print(f"judge requests (max): {2 * calls}")
        return

    output = RESULT_ROOT / args.name
    output.mkdir(parents=True, exist_ok=True)
    check_or_write_manifest(output, frozen_manifest(config, gen_prompt, args.attempts))
    deployment = os.environ["AZURE_OPENAI_LUNA_MODEL"].strip()
    api = client()
    if args.stage in ("generate", "all"):
        generation_stage(api, output, config, gen_prompt, args.attempts)
    if args.stage in ("judge", "all"):
        judge_stage(api, output, config, deployment)
    write_json(output / "summary.json", summarize(output, config))
    print(json.dumps(read_json(output / "summary.json"), indent=2))


if __name__ == "__main__":
    main()
