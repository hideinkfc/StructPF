import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.run_basic_glm_correctness_pilot as pilot
from scripts.run_basic_glm_correctness_pilot import (
    classify_correctness,
    compute_pm,
    evaluate_coherence,
    evaluate_derivation,
)


def test_numeric_equivalence_uses_shared_normalization():
    assert classify_correctness("5 x 24", r"5 \times 24", "What is the value?")[0] == "correct"
    assert classify_correctness("0.5", "1/2", "What is the value?")[0] == "correct"
    assert classify_correctness("19/5", r"3 \frac{4}{5}", "What is the value?")[0] == "correct"


def test_numeric_expressions_support_implicit_multiplication():
    assert classify_correctness("3 * 5 + 2", "3(5+2)", "What is the value?")[0] == "incorrect"
    assert classify_correctness("3(5 - 2)", "3(5+2)", "What is the value?")[0] == "incorrect"


def test_simple_equation_reversal_is_equivalent():
    assert classify_correctness("x=0", "0=x", "What is the equation?")[0] == "correct"
    assert classify_correctness("x=1", "x=0", "What is the equation?")[0] == "incorrect"
    assert classify_correctness("y=0", "x=0", "What is the equation?")[0] == "incorrect"
    assert classify_correctness("y=x", "x=0", "What is the equation?")[0] == "unknown"


def test_method_questions_do_not_collapse_expression_to_value():
    result = classify_correctness(
        "840",
        "5 x 7 x 24",
        "Which calculation gives the hours in 5 weeks?",
    )
    assert result[0] == "unknown"


def test_unsupported_symbolic_equivalence_is_unknown():
    result = classify_correctness("x=2", "x^2=4", "Solve the equation")
    assert result[0] == "unknown"


def test_derivation_checks_calculation_against_predicted_answer():
    distractor = {
        "text": "3 x 5 + 2",
        "student_calculation": "3 * 5 + 2",
        "predicted_answer": "17",
    }
    assert evaluate_derivation(distractor, "21", "What is the value?")[0] == "pass"

    distractor["predicted_answer"] = "18"
    assert evaluate_derivation(distractor, "21", "What is the value?")[0] == "fail"


def test_pm_uses_one_to_one_matching():
    question = {
        "QuestionId": 1,
        "CorrectAnswer": "D",
        "AnswerAText": "1/2",
        "AnswerBText": "2/3",
        "AnswerCText": "3/4",
        "AnswerDText": "1",
    }
    record = {
        "question_id": 1,
        "distractors": [{"text": "0.5"}, {"text": "0.5"}],
    }
    result = compute_pm(record, question)
    assert result["pm_typed"] == 0.5


def test_plausibility_and_diversity_use_cached_judge_results(monkeypatch):
    record = {
        "question_id": 1,
        "subject": "test",
        "question_text": "What is the value?",
        "correct_answer": "21",
        "parse_error": "",
        "distractors": [
            {"text": "17", "student_calculation": "3*5+2", "predicted_answer": "17"},
            {"text": "9", "student_calculation": "3*(5-2)", "predicted_answer": "9"},
            {"text": "12", "student_calculation": "(5+2)+5", "predicted_answer": "12"},
        ],
    }

    def fake_judge(prompt, client=None, model=None):
        if "same underlying error type" in prompt:
            return {"same_error": False, "shared_faulty_step": "", "reason": "different"}, True
        return {"score": 2, "reason": "recognizable student error"}, True

    monkeypatch.setattr(pilot, "cached_judge_json", fake_judge)
    _, plausibility = pilot.evaluate_plausibility([record], repeats=1)
    assert plausibility["plausible"].tolist() == [True, True, True]

    diversity, summary = pilot.evaluate_diversity(
        [record], plausibility, repeats=1, use_derivation=True
    )
    assert diversity.loc[0, "diversity"] == 1.0
    assert summary.loc[0, "questions_measured"] == 1


def test_coherence_judge_and_missing_path(monkeypatch):
    record = {
        "question_id": 1,
        "question_text": "What is the value?",
        "correct_answer": "21",
        "distractors": [
            {"text": "17", "faulty_step": "wrong order", "reasoning_steps": ["3 * 5 + 2"]},
            {"text": "9"},
        ],
    }

    def fake_judge(prompt, client=None, model=None):
        return {"coherent": True, "breaks_at_step": None, "reason": "steps end at text"}, True

    monkeypatch.setattr(pilot, "cached_judge_json", fake_judge)
    details, summary = evaluate_coherence([record])
    assert details.loc[0, "status"] == "pass"
    assert details.loc[1, "status"] == "unknown"
    assert summary.loc[0, "coherence_pass"] == 1
    assert summary.loc[0, "coherence_unknown"] == 1


def test_diversity_normalizes_two_valid_distractors(monkeypatch):
    record = {
        "question_id": 1,
        "subject": "test",
        "question_text": "What is the value?",
        "correct_answer": "21",
        "parse_error": "",
        "distractors": [
            {"text": "17"},
            {"text": "9"},
        ],
    }
    plausibility = pd.DataFrame(
        [
            {"question_id": 1, "distractor_index": 1, "plausible": True},
            {"question_id": 1, "distractor_index": 2, "plausible": True},
        ]
    )

    def fake_judge(prompt, client=None, model=None):
        return {"same_error": False, "shared_faulty_step": "", "reason": "different"}, True

    monkeypatch.setattr(pilot, "cached_judge_json", fake_judge)
    details, _ = pilot.evaluate_diversity([record], plausibility, repeats=1)
    assert details.loc[0, "diversity"] == 1.0
