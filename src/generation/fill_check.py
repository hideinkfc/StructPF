"""Exact arithmetic checks for a frozen D2 mathematical plan.

SymPy executes the expressions supplied by the plan. It does not decide whether
an expression is pedagogically meaningful; that correspondence is established
when the plan is reviewed. The legacy ``check_fill(payload)`` form remains
available for historical result inspection and uses a conservative largest-label
comparison.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any

from sympy import Abs, Expr, Integer, Rational, simplify

from src.generation.situation_skeletons import (
    ALLOWED_ANSWER_KINDS,
    ALLOWED_OPERATORS,
    ALLOWED_VALUE_DOMAINS,
    AnswerRule,
    FormulaPath,
    MathPlan,
    Quantity,
)


class FillCheckError(ValueError):
    """The fill or mathematical plan cannot be evaluated."""


@dataclass(frozen=True)
class PathResult:
    """Computed results for one labelled target or prior path."""

    name: str
    role: str
    values: dict[str, str]
    undefined: bool
    tied: bool
    argmax: tuple[str, ...]
    argmin: tuple[str, ...]
    error: str | None = None
    approach_id: str | None = None
    _computed: dict[str, Expr] = field(default_factory=dict, repr=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "values": dict(self.values),
            "undefined": self.undefined,
            "tied": self.tied,
            "argmax": list(self.argmax),
            "argmin": list(self.argmin),
            "error": self.error,
            "approach_id": self.approach_id,
        }


@dataclass(frozen=True)
class FillCheck:
    """The explicit result of checking a fill against a plan."""

    accepted: bool
    reason: str
    target: PathResult | None
    priors: tuple[PathResult, ...] = field(default_factory=tuple)
    status: str = "rejected"
    failures: tuple[str, ...] = field(default_factory=tuple)
    contrast_decisions: dict[str, bool] | None = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "reason": self.reason,
            "failures": list(self.failures),
            "target": None if self.target is None else self.target.to_dict(),
            "priors": [prior.to_dict() for prior in self.priors],
            "contrast_decisions": self.contrast_decisions,
        }

    def retry_feedback(self) -> str:
        if self.status == "needs_review":
            return (
                "The frozen mathematical plan needs review and cannot be repaired "
                "by changing numbers. Do not change its formulas or answer rule."
            )
        details = "; ".join(self.failures) if self.failures else self.reason
        return (
            f"Previous values were rejected: {details}. "
            "Return values only. Keep every expression, label, answer rule, and "
            "slot unchanged, and satisfy the declared constraints and any selected "
            "prior_contrast."
        )


def evaluate_formula(formula: str, values: dict[str, Any]) -> Expr:
    """Evaluate one restricted formula to an exact SymPy expression."""
    if not isinstance(formula, str) or not formula.strip():
        raise FillCheckError("formula is empty")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise FillCheckError(f"cannot parse {formula!r}") from exc
    return _eval_ast(tree.body, dict(values))


def check_fill(
    plan_or_payload: MathPlan | dict[str, Any],
    values: dict[str, Any] | None = None,
) -> FillCheck:
    """Check values against a frozen plan or a legacy formula-bearing payload.

    New callers pass ``check_fill(plan, values)``. Historical callers may pass
    the old ``{"values", "target", "priors"}`` payload; that form is converted
    to a conservative compatibility plan.
    """
    if isinstance(plan_or_payload, MathPlan):
        plan = plan_or_payload
        raw_values = values
    elif isinstance(plan_or_payload, dict):
        payload = plan_or_payload
        raw_values = values if values is not None else payload.get("values")
        try:
            plan = _legacy_plan_from_payload(payload, raw_values)
        except (FillCheckError, ValueError) as exc:
            return _reject(f"invalid mathematical plan: {exc}")
    else:
        return _reject("missing mathematical plan")

    plan_errors = validate_plan_expressions(plan)
    if plan_errors:
        return _review(
            "mathematical plan needs review: " + "; ".join(plan_errors),
            None,
            (),
        )
    if not isinstance(raw_values, dict) or not raw_values:
        return _reject("missing values")
    try:
        _validate_values(plan, raw_values)
    except FillCheckError as exc:
        return _reject(str(exc))
    unsupported = (
        []
        if plan.schema_version == "math-plan/v2"
        else [prior.name for prior in plan.priors if prior.checkability == "unsupported"]
    )
    if unsupported:
        return _review(
            "unsupported prior approaches require semantic review: " + ", ".join(unsupported),
            None,
            (),
        )

    try:
        target_result = _path_result(plan.target, "target", raw_values)
    except FillCheckError as exc:
        return _reject(f"target formulas cannot be read: {exc}")
    if target_result.undefined:
        return _reject(
            "the target path is undefined on these values",
            target=target_result,
            failures=(target_result.error or "undefined target",),
        )

    answer_error = _validate_target_decision(target_result, plan.answer_rule)
    if answer_error is not None:
        return _reject(answer_error, target=target_result, failures=(answer_error,))

    prior_results: list[PathResult] = []
    for prior in plan.priors if plan.schema_version != "math-plan/v2" else ():
        if prior.checkability == "qualitative":
            prior_results.append(
                PathResult(
                    name=prior.name,
                    role="prior",
                    values={},
                    undefined=False,
                    tied=False,
                    argmax=(),
                    argmin=(),
                    error="not numerically checked",
                    approach_id=prior.approach_id,
                )
            )
            continue
        try:
            result = _path_result(prior, "prior", raw_values)
        except FillCheckError as exc:
            return _reject(
                f"prior {prior.name!r} formulas cannot be read: {exc}",
                target=target_result,
                priors=tuple(prior_results),
            )
        prior_results.append(result)
        if result.undefined:
            reason = f"prior {prior.name!r} is undefined"
            return _reject(
                reason,
                target=target_result,
                priors=tuple(prior_results),
                failures=(result.error or reason,),
            )

    contrast_decisions = None
    if plan.prior_contrast is not None:
        try:
            contrast_result = _path_result(plan.prior_contrast, "prior_contrast", raw_values)
        except FillCheckError as exc:
            return _reject(
                f"selected prior contrast formulas cannot be read: {exc}",
                target=target_result,
                priors=tuple(prior_results),
            )
        prior_results.append(contrast_result)
        if contrast_result.undefined:
            reason = f"selected prior contrast {plan.prior_contrast.name!r} is undefined"
            return _reject(
                reason,
                target=target_result,
                priors=tuple(prior_results),
                failures=(contrast_result.error or reason,),
            )
        prior_decision = _path_decision(contrast_result, plan.answer_rule)
        target_decision = _path_decision(target_result, plan.answer_rule)
        if plan.answer_rule.kind == "equal":
            if (
                plan.prior_contrast_expected_target_equal is None
                or plan.prior_contrast_expected_prior_equal is None
            ):
                return _review(
                    "equal prior_contrast is missing its selected expected outcomes",
                    target_result,
                    tuple(prior_results),
                )
            contrast_decisions = {
                "target_equal": bool(target_decision[1]),
                "prior_equal": bool(prior_decision[1]),
                "expected_target_equal": plan.prior_contrast_expected_target_equal,
                "expected_prior_equal": plan.prior_contrast_expected_prior_equal,
            }
            if contrast_decisions["target_equal"] != contrast_decisions["expected_target_equal"]:
                reason = "target equality result differs from the selected prior_contrast design"
                return _reject(
                    reason,
                    target=target_result,
                    priors=tuple(prior_results),
                    failures=(reason,),
                    contrast_decisions=contrast_decisions,
                )
            if contrast_decisions["prior_equal"] != contrast_decisions["expected_prior_equal"]:
                reason = "prior equality result differs from the selected prior_contrast design"
                return _reject(
                    reason,
                    target=target_result,
                    priors=tuple(prior_results),
                    failures=(reason,),
                    contrast_decisions=contrast_decisions,
                )
        elif prior_decision == target_decision:
            reason = "selected prior contrast agrees with the target decision"
            return _reject(
                reason,
                target=target_result,
                priors=tuple(prior_results),
                failures=(reason,),
            )

    constraint_failures, constraint_review = _check_constraints(plan, raw_values)
    if constraint_review:
        return _review(
            constraint_review,
            target_result,
            tuple(prior_results),
            contrast_decisions=contrast_decisions,
        )
    if constraint_failures:
        return _reject(
            "declared number constraints failed",
            target_result,
            tuple(prior_results),
            failures=tuple(constraint_failures),
            contrast_decisions=contrast_decisions,
        )

    if plan.schema_version != "math-plan/v2":
        try:
            requirement_ok, requirement_reason = _check_required_paths(
                plan,
                target_result,
                tuple(prior_results),
            )
        except FillCheckError as exc:
            return _review(str(exc), target_result, tuple(prior_results))
        if not requirement_ok:
            return _reject(
                requirement_reason,
                target_result,
                tuple(prior_results),
                failures=(requirement_reason,),
            )
    return FillCheck(
        accepted=True,
        status="accepted",
        reason=(
            "values satisfy the frozen target answer rule and essential constraints"
            + (
                " and the selected prior contrast differs"
                if plan.prior_contrast is not None
                else ""
            )
            if plan.schema_version == "math-plan/v2"
            else "values satisfy the frozen answer rule and required prior contrast"
        ),
        target=target_result,
        priors=tuple(prior_results),
        contrast_decisions=contrast_decisions,
    )


def _reject(
    reason: str,
    target: PathResult | None = None,
    priors: tuple[PathResult, ...] = (),
    *,
    failures: tuple[str, ...] = (),
    contrast_decisions: dict[str, bool] | None = None,
) -> FillCheck:
    return FillCheck(
        accepted=False,
        status="rejected",
        reason=reason,
        target=target,
        priors=priors,
        failures=failures,
        contrast_decisions=contrast_decisions,
    )


def _review(
    reason: str,
    target: PathResult | None,
    priors: tuple[PathResult, ...],
    *,
    contrast_decisions: dict[str, bool] | None = None,
) -> FillCheck:
    return FillCheck(
        accepted=False,
        status="needs_review",
        contrast_decisions=contrast_decisions,
        reason=reason,
        target=target,
        priors=priors,
        failures=(reason,),
    )


def _validate_values(plan: MathPlan, values: dict[str, Any]) -> None:
    expected = {quantity.name for quantity in plan.given_quantities}
    actual = set(values)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise FillCheckError(f"missing values for given slots: {missing}")
    if extra:
        raise FillCheckError(f"values contain non-given slots: {extra}")
    for quantity in plan.given_quantities:
        value = values[quantity.name]
        if quantity.role == "list":
            if not isinstance(value, list) or not value:
                raise FillCheckError(f"{quantity.name!r} must be a non-empty list")
            if quantity.list_length is not None and len(value) != quantity.list_length:
                raise FillCheckError(
                    f"{quantity.name!r} must contain {quantity.list_length} values"
                )
            for item in value:
                _validate_number(item, quantity.name, quantity.value_domain)
        else:
            if isinstance(value, list):
                raise FillCheckError(f"{quantity.name!r} must be a scalar")
            _validate_number(value, quantity.name, quantity.value_domain)


def _validate_number(value: Any, name: str, value_domain: str = "positive") -> None:
    if value_domain not in ALLOWED_VALUE_DOMAINS:
        raise FillCheckError(f"{name!r} has unsupported value domain {value_domain!r}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FillCheckError(f"{name!r} must contain only numeric values")
    if isinstance(value, float) and not math.isfinite(value):
        raise FillCheckError(f"{name!r} contains a non-finite value")
    if value <= 0:
        raise FillCheckError(f"{name!r} must contain positive values")
    if value_domain == "positive_integer" and not isinstance(value, int):
        raise FillCheckError(f"{name!r} must contain positive whole numbers")


def validate_plan_expressions(plan: MathPlan) -> tuple[str, ...]:
    """Preflight the restricted expression language before number generation."""
    errors: list[str] = []
    quantities = {quantity.name: quantity for quantity in plan.given_quantities}
    paths = (("target", plan.target),)
    if plan.schema_version != "math-plan/v2":
        paths += tuple(
            (f"prior {prior.name}", prior)
            for prior in plan.priors
            if prior.checkability == "numerical"
        )
    elif plan.prior_contrast is not None:
        paths += (("selected prior contrast", plan.prior_contrast),)
    for path_name, path in paths:
        for label, formula in path.expressions:
            try:
                tree = ast.parse(formula.strip(), mode="eval")
                _validate_expression_ast(tree.body, quantities)
            except (FillCheckError, SyntaxError) as exc:
                errors.append(f"{path_name} {label!r}: {exc}")
    for index, constraint in enumerate(plan.constraints):
        for side_name, formula in (("left", constraint.left), ("right", constraint.right)):
            try:
                tree = ast.parse(formula.strip(), mode="eval")
                _validate_expression_ast(tree.body, quantities)
            except (FillCheckError, SyntaxError) as exc:
                errors.append(f"constraint {index} {side_name}: {exc}")
    return tuple(errors)


def _validate_expression_ast(
    node: ast.AST,
    quantities: dict[str, Quantity],
    *,
    in_sum: bool = False,
) -> None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FillCheckError(f"unsupported constant {node.value!r}")
        return
    if isinstance(node, ast.Name):
        quantity = quantities.get(node.id)
        if quantity is None:
            raise FillCheckError(f"unknown name {node.id!r}")
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        _validate_expression_ast(node.operand, quantities, in_sum=in_sum)
        return
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        _validate_expression_ast(node.left, quantities, in_sum=in_sum)
        _validate_expression_ast(node.right, quantities, in_sum=in_sum)
        return
    if isinstance(node, ast.Subscript):
        if not isinstance(node.value, ast.Name):
            raise FillCheckError("list indices must refer directly to a named slot")
        quantity = quantities.get(node.value.id)
        if quantity is None:
            raise FillCheckError(f"unknown name {node.value.id!r}")
        if quantity.role != "list":
            raise FillCheckError(f"cannot index scalar slot {quantity.name!r}")
        sl = node.slice
        if (
            not isinstance(sl, ast.Constant)
            or isinstance(sl.value, bool)
            or not isinstance(sl.value, int)
        ):
            raise FillCheckError("only literal integer list indices are allowed")
        if sl.value < 0:
            raise FillCheckError("list indices must be non-negative")
        if quantity.list_length is not None and sl.value >= quantity.list_length:
            raise FillCheckError(
                f"index {sl.value} is outside {quantity.name!r} length {quantity.list_length}"
            )
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
            raise FillCheckError(
                "only " + "(), ".join(sorted(_ALLOWED_FUNCTIONS)) + "() are allowed"
            )
        if node.keywords or len(node.args) != 1:
            raise FillCheckError(f"{node.func.id}() takes one positional argument")
        if node.func.id == "sum":
            argument = node.args[0]
            if not isinstance(argument, ast.Name):
                raise FillCheckError("sum() must receive a named list slot")
            quantity = quantities.get(argument.id)
            if quantity is None:
                raise FillCheckError(f"unknown name {argument.id!r}")
            if quantity.role != "list":
                raise FillCheckError(f"sum() needs a list slot, not {argument.id!r}")
        else:
            _validate_expression_ast(node.args[0], quantities, in_sum=in_sum)
        return
    raise FillCheckError(f"unsupported expression {type(node).__name__}")


def _validate_target_decision(result: PathResult, rule: AnswerRule) -> str | None:
    if rule.kind in {"largest", "smallest"}:
        winners = result.argmax if rule.kind == "largest" else result.argmin
        if rule.require_unique and len(winners) != 1:
            return "the target answer is tied but the answer rule requires a unique result"
    elif rule.kind == "equal" and len(result.values) < 2:
        return "an equal/not-equal answer needs at least two labelled results"
    elif rule.kind == "scalar" and len(result.values) != 1:
        return "a scalar answer rule needs exactly one computed result"
    return None


def _check_required_paths(
    plan: MathPlan,
    target: PathResult,
    priors: tuple[PathResult, ...],
) -> tuple[bool, str]:
    decisions = [_path_decision(target, plan.answer_rule)]
    numeric_priors = [prior for prior in priors if prior.error != "not numerically checked"]
    prior_decisions = [_path_decision(prior, plan.answer_rule) for prior in numeric_priors]
    by_name = {prior.name: decision for prior, decision in zip(numeric_priors, prior_decisions)}
    by_approach = {
        prior.approach_id: decision
        for prior, decision in zip(numeric_priors, prior_decisions)
        if prior.approach_id
    }
    target_decision = decisions[0]
    for requirement in plan.required_checks:
        if requirement == "at_least_one_prior_disagrees":
            if any(decision != target_decision for decision in prior_decisions):
                continue
            return False, "every required prior approach agrees with the target"
        if requirement == "all_priors_disagree":
            if all(decision != target_decision for decision in prior_decisions):
                continue
            return False, "not every required prior approach disagrees with the target"
        if requirement.startswith("prior_disagrees:"):
            key = requirement.split(":", 1)[1].strip()
            selected = by_name.get(key, by_approach.get(key))
            if selected is None:
                raise FillCheckError(f"required prior path {key!r} was not found")
            if selected == target_decision:
                return False, f"required prior path {key!r} agrees with the target"
            continue
        raise FillCheckError(f"unsupported required check {requirement!r}")
    return True, "required checks passed"


def _path_decision(result: PathResult, rule: AnswerRule) -> tuple[str, object]:
    if rule.kind == "largest":
        return "largest", result.argmax
    if rule.kind == "smallest":
        return "smallest", result.argmin
    if rule.kind == "equal":
        return "equal", _all_equal(list(result._computed.values()))
    value = next(iter(result._computed.values()))
    return "scalar", str(simplify(value))


def _check_constraints(
    plan: MathPlan,
    values: dict[str, Any],
) -> tuple[list[str], str | None]:
    failures: list[str] = []
    for constraint in plan.constraints:
        try:
            left = evaluate_formula(constraint.left, values)
            right = evaluate_formula(constraint.right, values)
        except FillCheckError as exc:
            return failures, f"cannot evaluate declared constraint: {exc}"
        comparison = simplify(left - right)
        operator = constraint.operator
        if operator == "==" and comparison != 0:
            passed = False
        elif operator == "!=" and comparison == 0:
            passed = False
        elif operator == ">" and not comparison > 0:
            passed = False
        elif operator == ">=" and not comparison >= 0:
            passed = False
        elif operator == "<" and not comparison < 0:
            passed = False
        elif operator == "<=" and not comparison <= 0:
            passed = False
        else:
            passed = True
        if not passed:
            failures.append(
                constraint.description or f"{constraint.left} {operator} {constraint.right}"
            )
    return failures, None


def _path_result(
    path: FormulaPath,
    role: str,
    values: dict[str, Any],
) -> PathResult:
    computed: dict[str, Expr] = {}
    for label, formula in path.expressions:
        try:
            computed[label] = evaluate_formula(formula, values)
        except ZeroDivisionError:
            return PathResult(
                name=path.name,
                role=role,
                values={},
                undefined=True,
                tied=False,
                argmax=(),
                argmin=(),
                error=f"{path.name!r} expression {label!r} divides by zero",
                approach_id=path.approach_id,
            )
    if not computed:
        raise FillCheckError(f"{path.name} has no expressions")
    rendered = {label: str(simplify(value)) for label, value in computed.items()}
    tied = len(computed) > 1 and _all_equal(list(computed.values()))
    return PathResult(
        name=path.name,
        role=role,
        values=rendered,
        undefined=False,
        tied=tied,
        argmax=_extrema(computed, high=True),
        argmin=_extrema(computed, high=False),
        approach_id=path.approach_id,
        _computed=computed,
    )


def _all_equal(values: list[Expr]) -> bool:
    if not values:
        return False
    first = values[0]
    return all(simplify(value - first) == 0 for value in values[1:])


def _extrema(computed: dict[str, Expr], *, high: bool) -> tuple[str, ...]:
    labels = list(computed)
    best = [labels[0]]
    for label in labels[1:]:
        delta = simplify(computed[label] - computed[best[0]])
        if delta == 0:
            best.append(label)
        elif (high and delta > 0) or (not high and delta < 0):
            best = [label]
    return tuple(sorted(best))


def _legacy_plan_from_payload(
    payload: dict[str, Any],
    values: dict[str, Any] | None,
) -> MathPlan:
    raw_values = values if values is not None else payload.get("values")
    if not isinstance(raw_values, dict) or not raw_values:
        raise FillCheckError("missing values")
    target = payload.get("target")
    priors = payload.get("priors")
    if not isinstance(target, dict) or not isinstance(target.get("expressions"), dict):
        raise FillCheckError("missing target expressions")
    if not isinstance(priors, list) or not priors:
        raise FillCheckError("missing prior expressions")
    quantities = tuple(
        Quantity(
            name=name,
            role="list" if isinstance(value, list) else "other",
            description="legacy fill slot",
            value_source="given",
            list_length=len(value) if isinstance(value, list) else None,
        )
        for name, value in raw_values.items()
    )
    target_path = FormulaPath(
        name="target",
        expressions=tuple(
            (str(label), str(formula)) for label, formula in target["expressions"].items()
        ),
    )
    prior_paths = []
    for index, item in enumerate(priors):
        if not isinstance(item, dict) or not isinstance(item.get("expressions"), dict):
            raise FillCheckError(f"prior {index} is missing expressions")
        prior_paths.append(
            FormulaPath(
                name=str(item.get("resource") or f"prior_{index}"),
                expressions=tuple(
                    (str(label), str(formula)) for label, formula in item["expressions"].items()
                ),
            )
        )
    labels = tuple(label for label, _ in target_path.expressions)
    return MathPlan(
        quantities=quantities,
        target=target_path,
        priors=tuple(prior_paths),
        answer_rule=AnswerRule(
            kind="largest",
            labels=labels,
            require_unique=True,
        ),
        required_checks=("at_least_one_prior_disagrees",),
        schema_version="math-plan/legacy-adapter",
    )


def _eval_ast(node: ast.AST, values: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FillCheckError(f"unsupported constant {node.value!r}")
        return _box(node.value)
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise FillCheckError(f"unknown name {node.id!r}")
        return _box(values[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_ast(node.operand, values)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval_ast(node.left, values)
        right = _eval_ast(node.right, values)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.Subscript):
        sequence = _eval_ast(node.value, values)
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
            index = sl.value
        else:
            raise FillCheckError("only integer list indices are allowed")
        try:
            return _box(sequence[index])
        except (TypeError, IndexError) as exc:
            raise FillCheckError(f"bad index {index}") from exc
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
            raise FillCheckError(
                "only " + "(), ".join(sorted(_ALLOWED_FUNCTIONS)) + "() are allowed"
            )
        if node.keywords:
            raise FillCheckError("keyword arguments are not allowed")
        args = [_eval_ast(arg, values) for arg in node.args]
        if node.func.id == "abs":
            if len(args) != 1:
                raise FillCheckError("abs() takes one argument")
            return Abs(args[0])
        if len(args) != 1:
            raise FillCheckError("sum() takes one list")
        try:
            return sum((_box(item) for item in args[0]), Integer(0))
        except TypeError as exc:
            raise FillCheckError("sum() needs a list") from exc
    if isinstance(node, ast.List):
        return [_eval_ast(elt, values) for elt in node.elts]
    raise FillCheckError(f"unsupported expression {type(node).__name__}")


def _box(value: Any) -> Any:
    if isinstance(value, Expr):
        return value
    if isinstance(value, bool):
        raise FillCheckError("boolean values are not allowed")
    if isinstance(value, int):
        return Integer(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FillCheckError("non-finite numbers are not allowed")
        return Rational(str(value))
    if isinstance(value, list):
        return [_box(item) for item in value]
    raise FillCheckError(f"unsupported value {value!r}")


_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}
_ALLOWED_FUNCTIONS = frozenset({"sum", "abs"})


def checker_capability_contract() -> str:
    """Render the authoritative execution contract for upstream design stages."""
    binary_examples = ", ".join(
        ast.unparse(
            ast.BinOp(
                left=ast.Name(id="x", ctx=ast.Load()),
                op=operator(),
                right=ast.Name(id="y", ctx=ast.Load()),
            )
        )
        for operator in _BINOPS
    )
    function_descriptions = [
        description
        for name, description in (
            ("sum", "sum(named_list) only"),
            ("abs", "abs(scalar_expression)"),
        )
        if name in _ALLOWED_FUNCTIONS
    ]
    functions = " and ".join(function_descriptions)
    operators = ", ".join(sorted(ALLOWED_OPERATORS))
    domains = ", ".join(sorted(ALLOWED_VALUE_DOMAINS))
    answer_kinds = ", ".join(sorted(ALLOWED_ANSWER_KINDS))
    return "\n".join(
        [
            "AUTHORITATIVE DETERMINISTIC CHECKER CONTRACT (source: src/generation/fill_check.py):",
            "A new plan is math-plan/v2: it has one executable target, an answer_rule, "
            "and essential constraints; it may also contain one explicitly selected "
            "numerical prior_contrast, but no general executable prior paths.",
            "Only quantities with value_source='given' are bound from the fill. The fill "
            "must contain exactly those names: no derived or unknown slots and no extras.",
            "Given scalar slots are finite, numeric, positive values (booleans are rejected). "
            "Given list slots are non-empty lists of finite, numeric, positive values; a declared "
            "list_length is enforced exactly. value_domain is authoritative: "
            f"{domains}; positive_integer additionally requires JSON integer values (for example, "
            "2 is valid but 2.0 is not).",
            "There is no equation solving or implicit binding. Derived quantities, unknown "
            "quantities, and target expression labels are not input slots; only given slots "
            "are bound from the fill.",
            "Plan formulas are preflighted as expressions over given slots only. They support "
            f"numeric literals, unary negation (-x) (which may make an expression result negative "
            f"but never permits negative given values), binary {binary_examples}, literal "
            "non-negative integer "
            f"indices on named list slots, and {functions}. "
            "Integer powers can be expanded as repeated multiplication (x*x is supported, "
            "but x**2 is rejected); a missing named function alone does not prove "
            "impossibility, and arbitrary functions are not thereby supported. "
            "Numeric constants are allowed only when they are genuine parts of the stated "
            "calculation; they must not be placeholders used to force success or failure or "
            "stand in for an omitted relationship. "
            "When list_length is declared, indices must be within it; fresh proposals "
            "require fixed lengths for given lists, while historical plans may rely on "
            "the runtime list length. Symbolic indices, exponentiation, modulo, "
            "comparisons inside formulas, and other functions are rejected.",
            "The target expression labels must exactly equal answer_rule.labels. Supported "
            f"answer_rule kinds are {answer_kinds}. A scalar rule has one label; "
            "largest/smallest compare all labels and may require a unique winner "
            "(ties are rejected); equal computes whether all listed results are equal and needs "
            "at least two labels.",
            "An optional prior_contrast is limited to one selected, numerically checkable "
            "approach. For a largest/smallest target with a unique winner, it uses the same "
            "labels and is rejected when it gives the same answer decision. For an equal target, "
            "target and prior paths each need at least two labeled results (their labels may "
            "differ); selected expected_target_equal and expected_prior_equal booleans must be "
            "opposite, and exact arithmetic must satisfy both. This checks all listed values, "
            "not one derived scalar. The checker verifies arithmetic and the declared decisions, "
            "not whether formulas faithfully represent the described student move.",
            "Constraints use the same formula language and only these comparison "
            f"operators: {operators}. "
            "They are evaluated on the filled values and failed constraints reject the fill.",
            "Unsupported or non-native operations cannot be written as new checker functions. "
            "An equivalent bounded formulation is "
            "allowed only when it uses the supported arithmetic above and is explicitly valid; "
            "do not invent a formula or blanket-ban an entire topic. If the target is not "
            "representable, keep that limitation explicit and block the plan.",
            "Keep open-ended student reasoning and numerical verification distinct: the checker "
            "verifies the frozen target, answer rule, constraints, and input domains; it does "
            "not prove that a plain-language approach is meaningful or that every prior "
            "route fails.",
            "Historical math-plan/v1 results may contain executable numerical priors or "
            "qualitative/unsupported priors for inspection, but new planning must use v2.",
        ]
    )
