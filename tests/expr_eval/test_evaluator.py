import math

import pytest

from solocoder_py.expr_eval import (
    DivisionByZeroError,
    EmptyExpressionError,
    ExprEvalError,
    ExprEvaluator,
    InvalidCharacterError,
    MismatchedParenthesisError,
    ParseError,
    TokenizeError,
)


@pytest.fixture
def evaluator():
    return ExprEvaluator()


class TestBasicArithmetic:
    def test_addition(self, evaluator):
        assert evaluator.evaluate("2 + 3") == 5.0

    def test_subtraction(self, evaluator):
        assert evaluator.evaluate("10 - 4") == 6.0

    def test_multiplication(self, evaluator):
        assert evaluator.evaluate("3 * 4") == 12.0

    def test_division(self, evaluator):
        assert evaluator.evaluate("10 / 2") == 5.0

    def test_negative_result(self, evaluator):
        assert evaluator.evaluate("3 - 7") == -4.0

    def test_large_numbers(self, evaluator):
        assert evaluator.evaluate("1000000 + 2000000") == 3000000.0

    def test_addition_three_operands(self, evaluator):
        assert evaluator.evaluate("1 + 2 + 3") == 6.0

    def test_subtraction_three_operands(self, evaluator):
        assert evaluator.evaluate("10 - 3 - 2") == 5.0


class TestOperatorPrecedence:
    def test_multiplication_before_addition(self, evaluator):
        assert evaluator.evaluate("2 + 3 * 4") == 14.0

    def test_division_before_addition(self, evaluator):
        assert evaluator.evaluate("2 + 8 / 2") == 6.0

    def test_multiplication_before_subtraction(self, evaluator):
        assert evaluator.evaluate("10 - 2 * 3") == 4.0

    def test_division_before_subtraction(self, evaluator):
        assert evaluator.evaluate("10 - 8 / 2") == 6.0

    def test_left_to_right_same_precedence_add_sub(self, evaluator):
        assert evaluator.evaluate("10 - 3 + 2") == 9.0

    def test_left_to_right_same_precedence_mul_div(self, evaluator):
        assert evaluator.evaluate("12 / 3 * 2") == 8.0

    def test_complex_precedence(self, evaluator):
        assert evaluator.evaluate("2 + 3 * 4 - 6 / 2") == 11.0

    def test_precedence_with_multiple_mul(self, evaluator):
        assert evaluator.evaluate("1 + 2 * 3 * 4 + 5") == 30.0


class TestParentheses:
    def test_parentheses_override_precedence(self, evaluator):
        assert evaluator.evaluate("(2 + 3) * 4") == 20.0

    def test_nested_parentheses(self, evaluator):
        assert evaluator.evaluate("((2 + 3)) * 4") == 20.0

    def test_deeply_nested_parentheses(self, evaluator):
        assert evaluator.evaluate("(((1 + 2) * 3) - 4)") == 5.0

    def test_parentheses_with_division(self, evaluator):
        assert evaluator.evaluate("(8 + 2) / 5") == 2.0

    def test_multiple_independent_parentheses(self, evaluator):
        assert evaluator.evaluate("(1 + 2) * (3 + 4)") == 21.0

    def test_nested_four_levels(self, evaluator):
        assert evaluator.evaluate("((((3))))") == 3.0

    def test_nested_five_levels(self, evaluator):
        assert evaluator.evaluate("((((1 + 2) * (3 + 4)) - 5) / 2)") == 8.0

    def test_complex_nested_expression(self, evaluator):
        assert evaluator.evaluate("((2 + 3) * (7 - 5)) + 1") == 11.0


class TestIntegerOperations:
    def test_single_integer(self, evaluator):
        assert evaluator.evaluate("42") == 42.0

    def test_zero(self, evaluator):
        assert evaluator.evaluate("0") == 0.0

    def test_large_integer(self, evaluator):
        assert evaluator.evaluate("999999") == 999999.0

    def test_integer_addition(self, evaluator):
        assert evaluator.evaluate("100 + 200") == 300.0

    def test_integer_result_is_float(self, evaluator):
        result = evaluator.evaluate("4 + 5")
        assert isinstance(result, float)


class TestFloatOperations:
    def test_single_float(self, evaluator):
        assert evaluator.evaluate("3.14") == pytest.approx(3.14)

    def test_float_addition(self, evaluator):
        assert evaluator.evaluate("1.5 + 2.5") == pytest.approx(4.0)

    def test_float_subtraction(self, evaluator):
        assert evaluator.evaluate("5.5 - 1.5") == pytest.approx(4.0)

    def test_float_multiplication(self, evaluator):
        assert evaluator.evaluate("2.5 * 4.0") == pytest.approx(10.0)

    def test_float_division(self, evaluator):
        assert evaluator.evaluate("7.5 / 2.5") == pytest.approx(3.0)

    def test_float_precision(self, evaluator):
        assert evaluator.evaluate("0.1 + 0.2") == pytest.approx(0.3)

    def test_float_multiply_precision(self, evaluator):
        assert evaluator.evaluate("0.1 * 0.2") == pytest.approx(0.02)

    def test_mixed_int_float(self, evaluator):
        assert evaluator.evaluate("3 + 1.5") == pytest.approx(4.5)

    def test_float_with_leading_dot(self, evaluator):
        assert evaluator.evaluate(".5 + .5") == pytest.approx(1.0)

    def test_float_with_trailing_dot(self, evaluator):
        assert evaluator.evaluate("5. + 3.") == pytest.approx(8.0)

    def test_complex_float_expression(self, evaluator):
        assert evaluator.evaluate("1.1 + 2.2 * 3.0") == pytest.approx(7.7)

    def test_division_precision(self, evaluator):
        assert evaluator.evaluate("1 / 3") == pytest.approx(1.0 / 3.0)


class TestUnaryOperators:
    def test_unary_minus(self, evaluator):
        assert evaluator.evaluate("-5") == -5.0

    def test_unary_plus(self, evaluator):
        assert evaluator.evaluate("+5") == 5.0

    def test_unary_minus_in_expression(self, evaluator):
        assert evaluator.evaluate("3 + -2") == 1.0

    def test_unary_plus_in_expression(self, evaluator):
        assert evaluator.evaluate("3 + +2") == 5.0

    def test_double_unary_minus(self, evaluator):
        assert evaluator.evaluate("--5") == 5.0

    def test_unary_minus_in_parentheses(self, evaluator):
        assert evaluator.evaluate("(-3) * 2") == -6.0

    def test_unary_minus_before_parentheses(self, evaluator):
        assert evaluator.evaluate("-(2 + 3)") == -5.0


class TestWhitespaceHandling:
    def test_no_spaces(self, evaluator):
        assert evaluator.evaluate("2+3*4") == 14.0

    def test_extra_spaces(self, evaluator):
        assert evaluator.evaluate("  2  +  3  ") == 5.0

    def test_tabs(self, evaluator):
        assert evaluator.evaluate("2\t+\t3") == 5.0

    def test_mixed_whitespace(self, evaluator):
        assert evaluator.evaluate(" 2  + \t 3 ") == 5.0


class TestSingleNumberExpression:
    def test_single_positive_integer(self, evaluator):
        assert evaluator.evaluate("42") == 42.0

    def test_single_float(self, evaluator):
        assert evaluator.evaluate("3.14") == pytest.approx(3.14)

    def test_single_zero(self, evaluator):
        assert evaluator.evaluate("0") == 0.0

    def test_single_negative(self, evaluator):
        assert evaluator.evaluate("-7") == -7.0

    def test_single_in_parentheses(self, evaluator):
        assert evaluator.evaluate("(42)") == 42.0


class TestDivisionByZero:
    def test_simple_division_by_zero(self, evaluator):
        with pytest.raises(DivisionByZeroError, match="Division by zero"):
            evaluator.evaluate("1 / 0")

    def test_division_by_zero_in_expression(self, evaluator):
        with pytest.raises(DivisionByZeroError):
            evaluator.evaluate("5 + 3 / 0")

    def test_division_by_zero_in_parentheses(self, evaluator):
        with pytest.raises(DivisionByZeroError):
            evaluator.evaluate("(1 + 2) / 0")

    def test_division_by_zero_float(self, evaluator):
        with pytest.raises(DivisionByZeroError):
            evaluator.evaluate("1.0 / 0.0")

    def test_division_by_zero_error_includes_position(self, evaluator):
        with pytest.raises(DivisionByZeroError, match="position"):
            evaluator.evaluate("1 / 0")

    def test_zero_numerator(self, evaluator):
        assert evaluator.evaluate("0 / 5") == 0.0


class TestMismatchedParentheses:
    def test_missing_closing_parenthesis(self, evaluator):
        with pytest.raises(MismatchedParenthesisError, match="Missing closing"):
            evaluator.evaluate("(2 + 3")

    def test_extra_closing_parenthesis(self, evaluator):
        with pytest.raises(MismatchedParenthesisError, match="Unexpected closing"):
            evaluator.evaluate("2 + 3)")

    def test_multiple_missing_closing(self, evaluator):
        with pytest.raises(MismatchedParenthesisError):
            evaluator.evaluate("((2 + 3)")

    def test_empty_parentheses(self, evaluator):
        with pytest.raises(ParseError, match="Empty parentheses"):
            evaluator.evaluate("()")


class TestInvalidCharacters:
    def test_letters(self, evaluator):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            evaluator.evaluate("2 + abc")

    def test_special_characters(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("2 @ 3")

    def test_single_letter(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("a")

    def test_error_includes_position(self, evaluator):
        with pytest.raises(InvalidCharacterError, match="position"):
            evaluator.evaluate("2 + x")

    def test_chinese_characters(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("1 + 二")

    def test_percent_sign(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("100 % 3")


class TestEmptyExpression:
    def test_empty_string(self, evaluator):
        with pytest.raises(EmptyExpressionError, match="empty"):
            evaluator.evaluate("")

    def test_whitespace_only(self, evaluator):
        with pytest.raises(EmptyExpressionError, match="empty"):
            evaluator.evaluate("   ")

    def test_none_expression(self, evaluator):
        with pytest.raises(EmptyExpressionError):
            evaluator.evaluate(None)


class TestInvalidNumberFormat:
    def test_lone_dot(self, evaluator):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            evaluator.evaluate(".")

    def test_dot_between_operators(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("2 + . + 3")


class TestExceptionHierarchy:
    def test_division_by_zero_is_evaluate_error(self):
        assert issubclass(DivisionByZeroError, ExprEvalError)

    def test_mismatched_parenthesis_is_parse_error(self):
        assert issubclass(MismatchedParenthesisError, ParseError)

    def test_parse_error_is_expr_eval_error(self):
        assert issubclass(ParseError, ExprEvalError)

    def test_tokenize_error_is_expr_eval_error(self):
        assert issubclass(TokenizeError, ExprEvalError)

    def test_invalid_character_is_tokenize_error(self):
        assert issubclass(InvalidCharacterError, TokenizeError)

    def test_empty_expression_is_expr_eval_error(self):
        assert issubclass(EmptyExpressionError, ExprEvalError)

    def test_all_errors_catchable_as_base(self, evaluator):
        errors = [
            (lambda: evaluator.evaluate(""), EmptyExpressionError),
            (lambda: evaluator.evaluate("1/0"), DivisionByZeroError),
            (lambda: evaluator.evaluate("(1+2"), MismatchedParenthesisError),
            (lambda: evaluator.evaluate("abc"), InvalidCharacterError),
        ]
        for fn, _ in errors:
            with pytest.raises(ExprEvalError):
                fn()


class TestEvaluatorNoCrash:
    def test_evaluator_survives_division_by_zero(self, evaluator):
        with pytest.raises(DivisionByZeroError):
            evaluator.evaluate("1 / 0")
        result = evaluator.evaluate("2 + 3")
        assert result == 5.0

    def test_evaluator_survives_invalid_char(self, evaluator):
        with pytest.raises(InvalidCharacterError):
            evaluator.evaluate("2 + x")
        result = evaluator.evaluate("4 * 5")
        assert result == 20.0

    def test_evaluator_survives_mismatched_parens(self, evaluator):
        with pytest.raises(MismatchedParenthesisError):
            evaluator.evaluate("(1 + 2")
        result = evaluator.evaluate("(1 + 2) * 3")
        assert result == 9.0

    def test_evaluator_reusable(self, evaluator):
        assert evaluator.evaluate("1 + 1") == 2.0
        assert evaluator.evaluate("2 * 3") == 6.0
        assert evaluator.evaluate("10 / 5") == 2.0


class TestEdgeCases:
    def test_very_long_expression(self, evaluator):
        expr = " + ".join(["1"] * 100)
        assert evaluator.evaluate(expr) == 100.0

    def test_consecutive_multiplications(self, evaluator):
        assert evaluator.evaluate("2 * 3 * 4 * 5") == 120.0

    def test_mixed_operations_complex(self, evaluator):
        assert evaluator.evaluate("(1 + 2) * 3 - 4 / 2 + (5 - 1)") == 11.0

    def test_deeply_nested_expression(self, evaluator):
        expr = "(((1 + 2) * (3 + 4) - 5) / 2 + 10) * 3"
        assert evaluator.evaluate(expr) == pytest.approx(54.0)

    def test_zero_in_expression(self, evaluator):
        assert evaluator.evaluate("0 * 100 + 5") == 5.0

    def test_float_result_from_int_division(self, evaluator):
        result = evaluator.evaluate("7 / 2")
        assert result == pytest.approx(3.5)
        assert isinstance(result, float)
