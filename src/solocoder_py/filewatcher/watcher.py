from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .debouncer import EventDebouncer
from .event_source import MemoryEventSource
from .exceptions import (
    FileWatcherAlreadyRunningError,
    FileWatcherNotRunningError,
    InvalidPathError,
)
from .glob_filter import GlobFilter
from .models import ChangeType, FileEvent

logger = logging.getLogger(__name__)


class FileWatcher:
    def __init__(
        self,
        root_path: Path | str,
        callback: Callable[[List[FileEvent]], None],
        debounce_window: timedelta = timedelta(seconds=0.5),
        include_patterns: Optional[Iterable[str]] = None,
        exclude_patterns: Optional[Iterable[str]] = None,
        event_source: Optional[MemoryEventSource] = None,
    ) -> None:
        self._root_path = Path(root_path)
        if not self._root_path.is_absolute():
            raise InvalidPathError(f"Root path must be absolute: {root_path}")

        self._callback = callback
        self._debounce_window = debounce_window
        self._is_running: bool = False
        self._event_source = event_source or MemoryEventSource()
        self._filter = GlobFilter(include_patterns, exclude_patterns)
        self._debouncer = EventDebouncer(debounce_window, self._on_debounced_events)
        self._event_source.set_callback(self._on_raw_event)

    @property
    def root_path(self) -> Path:
        return self._root_path

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def debounce_window(self) -> timedelta:
        return self._debounce_window

    @property
    def include_patterns(self) -> List[str]:
        return self._filter.include_patterns

    @property
    def exclude_patterns(self) -> List[str]:
        return self._filter.exclude_patterns

    @property
    def event_source(self) -> MemoryEventSource:
        return self._event_source

    def add_include_pattern(self, pattern: str) -> None:
        self._filter.add_include(pattern)

    def add_exclude_pattern(self, pattern: str) -> None:
        self._filter.add_exclude(pattern)

    def start(self) -> None:
        if self._is_running:
            raise FileWatcherAlreadyRunningError("FileWatcher is already running")

        self._event_source.start()
        self._event_source.add_watch(self._root_path, is_dir=True, exists=True)

        self._debouncer.start()
        self._is_running = True

    def stop(self) -> None:
        if not self._is_running:
            raise FileWatcherNotRunningError("FileWatcher is not running")

        self._is_running = False
        self._debouncer.stop()
        self._event_source.stop()

    def _on_raw_event(self, event: FileEvent) -> None:
        if not self._is_running:
            return

        if event.is_rename:
            if not self._is_path_under_root(event.path) and not self._is_path_under_root(event.old_path):
                return
            if not self._filter.matches(event.path) and not self._filter.matches(event.old_path):
                return
        else:
            if not self._is_path_under_root(event.path):
                return
            if not self._filter.matches(event.path):
                return

        self._debouncer.add_event(event)

        self._handle_directory_event(event)

    def _is_path_under_root(self, path: Path) -> bool:
        try:
            path.relative_to(self._root_path)
            return True
        except ValueError:
            return False

    def _handle_directory_event(self, event: FileEvent) -> None:
        if event.change_type != ChangeType.CREATED:
            return

        if not self._event_source.is_directory(event.path):
            return

        try:
            self._event_source.add_watch(event.path, is_dir=True, exists=True)
        except Exception as e:
            logger.warning(
                "Failed to add watch for new directory %s: %s",
                event.path,
                e,
            )

    def _on_debounced_events(self, events: List[FileEvent]) -> None:
        if not self._is_running:
            return

        if events:
            self._callback(events)

    def tick(self, current_time: Optional[datetime] = None) -> None:
        if not self._is_running:
            raise FileWatcherNotRunningError("FileWatcher is not running")
        self._debouncer.check_and_flush(current_time)

    def flush(self, current_time: Optional[datetime] = None) -> None:
        if not self._is_running:
            raise FileWatcherNotRunningError("FileWatcher is not running")
        self._debouncer.flush(current_time)

    def simulate_create_file(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self._root_path / path_obj
        self._event_source.create_file(path_obj, timestamp)

    def simulate_create_directory(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self._root_path / path_obj
        self._event_source.create_directory(path_obj, timestamp)

    def simulate_modify_file(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self._root_path / path_obj
        self._event_source.modify_file(path_obj, timestamp)

    def simulate_delete_path(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self._root_path / path_obj
        self._event_source.delete_path(path_obj, timestamp)

    def simulate_rename_path(
        self,
        old_path: Path | str,
        new_path: Path | str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        old_path_obj = Path(old_path)
        new_path_obj = Path(new_path)
        if not old_path_obj.is_absolute():
            old_path_obj = self._root_path / old_path_obj
        if not new_path_obj.is_absolute():
            new_path_obj = self._root_path / new_path_obj
        self._event_source.rename_path(old_path_obj, new_path_obj, timestamp)
