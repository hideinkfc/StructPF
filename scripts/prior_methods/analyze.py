"""Compute benchmark metrics and the pre-registered verdict.

Joins generations.jsonl + plausibility.jsonl + matching.jsonl and computes,
per model and per concept set (core / extended):
- error-recall @ dominant errors (>= 10% pick rate), with 5%/15% sensitivity
- non-confabulation rate (derived verdicts)
- plausibility mean (0-2)
- concept-leakage rate (concept_overlap share)

Derived verdict classes (no LLM at analysis time):
  concept_overlap=True                    -> target_concept
  matched_error_index != null             -> matches_documented_error
  no match, plausibility >= 1             -> valid_undocumented_strategy
  no match, plausibility == 0             -> confabulation

Verdict is read against the thresholds in
docs/pf-generation/PRIOR_METHODS_BENCHMARK.md section 7.

Usage:
  ./.venv/bin/python scripts/prior_methods/analyze.py \
      --results-dir experiments/results/prior_methods_benchmark/<date>_generation_v3
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prior_methods.common import ROOT, load_packages  # noqa: E402

CORE = {"c4_partwhole", "c5_commonbasis"}

# Pre-registered thresholds (benchmark doc section 7). Do not adjust after running.
RECALL_PASS = 0.6
NONCONFAB_PASS = 0.7
NONCONFAB_RECALL_ONLY = 0.4
PLAUSIBILITY_PASS = 1.4
DOMINANT_PCT = 10


def derive_class(overlap, matched_idx, score):
    if overlap:
        return "target_concept"
    if matched_idx is not None:
        return "matches_documented_error"
    if score is not None and score >= 1:
        return "valid_undocumented_strategy"
    return "confabulation"


def recall_at(matched_error_keys, package, threshold_pct):
    """Fraction of error rules with pick rate >= threshold covered by >=1 candidate.

    matched_error_keys: set of matched all_errors indices for this concept+model.
    """
    dominant = [i for i, e in enumerate(package["all_errors"])
                if e["pct_students"] >= threshold_pct]
    if not dominant:
        return None, 0
    covered = sum(1 for i in dominant if i in matched_error_keys)
    return covered / len(dominant), len(dominant)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    rd = args.results_dir if args.results_dir.is_absolute() else ROOT / args.results_dir

    packages = load_packages()
    plaus = {}
    for line in (rd / "plausibility.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            plaus[(r["concept_id"], r["model_label"], r["repeat"], r["method_index"])] = r
    match = {}
    for line in (rd / "matching.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            match[(r["concept_id"], r["model_label"], r["repeat"], r["method_index"])] = r

    gens = []
    for line in (rd / "generations.jsonl").read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            if rec.get("status") == "ok":
                gens.append(rec)

    # Per (concept, model): collect candidates
    by_cm = {}
    for g in gens:
        key = (g["concept_id"], g["model_label"])
        by_cm.setdefault(key, []).append(g)

    rows = []
    for (cid, model), gen_list in sorted(by_cm.items()):
        pkg = packages[cid]
        classes = []
        scores = []
        overlaps = 0
        matched_error_indices = set()
        n_matched_methods = 0
        per_list_recalls = []
        per_list_error_sets = []
        for g in gen_list:
            list_matched = set()
            for m_idx, _ in enumerate(g.get("methods", [])):
                k = (cid, model, g["repeat"], m_idx)
                p = plaus.get(k, {})
                mt = match.get(k, {})
                overlap = bool(p.get("concept_overlap"))
                score = p.get("score") if p.get("parse_ok") else None
                matched_idx = mt.get("matched_error_index") if mt.get("parse_ok") else None
                overlaps += overlap
                if score is not None:
                    scores.append(score)
                if matched_idx is not None:
                    matched_error_indices.add(matched_idx)
                    list_matched.add(matched_idx)
                    n_matched_methods += 1
                classes.append(derive_class(overlap, matched_idx, score))
            per_list_error_sets.append(list_matched)
            list_recall, _ = recall_at(list_matched, pkg, DOMINANT_PCT)
            if list_recall is not None:
                per_list_recalls.append(list_recall)

        n = len(classes)
        recall, n_dom = recall_at(matched_error_indices, pkg, DOMINANT_PCT)
        recall5, _ = recall_at(matched_error_indices, pkg, 5)
        recall15, _ = recall_at(matched_error_indices, pkg, 15)

        # Redundancy: distinct documented errors reached per matched method.
        # 1.0 = every match is a different error; 0.2 = five methods restate one error.
        distinct_ratio = (len(matched_error_indices) / n_matched_methods
                          if n_matched_methods else None)

        # Stability: mean pairwise Jaccard of the matched-error sets across repeats.
        # 1.0 = repeats find the same errors; 0.0 = disjoint (generation is a lottery).
        pairs = []
        for i in range(len(per_list_error_sets)):
            for j in range(i + 1, len(per_list_error_sets)):
                union = per_list_error_sets[i] | per_list_error_sets[j]
                if union:
                    inter = per_list_error_sets[i] & per_list_error_sets[j]
                    pairs.append(len(inter) / len(union))
        stability = mean(pairs) if pairs else None

        rows.append({
            "concept_id": cid,
            "set": "core" if cid in CORE else "extended",
            "model": model,
            "n_candidates": n,
            "plausibility_mean": round(mean(scores), 3) if scores else None,
            "concept_overlap_rate": round(overlaps / n, 3) if n else None,
            "error_recall_10": round(recall, 3) if recall is not None else None,
            "error_recall_5": round(recall5, 3) if recall5 is not None else None,
            "error_recall_15": round(recall15, 3) if recall15 is not None else None,
            "error_recall_per_list": (round(mean(per_list_recalls), 3)
                                      if per_list_recalls else None),
            "n_dominant_errors": n_dom,
            "n_matched_methods": n_matched_methods,
            "n_distinct_errors_reached": len(matched_error_indices),
            "distinct_per_matched": round(distinct_ratio, 3) if distinct_ratio else None,
            "repeat_stability": round(stability, 3) if stability is not None else None,
            "class_counts": {c: classes.count(c) for c in
                             ("matches_documented_error", "valid_undocumented_strategy",
                              "confabulation", "target_concept")},
        })

    def agg(subset):
        def m(key):
            vals = [r[key] for r in subset if r[key] is not None]
            return round(mean(vals), 3) if vals else None
        return {
            "n_concepts": len(subset),
            "candidates": sum(r["n_candidates"] for r in subset),
            "plausibility_mean": m("plausibility_mean"),
            "error_recall_10": m("error_recall_10"),
            "error_recall_per_list": m("error_recall_per_list"),
            "distinct_per_matched": m("distinct_per_matched"),
            "repeat_stability": m("repeat_stability"),
            "concept_overlap_rate": m("concept_overlap_rate"),
        }

    verdicts = {}
    for model in sorted({r["model"] for r in rows}):
        for setname in ("core", "extended"):
            subset = [r for r in rows if r["model"] == model and r["set"] == setname]
            if not subset:
                continue
            a = agg(subset)
            rec, pl = a["error_recall_10"], a["plausibility_mean"]
            if rec is not None and rec >= RECALL_PASS and pl is not None \
                    and pl >= PLAUSIBILITY_PASS:
                verdict = "C_valid_primary_source"
            elif rec is not None and rec < RECALL_PASS and pl is not None \
                    and pl >= PLAUSIBILITY_PASS:
                # Plausible student methods, but they are naive strategies rather than
                # the documented high-frequency misconceptions.
                verdict = "strategy_heavy_low_misconception_recall"
            elif rec is not None and rec < RECALL_PASS:
                verdict = "C_cannot_supply_demote"
            else:
                verdict = "inconclusive"
            verdicts[f"{model}/{setname}"] = {**a, "verdict": verdict}

    out = {
        "thresholds": {"recall_pass": RECALL_PASS,
                       "plausibility_pass": PLAUSIBILITY_PASS, "dominant_pct": DOMINANT_PCT},
        "metric_notes": {
            "error_recall_10": (
                "distinct dominant errors (>=10% pick rate) covered, pooled over repeats"),
            "error_recall_per_list": "same, but for a single 10-method list (what a user sees)",
            "distinct_per_matched": (
                "distinct errors reached / matched methods; low = redundant paraphrases"),
            "repeat_stability": "mean pairwise Jaccard of matched-error sets across repeats",
        },
        "per_concept": rows,
        "aggregate": verdicts,
    }
    out_path = rd / "analysis.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print(f"{'concept':16s} {'set':8s} {'model':9s} {'plaus':>6s} {'rec10':>6s} "
          f"{'recList':>7s} {'dist/m':>7s} {'stabil':>7s} {'overlap':>7s}")
    for r in rows:
        print(f"{r['concept_id']:16s} {r['set']:8s} {r['model']:9s} "
              f"{str(r['plausibility_mean']):>6s} {str(r['error_recall_10']):>6s} "
              f"{str(r['error_recall_per_list']):>7s} {str(r['distinct_per_matched']):>7s} "
              f"{str(r['repeat_stability']):>7s} {str(r['concept_overlap_rate']):>7s}")
    print("\nAggregate verdicts:")
    for k, v in verdicts.items():
        print(f"  {k}: recall={v['error_recall_10']} perList={v['error_recall_per_list']} "
              f"plaus={v['plausibility_mean']} distinct/matched={v['distinct_per_matched']} "
              f"stability={v['repeat_stability']} -> {v['verdict']}")
    print(f"\nsaved -> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
