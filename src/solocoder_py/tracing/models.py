from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import SpanAlreadyEndedError, SpanNotStartedError


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool
    parent_span_id: Optional[str] = None


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    sampled: bool
    parent_span_id: Optional[str] = None
    start_time: int = field(default_factory=lambda: time.time_ns())
    end_time: Optional[int] = None
    attributes: dict[str, str] = field(default_factory=dict)
    _children: list["Span"] = field(default_factory=list, repr=False)
    _ended: bool = field(default=False, repr=False)

    @property
    def is_ended(self) -> bool:
        return self._ended

    @property
    def duration_ns(self) -> int:
        if not self._ended:
            raise SpanNotStartedError(
                f"span '{self.name}' has not ended yet, cannot query duration"
            )
        assert self.end_time is not None
        return self.end_time - self.start_time

    @property
    def children(self) -> list["Span"]:
        return list(self._children)

    @property
    def context(self) -> TraceContext:
        return TraceContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            sampled=self.sampled,
            parent_span_id=self.parent_span_id,
        )

    def end(self) -> None:
        if self._ended:
            raise SpanAlreadyEndedError(
                f"span '{self.name}' has already been ended"
            )
        self.end_time = time.time_ns()
        self._ended = True

    def add_child(self, child: "Span") -> None:
        if self._ended:
            from .exceptions import CannotCreateChildSpanError

            raise CannotCreateChildSpanError(
                f"cannot create child span for already ended span '{self.name}'"
            )
        self._children.append(child)

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Optional[str]:
        return self.attributes.get(key)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sampled": self.sampled,
            "attributes": dict(self.attributes),
            "children": [child.to_dict() for child in self._children],
        }
