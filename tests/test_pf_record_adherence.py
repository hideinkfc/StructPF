import pytest

from scripts import report_pf_learning_record as report
from src.evaluation.pf_record_adherence import FLAGS, parse_coding


def packet():
    return {"a1": {"attempt": {
        "written_work": "Mean = (2 + 4) / 2 = 3.", "answer": "3", "unfinished": False,
    }, "unparsed_raw_text": None}}


def coding():
    row = {
        **{flag: "no" for flag in FLAGS},
        "evidence": {flag: [] for flag in FLAGS},
        "mathematics_status": "supported", "rationale": "A mean was calculated.",
    }
    row["prerequisite_applied"] = "yes"
    row["evidence"]["prerequisite_applied"] = ["Mean = (2 + 4) / 2 = 3."]
    return {"provenance": "Illustrative software test.", "attempts": {"a1": row}}


def test_actual_use_requires_source_quote_and_mention_only_is_separate():
    payload = coding()
    assert parse_coding(payload, packet()) == payload
    payload["attempts"]["a1"]["prerequisite_mentioned_only"] = "yes"
    with pytest.raises(ValueError, match="cannot both be positive"):
        parse_coding(payload, packet())
    payload = coding()
    payload["attempts"]["a1"]["evidence"]["prerequisite_applied"] = ["Invented quotation."]
    with pytest.raises(ValueError, match="does not match"):
        parse_coding(payload, packet())


def test_unknown_is_kept_in_all_attempt_denominators():
    first = coding()["attempts"]["a1"]
    second = {**first, "prerequisite_applied": "unknown"}
    counts = report.counts({"a1": first, "a2": second})
    assert counts["attempted"] == 2
    assert counts["prerequisite_applied/yes"] == 1
    assert counts["prerequisite_applied/unknown"] == 1
    missing = coding()
    missing["attempts"] = {}
    with pytest.raises(ValueError, match="every attempted response"):
        parse_coding(missing, packet())


def test_partial_work_can_have_unknown_resource_use_without_a_false_negative():
    partial = {"a1": {"attempt": None, "unparsed_raw_text": "I would compare"}}
    row = {
        **{flag: "unknown" for flag in FLAGS},
        "evidence": {flag: [] for flag in FLAGS},
        "mathematics_status": "unknown", "rationale": "The response is cut off.",
    }
    payload = {"provenance": "Illustrative incomplete output.", "attempts": {"a1": row}}
    assert parse_coding(payload, partial) == payload
    row["advanced_applied"] = "yes"
    with pytest.raises(ValueError, match="quoted evidence"):
        parse_coding(payload, partial)


def test_render_displays_actual_use_not_keywords_and_keeps_unknown(tmp_path):
    groups = {}
    for family in ("loibl_variance", "kerrigan_fair_division"):
        for profile in report.PROFILES:
            groups[f"{family}/{profile}"] = {
                "attempted": 12, "advanced_applied/yes": 2,
                "advanced_applied/unknown": 1, "advanced_mentioned_only/yes": 4,
            }
    summary = {
        "attempts": {}, "family_groups": groups,
        "execution": {"fresh": {"attempted": 96, "parsed": 94}},
    }
    report.render(tmp_path, summary)
    page = (tmp_path / "learning_record.html").read_text()
    assert "2/12 (1 unknown)" in page
    assert "merely mention the name" in page
    assert "2/12; 1 unknown" in page


def test_recall_label_cannot_stand_in_for_applying_a_method():
    payload = coding()
    payload["attempts"]["a1"]["advanced_named_as_recall"] = "yes"
    with pytest.raises(ValueError, match="requires actual advanced"):
        parse_coding(payload, packet())
