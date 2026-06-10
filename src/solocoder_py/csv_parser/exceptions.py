from __future__ import annotations


class CSVParserError(Exception):
    pass


class UnclosedQuoteError(CSVParserError):
    def __init__(self, position: int) -> None:
        self.position = position
        super().__init__(f"Unclosed quote detected at position {position}")


class UnexpectedQuoteError(CSVParserError):
    def __init__(self, position: int) -> None:
        self.position = position
        super().__init__(f"Unexpected quote character at position {position}")
