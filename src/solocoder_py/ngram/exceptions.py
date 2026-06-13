from __future__ import annotations


class NGramError(Exception):
    pass


class DocumentExistsError(NGramError):
    pass


class DocumentNotFoundError(NGramError):
    pass


class EmptyQueryError(NGramError):
    pass


class InvalidNValueError(NGramError):
    pass


class InvalidContextSizeError(NGramError):
    pass
