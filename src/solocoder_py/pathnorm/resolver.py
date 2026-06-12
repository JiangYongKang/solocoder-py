from __future__ import annotations

from typing import Optional, Set

from .exceptions import InvalidPathError, PathNotFoundError, SymlinkLoopError
from .models import SymlinkResolver
from .normalizer import PathNormalizer


_MAX_SYMLINK_FOLLOWS = 40


class PathResolver:
    def __init__(
        self,
        symlink_resolver: SymlinkResolver,
        normalizer: Optional[PathNormalizer] = None,
        max_symlink_follows: int = _MAX_SYMLINK_FOLLOWS,
    ):
        self._symlink_resolver = symlink_resolver
        self._normalizer = normalizer or PathNormalizer()
        self._max_symlink_follows = max_symlink_follows

    @property
    def normalizer(self) -> PathNormalizer:
        return self._normalizer

    @property
    def symlink_resolver(self) -> SymlinkResolver:
        return self._symlink_resolver

    def resolve(self, path: str, resolve_symlinks: bool = True) -> str:
        normalized = self._normalizer.normalize(path)

        if not resolve_symlinks:
            return normalized

        return self._resolve_symlinks(normalized)

    def _resolve_symlinks(self, path: str) -> str:
        if path == "" or path == ".":
            return path

        is_absolute = path.startswith("/")
        visited: Set[str] = set()
        follow_count = 0

        result = self._resolve_component_by_component(
            path, is_absolute, visited, follow_count
        )

        return self._normalizer.normalize(result)

    def _resolve_component_by_component(
        self,
        path: str,
        is_absolute: bool,
        visited: Set[str],
        follow_count: int,
    ) -> str:
        components = self._split_path(path)
        current_path = "/" if is_absolute else "."
        result_components = []

        for component in components:
            if component == "." or component == "":
                continue
            if component == "..":
                if result_components:
                    result_components.pop()
                elif is_absolute:
                    pass
                else:
                    result_components.append("..")
                continue

            if is_absolute:
                candidate = "/" + "/".join(result_components + [component]) if result_components else "/" + component
            else:
                candidate = "/".join(result_components + [component]) if result_components else component

            candidate = self._normalizer.normalize(candidate)

            if follow_count >= self._max_symlink_follows:
                raise SymlinkLoopError(path, f"exceeded {self._max_symlink_follows} symlink follows")

            path_info = self._symlink_resolver.get_path_info(candidate)

            if path_info.is_symlink():
                follow_count += 1

                if candidate in visited:
                    raise SymlinkLoopError(path, f"loop at {candidate}")
                visited.add(candidate)

                target = path_info.symlink_target
                if target is None:
                    result_components.append(component)
                    continue

                if not target.startswith("/"):
                    parent = "/".join(result_components) if result_components else ("." if not is_absolute else "/")
                    if is_absolute:
                        if parent == "/":
                            target_path = "/" + target
                        else:
                            target_path = "/" + parent + "/" + target
                    else:
                        if parent == ".":
                            target_path = target
                        else:
                            target_path = parent + "/" + target
                else:
                    target_path = target

                target_path = self._normalizer.normalize(target_path)

                resolved_target = self._resolve_component_by_component(
                    target_path,
                    target_path.startswith("/"),
                    visited.copy(),
                    follow_count,
                )

                resolved_components = self._split_path(resolved_target)

                if resolved_target.startswith("/"):
                    is_absolute = True
                    result_components = []
                    current_path = "/"

                for rc in resolved_components:
                    if rc == ".." and result_components:
                        result_components.pop()
                    elif rc not in (".", ""):
                        result_components.append(rc)

            elif path_info.exists:
                result_components.append(component)
            else:
                result_components.append(component)

        if is_absolute:
            return "/" + "/".join(result_components) if result_components else "/"
        else:
            return "/".join(result_components) if result_components else "."

    def _split_path(self, path: str) -> list[str]:
        if path == "/" or path == "":
            return []
        if path == ".":
            return []
        parts = path.split("/")
        return [p for p in parts if p != ""]

    def realpath(self, path: str) -> str:
        return self.resolve(path, resolve_symlinks=True)

    def exists(self, path: str) -> bool:
        try:
            resolved = self.resolve(path, resolve_symlinks=True)
            return self._symlink_resolver.exists(resolved)
        except (SymlinkLoopError, PathNotFoundError, InvalidPathError):
            return False

    def are_equivalent(
        self,
        path1: str,
        path2: str,
        resolve_symlinks: bool = True,
    ) -> bool:
        try:
            if resolve_symlinks:
                resolved1 = self.resolve(path1, resolve_symlinks=True)
                resolved2 = self.resolve(path2, resolve_symlinks=True)
            else:
                resolved1 = self._normalizer.normalize(path1)
                resolved2 = self._normalizer.normalize(path2)
            return self._normalizer.are_equal(resolved1, resolved2)
        except (SymlinkLoopError, PathNotFoundError, InvalidPathError):
            return False
