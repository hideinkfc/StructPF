"""MCQ distractor generator with strategy dispatch.

Supports:
  - zero_shot: generate from stem alone
  - misconception_conditioned: inject known misconception names
    - misconception_random: inject randomly sampled misconception names
  - fewshot_static: fixed example questions
  - fewshot_rag: retrieve similar questions by embedding

Each strategy shares a common output schema and prompt skeleton. Structured-path
mode additionally requires a faulty step and ordered reasoning steps.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# ── Schemas (Pydantic models used for structured generation) ─────────────────
from pydantic import BaseModel, Field

from src.generation.misconception_bank import MisconceptionBank
from src.generation.retriever import EmbeddingIndex
from src.utils.llm_client import LLMClient


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


class StructuredDistractorItem(DistractorItem):
    """A distractor with an executable student-error pathway."""

    faulty_step: str = Field(min_length=1)
    reasoning_steps: list[str] = Field(min_length=1)


class StructuredMCQGenerationOutput(BaseModel):
    """Structured MCQ output with required pathway fields."""

    model_config = {"extra": "allow"}

    distractors: list[StructuredDistractorItem]
    strategy: str = ""


# ── Strategy enum ───────────────────────────────────────────────────────────


class Strategy(str, Enum):
    ZERO_SHOT = "zero_shot"
    MISCONCEPTION_CONDITIONED = "misconception_conditioned"
    MISCONCEPTION_RANDOM = "misconception_random"
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
        structured_paths: bool = False,
        question_metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> MCQGenerationOutput | StructuredMCQGenerationOutput:
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
            mc_cond_depth: For misconception-conditioned: "names" | "causal" | "personas".
            structured_paths: Require a faulty step and ordered reasoning steps for every
                distractor.
            question_metadata: Optional stem metadata used for retrieval, such as subject
                and construct. Misconception labels are used only for post-generation logging.

        Returns:
            MCQGenerationOutput with generated distractors.
        """
        strategy = Strategy(strategy)
        conditioning_metadata: dict[str, Any] = {}
        messages = self._build_messages(
            question_text,
            correct_answer,
            strategy,
            n_distractors,
            prompt_variant,
            system_variant,
            instruction_variant,
            fewshot_mode,
            mc_cond_depth,
            structured_paths,
            question_metadata,
            conditioning_metadata,
        )

        schema = StructuredMCQGenerationOutput if structured_paths else MCQGenerationOutput
        result = self.llm.generate_structured(
            messages=messages,
            schema=schema,
            temperature=temperature,
            max_tokens=2048,
            **kwargs,
        )
        result.strategy = strategy.value
        if conditioning_metadata:
            result.conditioning_metadata = conditioning_metadata
        return result

    def generate_batch(
        self,
        questions: list[dict[str, Any]],
        strategy: Strategy | str = Strategy.ZERO_SHOT,
        n_distractors: int = 3,
        temperature: float = 0.7,
        structured_paths: bool = False,
    ) -> list[MCQGenerationOutput | StructuredMCQGenerationOutput]:
        """Generate distractors for a batch of questions."""
        results = []
        for q in questions:
            result = self.generate(
                question_text=q["question_text"],
                correct_answer=q["correct_answer"],
                strategy=strategy,
                n_distractors=n_distractors,
                temperature=temperature,
                structured_paths=structured_paths,
                question_metadata=q,
            )
            results.append(result)
        return results

    def build_fewshot_index(
        self,
        *,
        embed_client: LLMClient | None = None,
        cache_key: str | None = "eedi_mcq_fewshot_train_arctic_v1",
    ) -> None:
        """Build the semantic few-shot index from the Eedi training questions."""
        if self.bank is None:
            raise RuntimeError("A misconception bank is required for few-shot retrieval")

        items = []
        for _, row in self.bank.questions.iterrows():
            question_text = row.get("QuestionText", "")
            if pd.isna(question_text) or not str(question_text).strip():
                continue
            item = row.to_dict()
            item["QuestionText"] = str(question_text).strip()
            item["text"] = item["QuestionText"]
            items.append(item)

        if not items:
            raise RuntimeError("The Eedi training question bank contains no indexable questions")

        self._fewshot_index = EmbeddingIndex(embed_client or self.bank.embed_client)
        self._fewshot_index.add(items, text_field="text", cache_key=cache_key)

    # ── Message building ────────────────────────────────────────────────────

    # Prompt variant mappings
    _SYSTEM_MAP = {
        "basic": "SYSTEM_BASIC",
        "expert": "SYSTEM_EXPERT",
        "pedagogical": "SYSTEM_PEDAGOGICAL",
        "lookalike": "SYSTEM_LOOKALIKE",
    }
    _INSTRUCTION_MAP = {
        "direct": "USER_DIRECT",
        "cot": "USER_COT",
        "self_critique": "USER_SELF_CRITIQUE",
        "counterfactual": "USER_COUNTERFACTUAL",
        "difficulty_calibrated": "USER_DIFFICULTY_CALIBRATED",
        "negative_examples": "USER_NEGATIVE_EXAMPLES",
    }
    _INSTRUCTION_GUIDANCE_MAP = {
        "USER_COT": "INSTRUCTION_COT_GUIDANCE",
        "USER_SELF_CRITIQUE": "INSTRUCTION_SELF_CRITIQUE_GUIDANCE",
        "USER_COUNTERFACTUAL": "INSTRUCTION_COUNTERFACTUAL_GUIDANCE",
        "USER_DIFFICULTY_CALIBRATED": "INSTRUCTION_DIFFICULTY_GUIDANCE",
        "USER_NEGATIVE_EXAMPLES": "INSTRUCTION_NEGATIVE_EXAMPLES_GUIDANCE",
    }
    _FEWSHOT_MAP = {
        "minimal": "FEWSHOT_MINIMAL",
        "rationale": "FEWSHOT_RATIONALE",
        "contrastive": "FEWSHOT_CONTRASTIVE",
    }
    _MC_COND_MAP = {
        "names": "MC_CONDITIONED_NAMES",
        "causal": "MC_CONDITIONED_CAUSAL",
        "taxonomy": "MC_CONDITIONED_CAUSAL",
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
        structured_paths: bool = False,
        question_metadata: dict[str, Any] | None = None,
        conditioning_metadata: dict[str, Any] | None = None,
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
            else:
                raise ValueError(f"Unknown prompt variant: {prompt_variant}")

        if system_variant:
            if system_variant not in self._SYSTEM_MAP:
                raise ValueError(f"Unknown system variant: {system_variant}")
            system_key = self._SYSTEM_MAP[system_variant]
        if instruction_variant:
            if instruction_variant not in self._INSTRUCTION_MAP:
                raise ValueError(f"Unknown instruction variant: {instruction_variant}")
            instruction_key = self._INSTRUCTION_MAP[instruction_variant]

        system = self.prompts.get(system_key, "")

        if strategy == Strategy.ZERO_SHOT:
            user = self.prompts[instruction_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
            )

        elif strategy in (Strategy.MISCONCEPTION_CONDITIONED, Strategy.MISCONCEPTION_RANDOM):
            source = "random" if strategy == Strategy.MISCONCEPTION_RANDOM else "semantic"
            misconceptions = self._sample_misconceptions(
                question_text,
                question_metadata=question_metadata,
                k=5,
                source=source,
                conditioning_metadata=conditioning_metadata,
            )
            candidate_text = "\n".join(f"  - {m['name']}" for m in misconceptions)
            mc_key = self._MC_COND_MAP.get(mc_cond_depth, "MC_CONDITIONED_NAMES")
            user = self.prompts[mc_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
                candidate_misconceptions=candidate_text,
            )

        elif strategy in (Strategy.FEWSHOT_STATIC, Strategy.FEWSHOT_RAG):
            examples = self._retrieve_examples(
                question_text,
                strategy,
                question_metadata=question_metadata,
            )
            fs_key = self._FEWSHOT_MAP.get(fewshot_mode, "FEWSHOT_RATIONALE")
            user = self.prompts[fs_key].format(
                question_text=question_text,
                correct_answer=correct_answer,
                n_distractors=n_distractors,
                few_shot_examples=examples,
            )

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        if strategy != Strategy.ZERO_SHOT:
            guidance_key = self._INSTRUCTION_GUIDANCE_MAP.get(instruction_key)
            if guidance_key:
                user = (
                    user
                    + "\n\n"
                    + self.prompts[guidance_key].format(
                        n_distractors=n_distractors,
                    )
                )

        # Append output format instruction to every user prompt
        format_note = self.prompts.get("OUTPUT_FORMAT", "")
        if format_note:
            user = user + "\n\n" + format_note

        if structured_paths:
            path_note = self.prompts.get("STRUCTURED_PATH_OUTPUT", "")
            if path_note:
                user = (
                    user
                    + "\n\n"
                    + path_note.format(
                        n_distractors=n_distractors,
                    )
                )

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _sample_misconceptions(
        self,
        question_text: str,
        question_metadata: dict[str, Any] | None = None,
        k: int = 5,
        source: str = "semantic",
        conditioning_metadata: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Select candidate misconceptions semantically or as a random control."""
        if self.bank is None:
            return []

        if source == "random":
            candidates = [
                {"misconception_id": int(misconception_id), "name": name}
                for misconception_id, name in self.bank.misconceptions.items()
            ]
            selected = random.sample(candidates, min(k, len(candidates)))
        elif source == "semantic":
            metadata = question_metadata or {}
            query_parts = [f"Question: {question_text.strip()}"]
            for key, label in (
                ("SubjectName", "Subject"),
                ("ConstructName", "Construct"),
            ):
                value = metadata.get(key)
                if value is not None and str(value).strip():
                    query_parts.append(f"{label}: {str(value).strip()}")

            matches = self.bank.match_misconception(
                "\n".join(query_parts),
                k=k,
                min_score=0.0,
            )
            selected = [
                {
                    "misconception_id": item.get("misconception_id", item.get("id")),
                    "name": str(item["name"]),
                    "score": float(item["score"]) if item.get("score") is not None else None,
                }
                for item in matches
                if item.get("name")
            ]
        else:
            raise ValueError(f"Unknown misconception source: {source}")

        if conditioning_metadata is not None:
            candidate_ids = [
                int(item["misconception_id"])
                for item in selected
                if item.get("misconception_id") is not None
            ]
            conditioning_metadata.update(
                {
                    "source": source,
                    "candidate_misconception_ids": candidate_ids,
                    "candidate_misconceptions": [item["name"] for item in selected],
                }
            )
            scores = [item.get("score") for item in selected]
            if any(score is not None for score in scores):
                conditioning_metadata["candidate_scores"] = scores

            metadata = question_metadata or {}
            gold_ids = set()
            has_gold_fields = False
            for key in [
                "MisconceptionAId",
                "MisconceptionBId",
                "MisconceptionCId",
                "MisconceptionDId",
            ]:
                if key not in metadata:
                    continue
                has_gold_fields = True
                value = metadata[key]
                if value is None or pd.isna(value):
                    continue
                try:
                    gold_ids.add(int(value))
                except (TypeError, ValueError):
                    continue
            if source == "semantic":
                conditioning_metadata["gold_in_retrieved"] = (
                    bool(gold_ids.intersection(candidate_ids)) if has_gold_fields else None
                )
            else:
                conditioning_metadata["gold_in_candidates"] = (
                    bool(gold_ids.intersection(candidate_ids)) if has_gold_fields else None
                )

        return selected

    def _retrieve_examples(
        self,
        question_text: str,
        strategy: Strategy,
        question_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Retrieve few-shot examples from the Eedi bank, with distractors and misconception info."""
        if self.bank is None:
            if strategy == Strategy.FEWSHOT_RAG:
                raise RuntimeError("A misconception bank is required for few-shot retrieval")
            return ""

        if strategy == Strategy.FEWSHOT_RAG:
            if self._fewshot_index is None:
                raise RuntimeError("Call build_fewshot_index before using fewshot_rag")
            similar = self._fewshot_index.search(question_text, k=4)
            target_id = (question_metadata or {}).get("QuestionId")
            if target_id is not None:
                similar = [
                    item for item in similar if str(item.get("QuestionId", "")) != str(target_id)
                ][:3]
            else:
                normalized_question = question_text.strip()
                similar = [
                    item
                    for item in similar
                    if str(item.get("QuestionText", item.get("question", ""))).strip()
                    != normalized_question
                ][:3]
            if not similar:
                raise RuntimeError("Few-shot retrieval returned no eligible training examples")
        else:
            # Static: pick 2 questions from a matching subject
            all_qs = self.bank.questions
            subjects = [
                "BIDMAS",
                "Arithmetic",
                "Fractions",
                "Decimals",
                "Algebra",
                "Geometry",
                "Ratio",
                "Probability",
            ]
            q_lower = question_text.lower()
            matched = [
                s
                for s in subjects
                if s.lower().split("_")[0] in q_lower
                or any(w in q_lower for w in s.lower().split("_"))
            ]
            pool = all_qs
            if matched:
                pool = all_qs[
                    all_qs["SubjectName"].str.contains("|".join(matched), case=False, na=False)
                ]
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
