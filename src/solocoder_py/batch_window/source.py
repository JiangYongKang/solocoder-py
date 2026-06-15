from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import Event


@dataclass
class MemoryEventSource:
    _events: List[Event] = field(default_factory=list)
    _current_index: int = 0

    def add_event(self, event: Event) -> None:
        self._events.append(event)

    def add_events(self, events: List[Event]) -> None:
        self._events.extend(events)

    def has_next(self) -> bool:
        return self._current_index < len(self._events)

    def next(self) -> Event:
        if not self.has_next():
            raise StopIteration("No more events available")
        event = self._events[self._current_index]
        self._current_index += 1
        return event

    def peek(self) -> Event | None:
        if not self.has_next():
            return None
        return self._events[self._current_index]

    def remaining_count(self) -> int:
        return len(self._events) - self._current_index

    def total_count(self) -> int:
        return len(self._events)

    def reset(self) -> None:
        self._current_index = 0

    def clear(self) -> None:
        self._events.clear()
        self._current_index = 0

    def get_all_events(self) -> List[Event]:
        return list(self._events)

    def __iter__(self):
        return self

    def __next__(self) -> Event:
        return self.next()
