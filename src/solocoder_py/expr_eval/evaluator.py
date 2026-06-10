from __future__ import annotations

from solocoder_py.expr_eval.exceptions import (
    DivisionByZeroError,
    EmptyExpressionError,
    MismatchedParenthesisError,
    ParseError,
)
from solocoder_py.expr_eval.tokenizer import Token, TokenType, Tokenizer


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> float:
        if (
            len(self._tokens) == 1
            and self._tokens[0].type == TokenType.EOF
        ):
            raise EmptyExpressionError("Expression is empty")
        result = self._expression()
        if self._current().type == TokenType.RPAREN:
            raise MismatchedParenthesisError(
                f"Unexpected closing parenthesis at position {self._current().position}"
            )
        self._expect(TokenType.EOF)
        return result

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _expect(self, expected: TokenType) -> Token:
        token = self._current()
        if token.type != expected:
            raise ParseError(
                f"Expected {expected.name} but got {token.type.name} at position {token.position}"
            )
        return self._advance()

    def _expression(self) -> float:
        result = self._term()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance()
            right = self._term()
            if op.type == TokenType.PLUS:
                result = result + right
            else:
                result = result - right
        return result

    def _term(self) -> float:
        result = self._factor()
        while self._current().type in (TokenType.MULTIPLY, TokenType.DIVIDE):
            op = self._advance()
            right = self._factor()
            if op.type == TokenType.MULTIPLY:
                result = result * right
            else:
                if right == 0:
                    raise DivisionByZeroError(
                        f"Division by zero at position {op.position}"
                    )
                result = result / right
        return result

    def _factor(self) -> float:
        token = self._current()
        if token.type == TokenType.NUMBER:
            self._advance()
            return float(token.value)
        if token.type == TokenType.LPAREN:
            self._advance()
            result = self._expression()
            if self._current().type != TokenType.RPAREN:
                raise MismatchedParenthesisError(
                    f"Missing closing parenthesis at position {token.position}"
                )
            self._advance()
            return result
        if token.type == TokenType.RPAREN:
            raise MismatchedParenthesisError(
                f"Unexpected closing parenthesis at position {token.position}"
            )
        if token.type == TokenType.MINUS:
            self._advance()
            return -self._factor()
        if token.type == TokenType.PLUS:
            self._advance()
            return self._factor()
        raise ParseError(
            f"Unexpected token {token.type.name} at position {token.position}"
        )


class ExprEvaluator:
    def evaluate(self, expression: str) -> float:
        if expression is None:
            raise EmptyExpressionError("Expression is None")
        stripped = expression.strip()
        if not stripped:
            raise EmptyExpressionError("Expression is empty")
        tokenizer = Tokenizer(stripped)
        parser = Parser(tokenizer.tokens)
        return parser.parse()
