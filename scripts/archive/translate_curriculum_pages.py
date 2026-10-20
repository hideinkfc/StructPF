"""Create English page translations for non-English curriculum chunks.

Translations are a build-time artifact. The original page text remains in the
corpus, and the translated chunk keeps the same document and page provenance.

Usage:
    ./.venv/bin/python scripts/translate_curriculum_pages.py --limit 1
    ./.venv/bin/python scripts/translate_curriculum_pages.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prior_methods.common import chat_json, load_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "curriculum_grounding" / "corpus_chunks.json"
OUT_PATH = ROOT / "data" / "curriculum_grounding" / "corpus_translations.json"

SYSTEM_PROMPT = """\
You translate official curriculum text from German into English for a
searchable research corpus. Translate faithfully and literally. Preserve
curriculum codes, mathematical notation, grade labels, and list structure.
Do not summarize, interpret, add examples, or infer what the curriculum means.
Return only valid JSON.
"""

USER_TEMPLATE = """\
Translate this one curriculum page into English.

DOCUMENT: {doc_title}
PAGE: {page}
SOURCE TEXT:
{source_text}

Return exactly:
{{"translation": "faithful English translation"}}
"""


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_state() -> dict:
    if not OUT_PATH.exists():
        return {"schema_version": 1, "model": None, "translations": {}}
    state = json.loads(OUT_PATH.read_text())
    if not isinstance(state.get("translations"), dict):
        raise ValueError(f"translations must be an object in {OUT_PATH}")
    return state


def _save_state(state: dict) -> None:
    OUT_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def _translation_pages() -> list[dict]:
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"Build the corpus first: {CORPUS_PATH}")
    chunks = json.loads(CORPUS_PATH.read_text())
    pages = [
        chunk
        for chunk in chunks
        if chunk.get("language") != "en" and chunk.get("chunk_id", "").endswith("::original")
    ]
    return sorted(pages, key=lambda chunk: (chunk["doc"], chunk["page"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="Translate at most this many pages")
    parser.add_argument(
        "--model",
        default="gpt41mini",
        choices=("gpt41mini", "gpt41", "gpt54", "luna"),
        help="Azure model label (default: gpt41mini)",
    )
    args = parser.parse_args()

    pages = _translation_pages()
    state = _load_state()
    client, model = load_client(args.model)
    state["model"] = model
    pending = []
    for page in pages:
        key = f"{page['doc']}::p{page['page']}"
        existing = state["translations"].get(key)
        if (
            isinstance(existing, dict)
            and existing.get("source_sha256") == _source_hash(page["text"])
            and isinstance(existing.get("translation"), str)
            and existing["translation"].strip()
        ):
            continue
        pending.append(page)

    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        pending = pending[: args.limit]

    print(f"pages needing translation: {len(pending)}")
    for number, page in enumerate(pending, 1):
        key = f"{page['doc']}::p{page['page']}"
        prompt = USER_TEMPLATE.format(
            doc_title=page["doc_title"],
            page=page["page"],
            source_text=page["text"],
        )
        payload, raw = chat_json(
            client,
            model,
            SYSTEM_PROMPT,
            prompt,
            temperature=0.0,
            max_tokens=2500,
        )
        translation = payload.get("translation") if isinstance(payload, dict) else None
        if not isinstance(translation, str) or not translation.strip():
            raise ValueError(f"Translation failed for {key}; raw response: {raw[:500]}")
        state["translations"][key] = {
            "translation": translation.strip(),
            "source_sha256": _source_hash(page["text"]),
            "model": model,
        }
        _save_state(state)
        print(f"[{number}/{len(pending)}] {key}")

    print(f"saved -> {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
