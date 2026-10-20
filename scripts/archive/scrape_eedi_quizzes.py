#!/usr/bin/env python3
"""
Scrape Eedi quiz pages (public, no login) for:
  - quiz metadata (name, topic, skills)
  - per-question: image URL, answer choices, correct answer,
    misconception explanations, student response percentages.

Usage:
  python scripts/scrape_eedi_quizzes.py \
    --ids-file /tmp/eedi_sample_ids.txt \
    --out-dir data/eedi_scraped \
    [--start 0] [--max 30]
"""

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def accept_cookies(page):
    """Click the cookie Accept button if present."""
    try:
        btn = page.locator("button", has_text="Accept")
        if btn.is_visible(timeout=2000):
            btn.click()
            time.sleep(1)
    except Exception:
        pass  # no cookie banner


def extract_quiz_metadata(page):
    """Extract quiz name and topic from the page heading."""
    try:
        heading = page.locator("h1").first.text_content(timeout=5000).strip()
    except Exception:
        heading = "unknown"
    try:
        # fallback: find text right after h1
        topic_text = ""
        for el in page.locator("h1 ~ *").all():
            txt = el.text_content().strip()
            if txt and txt != heading and len(txt) < 80:
                topic_text = txt
                break
    except Exception:
        topic_text = "unknown"
    return heading, topic_text


def extract_skills(page):
    """Extract skills listed under 'Skills covered in this quiz'."""
    try:
        section = page.locator("h3", has_text="Skills covered").locator("..")
        items = section.locator("> div, > p, > span")
        skills = []
        for i in range(items.count()):
            txt = items.nth(i).text_content().strip()
            if txt and txt != "Skills covered in this quiz":
                skills.append(txt)
        return skills
    except Exception:
        return []


def get_question_image_urls(page):
    """Get the image URLs for all question thumbnails currently visible."""
    imgs = page.locator('img[alt="question"]')
    urls = []
    for i in range(imgs.count()):
        src = imgs.nth(i).get_attribute("src")
        if src:
            urls.append(src)
    # deduplicate while preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def click_question_tab(page, q_num: int):
    """Click the nth question tab (1-indexed)."""
    # Question tabs are spans with exact digit text
    tabs = page.locator("span.sc-iFMCCV")
    count = tabs.count()
    for i in range(count):
        txt = tabs.nth(i).text_content().strip()
        if txt == str(q_num):
            tabs.nth(i).click()
            time.sleep(1)
            return True
    return False


def click_answer_choice(page, label: str) -> dict:
    """Click answer A/B/C/D and extract its explanation info.

    Returns dict with: heading, explanation, pct, is_correct
    """
    # Answer buttons are div.sc-jivDif with text matching the label
    btns = page.locator("div.sc-jivDif")
    count = btns.count()
    clicked = False
    for i in range(count):
        txt = btns.nth(i).text_content().strip()
        # Match exactly "A", "B", "C", "D" (possibly with checkmark SVG)
        if txt.startswith(label) and (len(txt) == 1 or txt[1:].strip() == ""):
            btns.nth(i).click()
            time.sleep(0.6)
            clicked = True
            break
    if not clicked:
        return {"error": f"Could not click choice {label}"}

    # Extract explanation text
    info = {}
    try:
        h4 = page.locator("h4").first
        info["heading"] = h4.text_content().strip()
        # Get the parent container text
        parent = h4.locator("..")
        info["explanation"] = parent.text_content().strip()
    except Exception:
        info["heading"] = ""
        info["explanation"] = ""

    # Check if this answer has a checkmark (green tick SVG)
    try:
        current_btn = page.locator(f"div.sc-jivDif:has-text('{label}')").first
        svg = current_btn.locator("svg")
        info["is_correct"] = svg.count() > 0
    except Exception:
        info["is_correct"] = False

    # Extract percentage
    body_text = page.inner_text("body")
    pct_match = re.search(r"(\d+)% of students on Eedi chose\s+([A-D])", body_text)
    if pct_match:
        info["pct_students"] = int(pct_match.group(1))
        info["chosen_label"] = pct_match.group(2)

    return info


def scrape_quiz(page, quiz_id: str) -> dict:
    """Scrape a single quiz page and return structured data."""
    url = f"https://teacher.eedi.com/quizzes/{quiz_id}"
    print(f"  Navigating to {url}...")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        return {"error": f"Navigation failed: {e}"}

    time.sleep(2)
    accept_cookies(page)

    quiz_name, topic = extract_quiz_metadata(page)
    skills = extract_skills(page)

    result = {
        "quiz_id": quiz_id,
        "quiz_name": quiz_name,
        "topic": topic,
        "skills": skills,
        "questions": [],
    }

    # Find how many questions by counting question tabs
    tab_count = page.locator("span.sc-iFMCCV").count()
    # Filter to only digit-text tabs (1-9)
    q_nums = []
    for i in range(tab_count):
        txt = page.locator("span.sc-iFMCCV").nth(i).text_content().strip()
        if txt.isdigit():
            q_nums.append(int(txt))
    max_q = max(q_nums) if q_nums else 5
    print(f"  Found {max_q} questions")

    for q_num in range(1, max_q + 1):
        print(f"    Q{q_num}...", end=" ")
        # Click the question tab
        if not click_question_tab(page, q_num):
            print("tab not found, skipping")
            continue

        q_data = {
            "question_number": q_num,
            "image_urls": get_question_image_urls(page),
            "answers": {},
        }

        # Click each answer choice
        for label in ["A", "B", "C", "D"]:
            ans_data = click_answer_choice(page, label)
            q_data["answers"][label] = ans_data

        result["questions"].append(q_data)
        print(
            f"done ({sum(1 for a in q_data['answers'].values() if a.get('is_correct'))} correct identified)"
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape Eedi quiz pages")
    parser.add_argument(
        "--ids-file", required=True, help="TSV file: quiz_id\\tsubject\\ttopic\\tname"
    )
    parser.add_argument("--out-dir", default="data/eedi_scraped")
    parser.add_argument("--start", type=int, default=0, help="Start index (0-based)")
    parser.add_argument("--max", type=int, default=30, help="Max quizzes to scrape")
    args = parser.parse_args()

    # Read target quiz IDs
    targets = []
    with open(args.ids_file) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                targets.append(
                    {
                        "quiz_id": parts[0],
                        "subject": parts[1],
                        "topic": parts[2],
                        "quiz_name_csv": parts[3],
                    }
                )

    targets = targets[args.start : args.start + args.max]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scraping {len(targets)} quizzes to {out_dir}/")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = context.new_page()

        success_count = 0
        for i, target in enumerate(targets):
            qid = target["quiz_id"]
            print(f"\n[{i + 1}/{len(targets)}] {qid}: {target['quiz_name_csv']}")

            try:
                data = scrape_quiz(page, qid)
            except Exception as e:
                data = {"error": str(e), "quiz_id": qid}
                print(f"  ERROR: {e}")

            # Merge CSV metadata
            data["subject"] = target["subject"]
            data["topic_csv"] = target["topic"]
            data["quiz_name_csv"] = target["quiz_name_csv"]

            # Save individual file
            fname = f"{qid}.json"
            out_path = out_dir / fname
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Saved to {fname}")

            if "error" not in data:
                success_count += 1

            time.sleep(1)  # polite delay

        browser.close()

    # Also save an aggregated summary
    all_data = []
    for f in sorted(out_dir.glob("*.json")):
        with open(f) as fh:
            all_data.append(json.load(fh))

    summary_path = out_dir / "_aggregated.json"
    with open(summary_path, "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Done! {success_count}/{len(targets)} successful")
    print(f"Output: {out_dir}/_aggregated.json + {len(all_data)} individual files")


if __name__ == "__main__":
    main()
