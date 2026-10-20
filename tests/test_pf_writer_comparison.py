import json

import pytest

from scripts.render_pf_writer_comparison import (
    render_body,
    render_comparison,
    task_panel,
    word_count,
)


def test_word_count_excludes_markdown_separators_but_keeps_values():
    task = {"title": "Compare", "body": "| 9.8 | 20 |\n|---|---|", "question": "Explain why."}
    assert word_count(task) == 5


def test_render_body_preserves_data_and_escapes_html():
    text = "| A | B |\n|---|---|\n| 2 | 8 |\n\nExplain <why>."
    rendered = render_body(text)
    assert "<th>A</th>" in rendered
    assert "<td>8</td>" in rendered
    assert "Explain &lt;why&gt;." in rendered
    assert "<why>" not in rendered


def test_task_panel_displays_draft_and_escapes_unresolved_findings(tmp_path):
    task = {
        "status": "ready",
        "title": "Explore",
        "body": "Given data.",
        "question": "Explain.",
        "quality_status": "review_needed",
        "quality_findings": ["Unverified <condition>"],
    }
    rendered = task_panel(task, "Draft", tmp_path / "result.json")
    assert "Given data." in rendered
    assert "Draft produced with unresolved findings" in rendered
    assert "Unverified &lt;condition&gt;" in rendered
    assert "<condition>" not in rendered


@pytest.mark.parametrize("status", ["ready", "blocked"])
def test_comparison_reads_exact_saved_outputs_and_reports_blocked(tmp_path, status):
    old = {
        "status": "ready",
        "title": "Original",
        "body": "A: 2, 2, 8, 8",
        "question": "Show why.",
        "blocking_issues": [],
    }
    new = {**old, "title": "Rewritten", "status": status, "blocking_issues": ["Missing unit"]}
    (tmp_path / "old.json").write_text(json.dumps({"stages": {"D2_D3": {"task": old}}}))
    (tmp_path / "new.json").write_text(json.dumps({"task": new}))
    audit = {
        "cases": [
            {
                "topic": "Comparison",
                "source_result": "old.json",
                "replay_result": "new.json",
                "inspection": {
                    "change": "Shorter.",
                    "fidelity": "Data kept.",
                    "limitation": "Untested.",
                },
            }
        ]
    }
    rendered = render_comparison(audit, root=tmp_path)
    assert "Original" in rendered
    assert "A: 2, 2, 8, 8" in rendered
    if status == "ready":
        assert "Rewritten" in rendered
    else:
        assert "Writer blocked" in rendered
        assert "Blocked: Missing unit" in rendered
        assert "Rewritten" not in rendered
