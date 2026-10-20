"""Bounded, exact arithmetic for simplified D2b design conditions.

This language is independent of the legacy fill checker. Symbols are declared
explicitly; undecidable conditions and unsupported expressions never mean false.
Quantities are finite Python integers/floats or lists nested at most four levels
with at most 512 total numbers and list containers; decimal literals are read exactly.
Powers accept rational exponents of magnitude at most 16 and
denominator at most 16. Fractional powers use the nonnegative real domain.
"""

from __future__ import annotations

import ast
import keyword
import math
from decimal import Decimal
from typing import Any

from sympy import Abs, Expr, Integer, Max, Min, Rational, Symbol, preorder_traversal, simplify

from src.generation.fill_check import _box

_FUNCTIONS = frozenset({"sqrt", "min", "max", "sum", "abs", "len", "unit"})
_ASSUMPTIONS = frozenset({"positive", "nonnegative", "real", "integer"})
_MAX_SOURCE = 4096
_MAX_NODES = 256
_MAX_DEPTH = 40
_MAX_BINDINGS = 64
_MAX_LIST = 128
_MAX_LIST_DEPTH = 4
_MAX_BITS = 4096


class _CalculationError(Exception):
    def __init__(self, status: str, reason: str):
        self.status = status
        super().__init__(reason)


def calculate_condition(
    calculation: dict, values: dict, *, units: dict[str, str] | None = None
) -> dict:
    """Return ``status``, exact string ``computed`` values, and a concrete reason.

    Expressions bind labels in insertion order. Predicates use comparisons and
    three-valued Boolean logic: an unresolved symbol is unknown, not false.
    Intermediate conditions bind Boolean values or an unresolved value internally;
    their computed strings are ``True``, ``False``, or ``unknown``.
    ``unit(quantity_name)`` reads optional metadata for a given quantity, without
    conversion. Unit strings support equality/inequality only; missing units are unknown.
    Unsupported syntax/configuration is distinct from repairable numeric errors.
    """
    computed: dict[str, str] = {}
    context = "calculation"
    try:
        if not isinstance(calculation, dict) or not isinstance(values, dict):
            raise _CalculationError("unsupported", "calculation and values must be dictionaries")
        units = {} if units is None else units
        if not isinstance(units, dict):
            raise _CalculationError("unsupported", "units must be a dictionary")
        for name, label in units.items():
            if name not in values:
                raise _CalculationError(
                    "unsupported", f"unit metadata for unknown quantity {name!r}"
                )
            if type(label) is not str or len(label) > _MAX_SOURCE:
                raise _CalculationError("unsupported", "unit metadata must be bounded strings")
        expressions = calculation.get("expressions")
        symbols = calculation.get("symbols", {})
        if not isinstance(expressions, dict) or not isinstance(symbols, dict):
            raise _CalculationError("unsupported", "expressions and symbols must be dictionaries")
        groups = (values, symbols, expressions)
        if sum(len(group) for group in groups) > _MAX_BINDINGS:
            raise _CalculationError(
                "unsupported", "too many values, symbols, or intermediate labels"
            )
        names: set[str] = set()
        for group in groups:
            for name in group:
                if (
                    not isinstance(name, str)
                    or len(name) > 64
                    or not name.isidentifier()
                    or keyword.iskeyword(name)
                    or name.startswith("__")
                    or name in _FUNCTIONS
                ):
                    raise _CalculationError("unsupported", f"invalid or reserved name {name!r}")
                if name in names:
                    raise _CalculationError("unsupported", f"name collision for {name!r}")
                names.add(name)

        # Validate every branch before executing; short-circuiting cannot hide syntax.
        parsed = {
            label: _parse(source, predicate=False)
            for label, source in expressions.items()
        }
        predicate = _parse(calculation.get("predicate"), predicate=True)
        for tree in (*parsed.values(), predicate):
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and node.func.id == "unit":
                    name = node.args[0].id
                    if name not in values:
                        raise _CalculationError(
                            "unsupported",
                            f"unit() requires a given quantity; unknown name {name!r}",
                        )
        environment: dict[str, Any] = {}
        for name, assumption in symbols.items():
            if not isinstance(assumption, str) or assumption not in _ASSUMPTIONS:
                raise _CalculationError("unsupported", f"invalid assumption for symbol {name!r}")
            environment[name] = Symbol(name, **{assumption: True})
        for name, value in values.items():
            context = f"value {name!r}"
            environment[name] = _quantity(value)
        for label, tree in parsed.items():
            context = f"expression {label!r}"
            if _is_condition(tree.body):
                try:
                    result = _predicate(tree.body, environment, expressions[label], units)
                except _CalculationError as exc:
                    if exc.status != "unknown":
                        raise
                    result = None
            else:
                result = _arithmetic(tree.body, environment, expressions[label], units)
            environment[label] = result
            computed[label] = "unknown" if result is None else str(result)
        context = "predicate"
        decision = _predicate(predicate.body, environment, calculation["predicate"], units)
        if decision is None:
            return {
                "status": "unknown",
                "computed": computed,
                "reason": "predicate cannot be decided from supplied data and symbol assumptions",
            }
        return {
            "status": "holds" if decision else "fails",
            "computed": computed,
            "reason": "predicate holds" if decision else "predicate is false",
        }
    except _CalculationError as exc:
        return {"status": exc.status, "computed": computed, "reason": f"{context}: {exc}"}
    except (RecursionError, OverflowError):
        return {
            "status": "unsupported",
            "computed": computed,
            "reason": f"{context}: calculation exceeds resource limits",
        }


def _parse(source: Any, *, predicate: bool) -> ast.Expression:
    if not isinstance(source, str) or not source.strip():
        raise _CalculationError("unsupported", "an expression or predicate is missing or empty")
    if len(source) > _MAX_SOURCE:
        raise _CalculationError("unsupported", "expression exceeds source length limit")
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise _CalculationError("unsupported", "cannot parse expression") from exc
    stack = [(tree.body, 0)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > _MAX_NODES or depth > _MAX_DEPTH:
            raise _CalculationError("unsupported", "expression exceeds AST size or depth limit")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    _validate(tree.body, predicate=predicate or _is_condition(tree.body))
    return tree


def _is_condition(node: ast.AST) -> bool:
    return isinstance(node, (ast.Compare, ast.BoolOp)) or (
        isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)
    )


def _validate(node: ast.AST, *, predicate: bool = False) -> None:
    if predicate:
        if isinstance(node, ast.Name):
            return
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            for child in node.values:
                _validate(child, predicate=True)
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            _validate(node.operand, predicate=True)
            return
        if isinstance(node, ast.Compare):
            if not all(
                isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE))
                for op in node.ops
            ):
                raise _CalculationError("unsupported", "unsupported comparison operator")
            for child in (node.left, *node.comparators):
                _validate(child)
            return
        raise _CalculationError(
            "unsupported", "predicate must use comparisons, Boolean names, and and/or/not"
        )
    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float, str):
            raise _CalculationError("unsupported", "only numeric or string literals are supported")
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        _validate(node.operand)
        return
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
    ):
        _validate(node.left)
        _validate(node.right)
        return
    if isinstance(node, ast.List):
        if len(node.elts) > _MAX_LIST:
            raise _CalculationError("unsupported", "list exceeds length limit")
        for child in node.elts:
            _validate(child)
        return
    if isinstance(node, ast.Subscript):
        if not (
            isinstance(node.slice, ast.Constant)
            and type(node.slice.value) is int
            and 0 <= node.slice.value < _MAX_LIST
        ):
            raise _CalculationError(
                "unsupported", "list indices must be bounded nonnegative integers"
            )
        _validate(node.value)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise _CalculationError(
                "unsupported", "unsupported function; use sqrt/min/max/sum/abs/len/unit"
            )
        if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
            raise _CalculationError("unsupported", "keyword and unpacked arguments are unsupported")
        name = node.func.id
        if name in {"min", "max"}:
            if not node.args:
                raise _CalculationError(
                    "unsupported", f"{name}() requires a nonempty list or at least two scalars"
                )
        elif len(node.args) != 1:
            raise _CalculationError("unsupported", f"{name}() requires one argument")
        if name == "unit" and not isinstance(node.args[0], ast.Name):
            raise _CalculationError("unsupported", "unit() requires a given quantity name")
        for child in node.args:
            _validate(child)
        return
    raise _CalculationError("unsupported", f"unsupported syntax {type(node).__name__}")


def _quantity(value: Any) -> Any:
    if isinstance(value, list):
        _check_list(value)
        return [_quantity(item) for item in value]
    return _quantity_scalar(value)


def _check_list(value: list, depth: int = 1) -> int:
    if depth > _MAX_LIST_DEPTH:
        raise _CalculationError("unsupported", "list exceeds nesting limit")
    if len(value) > _MAX_LIST:
        raise _CalculationError("unsupported", "list exceeds length limit")
    size = 1
    for item in value:
        size += _check_list(item, depth + 1) if isinstance(item, list) else 1
        if size > _MAX_NODES * 2:
            raise _CalculationError("unsupported", "list exceeds total size limit")
    return size


def _quantity_scalar(value: Any) -> Expr:
    if type(value) not in (int, float):
        raise _CalculationError(
            "fails", "quantity must be a finite number, not a boolean or other type"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise _CalculationError("fails", "non-finite quantity")
    if isinstance(value, int) and value.bit_length() > _MAX_BITS:
        raise _CalculationError("unsupported", "number exceeds bit-length limit")
    return _checked(_box(value))


def _scalar(value: Any) -> Expr:
    if not isinstance(value, Expr):
        raise _CalculationError(
            "unsupported",
            "operation requires a scalar quantity, not a list, string, or Boolean condition",
        )
    return value


def _checked(value: Expr) -> Expr:
    if value.is_finite is False or value.is_real is False:
        raise _CalculationError(
            "fails", "calculation is non-finite or outside the real-number domain"
        )
    for index, part in enumerate(preorder_traversal(value)):
        if index >= _MAX_NODES * 2:
            raise _CalculationError("unsupported", "computed expression exceeds size limit")
        if (
            isinstance(part, Rational)
            and max(int(part.p).bit_length(), int(part.q).bit_length()) > _MAX_BITS
        ):
            raise _CalculationError("unsupported", "computed number exceeds bit-length limit")
        if part.is_Pow and part.exp.is_number and abs(part.exp) > 1024:
            raise _CalculationError("unsupported", "computed power exceeds exponent limit")
    return value


def _arithmetic(node: ast.AST, environment: dict, source: str, units: dict) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if type(node.value) is int:
            return _quantity_scalar(node.value)
        if not math.isfinite(node.value):
            raise _CalculationError("fails", "non-finite numeric literal")
        literal = Decimal(ast.get_source_segment(source.strip(), node).replace("_", ""))
        if abs(literal.adjusted()) > 1024:
            raise _CalculationError("unsupported", "numeric literal exceeds precision limit")
        numerator, denominator = literal.as_integer_ratio()
        return _checked(Rational(numerator, denominator))
    if isinstance(node, ast.Name):
        if node.id not in environment:
            raise _CalculationError(
                "unknown", f"name {node.id!r} is not bound; supply a value or earlier expression"
            )
        return environment[node.id]
    if isinstance(node, ast.List):
        result = [_arithmetic(child, environment, source, units) for child in node.elts]
        for item in result:
            if not isinstance(item, list):
                _scalar(item)
        _check_list(result)
        return result
    if isinstance(node, ast.Subscript):
        sequence = _arithmetic(node.value, environment, source, units)
        if not isinstance(sequence, list):
            raise _CalculationError("unsupported", "indexing requires a list")
        if node.slice.value >= len(sequence):
            raise _CalculationError("unsupported", f"list index {node.slice.value} is out of range")
        return sequence[node.slice.value]
    if isinstance(node, ast.UnaryOp):
        value = _scalar(_arithmetic(node.operand, environment, source, units))
        return _checked(-value if isinstance(node.op, ast.USub) else value)
    if isinstance(node, ast.BinOp):
        left = _scalar(_arithmetic(node.left, environment, source, units))
        right = _scalar(_arithmetic(node.right, environment, source, units))
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            _nonzero(right, "division by zero")
            result = left / right
        else:
            if not isinstance(right, Rational) or abs(right) > 16 or right.q > 16:
                raise _CalculationError(
                    "unsupported", "powers require rational exponents bounded by 16"
                )
            if right <= 0:
                _nonzero(left, "zero cannot have a zero or negative exponent")
            if right.q != 1:
                _nonnegative(left, "fractional power")
            if isinstance(left, Rational):
                bits = max(int(left.p).bit_length(), int(left.q).bit_length())
                if bits * max(1, abs(int(right.p))) > _MAX_BITS:
                    raise _CalculationError("unsupported", "power exceeds numeric bit-length limit")
            result = left ** right
        return _checked(result)
    if isinstance(node, ast.Call):
        name = node.func.id
        if name == "unit":
            quantity = node.args[0].id
            if quantity not in units:
                raise _CalculationError("unknown", f"unit metadata is missing for {quantity!r}")
            return units[quantity]
        args = [_arithmetic(arg, environment, source, units) for arg in node.args]
        if name in {"min", "max"}:
            if len(args) == 1 and isinstance(args[0], list):
                args = args[0]
            elif len(args) < 2:
                raise _CalculationError(
                    "unsupported", f"{name}() requires a nonempty list or at least two scalars"
                )
            if not args:
                raise _CalculationError("unsupported", f"{name}() requires a nonempty list")
            return _checked((Min if name == "min" else Max)(*[_scalar(arg) for arg in args]))
        if len(args) != 1:
            raise _CalculationError("unsupported", f"{name}() requires one argument")
        value = args[0]
        if name in {"sum", "len"}:
            if not isinstance(value, list):
                raise _CalculationError("unsupported", f"{name}() requires a list")
            return _checked(
                Integer(len(value)) if name == "len"
                else sum((_scalar(item) for item in value), Integer(0))
            )
        value = _scalar(value)
        if name == "abs":
            return _checked(Abs(value))
        _nonnegative(value, "sqrt")
        return _checked(value ** Rational(1, 2))
    raise _CalculationError("unsupported", f"unsupported syntax {type(node).__name__}")


def _nonzero(value: Expr, message: str) -> None:
    if value.is_zero is None:
        value = _checked(simplify(value))
    if value.is_zero is True:
        raise _CalculationError("fails", message)
    if value.is_zero is None:
        raise _CalculationError("unknown", f"{message}: symbolic denominator/base may be zero")


def _nonnegative(value: Expr, operation: str) -> None:
    if value.is_nonnegative is False:
        raise _CalculationError("fails", f"{operation} requires a nonnegative real argument")
    if value.is_nonnegative is None:
        raise _CalculationError("unknown", f"{operation} argument is not known to be nonnegative")


def _predicate(node: ast.AST, environment: dict, source: str, units: dict) -> bool | None:
    if isinstance(node, ast.Name):
        value = _arithmetic(node, environment, source, units)
        if type(value) is bool or value is None:
            return value
        raise _CalculationError(
            "unsupported",
            f"name {node.id!r} is not a Boolean condition; "
            "numeric/string truthiness is unsupported",
        )
    if isinstance(node, ast.UnaryOp):
        result = _predicate(node.operand, environment, source, units)
        return None if result is None else not result
    if isinstance(node, ast.BoolOp):
        decisions = []
        for child in node.values:
            try:
                decision = _predicate(child, environment, source, units)
            except _CalculationError as exc:
                if exc.status != "unknown":
                    raise
                decision = None
            if isinstance(node.op, ast.And) and decision is False:
                return False
            if isinstance(node.op, ast.Or) and decision is True:
                return True
            decisions.append(decision)
        if None in decisions:
            return None
        return isinstance(node.op, ast.And)
    left = _arithmetic(node.left, environment, source, units)
    unknown = False
    for op, child in zip(node.ops, node.comparators):
        right = _arithmetic(child, environment, source, units)
        if isinstance(left, str) or isinstance(right, str):
            if not isinstance(left, str) or not isinstance(right, str):
                raise _CalculationError("unsupported", "strings can only be compared with strings")
            if not isinstance(op, (ast.Eq, ast.NotEq)):
                raise _CalculationError(
                    "unsupported", "string ordering is unsupported; use == or !="
                )
            decision = left == right if isinstance(op, ast.Eq) else left != right
        else:
            difference = _checked(simplify(_checked(_scalar(left) - _scalar(right))))
            if isinstance(op, (ast.Eq, ast.NotEq)):
                decision = difference.is_zero
                if isinstance(op, ast.NotEq) and decision is not None:
                    decision = not decision
            elif isinstance(op, ast.Lt):
                decision = difference.is_negative
            elif isinstance(op, ast.LtE):
                decision = difference.is_nonpositive
            elif isinstance(op, ast.Gt):
                decision = difference.is_positive
            else:
                decision = difference.is_nonnegative
        if decision is False:
            return False
        unknown = unknown or decision is None
        left = right
    return None if unknown else True
