from __future__ import annotations


class FutureError(Exception):
    pass


class FutureNotReadyError(FutureError):
    pass


class FutureAlreadyCompletedError(FutureError):
    pass


class FutureTimeoutError(FutureError):
    pass


class AllCombinatorError(FutureError):
    def __init__(self, first_error: Exception) -> None:
        self.first_error: Exception = first_error
        super().__init__(f"All combinator failed: {first_error}")


class AnyCombinatorError(FutureError):
    def __init__(self, errors: list[Exception]) -> None:
        self.errors: list[Exception] = errors
        msgs = "; ".join(str(e) for e in errors)
        super().__init__(f"All futures failed in any combinator: [{msgs}]")
