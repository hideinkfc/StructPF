"""Concrete design data and evidence, without the legacy mathematical-plan schema."""

from __future__ import annotations

import math
import re
from collections import Counter
from decimal import Decimal
from typing import Any

NUMBER = re.compile(r"(?<![\w.])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![\w.])")


def value_numerals(value: int | float | list) -> Counter:
    if isinstance(value, list):
        return sum((value_numerals(item) for item in value), Counter())
    return Counter({Decimal(str(value)): 1})


def text_numerals(text: str) -> Counter:
    return Counter(Decimal(token) for token in NUMBER.findall(text))


def _name(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]*", value) is not None


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _number_shape(value: object) -> object:
    if isinstance(value, list) and value:
        return tuple(_number_shape(item) for item in value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("values must contain finite numbers or non-empty lists of numbers")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("values must be finite")
    return None


def validate_values(
    values: object, quantities: dict, previous: dict | None = None
) -> dict[str, Any]:
    if not isinstance(values, dict) or set(values) != set(quantities):
        raise ValueError("values must have exactly the declared quantity names")
    for name, value in values.items():
        shape = _number_shape(value)
        if previous is not None and shape != _number_shape(previous[name]):
            raise ValueError(f"repair changed the number of entries in {name}")
    return values


def proposal_from_payload(
    payload: object, requirements: list[str], *, require_roles: bool = False
) -> dict:
    """Validate the model boundary and retain every original design requirement."""
    if not isinstance(payload, dict) or set(payload) != {"quantities", "values", "conditions"}:
        raise ValueError("proposal requires exactly quantities, values, and conditions")
    quantities = payload["quantities"]
    if not isinstance(quantities, dict) or not quantities:
        raise ValueError("quantities must be a non-empty object")
    for name, metadata in quantities.items():
        if not _name(name):
            raise ValueError(f"invalid quantity name: {name!r}")
        if (
            not isinstance(metadata, dict)
            or not {"description", "unit"}.issubset(metadata)
            or set(metadata) - {"description", "unit", "role"}
        ):
            raise ValueError(f"{name} requires description, unit, and optional role")
        _text(metadata["description"], f"{name}.description")
        _text(metadata["unit"], f"{name}.unit (use 'unitless' where appropriate)")
        if require_roles and "role" not in metadata:
            raise ValueError(f"{name}.role is required for new proposals")
        if "role" in metadata and metadata["role"] not in ("given", "teacher_example"):
            raise ValueError(f"{name}.role must be given or teacher_example")
    validate_values(payload["values"], quantities)
    conditions = payload["conditions"]
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("conditions must be a non-empty list")
    covered = set()
    for condition in conditions:
        required = {"statement", "requirement_indices", "essential", "calculation", "reasoning"}
        if (
            not isinstance(condition, dict)
            or not required.issubset(condition)
            or set(condition) - required - {"judgment"}
        ):
            raise ValueError(
                "each condition requires statement, requirement_indices, essential, "
                "calculation, and reasoning"
            )
        _text(condition["statement"], "condition.statement")
        _text(condition["reasoning"], "condition.reasoning")
        indices = condition["requirement_indices"]
        if not isinstance(indices, list) or any(
            type(index) is not int or not 0 <= index < len(requirements) for index in indices
        ):
            raise ValueError("requirement_indices must reference the supplied requirements")
        if not isinstance(condition["essential"], bool) or (indices and not condition["essential"]):
            raise ValueError("conditions linked to original requirements must be essential")
        covered.update(indices)
        calculation = condition["calculation"]
        if calculation is None:
            if condition.get("judgment") not in ("holds", "fails", "uncertain"):
                raise ValueError("a non-computed condition requires an explicit judgment")
        else:
            if (
                not isinstance(calculation, dict)
                or not {"expressions", "predicate"}.issubset(calculation)
                or set(calculation) - {"expressions", "predicate", "symbols"}
            ):
                raise ValueError(
                    "calculation requires expressions, predicate, and optional symbols"
                )
            expressions = calculation["expressions"]
            if not isinstance(expressions, dict) or any(
                not _name(name) or not isinstance(expr, str) or not expr.strip()
                for name, expr in expressions.items()
            ):
                raise ValueError("expressions must map valid names to non-empty formulas")
            _text(calculation["predicate"], "calculation.predicate")
    missing = set(range(len(requirements))) - covered
    if missing:
        raise ValueError(f"conditions omit original requirements: {sorted(missing)}")
    return payload


def check_proposal(proposal: dict) -> dict:
    from src.generation.design_calculator import calculate_condition

    evidence = []
    failures = []
    textual_failures = []
    unresolved = []
    warnings = []
    for index, condition in enumerate(proposal["conditions"]):
        calculation = condition["calculation"]
        if calculation is None:
            result = {
                "status": "model_judged" if condition["judgment"] != "uncertain" else "unverified",
                "computed": {},
                "reason": condition["reasoning"],
                "judgment": condition["judgment"],
            }
        else:
            result = calculate_condition(
                calculation,
                proposal["values"],
                units={name: metadata["unit"] for name, metadata in proposal["quantities"].items()},
            )
        evidence.append({"index": index, **condition, **result})
        detail = f"{condition['statement']}: {result['reason']}"
        failed = result["status"] == "fails" or (
            calculation is None and result["judgment"] == "fails"
        )
        if failed:
            if condition["essential"]:
                if calculation is None:
                    textual_failures.append(detail)
                else:
                    failures.append(condition["statement"])
            else:
                warnings.append(detail)
        elif result["status"] not in ("holds", "model_judged"):
            unresolved.append(detail)
            warnings.append(detail)
    status = "review_needed" if textual_failures else "rejected" if failures else "accepted"
    reasons = textual_failures or failures
    reason = "; ".join(reasons) if reasons else "No essential condition is known to fail."
    if warnings:
        reason += " Nonblocking warnings: " + "; ".join(warnings)
    return {
        "status": status,
        "accepted": status == "accepted",
        "conditions": evidence,
        "failures": failures,
        "textual_failures": textual_failures,
        "unresolved": unresolved,
        "warnings": warnings,
        "reason": reason,
    }
