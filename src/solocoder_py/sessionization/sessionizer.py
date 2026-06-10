from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    InvalidEventError,
    InvalidSubjectError,
    InvalidThresholdError,
    SessionNotFoundError,
)
from .models import Session, SessionEvent, make_session, merge_sessions


@dataclass
class Sessionizer:
    idle_threshold: float = 300.0
    merge_threshold: float = 0.0
    timeout: float = 1800.0
    _clock: Clock = field(default_factory=SystemClock)
    _sessions_by_subject: Dict[str, List[Session]] = field(default_factory=dict)
    _active_session_by_subject: Dict[str, Optional[Session]] = field(default_factory=dict)
    _subject_locks: Dict[str, threading.RLock] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)
    _session_closed_callbacks: List[Callable[[Session], None]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.idle_threshold <= 0:
            raise InvalidThresholdError("idle_threshold must be positive")
        if self.merge_threshold < 0:
            raise InvalidThresholdError("merge_threshold cannot be negative")
        if self.timeout <= 0:
            raise InvalidThresholdError("timeout must be positive")

    def _get_or_create_subject_lock(self, subject_id: str) -> threading.RLock:
        if subject_id not in self._subject_locks:
            self._subject_locks[subject_id] = threading.RLock()
        return self._subject_locks[subject_id]

    def _init_subject_state(self, subject_id: str) -> None:
        if subject_id not in self._sessions_by_subject:
            self._sessions_by_subject[subject_id] = []
        if subject_id not in self._active_session_by_subject:
            self._active_session_by_subject[subject_id] = None

    def add_event(self, event: SessionEvent) -> Session:
        if event is None:
            raise InvalidEventError("event cannot be None")
        if not event.subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        subject_id = event.subject_id

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._check_timeout(subject_id)

            active_session = self._active_session_by_subject.get(subject_id)

            if active_session is None:
                new_session = make_session(subject_id, event)
                self._active_session_by_subject[subject_id] = new_session
                return new_session.copy()

            if event.event_time >= active_session.start_time:
                gap_from_end = (event.event_time - active_session.end_time).total_seconds()
                if gap_from_end <= self.idle_threshold:
                    active_session.add_event(event)
                    return active_session.copy()
            else:
                gap_from_start = (active_session.start_time - event.event_time).total_seconds()
                if gap_from_start <= self.idle_threshold:
                    active_session.add_event(event)
                    return active_session.copy()

            self._close_active_session(subject_id)
            new_session = make_session(subject_id, event)
            self._active_session_by_subject[subject_id] = new_session
            return new_session.copy()

    def _close_active_session(self, subject_id: str) -> None:
        active_session = self._active_session_by_subject.get(subject_id)
        if active_session is not None and active_session.is_active:
            active_session.close()
            self._sessions_by_subject[subject_id].append(active_session)
            self._active_session_by_subject[subject_id] = None
            for callback in self._session_closed_callbacks:
                callback(active_session.copy())

    def _check_timeout(self, subject_id: str) -> None:
        active_session = self._active_session_by_subject.get(subject_id)
        if active_session is None or not active_session.is_active:
            return

        now = self._clock.now()
        idle_time = (now - active_session.end_time).total_seconds()

        if idle_time >= self.timeout:
            self._close_active_session(subject_id)

    def check_timeouts(self) -> List[Session]:
        closed_sessions: List[Session] = []

        with self._global_lock:
            subject_ids = list(self._active_session_by_subject.keys())

        for subject_id in subject_ids:
            subject_lock = self._get_or_create_subject_lock(subject_id)
            with subject_lock:
                active_session = self._active_session_by_subject.get(subject_id)
                if active_session is not None and active_session.is_active:
                    now = self._clock.now()
                    idle_time = (now - active_session.end_time).total_seconds()
                    if idle_time >= self.timeout:
                        self._close_active_session(subject_id)
                        closed_sessions.append(active_session.copy())

        return closed_sessions

    def get_active_session(self, subject_id: str) -> Optional[Session]:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            if subject_id not in self._active_session_by_subject:
                return None
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._check_timeout(subject_id)
            active = self._active_session_by_subject.get(subject_id)
            return active.copy() if active is not None else None

    def get_closed_sessions(self, subject_id: str) -> List[Session]:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._check_timeout(subject_id)
            sessions = self._sessions_by_subject.get(subject_id, [])
            return [s.copy() for s in sessions]

    def get_all_sessions(self, subject_id: str) -> List[Session]:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._check_timeout(subject_id)
            closed = self._sessions_by_subject.get(subject_id, [])
            active = self._active_session_by_subject.get(subject_id)
            all_sessions = [s.copy() for s in closed]
            if active is not None:
                all_sessions.append(active.copy())
            all_sessions.sort(key=lambda s: s.start_time)
            return all_sessions

    def close_session(self, subject_id: str, session_id: str) -> Session:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")
        if not session_id:
            raise ValueError("session_id cannot be empty")

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            active = self._active_session_by_subject.get(subject_id)
            if active is not None and active.session_id == session_id:
                self._close_active_session(subject_id)
                return active.copy()

            closed_list = self._sessions_by_subject.get(subject_id, [])
            for session in closed_list:
                if session.session_id == session_id:
                    return session.copy()

            raise SessionNotFoundError(
                f"Session {session_id} not found for subject {subject_id}"
            )

    def force_close_all(self, subject_id: str) -> List[Session]:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._close_active_session(subject_id)
            sessions = self._sessions_by_subject.get(subject_id, [])
            return [s.copy() for s in sessions]

    def merge_adjacent_sessions(self, subject_id: str) -> List[Session]:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            self._init_subject_state(subject_id)
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            self._close_active_session(subject_id)
            closed = self._sessions_by_subject.get(subject_id, [])

            if len(closed) < 2:
                return [s.copy() for s in closed]

            sorted_sessions = sorted(closed, key=lambda s: s.start_time)
            merged: List[Session] = []
            current = sorted_sessions[0]

            for i in range(1, len(sorted_sessions)):
                next_session = sorted_sessions[i]
                gap = (next_session.start_time - current.end_time).total_seconds()

                if gap <= self.merge_threshold:
                    current = merge_sessions(current, next_session)
                else:
                    merged.append(current)
                    current = next_session

            merged.append(current)
            self._sessions_by_subject[subject_id] = merged
            return [s.copy() for s in merged]

    def add_session_closed_callback(self, callback: Callable[[Session], None]) -> None:
        if callback is None:
            raise ValueError("callback cannot be None")
        self._session_closed_callbacks.append(callback)

    def clear_subject(self, subject_id: str) -> None:
        if not subject_id:
            raise InvalidSubjectError("subject_id cannot be empty")

        with self._global_lock:
            subject_lock = self._get_or_create_subject_lock(subject_id)

        with subject_lock:
            if subject_id in self._sessions_by_subject:
                self._sessions_by_subject[subject_id] = []
            if subject_id in self._active_session_by_subject:
                self._active_session_by_subject[subject_id] = None

    def clear_all(self) -> None:
        with self._global_lock:
            self._sessions_by_subject.clear()
            self._active_session_by_subject.clear()
            self._subject_locks.clear()
