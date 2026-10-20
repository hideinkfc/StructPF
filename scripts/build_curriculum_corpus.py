"""Build a page-referenced chunk corpus from curriculum grounding PDFs.

Each curriculum document is split into one chunk per page. Chunks keep
(source file, page, jurisdiction, grade range), so a topic query returns the
curriculum content plus exactly which page of which official document it came
from. If a translation artifact exists, each non-English page also gets a
parallel English chunk with the same page provenance.

Design:
- Chunking is page-level: one chunk = one PDF page. No format-specific heading
  detection — works for any curriculum document without assumptions.
- Chunks are capped (~2000 chars) to stay within embedding context.
- Output: data/curriculum_grounding/corpus_chunks.json

Usage:
    ./.venv/bin/python scripts/build_curriculum_corpus.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "data" / "curriculum_grounding" / "documents"
OUT_PATH = ROOT / "data" / "curriculum_grounding" / "corpus_chunks.json"
TRANSLATIONS_PATH = ROOT / "data" / "curriculum_grounding" / "corpus_translations.json"
SUPPLEMENT_PATH = DOC_DIR / "ccss_statistics_supplement.json"

# Document registry: what each local PDF is, and which country/grades it covers.
# This is the retrieval filter surface.
DOCUMENTS = {
    "moe_sg_2020_secondary_maths.pdf": {
        "jurisdiction": "Singapore",
        "authority": "MOE Singapore",
        "title": "2020 Express/N(A) Mathematics Syllabuses (O-Level & N(A)-Level)",
        "grades": [7, 8, 9, 10],
        "subject": "mathematics",
        "language": "en",
        "url": "https://www.moe.gov.sg/-/media/files/secondary/syllabuses/maths/2020-express_na-maths_syllabuses.pdf",
    },
    "cbse_physics_srsec_2025_26.pdf": {
        "jurisdiction": "India (CBSE)",
        "authority": "CBSE Academic Unit",
        "title": "Senior Secondary Physics Curriculum 2025-26",
        "grades": [11, 12],
        "subject": "physics",
        "language": "en",
        "url": "https://cbseacademic.nic.in/web_material/CurriculumMain26/SrSec/Physics_SrSec_2025-26.pdf",
    },
    "nrw_g9_gymnasium_m_klp.pdf": {
        "jurisdiction": "Germany (NRW)",
        "authority": "NRW LehrplanNavigator",
        "title": "Kernlehrplan Mathematik Gymnasium (G9)",
        "grades": [5, 6, 7, 8, 9, 10],
        "subject": "mathematics",
        "language": "de",
        "url": "https://lehrplannavigator.nrw.de/system/files/media/document/file/g9_m_klp_3401_2019_06_23_0.pdf",
    },
    "lippman_apportionment_v2_6.pdf": {
        "jurisdiction": "USA (OER)",
        "authority": "OpenTextBookStore / David Lippman",
        "title": "Math in Society v2.6 - Apportionment",
        "grades": ["undergraduate"],
        "subject": "mathematics",
        "language": "en",
        "url": "https://www.opentextbookstore.com/mathinsociety/2.6/Apportionment.pdf",
    },
    "lippman_fair_division_v2_6.pdf": {
        "jurisdiction": "USA (OER)",
        "authority": "OpenTextBookStore / David Lippman",
        "title": "Math in Society v2.6 - Fair Division",
        "grades": ["undergraduate"],
        "subject": "mathematics",
        "language": "en",
        "url": "https://www.opentextbookstore.com/mathinsociety/2.6/FairDivision.pdf",
    },
    "lippman_voting_theory_v2_6.pdf": {
        "jurisdiction": "USA (OER)",
        "authority": "OpenTextBookStore / David Lippman",
        "title": "Math in Society v2.6 - Voting Theory",
        "grades": ["undergraduate"],
        "subject": "mathematics",
        "language": "en",
        "url": "https://www.opentextbookstore.com/mathinsociety/2.6/VotingTheory.pdf",
    },
}

MAX_CHUNK_CHARS = 2000
MIN_CHUNK_CHARS = 40


def chunk_document(fname: str, meta: dict) -> list[dict]:
    """One chunk per page, capped at MAX_CHUNK_CHARS."""
    reader = PdfReader(str(DOC_DIR / fname))
    chunks: list[dict] = []
    for page_no, page in enumerate(reader.pages, 1):
        text = " ".join((page.extract_text() or "").split())
        if len(text) < MIN_CHUNK_CHARS:
            continue
        if len(text) > MAX_CHUNK_CHARS:
            text = text[:MAX_CHUNK_CHARS]
        chunks.append(
            {
                "doc": fname,
                "jurisdiction": meta["jurisdiction"],
                "grades": meta["grades"],
                "subject": meta["subject"],
                "doc_title": meta["title"],
                "source_url": meta["url"],
                "page": page_no,
                "language": meta["language"],
                "chunk_id": f"{fname}::p{page_no}::original",
                "text": text,
            }
        )
    return chunks


def load_translations() -> dict[str, dict]:
    if not TRANSLATIONS_PATH.exists():
        return {}
    payload = json.loads(TRANSLATIONS_PATH.read_text())
    translations = payload.get("translations", {})
    if not isinstance(translations, dict):
        raise ValueError(f"translations must be an object in {TRANSLATIONS_PATH}")
    return translations


def add_translation_chunks(chunks: list[dict], translations: dict[str, dict]) -> list[dict]:
    output = list(chunks)
    for chunk in chunks:
        if chunk["language"] == "en":
            continue
        key = f"{chunk['doc']}::p{chunk['page']}"
        record = translations.get(key)
        if record is None:
            continue
        expected_hash = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()
        if record.get("source_sha256") != expected_hash:
            raise ValueError(f"Stale translation for {key} in {TRANSLATIONS_PATH}")
        text = record.get("translation")
        if not isinstance(text, str) or len(text.strip()) < MIN_CHUNK_CHARS:
            raise ValueError(f"Invalid translation for {key} in {TRANSLATIONS_PATH}")
        output.append(
            {
                **chunk,
                "chunk_id": f"{chunk['doc']}::p{chunk['page']}::en_translation",
                "language": "en",
                "translation_of": chunk["chunk_id"],
                "translation_model": record.get("model"),
                "translation_source_sha256": expected_hash,
                "text": text.strip()[:MAX_CHUNK_CHARS],
            }
        )
    return output


def load_supplement_chunks() -> list[dict]:
    if not SUPPLEMENT_PATH.exists():
        return []
    payload = json.loads(SUPPLEMENT_PATH.read_text())
    source = payload.get("source", {})
    records = payload.get("records", [])
    if not isinstance(source, dict) or not isinstance(records, list):
        raise ValueError(f"Invalid supplement shape in {SUPPLEMENT_PATH}")
    chunks = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Invalid supplement record {index} in {SUPPLEMENT_PATH}")
        standard_id = record.get("standard_id")
        text = record.get("text")
        grades = record.get("grade_band")
        url = record.get("url")
        if (
            not isinstance(standard_id, str)
            or not isinstance(text, str)
            or not isinstance(grades, list)
            or not all(isinstance(grade, int) for grade in grades)
            or not isinstance(url, str)
        ):
            raise ValueError(f"Invalid supplement record {index} in {SUPPLEMENT_PATH}")
        chunks.append(
            {
                "doc": SUPPLEMENT_PATH.name,
                "jurisdiction": source.get("jurisdiction", "unknown"),
                "grades": grades,
                "subject": source.get("subject", "unknown"),
                "doc_title": source.get("title", SUPPLEMENT_PATH.name),
                "source_url": url,
                "page": standard_id,
                "language": source.get("language", "en"),
                "chunk_id": f"{SUPPLEMENT_PATH.name}::{standard_id}",
                "text": text.strip()[:MAX_CHUNK_CHARS],
            }
        )
    return chunks


def main() -> None:
    all_chunks: list[dict] = []
    translations = load_translations()
    for fname, meta in DOCUMENTS.items():
        path = DOC_DIR / fname
        if not path.exists():
            print(f"SKIP (missing): {fname}")
            continue
        chunks = chunk_document(fname, meta)
        print(f"{fname}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    all_chunks = add_translation_chunks(all_chunks, translations)
    supplement_chunks = load_supplement_chunks()
    if supplement_chunks:
        print(f"{SUPPLEMENT_PATH.name}: {len(supplement_chunks)} chunks")
        all_chunks.extend(supplement_chunks)
    OUT_PATH.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    print(f"\nTotal: {len(all_chunks)} chunks -> {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
