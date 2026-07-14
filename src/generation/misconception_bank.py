"""Misconception bank — loads Eedi data, provides lookups and embedding search.

Sources:
  - train.csv: Questions with 4 answer options + misconception labels per option
  - misconception_mapping.csv: ~2,500 misconception names with IDs

Usage:
    bank = MisconceptionBank()
    bank.load()  # loads CSV, pre-embeds misconceptions

    # Find which misconception a distractor maps to
    bank.match_misconception("22")  # → {"id": ..., "name": "Concatenation", "score": 0.92}

    # Get questions by subject
    bank.questions_by_subject("BIDMAS")
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.generation.retriever import EmbeddingIndex
from src.utils.llm_client import LLMClient

# Paths relative to project root
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "eedi"


class MisconceptionBank:
    """Loads and indexes Eedi data for MCQ distractor generation."""

    def __init__(self, embed_client: LLMClient | None = None):
        self.embed_client = embed_client or LLMClient.from_role("embed")
        self._misconception_map: dict[int, str] = {}      # id → name
        self._questions: pd.DataFrame | None = None
        self._index: EmbeddingIndex | None = None

    # ── Loading ─────────────────────────────────────────────────────────────

    def load(self) -> "MisconceptionBank":
        """Load both CSV files and build the embedding index."""
        return self._load_misconceptions()._load_questions()._build_index()

    def _load_misconceptions(self) -> "MisconceptionBank":
        path = DATA_DIR / "misconception_mapping.csv"
        df = pd.read_csv(path)
        self._misconception_map = dict(
            zip(df["MisconceptionId"], df["MisconceptionName"])
        )
        print(f"  Loaded {len(self._misconception_map)} misconceptions")
        return self

    def _load_questions(self) -> "MisconceptionBank":
        path = DATA_DIR / "train.csv"
        self._questions = pd.read_csv(path)
        print(f"  Loaded {len(self._questions)} questions")
        return self

    def _build_index(self) -> "MisconceptionBank":
        """Pre-embed all misconception names for fast similarity matching."""
        items = [
            {"misconception_id": id_, "name": name}
            for id_, name in self._misconception_map.items()
        ]
        self._index = EmbeddingIndex(self.embed_client)
        self._index.add(items, text_field="name", cache_key="eedi_misconceptions")
        print(f"  Indexed {self._index.size} misconception embeddings")
        return self

    # ── Lookups ─────────────────────────────────────────────────────────────

    @property
    def misconceptions(self) -> dict[int, str]:
        """Map of misconception_id → name."""
        return dict(self._misconception_map)

    @property
    def questions(self) -> pd.DataFrame:
        """Full Eedi train DataFrame."""
        if self._questions is None:
            raise RuntimeError("MisconceptionBank not loaded. Call .load() first.")
        return self._questions

    def question_count(self) -> int:
        return len(self._questions) if self._questions is not None else 0

    def questions_by_subject(self, subject: str) -> pd.DataFrame:
        """Filter questions by SubjectName."""
        if self._questions is None:
            return pd.DataFrame()
        return self._questions[
            self._questions["SubjectName"].str.contains(subject, case=False, na=False)
        ]

    def get_misconception_name(self, misconception_id: float | int | None) -> str | None:
        """Resolve a misconception ID to its name."""
        if pd.isna(misconception_id):
            return None
        return self._misconception_map.get(int(misconception_id))

    def get_ground_truth_distractors(self, question_id: int) -> list[dict]:
        """Return the human-written distractors + misconception labels for a question.

        Returns:
            List of dicts with keys: text, is_correct, misconception_id, misconception_name
        """
        if self._questions is None:
            return []

        row = self._questions[self._questions["QuestionId"] == question_id]
        if row.empty:
            return []

        row = row.iloc[0]
        correct = row["CorrectAnswer"]
        options = []

        for letter in ["A", "B", "C", "D"]:
            text = row.get(f"Answer{letter}Text", "")
            if pd.isna(text) or not str(text).strip():
                continue
            misconception_id = row.get(f"Misconception{letter}Id", None)
            options.append({
                "text": str(text).strip(),
                "is_correct": letter == correct,
                "misconception_id": misconception_id,
                "misconception_name": self.get_misconception_name(misconception_id),
            })

        return options

    # ── Matching ────────────────────────────────────────────────────────────

    def match_misconception(
        self,
        distractor_text: str,
        k: int = 3,
        min_score: float = 0.5,
    ) -> list[dict]:
        """Find the closest misconception(s) for a generated distractor text.

        Uses embedding similarity to map a distractor to the most likely
        misconception from the Eedi bank.
        """
        if self._index is None:
            raise RuntimeError("MisconceptionBank not loaded. Call .load() first.")
        return self._index.search(distractor_text, k=k, min_score=min_score)

    def match_misconception_by_vector(
        self,
        vector: list[float],
        k: int = 3,
        min_score: float = 0.5,
    ) -> list[dict]:
        """Same as match_misconception but using a pre-computed vector."""
        if self._index is None:
            raise RuntimeError("MisconceptionBank not loaded. Call .load() first.")
        return self._index.search_by_vector(vector, k=k, min_score=min_score)
