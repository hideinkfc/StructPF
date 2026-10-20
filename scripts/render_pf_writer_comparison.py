"""Render exact saved PF writer outputs side by side from a comparison audit."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def word_count(task: dict) -> int:
    """Count whitespace-separated tokens containing a letter or digit."""
    text = "\n".join(task[field] for field in ("title", "body", "question"))
    return sum(any(character.isalnum() for character in token) for token in text.split())


def render_body(text: str) -> str:
    blocks = []
    for block in text.split("\n\n"):
        lines = block.splitlines()
        if len(lines) >= 2 and lines[0].startswith("|") and re.fullmatch(r"[\s|:\-]+", lines[1]):
            rows = []
            for index, line in enumerate(lines):
                if index == 1:
                    continue
                tag = "th" if index == 0 else "td"
                cells = "".join(
                    f"<{tag}>{html.escape(cell.strip())}</{tag}>"
                    for cell in line.strip().strip("|").split("|")
                )
                rows.append(f"<tr>{cells}</tr>")
            blocks.append('<div class="table-wrap"><table>' + "".join(rows) + "</table></div>")
        else:
            blocks.append('<p class="prose">' + html.escape(block) + "</p>")
    return "".join(blocks)


def task_panel(task: dict, label: str, source: Path) -> str:
    if task["status"] == "ready":
        content = (
            f"<h3>{html.escape(task['title'])}</h3>"
            + render_body(task["body"])
            + f'<div class="question">{html.escape(task["question"])}</div>'
        )
    else:
        content = "<p>Blocked: " + html.escape("; ".join(task["blocking_issues"])) + "</p>"
    if task.get("quality_findings"):
        content += (
            "<details><summary>Draft produced with unresolved findings</summary><ul>"
            + "".join(f"<li>{html.escape(finding)}</li>" for finding in task["quality_findings"])
            + "</ul></details>"
        )
    return (
        f'<article><div class="label">{html.escape(label)}</div>{content}'
        f'<a class="source" href="{html.escape(source.as_uri(), quote=True)}">'
        "Exact saved result</a></article>"
    )


def render_comparison(audit: dict, root: Path = ROOT) -> str:
    sections = []
    totals = [0, 0]
    for index, item in enumerate(audit["cases"]):
        source = (root / item["source_result"]).resolve()
        replay = (root / item["replay_result"]).resolve()
        old = json.loads(source.read_text(encoding="utf-8"))["stages"]["D2_D3"]["task"]
        new = json.loads(replay.read_text(encoding="utf-8"))["task"]
        counts = [word_count(task) if task["status"] == "ready" else 0 for task in (old, new)]
        totals = [total + count for total, count in zip(totals, counts)]
        count_text = (
            f"{counts[0]} to {counts[1]} words" if new["status"] == "ready" else "Writer blocked"
        )
        inspection = item["inspection"]
        notes = " ".join(
            f"<strong>{label}:</strong> {html.escape(inspection[key])}"
            for label, key in (
                ("Wording", "change"),
                ("Content check", "fidelity"),
                ("Still unresolved", "limitation"),
            )
        )
        sections.append(
            f'<details name="tasks"{" open" if index == 0 else ""}>'
            f"<summary>{html.escape(item['topic'])}"
            f'<span>{count_text}</span></summary><div class="pair">'
            + task_panel(old, "Before / previous writer", source)
            + task_panel(new, "After / three writing rules", replay)
            + f'</div><p class="notes">{notes}</p></details>'
        )
    return (
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PF writer - before and after</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f1;color:#23392f;
font-family:system-ui,sans-serif;line-height:1.55}
header{padding:24px 32px;background:#173e31;color:white}
h1{margin:0 0 8px;font-size:27px}header p{margin:6px 0;font-size:14px}
main{max-width:1420px;margin:24px auto;padding:0 24px}
.rules{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 18px}
.rules span{background:#e3ebe0;padding:7px 12px;border-radius:8px;font-size:14px}
details{background:white;border:1px solid #d5ded6;border-radius:10px;margin:12px 0}
summary{cursor:pointer;padding:16px 20px;font-weight:650}
summary span{float:right;color:#526951;font-size:13px;font-weight:400}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:0 20px 20px}
article{border:1px solid #dce3d9;border-radius:8px;padding:22px;min-width:0}
article:nth-child(2){border-color:#92b092;background:#fbfdf9}
.label{font-size:12px;text-transform:uppercase;color:#617b62;letter-spacing:.7px}
h3{font-size:23px;line-height:1.25;margin:12px 0 22px}
.prose,.question{white-space:pre-wrap;font-size:15px}
.question{background:#edf3e9;border-left:3px solid #6f8c60;padding:15px;margin:20px 0}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:8px;text-align:left;border-bottom:1px solid #dce5dc}
th{background:#edf3eb}.source{font-size:12px;color:#3d6648}
.notes{margin:0;padding:16px 20px;background:#f0f3ed;font-size:13px}
.notes strong{margin-left:8px}.notes strong:first-child{margin-left:0}
footer{font-size:12px;color:#586b5e;padding:15px 0}
summary:focus-visible,a:focus-visible{outline:3px solid #b77917}
@media(max-width:820px){.pair{grid-template-columns:1fr}main{padding:0 12px}
header{padding:20px}summary span{float:none;display:block}article{padding:16px}}
</style></head><body><header><h1>Final writer: before and after</h1>
<p>Same saved designs and numbers. Only the final writing step rerun.</p>
<p>Exact model outputs; neither column has been edited for display.</p></header><main>
<div class="rules"><span>Plain, precise language</span>
<span>Clear goal, open method</span><span>Show and explain thinking</span></div>"""
        + "".join(sections)
        + f"<footer>Word count: {totals[0]} before, {totals[1]} after across "
        f"{len(sections)} saved cases. Counts include title, body, question and data; "
        "standalone Markdown separators are excluded. Shorter is not automatically better. "
        "Content notes are an assistant inspection, not independent human ratings. "
        "No student learning or approach-diversity outcomes were measured.</footer>"
        "</main></body></html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rendered = render_comparison(json.loads(args.audit.read_text(encoding="utf-8")))
    with args.output.open("x", encoding="utf-8") as output:
        output.write(rendered)


if __name__ == "__main__":
    main()
