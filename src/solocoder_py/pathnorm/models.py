from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class CaseSensitivity(Enum):
    SENSITIVE = "sensitive"
    INSENSITIVE = "insensitive"


class PathType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PathInfo:
    path: str
    path_type: PathType = PathType.UNKNOWN
    symlink_target: Optional[str] = None
    exists: bool = True

    def is_symlink(self) -> bool:
        return self.path_type == PathType.SYMLINK


class SymlinkResolver(ABC):
    @abstractmethod
    def get_path_info(self, path: str) -> PathInfo:
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...


class InMemorySymlinkResolver(SymlinkResolver):
    def __init__(
        self,
        symlinks: Optional[Dict[str, str]] = None,
        directories: Optional[set[str]] = None,
        case_sensitive: bool = True,
    ):
        self._case_sensitive = case_sensitive
        self._symlinks: Dict[str, str] = {}
        self._directories: set[str] = set()
        self._all_paths: set[str] = set()

        if symlinks:
            for src, target in symlinks.items():
                self._add_symlink(src, target)

        if directories:
            for d in directories:
                self._add_directory(d)

    def _normalize_key(self, path: str) -> str:
        if self._case_sensitive:
            return path
        return path.lower()

    def _add_symlink(self, src: str, target: str) -> None:
        key = self._normalize_key(src)
        self._symlinks[key] = target
        self._all_paths.add(key)
        self._ensure_parent_exists(src)

    def _add_directory(self, path: str) -> None:
        key = self._normalize_key(path)
        self._directories.add(key)
        self._all_paths.add(key)
        self._ensure_parent_exists(path)

    def _ensure_parent_exists(self, path: str) -> None:
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        if parent and parent != "/":
            parent_key = self._normalize_key(parent)
            if parent_key not in self._all_paths:
                self._directories.add(parent_key)
                self._all_paths.add(parent_key)
                self._ensure_parent_exists(parent)
        elif path.startswith("/"):
            root_key = self._normalize_key("/")
            if root_key not in self._all_paths:
                self._directories.add(root_key)
                self._all_paths.add(root_key)

    def add_symlink(self, src: str, target: str) -> None:
        self._add_symlink(src, target)

    def add_directory(self, path: str) -> None:
        self._add_directory(path)

    def get_path_info(self, path: str) -> PathInfo:
        key = self._normalize_key(path)

        if key in self._symlinks:
            return PathInfo(
                path=path,
                path_type=PathType.SYMLINK,
                symlink_target=self._symlinks[key],
                exists=True,
            )

        if key in self._directories:
            return PathInfo(
                path=path,
                path_type=PathType.DIRECTORY,
                exists=True,
            )

        if key in self._all_paths:
            return PathInfo(
                path=path,
                path_type=PathType.FILE,
                exists=True,
            )

        return PathInfo(
            path=path,
            path_type=PathType.UNKNOWN,
            exists=False,
        )

    def exists(self, path: str) -> bool:
        key = self._normalize_key(path)
        return key in self._all_paths
