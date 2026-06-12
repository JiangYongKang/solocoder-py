from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List

import pytest

from solocoder_py.filewatcher import (
    ChangeType,
    EventDebouncer,
    FileEvent,
    FileWatcher,
    GlobFilter,
    MemoryEventSource,
)


def make_test_root() -> Path:
    return Path("C:/test_root")


def make_event_source() -> MemoryEventSource:
    return MemoryEventSource()


def make_glob_filter(
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
) -> GlobFilter:
    return GlobFilter(include_patterns, exclude_patterns)


def make_debouncer(
    callback: Callable[[List[FileEvent]], None],
    debounce_window: timedelta = timedelta(seconds=0.5),
) -> EventDebouncer:
    return EventDebouncer(debounce_window, callback)


def make_watcher(
    callback: Callable[[List[FileEvent]], None],
    root_path: Path | None = None,
    debounce_window: timedelta = timedelta(seconds=0.5),
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    event_source: MemoryEventSource | None = None,
) -> FileWatcher:
    return FileWatcher(
        root_path=root_path or make_test_root(),
        callback=callback,
        debounce_window=debounce_window,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        event_source=event_source,
    )


def make_timestamp(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


@pytest.fixture
def test_root() -> Path:
    return make_test_root()


@pytest.fixture
def event_source() -> MemoryEventSource:
    return make_event_source()


@pytest.fixture
def collected_events() -> List[FileEvent]:
    return []


@pytest.fixture
def event_callback(collected_events: List[FileEvent]) -> Callable[[List[FileEvent]], None]:
    def callback(events: List[FileEvent]) -> None:
        collected_events.extend(events)
    return callback


@pytest.fixture
def watcher(
    test_root: Path,
    event_callback: Callable[[List[FileEvent]], None],
    event_source: MemoryEventSource,
) -> FileWatcher:
    return make_watcher(
        callback=event_callback,
        root_path=test_root,
        event_source=event_source,
    )
