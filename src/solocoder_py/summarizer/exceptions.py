from __future__ import annotations


class SummarizerError(Exception):
    pass


class SummarizerInvalidParameterError(SummarizerError):
    pass


class SummarizerInvalidInputError(SummarizerError):
    pass
