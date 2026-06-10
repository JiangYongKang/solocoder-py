from __future__ import annotations

from typing import Iterator, List, Optional

from .models import Event


class MemoryEventSource:
    def __init__(self, events: Optional[List[Event]] = None) -> None:
        self._events: List[Event] = list(events) if events else []
        self._cursor: int = 0

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def remaining_events(self) -> int:
        return len(self._events) - self._cursor

    def add_event(self, event: Event) -> None:
        self._events.append(event)

    def add_events(self, events: List[Event]) -> None:
        self._events.extend(events)

    def has_next(self) -> bool:
        return self._cursor < len(self._events)

    def next_event(self) -> Optional[Event]:
        if not self.has_next():
            return None
        event = self._events[self._cursor]
        self._cursor += 1
        return event

    def peek(self) -> Optional[Event]:
        if not self.has_next():
            return None
        return self._events[self._cursor]

    def reset(self) -> None:
        self._cursor = 0

    def __iter__(self) -> Iterator[Event]:
        return self

    def __next__(self) -> Event:
        event = self.next_event()
        if event is None:
            raise StopIteration
        return event

    def __len__(self) -> int:
        return self.remaining_events
