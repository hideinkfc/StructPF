"""User-friendly CLI for the StructPF generation and evaluation pipeline.

Provides five subcommands:
  - list:     Browse built-in curriculum topics and benchmark cases (offline).
  - generate: Generate a Productive Failure task with StructPF or one-shot prompting.
  - evaluate: Evaluate a generated or saved task with the 5-measure v3.0 evaluator,
              the 2-gate prior-knowledge/shortcut check, or the 5D surface rubric.
  - inspect:  Print a readable summary of any saved run directory or result JSON (offline).
  - figures:  Render the thesis overview and result figures (offline).
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_diagnostic as diagnostic  # noqa: E402
from scripts import run_progression_bridge_study as bridge_study  # noqa: E402
from scripts.build_progression_bridge_dataset import (  # noqa: E402
    load_progression_bridge_dataset,
    progression_bridge_bundle,
)
from scripts.prior_methods.common import MODEL_ENVS, chat_json, load_client  # noqa: E402
from scripts.run_pf_accessibility_sensitivity import build_chats  # noqa: E402
from scripts.run_prior_recommendations import _load_cases as load_classic_cases  # noqa: E402
from src.evaluation import pf_rubric_setting as rubric_eval  # noqa: E402
from src.evaluation import pf_three_role_v30 as v30  # noqa: E402
from src.evaluation.frozen import pf_three_role_v22 as v22  # noqa: E402
from src.evaluation.frozen import pf_three_role_v25 as v25  # noqa: E402
from src.evaluation.pf_task_measures import MEASURES  # noqa: E402

RAHIMI_CONFIG = ROOT / "experiments/configs/pf_rahimi_multi_theme_setting.json"
DEFAULT_RUNS_DIR = ROOT / "experiments/results/runs"

FIGURE_SCRIPTS: dict[int, list[str]] = {
    1: ["scripts/render_fig1_1_intro_overview.py"],
    2: ["scripts/render_fig2_1_rahimi_setup_rubric.py"],
    3: [
        "scripts/render_fig3_1_oneshot_setup.py",
        "scripts/render_fig3_2_rubric_results.py",
        "scripts/render_fig3_issue_examples.py",
    ],
    4: [
        "scripts/render_fig4_1_structpf_overview.py",
        "scripts/render_fig4_2_learning_commons_graph.py",
        "scripts/render_fig4_3_stage2_design_and_check.py",
        "scripts/render_fig4_4_stage3_task_writer.py",
        "scripts/render_fig4_6_structpf_architecture.py",
    ],
    5: [
        "scripts/render_fig5_1_simstudent_vs_solver.py",
        "scripts/render_fig5_2_eval_overview.py",
        "scripts/render_fig5_3_three_roles.py",
    ],
}


def _load_env() -> None:
    """Load .env.local first, then fall back to .env so either file works."""
    load_dotenv(ROOT / ".env.local", override=False)
    load_dotenv(ROOT / ".env", override=False)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _load_all_catalogs() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    lc_cases: dict[str, dict] = {}
    try:
        ds = load_progression_bridge_dataset()
        for item in ds.get("cases", []):
            lc_cases[item["id"]] = item
    except Exception:
        pass

    classic_cases: dict[str, dict] = {}
    try:
        for item in load_classic_cases():
            if isinstance(item, dict) and item.get("id"):
                classic_cases[item["id"]] = item
    except Exception:
        pass

    rahimi_cells: dict[str, dict] = {}
    if RAHIMI_CONFIG.is_file():
        raw = json.loads(RAHIMI_CONFIG.read_text(encoding="utf-8"))
        for item in raw.get("cells", []):
            if isinstance(item, dict):
                cid = item.get("cell_id") or item.get("id")
                case_obj = item.get("case") or item
                if cid:
                    rahimi_cells[str(cid)] = {
                        "id": str(cid),
                        "grade": case_obj.get("grade", 7),
                        "topic": case_obj.get("topic", ""),
                        "target_concept": case_obj.get("target_concept", ""),
                        "benchmark_context": case_obj.get("benchmark_context") or {},
                    }

    return lc_cases, classic_cases, rahimi_cells


def _std_code(item: dict[str, Any]) -> str:
    if item.get("target_code"):
        return str(item["target_code"])
    bridge = item.get("progression_bridge") or {}
    target_std = bridge.get("target_standard") or {}
    return str(target_std.get("statementCode") or "-")


def _matches_filter(item: dict[str, Any], grade: int | None, search: str | None) -> bool:
    if grade is not None and str(item.get("grade", "")).strip() != str(grade).strip():
        return False
    if search:
        needle = search.lower()
        haystack = " ".join(
            [
                _std_code(item),
                *(
                    str(item.get(k, ""))
                    for k in ("id", "topic", "target_concept", "jurisdiction", "theme")
                ),
            ]
        ).lower()
        if needle not in haystack:
            return False
    return True


def cmd_list(args: argparse.Namespace) -> int:
    lc_cases, classic_cases, rahimi_cells = _load_all_catalogs()

    if args.dataset in {"all", "lc30"}:
        rows = [c for c in lc_cases.values() if _matches_filter(c, args.grade, args.search)]
        print(
            f"\n=== Learning Commons Progression Bridge Topics ({len(rows)} / {len(lc_cases)}) ==="
        )
        print(f"{'Case ID':<44} {'Grade':<6} {'Standard':<13} {'Topic'}")
        print("-" * 105)
        for c in rows:
            print(f"{c['id']:<44} G{c['grade']:<5} {_std_code(c):<13} {c['topic']}")

    if args.dataset in {"all", "classic8"}:
        rows = [c for c in classic_cases.values() if _matches_filter(c, args.grade, args.search)]
        print(
            f"\n=== Classic & Multi-Curriculum Benchmark Cases ({len(rows)} / {len(classic_cases)}) ==="
        )
        print(f"{'Case ID':<44} {'Grade':<6} {'Jurisdiction':<15} {'Topic'}")
        print("-" * 105)
        for c in rows:
            print(
                f"{c['id']:<44} G{c['grade']:<5} {str(c.get('jurisdiction', '-')):<15} {c['topic']}"
            )

    if args.dataset in {"all", "rahimi4"}:
        rows = [c for c in rahimi_cells.values() if _matches_filter(c, args.grade, args.search)]
        print(f"\n=== One-Shot Multi-Theme Grade 7 Cells ({len(rows)} / {len(rahimi_cells)}) ===")
        print(f"{'Cell ID':<44} {'Grade':<6} {'Theme':<22} {'Target Concept'}")
        print("-" * 105)
        for c in rows:
            theme = (c.get("benchmark_context") or {}).get("theme", c.get("theme", "-"))
            target = str(c.get("target_concept", ""))[:42]
            print(f"{c['id']:<44} G{c.get('grade', 7):<5} {theme:<22} {target}")

    print()
    return 0


def _extract_task_dict(res: dict[str, Any]) -> dict[str, Any]:
    stages = res.get("stages") or {}
    d2_d3 = stages.get("D2_D3") or {}
    if isinstance(d2_d3.get("task"), dict):
        return d2_d3["task"]
    d2 = stages.get("D2") or {}
    for key in ("student_task", "final_task", "task"):
        candidate = d2.get(key) or res.get(key)
        if isinstance(candidate, dict):
            return candidate
    return {}


def _print_generation_summary(res: dict[str, Any], out_dir: Path) -> None:
    print("\n" + "=" * 88)
    print(f"Generation Status : {res.get('status')}  (saved to {out_dir.relative_to(ROOT)})")
    print("=" * 88)

    d1_recs = bridge_study.extract_d1_resources(res)
    if d1_recs:
        print(f"\n[Stage 1] Prior-Knowledge Skills ({len(d1_recs)}):")
        for idx, rec in enumerate(d1_recs, start=1):
            print(f"  {idx}. {rec.get('resource')}: {rec.get('taught_as')}")
            if rec.get("student_move"):
                print(f"     First move: {rec.get('student_move')}")

    stages = res.get("stages") or {}
    d2_d3 = stages.get("D2_D3") or {}
    winner = d2_d3.get("original_winner") or {}
    selected_brief = winner.get("brief") if isinstance(winner, dict) else {}
    if isinstance(selected_brief, dict) and selected_brief.get("goal"):
        print(f"\n[Stage 2a] Selected Design Brief Goal:\n  {selected_brief['goal']}")

    d2b = d2_d3.get("design_data") or d2_d3.get("d2b") or {}
    if isinstance(d2b, dict) and d2b:
        accepted = d2b.get("accepted", (d2b.get("check") or {}).get("passed"))
        vals = (d2b.get("payload") or d2b.get("proposal") or {}).get("values") or {}
        print(f"\n[Stage 2b] Calculator Verification: accepted={accepted}")
        if vals:
            print(f"  Verified values: {json.dumps(vals, ensure_ascii=False)}")

    task = _extract_task_dict(res)
    if task:
        print("\n[Stage 3] Student-Facing PF Task:")
        print("-" * 88)
        if task.get("title"):
            print(f"Title: {task['title']}\n")
        if task.get("body"):
            print(f"{task['body']}\n")
        if task.get("question"):
            print(f"Question:\n{task['question']}")
        print("-" * 88)


def cmd_generate(args: argparse.Namespace) -> int:
    _load_env()
    lc_cases, classic_cases, _ = _load_all_catalogs()

    lc_case: dict[str, Any] | None = None
    classic_case: dict[str, Any] | None = None

    if args.case:
        if args.case in lc_cases:
            lc_case = lc_cases[args.case]
        elif args.case in classic_cases:
            classic_case = classic_cases[args.case]
        else:
            print(
                f"Error: Unknown case {args.case!r}. Run `python scripts/structpf.py list` to see available cases.",
                file=sys.stderr,
            )
            return 1
        case_id = args.case
    else:
        if not (args.grade and args.topic and args.target):
            print(
                "Error: Provide either `--case <CASE_ID>` OR custom `--grade`, `--topic`, and `--target`.",
                file=sys.stderr,
            )
            return 1
        if args.standard:
            for item in lc_cases.values():
                if _std_code(item).lower() == args.standard.lower():
                    lc_case = copy.deepcopy(item)
                    lc_case["grade"] = args.grade
                    lc_case["topic"] = args.topic
                    lc_case["target_concept"] = args.target
                    break
        slug = "".join(ch if ch.isalnum() else "_" for ch in args.topic.lower()).strip("_")[:32]
        case_id = f"custom_g{args.grade}_{slug}"

    out_dir = (
        Path(args.output)
        if args.output
        else DEFAULT_RUNS_DIR / f"{_timestamp()}_{case_id}_{args.mode}"
    )
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    grounding = args.grounding
    if grounding == "auto":
        if lc_case is not None:
            grounding = "lc"
        elif classic_case is not None:
            grounding = "curriculum"
        else:
            grounding = "none"

    print(
        f"Running {args.mode.upper()} generation for {case_id!r} "
        f"(model={args.model}, grounding={grounding}) ..."
    )

    if lc_case is not None:
        case_input = bridge_study.build_generation_case_input(lc_case)
        case_input["id"] = case_id
    elif classic_case is not None:
        case_input = copy.deepcopy(classic_case)
    else:
        case_input = {
            "id": case_id,
            "grade": args.grade,
            "subject": args.subject,
            "jurisdiction": args.jurisdiction,
            "topic": args.topic,
            "target_concept": args.target,
            "exclude_resource_terms": [],
            "teacher_skills": [],
        }

    if args.mode == "oneshot":
        res = bridge_study.run_direct_case_worker(case_input, out_dir, args.model)
    else:
        d1_cond = "ungrounded" if grounding == "none" else "grounded"
        lc_records = (
            bridge_study.build_lc_grounding_records(lc_case)
            if grounding == "lc" and lc_case is not None
            else None
        )
        shared = (
            {"learning_commons_progression_bridge": progression_bridge_bundle(lc_case["id"])}
            if grounding == "lc" and lc_case is not None
            else None
        )
        res = diagnostic.run_case_worker(
            case_id,
            str(out_dir),
            args.model,
            args.proposals,
            None,
            case_override=case_input,
            shared_context=shared,
            d1_condition=d1_cond,
            grounding_evidence=lc_records,
            evidence_k=len(lc_records) if lc_records else 6,
            learning_commons=(grounding == "lc" and lc_case is None),
        )

    task_txt = bridge_study.extract_student_task(res)
    if task_txt:
        (out_dir / "student_task.md").write_text(task_txt + "\n", encoding="utf-8")

    _print_generation_summary(res, out_dir)

    if args.evaluate and task_txt:
        eval_args = argparse.Namespace(
            run=str(out_dir),
            mode="v30",
            judge_model=args.model,
            case=lc_case["id"] if lc_case else (classic_case["id"] if classic_case else None),
        )
        return cmd_evaluate(eval_args)
    return 0 if res.get("status") == "completed" else 1


def _resolve_eval_inputs(
    run_path: Path, case_hint: str | None
) -> tuple[str, str, dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    lc_cases, classic_cases, _ = _load_all_catalogs()
    res_file = run_path / "result.json" if run_path.is_dir() else run_path
    data = json.loads(res_file.read_text(encoding="utf-8"))

    if "student_task" in data and "learner_context" in data and "learning_target" in data:
        return (
            str(data["student_task"]),
            str(data["learning_target"]),
            dict(data["learner_context"]),
            data,
            None,
        )

    case_id = case_hint or data.get("case_id") or (data.get("case_input") or {}).get("id")
    lc_case = lc_cases.get(str(case_id)) if case_id else None
    classic_case = classic_cases.get(str(case_id)) if case_id else None

    task_txt = bridge_study.extract_student_task(data)
    if not task_txt and isinstance(data.get("title"), str):
        task_txt = bridge_study.student_task_text(data)

    case_in = data.get("case_input") or lc_case or classic_case or {}
    target = str(case_in.get("target_concept") or data.get("learning_target") or "")

    if lc_case is not None:
        learner_ctx = bridge_study.build_official_learner_context(lc_case)
    else:
        d1_recs = bridge_study.extract_d1_resources(data)
        skills = [
            f"{r.get('resource')}: {r.get('taught_as')}" for r in d1_recs if r.get("resource")
        ] or list(case_in.get("teacher_skills") or [])
        learner_ctx = {
            "grade": str(case_in.get("grade", "7")),
            "subject": str(case_in.get("subject", "mathematics")),
            "jurisdiction": str(case_in.get("jurisdiction", "USA")),
            "assumed_prior_knowledge": skills,
        }
    return task_txt, target, learner_ctx, data, lc_case


def cmd_evaluate(args: argparse.Namespace) -> int:
    _load_env()
    run_path = Path(args.run)
    if not run_path.is_absolute():
        run_path = ROOT / run_path
    if not run_path.exists():
        print(f"Error: Path does not exist: {run_path}", file=sys.stderr)
        return 1

    out_dir = run_path if run_path.is_dir() else run_path.parent
    task_txt, target, learner_ctx, raw_data, lc_case = _resolve_eval_inputs(run_path, args.case)
    if not task_txt.strip():
        print("Error: Could not find student task text in the supplied path.", file=sys.stderr)
        return 1

    print(f"\nEvaluating task in {out_dir.relative_to(ROOT)} (mode={args.mode}) ...")

    if args.mode in {"v30", "task-only"}:
        solver_chats, judge_chats = build_chats()
        judge_chat = judge_chats.get(args.judge_model) or next(iter(judge_chats.values()))
        if args.mode == "task-only":
            prepared = v25.prepare_input(task_txt, target, copy.deepcopy(learner_ctx))
            job = v30.run_judge_v30(
                "task_judge", v22.role_input("task_judge", prepared), judge_chat
            )
            measures = (
                v30.parse_task_v30(job["output"], prepared) if job["status"] == "completed" else {}
            )
            eval_out = {
                "version": v30.VERSION,
                "mode": "task-only",
                "measures": measures,
                "task_judge": job,
            }
        else:
            eval_out = v30.evaluate_v30(
                task_txt,
                target,
                copy.deepcopy(learner_ctx),
                solver_chats=solver_chats,
                judge_chat=judge_chat,
                toolkit=True,
            )
        out_file = out_dir / f"evaluation_{args.mode.replace('-', '_')}.json"
        out_file.write_text(
            json.dumps(eval_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        print("\n=== Five Task-Design Measures (pf-three-role/v3.0) ===")
        for m in MEASURES:
            row = (eval_out.get("measures") or {}).get(m) or {}
            val = row.get("value") or row.get("status") or "not_assessed"
            print(f"  - {m:<32}: {str(val).upper()}")
        counts = eval_out.get("approach_counts")
        if counts:
            print(
                f"\n  Solver attempts: {counts.get('attempts_produced')} total | "
                f"target_limit={counts.get('target_limits')} | "
                f"meets_demands={counts.get('meets_demands')} | "
                f"not_supported={counts.get('not_supported')}"
            )
        print(f"Saved full audit to {out_file.relative_to(ROOT)}\n")
        return 0

    if args.mode == "gates":
        if lc_case is None:
            print(
                "Error: `--mode gates` requires a Learning Commons progression bridge case (`--case <ID>`).",
                file=sys.stderr,
            )
            return 1
        client, model = load_client(args.judge_model)
        k_prior = bridge_study.extract_d1_resources(raw_data)
        g1 = bridge_study.evaluate_gate1_prior_set(client, model, lc_case, k_prior, task_txt)
        g2 = bridge_study.evaluate_gate2_solver_trap(client, model, lc_case, g1, task_txt)
        score = 0 if not g1["gate1_passed"] else int(g2["two_gate_score"])
        eval_out = {"gate1": g1, "gate2": g2, "two_gate_score": score}
        out_file = out_dir / "evaluation_gates.json"
        out_file.write_text(
            json.dumps(eval_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("\n=== Two-Gate Progression Check ===")
        print(
            f"  Gate 1 (Prior-Knowledge Validity) : {'PASS' if g1['gate1_passed'] else 'FAIL'} ({g1['valid_count']}/{g1['total_count']} valid, spoilers={g1['spoiler_count']})"
        )
        print(f"  Gate 2 (Shortcut Failure on Task) : {g2.get('gate2_outcome', 'skipped').upper()}")
        print(f"  Combined Two-Gate Score (0-2)     : {score} / 2")
        print(f"Saved full audit to {out_file.relative_to(ROOT)}\n")
        return 0

    if args.mode == "rubric":
        client, model = load_client(args.judge_model)
        prompt = rubric_eval.load_prompt()
        case_meta = {
            "target_concept": target,
            "benchmark_context": {"theme": "general mathematics", "interest": "problem solving"},
        }
        user_msg = rubric_eval.judge_input(task_txt, case_meta, learner_ctx)
        payload, _ = chat_json(
            client, model, prompt["system"], user_msg, temperature=0.0, max_tokens=2500
        )
        rating = rubric_eval.parse_rating(payload or {})
        out_file = out_dir / "evaluation_rubric.json"
        out_file.write_text(
            json.dumps(rating, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("\n=== Five-Dimension Surface Rubric (Rahimi et al., 2025) ===")
        for dim in rubric_eval.DIMENSIONS:
            score_val = (rating.get("dimensions") or {}).get(dim, {}).get("score")
            print(f"  - {dim:<6}: {score_val} / 3")
        print(f"  Total   : {rating.get('total_score')} / 15")
        print(f"Saved full rating to {out_file.relative_to(ROOT)}\n")
        return 0

    return 1


def cmd_inspect(args: argparse.Namespace) -> int:
    run_path = Path(args.run)
    if not run_path.is_absolute():
        run_path = ROOT / run_path
    res_file = run_path / "result.json" if run_path.is_dir() else run_path
    if not res_file.is_file():
        print(f"Error: Could not find result JSON at {res_file}", file=sys.stderr)
        return 1
    res = json.loads(res_file.read_text(encoding="utf-8"))
    out_dir = res_file.parent
    _print_generation_summary(res, out_dir)

    for eval_file in sorted(out_dir.glob("evaluation_*.json")):
        print(f"\nFound saved evaluation: {eval_file.name}")
        ev = json.loads(eval_file.read_text(encoding="utf-8"))
        if "measures" in ev:
            for m in MEASURES:
                row = (ev.get("measures") or {}).get(m) or {}
                print(f"  - {m:<32}: {row.get('value') or row.get('status')}")
        elif "two_gate_score" in ev:
            print(f"  - Two-Gate Score: {ev.get('two_gate_score')} / 2")
        elif "total_score" in ev:
            print(f"  - 5D Rubric Total: {ev.get('total_score')} / 15")
    print()
    return 0


def cmd_figures(args: argparse.Namespace) -> int:
    chapters = [args.chapter] if args.chapter else sorted(FIGURE_SCRIPTS)
    scripts_to_run = [s for ch in chapters for s in FIGURE_SCRIPTS.get(ch, [])]
    for rel_script in scripts_to_run:
        print(f"Rendering {rel_script} ...")
        subprocess.run([sys.executable, str(ROOT / rel_script)], check=True)
    print("All requested figures rendered into thesis/figures/.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structpf",
        description="Unified CLI for StructPF task generation, evaluation, inspection, and figures.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List built-in curriculum topics and benchmark cases.")
    p_list.add_argument(
        "--dataset",
        choices=["all", "lc30", "classic8", "rahimi4"],
        default="all",
        help="Filter by catalog (default: all).",
    )
    p_list.add_argument(
        "--grade", type=int, default=None, help="Filter by grade level (e.g. 6, 7, 8)."
    )
    p_list.add_argument(
        "--search", type=str, default=None, help="Filter by keyword in ID, standard, or topic."
    )
    p_list.set_defaults(func=cmd_list)

    p_gen = sub.add_parser(
        "generate", help="Generate a PF task using StructPF or one-shot prompting."
    )
    p_gen.add_argument(
        "--case", type=str, default=None, help="Built-in case ID (see `structpf list`)."
    )
    p_gen.add_argument(
        "--grade", type=int, default=None, help="Grade level for a custom topic (e.g. 7)."
    )
    p_gen.add_argument("--topic", type=str, default=None, help="Topic name for a custom run.")
    p_gen.add_argument(
        "--target", type=str, default=None, help="Target concept description for a custom run."
    )
    p_gen.add_argument(
        "--standard",
        type=str,
        default=None,
        help="Optional Common Core code (e.g. 6.G.A.1) to attach Learning Commons prerequisites.",
    )
    p_gen.add_argument(
        "--subject", type=str, default="mathematics", help="Subject (default: mathematics)."
    )
    p_gen.add_argument(
        "--jurisdiction", type=str, default="USA", help="Jurisdiction (default: USA)."
    )
    p_gen.add_argument(
        "--mode",
        choices=["structpf", "oneshot"],
        default="structpf",
        help="Generation method: `structpf` (3-stage pipeline) or `oneshot` (baseline).",
    )
    p_gen.add_argument(
        "--grounding",
        choices=["auto", "lc", "curriculum", "none"],
        default="auto",
        help="Stage 1 prior-knowledge source (default: auto).",
    )
    p_gen.add_argument(
        "--model",
        choices=sorted(MODEL_ENVS),
        default="luna",
        help="Model selector from .env / .env.local (default: luna).",
    )
    p_gen.add_argument(
        "--proposals", type=int, default=2, help="Step 2a candidate brief count (default: 2)."
    )
    p_gen.add_argument("--output", type=str, default=None, help="Custom output directory.")
    p_gen.add_argument(
        "--evaluate",
        action="store_true",
        help="Immediately evaluate the generated task with the 5-measure v3.0 evaluator.",
    )
    p_gen.set_defaults(func=cmd_generate)

    p_eval = sub.add_parser("evaluate", help="Evaluate a generated run directory or task JSON.")
    p_eval.add_argument("--run", required=True, help="Path to a run directory or result.json file.")
    p_eval.add_argument(
        "--mode",
        choices=["v30", "task-only", "gates", "rubric"],
        default="v30",
        help="Evaluation instrument: `v30` (5 measures + solver), `task-only`, `gates` (Gate 1+2), or `rubric` (5D).",
    )
    p_eval.add_argument(
        "--case", type=str, default=None, help="Optional case ID override for reference context."
    )
    p_eval.add_argument(
        "--judge-model",
        choices=sorted(MODEL_ENVS),
        default="luna",
        help="Judge model selector (default: luna).",
    )
    p_eval.set_defaults(func=cmd_evaluate)

    p_insp = sub.add_parser(
        "inspect", help="Print a clean summary of a saved run directory (offline)."
    )
    p_insp.add_argument(
        "--run", required=True, help="Path to a saved run directory or result.json."
    )
    p_insp.set_defaults(func=cmd_inspect)

    p_fig = sub.add_parser("figures", help="Render thesis figures into thesis/figures/ (offline).")
    p_fig.add_argument(
        "--chapter",
        type=int,
        choices=sorted(FIGURE_SCRIPTS),
        default=None,
        help="Render figures for one chapter only (1-5); omit to render all.",
    )
    p_fig.set_defaults(func=cmd_figures)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
