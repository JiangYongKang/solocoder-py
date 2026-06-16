from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class Direction(str, Enum):
    NEXT = "next"
    PREV = "prev"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class SortField:
    name: str
    order: SortOrder = SortOrder.ASC

    def __post_init__(self) -> None:
        if isinstance(self.order, str):
            self.order = SortOrder(self.order.lower())


@dataclass(frozen=True)
class DecodedCursor:
    sort_values: tuple[Any, ...]
    direction: Direction
    created_at: float
    version: int = 1


@dataclass
class PageResult:
    data: list[dict[str, Any]]
    page_size: int
    has_next: bool
    has_prev: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None
    total: Optional[int] = None
    total_estimated: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "data": self.data,
            "page_size": self.page_size,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "start_cursor": self.start_cursor,
            "end_cursor": self.end_cursor,
        }
        if self.total is not None:
            result["total"] = self.total
            result["total_estimated"] = self.total_estimated
        return result


@dataclass
class PaginationConfig:
    max_page_size: int = 100
    default_page_size: int = 20
    cursor_ttl_seconds: Optional[float] = None
    cursor_secret: Optional[str] = None
    enable_hmac: bool = True
    estimate_total_fn: Optional[Callable[[], int]] = None
