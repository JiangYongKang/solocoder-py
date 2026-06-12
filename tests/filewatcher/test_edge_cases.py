from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from solocoder_py.filewatcher import (
    ChangeType,
    FileEvent,
    FileWatcher,
    GlobFilter,
)

from .conftest import make_glob_filter, make_timestamp, make_watcher


class TestEmptyDirectory:
    def test_start_and_stop_empty_directory(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.tick(make_timestamp(1))
        watcher.stop()
        assert len(collected_events) == 0

    def test_create_after_empty_start(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.tick(make_timestamp(0.5))
        watcher.simulate_create_file("new.txt", timestamp=make_timestamp(0.6))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 1
        assert collected_events[0].change_type == ChangeType.CREATED


class TestSingleLevelDirectory:
    def test_single_level_no_subdirs(
        self,
        watcher: FileWatcher,
        collected_events: list[FileEvent],
    ) -> None:
        watcher.start()
        watcher.simulate_create_file("file1.txt", timestamp=make_timestamp(0))
        watcher.simulate_create_file("file2.txt", timestamp=make_timestamp(0.1))
        watcher.tick(make_timestamp(1))
        create_count = len([e for e in collected_events if e.change_type == ChangeType.CREATED])
        collected_events.clear()

        watcher.simulate_modify_file("file1.txt", timestamp=make_timestamp(1.2))
        watcher.tick(make_timestamp(2.2))
        modify_count = len([e for e in collected_events if e.change_type == ChangeType.MODIFIED])
        collected_events.clear()

        watcher.simulate_delete_path("file2.txt", timestamp=make_timestamp(2.5))
        watcher.tick(make_timestamp(3.5))
        delete_count = len([e for e in collected_events if e.change_type == ChangeType.DELETED])

        assert create_count >= 1
        assert modify_count == 1
        assert delete_count == 1


class TestDebounceWindowBoundary:
    def test_event_at_exact_window_boundary(
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
        watcher.simulate_create_file("boundary.txt", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(1))

        assert len(collected_events) == 1
        assert collected_events[0].path == Path("C:/test_root/boundary.txt")

    def test_event_just_before_window_boundary_not_flushed(
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
        watcher.simulate_create_file("early.txt", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(0.999))

        assert len(collected_events) == 0

    def test_event_just_after_window_boundary_flushed(
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
        watcher.simulate_create_file("late.txt", timestamp=make_timestamp(0))
        watcher.tick(make_timestamp(1.001))

        assert len(collected_events) == 1


class TestGlobPatternBoundaries:
    def test_glob_exact_match(self) -> None:
        gf = make_glob_filter(include_patterns=["exact.txt"])
        assert gf.matches("exact.txt") is True
        assert gf.matches("exacttxt") is False
        assert gf.matches("exact.txt.bak") is False

    def test_glob_wildcard_match(self) -> None:
        gf = make_glob_filter(include_patterns=["*.py"])
        assert gf.matches("test.py") is True
        assert gf.matches("src/test.py") is True
        assert gf.matches("test.pyc") is False
        assert gf.matches("test.txt") is False

    def test_glob_double_star_match(self) -> None:
        gf = make_glob_filter(include_patterns=["**/*.txt"])
        assert gf.matches("test.txt") is True
        assert gf.matches("a/test.txt") is True
        assert gf.matches("a/b/c/test.txt") is True
        assert gf.matches("test.py") is False

    def test_glob_question_mark(self) -> None:
        gf = make_glob_filter(include_patterns=["file?.txt"])
        assert gf.matches("file1.txt") is True
        assert gf.matches("fileA.txt") is True
        assert gf.matches("file12.txt") is False
        assert gf.matches("file.txt") is False

    def test_glob_character_class(self) -> None:
        gf = make_glob_filter(include_patterns=["[abc].txt"])
        assert gf.matches("a.txt") is True
        assert gf.matches("b.txt") is True
        assert gf.matches("c.txt") is True
        assert gf.matches("d.txt") is False

    def test_glob_negated_character_class(self) -> None:
        gf = make_glob_filter(include_patterns=["[!abc].txt"])
        assert gf.matches("d.txt") is True
        assert gf.matches("a.txt") is False

    def test_glob_no_include_matches_all(self) -> None:
        gf = make_glob_filter()
        assert gf.matches("anything.txt") is True
        assert gf.matches("any/path/file.py") is True

    def test_glob_exclude_overrides_include(self) -> None:
        gf = make_glob_filter(
            include_patterns=["*.py"],
            exclude_patterns=["test_*.py"],
        )
        assert gf.matches("main.py") is True
        assert gf.matches("test_main.py") is False
        assert gf.matches("other.txt") is False


class TestCreateDeleteCancellation:
    def test_create_then_delete_within_window_cancelled(
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
        watcher.simulate_create_file("temp.txt", timestamp=make_timestamp(0))
        watcher.simulate_delete_path("temp.txt", timestamp=make_timestamp(0.5))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 0

    def test_delete_then_create_within_window_kept(
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
        watcher.simulate_create_file("file.txt", timestamp=make_timestamp(-1))
        watcher.tick(make_timestamp(0))
        collected_events.clear()

        watcher.simulate_delete_path("file.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("file.txt", timestamp=make_timestamp(0.2))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 1

    def test_multiple_create_delete_pairs(
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
        watcher.simulate_create_file("flip.txt", timestamp=make_timestamp(0))
        watcher.simulate_delete_path("flip.txt", timestamp=make_timestamp(0.1))
        watcher.simulate_create_file("flip.txt", timestamp=make_timestamp(0.2))
        watcher.simulate_delete_path("flip.txt", timestamp=make_timestamp(0.3))
        watcher.tick(make_timestamp(2))

        assert len(collected_events) == 0
