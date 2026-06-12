from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional, Set

from .exceptions import EventSourceError, InvalidPathError
from .models import ChangeType, FileEvent


class MemoryEventSource:
    def __init__(self) -> None:
        self._watched_paths: Set[Path] = set()
        self._path_exists: Dict[Path, bool] = {}
        self._is_dir: Dict[Path, bool] = {}
        self._children: Dict[Path, Set[Path]] = defaultdict(set)
        self._callback: Optional[Callable[[FileEvent], None]] = None
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def watched_paths(self) -> Set[Path]:
        return set(self._watched_paths)

    def set_callback(self, callback: Callable[[FileEvent], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._is_running:
            raise EventSourceError("Event source is already running")
        self._is_running = True

    def stop(self) -> None:
        if not self._is_running:
            raise EventSourceError("Event source is not running")
        self._is_running = False
        self._watched_paths.clear()
        self._path_exists.clear()
        self._is_dir.clear()
        self._children.clear()

    def add_watch(self, path: Path | str, is_dir: bool = True, exists: bool = True) -> None:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            raise InvalidPathError(f"Path must be absolute: {path}")

        self._watched_paths.add(path_obj)
        self._path_exists[path_obj] = exists
        self._is_dir[path_obj] = is_dir

        if is_dir and path_obj.parent != path_obj:
            self._children[path_obj.parent].add(path_obj)

    def remove_watch(self, path: Path | str) -> None:
        path_obj = Path(path)
        self._watched_paths.discard(path_obj)
        self._path_exists.pop(path_obj, None)
        self._is_dir.pop(path_obj, None)
        if path_obj in self._children:
            children = set(self._children[path_obj])
            for child in children:
                self.remove_watch(child)
            del self._children[path_obj]
        if path_obj.parent in self._children:
            self._children[path_obj.parent].discard(path_obj)

    def is_watched(self, path: Path | str) -> bool:
        path_obj = Path(path)
        return path_obj in self._watched_paths

    def path_exists(self, path: Path | str) -> bool:
        return self._path_exists.get(Path(path), False)

    def is_directory(self, path: Path | str) -> bool:
        return self._is_dir.get(Path(path), False)

    def get_children(self, path: Path | str) -> Set[Path]:
        return set(self._children.get(Path(path), set()))

    def _emit_event(self, event: FileEvent) -> None:
        if self._is_running and self._callback is not None:
            self._callback(event)

    def create_file(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not self._is_running:
            raise EventSourceError("Event source is not running")

        ts = timestamp or datetime.now(timezone.utc)
        self._path_exists[path_obj] = True
        self._is_dir[path_obj] = False
        self._children[path_obj.parent].add(path_obj)

        self._emit_event(FileEvent.created(path_obj, ts))

    def create_directory(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not self._is_running:
            raise EventSourceError("Event source is not running")

        ts = timestamp or datetime.now(timezone.utc)
        self._path_exists[path_obj] = True
        self._is_dir[path_obj] = True
        self._children[path_obj.parent].add(path_obj)

        if path_obj not in self._watched_paths:
            self._watched_paths.add(path_obj)

        self._emit_event(FileEvent.created(path_obj, ts))

    def modify_file(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not self._is_running:
            raise EventSourceError("Event source is not running")
        if not self._path_exists.get(path_obj, False):
            raise EventSourceError(f"Cannot modify non-existent path: {path}")

        ts = timestamp or datetime.now(timezone.utc)
        self._emit_event(FileEvent.modified(path_obj, ts))

    def delete_path(self, path: Path | str, timestamp: Optional[datetime] = None) -> None:
        path_obj = Path(path)
        if not self._is_running:
            raise EventSourceError("Event source is not running")
        if not self._path_exists.get(path_obj, False):
            raise EventSourceError(f"Cannot delete non-existent path: {path}")

        ts = timestamp or datetime.now(timezone.utc)

        if self._is_dir.get(path_obj, False):
            children = set(self._children.get(path_obj, set()))
            for child in sorted(children, key=lambda p: len(str(p)), reverse=True):
                self.delete_path(child, ts)

        self._path_exists[path_obj] = False
        if path_obj.parent in self._children:
            self._children[path_obj.parent].discard(path_obj)

        self._emit_event(FileEvent.deleted(path_obj, ts))

    def rename_path(
        self,
        old_path: Path | str,
        new_path: Path | str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        old_path_obj = Path(old_path)
        new_path_obj = Path(new_path)
        if not self._is_running:
            raise EventSourceError("Event source is not running")
        if not self._path_exists.get(old_path_obj, False):
            raise EventSourceError(f"Cannot rename non-existent path: {old_path}")

        ts = timestamp or datetime.now(timezone.utc)

        is_dir = self._is_dir.get(old_path_obj, False)

        if is_dir:
            children = dict(self._children)
            old_str = str(old_path_obj)
            new_str = str(new_path_obj)
            for parent_path, child_set in list(children.items()):
                for child in list(child_set):
                    child_str = str(child)
                    if child_str.startswith(old_str + "\\") or child_str.startswith(old_str + "/"):
                        new_child_str = child_str.replace(old_str, new_str, 1)
                        new_child = Path(new_child_str)
                        self._path_exists[new_child] = self._path_exists.pop(child)
                        self._is_dir[new_child] = self._is_dir.pop(child)
                        if child in self._watched_paths:
                            self._watched_paths.discard(child)
                            self._watched_paths.add(new_child)
                        child_set.discard(child)
                        self._children[new_child.parent].add(new_child)

        self._path_exists[new_path_obj] = self._path_exists.pop(old_path_obj)
        self._is_dir[new_path_obj] = self._is_dir.pop(old_path_obj)
        if old_path_obj in self._watched_paths:
            self._watched_paths.discard(old_path_obj)
            self._watched_paths.add(new_path_obj)
        if old_path_obj.parent in self._children:
            self._children[old_path_obj.parent].discard(old_path_obj)
        self._children[new_path_obj.parent].add(new_path_obj)

        self._emit_event(FileEvent.renamed(old_path_obj, new_path_obj, ts))
