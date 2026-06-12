from __future__ import annotations


class AuditLogError(Exception):
    pass


class EmptyAuditLogError(AuditLogError):
    pass


class TimestampRegressionError(AuditLogError):
    def __init__(self, new_timestamp: float, last_timestamp: float) -> None:
        self.new_timestamp = new_timestamp
        self.last_timestamp = last_timestamp
        super().__init__(
            f"New timestamp {new_timestamp} is earlier than last timestamp {last_timestamp}"
        )


class InvalidIndexError(AuditLogError):
    pass
