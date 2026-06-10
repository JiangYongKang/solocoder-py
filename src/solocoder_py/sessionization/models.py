from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .exceptions import InvalidEventError, InvalidSubjectError


@dataclass
class SessionEvent:
    subject_id: str
    event_time: datetime
    event_type: str = "default"
    payload: Any = None

    def __post_init__(self) -> None:
        if not self.subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")
        if self.event_time is None:
            raise InvalidEventError("event_time cannot be None")


@dataclass
class Session:
    session_id: str
    subject_id: str
    start_time: datetime
    end_time: datetime
    event_count: int = 0
    is_active: bool = True
    events: list[SessionEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")
        if self.start_time > self.end_time:
            raise ValueError("start_time cannot be later than end_time")

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    def add_event(self, event: SessionEvent) -> None:
        self.events.append(event)
        self.event_count += 1
        if event.event_time > self.end_time:
            self.end_time = event.event_time
        if event.event_time < self.start_time:
            self.start_time = event.event_time

    def close(self) -> None:
        self.is_active = False

    def copy(self) -> "Session":
        new = object.__new__(Session)
        new.session_id = self.session_id
        new.subject_id = self.subject_id
        new.start_time = self.start_time
        new.end_time = self.end_time
        new.event_count = self.event_count
        new.is_active = self.is_active
        new.events = list(self.events)
        return new


def make_session(subject_id: str, first_event: SessionEvent) -> Session:
    if not subject_id:
        raise InvalidSubjectError("subject_id cannot be empty")
    if first_event is None:
        raise InvalidEventError("first_event cannot be None")
    if subject_id != first_event.subject_id:
        raise InvalidEventError("subject_id mismatch between session and event")

    session = Session(
        session_id=str(uuid4()),
        subject_id=subject_id,
        start_time=first_event.event_time,
        end_time=first_event.event_time,
        event_count=1,
        is_active=True,
        events=[first_event],
    )
    return session


def merge_sessions(session_a: Session, session_b: Session) -> Session:
    if session_a.subject_id != session_b.subject_id:
        raise InvalidSubjectError("Cannot merge sessions from different subjects")

    merged_start = min(session_a.start_time, session_b.start_time)
    merged_end = max(session_a.end_time, session_b.end_time)

    all_events = sorted(
        session_a.events + session_b.events,
        key=lambda e: e.event_time,
    )

    merged = Session(
        session_id=str(uuid4()),
        subject_id=session_a.subject_id,
        start_time=merged_start,
        end_time=merged_end,
        event_count=len(all_events),
        is_active=False,
        events=all_events,
    )
    return merged
