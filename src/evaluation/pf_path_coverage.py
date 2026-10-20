"""Operational intended-path diagnostics with evidence and honest denominators."""

import math

STATUSES = {"reached", "not_observed", "unknown"}
KINDS = {"algorithm", "insight", "representation", "compound"}


def source_text(entry: dict) -> str:
    attempt = entry.get("attempt")
    return (
        attempt["written_work"] + "\n" + attempt["answer"]
        if isinstance(attempt, dict)
        else entry.get("unparsed_raw_text") or entry.get("raw_text") or ""
    )


def validate_path(path: dict, attempts: dict, design_text: str) -> dict:
    if path.get("kind") not in KINDS:
        raise ValueError("Unknown intended-path kind")
    quote = path.get("design_quote")
    if not isinstance(quote, str) or not quote.strip() or quote not in design_text:
        raise ValueError("Intended-path quote does not match the saved design")
    definition = path.get("operational_definition")
    if not isinstance(definition, str) or not definition.strip():
        raise ValueError("A path needs a frozen mathematical-action definition")
    rows = path.get("attempts")
    if not isinstance(rows, dict) or set(rows) != set(attempts):
        raise ValueError("Path assessment must cover every scheduled attempt")
    for label, row in rows.items():
        if row.get("status") not in STATUSES:
            raise ValueError("Unknown intended-path reachability")
        if "phase" in row and row["phase"] not in {
            "attempted",
            "successful",
            "unsuccessful",
            "unknown",
        }:
            raise ValueError("Unknown intended-path execution phase")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or (row["status"] == "reached" and not evidence):
            raise ValueError("A reached path requires an exact attempt quotation")
        for item in evidence:
            if (
                not isinstance(item, str)
                or not item.strip()
                or item not in source_text(attempts[label])
            ):
                raise ValueError("Path evidence does not match the saved attempt")
    return path


def path_counts(path: dict) -> dict:
    rows = path["attempts"]
    return {
        "attempted": len(rows),
        **{status: sum(row["status"] == status for row in rows.values()) for status in STATUSES},
        "reached_successful": sum(
            row["status"] == "reached" and row.get("phase") == "successful" for row in rows.values()
        ),
        "reached_unsuccessful": sum(
            row["status"] == "reached" and row.get("phase") == "unsuccessful"
            for row in rows.values()
        ),
        "interpretation": (
            "Not-observed is not an inability or a human probability; unknown is separate."
        ),
    }


def weighted_path_rate(rows: dict, profiles: dict, weights: dict) -> dict:
    if not weights or any(
        isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0
        for w in weights.values()
    ):
        raise ValueError("Assumed profile weights must be nonnegative numbers")
    if abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("Assumed profile weights must sum to one")
    by_profile = {}
    for profile, weight in weights.items():
        subset = [row for label, row in rows.items() if profiles[label] == profile]
        if not subset:
            raise ValueError("An assumed profile has no observed attempts")
        by_profile[profile] = {
            "weight": weight,
            "attempted": len(subset),
            "reached": sum(row["status"] == "reached" for row in subset),
            "unknown": sum(row["status"] == "unknown" for row in subset),
        }
    lower = sum(
        value["weight"] * value["reached"] / value["attempted"] for value in by_profile.values()
    )
    upper = sum(
        value["weight"] * (value["reached"] + value["unknown"]) / value["attempted"]
        for value in by_profile.values()
    )
    return {
        "assumed_weights": weights,
        "weighted_observed_reach": lower,
        "weighted_reach_if_unknowns_reach": upper,
        "profile_counts": by_profile,
        "interpretation": (
            "Assumed-mixture sensitivity, not fitted classroom distribution or forecast."
        ),
    }
