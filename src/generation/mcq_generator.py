"""MCQ distractor generator with strategy dispatch.

Supports:
  - zero_shot: generate from stem alone
  - misconception_conditioned: inject known misconception names
  - fewshot_static: fixed example questions
  - fewshot_rag: retrieve similar questions by embedding

Each strategy shares a common output schema and prompt skeleton.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from src.generation.misconception_bank import MisconceptionBank
from src.generation.retriever import EmbeddingIndex
from src.utils.llm_client import LLMClient

# ── Schemas (Pydantic models used for structured generation) ─────────────────

from pydantic import BaseModel


class DistractorItem(BaseModel):
    """A single generated distractor. Accepts extra fields from prompt variants."""
    model_config = {"extra": "allow"}

    text: str
    target_misconception: str
    error_rationale: str


class MCQGenerationOutput(BaseModel):
    """Output schema for MCQ distractor generation."""
    model_config = {"extra": "allow"}

    distractors: list[DistractorItem]
    strategy: str = ""


# ── Strategy enum ───────────────────────────────────────────────────────────

class Strategy(str, Enum):
    ZERO_SHOT = "zero_shot"
    MISCONCEPTION_CONDITIONED = "misconception_conditioned"
    FEWSHOT_STATIC = "fewshot_static"
    FEWSHOT_RAG = "fewshot_rag"


# ── Generator ───────────────────────────────────────────────────────────────

@dataclass
class MCQGenerator:
    """Generates MCQ distractors using different strategies."""

    llm: LLMClient = field(default_factory=lambda: LLMClient.from_role("structured"))
    bank: MisconceptionBank | None = None
    prompts: dict[str, str] = field(default_factory=dict)
    _fewshot_index: EmbeddingIndex | None = field(default=None, repr=False)

    def __post_init__(self):
        if not self.prompts:
            self._load_prompts()

    def _load_prompts(self) -> None:
        path = Path(__file__).resolve().parent / "prompts" / "mcq.yaml"
        with open(path) as f:
            self.prompts = yaml.safe_load(f)

    # ── Public API ──────────────────────────────────────────────────────────

    def generate(
        self,
        question_text: str,
        correct_answer: str,
        strategy: Strategy | str = Strategy.ZERO_SHOT,
        n_distractors: int = 3,
        temperature: float = 0.7,
        prompt_variant: str = "default",
        system_variant: str = "",
        instruction_variant: str = "",
        fewshot_mode: str = "rationale",
        mc_cond_depth: str = "names",
        **kwargs,
    ) -> MCQGenerationOutput:
        """Generate distractors for a question using the specified strategy.

        Args:
            question_text: The math question stem.
            correct_answer: The correct answer text.
            strategy: Generation strategy.
            n_distractors: How many distractors to generate.
            temperature: Sampling temperature.
            prompt_variant: Legacy shortcut. One of "default" | system key | instruction key.
            system_variant: System prompt: "basic" | "expert" | "pedagogical" | "lookalike".
            instruction_variant: Instruction: "direct" | "cot" | "self_critique" |
                "counterfactual" | "difficulty_calibrated" | "negative_examples".
            fewshot_mode: For few-shot strategies: "minimal" | "rationale" | "contrastive".
            mc_cond_depth: For misconception-conditioned: "names" | "taxonomy" | "personas".

        Returns:
            MCQGenerationOutput with generated distractors.
        """
        strategy = Strategy(strategy)
        messages = self._build_messages(
            question_text, correct_answer, strategy, n_distractors,
            prompt_variant, system_variant, instruction_variant,
            fewshot_mode, mc_cond_depth,
        )

        result = self.llm.generate_structured(
            messages=messages,
            schema=MCQGenerationOutput,
            temperature=temperature,
            max_tokens=2048,
            **kwargs,
        )
        result.strategy = strategy.value
        return result

    def generate_batch(
        self,
        questions: list[dict[str, Any]],
        strategy: Strategy | str = Strategy.ZERO_SHOT,
        n_distractors: int = 3,
        temperature: float = 0.7,
    ) -> list[MCQGenerationOutput]:
        """Generate distractors for a batch of questions."""
        results = []
        for q in questions:
            result = self.generate(
                question_text=q["question_text"],
                correct_answer=q["correct_answer"],
                strategy=strategy,
                n_distractors=n_distractors,
                temperature=temperature,
            )
            results.append(result)
        return results

    # ── Message building ────────────────────────────────────────────────────

    # Prompt variant mappings
    _SYSTEM_MAP = {
        "basic":       "SYSTEM_BASIC",
        "expert":      "SYSTEM_EXPERT",
        "pedagogical": "SYSTEM_PEDAGOGICAL",
        "lookalike":   "SYSTEM_LOOKALIKE",
    }
    _INSTRUCTION_MAP = {
        "direct":              "USER_DIRECT",
        "cot":                 "USER_COT",
        "self_critique":       "USER_SELF_CRITIQUE",
        "counterfactual":      "USER_COUNTERFACTUAL",
        "difficulty_calibrated":"USER_DIFFICULTY_CALIBRATED",
        "negative_examples":   "USER_NEGATIVE_EXAMPLES",
    }
    _FEWSHOT_MAP = {
        "minimal":     "FEWSHOT_MINIMAL",
        "rationale":   "FEWSHOT_RATIONALE",
        "contrastive":  "FEWSHOT_CONTRASTIVE",
    }
    _MC_COND_MAP = {
        "names":    "MC_CONDITIONED_NAMES",
        "taxonomy": "MC_CONDITIONED_TAXONOMY",
        "personas": "MC_CONDITIONED_PERSONAS",
    }

    def _build_messages(
        self,
        question_text: str,
        correct_answer: str,
        strategy: Strategy,
        n_distractors: int,
        prompt_variant: str = "default",
        system_variant: str = "",
        instruction_variant: str = "",
        fewshot_mode: str = "rationale",
        mc_cond_depth: str = "names",
    ) -> list[dict[str, str]]:
        """Build the message list based on strategy and prompt variant."""
        # Resolve system and instruction keys
        system_key = "SYSTEM_EXPERT"
        instruction_key = "USER_DIRECT"

        if prompt_variant != "default":
            if prompt_variant in self._SYSTEM_MAP:
                system_key = self._SYSTEM_MAP[prompt_variant]
            elif prompt_variant in self._INSTRUCTION_MAP:
                instruction_key = self._INSTRUCTION_MAP[prompt_variant]

        if system_variant and system_variant in self._SYSTEM_MAP:
            system_key = self._SYSTEM_MAP[system_variant]
        if instruction_variant and instruction_variant in self._INSTRUCTION_MAP:
            instruction_key = self._INSTRUCTION_MAP[instruction_variant]

        system = self.prompts.get(system_key, "")

        if strategy == Strategy.ZERO_SHOT:
            user = self.prompts[instruction_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
            )

        elif strategy == Strategy.MISCONCEPTION_CONDITIONED:
            misconceptions = self._sample_misconceptions(question_text, k=5)
            candidate_text = "\n".join(
                f"  - {m['name']}" for m in misconceptions
            )
            mc_key = self._MC_COND_MAP.get(mc_cond_depth, "MC_CONDITIONED_NAMES")
            user = self.prompts[mc_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
                candidate_misconceptions=candidate_text,
            )

        elif strategy in (Strategy.FEWSHOT_STATIC, Strategy.FEWSHOT_RAG):
            examples = self._retrieve_examples(question_text, strategy)
            fs_key = self._FEWSHOT_MAP.get(fewshot_mode, "FEWSHOT_RATIONALE")
            user = self.prompts[fs_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
                few_shot_examples=examples,
            )

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Append output format instruction to every user prompt
        format_note = self.prompts.get("OUTPUT_FORMAT", "")
        if format_note:
            user = user + "\n\n" + format_note

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _sample_misconceptions(self, question_text: str, k: int = 5) -> list[dict]:
        """Sample candidate misconceptions for conditioning.

        Finds misconceptions from Eedi questions in the same subject area.
        Uses the question text to find similar questions, then collects the
        misconceptions from those questions' known distractors.
        """
        if self.bank is None:
            return []

        # Try to find a matching subject via keyword overlap
        # Common math subjects in Eedi
        subjects = ["BIDMAS", "Arithmetic", "Fractions", "Decimals", "Percentages",
                     "Algebra", "Geometry", "Statistics", "Ratio", "Probability"]

        # Simple heuristic: check which subjects appear in the question text
        question_lower = question_text.lower()
        relevant_subjects = [s for s in subjects if any(
            word in question_lower for word in s.lower().split("_")
        )]

        if relevant_subjects:
            # Get questions from matching subjects
            matched_qs = self.bank.questions[
                self.bank.questions["SubjectName"].str.contains(
                    "|".join(relevant_subjects), case=False, na=False
                )
            ]
        else:
            matched_qs = self.bank.questions.sample(min(50, self.bank.question_count()))

        # Collect unique misconception IDs from these questions
        mc_ids = set()
        for col in ["MisconceptionAId", "MisconceptionBId",
                     "MisconceptionCId", "MisconceptionDId"]:
            ids = matched_qs[col].dropna().unique()
            mc_ids.update(int(x) for x in ids if not pd.isna(x))

        # Resolve to names
        mc_names = [
            {"name": self.bank.get_misconception_name(mid)}
            for mid in mc_ids
            if self.bank.get_misconception_name(mid) is not None
        ]

        return random.sample(mc_names, min(k, len(mc_names))) if mc_names else []

    def _retrieve_examples(self, question_text: str, strategy: Strategy) -> str:
        """Retrieve few-shot examples from the Eedi bank, with distractors and misconception info."""
        if self.bank is None:
            return ""

        if strategy == Strategy.FEWSHOT_RAG and self._fewshot_index is not None:
            similar = self._fewshot_index.search(question_text, k=2)
        else:
            # Static: pick 2 questions from a matching subject
            all_qs = self.bank.questions
            subjects = ["BIDMAS", "Arithmetic", "Fractions", "Decimals",
                         "Algebra", "Geometry", "Ratio", "Probability"]
            q_lower = question_text.lower()
            matched = [s for s in subjects if s.lower().split("_")[0] in q_lower
                       or any(w in q_lower for w in s.lower().split("_"))]
            pool = all_qs
            if matched:
                pool = all_qs[all_qs["SubjectName"].str.contains("|".join(matched), case=False, na=False)]
            similar_qs = pool.sample(min(2, len(pool)))
            similar = [row for _, row in similar_qs.iterrows()]

        lines = []
        for i, row in enumerate(similar, 1):
            q_text = row.get("QuestionText", row.get("question", ""))
            correct = row.get("CorrectAnswer", "A")
            distractors = []
            for letter in ["A", "B", "C", "D"]:
                text = row.get(f"Answer{letter}Text", "")
                mc_id = row.get(f"Misconception{letter}Id", "")
                if text and letter != correct:
                    mc_name = self.bank.get_misconception_name(mc_id) if mc_id else ""
                    distractors.append(f"    - {text}  (misconception: {mc_name or '—'})")
            lines.append(f"Example {i}:")
            lines.append(f"  Question: {q_text}")
            lines.append(f"  Correct answer: {row.get(f'Answer{correct}Text', '')}")
            lines.append("  Wrong answers (distractors):")
            lines.extend(distractors[:3])
            lines.append("")
        return "\n".join(lines)
