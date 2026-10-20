import json
import re
from pathlib import Path

from src.evaluation import pf_rubric, pf_rubric_v2_1


def _anchors(system):
    return [
        line.strip()
        for line in system.splitlines()
        if line.strip().startswith(("1 (Low):", "2 (Moderate):", "3 (High):"))
    ]


def test_v2_1_preserves_every_anchor_and_discloses_task_level_adaptation():
    v1 = pf_rubric.load_prompt()
    v2_1 = pf_rubric_v2_1.load_prompt()
    assert v2_1["version"] == "rahimi-table1/v2.1"
    assert "v2 operational interpretation" in v2_1["source"]
    assert "not verbatim wording from the paper" in v2_1["source"]
    assert _anchors(v2_1["system"]) == _anchors(v1["system"])
    assert len(_anchors(v2_1["system"])) == 15


def test_mr_and_oe_clarify_without_requiring_a_new_gate():
    system = re.sub(r"\s+", " ", pf_rubric_v2_1.load_prompt()["system"])
    assert "Keep both parts of the anchor in view" in system
    assert "can count as a different representation" in system
    assert "is not by itself a different solution method" in system
    assert "Judge the overall breadth and relevance of both aspects" in system
    assert "Use the anchor's stated complexity and integration" in system
    assert "are not an extra requirement for a high score" in system
    assert "A task with a determinate answer may still be highly complex" in system
    assert "Do not infer or favor a generation method" in system


def test_v2_1_rating_input_drops_teacher_trace_and_method_labels():
    text = pf_rubric_v2_1.student_task_text({
        "status": "ready",
        "title": "Compare two groups",
        "body": "Their scores are listed.",
        "question": "What can you conclude?",
        "condition": "PIPELINE",
        "teacher_trace": "SECRET_TRACE",
        "teacher_label": "SECRET_LABEL",
        "review_result": "SECRET_REVIEW",
    })
    user = pf_rubric_v2_1.judge_input(
        text,
        {
            "grade": 7,
            "subject": "mathematics",
            "jurisdiction": "USA",
            "assumed_prior_knowledge": [{
                "resource": "Unit rates",
                "taught_as": "Compute rates.",
                "teacher_trace": "SECRET_CONTEXT_TRACE",
            }],
            "condition": "V1",
            "teacher_trace": "SECRET_CONTEXT_TRACE",
            "teacher_label": "SECRET_CONTEXT_LABEL",
        },
        "Recognize proportional relationships.",
    )
    assert "SECRET" not in user
    assert "PIPELINE" not in user
    assert "V1" not in user
    payload = json.loads(user)
    assert set(payload) == {"learner_context", "student_task"}


def test_v4_frozen_direct_and_pipeline_prompts_both_include_all_anchors():
    root = Path(__file__).resolve().parents[1]
    source = root / "experiments/results/pf_paper_benchmark/20260923_luna_v4"
    manifest = json.loads((source / "manifest.json").read_text())
    snapshot = source / manifest["source_snapshot_dir"]
    direct = snapshot / "src/generation/prompts/pf_paper_benchmark.yaml"
    pipeline = snapshot / "src/generation/prompts/situation_skeletons.yaml"
    assert all(anchor in direct.read_text() for anchor in _anchors(
        pf_rubric.load_prompt()["system"]
    ))
    assert all(anchor in pipeline.read_text() for anchor in _anchors(
        pf_rubric.load_prompt()["system"]
    ))
