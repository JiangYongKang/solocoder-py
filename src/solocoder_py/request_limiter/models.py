from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .exceptions import InvalidLimitError


class LimitStatus(str, Enum):
    OK = "OK"
    TOO_LARGE = "TOO_LARGE"
    INCOMPLETE = "INCOMPLETE"


@dataclass
class LimitConfig:
    max_body_bytes: int
    chunk_size: int = 8192
    error_status_code: int = 413
    error_message: str = "Payload Too Large"

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.max_body_bytes, int) or self.max_body_bytes < 0:
            raise InvalidLimitError(self.max_body_bytes)
        if not isinstance(self.chunk_size, int) or self.chunk_size <= 0:
            raise InvalidLimitError(
                self.chunk_size,
                f"Invalid chunk_size: {self.chunk_size}. Must be a positive integer.",
            )
        if not isinstance(self.error_status_code, int) or self.error_status_code < 400:
            raise InvalidLimitError(
                self.error_status_code,
                f"Invalid error_status_code: {self.error_status_code}. Must be >= 400.",
            )


@dataclass
class LimitResult:
    status: LimitStatus
    total_read_bytes: int
    limit_bytes: int
    body: bytes | None = None
    error_message: str | None = None

    @property
    def is_ok(self) -> bool:
        return self.status == LimitStatus.OK

    @property
    def is_too_large(self) -> bool:
        return self.status == LimitStatus.TOO_LARGE

    @property
    def is_incomplete(self) -> bool:
        return self.status == LimitStatus.INCOMPLETE


@dataclass
class Request:
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    body_stream: Any = None
    expected_content_length: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None

    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class LimitStats:
    total_requests: int = 0
    accepted_requests: int = 0
    rejected_too_large: int = 0
    rejected_incomplete: int = 0
    total_bytes_read: int = 0
    max_observed_bytes: int = 0

    def record_result(self, result: LimitResult) -> None:
        self.total_requests += 1
        self.total_bytes_read += result.total_read_bytes
        if result.total_read_bytes > self.max_observed_bytes:
            self.max_observed_bytes = result.total_read_bytes
        if result.is_ok:
            self.accepted_requests += 1
        elif result.is_too_large:
            self.rejected_too_large += 1
        elif result.is_incomplete:
            self.rejected_incomplete += 1


Handler = Callable[[Request, bytes], Response]
