from __future__ import annotations


class RateCapError(Exception):
    pass


class InvalidWindowConfigError(RateCapError):
    pass


class OperationRejectedError(RateCapError):
    def __init__(
        self,
        subject_id: str | None,
        dimension: str,
        window_name: str,
        used: int,
        limit: int,
    ) -> None:
        self.subject_id = subject_id
        self.dimension = dimension
        self.window_name = window_name
        self.used = used
        self.limit = limit
        reason = (
            f"Operation rejected at {dimension} dimension, "
            f"window='{window_name}', used={used}, limit={limit}"
        )
        if subject_id is not None:
            reason = f"subject='{subject_id}', {reason}"
        super().__init__(reason)


class SubjectNotFoundError(RateCapError):
    pass
