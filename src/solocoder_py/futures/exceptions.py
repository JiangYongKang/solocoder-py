from __future__ import annotations


class FutureError(Exception):
    pass


class FutureNotReadyError(FutureError):
    pass


class FutureAlreadySettledError(FutureError):
    pass


class TimeoutError(FutureError):
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"Future timed out after {timeout} seconds")
