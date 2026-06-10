from __future__ import annotations

from enum import Enum, auto

from solocoder_py.expr_eval.exceptions import InvalidCharacterError


class TokenType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


class Token:
    __slots__ = ("type", "value", "position")

    def __init__(self, type: TokenType, value: str, position: int) -> None:
        self.type = type
        self.value = value
        self.position = position

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, pos={self.position})"


class Tokenizer:
    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0
        self._tokens: list[Token] = []
        self._tokenize()

    @property
    def tokens(self) -> list[Token]:
        return self._tokens

    def _tokenize(self) -> None:
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch.isspace():
                self._pos += 1
                continue
            if ch.isdigit() or ch == ".":
                self._read_number()
            elif ch == "+":
                self._tokens.append(Token(TokenType.PLUS, "+", self._pos))
                self._pos += 1
            elif ch == "-":
                self._tokens.append(Token(TokenType.MINUS, "-", self._pos))
                self._pos += 1
            elif ch == "*":
                self._tokens.append(Token(TokenType.MULTIPLY, "*", self._pos))
                self._pos += 1
            elif ch == "/":
                self._tokens.append(Token(TokenType.DIVIDE, "/", self._pos))
                self._pos += 1
            elif ch == "(":
                self._tokens.append(Token(TokenType.LPAREN, "(", self._pos))
                self._pos += 1
            elif ch == ")":
                self._tokens.append(Token(TokenType.RPAREN, ")", self._pos))
                self._pos += 1
            else:
                raise InvalidCharacterError(
                    f"Invalid character '{ch}' at position {self._pos}"
                )
        self._tokens.append(Token(TokenType.EOF, "", self._pos))

    def _read_number(self) -> None:
        start = self._pos
        has_dot = False
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch.isdigit():
                self._pos += 1
            elif ch == "." and not has_dot:
                has_dot = True
                self._pos += 1
            else:
                break
        num_str = self._text[start : self._pos]
        if num_str == ".":
            raise InvalidCharacterError(
                f"Invalid character '.' at position {start}"
            )
        self._tokens.append(Token(TokenType.NUMBER, num_str, start))
