from __future__ import annotations


class RequestLimiterError(Exception):
    pass


class PayloadTooLargeError(RequestLimiterError):
    def __init__(
        self,
        limit_bytes: int,
        received_bytes: int,
        message: str | None = None,
    ) -> None:
        self.limit_bytes = limit_bytes
        self.received_bytes = received_bytes
        if message is None:
            message = (
                f"Request body exceeds size limit: "
                f"received {received_bytes} bytes, limit {limit_bytes} bytes"
            )
        super().__init__(message)


class IncompleteReadError(RequestLimiterError):
    def __init__(
        self,
        received_bytes: int,
        expected_bytes: int | None = None,
        message: str | None = None,
    ) -> None:
        self.received_bytes = received_bytes
        self.expected_bytes = expected_bytes
        if message is None:
            if expected_bytes is not None:
                message = (
                    f"Incomplete request body read: "
                    f"received {received_bytes} of {expected_bytes} expected bytes"
                )
            else:
                message = (
                    f"Incomplete request body read: "
                    f"received {received_bytes} bytes before connection closed"
                )
        super().__init__(message)


class InvalidLimitError(RequestLimiterError):
    def __init__(self, limit: int, message: str | None = None) -> None:
        self.limit = limit
        if message is None:
            message = f"Invalid size limit: {limit}. Must be a non-negative integer."
        super().__init__(message)
