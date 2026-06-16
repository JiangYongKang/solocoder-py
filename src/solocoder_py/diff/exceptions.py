from __future__ import annotations


class DiffError(Exception):
    pass


class InvalidGranularityError(DiffError):
    def __init__(self, granularity: str) -> None:
        self.granularity = granularity
        super().__init__(f"Unsupported granularity: {granularity}")


class InvalidContextLinesError(DiffError):
    def __init__(self, context_lines: int) -> None:
        self.context_lines = context_lines
        super().__init__(f"Invalid context lines: {context_lines}, must be >= 0")
