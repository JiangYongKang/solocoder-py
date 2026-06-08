from __future__ import annotations


class WalError(Exception):
    pass


class TruncatedLsnError(WalError):
    def __init__(self, lsn: int, min_readable_lsn: int) -> None:
        self.lsn = lsn
        self.min_readable_lsn = min_readable_lsn
        super().__init__(
            f"Log sequence number {lsn} has been truncated. "
            f"Minimum readable LSN is {min_readable_lsn}."
        )


class InvalidTruncateLsnError(WalError):
    def __init__(self, lsn: int, min_readable_lsn: int, max_lsn: int) -> None:
        self.lsn = lsn
        self.min_readable_lsn = min_readable_lsn
        self.max_lsn = max_lsn
        super().__init__(
            f"Invalid truncate LSN {lsn}: "
            f"must be >= {min_readable_lsn} and <= {max_lsn}."
        )


class LsnNotFoundError(WalError):
    def __init__(self, lsn: int, min_readable_lsn: int, max_lsn: int) -> None:
        self.lsn = lsn
        self.min_readable_lsn = min_readable_lsn
        self.max_lsn = max_lsn
        super().__init__(
            f"LSN {lsn} not found. "
            f"Valid range is [{min_readable_lsn}, {max_lsn}]."
        )


class EmptyWalError(WalError):
    pass
