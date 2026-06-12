from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from solocoder_py.filewatcher import (
    ChangeType,
    DebouncerNotRunningError,
    EventDebouncer,
    EventSourceError,
    FileEvent,
    FileWatcher,
    FileWatcherAlreadyRunningError,
    FileWatcherNotRunningError,
    GlobFilter,
    InvalidGlobPatternError,
    InvalidPathError,
    MemoryEventSource,
    PendingEvents,
)

from .conftest import make_debouncer, make_glob_filter, make_timestamp, make_watcher


class TestExcludedDirectoryEvents:
    def test_excluded_directory_no_events(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            exclude_patterns=["**/excluded/**", "**/excluded"],
        )
        watcher.start()
        watcher.simulate_create_directory("excluded", timestamp=make_timestamp(0))
        watcher.simulate_create_file("excluded/secret.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("included.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 1
        assert collected_events[0].path == Path("C:/test_root/included.txt")

    def test_exclude_patterns_no_events(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            exclude_patterns=["*.log", "*.tmp"],
        )
        watcher.start()
        watcher.simulate_create_file("app.log", timestamp=make_timestamp(0))
        watcher.simulate_create_file("cache.tmp", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("data.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 1
        assert collected_events[0].path == Path("C:/test_root/data.txt")


class TestInvalidGlobPattern:
    def test_empty_glob_pattern_rejected(self) -> None:
        with pytest.raises(InvalidGlobPatternError, match="Glob pattern cannot be empty"):
            make_glob_filter(include_patterns=[""])

    def test_invalid_glob_pattern_rejected(self) -> None:
        with pytest.raises(InvalidGlobPatternError):
            GlobFilter(include_patterns=["[unterminated"])

    def test_add_invalid_include_pattern_rejected(self) -> None:
        gf = make_glob_filter()
        with pytest.raises(InvalidGlobPatternError):
            gf.add_include("[bad")

    def test_add_invalid_exclude_pattern_rejected(self) -> None:
        gf = make_glob_filter()
        with pytest.raises(InvalidGlobPatternError):
            gf.add_exclude("[bad")


class TestMixedEventTypesDebounce:
    def test_rename_then_modify_merged(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            debounce_window=timedelta(seconds=1),
        )
        watcher.start()
        watcher.simulate_create_file("old.txt", timestamp=make_timestamp(-1))
        watcher.tick(make_timestamp(0))
        collected_events.clear()

        watcher.simulate_rename_path("old.txt", "new.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_modify_file("new.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 1
        assert collected_events[0].change_type == ChangeType.MODIFIED
        assert collected_events[0].path == Path("C:/test_root/new.txt")

    def test_mixed_event_types_ordering(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            debounce_window=timedelta(seconds=1),
        )
        watcher.start()
        watcher.simulate_create_file("mixed.txt", timestamp=make_timestamp(0))
        watcher.simulate_modify_file("mixed.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_delete_path("mixed.txt", timestamp=make_timestamp(0.2))
        watcher.simulate_create_file("mixed.txt", timestamp=make_timestamp(0.3))
        watcher.simulate_modify_file("mixed.txt", timestamp=make_timestamp(0.4))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 1
        assert collected_events[0].change_type in [ChangeType.CREATED, ChangeType.MODIFIED]


class TestDirectoryDeletedDuringMonitoring:
    def test_monitored_directory_deleted(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("subdir", timestamp=make_timestamp(0))
        watcher.simulate_create_file("subdir/file.txt", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))
        collected_events.clear()

        watcher.simulate_delete_path("subdir", timestamp=make_timestamp(1.1))
        watcher.tick(make_timestamp(2))

        delete_events = [e for e in collected_events if e.change_type == ChangeType.DELETED]
        assert len(delete_events) >= 2

    def test_operations_on_deleted_directory_raise_error(
        self,
        watcher: FileWatcher,
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("temp", timestamp=make_timestamp(0))
        watcher.simulate_delete_path("temp", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))

        with pytest.raises(EventSourceError):
            watcher.simulate_modify_file("temp", timestamp=make_timestamp(1.1))

        with pytest.raises(EventSourceError):
            watcher.simulate_delete_path("temp", timestamp=make_timestamp(1.1))


class TestSpecialCharacterPaths:
    def test_path_with_spaces(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
        )
        watcher.start()
        watcher.simulate_create_directory("my docs", timestamp=make_timestamp(0))
        watcher.simulate_create_file("my docs/hello world.txt", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))

        paths = [e.path for e in collected_events]
        assert Path("C:/test_root/my docs") in paths
        assert Path("C:/test_root/my docs/hello world.txt") in paths

    def test_path_with_chinese_characters(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
        )
        watcher.start()
        watcher.simulate_create_directory("目录", timestamp=make_timestamp(0))
        watcher.simulate_create_file("目录/测试.py", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))

        paths = [e.path for e in collected_events]
        assert Path("C:/test_root/目录") in paths
        assert Path("C:/test_root/目录/测试.py") in paths

    def test_glob_matches_special_characters(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            include_patterns=["*.py"],
        )
        watcher.start()
        watcher.simulate_create_file("my file.py", timestamp=make_timestamp(0))
        watcher.simulate_create_file("测试.py", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("normal.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 2
        py_paths = [e.path for e in collected_events if str(e.path).endswith(".py")]
        assert len(py_paths) == 2


class TestWatcherStateErrors:
    def test_start_when_already_running(self, watcher: FileWatcher) -> None:
        watcher.start()
        with pytest.raises(FileWatcherAlreadyRunningError):
            watcher.start()

    def test_stop_when_not_running(self, watcher: FileWatcher) -> None:
        with pytest.raises(FileWatcherNotRunningError):
            watcher.stop()

    def test_tick_when_not_running(self, watcher: FileWatcher) -> None:
        with pytest.raises(FileWatcherNotRunningError):
            watcher.tick()

    def test_flush_when_not_running(self, watcher: FileWatcher) -> None:
        with pytest.raises(FileWatcherNotRunningError):
            watcher.flush()

    def test_relative_root_path_rejected(self, event_callback) -> None:
        with pytest.raises(InvalidPathError, match="Root path must be absolute"):
            FileWatcher(
                root_path=Path("relative/path"),
                callback=event_callback,
            )


class TestEventSourceErrors:
    def test_modify_non_existent_path(self, watcher: FileWatcher) -> None:
        watcher.start()
        with pytest.raises(EventSourceError):
            watcher.simulate_modify_file("nonexistent.txt")

    def test_delete_non_existent_path(self, watcher: FileWatcher) -> None:
        watcher.start()
        with pytest.raises(EventSourceError):
            watcher.simulate_delete_path("nonexistent.txt")

    def test_rename_non_existent_path(self, watcher: FileWatcher) -> None:
        watcher.start()
        with pytest.raises(EventSourceError):
            watcher.simulate_rename_path("nonexistent.txt", "new.txt")


class TestDebouncerErrors:
    def test_negative_debounce_window_rejected(self, event_callback) -> None:
        with pytest.raises(ValueError, match="debounce_window must be positive"):
            EventDebouncer(
                debounce_window=timedelta(seconds=-1),
                callback=event_callback,
            )

    def test_zero_debounce_window_rejected(self, event_callback) -> None:
        with pytest.raises(ValueError, match="debounce_window must be positive"):
            EventDebouncer(
                debounce_window=timedelta(seconds=0),
                callback=event_callback,
            )

    def test_add_event_when_not_running(self, event_callback) -> None:
        debouncer = make_debouncer(event_callback)
        event = FileEvent.created(Path("test.txt"), make_timestamp(0))
        with pytest.raises(DebouncerNotRunningError, match="debouncer is not running"):
            debouncer.add_event(event)
        assert debouncer.pending_count() == 0

    def test_stop_when_not_running(self, event_callback) -> None:
        debouncer = make_debouncer(event_callback)
        debouncer.stop()
        assert debouncer.is_running is False


class TestPendingEvents:
    def test_empty_pending_returns_none(self) -> None:
        pe = PendingEvents()
        assert pe.merge() is None

    def test_pending_events_sorted_by_timestamp(self) -> None:
        pe = PendingEvents()
        pe.add(FileEvent.created(Path("test.txt"), make_timestamp(0.5)))
        pe.add(FileEvent.modified(Path("test.txt"), make_timestamp(0.1)))
        pe.add(FileEvent.modified(Path("test.txt"), make_timestamp(0.3)))

        result = pe.merge()
        assert result is not None
        assert result.change_type == ChangeType.CREATED

    def test_rename_without_modify_keeps_rename(self) -> None:
        pe = PendingEvents()
        pe.add(FileEvent.renamed(Path("old.txt"), Path("new.txt"), make_timestamp(0)))

        result = pe.merge()
        assert result is not None
        assert result.change_type == ChangeType.RENAMED
        assert result.old_path == Path("old.txt")
        assert result.path == Path("new.txt")

    def test_rename_with_subsequent_modify_becomes_modify(self) -> None:
        pe = PendingEvents()
        pe.add(FileEvent.renamed(Path("old.txt"), Path("new.txt"), make_timestamp(0)))
        pe.add(FileEvent.modified(Path("new.txt"), make_timestamp(0.1)))

        result = pe.merge()
        assert result is not None
        assert result.change_type == ChangeType.MODIFIED
        assert result.path == Path("new.txt")
