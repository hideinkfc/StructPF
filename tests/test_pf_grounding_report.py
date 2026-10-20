import pytest

from scripts.report_pf_grounding_study import PROPERTIES, render, summarize


def fixture():
    catalog, rows = [], []
    for case in ("one", "two"):
        for arm in ("A", "B", "C"):
            task_id = f"{case}-{arm}"
            outcome = arm != "A"
            catalog.append(
                {
                    "task_id": task_id,
                    "case_id": case,
                    "repeat": 1,
                    "arm": arm,
                    "produced": True,
                    "task": {"title": "t", "body": "b", "question": "q"},
                }
            )
            rows.append(
                {
                    "task_id": task_id,
                    "fixed_checklist_value": outcome,
                    "availability": "available",
                    "availability_reason": None,
                    "consensus_values": {prop: outcome for prop in PROPERTIES},
                    "property_availability": {prop: "available" for prop in PROPERTIES},
                    "property_failure_reasons": {},
                }
            )
    return catalog, {"rows": rows, "execution": {}, "analysis_version": "test"}


def test_report_joins_task_id_to_canonical_case_not_audit_case():
    catalog, audits = fixture()
    for row in audits["rows"]:
        row["case"] = None
    summary = summarize(catalog, audits)
    assert summary["delivered"] == {"A": 2, "B": 2, "C": 2}
    assert summary["rates"]["fixed_checklist"]["B"]["supported"] == 2
    primary = summary["comparisons"]["fixed_checklist"]["curriculum_vs_none"]
    assert primary["task_specifications"] == 2
    assert primary["equal_case_weighted_supported_rate_difference"] == 1


def test_report_preserves_unknown_and_escapes_links():
    catalog, audits = fixture()
    audits["rows"][0]["fixed_checklist_value"] = None
    summary = summarize(catalog, audits)
    assert summary["rates"]["fixed_checklist"]["A"]["unknown"] == 1
    page = render(summary, 'a" onclick="bad', "audit.html")
    assert 'href="a&quot; onclick=&quot;bad"' in page
    assert "Unknowns are not failures." in page


def test_missing_duplicate_or_unrecognized_arm_is_explicit_error():
    catalog, audits = fixture()
    with pytest.raises(ValueError, match="exactly one"):
        summarize(catalog, {**audits, "rows": audits["rows"][:-1]})
    with pytest.raises(ValueError, match="unique"):
        summarize(catalog, {**audits, "rows": audits["rows"] + audits["rows"][:1]})
    catalog[0]["arm"] = "other"
    with pytest.raises(ValueError, match="Unknown arm"):
        summarize(catalog, audits)
