import json
from pathlib import Path

import pytest

from src.evaluation import pf_rubric, pf_rubric_setting

CONFIG = Path("experiments/configs/pf_rahimi_multi_theme_setting.json")


def _anchors(system):
    return [
        line.strip()
        for line in system.splitlines()
        if line.strip().startswith(("1 (Low):", "2 (Moderate):", "3 (High):"))
    ]


def test_setting_prompt_keeps_every_table1_anchor_verbatim():
    v1 = pf_rubric.load_prompt()
    setting = pf_rubric_setting.load_prompt()
    assert setting["version"] == "rahimi-table1/v1-setting"
    assert "not verbatim wording from the paper" in setting["source"]
    assert _anchors(setting["system"]) == _anchors(v1["system"])
    assert len(_anchors(setting["system"])) == 15
    assert "task_setting" in setting["system"]


def test_judge_input_has_setting_but_no_model_examples_or_generation_rules():
    case = {
        "id": "SECRET_CELL_ID",
        "target_concept": "Compare two data distributions (7.SP.B.4). Not yet taught.",
        "teacher_recently_taught": ["SECRET_TEACHER_LIST"],
        "benchmark_context": {
            "theme": "music",
            "interest": "bands and playlists",
            "setting_rule": "SECRET_SETTING_RULE",
            "prior_knowledge_boundary": "SECRET_BOUNDARY",
            "task_rule": "SECRET_TASK_RULE",
        },
        "generator_model": "SECRET_MODEL",
    }
    context = {
        "grade": 7,
        "subject": "mathematics",
        "jurisdiction": "USA",
        "assumed_prior_knowledge": [
            {
                "resource": "Mean",
                "taught_as": "Compute a mean.",
                "student_move": "SECRET_MOVE",
            }
        ],
    }
    text = pf_rubric_setting.student_task_text(
        {
            "status": "ready",
            "title": "T",
            "body": "B",
            "question": "Q",
            "consolidation": "SECRET_SOLUTION",
        }
    )
    result = json.loads(pf_rubric_setting.judge_input(text, case, context))
    assert list(result) == ["task_setting", "learner_context", "student_task"]
    assert result["task_setting"] == {
        "intended_use": pf_rubric_setting.INTENDED_USE,
        "learning_target": case["target_concept"],
        "theme": "music",
        "student_interest": "bands and playlists",
    }
    assert "SECRET" not in json.dumps(result)
    assert result["student_task"] == "T\n\nB\n\nQ"


def test_missing_setting_field_fails_loudly():
    with pytest.raises(ValueError):
        pf_rubric_setting.task_setting({"target_concept": "X", "benchmark_context": {"theme": "t"}})


def test_every_configured_cell_builds_a_judge_input():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for cell in config["cells"]:
        raw = pf_rubric_setting.judge_input("Task.", cell["case"], cell["learner_context"])
        result = json.loads(raw)
        assert result["task_setting"]["learning_target"] == cell["case"]["target_concept"]
        assert cell["cell_id"] not in json.dumps(result)
