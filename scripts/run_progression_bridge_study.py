"""Run and evaluate the 20-case 2-arm Learning Commons Progression Bridge study.

Compares across all 20 curriculum progression bridges (Grades 5-10):
  - Arm A (ungrounded): Stage D1 -> D2a -> D2b -> D3 given only {grade, subject,
    topic, target_concept}, with no curriculum graph or hand-written teacher D1.
  - Arm B (lc_grounded): Stage D1 -> D2a -> D2b -> D3 given the same input plus
    the official Learning Commons v1.14.0 progression bridge (S_prior
    `buildsTowards` prerequisites and `supports` learning components for D1, and
    the structured progression bundle in shared_context for D2a-D3).

Evaluates every case with:
  1. Progression Bridge Fit (0 / 1 / 2) on (D1 prior resources + D3 student task)
     against the official S_prior --buildsTowards--> S_target edge.
  2. Position-swapped blinded pairwise comparison (Arm A vs Arm B) on the
     S_prior -> S_target progression bridge.
  3. The frozen pf-three-role/v2.9 five-measure evaluator using the official
     S_prior prerequisite standards as the grade's learner_context.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts import run_pf_diagnostic as diagnostic
from scripts.build_progression_bridge_dataset import (
    DEFAULT_DATASET_PATH,
    load_progression_bridge_dataset,
    progression_bridge_bundle,
)
from scripts.prior_methods.common import chat_json, load_client
from scripts.run_pf_accessibility_sensitivity import build_chats
from src.evaluation.frozen import pf_three_role_v29 as v29
from src.evaluation.pf_task_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments/results/pf_progression_bridge_20cases_20261016"
ARMS = ("ungrounded", "lc_grounded")
THREE_ARMS = ("direct", "ungrounded", "lc_grounded")
LC_EXPORT_URL = "https://cdn.learningcommons.org/knowledge-graph/v1.14.0/exports/nodes.jsonl"

DIRECT_WITH_K_PRIOR_SYSTEM = """\
ROLE AND OBJECTIVE
You are an educational design assistant creating a mathematics Productive Failure (PF)
problem for a target concept and grade level. You are NOT given a pre-built list of
prior knowledge; instead, you must:
1. Propose the set of prior-knowledge skills K_prior = {k_1, k_2, k_3} that students
   will use to attempt the problem before being taught the target concept.
2. Design one open-ended Productive Failure student task (title, body, question)
   that students can attempt using K_prior before instruction on the target concept.

RESPONSE RULES
- Do not supply a worked solution, teacher commentary, or a sequence of steps teaching
  the target concept.
- Leave room for students to choose and explain mathematical approaches using K_prior.
- Output ONLY a valid JSON object with exactly these fields:
{
  "status": "ready",
  "proposed_prior_knowledge": [
    {
      "resource": "Short name of the prior mathematical skill or concept",
      "taught_as": "What students previously learned to calculate or represent with this skill",
      "student_move": "Concrete calculation or step a student takes on this task using this skill"
    }
  ],
  "title": "...",
  "body": "...",
  "question": "..."
}
Include 3 distinct items in "proposed_prior_knowledge". Put the scenario and all
numerical data in "body", and the student prompt in "question"."""

GATE1_PRIOR_SET_JUDGE_SYSTEM = """\
You are an expert mathematics curriculum evaluator performing Gate 1 (Left-to-Right
Validity of the Proposed Prior-Knowledge Set K_prior = {k_1, ..., k_m}).

You are given:
1. The target concept C_target and grade level (plus official curriculum standards for
   context).
2. The generated student task T.
3. The generator's proposed prior-knowledge set K_prior = {k_1, ..., k_m}, where each
   k_i has {resource, taught_as, student_move}.

LEFT-TO-RIGHT VALIDITY RULE FOR EACH k_i (SKIPS IN BETWEEN ARE ALLOWED):
  [Basic Skill] ---> [Intermediate Skill] ---> [Direct Prerequisite] ===> [ C_target ]
  |<------------------------ VALID k_i ZONE --------------------------->|  |<- SPOILER ->|

Classify each k_i into exactly one of:
- "valid":
  1. Left-to-right arrow exists (k_i ---> ... ---> C_target): k_i sits strictly to the
     left of C_target on a mathematical learning progression. Very basic skills with
     skips in between ARE VALID as long as they lead toward C_target.
  2. Not a spoiler: NONE of k_i's fields (`resource`, `taught_as`, or `student_move`)
     state or execute the target concept/formula C_target, any term in
     `exclude_prior_terms`, or any target-level procedure beyond
     `curriculum_reference_direct_prereqs` and `curriculum_reference_prereq_components`.
     CRITICAL RULE: Any skill k_i whose `resource`, `taught_as`, and `student_move`
     remain within `curriculum_reference_direct_prereqs` or
     `curriculum_reference_prereq_components` is BY DEFINITION strictly to the left of
     C_target (`is_spoiler: false`, `has_left_to_right_arrow: true`) and must NEVER be
     classified as "spoiler".
  3. Helpful on Task T (`helpful_to_start_task: true`): Task T contains mathematical
     quantities/objects (numbers, tables, graphs, shapes, counts) on which a student
     can ATTEMPT k_i as a starting approach—EVEN IF k_i's simplifying assumption
     (such as proportionality y/x on a nonproportional function, whole-number division
     on a remainder problem, or whole-sample probability on a two-way table) fails or
     is insufficient on Task T! (Whether k_i succeeds or fails on Task T is tested in
     Gate 2, NOT Gate 1.)
- "irrelevant":
  * k_i is mathematically wrong/nonsense, comes from an unrelated math domain with no
    progression arrow k_i ---> ... ---> C_target, OR Task T has no quantities/objects
    on which a student could even try k_i (for example, k_i requires reading a dot plot,
    box plot, or graph when Task T only provides raw numbers or a table, or k_i requires
    factoring quadratics or independent-event products when they do not apply to Task T).
- "spoiler":
  * k_i (`resource`, `taught_as`, OR `student_move`) is already at or beyond C_target
    (k_i >= C_target), explicitly teaching or instructing the student to execute a
    target-level formula or procedure that goes strictly beyond
    `curriculum_reference_direct_prereqs` and `curriculum_reference_prereq_components`
    (for example: computing two-point slope (y2 - y1)/(x2 - x1) for 8.F.B.4; dividing
    successive values to test for constant multiplicative ratio for HSF-LE.A.1;
    multiplying P(A)*P(B) and comparing to P(A and B) for HSS-CP.A.2; restricting a
    probability denominator to a conditioning subgroup for HSS-CP.B.6; matching terms
    to (x + b)^2 = x^2 + 2bx + b^2 for HSA-SSE.B.3.b; or calculating people per square
    meter / mass per cubic meter in `student_move` for HSG-MG.A.2).

Also check `combination_is_spoiler`: true if one or more k_i is a "spoiler" OR if
combining the `taught_as` and `student_move` instructions of {k_1, ..., k_m} together
already spells out the complete target procedure C_target beyond
`curriculum_reference_direct_prereqs`.

Respond ONLY with valid JSON matching:
{
  "items": [
    {
      "index": 0,
      "resource": "...",
      "classification": "valid" | "irrelevant" | "spoiler",
      "has_left_to_right_arrow": true | false,
      "helpful_to_start_task": true | false,
      "is_spoiler": true | false,
      "reason": "1 concise sentence"
    }
  ],
  "combination_is_spoiler": true | false,
  "set_summary": "1-2 concise sentences summarizing Gate 1 for the set K_prior"
}"""

GATE2_K_VALID_SOLVER_SYSTEM = """\
You are a mathematics student solver attempting a problem using ONLY a restricted
set of allowed prior-knowledge skills K_valid = {k_1, ..., k_r} BEFORE being taught
the forbidden target concept C_target.

STRICT RULES:
1. For each skill k_i in K_valid, you may ONLY execute the literal procedure stated
   in k_i's `taught_as` and `student_move`. Do NOT upgrade a qualitative or whole-space
   prior skill into a more advanced formula!
2. You have NOT been taught `forbidden_target_concept` (or `forbidden_target_terms`).
   You are STRICTLY FORBIDDEN from applying the target concept's procedure (for example:
   do NOT restrict probability denominators to a subgroup if k_i only teaches sample-space
   probability; do NOT compute two-point slope (y2 - y1)/(x2 - x1) or solve for a non-zero
   intercept if k_i only teaches proportional ratio y/x or qualitative straight-line
   recognition; do NOT partition leftover division remainders into fractional shares if
   k_i only teaches whole-number division).
3. Only if Task T's numbers allow the literal prior skill k_i itself to get the right
   final answer/winner (for example, because both groups have the same sample size, or
   the relationship passes through (0,0), or the division has no remainder) should k_i
   succeed without hitting a limitation.
4. For EACH skill k_i in K_valid:
   - Apply ONLY k_i's literal `taught_as` / `student_move` to the numbers in Task T.
   - State the exact numerical result, naive conclusion, or incomplete step k_i produces.
   - State whether k_i hits a conflict, tie, or limitation on Task T's numbers.

Respond ONLY with valid JSON matching:
{
  "skill_attempts": [
    {
      "resource": "Name of k_i from K_valid",
      "calculation": "Concrete calculation on Task T's numbers using ONLY k_i's literal move",
      "result_or_winner": "The numerical value, ranking, or partial result produced by k_i",
      "hits_limitation_on_task": true | false,
      "limitation_description": "What conflict, tie, or gap k_i hits on Task T"
    }
  ],
  "combined_attempt_summary": "What happens when comparing all literal K_valid attempts on Task T",
  "solves_task_without_new_concept": true | false
}"""

GATE2_TRAP_JUDGE_SYSTEM = """\
You are an expert mathematics education evaluator performing Gate 2 (Solver Trap Check
on Task T using the Valid Prior-Knowledge Set K_valid).

You are given:
1. The target concept C_target.
2. The generated student task T.
3. The valid prior-knowledge set K_valid = {k_1, ..., k_r} that passed Gate 1.
4. The K_valid-Only Solver's concrete mathematical attempts on Task T using each k_i
   in K_valid.

Classify the Gate 2 outcome into Score 1 or Score 2:
- Score 1 ("trap_bypassed" or "off_target_failure"):
  * "trap_bypassed": AT LEAST ONE k_i in K_valid (using ONLY k_i's literal prior-skill
    procedure, without smuggling in C_target) directly gets the right final answer/winner
    on Task T's numbers (for example, because group sizes are equal so raw counts give
    the same winner as conditional rates, or the line passes through (0,0) so y/x gives
    the right slope, or the dividend divides evenly with no remainder), OR Task T's
    text explicitly states the step-by-step target formula.
    IMPORTANT: Defining the problem question or domain context (such as asking about
    outcomes among attendees, or stating that a plan has an unstated starting fee and
    constant hourly change when only two non-zero points like (2,9) and (6,17) are
    given) is NOT a target leak—that is the problem setup!
  * "off_target_failure": The solver using K_valid gets stuck, but only because Task T
    has missing data, contradictory/impossible numbers, or an arithmetic chore that
    does NOT expose the conceptual reason C_target is needed.
- Score 2 ("productive_trap"):
  * None of the literal prior skills in K_valid can finish or get the right winner on
    Task T without C_target; AND
  * The literal prior skills in K_valid produce concrete attempts on Task T's numbers
    that EITHER conflict with each other OR hit a built-in mathematical limitation
    (e.g., unequal y/x ratios across points because of an unstated initial value,
    overall or raw-count probabilities disagreeing with subgroup sizes, or whole-number
    division leaving an unshared remainder) for the exact conceptual reason C_target
    is needed.

Respond ONLY with valid JSON matching:
{
  "gate2_score": 1 | 2,
  "outcome": "trap_bypassed" | "off_target_failure" | "productive_trap",
  "any_k_valid_bypasses_trap": true | false,
  "task_text_leaks_target": true | false,
  "hits_productive_trap_toward_target": true | false,
  "rationale": "2-3 concise sentences explaining the Gate 2 verdict on Task T"
}"""

BRIDGE_JUDGE_SYSTEM = """\
You are an expert mathematics curriculum evaluator scoring a Productive Failure (PF)
generation attempt on a single criterion: Progression Bridge Fit (0, 1, or 2).

You are given:
1. The official curriculum progression edge:
   - Prerequisite standards (S_prior, taught before this lesson via `buildsTowards`)
     and their supporting learning components.
   - Target standard (S_target, the new concept to be invented; NOT yet taught).
   - Case-specific 0/1/2 anchor definitions.
2. The generator's Stage D1 prior-resource inventory (what the generator assumed
   students already know).
3. The generator's Stage D3 student-facing task.

Score Progression Bridge Fit on the 0 / 1 / 2 scale:
- Score 0 (Boundary Miss):
  * Stage D1 lists S_target (or its target formula/procedure) as already-taught prior
    knowledge (target leakage), OR
  * Stage D3 gives away the target formula/procedure in the student prompt, OR
  * The task fails to engage S_prior (e.g., drops to trivial arithmetic or does not
    start from the prerequisite representation/skill).
- Score 1 (Loose Topic Match):
  * No target leak in D1 or D3, and the task touches S_prior, BUT applying S_prior
    directly already solves the whole question (no mathematical impasse), or S_prior
    fails only on an unrelated wording/unit trick rather than the mathematical gap
    to S_target.
- Score 2 (Exact Progression Bridge):
  * Zero target leakage in D1 and D3;
  * Stage D1 accurately identifies S_prior prerequisite skills;
  * The student task's starting quantities directly invite S_prior as the first move; AND
  * Applying S_prior hits a built-in mathematical limitation (such as a tie, opposite
    ranking, or structural conflict) that requires inventing S_target.

Respond ONLY with valid JSON matching:
{
  "score": 0 | 1 | 2,
  "d1_target_leak": true | false,
  "d3_target_leak": true | false,
  "activates_s_prior": true | false,
  "s_prior_hits_bridge_impasse": true | false,
  "d1_quote": "short verbatim quote from D1 resources",
  "task_quote": "short verbatim quote from student task",
  "rationale": "2-3 concise sentences explaining the score against S_prior -> S_target"
}"""

PAIRWISE_JUDGE_SYSTEM = """\
You are a blinded mathematics education reviewer comparing two candidate Productive
Failure (PF) packages (Option 1 and Option 2) for the same curriculum progression bridge:
  Prerequisite Standard (S_prior) ---buildsTowards---> Target Standard (S_target)

Each option includes its Stage D1 assumed prior-knowledge list and its Stage D3
student-facing task.

Judge which option better bridges S_prior -> S_target using three criteria in order:
1. Boundary discipline: Does D1 stay strictly within S_prior without leaking S_target
   as already taught, and does D3 withhold the target formula?
2. Prerequisite activation: Does the student task directly invite the exact S_prior
   prerequisite skill as the entry move?
3. Progression impasse: Does applying S_prior hit a genuine mathematical limitation
   (tie, opposite ranking, or conflict) that motivates inventing S_target?

Respond ONLY with valid JSON matching:
{
  "winner": "option_1" | "option_2" | "tie",
  "rationale": "2-3 concise sentences comparing Option 1 and Option 2"
}"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def student_task_text(task: dict[str, Any] | None) -> str:
    if not isinstance(task, dict):
        return ""
    return "\n\n".join(
        str(task.get(k, "")).strip() for k in ("title", "body", "question") if task.get(k)
    )


def build_generation_case_input(case: dict[str, Any]) -> dict[str, Any]:
    """Common ungrounded input for both arms (no hand-written exclusions or teacher skills)."""
    return {
        "id": case["id"],
        "target_concept": case["target_concept"],
        "topic": case["topic"],
        "grade": case["grade"],
        "jurisdiction": "USA",
        "subject": case["subject"],
        "exclude_resource_terms": [],
        "teacher_skills": [],
    }


def build_lc_grounding_records(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Build official D1 grounding_evidence records from S_prior standards and components."""
    bridge = case["progression_bridge"]
    records: list[dict[str, Any]] = []
    for std in bridge["prerequisite_standards_builds_towards"]:
        code = std["statementCode"]
        records.append(
            {
                "source_url": LC_EXPORT_URL,
                "standard_id": f"std:{code}",
                "label": (
                    f"Learning Commons v1.14.0 CCSSM Prerequisite Standard {code} "
                    f"(Grade {','.join(std.get('gradeLevel') or [])}, buildsTowards target)"
                ),
                "text": std["description"],
            }
        )
    for idx, comp in enumerate(bridge["prerequisite_learning_components"][:8], start=1):
        p_code = comp.get("supports_standard_code") or "prereq"
        records.append(
            {
                "source_url": LC_EXPORT_URL,
                "standard_id": f"comp:{idx}",
                "label": (
                    f"Learning Commons v1.14.0 Learning Component #{idx} supporting {p_code} "
                    f"(Grade {','.join(comp.get('gradeLevel') or [])})"
                ),
                "text": comp["description"],
            }
        )
    return records


def build_official_learner_context(case: dict[str, Any]) -> dict[str, Any]:
    """Construct the official grade-level learner_context from S_prior for v2.9 evaluation."""
    bridge = case["progression_bridge"]
    prior_skills = [
        f"{s['statementCode']}: {s['description']}"
        for s in bridge["prerequisite_standards_builds_towards"]
    ]
    for comp in bridge["prerequisite_learning_components"][:6]:
        prior_skills.append(
            f"Component ({comp.get('supports_standard_code')}): {comp['description']}"
        )
    return {
        "grade": case["grade"],
        "subject": case["subject"],
        "jurisdiction": "USA (Common Core)",
        "assumed_prior_knowledge": prior_skills,
    }


def extract_d1_resources(gen_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only student prior-knowledge fields (excluding internal falls_short_because)."""
    d1_out = gen_result.get("stages", {}).get("D1", {}).get("output", {})
    recs = d1_out.get("recommendations", [])
    if isinstance(recs, list) and recs:
        return [
            {
                "resource": r.get("resource", ""),
                "taught_as": r.get("taught_as", ""),
                "student_move": r.get("student_move", ""),
            }
            for r in recs
            if isinstance(r, dict)
        ]
    pc = gen_result.get("prior_context", {})
    methods = pc.get("methods", [])
    if isinstance(methods, list):
        return [
            {
                "resource": m.get("resource", ""),
                "taught_as": m.get("taught_as", ""),
                "student_move": m.get("student_move", ""),
            }
            for m in methods
            if isinstance(m, dict)
        ]
    return []


def extract_student_task(gen_result: dict[str, Any]) -> str:
    d2_d3 = (gen_result.get("stages") or {}).get("D2_D3") or {}
    txt = student_task_text(d2_d3.get("task"))
    if txt:
        return txt
    d2 = (gen_result.get("stages") or {}).get("D2") or {}
    for k in ("student_task", "final_task", "task"):
        txt = student_task_text(d2.get(k) or gen_result.get(k))
        if txt:
            return txt
    return ""


def run_direct_case_worker(
    case_input: dict[str, Any],
    attempt_dir: Path,
    model_selector: str,
) -> dict[str, Any]:
    """Run one-shot Arm 1 (Direct Generation) proposing K_prior = {k1..km} and Task T."""
    attempt_dir.mkdir(parents=True, exist_ok=True)
    client, model = load_client(model_selector)
    user_payload = {
        "grade": case_input["grade"],
        "subject": case_input["subject"],
        "jurisdiction": case_input["jurisdiction"],
        "topic": case_input["topic"],
        "target_concept": case_input["target_concept"],
    }
    payload = None
    raw = ""
    for attempt in range(4):
        try:
            payload, raw = chat_json(
                client,
                model,
                DIRECT_WITH_K_PRIOR_SYSTEM,
                json.dumps(user_payload, ensure_ascii=False, indent=2),
                temperature=0.0,
                max_tokens=6000,
            )
        except Exception as exc:
            raw = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
            continue
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("proposed_prior_knowledge"), list)
            and payload.get("proposed_prior_knowledge")
            and str(payload.get("body", "")).strip()
            and str(payload.get("question", "")).strip()
        ):
            break
    if not isinstance(payload, dict) or not str(payload.get("body", "")).strip():
        res = {
            "case_id": case_input["id"],
            "arm": "direct",
            "status": "failed",
            "raw_response": raw[:1000],
        }
        save_json(attempt_dir / "result.json", res)
        return res

    recs = [
        {
            "resource": str(item.get("resource", "")).strip(),
            "taught_as": str(item.get("taught_as", "")).strip(),
            "student_move": str(item.get("student_move", "")).strip(),
        }
        for item in payload.get("proposed_prior_knowledge", [])
        if isinstance(item, dict) and str(item.get("resource", "")).strip()
    ]
    task_obj = {
        "status": "ready",
        "title": str(payload.get("title", "")).strip(),
        "body": str(payload.get("body", "")).strip(),
        "question": str(payload.get("question", "")).strip(),
    }
    res = {
        "case_id": case_input["id"],
        "arm": "direct",
        "status": "completed",
        "generated_at": now(),
        "stages": {
            "D1": {"output": {"recommendations": recs}},
            "D2": {"student_task": task_obj},
        },
    }
    save_json(attempt_dir / "stage_d1_prior_knowledge.json", {"recommendations": recs})
    save_json(attempt_dir / "stage_d3_student_task.json", task_obj)
    save_json(attempt_dir / "result.json", res)
    return res


def generate_one_job(job: tuple[dict[str, Any], str, str, str]) -> dict[str, Any]:
    case, arm, output_str, model_name = job
    output = Path(output_str)
    case_id = case["id"]
    attempt_dir = output / "generation" / arm / case_id
    result_path = attempt_dir / "result.json"
    if result_path.exists():
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed" and extract_student_task(saved):
            return {"case_id": case_id, "arm": arm, "result": saved}
    if attempt_dir.exists():
        shutil.rmtree(attempt_dir)

    case_input = build_generation_case_input(case)
    res: dict[str, Any] = {"case_id": case_id, "arm": arm, "status": "failed"}
    for attempt in range(4):
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        try:
            if arm == "direct":
                res = run_direct_case_worker(case_input, attempt_dir, model_name)
            elif arm == "ungrounded":
                res = diagnostic.run_case_worker(
                    case_id,
                    str(attempt_dir),
                    model_name,
                    2,
                    None,
                    case_override=case_input,
                    shared_context=None,
                    d1_condition="ungrounded",
                    grounding_evidence=None,
                    learning_commons=False,
                )
            elif arm == "lc_grounded":
                lc_records = build_lc_grounding_records(case)
                lc_bundle = progression_bridge_bundle(case_id)
                res = diagnostic.run_case_worker(
                    case_id,
                    str(attempt_dir),
                    model_name,
                    2,
                    None,
                    case_override=case_input,
                    shared_context={"learning_commons_progression_bridge": lc_bundle},
                    d1_condition="grounded",
                    grounding_evidence=lc_records,
                    evidence_k=len(lc_records),
                    learning_commons=False,
                )
            else:
                raise ValueError(f"Unknown arm: {arm}")
        except Exception as exc:
            res = {
                "case_id": case_id,
                "arm": arm,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
            time.sleep(2 * (attempt + 1))
            continue
        if res.get("status") == "completed" and extract_student_task(res):
            break
        time.sleep(2 * (attempt + 1))
    return {"case_id": case_id, "arm": arm, "result": res}


def evaluate_gate1_prior_set(
    client: Any,
    model: str,
    case: dict[str, Any],
    k_prior_set: list[dict[str, Any]],
    task_text: str,
) -> dict[str, Any]:
    """Gate 1: Check left-to-right validity of each k_i in K_prior = {k_1, ..., k_m}."""
    if not k_prior_set or not task_text.strip():
        return {
            "gate1_passed": False,
            "failure_reason": "empty_prior_or_task",
            "any_spoiler": False,
            "combination_is_spoiler": False,
            "total_count": len(k_prior_set),
            "valid_count": 0,
            "irrelevant_count": len(k_prior_set),
            "spoiler_count": 0,
            "valid_ratio": 0.0,
            "items": [],
            "k_valid": [],
            "set_summary": "No prior skills or task text produced.",
        }
    bridge = case["progression_bridge"]
    user_payload = {
        "case_id": case["id"],
        "grade": case["grade"],
        "topic": case["topic"],
        "target_concept": case["target_concept"],
        "exclude_prior_terms": case["exclude_prior_terms"],
        "curriculum_reference_target": {
            "code": bridge["target_standard"]["statementCode"],
            "description": bridge["target_standard"]["description"],
        },
        "curriculum_reference_direct_prereqs": [
            {"code": s["statementCode"], "description": s["description"]}
            for s in bridge["prerequisite_standards_builds_towards"]
        ],
        "curriculum_reference_prereq_components": [
            {
                "supports": c.get("supports_standard_code"),
                "description": c["description"],
            }
            for c in bridge["prerequisite_learning_components"][:8]
        ],
        "proposed_k_prior_set": [
            {"index": idx, **item} for idx, item in enumerate(k_prior_set)
        ],
        "student_task": task_text,
    }
    payload = None
    raw = ""
    for attempt in range(4):
        try:
            payload, raw = chat_json(
                client,
                model,
                GATE1_PRIOR_SET_JUDGE_SYSTEM,
                json.dumps(user_payload, ensure_ascii=False, indent=2),
                temperature=0.0,
                max_tokens=6000,
            )
        except Exception as exc:
            raw = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
            continue
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            break
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"Invalid Gate 1 response: {raw[:400]}")

    raw_items = payload["items"]
    norm_items: list[dict[str, Any]] = []
    k_valid: list[dict[str, Any]] = []
    for idx, src in enumerate(k_prior_set):
        matched = next(
            (it for it in raw_items if isinstance(it, dict) and it.get("index") == idx),
            raw_items[idx] if idx < len(raw_items) and isinstance(raw_items[idx], dict) else {},
        )
        cls = str(matched.get("classification", "irrelevant")).strip().lower()
        if cls not in {"valid", "irrelevant", "spoiler"}:
            cls = "irrelevant"
        is_spoiler = bool(matched.get("is_spoiler")) or cls == "spoiler"
        has_arrow = bool(matched.get("has_left_to_right_arrow"))
        helpful = bool(matched.get("helpful_to_start_task"))
        if is_spoiler:
            cls = "spoiler"
        elif has_arrow and helpful:
            cls = "valid"
        else:
            cls = "irrelevant"
        norm_items.append(
            {
                "index": idx,
                "resource": src.get("resource", ""),
                "classification": cls,
                "has_left_to_right_arrow": has_arrow,
                "helpful_to_start_task": helpful,
                "is_spoiler": is_spoiler,
                "reason": str(matched.get("reason", "")),
            }
        )
        if cls == "valid":
            k_valid.append(src)

    combination_is_spoiler = bool(payload.get("combination_is_spoiler"))
    spoiler_count = sum(1 for it in norm_items if it["classification"] == "spoiler")
    valid_count = len(k_valid)
    irrelevant_count = sum(1 for it in norm_items if it["classification"] == "irrelevant")
    any_spoiler = spoiler_count > 0 or combination_is_spoiler
    gate1_passed = (not any_spoiler) and (valid_count > 0)
    if any_spoiler:
        failure_reason = "spoiler_in_prior_set"
    elif valid_count == 0:
        failure_reason = "no_valid_prior_skill"
    else:
        failure_reason = "none"

    return {
        "gate1_passed": gate1_passed,
        "failure_reason": failure_reason,
        "any_spoiler": any_spoiler,
        "combination_is_spoiler": combination_is_spoiler,
        "total_count": len(k_prior_set),
        "valid_count": valid_count,
        "irrelevant_count": irrelevant_count,
        "spoiler_count": spoiler_count,
        "valid_ratio": round(valid_count / len(k_prior_set), 3),
        "items": norm_items,
        "k_valid": k_valid,
        "set_summary": str(payload.get("set_summary", "")),
    }


def evaluate_gate2_k_valid_solver(
    client: Any,
    model: str,
    case: dict[str, Any],
    k_valid: list[dict[str, Any]],
    task_text: str,
) -> dict[str, Any]:
    """Gate 2: Run the K_valid-Only Solver on Task T, then judge if it hits the trap."""
    solver_input = {
        "grade": case["grade"],
        "allowed_k_valid_skills": k_valid,
        "forbidden_target_concept": case["target_concept"],
        "forbidden_target_terms": case["exclude_prior_terms"],
        "student_task": task_text,
    }
    solver_payload = None
    raw_solver = ""
    for attempt in range(4):
        try:
            solver_payload, raw_solver = chat_json(
                client,
                model,
                GATE2_K_VALID_SOLVER_SYSTEM,
                json.dumps(solver_input, ensure_ascii=False, indent=2),
                temperature=0.0,
                max_tokens=6000,
            )
        except Exception as exc:
            raw_solver = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
            continue
        if isinstance(solver_payload, dict) and isinstance(
            solver_payload.get("skill_attempts"), list
        ):
            break
    if not isinstance(solver_payload, dict):
        raise ValueError(f"Invalid Gate 2 solver response: {raw_solver[:400]}")

    judge_input = {
        "case_id": case["id"],
        "grade": case["grade"],
        "target_concept": case["target_concept"],
        "bridge_rubric_anchor": case["bridge_rubric_anchor"],
        "k_valid_skills": k_valid,
        "student_task": task_text,
        "k_valid_solver_output": solver_payload,
    }
    judge_payload = None
    raw_judge = ""
    for attempt in range(4):
        try:
            judge_payload, raw_judge = chat_json(
                client,
                model,
                GATE2_TRAP_JUDGE_SYSTEM,
                json.dumps(judge_input, ensure_ascii=False, indent=2),
                temperature=0.0,
                max_tokens=6000,
            )
        except Exception as exc:
            raw_judge = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
            continue
        if isinstance(judge_payload, dict) and judge_payload.get("gate2_score") in {1, 2}:
            break
    if not isinstance(judge_payload, dict) or judge_payload.get("gate2_score") not in {1, 2}:
        raise ValueError(f"Invalid Gate 2 judge response: {raw_judge[:400]}")

    return {
        "gate2_score": int(judge_payload["gate2_score"]),
        "outcome": str(judge_payload.get("outcome", "")),
        "any_k_valid_bypasses_trap": bool(judge_payload.get("any_k_valid_bypasses_trap")),
        "task_text_leaks_target": bool(judge_payload.get("task_text_leaks_target")),
        "hits_productive_trap_toward_target": bool(
            judge_payload.get("hits_productive_trap_toward_target")
        ),
        "rationale": str(judge_payload.get("rationale", "")),
        "solver_trace": solver_payload,
    }


def evaluate_two_gate_arm(
    client: Any,
    model: str,
    case: dict[str, Any],
    k_prior_set: list[dict[str, Any]],
    task_text: str,
) -> dict[str, Any]:
    """Run Gate 1 (Set Validity) -> Gate 2 (K_valid-Only Solver Trap Check) for one arm."""
    gate1 = evaluate_gate1_prior_set(client, model, case, k_prior_set, task_text)
    if not gate1["gate1_passed"]:
        return {
            "score": 0,
            "outcome": f"score_0_{gate1['failure_reason']}",
            "gate1": gate1,
            "gate2": None,
        }
    gate2 = evaluate_gate2_k_valid_solver(
        client, model, case, gate1["k_valid"], task_text
    )
    score = int(gate2["gate2_score"])
    return {
        "score": score,
        "outcome": f"score_{score}_{gate2['outcome']}",
        "gate1": gate1,
        "gate2": gate2,
    }


def score_bridge_fit(
    client: Any,
    model: str,
    case: dict[str, Any],
    d1_resources: list[dict[str, Any]],
    task_text: str,
) -> dict[str, Any]:
    if not task_text.strip():
        return {
            "score": 0,
            "d1_target_leak": False,
            "d3_target_leak": False,
            "activates_s_prior": False,
            "s_prior_hits_bridge_impasse": False,
            "d1_quote": "",
            "task_quote": "",
            "rationale": "No student task was produced.",
        }
    bridge = case["progression_bridge"]
    user_payload = {
        "case_id": case["id"],
        "grade": case["grade"],
        "target_concept": case["target_concept"],
        "exclude_prior_terms": case["exclude_prior_terms"],
        "s_prior_standards_builds_towards": [
            {"code": s["statementCode"], "description": s["description"]}
            for s in bridge["prerequisite_standards_builds_towards"]
        ],
        "s_prior_learning_components": [
            {
                "supports": c.get("supports_standard_code"),
                "description": c["description"],
            }
            for c in bridge["prerequisite_learning_components"][:8]
        ],
        "s_target_standard": {
            "code": bridge["target_standard"]["statementCode"],
            "description": bridge["target_standard"]["description"],
        },
        "bridge_rubric_anchor": case["bridge_rubric_anchor"],
        "generated_d1_prior_resources": d1_resources,
        "generated_d3_student_task": task_text,
    }
    payload = None
    raw = ""
    for _ in range(3):
        payload, raw = chat_json(
            client,
            model,
            BRIDGE_JUDGE_SYSTEM,
            json.dumps(user_payload, ensure_ascii=False, indent=2),
            temperature=0.0,
            max_tokens=6000,
        )
        if isinstance(payload, dict) and payload.get("score") in {0, 1, 2}:
            break
    if not isinstance(payload, dict) or payload.get("score") not in {0, 1, 2}:
        raise ValueError(f"Invalid bridge judge response: {raw[:400]}")
    return {
        "score": int(payload["score"]),
        "d1_target_leak": bool(payload.get("d1_target_leak")),
        "d3_target_leak": bool(payload.get("d3_target_leak")),
        "activates_s_prior": bool(payload.get("activates_s_prior")),
        "s_prior_hits_bridge_impasse": bool(payload.get("s_prior_hits_bridge_impasse")),
        "d1_quote": str(payload.get("d1_quote", "")),
        "task_quote": str(payload.get("task_quote", "")),
        "rationale": str(payload.get("rationale", "")),
    }


def score_blinded_pair(
    client: Any,
    model: str,
    case: dict[str, Any],
    ungrounded_pack: dict[str, Any],
    grounded_pack: dict[str, Any],
) -> dict[str, Any]:
    """Run position-swapped blinded comparison (AB and BA) to eliminate order bias."""
    bridge = case["progression_bridge"]
    common = {
        "case_id": case["id"],
        "grade": case["grade"],
        "target_concept": case["target_concept"],
        "s_prior_standards_builds_towards": [
            {"code": s["statementCode"], "description": s["description"]}
            for s in bridge["prerequisite_standards_builds_towards"]
        ],
        "s_target_standard": {
            "code": bridge["target_standard"]["statementCode"],
            "description": bridge["target_standard"]["description"],
        },
        "bridge_rubric_anchor": case["bridge_rubric_anchor"],
    }

    def _ask(opt1: dict[str, Any], opt2: dict[str, Any]) -> dict[str, Any]:
        prompt = {
            **common,
            "option_1": opt1,
            "option_2": opt2,
        }
        payload = None
        raw = ""
        for _ in range(3):
            payload, raw = chat_json(
                client,
                model,
                PAIRWISE_JUDGE_SYSTEM,
                json.dumps(prompt, ensure_ascii=False, indent=2),
                temperature=0.0,
                max_tokens=6000,
            )
            if isinstance(payload, dict) and payload.get("winner") in {
                "option_1",
                "option_2",
                "tie",
            }:
                return payload
        raise ValueError(f"Invalid pairwise response: {raw[:400]}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_ab = pool.submit(_ask, ungrounded_pack, grounded_pack)
        f_ba = pool.submit(_ask, grounded_pack, ungrounded_pack)
        ab = f_ab.result()
        ba = f_ba.result()

    def _map_ab(w: str) -> str:
        return {"option_1": "ungrounded", "option_2": "lc_grounded", "tie": "tie"}[w]

    def _map_ba(w: str) -> str:
        return {"option_1": "lc_grounded", "option_2": "ungrounded", "tie": "tie"}[w]

    v_ab = _map_ab(ab["winner"])
    v_ba = _map_ba(ba["winner"])
    if v_ab == v_ba:
        consensus = v_ab
    elif "tie" in {v_ab, v_ba}:
        consensus = v_ab if v_ba == "tie" else v_ba
    else:
        consensus = "tie"
    return {
        "consensus_winner": consensus,
        "order_ab_winner": v_ab,
        "order_ba_winner": v_ba,
        "order_ab_rationale": str(ab.get("rationale", "")),
        "order_ba_rationale": str(ba.get("rationale", "")),
    }


def evaluate_case_pair(
    case: dict[str, Any],
    gen_ungrounded: dict[str, Any],
    gen_grounded: dict[str, Any],
    output: Path,
    judge_model_selector: str = "luna",
    run_v29: bool = True,
    rejudge_bridge_only: bool = False,
) -> dict[str, Any]:
    case_id = case["id"]
    eval_path = output / "evaluations" / f"{case_id}.json"
    saved_eval = None
    if eval_path.exists():
        saved_eval = json.loads(eval_path.read_text(encoding="utf-8"))
        if not rejudge_bridge_only:
            return saved_eval

    client, model = load_client(judge_model_selector)
    need_v29 = run_v29 and not rejudge_bridge_only
    chats = build_chats() if need_v29 else {}
    learner_context = build_official_learner_context(case)

    u_d1 = extract_d1_resources(gen_ungrounded)
    u_task = extract_student_task(gen_ungrounded)
    g_d1 = extract_d1_resources(gen_grounded)
    g_task = extract_student_task(gen_grounded)

    with ThreadPoolExecutor(max_workers=5) as pool:
        f_u_bridge = pool.submit(score_bridge_fit, client, model, case, u_d1, u_task)
        f_g_bridge = pool.submit(score_bridge_fit, client, model, case, g_d1, g_task)
        f_pair = pool.submit(
            score_blinded_pair,
            client,
            model,
            case,
            {"d1_prior_resources": u_d1, "d3_student_task": u_task},
            {"d1_prior_resources": g_d1, "d3_student_task": g_task},
        )
        f_u_v29 = (
            pool.submit(
                v29.evaluate_v29,
                u_task,
                case["target_concept"],
                copy.deepcopy(learner_context),
                solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
                judge_chat=chats["luna"],
            )
            if (need_v29 and u_task.strip())
            else None
        )
        f_g_v29 = (
            pool.submit(
                v29.evaluate_v29,
                g_task,
                case["target_concept"],
                copy.deepcopy(learner_context),
                solver_chats={"luna": chats["luna"], "gpt41": chats["gpt41"]},
                judge_chat=chats["luna"],
            )
            if (need_v29 and g_task.strip())
            else None
        )

        u_bridge = f_u_bridge.result()
        g_bridge = f_g_bridge.result()
        pairwise = f_pair.result()
        u_v29 = (
            f_u_v29.result()
            if f_u_v29 is not None
            else (saved_eval["ungrounded"].get("v29") if saved_eval else None)
        )
        g_v29 = (
            f_g_v29.result()
            if f_g_v29 is not None
            else (saved_eval["lc_grounded"].get("v29") if saved_eval else None)
        )

    record = {
        "case_id": case_id,
        "grade": case["grade"],
        "target_code": case["progression_bridge"]["target_standard"]["statementCode"],
        "prereq_codes": [
            s["statementCode"]
            for s in case["progression_bridge"]["prerequisite_standards_builds_towards"]
        ],
        "evaluated_at": now(),
        "ungrounded": {
            "d1_resources": u_d1,
            "student_task": u_task,
            "bridge_fit": u_bridge,
            "v29": u_v29,
        },
        "lc_grounded": {
            "d1_resources": g_d1,
            "student_task": g_task,
            "bridge_fit": g_bridge,
            "v29": g_v29,
        },
        "pairwise": pairwise,
    }
    save_json(eval_path, record)
    return record


def summarize_study(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "n_cases": len(records),
        "arms": {},
        "pairwise_wins": dict(Counter(r["pairwise"]["consensus_winner"] for r in records)),
    }
    for arm in ARMS:
        scores = [r[arm]["bridge_fit"]["score"] for r in records]
        score_dist = dict(Counter(scores))
        d1_leaks = sum(1 for r in records if r[arm]["bridge_fit"]["d1_target_leak"])
        d3_leaks = sum(1 for r in records if r[arm]["bridge_fit"]["d3_target_leak"])
        activates = sum(1 for r in records if r[arm]["bridge_fit"]["activates_s_prior"])
        impasse = sum(
            1 for r in records if r[arm]["bridge_fit"]["s_prior_hits_bridge_impasse"]
        )
        v29_counts = {m: Counter() for m in MEASURES}
        v29_all5 = 0
        v29_evaluated = 0
        for r in records:
            v = r[arm].get("v29")
            if isinstance(v, dict) and "measures" in v:
                v29_evaluated += 1
                ms = v["measures"]
                for m in MEASURES:
                    val = ms[m]["value"]
                    v29_counts[m][str(val) if val is not None else ms[m]["status"]] += 1
                if all(ms[m]["value"] == "yes" for m in MEASURES):
                    v29_all5 += 1
        summary["arms"][arm] = {
            "tasks_produced": sum(1 for r in records if r[arm]["student_task"].strip()),
            "bridge_fit_mean": round(sum(scores) / len(scores), 3) if scores else 0.0,
            "bridge_fit_score_counts": {
                "score_2_exact_bridge": score_dist.get(2, 0),
                "score_1_loose_match": score_dist.get(1, 0),
                "score_0_boundary_miss": score_dist.get(0, 0),
            },
            "d1_target_leak_count": d1_leaks,
            "d3_target_leak_count": d3_leaks,
            "activates_s_prior_count": activates,
            "s_prior_hits_bridge_impasse_count": impasse,
            "v29_evaluated": v29_evaluated,
            "v29_all_5_yes": v29_all5,
            "v29_measures": {m: dict(v29_counts[m]) for m in MEASURES},
        }
    return summary


def evaluate_case_three_arms(
    case: dict[str, Any],
    gen_by_arm: dict[str, dict[str, Any]],
    output: Path,
    judge_model_selector: str = "luna",
    rejudge: bool = False,
) -> dict[str, Any]:
    """Evaluate all 3 arms (direct, ungrounded, lc_grounded) with Gate 1 + Gate 2."""
    case_id = case["id"]
    eval_path = output / "evaluations_three_arm" / f"{case_id}.json"
    if eval_path.exists() and not rejudge:
        return json.loads(eval_path.read_text(encoding="utf-8"))

    client, model = load_client(judge_model_selector)
    arm_packs: dict[str, tuple[list[dict[str, Any]], str]] = {}
    for arm in THREE_ARMS:
        gen = gen_by_arm[arm]
        arm_packs[arm] = (extract_d1_resources(gen), extract_student_task(gen))

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {
            arm: pool.submit(
                evaluate_two_gate_arm,
                client,
                model,
                case,
                arm_packs[arm][0],
                arm_packs[arm][1],
            )
            for arm in THREE_ARMS
        }
        arm_evals = {arm: futs[arm].result() for arm in THREE_ARMS}

    record: dict[str, Any] = {
        "case_id": case_id,
        "grade": case["grade"],
        "target_code": case["progression_bridge"]["target_standard"]["statementCode"],
        "prereq_codes": [
            s["statementCode"]
            for s in case["progression_bridge"]["prerequisite_standards_builds_towards"]
        ],
        "evaluated_at": now(),
    }
    for arm in THREE_ARMS:
        record[arm] = {
            "k_prior_set": arm_packs[arm][0],
            "student_task": arm_packs[arm][1],
            "two_gate": arm_evals[arm],
        }
    save_json(eval_path, record)
    return record


def summarize_three_arm_study(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"n_cases": len(records), "arms": {}}
    for arm in THREE_ARMS:
        scores = [r[arm]["two_gate"]["score"] for r in records]
        dist = Counter(scores)
        gate1_pass = sum(
            1 for r in records if r[arm]["two_gate"]["gate1"]["gate1_passed"]
        )
        spoiler_sets = sum(
            1 for r in records if r[arm]["two_gate"]["gate1"]["any_spoiler"]
        )
        valid_ratios = [r[arm]["two_gate"]["gate1"]["valid_ratio"] for r in records]
        total_k = sum(r[arm]["two_gate"]["gate1"]["total_count"] for r in records)
        valid_k = sum(r[arm]["two_gate"]["gate1"]["valid_count"] for r in records)
        irrel_k = sum(r[arm]["two_gate"]["gate1"]["irrelevant_count"] for r in records)
        spoil_k = sum(r[arm]["two_gate"]["gate1"]["spoiler_count"] for r in records)
        summary["arms"][arm] = {
            "tasks_produced": sum(
                1 for r in records if r[arm]["student_task"].strip()
            ),
            "two_gate_score_mean": (
                round(sum(scores) / len(scores), 3) if scores else 0.0
            ),
            "score_counts": {
                "score_2_productive_trap": dist.get(2, 0),
                "score_1_trap_bypassed_or_off_target": dist.get(1, 0),
                "score_0_invalid_prior_set": dist.get(0, 0),
            },
            "gate1_valid_set_count": gate1_pass,
            "gate1_spoiler_set_count": spoiler_sets,
            "mean_valid_skill_ratio": (
                round(sum(valid_ratios) / len(valid_ratios), 3)
                if valid_ratios
                else 0.0
            ),
            "item_totals": {
                "total_proposed_skills": total_k,
                "valid_skills": valid_k,
                "irrelevant_skills": irrel_k,
                "spoiler_skills": spoil_k,
            },
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", nargs="*", default=None)
    parser.add_argument("--model", default="luna")
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--three-arms", action="store_true")
    parser.add_argument("--skip-v29", action="store_true")
    parser.add_argument("--rejudge-bridge-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dataset = load_progression_bridge_dataset(args.dataset)
    cases = dataset["cases"]
    if args.cases:
        wanted = set(args.cases)
        cases = [c for c in cases if c["id"] in wanted]

    active_arms = THREE_ARMS if args.three_arms else ARMS

    if args.dry_run:
        for c in cases:
            recs = build_lc_grounding_records(c)
            bundle = progression_bridge_bundle(c["id"], dataset_path=args.dataset)
            print(
                f"{c['id']}: grade={c['grade']} lc_d1_records={len(recs)} "
                f"prereq_stds={len(bundle['prerequisite_standards_builds_towards'])}"
            )
        print(
            f"Dry run complete: {len(cases)} cases x {len(active_arms)} arms "
            f"= {len(cases) * len(active_arms)} generations."
        )
        return

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    gen_jobs = [
        (case, arm, str(output), args.model)
        for case in cases
        for arm in active_arms
    ]
    gen_by_case_arm: dict[tuple[str, str], dict[str, Any]] = {}
    print(f"Starting {len(gen_jobs)} generations across {args.max_workers} processes...")
    with ProcessPoolExecutor(max_workers=args.max_workers) as pool:
        futs = {pool.submit(generate_one_job, job): (job[0]["id"], job[1]) for job in gen_jobs}
        for fut in as_completed(futs):
            cid, arm = futs[fut]
            res = fut.result()
            gen_by_case_arm[(cid, arm)] = res["result"]
            task_ok = bool(extract_student_task(res["result"]))
            print(
                f"[GEN DONE] {cid} ({arm}) -> status={res['result'].get('status')} "
                f"task={task_ok}",
                flush=True,
            )

    if args.three_arms:
        print(f"Starting 3-arm Gate 1 + Gate 2 evaluations for {len(cases)} cases...")
        eval_records_3: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(args.max_workers, 4)) as pool:
            futs = {
                pool.submit(
                    evaluate_case_three_arms,
                    case,
                    {arm: gen_by_case_arm[(case["id"], arm)] for arm in THREE_ARMS},
                    output,
                    args.model,
                    args.rejudge_bridge_only,
                ): case["id"]
                for case in cases
            }
            for fut in as_completed(futs):
                cid = futs[fut]
                rec = fut.result()
                eval_records_3.append(rec)
                d_s = rec["direct"]["two_gate"]["score"]
                u_s = rec["ungrounded"]["two_gate"]["score"]
                g_s = rec["lc_grounded"]["two_gate"]["score"]
                print(
                    f"[3-ARM EVAL DONE] {cid}: direct={d_s} ungrounded={u_s} lc_grounded={g_s}",
                    flush=True,
                )
        order = {c["id"]: i for i, c in enumerate(cases)}
        eval_records_3.sort(key=lambda r: order[r["case_id"]])
        three_arm_summary = {
            "generated_at": now(),
            "dataset_path": str(args.dataset),
            "model_selector": args.model,
            "summary": summarize_three_arm_study(eval_records_3),
            "per_case": [
                {
                    "case_id": r["case_id"],
                    "grade": r["grade"],
                    "target_code": r["target_code"],
                    "prereq_codes": r["prereq_codes"],
                    "direct_score": r["direct"]["two_gate"]["score"],
                    "direct_outcome": r["direct"]["two_gate"]["outcome"],
                    "direct_valid_ratio": r["direct"]["two_gate"]["gate1"]["valid_ratio"],
                    "ungrounded_score": r["ungrounded"]["two_gate"]["score"],
                    "ungrounded_outcome": r["ungrounded"]["two_gate"]["outcome"],
                    "ungrounded_valid_ratio": r["ungrounded"]["two_gate"]["gate1"]["valid_ratio"],
                    "lc_grounded_score": r["lc_grounded"]["two_gate"]["score"],
                    "lc_grounded_outcome": r["lc_grounded"]["two_gate"]["outcome"],
                    "lc_grounded_valid_ratio": r["lc_grounded"]["two_gate"]["gate1"]["valid_ratio"],
                }
                for r in eval_records_3
            ],
        }
        save_json(output / "summary_three_arm.json", three_arm_summary)
        print(json.dumps(three_arm_summary["summary"], indent=2))
        return

    print(f"Starting evaluations for {len(cases)} case pairs...")
    eval_records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.max_workers, 4)) as pool:
        futs = {
            pool.submit(
                evaluate_case_pair,
                case,
                gen_by_case_arm[(case["id"], "ungrounded")],
                gen_by_case_arm[(case["id"], "lc_grounded")],
                output,
                args.model,
                not args.skip_v29,
                args.rejudge_bridge_only,
            ): case["id"]
            for case in cases
        }
        for fut in as_completed(futs):
            cid = futs[fut]
            rec = fut.result()
            eval_records.append(rec)
            u_s = rec["ungrounded"]["bridge_fit"]["score"]
            g_s = rec["lc_grounded"]["bridge_fit"]["score"]
            w = rec["pairwise"]["consensus_winner"]
            print(
                f"[EVAL DONE] {cid}: ungrounded={u_s} lc_grounded={g_s} winner={w}",
                flush=True,
            )

    order = {c["id"]: i for i, c in enumerate(cases)}
    eval_records.sort(key=lambda r: order[r["case_id"]])
    study_summary = {
        "generated_at": now(),
        "dataset_path": str(args.dataset),
        "model_selector": args.model,
        "summary": summarize_study(eval_records),
        "per_case": [
            {
                "case_id": r["case_id"],
                "grade": r["grade"],
                "target_code": r["target_code"],
                "prereq_codes": r["prereq_codes"],
                "ungrounded_bridge_score": r["ungrounded"]["bridge_fit"]["score"],
                "lc_grounded_bridge_score": r["lc_grounded"]["bridge_fit"]["score"],
                "ungrounded_d1_leak": r["ungrounded"]["bridge_fit"]["d1_target_leak"],
                "lc_grounded_d1_leak": r["lc_grounded"]["bridge_fit"]["d1_target_leak"],
                "pairwise_winner": r["pairwise"]["consensus_winner"],
                "ungrounded_v29_all5": (
                    all(
                        r["ungrounded"]["v29"]["measures"][m]["value"] == "yes"
                        for m in MEASURES
                    )
                    if isinstance(r["ungrounded"].get("v29"), dict)
                    else None
                ),
                "lc_grounded_v29_all5": (
                    all(
                        r["lc_grounded"]["v29"]["measures"][m]["value"] == "yes"
                        for m in MEASURES
                    )
                    if isinstance(r["lc_grounded"].get("v29"), dict)
                    else None
                ),
            }
            for r in eval_records
        ],
    }
    save_json(output / "summary.json", study_summary)
    print(json.dumps(study_summary["summary"], indent=2))


if __name__ == "__main__":
    main()
