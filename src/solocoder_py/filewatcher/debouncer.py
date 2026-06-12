from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .exceptions import DebouncerNotRunningError
from .models import ChangeType, FileEvent


class PendingEvents:
    def __init__(self) -> None:
        self._events: List[FileEvent] = []

    def add(self, event: FileEvent) -> None:
        self._events.append(event)

    def merge(self) -> Optional[FileEvent]:
        if not self._events:
            return None

        sorted_events = sorted(self._events, key=lambda e: e.timestamp)

        create_events = [e for e in sorted_events if e.change_type == ChangeType.CREATED]
        delete_events = [e for e in sorted_events if e.change_type == ChangeType.DELETED]
        modify_events = [e for e in sorted_events if e.change_type == ChangeType.MODIFIED]
        rename_events = [e for e in sorted_events if e.change_type == ChangeType.RENAMED]

        has_create = len(create_events) > 0
        has_delete = len(delete_events) > 0

        if has_create and has_delete:
            last_delete = delete_events[-1]
            last_create = create_events[-1]
            if last_delete.timestamp > last_create.timestamp:
                return None
            if rename_events:
                return self._merge_with_renames(sorted_events, create_events, delete_events, modify_events, rename_events)
            last_modify = modify_events[-1] if modify_events else None
            if last_modify and last_modify.timestamp > last_create.timestamp:
                return last_modify
            return last_create

        if rename_events:
            return self._merge_with_renames(sorted_events, create_events, delete_events, modify_events, rename_events)

        if has_create and not has_delete:
            last_create = create_events[-1]
            if modify_events:
                last_modify = modify_events[-1]
                if last_modify.timestamp > last_create.timestamp:
                    return FileEvent(
                        change_type=ChangeType.CREATED,
                        path=last_create.path,
                        timestamp=last_modify.timestamp,
                    )
            return last_create

        if has_delete and not has_create:
            return delete_events[-1]

        if modify_events:
            return modify_events[-1]

        return sorted_events[-1]

    def _merge_with_renames(
        self,
        sorted_events: List[FileEvent],
        create_events: List[FileEvent],
        delete_events: List[FileEvent],
        modify_events: List[FileEvent],
        rename_events: List[FileEvent],
    ) -> Optional[FileEvent]:
        last_event = sorted_events[-1]

        if last_event.change_type == ChangeType.RENAMED:
            if modify_events and modify_events[-1].timestamp > last_event.timestamp:
                last_modify = modify_events[-1]
                return FileEvent(
                    change_type=ChangeType.MODIFIED,
                    path=last_event.path,
                    timestamp=last_modify.timestamp,
                )
            return last_event

        if last_event.change_type == ChangeType.MODIFIED:
            return last_event

        return last_event


class EventDebouncer:
    def __init__(
        self,
        debounce_window: timedelta,
        callback: Callable[[List[FileEvent]], None],
    ) -> None:
        if debounce_window <= timedelta(0):
            raise ValueError("debounce_window must be positive")
        self._debounce_window = debounce_window
        self._callback = callback
        self._pending: Dict[Path, PendingEvents] = defaultdict(PendingEvents)
        self._path_first_seen: Dict[Path, datetime] = {}
        self._is_running: bool = False
        self._last_flush_time: datetime = datetime.now(timezone.utc)

    @property
    def debounce_window(self) -> timedelta:
        return self._debounce_window

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        self._is_running = True
        self._last_flush_time = datetime.now(timezone.utc)

    def stop(self) -> None:
        self.flush()
        self._is_running = False
        self._pending.clear()
        self._path_first_seen.clear()

    def add_event(self, event: FileEvent) -> None:
        if not self._is_running:
            raise DebouncerNotRunningError(
                "Cannot add event: debouncer is not running"
            )

        path = event.path
        if path not in self._path_first_seen:
            self._path_first_seen[path] = event.timestamp

        self._pending[path].add(event)

    def check_and_flush(self, current_time: Optional[datetime] = None) -> None:
        if not self._is_running:
            return

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self._last_flush_time = now

        ready_paths: List[Path] = []
        for path, first_seen in self._path_first_seen.items():
            if now - first_seen >= self._debounce_window:
                ready_paths.append(path)

        if not ready_paths:
            return

        flushed_events: List[FileEvent] = []
        for path in ready_paths:
            pending = self._pending.pop(path, None)
            self._path_first_seen.pop(path, None)
            if pending is not None:
                merged = pending.merge()
                if merged is not None:
                    flushed_events.append(merged)

        if flushed_events:
            flushed_events.sort(key=lambda e: e.timestamp)
            self._callback(flushed_events)

    def flush(self, current_time: Optional[datetime] = None) -> None:
        if not self._pending:
            return

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        flushed_events: List[FileEvent] = []
        for path, pending in list(self._pending.items()):
            merged = pending.merge()
            if merged is not None:
                flushed_events.append(merged)

        self._pending.clear()
        self._path_first_seen.clear()

        if flushed_events:
            flushed_events.sort(key=lambda e: e.timestamp)
            self._callback(flushed_events)

    def pending_count(self) -> int:
        return len(self._pending)
