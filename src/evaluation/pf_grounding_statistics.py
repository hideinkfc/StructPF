"""Paired descriptive analysis with task-specification blocks, not learner claims."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


def exact_sign_test(wins: int, losses: int) -> float | None:
    if type(wins) is not int or type(losses) is not int or min(wins, losses) < 0:
        raise ValueError("Wins and losses must be nonnegative integers")
    n = wins + losses
    if not n:
        return None
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2**n)


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("A percentile requires values and a probability in [0, 1]")
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def paired_block_summary(
    records: Sequence[Mapping[str, Any]],
    *,
    treatment: str,
    baseline: str,
    bootstrap_samples: int = 5000,
    seed: int = 20261013,
) -> dict[str, Any]:
    """Summarize same-request outcomes; retain unknowns and resample whole cases."""
    if not treatment or not baseline or treatment == baseline:
        raise ValueError("Two distinct nonempty arms are required")
    if type(bootstrap_samples) is not int or bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be a positive integer")
    slots: dict[tuple[str, int], dict[str, bool | None]] = defaultdict(dict)
    availability: dict[tuple[str, int, str], str] = {}
    reasons: dict[tuple[str, int, str], str] = {}
    for record in records:
        arm = record.get("arm")
        if arm not in (treatment, baseline):
            continue
        case = record.get("case_id")
        repeat = record.get("repeat")
        outcome = record.get("outcome")
        if not isinstance(case, str) or not case.strip():
            raise ValueError("Every record requires a nonempty case_id")
        if type(repeat) is not int or repeat < 0:
            raise ValueError("Every repeat must be a nonnegative integer")
        if outcome is not None and type(outcome) is not bool:
            raise ValueError("outcome must be true, false, or null")
        if "outcome" not in record:
            raise ValueError("A missing outcome must be explicitly null")
        state = record.get("availability", "available")
        if state not in ("available", "task_unavailable", "audit_unavailable"):
            raise ValueError(
                "availability must distinguish available, task, or audit unavailability"
            )
        if state != "available":
            reason = record.get("unavailability_reason")
            if outcome is not None or not isinstance(reason, str) or not reason.strip():
                raise ValueError("Unavailable records require a null outcome and explicit reason")
            reasons[(case, repeat, arm)] = reason
        pair = slots[(case, repeat)]
        if arm in pair:
            raise ValueError(f"Duplicate paired record: {case}/{repeat}/{arm}")
        pair[arm] = outcome
        availability[(case, repeat, arm)] = state
    if not slots:
        raise ValueError("No records for the requested arms")
    incomplete = [
        f"{case}/{repeat}" for (case, repeat), pair in slots.items() if len(pair) != 2
    ]
    if incomplete:
        raise ValueError(f"Missing scheduled arm records: {', '.join(incomplete)}")

    blocks: dict[str, list[tuple[int, dict[str, bool | None]]]] = defaultdict(list)
    for (case, repeat), pair in slots.items():
        blocks[case].append((repeat, pair))
    per_case = []
    for case, block in sorted(blocks.items()):
        pairs = [pair for _, pair in block]
        n = len(pairs)
        arm_counts = {}
        for arm in (treatment, baseline):
            arm_counts[arm] = {
                "supported": sum(pair[arm] is True for pair in pairs),
                "not_supported": sum(pair[arm] is False for pair in pairs),
                "unknown": sum(
                    pair[arm] is None and availability[(case, repeat, arm)] == "available"
                    for repeat, pair in block
                ),
                "task_unavailable": sum(
                    availability[(case, repeat, arm)] == "task_unavailable"
                    for repeat, _ in block
                ),
                "audit_unavailable": sum(
                    availability[(case, repeat, arm)] == "audit_unavailable"
                    for repeat, _ in block
                ),
            }
        t = arm_counts[treatment]
        b = arm_counts[baseline]
        t_unknown = t["unknown"] + t["audit_unavailable"]
        b_unknown = b["unknown"] + b["audit_unavailable"]
        per_case.append(
            {
                "case_id": case,
                "scheduled_pairs": n,
                "arms": arm_counts,
                "both_supported": sum(
                    pair[treatment] is True and pair[baseline] is True for pair in pairs
                ),
                "both_not_supported": sum(
                    pair[treatment] is False and pair[baseline] is False for pair in pairs
                ),
                "treatment_only": sum(
                    pair[treatment] is True and pair[baseline] is False for pair in pairs
                ),
                "baseline_only": sum(
                    pair[treatment] is False and pair[baseline] is True for pair in pairs
                ),
                "unresolved_pairs": sum(
                    pair[treatment] is None or pair[baseline] is None for pair in pairs
                ),
                "unavailability_records": [
                    {
                        "repeat": repeat,
                        "arm": arm,
                        "availability": availability[(case, repeat, arm)],
                        "reason": reasons[(case, repeat, arm)],
                    }
                    for repeat, _ in block
                    for arm in (treatment, baseline)
                    if availability[(case, repeat, arm)] != "available"
                ],
                "supported_rate_difference": (t["supported"] - b["supported"]) / n,
                "unknown_sensitivity_bounds": [
                    (t["supported"] - b["supported"] - b_unknown) / n,
                    (t["supported"] + t_unknown - b["supported"]) / n,
                ],
            }
        )
    differences = [case["supported_rate_difference"] for case in per_case]
    rng = random.Random(seed)
    draws = [
        sum(rng.choices(differences, k=len(differences))) / len(differences)
        for _ in range(bootstrap_samples)
    ]
    positive = sum(value > 0 for value in differences)
    negative = sum(value < 0 for value in differences)
    return {
        "treatment": treatment,
        "baseline": baseline,
        "scheduled_pairs": len(slots),
        "task_specifications": len(per_case),
        "per_case": per_case,
        "equal_case_weighted_supported_rate_difference": sum(differences) / len(differences),
        "equal_case_weighted_unknown_sensitivity_bounds": [
            sum(case["unknown_sensitivity_bounds"][side] for case in per_case) / len(per_case)
            for side in (0, 1)
        ],
        "target_block_bootstrap": {
            "samples": bootstrap_samples,
            "seed": seed,
            "interval_95": [_percentile(draws, 0.025), _percentile(draws, 0.975)],
            "interpretation": (
                "Exploratory task-specification-block interval; few blocks give unstable "
                "uncertainty. Unknown is not classified as mathematical or educational failure."
            ),
        },
        "case_signs": {
            "positive": positive,
            "negative": negative,
            "ties": len(differences) - positive - negative,
            "descriptive_two_sided_p": exact_sign_test(positive, negative),
            "independence_boundary": (
                "Cases may share broader topics; this is not proof of task-family generalization."
            ),
        },
        "scope": "Model-audit supported-outcome rates, not human-validated PF or learning",
        "missingness": (
            "Task unavailability is missing delivery, not a judged task flaw; audit "
            "unavailability enters uncertainty bounds but is reported separately from "
            "substantive unknown judgments."
        ),
    }
