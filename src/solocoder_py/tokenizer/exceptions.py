from __future__ import annotations


class TokenizerError(Exception):
    pass


class EmptyInputError(TokenizerError):
    pass


class InvalidTextError(TokenizerError):
    pass
