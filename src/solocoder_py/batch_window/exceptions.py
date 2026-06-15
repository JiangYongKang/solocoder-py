from __future__ import annotations


class BatchWindowError(Exception):
    pass


class InvalidWindowConfigError(BatchWindowError):
    pass


class LateEventDroppedError(BatchWindowError):
    def __init__(
        self,
        event_timestamp: float,
        window_end: float,
        allowed_lateness: float,
    ) -> None:
        self.event_timestamp = event_timestamp
        self.window_end = window_end
        self.allowed_lateness = allowed_lateness
        super().__init__(
            f"Event at {event_timestamp} dropped: window end {window_end} + "
            f"allowed lateness {allowed_lateness} has passed"
        )


class WindowAlreadyClosedError(BatchWindowError):
    def __init__(self, window_start: float, window_end: float) -> None:
        self.window_start = window_start
        self.window_end = window_end
        super().__init__(
            f"Window [{window_start}, {window_end}) is already closed and cannot accept events"
        )
