"""Retrieve candidate prior-knowledge sections from the curriculum corpus.

Given a topic (e.g. "average speed", "variance", "fraction equivalence"), return
the most semantically similar curriculum sections across the downloaded official
documents, each with jurisdiction, grade range, section heading, and page.

The point: given a NEW target topic/grade, this proposes what plausibly precedes
it — the `[builds on]` candidate pool — which a teacher or pipeline then filters.

Requires: data/curriculum_grounding/corpus_chunks.json
  (build with scripts/build_curriculum_corpus.py)

Usage:
    ./.venv/bin/python scripts/retrieve_prior_knowledge.py "average speed"
    ./.venv/bin/python scripts/retrieve_prior_knowledge.py "variance spread consistency" \
        --grade 10 --jurisdiction NRW
    ./.venv/bin/python scripts/retrieve_prior_knowledge.py "kinematics braking motion" --k 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generation.retriever import EmbeddingIndex  # noqa: E402
from src.utils.llm_client import LLMClient  # noqa: E402

CORPUS_PATH = ROOT / "data" / "curriculum_grounding" / "corpus_chunks.json"
CACHE_PREFIX = "curriculum_grounding_chunks_v2"
EMBED_MODEL = "text-embedding-3-small-EU"


def _azure_embed_client() -> LLMClient:
    load_dotenv(ROOT / ".env", override=False)
    base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("AZURE_OPENAI_BASE_URL / AZURE_OPENAI_API_KEY missing from .env")
    return LLMClient(base_url=base_url, model=EMBED_MODEL, api_key=api_key)


def load_chunks() -> list[dict]:
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"Build the corpus first: {CORPUS_PATH}")
    chunks = json.loads(CORPUS_PATH.read_text())
    if not isinstance(chunks, list):
        raise ValueError(f"Corpus must be a list in {CORPUS_PATH}")
    return chunks


def _cache_key(chunks: list[dict]) -> str:
    source = json.dumps(chunks, sort_keys=True, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(source).hexdigest()[:12]
    return f"{CACHE_PREFIX}_{digest}"


def build_index() -> EmbeddingIndex:
    chunks = load_chunks()
    for c in chunks:
        c["_embed_text"] = (
            f"{c['jurisdiction']} {c['doc_title']} (p.{c['page']}, {c['language']}) | {c['text']}"
        )

    index = EmbeddingIndex(_azure_embed_client())
    index.add(chunks, text_field="_embed_text", cache_key=_cache_key(chunks))
    return index


def retrieve_chunks(
    query: str,
    *,
    k: int = 6,
    grade: int | None = None,
    jurisdiction: str | None = None,
    subject: str | None = None,
    min_score: float = 0.0,
) -> list[dict]:
    """Return top-k corpus pages after metadata filtering."""
    if k < 1:
        raise ValueError("k must be positive")
    index = build_index()
    results = index.search(query, k=max(k * 8, 50), min_score=min_score)
    filtered = []
    for result in results:
        if grade is not None and grade not in result.get("grades", []):
            continue
        if jurisdiction and jurisdiction.lower() not in result.get("jurisdiction", "").lower():
            continue
        if subject and subject.lower() not in result.get("subject", "").lower():
            continue
        filtered.append(result)
        if len(filtered) >= k:
            break
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Target topic text")
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--grade", type=int, help="Keep only docs covering this grade")
    parser.add_argument("--jurisdiction", help="Substring filter, e.g. NRW or Singapore")
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()

    filtered = retrieve_chunks(
        args.query,
        k=args.k,
        grade=args.grade,
        jurisdiction=args.jurisdiction,
        min_score=args.min_score,
    )

    out = [
        {
            "score": round(r["score"], 3),
            "jurisdiction": r["jurisdiction"],
            "grades": r["grades"],
            "doc": r["doc_title"],
            "page": r["page"],
            "excerpt": r["text"][:280],
        }
        for r in filtered
    ]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
