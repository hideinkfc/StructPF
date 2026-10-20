"""Eedi coverage pilot: do solver approaches reproduce the wrong answers and misconceptions students show?

Stages (each saved per case, so reruns reuse finished jobs):
  solver  - the frozen v3.0 solver, two models, text-only, options hidden
  direct  - one-call baseline: the same model proposes up to four approaches without the solver loop
  judge   - the frozen matching judge maps each approach to an option and to a wrong option's misconception
  score   - student-weighted coverage (pct_students of wrong options), oracle and random references

Computational pilot. The percentages are real student choices; the matches are model judgements
that have not yet been checked by hand.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation import pf_three_role_v30 as v30
from src.evaluation.frozen import pf_three_role_v22 as v22
from src.evaluation.frozen import pf_three_role_v25 as v25
from src.utils.llm_client import LLMResponse

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "experiments/configs/pf_eedi_coverage_cases_20261016.json"
PROFILES = ROOT / "experiments/configs/pf_eedi_profiles_20261016_v2.yaml"
JUDGE = ROOT / "src/evaluation/prompts/pf_eedi_match_v1.yaml"
OUTPUT = ROOT / "experiments/results/pf_eedi_coverage_20261016"
SOLVERS = ("luna", "gpt41")
DIRECT_SYSTEM = (
    "You are simulating how a learner with ONLY the listed prior knowledge might attempt a maths "
    "question. Do not use any knowledge that is not listed. Propose up to four distinct approaches, "
    "each a different mathematical idea. For each, give the working in words and the final answer. "
    'Return JSON only: {"approaches":[{"idea":<string>,"work":<string>,"final_answer":<string>}]}'
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_profiles() -> dict[str, dict]:
    spec = yaml.safe_load(PROFILES.read_text())
    out = {}
    for topic, resources in spec["profiles"].items():
        out[topic] = {
            "grade": "Year 8 (UK, age 12-13)",
            "subject": "mathematics",
            "country": "UK",
            "assumed_prior_knowledge": [{"resource": r, "taught_as": r} for r in resources],
        }
    return out


def learner_context(case: dict, profiles: dict[str, dict]) -> dict:
    return copy.deepcopy(profiles[case["topic"]])


def run_solver(case: dict, solver_id: str, chat, profiles: dict, out: Path) -> dict:
    path = out / "solver" / f"{case['case_id']}__{solver_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    ctx = learner_context(case, profiles)
    prepared = v25.prepare_input(case["stem"], None, copy.deepcopy(ctx))
    payload = v22.role_input("solver", prepared)
    rec = v30.run_solver_v30(payload, chat, solver_id=solver_id, toolkit=True)
    record = {"case_id": case["case_id"], "solver": solver_id, "started_at": now(), "run": rec}
    save(path, record)
    return record


def run_direct(case: dict, chat, profiles: dict, out: Path) -> dict:
    path = out / "direct" / f"{case['case_id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    ctx = learner_context(case, profiles)
    messages = [
        {"role": "system", "content": DIRECT_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {"student_task": case["stem"], "learner_context": ctx}, ensure_ascii=False
            ),
        },
    ]
    record = {
        "case_id": case["case_id"],
        "started_at": now(),
        "status": "completed",
        "raw": None,
        "approaches": [],
    }
    try:
        response = chat(messages)
        record["raw"] = response.text
        raw = json.loads(response.text)
        approaches = raw.get("approaches")
        if not isinstance(approaches, list) or not approaches:
            raise ValueError("approaches must be a non-empty list")
        record["approaches"] = [
            {
                "idea": str(a.get("idea", "")).strip(),
                "work": str(a.get("work", "")).strip(),
                "final_answer": str(a.get("final_answer", "")).strip(),
            }
            for a in approaches[:4]
        ]
    except Exception as exc:  # keep the failure visible in the record
        record["status"] = "invalid_response"
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["finished_at"] = now()
    save(path, record)
    return record


def solver_items(record: dict) -> list[dict]:
    run = record["run"]
    if run["status"] != "completed":
        return []
    return [{"idea": a["idea"], "work": a["work"]} for a in run["output"]["attempts"]]


def judge_prompt_text(case: dict) -> str:
    options = []
    for o in case["options"]:
        options.append(
            {
                "letter": o["letter"],
                "text": o["text"],
                "is_correct": o["is_correct"],
                "error_description": None if o["is_correct"] else o["error_explanation"],
            }
        )
    return json.dumps({"question": case["stem"], "options": options}, ensure_ascii=False)


def run_judge(
    case: dict, system_name: str, items: list[dict], chat, judge_system: str, out: Path
) -> dict:
    path = out / "judge" / f"{case['case_id']}__{system_name}.json"
    if path.exists():
        return json.loads(path.read_text())
    record = {
        "case_id": case["case_id"],
        "system": system_name,
        "started_at": now(),
        "items": items,
    }
    if not items:
        record.update({"status": "no_approaches", "matches": []})
        save(path, record)
        return record
    payload = {
        "question_and_options": json.loads(judge_prompt_text(case)),
        "approaches": [{"approach_index": i, **item} for i, item in enumerate(items)],
    }
    messages = [
        {"role": "system", "content": judge_system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    try:
        response: LLMResponse = chat(messages)
        raw = json.loads(response.text)
        matches = raw.get("matches")
        if not isinstance(matches, list) or len(matches) != len(items):
            raise ValueError(
                f"expected {len(items)} matches, got {len(matches) if isinstance(matches, list) else 'non-list'}"
            )
        for m, item in zip(matches, items):
            for field, text in (("answer_quote", item["work"]), ("reasoning_quote", item["work"])):
                quote = m.get(field)
                m[f"{field}_in_work"] = bool(quote) and quote in text
        record.update({"status": "completed", "matches": matches})
    except Exception as exc:
        record.update(
            {"status": "invalid_response", "error": f"{type(exc).__name__}: {exc}", "matches": []}
        )
    record["finished_at"] = now()
    save(path, record)
    return record


def coverage(case: dict, match_records: list[dict]) -> dict:
    options = {o["letter"]: o for o in case["options"]}
    wrong = [o for o in case["options"] if not o["is_correct"]]
    wrong_letters = {o["letter"] for o in wrong}
    total = sum(o["pct_students"] for o in wrong)
    n = len(wrong)
    value_hit, mis_yes, mis_any = set(), set(), set()
    approaches = 0
    failed = []
    for rec in match_records:
        if rec["status"] not in ("completed", "no_approaches"):
            failed.append(rec["system"])
            continue
        for m in rec["matches"]:
            approaches += 1
            if m.get("final_answer_option") in wrong_letters:
                value_hit.add(m["final_answer_option"])
            letter = m.get("misconception_letter")
            if letter in wrong_letters:
                if m.get("misconception_strength") == "yes":
                    mis_yes.add(letter)
                if m.get("misconception_strength") in ("yes", "partly"):
                    mis_any.add(letter)
    k = min(approaches, n)
    pct = {letter: options[letter]["pct_students"] for letter in wrong_letters}
    top_k = sorted(pct.values(), reverse=True)[:k]
    return {
        "case_id": case["case_id"],
        "topic": case["topic"],
        "wrong_options": n,
        "wrong_pct_total": total,
        "approaches": approaches,
        "failed_systems": failed,
        "value_weighted": sum(pct[label] for label in value_hit) / total if total else None,
        "misconception_weighted": sum(pct[label] for label in mis_yes) / total if total else None,
        "misconception_partly_weighted": sum(pct[label] for label in mis_any) / total
        if total
        else None,
        "misconception_unweighted": len(mis_yes) / n if n else None,
        "oracle_top_k_weighted": sum(top_k) / total if total and k else None,
        "random_k_fraction": k / n if n else None,
        "matched_misconceptions": sorted(mis_yes),
    }


def mean(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def summarise(rows: list[dict]) -> dict:
    keys = [
        "value_weighted",
        "misconception_weighted",
        "misconception_partly_weighted",
        "misconception_unweighted",
        "oracle_top_k_weighted",
        "random_k_fraction",
    ]
    by_topic = defaultdict(list)
    for r in rows:
        by_topic[r["topic"]].append(r)
    return {
        "cases": len(rows),
        "means": {k: mean([r[k] for r in rows]) for k in keys},
        "mean_approaches_per_case": mean([r["approaches"] for r in rows]),
        "cases_with_no_approaches": sum(1 for r in rows if r["approaches"] == 0),
        "by_topic": {
            t: {
                "cases": len(v),
                "misconception_weighted": mean([r["misconception_weighted"] for r in v]),
            }
            for t, v in sorted(by_topic.items())
        },
    }


def select(cases: list[dict], limit: int | None) -> list[dict]:
    if not limit:
        return cases
    step = max(1, len(cases) // limit)
    return cases[::step][:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--limit", type=int, default=None, help="evenly spaced subset for calibration"
    )
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    cases = select(json.loads(CASES.read_text())["cases"], args.limit)
    profiles = load_profiles()
    judge_system = (
        yaml.safe_load(JUDGE.read_text())["system"]
        + "\n"
        + yaml.safe_load(JUDGE.read_text())["contract"]
    )
    out = args.output.resolve()
    manifest = {
        "version": "pf-eedi-coverage/v1",
        "started_at": now(),
        "cases_sha256": sha(CASES),
        "profiles_sha256": sha(PROFILES),
        "judge_prompt_sha256": sha(JUDGE),
        "solver_prompt_sha256": v30.fingerprint(),
        "solver_system_sha256": {"toolkit": v30.solver_system_sha256(toolkit=True)},
        "case_count": len(cases),
        "limit": args.limit,
        "models": {"solvers": list(SOLVERS), "judge": "luna", "direct": "luna"},
    }
    save(out / "manifest.json", manifest)

    chats = build_chats()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = []
        for case in cases:
            for solver_id in SOLVERS:
                futs.append(
                    pool.submit(run_solver, case, solver_id, chats[solver_id], profiles, out)
                )
            futs.append(pool.submit(run_direct, case, chats["luna"], profiles, out))
        for fut in as_completed(futs):
            fut.result()

    jobs = []
    for case in cases:
        solver_recs = {
            s: json.loads((out / "solver" / f"{case['case_id']}__{s}.json").read_text())
            for s in SOLVERS
        }
        direct = json.loads((out / "direct" / f"{case['case_id']}.json").read_text())
        systems = {
            "solver_luna": [
                {**i, "source": "solver_luna"} for i in solver_items(solver_recs["luna"])
            ],
            "solver_gpt41": [
                {**i, "source": "solver_gpt41"} for i in solver_items(solver_recs["gpt41"])
            ],
            "direct": [
                {"idea": a["idea"], "work": a["work"], "source": "direct"}
                for a in direct.get("approaches", [])
            ],
        }
        for name, items in systems.items():
            jobs.append((case, name, items))

    judged: dict[tuple[str, str], dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(run_judge, case, name, items, chats["luna"], judge_system, out): (
                case["case_id"],
                name,
            )
            for case, name, items in jobs
        }
        for fut in as_completed(futs):
            judged[futs[fut]] = fut.result()

    rows = {"pf_solver": [], "solver_luna": [], "solver_gpt41": [], "direct": []}
    for case in cases:
        cid = case["case_id"]
        pooled = [judged[(cid, "solver_luna")], judged[(cid, "solver_gpt41")]]
        rows["solver_luna"].append(coverage(case, [judged[(cid, "solver_luna")]]))
        rows["solver_gpt41"].append(coverage(case, [judged[(cid, "solver_gpt41")]]))
        rows["pf_solver"].append(coverage(case, pooled))
        rows["direct"].append(coverage(case, [judged[(cid, "direct")]]))
    summary = {
        "generated_at": now(),
        "systems": {name: summarise(vals) for name, vals in rows.items()},
        "per_case": rows,
        "limitations": [
            "Matches are model judgements, not yet hand-checked.",
            "Learner profiles are pre-topic prerequisites; Eedi students were taught the topic first.",
            "Picture-dependent questions are excluded; the thermometer question was excluded by hand.",
        ],
    }
    save(out / "summary.json", summary)
    print(json.dumps({k: v["means"] for k, v in summary["systems"].items()}, indent=2))


if __name__ == "__main__":
    main()
