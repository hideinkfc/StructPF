"""Report source-category coverage without equating it with learner fidelity."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_pf_paper_benchmark as benchmark  # noqa: E402

CATEGORY_LABELS = {
    "hady_walks_more": "Faster friend should walk more (insight)",
    "complementary_distances": "Complementary journey distances (insight)",
    "diagram": "Journey/partition diagram (representation)",
    "lcm_hcf": "Common multiple/factor strategy",
    "ratios": "Ratio-based partition",
    "trial_bruteforce": "Numerical trial and checking",
    "trial_ratio_informed": "Ratio-informed trial and checking",
    "algebra_multiple_variables": "Multiple-variable algebra",
    "algebra_single_variable": "Single-variable algebra",
}
ALGORITHMS = tuple(list(CATEGORY_LABELS)[3:])


def response_text(entry: dict) -> str:
    if entry["response_type"] == "attempt" and isinstance(entry["output"], dict):
        return entry["output"]["written_work"] + "\n" + entry["output"]["answer"]
    return entry["raw_text"]


def validate_coding(payload: dict, packet: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"provenance", "responses"}:
        raise ValueError("Reference coding requires provenance and responses")
    if set(payload["responses"]) != set(packet):
        raise ValueError("Reference coding must cover every fresh response")
    for label, row in payload["responses"].items():
        if set(row) != {
            "categories",
            "mentioned_only",
            "evidence",
            "unsuccessful_work",
            "unsuccessful_evidence",
            "final_result",
            "rationale",
        }:
            raise ValueError(f"Unexpected reference coding fields: {label}")
        for field in ("categories", "mentioned_only"):
            items = row[field]
            if (
                not isinstance(items, list)
                or set(items) - set(CATEGORY_LABELS)
                or len(set(items)) != len(items)
            ):
                raise ValueError(f"Unknown or repeated source category: {label}")
        if set(row["categories"]) & set(row["mentioned_only"]):
            raise ValueError("An applied category cannot also be mention-only")
        if not isinstance(row["evidence"], dict) or set(row["evidence"]) != set(row["categories"]):
            raise ValueError("Every applied or predicted category requires evidence")
        text = response_text(packet[label])
        for category, quotes in row["evidence"].items():
            _quotes(quotes, text, required=True)
        if row["unsuccessful_work"] not in {"yes", "no", "unknown"}:
            raise ValueError("Unknown unsuccessful-work classification")
        _quotes(row["unsuccessful_evidence"], text, required=row["unsuccessful_work"] == "yes")
        if row["final_result"] not in {
            "correct",
            "incorrect",
            "unfinished",
            "not_applicable",
            "unknown",
        }:
            raise ValueError("Unknown final-result classification")
        if (
            packet[label]["response_type"] == "prediction"
            and row["final_result"] != "not_applicable"
        ):
            raise ValueError("A prediction is not a completed learner solution")
        if not isinstance(row["rationale"], str) or not row["rationale"].strip():
            raise ValueError("Reference coding needs a rationale")
    return payload


def _quotes(quotes: object, text: str, *, required: bool) -> None:
    if not isinstance(quotes, list) or (required and not quotes):
        raise ValueError("Reference classification requires source quotations")
    if any(
        not isinstance(quote, str) or not quote.strip() or quote not in text for quote in quotes
    ):
        raise ValueError("Reference quote does not match written output")


def exact_check() -> dict:
    distance = Fraction(5000)
    x = (distance / 200 - distance / 30) / (
        Fraction(1, 150) - Fraction(1, 30) - Fraction(1, 50) + Fraction(1, 200)
    )
    mira = x / 150 + (distance - x) / 30
    leon = x / 50 + (distance - x) / 200
    if mira != leon or not 0 < x < distance or not x / 150 < x / 50:
        raise ValueError("Normalized reference task fails independent feasibility check")
    return {
        "handover_metres": str(x),
        "mira_minutes": str(mira),
        "leon_minutes": str(leon),
        "bike_available_before_leon_arrives": True,
        "scope": (
            "Exact arithmetic for the normalized constant-rate task, not an original worksheet."
        ),
    }


def summarize(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Reference run must finish before summarizing")
    packet = json.loads((output / "review_packet.json").read_text())
    key = json.loads((output / "review_key.json").read_text())
    coding = validate_coding(json.loads((output / "pathway_coding.json").read_text()), packet)
    requests = {row["id"]: row for row in manifest["requests"]}
    result_paths = {row["id"]: row["result_path"] for row in manifest["results"]}
    fresh = {row["id"] for row in requests.values() if row["phase"] == "fresh"}
    if set(key) != set(packet) or set(key.values()) != fresh or len(key.values()) != len(fresh):
        raise ValueError("Reference key must identify every fresh request exactly once")
    groups, profiles = {}, {}
    rows = {}
    for label, row in coding["responses"].items():
        request = requests[key[label]]
        kind = request["kind"]
        counts = groups.setdefault(kind, Counter())
        profile = profiles.setdefault(f"{request['profile']}/{request['model']}", Counter())
        for bucket in (counts, profile):
            bucket["responses"] += 1
            bucket[f"final/{row['final_result']}"] += 1
            if kind != "prediction":
                bucket[f"unsuccessful_work/{row['unsuccessful_work']}"] += 1
            for category in row["categories"]:
                bucket[f"category/{category}"] += 1
            for category in row["mentioned_only"]:
                bucket[f"mention/{category}"] += 1
        rows[key[label]] = {**row, "anonymous_id": label, "kind": kind}
    execution = {"calibration": Counter(), "fresh": Counter()}
    usage = {"calibration": Counter(), "fresh": Counter()}
    for request in requests.values():
        result = json.loads((output / result_paths[request["id"]]).read_text())
        bucket = execution[request["phase"]]
        bucket["responses"] += 1
        bucket[result["status"]] += 1
        trace = output / result_paths[request["id"]].replace("result.json", "model_calls.jsonl")
        stats = benchmark._trace_stats(trace)
        if stats["calls"] != 1 or stats["finished"] != 1 or stats["malformed_lines"]:
            raise ValueError("Reference trace has missing/extra request records")
        bucket["calls"] += stats["calls"]
        bucket["api_errors"] += stats["errors"]
        if stats["usage"] is not None:
            usage[request["phase"]].update(stats["usage"])
    result = {
        "question": manifest["protocol"]["question"],
        "provenance": coding["provenance"],
        "groups": {kind: dict(counts) for kind, counts in groups.items()},
        "profiles": {kind: dict(counts) for kind, counts in profiles.items()},
        "execution": {phase: dict(counts) for phase, counts in execution.items()},
        "usage": {phase: dict(counts) for phase, counts in usage.items()},
        "exact_check": exact_check(),
        "category_coverage": {
            kind: {
                "all_reference_categories": sum(
                    counts.get(f"category/{c}", 0) > 0 for c in CATEGORY_LABELS
                ),
                "algorithm_categories": sum(counts.get(f"category/{c}", 0) > 0 for c in ALGORITHMS),
                "warning": "Union presence is not a human classroom probability or quality score.",
            }
            for kind, counts in groups.items()
        },
        "responses": rows,
        "limitations": manifest["protocol"]["limits"],
    }
    verification_path = output / "coding_verification.json"
    if verification_path.exists():
        result["coding_verification"] = json.loads(verification_path.read_text())
    benchmark._write_json(output / "summary.json", result)
    benchmark._write_json(output / "exact_check.json", result["exact_check"])
    render(output, result, packet, key)
    return result


def render(output: Path, summary: dict, packet: dict, key: dict) -> None:
    table = []
    for category, label in CATEGORY_LABELS.items():
        table.append(
            "<tr><td>"
            + label
            + "</td>"
            + "".join(
                f"<td>{summary['groups'][kind].get(f'category/{category}', 0)}/"
                f"{summary['groups'][kind]['responses']}</td>"
                for kind in ("learner", "solver", "prediction")
            )
            + "</tr>"
        )
    panels = []
    for label, entry in packet.items():
        row = summary["responses"][key[label]]
        panels.append(
            "<details><summary>"
            + html.escape(f"{row['kind']} / {label} / {row['final_result']}")
            + "</summary><p><b>Categories:</b> "
            + html.escape(", ".join(row["categories"]))
            + "</p><p>"
            + html.escape(row["rationale"])
            + "</p><pre>"
            + html.escape(response_text(entry))
            + "</pre></details>"
        )
    task = json.loads((output / "manifest.json").read_text())["protocol"]["task"]
    learners = summary["groups"]["learner"]
    solvers = summary["groups"]["solver"]
    overview = (
        "<h2>What happened in the written attempts</h2><p>Learners used single-variable "
        f"algebra in {learners.get('category/algebra_single_variable', 0)}/"
        f"{learners['responses']} attempts, and actual numerical trial-and-error in "
        f"{learners.get('category/trial_bruteforce', 0)}/{learners['responses']}. "
        "One response used both, so these counts overlap.</p>"
        f"<p>{learners.get('final/correct', 0)} learner attempts finished correctly, "
        f"{learners.get('final/unfinished', 0)} stopped unfinished and "
        f"{learners.get('final/incorrect', 0)} retained an incorrect answer. "
        f"{solvers.get('final/correct', 0)}/{solvers['responses']} ordinary solvers "
        "used correct algebra. No actual ratio-partition, LCM-partition or diagram "
        "appeared, although prediction-only responses anticipated them.</p>"
        "<p><b>Conclusion:</b> the learner prompt can produce exploratory trials as "
        "well as direct solutions, but coverage is narrower than the published "
        "group methods. This neither validates a realistic class nor proves that "
        "the simulator is incapable of useful task diagnosis.</p>"
    )
    bars = []
    for index, (category, label) in enumerate(
        (
            ("algebra_single_variable", "Single-variable algebra"),
            ("trial_bruteforce", "Numerical trial and checking"),
            ("ratios", "Ratio partition"),
            ("lcm_hcf", "LCM/HCF partition"),
        )
    ):
        count = learners.get(f"category/{category}", 0)
        y = 18 + 44 * index
        bars.append(
            f"<text x='10' y='{y + 18}'>{label}</text>"
            f"<rect x='280' y='{y}' width='400' height='25' fill='#dfe7ee'/>"
            f"<rect x='280' y='{y}' width='{400 * count / learners['responses']}' "
            f"height='25' fill='#3276a5'/>"
            f"<text x='700' y='{y + 18}'>{count}/{learners['responses']} attempts</text>"
        )
    chart = (
        "<svg viewBox='0 0 920 202' role='img' style='width:100%;font:16px system-ui' "
        "aria-label='Actual algorithm coverage in24 model learner attempts'>"
        + "".join(bars)
        + "</svg>"
        "<p>Measured written model outputs. Algebra and trials overlap in one reply. "
        "These are not observed human-student frequencies.</p>"
    )
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Kapur reference: which paths do LLM learners take?</title><style>"
        "body{font:17px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:0 24px;"
        "background:#f5f7fa;color:#233448}pre{white-space:pre-wrap;font:inherit}"
        "td,th{border:1px solid #ccd6df;padding:10px;text-align:left}"
        "table{border-collapse:collapse;width:100%}details{background:white;padding:14px;"
        "margin:12px 0;border:1px solid #ccd6df}summary{cursor:pointer;font-weight:bold}</style>"
        "<h1>Can simulated learners reach the pathways observed in the Kapur study?</h1>"
        "<p>24 unprompted learner attempts, four ordinary-solver controls and two "
        "prediction-only responses. Four execution controls are separate. "
        "The nine category names were kept out of model prompts.</p>"
        + overview
        + chart
        + "<details><summary>Source-normalized task, not the original worksheet</summary><pre>"
        + html.escape(task["title"] + "\n\n" + task["body"] + "\n\n" + task["question"])
        + "</pre></details><h2>Source-category coverage</h2><table>"
        "<tr><th>Category documented in real group work</th><th>Learner attempts</th>"
        "<th>Ordinary solvers</th><th>Predictions only</th></tr>" + "".join(table) + "</table>"
        "<p>These count written model responses containing each category, not real "
        "student frequencies. Predictions anticipate categories; they do not perform "
        "them. Insights and diagrams are not extra algorithms. Failed intermediate "
        "guesses, failed final solutions and lack of a method are different outcomes.</p>"
        "<p>Published group exploration, normalized individual responses and potentially "
        "memorized tasks are not equivalent experimental conditions. Missing paths "
        "alone cannot prove simulator incompetence or bad task design; coverage alone "
        "cannot validate a realistic class distribution.</p>"
        "<p><a href='summary.json'>Counts and limitations</a> &middot; "
        "<a href='coding_verification.json'>Category correction and evidence checks</a> &middot; "
        "<a href='pathway_coding.json'>Anonymous source-quoted coding</a></p>"
        + "".join(panels)
        + "</html>"
    )
    (output / "reference.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.output)
    print(json.dumps({key: result[key] for key in ("groups", "category_coverage")}, indent=2))
