import pytest

from src.evaluation.mcq_metrics import MCQEvaluator


def test_pm_is_case_insensitive_and_one_to_one():
    evaluator = MCQEvaluator.__new__(MCQEvaluator)

    assert evaluator.compute_pm(
        ["protractor", "Ruler", "Set square"],
        ["Callipers", "Protractor", "Slide rule"],
    ) == pytest.approx(1 / 3)
    assert evaluator.compute_pm(
        ["Protractor", "Protractor", "Protractor"],
        ["Callipers", "Protractor", "Slide rule"],
    ) == pytest.approx(1 / 3)
