import pytest

from src.generation.design_calculator import calculate_condition
from src.generation.fill_check import FillCheckError, evaluate_formula


def test_numeric_winner_and_insertion_order():
    result = calculate_condition(
        {
            "expressions": {
                "A": "sum(a)/sum(ta)",
                "B": "sum(b)/sum(tb)",
                "gap": "B-A",
            },
            "predicate": "B > A and gap == 1/10",
        },
        {"a": [9, 10], "ta": [9, 1], "b": [2, 2], "tb": [1, 1]},
    )
    assert result["status"] == "holds"
    assert result["computed"] == {"A": "19/10", "B": "2", "gap": "1/10"}


@pytest.mark.parametrize(
    ("units", "status"),
    [
        ({"distance": "km", "time": "h"}, "holds"),
        ({"distance": "m", "time": "h"}, "fails"),
        ({"distance": "km", "time": "min"}, "fails"),
    ],
)
def test_unit_matching_and_mismatch_with_named_intermediates(units, status):
    result = calculate_condition(
        {
            "expressions": {
                "distance_unit": "unit(distance)",
                "alias": "distance_unit",
                "consistent": "alias == 'km' and unit(time) == 'h' and unit(time) != 'min'",
                "speed": "distance/time",
            },
            "predicate": "consistent and speed == 60",
        },
        {"distance": 120, "time": 2},
        units=units,
    )
    assert result["status"] == status
    assert result["computed"]["distance_unit"] == units["distance"]
    assert result["computed"]["alias"] == units["distance"]
    assert result["computed"]["speed"] == "60"


@pytest.mark.parametrize("units", [None, {}, {"time": "h"}])
def test_missing_unit_metadata_is_unknown(units):
    result = calculate_condition(
        {"expressions": {}, "predicate": "unit(distance) == 'km'"},
        {"distance": 120, "time": 2},
        units=units,
    )
    assert result["status"] == "unknown"
    assert "unit metadata is missing" in result["reason"]


@pytest.mark.parametrize(
    ("predicate", "status"),
    [
        ("unit_check and speed == 60", "unknown"),
        ("unit_check or speed == 60", "holds"),
        ("unit_check and speed == 0", "fails"),
        ("not unit_check", "unknown"),
    ],
)
def test_missing_unit_metadata_in_boolean_intermediates_stays_unknown(predicate, status):
    result = calculate_condition(
        {
            "expressions": {"unit_check": "unit(distance) == 'km'", "speed": "distance/time"},
            "predicate": predicate,
        },
        {"distance": 120, "time": 2},
    )
    assert result["status"] == status
    assert result["computed"] == {"unit_check": "unknown", "speed": "60"}


def test_missing_unit_string_intermediate_returns_unknown():
    result = calculate_condition(
        {"expressions": {"label": "unit(distance)"}, "predicate": "label == 'km'"},
        {"distance": 120},
    )
    assert result["status"] == "unknown"
    assert "unit metadata is missing" in result["reason"]


def test_unit_accessor_reads_list_quantity_metadata_and_compares_exact_strings():
    result = calculate_condition(
        {
            "expressions": {
                "speed": "sum(distances)/sum(times)",
                "label": "unit(distances)",
            },
            "predicate": (
                "'km' == label == unit(distances) and "
                "'h' == unit(times) and 'KM' != label and speed == 60"
            ),
        },
        {"distances": [60, 120], "times": [1, 2]},
        units={"distances": "km", "times": "h"},
    )
    assert result["status"] == "holds"
    assert result["computed"] == {"speed": "60", "label": "km"}


@pytest.mark.parametrize(
    "formula",
    [
        "unit(distance) + 1",
        "unit(distance) + 'km'",
        "unit(distance) * 2",
        "-unit(distance)",
        "abs(unit(distance))",
        "sqrt(unit(distance))",
        "sum([unit(distance)])",
        "min(unit(distance), 'km')",
        "max(unit(distance), 'km')",
        "len(unit(distance))",
        "unit(distance)[0]",
        "'2' + 1",
        "'2' * 2",
        "'2'/2",
        "'2'**2",
    ],
)
def test_unit_strings_and_arbitrary_strings_are_not_numeric_operands(formula):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 1"},
        {"distance": 120},
        units={"distance": "km"},
    )
    assert result["status"] == "unsupported"


@pytest.mark.parametrize(
    "predicate",
    [
        "unit(distance) < 'km'",
        "unit(distance) <= 'km'",
        "unit(distance) > 'km'",
        "unit(distance) >= 'km'",
        "unit(distance) == 120",
        "120 != unit(distance)",
        "distance_unit",
        "not distance_unit",
        "distance_unit or 1 == 1",
        "'km'",
        "unit(distance)",
    ],
)
def test_string_ordering_mixed_comparisons_and_truthiness_are_unsupported(predicate):
    result = calculate_condition(
        {"expressions": {"distance_unit": "unit(distance)"}, "predicate": predicate},
        {"distance": 120},
        units={"distance": "km"},
    )
    assert result["status"] == "unsupported"


@pytest.mark.parametrize(
    "call",
    [
        "unit()",
        "unit(distance, distance)",
        "unit('distance')",
        "unit(distance+1)",
        "unit(distance[0])",
        "unit(name=distance)",
        "unit(*distance)",
        "unit(missing)",
        "unit(k)",
        "unit(answer)",
        "unit(distance).__class__",
        "unit(distance).lower()",
        "__import__('os')",
    ],
)
def test_unit_syntax_and_unknown_quantity_are_prevalidated_in_unused_branches(call):
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {"answer": "1"},
            "predicate": f"1 == 1 or {call} == 'km'",
        },
        {"distance": 120},
        units={"distance": "km"},
    )
    assert result["status"] == "unsupported"
    assert result["computed"] == {}


@pytest.mark.parametrize(
    "units",
    [[], {"missing": "km"}, {"distance": 120}, {"distance": True}, {"distance": "x" * 4097}],
)
def test_invalid_unit_metadata_is_unsupported(units):
    result = calculate_condition(
        {"expressions": {}, "predicate": "distance == 120"}, {"distance": 120}, units=units
    )
    assert result["status"] == "unsupported"


def test_unit_metadata_cannot_convert_or_mutate_numeric_values():
    calculation = {"expressions": {"speed": "distance/time"}, "predicate": "speed == 60"}
    values = {"distance": 120, "time": 2}
    expected = calculate_condition(calculation, values)
    for label in ("km", "m", "1/0", "__import__('os')", ""):
        units = {"distance": label, "time": "h"}
        assert calculate_condition(calculation, values, units=units) == expected
        assert units == {"distance": label, "time": "h"}
        assert values == {"distance": 120, "time": 2}


def test_unit_metadata_does_not_make_string_input_a_numeric_quantity():
    result = calculate_condition(
        {"expressions": {}, "predicate": "unit(distance) == 'km'"},
        {"distance": "km"},
        units={"distance": "km"},
    )
    assert result["status"] == "fails"
    assert "quantity" in result["reason"]


@pytest.mark.parametrize(("predicate", "status"), [("ratio == 5/8", "holds"), ("k > 1", "unknown")])
def test_units_leave_symbolic_decisions_unchanged(predicate, status):
    calculation = {
        "symbols": {"k": "positive"},
        "expressions": {"ratio": "(5*k)/(8*k)"},
        "predicate": predicate,
    }
    expected = calculate_condition(calculation, {"distance": 120})
    assert expected["status"] == status
    assert calculate_condition(calculation, {"distance": 120}, units={"distance": "km"}) == expected


def test_exact_mean_and_variability_with_square_roots_and_powers():
    result = calculate_condition(
        {
            "expressions": {
                "mean": "sum(xs)/len(xs)",
                "variance": "((xs[0]-mean)**2 + (xs[1]-mean)**2)/len(xs)",
                "spread": "sqrt(variance)",
                "range": "max(xs) - min(xs)",
                "root": "8**(1/2)",
            },
            "predicate": "mean == 3 and spread == 1 and range == 2 and root == 2*sqrt(2)",
        },
        {"xs": [2, 4]},
    )
    assert result["status"] == "holds"
    assert result["computed"]["spread"] == "1"
    assert result["computed"]["root"] == "2*sqrt(2)"


def test_general_symbolic_identity():
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {"ratio": "(5*k)/(8*k)"},
            "predicate": "ratio == 5/8",
        },
        {},
    )
    assert result["status"] == "holds"
    assert result["computed"] == {"ratio": "5/8"}


@pytest.mark.parametrize(
    ("predicate", "status"),
    [
        ("k > 0", "holds"),
        ("k < 0", "fails"),
        ("k > 1", "unknown"),
        ("k == 1", "unknown"),
        ("k != 1", "unknown"),
    ],
)
def test_symbolic_decisions(predicate, status):
    result = calculate_condition(
        {"symbols": {"k": "positive"}, "expressions": {}, "predicate": predicate},
        {},
    )
    assert result["status"] == status


def test_division_by_zero_is_repairable_numeric_failure():
    result = calculate_condition(
        {"expressions": {"mean": "sum(xs)/len(xs)"}, "predicate": "mean > 0"},
        {"xs": []},
    )
    assert result["status"] == "fails"
    assert "division by zero" in result["reason"]


@pytest.mark.parametrize(
    "formula",
    [
        "x.__class__",
        "__import__('os').system('echo unsafe')",
        "open('file')",
        "(lambda: 1)()",
        "[x for x in xs]",
        "x % 2",
    ],
)
def test_hostile_or_unsupported_syntax_is_not_executed(formula):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 1"},
        {"x": 1, "xs": [1]},
    )
    assert result["status"] == "unsupported"


def test_legacy_formula_language_is_unchanged():
    assert str(evaluate_formula("sum(xs)/2 + abs(xs[0]-xs[1])", {"xs": [2, 4]})) == "5"
    for formula in ("x**2", "sqrt(x)", "min(xs)", "len(xs)", "x > 0", "unit(x)"):
        with pytest.raises(FillCheckError):
            evaluate_formula(formula, {"x": 4, "xs": [2, 4]})


def test_decimal_values_and_literals_are_exact():
    result = calculate_condition(
        {
            "expressions": {
                "total": "a+b",
                "literal": "0.12345678901234567890123456789",
                "scientific": "1.25e-2 + 1_000.0",
            },
            "predicate": (
                "total == 3/10 and "
                "literal == 12345678901234567890123456789/100000000000000000000000000000 "
                "and scientific == 80001/80"
            ),
        },
        {"a": 0.1, "b": 0.2},
    )
    assert result["status"] == "holds"
    assert result["computed"]["total"] == "3/10"
    assert result["computed"]["literal"] == (
        "12345678901234567890123456789/100000000000000000000000000000"
    )


def test_polynomial_identity_uses_symbolic_simplification():
    result = calculate_condition(
        {
            "symbols": {"k": "real"},
            "expressions": {"left": "(k+1)**2", "right": "k**2 + 2*k + 1"},
            "predicate": "left == right and not (left != right)",
        },
        {},
    )
    assert result["status"] == "holds"


@pytest.mark.parametrize(
    ("assumption", "formula", "predicate", "status"),
    [
        ("positive", "1/k", "answer > 0", "holds"),
        ("nonnegative", "sqrt(k)", "answer**2 == k", "holds"),
        ("real", "sqrt(k**2)", "answer == abs(k)", "holds"),
        ("integer", "abs(k)", "answer >= 0", "holds"),
        ("real", "k+1", "answer > k", "holds"),
        ("real", "1/k", "answer == answer", "unknown"),
        ("nonnegative", "1/k", "answer == answer", "unknown"),
        ("real", "sqrt(k)", "answer > 0", "unknown"),
        ("real", "k**(1/2)", "answer > 0", "unknown"),
    ],
)
def test_supported_assumptions_and_uncertain_domains(assumption, formula, predicate, status):
    result = calculate_condition(
        {
            "symbols": {"k": assumption},
            "expressions": {"answer": formula},
            "predicate": predicate,
        },
        {},
    )
    assert result["status"] == status


@pytest.mark.parametrize(
    ("predicate", "status"),
    [
        ("1 < 2 <= 2 and 3 > 2 >= 2", "holds"),
        ("1 == 1 and 1 != 2", "holds"),
        ("not (1 >= 2 or 1 > 2)", "holds"),
        ("2 < 1", "fails"),
        ("k > 1 or 1 == 1", "holds"),
        ("k > 1 and 1 == 2", "fails"),
        ("k > 1 and 1 == 1", "unknown"),
        ("k > 1 or 1 == 2", "unknown"),
        ("not (k > 1)", "unknown"),
        ("1 < k < 0", "fails"),
    ],
)
def test_comparisons_and_three_valued_logic(predicate, status):
    result = calculate_condition(
        {"symbols": {"k": "positive"}, "expressions": {}, "predicate": predicate}, {}
    )
    assert result["status"] == status


def test_multiple_named_comparisons_composed_in_final_predicate():
    result = calculate_condition(
        {
            "expressions": {
                "total": "sum(xs)",
                "enough": "total >= 6",
                "bounded": "min(xs) > 0 and max(xs) <= 3",
                "distinct": "xs[0] != xs[1]",
                "invalid": "not (enough and bounded)",
                "alias": "distinct",
            },
            "predicate": "enough and bounded and alias and not invalid",
        },
        {"xs": [1, 2, 3]},
    )
    assert result["status"] == "holds"
    assert result["computed"] == {
        "total": "6",
        "enough": "True",
        "bounded": "True",
        "distinct": "True",
        "invalid": "False",
        "alias": "True",
    }


@pytest.mark.parametrize(
    ("formula", "computed", "status"),
    [
        ("uncertain", "unknown", "unknown"),
        ("not uncertain", "unknown", "unknown"),
        ("uncertain or yes", "True", "holds"),
        ("yes or uncertain", "True", "holds"),
        ("uncertain and no", "False", "fails"),
        ("no and uncertain", "False", "fails"),
        ("uncertain and yes", "unknown", "unknown"),
        ("uncertain or no", "unknown", "unknown"),
        ("not (uncertain or yes)", "False", "fails"),
        ("not (uncertain and no)", "True", "holds"),
    ],
)
def test_unknown_boolean_intermediates_preserve_three_valued_logic(formula, computed, status):
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {
                "uncertain": "k > 1",
                "yes": "1 == 1",
                "no": "1 == 2",
                "combined": formula,
            },
            "predicate": "combined",
        },
        {},
    )
    assert result["status"] == status
    assert result["computed"]["uncertain"] == "unknown"
    assert result["computed"]["combined"] == computed


@pytest.mark.parametrize(
    ("predicate", "status"),
    [("uncertain", "unknown"), ("uncertain or yes", "holds"), ("uncertain and no", "fails")],
)
@pytest.mark.parametrize("formula", ["k > 1", "missing > 0", "sqrt(k-2) > 0"])
def test_final_predicate_can_short_circuit_unknown_named_conditions(formula, predicate, status):
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {"uncertain": formula, "yes": "1 == 1", "no": "1 == 2"},
            "predicate": predicate,
        },
        {},
    )
    assert result["status"] == status
    assert result["computed"]["uncertain"] == "unknown"


@pytest.mark.parametrize("value", [0, 1, -1])
@pytest.mark.parametrize("predicate", ["amount", "not amount", "amount and 1 == 1"])
def test_scalar_names_are_not_coerced_to_boolean(value, predicate):
    result = calculate_condition(
        {"expressions": {"amount": "x"}, "predicate": predicate}, {"x": value}
    )
    assert result["status"] == "unsupported"
    assert "not a Boolean condition" in result["reason"]


def test_scalar_used_as_boolean_in_intermediate_is_unsupported():
    result = calculate_condition(
        {"expressions": {"amount": "1", "check": "amount and 1 == 1"}, "predicate": "check"},
        {},
    )
    assert result["status"] == "unsupported"
    assert result["computed"] == {"amount": "1"}


@pytest.mark.parametrize("predicate", ["missing", "not missing"])
def test_unbound_boolean_names_are_unknown_not_false(predicate):
    result = calculate_condition({"expressions": {}, "predicate": predicate}, {})
    assert result["status"] == "unknown"
    assert "not bound" in result["reason"]


@pytest.mark.parametrize("name", ["k", "row"])
def test_symbol_and_list_names_are_not_boolean_conditions(name):
    result = calculate_condition(
        {"symbols": {"k": "real"}, "expressions": {}, "predicate": name}, {"row": [1]}
    )
    assert result["status"] == "unsupported"
    assert "not a Boolean condition" in result["reason"]


@pytest.mark.parametrize("value", [True, False])
def test_boolean_input_quantities_remain_invalid(value):
    result = calculate_condition({"expressions": {}, "predicate": "flag"}, {"flag": value})
    assert result["status"] == "fails"
    assert "quantity" in result["reason"]


def test_false_named_numeric_check_is_failure_not_unknown():
    result = calculate_condition(
        {
            "expressions": {"mean": "sum(xs)/len(xs)", "check": "mean == 4", "alias": "check"},
            "predicate": "alias",
        },
        {"xs": [2, 4]},
    )
    assert result["status"] == "fails"
    assert result["computed"] == {"mean": "3", "check": "False", "alias": "False"}
    assert result["reason"] == "predicate is false"


@pytest.mark.parametrize("condition", ["1 == 1", "1 == 2", "k > 1"])
@pytest.mark.parametrize("formula", ["flag + 1", "sum([flag])", "flag == 1", "abs(flag)"])
def test_boolean_intermediates_cannot_be_numeric_operands(condition, formula):
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {"flag": condition, "answer": formula},
            "predicate": "answer > 0",
        },
        {},
    )
    assert result["status"] == "unsupported"
    assert "scalar quantity" in result["reason"]


@pytest.mark.parametrize(
    "formula",
    [
        "yes or x.__class__ == 1",
        "no and __import__('os') == 1",
        "yes or open('file') == 1",
        "yes or sqrt() == 1",
    ],
)
def test_boolean_intermediate_syntax_is_prevalidated_in_unused_branches(formula):
    result = calculate_condition(
        {
            "expressions": {"yes": "1 == 1", "no": "1 == 2", "answer": formula},
            "predicate": "answer",
        },
        {"x": 1},
    )
    assert result["status"] == "unsupported"
    assert result["computed"] == {}


@pytest.mark.parametrize("formula", ["1/(x-x) > 0", "sqrt(-x) > 0"])
def test_undefined_numeric_boolean_intermediate_remains_failure(formula):
    result = calculate_condition(
        {"expressions": {"check": formula}, "predicate": "check or 1 == 1"}, {"x": 1}
    )
    assert result["status"] == "fails"
    assert result["computed"] == {}


def test_list_intermediates_and_function_forms():
    result = calculate_condition(
        {
            "expressions": {
                "parts": "[abs(x), +y, -x]",
                "total": "sum(parts)",
                "count": "len(parts)",
                "small": "min(parts)",
                "large": "max(x, y, total)",
                "inverse": "2**-2",
            },
            "predicate": (
                "total == 7 and count == 3 and small == 2 and large == 7 and inverse == 1/4"
            ),
        },
        {"x": -2, "y": 3},
    )
    assert result["status"] == "holds"
    assert result["computed"]["parts"] == "[2, 3, 2]"


def test_nested_numeric_matrix_indexing_and_row_functions():
    result = calculate_condition(
        {
            "expressions": {
                "entry": "matrix[0][1]",
                "row": "matrix[1]",
                "total": "sum(row)",
                "small": "min(row)",
                "large": "max(row)",
                "rows": "len(matrix)",
            },
            "predicate": "entry == 1/5 and total == 7 and small == 3 and large == 4 and rows == 2",
        },
        {"matrix": [[0.1, 0.2], [3, 4]]},
    )
    assert result["status"] == "holds"
    assert result["computed"]["entry"] == "1/5"
    assert result["computed"]["row"] == "[3, 4]"


def test_nested_expression_lists_and_data_rows():
    result = calculate_condition(
        {
            "expressions": {
                "matrix": "[[x, sqrt(4)], row, [x/2, 1/3]]",
                "entry": "matrix[2][1]",
                "nested": "[matrix]",
            },
            "predicate": "entry == 1/3 and nested[0][1][0] == 5 and matrix[0][0] == 2",
        },
        {"x": 2, "row": [5, 6]},
    )
    assert result["status"] == "holds"
    assert result["computed"]["matrix"] == "[[2, 2], [5, 6], [1, 1/3]]"


@pytest.mark.parametrize(
    "formula",
    ["sum(matrix)", "min(matrix)", "max(matrix)", "min(1, matrix)", "max(matrix, 1)"],
)
def test_nested_aggregate_operands_are_unsupported(formula):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 0"},
        {"matrix": [[1, 2], [3, 4]]},
    )
    assert result["status"] == "unsupported"
    assert "scalar" in result["reason"]


@pytest.mark.parametrize("depth", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("source", ["data", "expression"])
def test_list_nesting_is_bounded(depth, source):
    value = 1
    for _ in range(depth):
        value = [value]
    formula = "matrix" if source == "data" else "[" * depth + "1" + "]" * depth
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "len(answer) == 1"},
        {"matrix": value} if source == "data" else {},
    )
    assert result["status"] == ("unsupported" if depth > 4 else "holds")
    if depth > 4:
        assert "nesting limit" in result["reason"]


def test_nested_list_total_size_is_bounded_for_data_and_expression_results():
    matrix = [[1] * 128] * 4
    for formula, values in (
        ("matrix", {"matrix": matrix}),
        ("[row, row, row, row]", {"row": [1] * 128}),
    ):
        result = calculate_condition(
            {"expressions": {"answer": formula}, "predicate": "len(answer) == 4"}, values
        )
        assert result["status"] == "unsupported"
        assert "total size limit" in result["reason"]


def test_expression_list_nesting_limit_includes_referenced_data():
    result = calculate_condition(
        {"expressions": {"answer": "[matrix]"}, "predicate": "len(answer) == 1"},
        {"matrix": [[[[1]]]]},
    )
    assert result["status"] == "unsupported"
    assert "nesting limit" in result["reason"]


def test_nested_list_length_and_cycles_are_bounded():
    cyclic = []
    cyclic.append(cyclic)
    for value, reason in (([[1] * 129], "length limit"), (cyclic, "nesting limit")):
        result = calculate_condition(
            {"expressions": {}, "predicate": "1 == 1"}, {"matrix": value}
        )
        assert result["status"] == "unsupported"
        assert reason in result["reason"]


@pytest.mark.parametrize(
    ("formula", "reason"),
    [("1/matrix[0][0]", "division by zero"), ("sqrt(matrix[0][1])", "nonnegative")],
)
def test_nested_numeric_domain_errors_remain_repairable_failures(formula, reason):
    calculation = {"expressions": {"answer": formula}, "predicate": "answer > 0"}
    result = calculate_condition(calculation, {"matrix": [[0, -1]]})
    assert result["status"] == "fails"
    assert reason in result["reason"]
    assert calculate_condition(calculation, {"matrix": [[1, 4]]})["status"] == "holds"


def test_missing_value_and_forward_reference_are_not_false():
    for expressions in ({"answer": "missing+1"}, {"answer": "later+1", "later": "1"}):
        result = calculate_condition(
            {"expressions": expressions, "predicate": "answer > 0"}, {}
        )
        assert result["status"] == "unknown"
        assert "not bound" in result["reason"]
    ordered = calculate_condition(
        {"expressions": {"first": "1", "answer": "1/0"}, "predicate": "answer > 0"}, {}
    )
    assert ordered["status"] == "fails"
    assert ordered["computed"] == {"first": "1"}


@pytest.mark.parametrize(
    "quantity",
    [True, False, float("nan"), float("inf"), -float("inf"), "1/2", None, {}, [True], [[False]]],
)
def test_invalid_quantities_fail_with_reason(quantity):
    result = calculate_condition(
        {"expressions": {"answer": "1"}, "predicate": "answer == 1"}, {"x": quantity}
    )
    assert result["status"] == "fails"
    assert "value 'x'" in result["reason"]
    assert result["computed"] == {}


@pytest.mark.parametrize(
    ("formula", "reason"),
    [
        ("1/x", "division by zero"),
        ("sqrt(-1)", "nonnegative"),
        ("(-1)**(1/2)", "nonnegative"),
        ("0**-1", "zero"),
        ("0**0", "zero"),
        ("1e999", "non-finite"),
    ],
)
def test_undefined_numeric_calculations_are_concrete_failures(formula, reason):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 0"},
        {"x": 0, "xs": [1]},
    )
    assert result["status"] == "fails"
    assert reason in result["reason"]


@pytest.mark.parametrize(
    ("formula", "reason"),
    [
        ("sqrt(xs)", "scalar"),
        ("abs(xs)", "scalar"),
        ("sum(x)", "list"),
        ("len(x)", "list"),
        ("min([])", "nonempty"),
        ("max([])", "nonempty"),
        ("min(x)", "list"),
        ("sqrt()", "one argument"),
        ("sqrt(missing, 1)", "one argument"),
        ("sum(xs, 1)", "one argument"),
        ("len()", "one argument"),
        ("abs(1, 2)", "one argument"),
        ("min()", "nonempty"),
        ("max()", "nonempty"),
        ("xs + 1", "scalar"),
        ("xs[1]", "out of range"),
        ("x[0]", "list"),
        ("[[1]][0][1]", "out of range"),
        ("matrix[1][1]", "out of range"),
    ],
)
def test_fixed_arity_and_operand_shapes_are_unsupported(formula, reason):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 0"},
        {"x": 0, "xs": [1], "matrix": [[1, 2], [3]]},
    )
    assert result["status"] == "unsupported"
    assert reason in result["reason"]


def test_algebraically_zero_symbolic_denominator_is_rejected():
    result = calculate_condition(
        {
            "symbols": {"k": "real"},
            "expressions": {"answer": "1/((k+1)**2 - (k*k + 2*k + 1))"},
            "predicate": "answer > 0",
        },
        {},
    )
    assert result["status"] == "fails"
    assert "division by zero" in result["reason"]


@pytest.mark.parametrize(
    "formula",
    [
        "True",
        "'1'",
        "2**17",
        "2**(1/17)",
        "2**k",
        "xs[-1]",
        "xs[True]",
        "xs[:1]",
        "sum(xs, start=0)",
        "min(*xs)",
        "(1, 2)",
        "{1: 2}",
        "'x' + 'y'",
        "2**(2**16)",
        "1e-9999999",
        "k**16**16",
        "((k**16)**16)**16",
    ],
)
def test_unsupported_shapes_and_powers(formula):
    result = calculate_condition(
        {
            "symbols": {"k": "positive"},
            "expressions": {"answer": formula},
            "predicate": "answer == 0",
        },
        {"xs": [1]},
    )
    assert result["status"] == "unsupported"


@pytest.mark.parametrize(
    "predicate",
    [
        "answer",
        "True",
        "answer in [1]",
        "answer is answer",
        "1 == 1 or answer.__class__ == 1",
        "1 == 1 or __import__('os') == 1",
        "(answer > 0) & (answer < 2)",
    ],
)
def test_unsupported_predicate_syntax_even_in_unused_branches(predicate):
    result = calculate_condition({"expressions": {"answer": "1"}, "predicate": predicate}, {})
    assert result["status"] == "unsupported"


@pytest.mark.parametrize(
    ("calculation", "values"),
    [
        (None, {}),
        ({"expressions": {}, "predicate": "1 == 1"}, None),
        ({"predicate": "1 == 1"}, {}),
        ({"expressions": [], "predicate": "1 == 1"}, {}),
        ({"expressions": {}, "symbols": [], "predicate": "1 == 1"}, {}),
        ({"expressions": {}, "symbols": {"k": "complex"}, "predicate": "1 == 1"}, {}),
        ({"expressions": {}, "symbols": {"k": ["positive"]}, "predicate": "1 == 1"}, {}),
        ({"expressions": {"x": "1"}, "predicate": "x == 1"}, {"x": 1}),
        ({"expressions": {}, "symbols": {"k": "real"}, "predicate": "k == 1"}, {"k": 1}),
        ({"expressions": {"k": "1"}, "symbols": {"k": "real"}, "predicate": "k == 1"}, {}),
        ({"expressions": {"bad label": "1"}, "predicate": "1 == 1"}, {}),
        ({"expressions": {"sum": "1"}, "predicate": "1 == 1"}, {}),
        ({"expressions": {}, "predicate": "1 == 1"}, {"sqrt": 1}),
        ({"expressions": {}, "predicate": "1 == 1"}, {"__secret": 1}),
        ({"expressions": {"answer": ""}, "predicate": "1 == 1"}, {}),
        ({"expressions": {}, "predicate": None}, {}),
        ({"expressions": {"answer": "1 +"}, "predicate": "1 == 1"}, {}),
    ],
)
def test_invalid_specs_and_name_collisions_are_unsupported(calculation, values):
    result = calculate_condition(calculation, values)
    assert result["status"] == "unsupported"
    assert result["reason"]


@pytest.mark.parametrize(
    "formula",
    ["1" * 4097, "+".join(["1"] * 150), "-" * 45 + "1", "(2**16)**16**16"],
)
def test_expression_resource_limits(formula):
    result = calculate_condition(
        {"expressions": {"answer": formula}, "predicate": "answer == 1"}, {}
    )
    assert result["status"] == "unsupported"
    assert "limit" in result["reason"] or "bounded" in result["reason"]


@pytest.mark.parametrize(
    "values",
    [{"xs": [1] * 129}, {"x": 1 << 4096}, {f"x{i}": i for i in range(65)}],
)
def test_data_resource_limits(values):
    result = calculate_condition({"expressions": {}, "predicate": "1 == 1"}, values)
    assert result["status"] == "unsupported"
