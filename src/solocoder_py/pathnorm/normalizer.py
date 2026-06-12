from __future__ import annotations

import re
from typing import List, Optional

from .exceptions import InvalidPathError


_ILLEGAL_CHARS_PATTERN = re.compile(r'[\x00-\x1f]')
_MAX_PATH_LENGTH = 4096


class PathNormalizer:
    def __init__(
        self,
        case_sensitive: bool = True,
        max_path_length: int = _MAX_PATH_LENGTH,
        illegal_chars_pattern: Optional[re.Pattern] = None,
    ):
        self._case_sensitive = case_sensitive
        self._max_path_length = max_path_length
        self._illegal_chars_pattern = illegal_chars_pattern or _ILLEGAL_CHARS_PATTERN

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    def normalize(self, path: str) -> str:
        if not isinstance(path, str):
            raise TypeError(f"Path must be a string, got {type(path).__name__}")

        self._validate_path_length(path)
        self._validate_illegal_chars(path)

        if path == "":
            return "."

        is_absolute = path.startswith("/")
        trailing_slash = path.endswith("/") and len(path) > 1

        parts = self._split_into_components(path)
        normalized_parts = self._process_components(parts, is_absolute)

        result = self._join_components(normalized_parts, is_absolute)

        if result == "":
            result = "." if not is_absolute else "/"

        if is_absolute and result == "":
            result = "/"

        return result

    def _validate_path_length(self, path: str) -> None:
        if len(path) > self._max_path_length:
            raise InvalidPathError(
                path,
                f"path length {len(path)} exceeds maximum {self._max_path_length}",
            )

    def _validate_illegal_chars(self, path: str) -> None:
        if self._illegal_chars_pattern.search(path):
            raise InvalidPathError(path, "contains illegal characters")

    def _split_into_components(self, path: str) -> List[str]:
        parts = path.split("/")
        return [p for p in parts if p != ""]

    def _process_components(self, components: List[str], is_absolute: bool) -> List[str]:
        stack: List[str] = []

        for component in components:
            if component == ".":
                continue
            elif component == "..":
                if is_absolute:
                    if len(stack) > 0:
                        stack.pop()
                else:
                    if len(stack) > 0 and stack[-1] != "..":
                        stack.pop()
                    else:
                        stack.append("..")
            else:
                stack.append(component)

        return stack

    def _join_components(self, components: List[str], is_absolute: bool) -> str:
        if is_absolute:
            return "/" + "/".join(components) if components else "/"
        else:
            return "/".join(components) if components else "."

    def normalize_case(self, path: str) -> str:
        if not self._case_sensitive:
            return path.lower()
        return path

    def are_equal(self, path1: str, path2: str) -> bool:
        norm1 = self.normalize(path1)
        norm2 = self.normalize(path2)

        if not self._case_sensitive:
            return norm1.lower() == norm2.lower()
        return norm1 == norm2
