from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from solocoder_py.filewatcher import (
    ChangeType,
    FileEvent,
    FileWatcher,
)

from .conftest import make_timestamp, make_watcher


class TestRecursiveDirectoryMonitoring:
    def test_watch_subdirectory_file_creation(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("subdir", timestamp=make_timestamp(0))
        watcher.simulate_create_file("subdir/file.txt", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 2
        assert collected_events[0].change_type == ChangeType.CREATED
        assert collected_events[0].path == Path("C:/test_root/subdir")
        assert collected_events[1].change_type == ChangeType.CREATED
        assert collected_events[1].path == Path("C:/test_root/subdir/file.txt")

    def test_watch_subdirectory_file_modification(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("src", timestamp=make_timestamp(0))
        watcher.simulate_create_file("src/main.py", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))
        collected_events.clear()

        watcher.simulate_modify_file("src/main.py", timestamp=make_timestamp(1.2))
        watcher.tick(make_timestamp(2.2))

        modify_events = [e for e in collected_events if e.change_type == ChangeType.MODIFIED]
        assert len(modify_events) == 1
        assert modify_events[0].path == Path("C:/test_root/src/main.py")

    def test_watch_subdirectory_file_deletion(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("docs", timestamp=make_timestamp(0))
        watcher.simulate_create_file("docs/readme.md", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))
        collected_events.clear()

        watcher.simulate_delete_path("docs/readme.md", timestamp=make_timestamp(1.1))
        watcher.tick(make_timestamp(2))

        delete_events = [e for e in collected_events if e.change_type == ChangeType.DELETED]
        assert len(delete_events) == 1
        assert delete_events[0].path == Path("C:/test_root/docs/readme.md")

    def test_nested_subdirectory_auto_monitoring(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("a", timestamp=make_timestamp(0))
        watcher.simulate_create_directory("a/b", timestamp=make_timestamp(0.1))
        watcher.simulate_create_directory("a/b/c", timestamp=make_timestamp(0.2))
        watcher.simulate_create_file("a/b/c/deep.txt", timestamp=make_timestamp(0.3))
        watcher.tick(make_timestamp(1))

        paths = [e.path for e in collected_events]
        assert Path("C:/test_root/a") in paths
        assert Path("C:/test_root/a/b") in paths
        assert Path("C:/test_root/a/b/c") in paths
        assert Path("C:/test_root/a/b/c/deep.txt") in paths

    def test_new_subdirectory_included_in_watch(
        self,
        watcher: FileWatcher,
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("new_dir", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(1))

        assert watcher.event_source.is_watched("C:/test_root/new_dir")


class TestEventDebouncing:
    def test_multiple_modifications_single_event(
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
        watcher.simulate_create_file("test.txt", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(2))
        collected_events.clear()

        watcher.simulate_modify_file("test.txt", timestamp=make_timestamp(2.1))
        watcher.simulate_modify_file("test.txt", timestamp=make_timestamp(2.2))
        watcher.simulate_modify_file("test.txt", timestamp=make_timestamp(2.3))
        watcher.tick(make_timestamp(4))

        assert len(collected_events) == 1
        assert collected_events[0].change_type == ChangeType.MODIFIED
        assert collected_events[0].path == Path("C:/test_root/test.txt")

    def test_create_then_modify_within_window_merged(
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
        watcher.simulate_create_file("merged.txt", timestamp=make_timestamp(0))
        watcher.simulate_modify_file("merged.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_modify_file("merged.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 1
        assert collected_events[0].change_type == ChangeType.CREATED
        assert collected_events[0].path == Path("C:/test_root/merged.txt")

    def test_multiple_paths_independent_debouncing(
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
        watcher.simulate_create_file("a.txt", timestamp=make_timestamp(0))
        watcher.simulate_modify_file("a.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("b.txt", timestamp=make_timestamp(0.5))
        watcher.simulate_modify_file("b.txt", timestamp=make_timestamp(0.6))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 2
        paths = {e.path for e in collected_events}
        assert Path("C:/test_root/a.txt") in paths
        assert Path("C:/test_root/b.txt") in paths


class TestGlobIncludeFilter:
    def test_include_python_files_only(
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
        watcher.simulate_create_file("main.py", timestamp=make_timestamp(0))
        watcher.simulate_create_file("readme.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("utils.py", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 2
        paths = [e.path for e in collected_events]
        assert Path("C:/test_root/main.py") in paths
        assert Path("C:/test_root/utils.py") in paths

    def test_include_deep_glob_pattern(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            include_patterns=["**/*.txt"],
        )
        watcher.start()
        watcher.simulate_create_directory("a", timestamp=make_timestamp(0))
        watcher.simulate_create_directory("a/b", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("a/b/deep.txt", timestamp=make_timestamp(0.2))
        watcher.simulate_create_file("a/b/data.json", timestamp=make_timestamp(0.3))
        watcher.tick(make_timestamp(1))

        file_events = [e for e in collected_events if e.change_type == ChangeType.CREATED and not watcher.event_source.is_directory(e.path)]
        assert len(file_events) == 1
        assert file_events[0].path == Path("C:/test_root/a/b/deep.txt")

    def test_include_multiple_patterns(
        self,
        test_root: Path,
        event_callback,
        collected_events: list[FileEvent],
    ) -> None:
        watcher = make_watcher(
            callback=event_callback,
            root_path=test_root,
            include_patterns=["*.py", "*.txt"],
        )
        watcher.start()
        watcher.simulate_create_file("main.py", timestamp=make_timestamp(0))
        watcher.simulate_create_file("notes.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("data.json", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 2


class TestStopMonitoring:
    def test_stop_no_more_events(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_file("before.txt", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(1))
        watcher.stop()

        with pytest.raises(Exception):
            watcher.simulate_create_file("after.txt", timestamp=make_timestamp(2))

        assert len(collected_events) == 1
        assert collected_events[0].path == Path("C:/test_root/before.txt")

    def test_stop_clears_watches(
        self,
        watcher: FileWatcher,
    ) -> None:
        watcher.start()
        watcher.simulate_create_directory("subdir", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(1))
        watcher.stop()

        assert len(watcher.event_source.watched_paths) == 0
