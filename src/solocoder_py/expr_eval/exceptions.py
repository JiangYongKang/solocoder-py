from __future__ import annotations


class ExprEvalError(Exception):
    pass


class TokenizeError(ExprEvalError):
    pass


class ParseError(ExprEvalError):
    pass


class EvaluateError(ExprEvalError):
    pass


class DivisionByZeroError(EvaluateError):
    pass


class EmptyExpressionError(ExprEvalError):
    pass


class MismatchedParenthesisError(ParseError):
    pass


class InvalidCharacterError(TokenizeError):
    pass
