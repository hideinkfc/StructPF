import pandas as pd
import pytest

from src.generation.mcq_generator import MCQGenerator, Strategy
from src.generation.misconception_bank import MisconceptionBank


class FakeEmbedder:
    vectors = {
        "target question": [1.0, 0.0],
        "nearest one": [0.99, 0.1],
        "nearest two": [0.95, 0.2],
        "nearest three": [0.9, 0.3],
        "other question": [0.0, 1.0],
    }

    def embed(self, texts):
        single = isinstance(texts, str)
        values = [self.vectors[text] for text in ([texts] if single else texts)]
        return values[0] if single else values


def make_generator() -> MCQGenerator:
    embedder = FakeEmbedder()
    bank = MisconceptionBank(embed_client=embedder)
    bank._questions = pd.DataFrame([
        {"QuestionId": 99, "QuestionText": "target question", "CorrectAnswer": "A",
         "AnswerAText": "1"},
        {"QuestionId": 1, "QuestionText": "nearest one", "CorrectAnswer": "A",
         "AnswerAText": "1"},
        {"QuestionId": 2, "QuestionText": "nearest two", "CorrectAnswer": "A",
         "AnswerAText": "2"},
        {"QuestionId": 3, "QuestionText": "nearest three", "CorrectAnswer": "A",
         "AnswerAText": "3"},
        {"QuestionId": 4, "QuestionText": "other question", "CorrectAnswer": "A",
         "AnswerAText": "4"},
    ])
    generator = MCQGenerator(llm=object(), bank=bank)
    generator.build_fewshot_index(embed_client=embedder, cache_key=None)
    return generator


def test_fewshot_rag_retrieves_three_nearest_training_questions_without_target():
    generator = make_generator()

    examples = generator._retrieve_examples("target question", Strategy.FEWSHOT_RAG)

    assert "target question" not in examples
    assert examples.count("Example ") == 3
    assert examples.index("nearest one") < examples.index("nearest two")
    assert examples.index("nearest two") < examples.index("nearest three")


def test_fewshot_rag_requires_an_initialized_index():
    embedder = FakeEmbedder()
    bank = MisconceptionBank(embed_client=embedder)
    bank._questions = pd.DataFrame([{
        "QuestionId": 1,
        "QuestionText": "question",
        "CorrectAnswer": "A",
        "AnswerAText": "1",
    }])
    generator = MCQGenerator(llm=object(), bank=bank)

    with pytest.raises(RuntimeError, match="build_fewshot_index"):
        generator._retrieve_examples("question", Strategy.FEWSHOT_RAG)


def test_fewshot_rag_excludes_target_id_but_keeps_duplicate_stem_examples():
    class FakeIndex:
        def search(self, query, k=5):
            return [
                {
                    "QuestionId": 99,
                    "QuestionText": "target question",
                    "CorrectAnswer": "A",
                    "AnswerAText": "Correct",
                    "AnswerBText": "Wrong",
                },
                {
                    "QuestionId": 1,
                    "QuestionText": "target question",
                    "CorrectAnswer": "A",
                    "AnswerAText": "Correct",
                    "AnswerBText": "Wrong",
                },
                {
                    "QuestionId": 2,
                    "QuestionText": "target question",
                    "CorrectAnswer": "A",
                    "AnswerAText": "Correct",
                    "AnswerBText": "Wrong",
                },
                {
                    "QuestionId": 3,
                    "QuestionText": "nearest question",
                    "CorrectAnswer": "A",
                    "AnswerAText": "Correct",
                    "AnswerBText": "Wrong",
                },
            ]

    bank = MisconceptionBank(embed_client=object())
    generator = MCQGenerator(llm=object(), bank=bank)
    generator._fewshot_index = FakeIndex()

    examples = generator._retrieve_examples(
        "target question",
        Strategy.FEWSHOT_RAG,
        question_metadata={"QuestionId": 99},
    )

    assert examples.count("Question: target question") == 2
    assert "nearest question" in examples


def test_semantic_misconceptions_use_question_metadata_and_log_gold_coverage():
    bank = MisconceptionBank(embed_client=object())
    calls = []

    def fake_match(query, k=3, min_score=0.5):
        calls.append((query, k, min_score))
        return [{
            "misconception_id": 295,
            "name": "Confuses mathematical instruments",
            "score": 0.91,
        }]

    bank.match_misconception = fake_match
    generator = MCQGenerator(llm=object(), bank=bank)
    metadata = {}

    messages = generator._build_messages(
        "What instrument constructs circles?",
        "Compass",
        Strategy.MISCONCEPTION_CONDITIONED,
        3,
        system_variant="expert",
        instruction_variant="direct",
        mc_cond_depth="names",
        question_metadata={
            "SubjectName": "Construct Angle",
            "ConstructName": "Identify mathematical instruments and their functions",
            "MisconceptionAId": 295,
        },
        conditioning_metadata=metadata,
    )

    assert len(messages) == 2
    assert "Construct Angle" in calls[0][0]
    assert "Identify mathematical instruments" in calls[0][0]
    assert "MisconceptionAId" not in calls[0][0]
    assert calls[0][2] == 0.0
    assert metadata["source"] == "semantic"
    assert metadata["candidate_misconception_ids"] == [295]
    assert metadata["gold_in_retrieved"] is True


def test_cot_guidance_composes_with_misconception_prompt():
    bank = MisconceptionBank(embed_client=object())
    bank.match_misconception = lambda query, k=3, min_score=0.5: [{
        "misconception_id": 1,
        "name": "Uses the wrong operation",
        "score": 0.8,
    }]
    generator = MCQGenerator(llm=object(), bank=bank)

    direct = generator._build_messages(
        "Calculate 2 + 2.", "4", Strategy.MISCONCEPTION_CONDITIONED, 3,
        instruction_variant="direct",
    )[1]["content"]
    cot = generator._build_messages(
        "Calculate 2 + 2.", "4", Strategy.MISCONCEPTION_CONDITIONED, 3,
        instruction_variant="cot",
    )[1]["content"]

    assert direct != cot
    assert "Before finalizing" in cot
    assert "Uses the wrong operation" in cot


def test_random_misconception_control_samples_the_full_bank():
    bank = MisconceptionBank(embed_client=object())
    bank._misconception_map = {
        1: "First misconception",
        2: "Second misconception",
        3: "Third misconception",
    }
    generator = MCQGenerator(llm=object(), bank=bank)

    candidates = generator._sample_misconceptions(
        "Question text",
        k=2,
        source="random",
    )

    assert len(candidates) == 2
    assert {item["misconception_id"] for item in candidates} <= {1, 2, 3}


def test_unknown_instruction_variant_fails_fast():
    generator = MCQGenerator(llm=object())

    with pytest.raises(ValueError, match="Unknown instruction variant"):
        generator._build_messages(
            "Question text",
            "Correct answer",
            Strategy.ZERO_SHOT,
            3,
            instruction_variant="typo",
        )


def test_structured_paths_append_path_contract_and_require_fields():
    generator = MCQGenerator(llm=object())

    messages = generator._build_messages(
        "Calculate 2 + 2.",
        "4",
        Strategy.ZERO_SHOT,
        3,
        structured_paths=True,
    )

    assert "STRUCTURED PATH REQUIREMENT" in messages[1]["content"]
    assert "faulty_step" in messages[1]["content"]
    assert "reasoning_steps" in messages[1]["content"]
