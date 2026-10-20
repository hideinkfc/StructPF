#!/usr/bin/env python3
"""
Post-process scraped Eedi quiz files: download question images and OCR them
to add human-readable question_text to each question.

Usage:
  python scripts/ocr_eedi_images.py --dir data/eedi_scraped
"""

import argparse
import json
import time
from pathlib import Path

import pytesseract
import requests
from PIL import Image


def ocr_image(url: str, cache_dir: Path, max_retries: int = 2) -> str:
    """Download an image from URL, cache it, and return OCR text."""
    # Use the UUID filename from the URL
    fname = url.split("/")[-1]  # e.g. a414fa0a-c56c-4a51-8686-875c28a9fb0b.jpg
    cache_path = cache_dir / fname

    if not cache_path.exists():
        for attempt in range(max_retries + 1):
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    cache_path.write_bytes(r.content)
                    break
            except Exception:
                if attempt == max_retries:
                    return f"[download failed: {url}]"
                time.sleep(1)

    try:
        img = Image.open(cache_path)
        # Convert to grayscale for better OCR
        img = img.convert("L")
        text = pytesseract.image_to_string(img).strip()
        return text
    except Exception as e:
        return f"[OCR error: {e}]"


def main():
    parser = argparse.ArgumentParser(description="OCR Eedi question images")
    parser.add_argument(
        "--dir", default="data/eedi_scraped", help="Directory with scraped JSON files"
    )
    args = parser.parse_args()

    data_dir = Path(args.dir)
    cache_dir = data_dir / "_images_cache"
    cache_dir.mkdir(exist_ok=True)

    json_files = sorted([f for f in data_dir.glob("*.json") if not f.name.startswith("_")])
    print(f"Processing {len(json_files)} quiz files...")

    for i, fpath in enumerate(json_files):
        with open(fpath) as f:
            quiz = json.load(f)

        modified = False
        for q in quiz.get("questions", []):
            # Skip if already has question_text
            if q.get("question_text"):
                continue

            all_text = []
            for img_url in q.get("image_urls", []):
                if img_url:
                    ocr_text = ocr_image(img_url, cache_dir)
                    all_text.append(ocr_text)
                    modified = True
                    time.sleep(0.3)  # polite delay

            if all_text:
                q["question_text"] = "\n\n".join(all_text)

        if modified:
            with open(fpath, "w") as f:
                json.dump(quiz, f, indent=2, ensure_ascii=False)
            print(
                f"  [{i + 1}/{len(json_files)}] {quiz.get('quiz_id', '?')}: OCR'd {sum(1 for q in quiz['questions'] if q.get('question_text'))} questions"
            )

    print("Done!")


if __name__ == "__main__":
    main()
