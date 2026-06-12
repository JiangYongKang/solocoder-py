from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List, Optional

from .exceptions import InvalidGlobPatternError


def _validate_glob_syntax(pattern: str) -> None:
    bracket_depth = 0
    in_bracket = False
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == '[' and not in_bracket:
            in_bracket = True
            bracket_depth += 1
        elif c == ']' and in_bracket:
            in_bracket = False
            bracket_depth -= 1
        elif c == '*' and i + 1 < len(pattern) and pattern[i + 1] == '*':
            if i > 0 and pattern[i - 1] not in ('/', '\\'):
                raise InvalidGlobPatternError(
                    f"Invalid glob pattern '{pattern}': '**' must be preceded by '/' or at start"
                )
            if i + 2 < len(pattern) and pattern[i + 2] not in ('/', '\\'):
                raise InvalidGlobPatternError(
                    f"Invalid glob pattern '{pattern}': '**' must be followed by '/' or at end"
                )
            i += 1
        i += 1

    if bracket_depth != 0:
        raise InvalidGlobPatternError(
            f"Invalid glob pattern '{pattern}': unmatched bracket"
        )


def _compile_glob(pattern: str) -> str:
    if not pattern:
        raise InvalidGlobPatternError("Glob pattern cannot be empty")
    _validate_glob_syntax(pattern)
    try:
        test_path = Path("test")
        fnmatch(str(test_path), pattern)
    except (ValueError, TypeError) as e:
        raise InvalidGlobPatternError(f"Invalid glob pattern '{pattern}': {e}") from e
    return pattern


class GlobFilter:
    def __init__(
        self,
        include_patterns: Optional[Iterable[str]] = None,
        exclude_patterns: Optional[Iterable[str]] = None,
    ) -> None:
        self._include_patterns: List[str] = []
        self._exclude_patterns: List[str] = []

        if include_patterns is not None:
            for p in include_patterns:
                self._include_patterns.append(_compile_glob(p))

        if exclude_patterns is not None:
            for p in exclude_patterns:
                self._exclude_patterns.append(_compile_glob(p))

    @property
    def include_patterns(self) -> List[str]:
        return list(self._include_patterns)

    @property
    def exclude_patterns(self) -> List[str]:
        return list(self._exclude_patterns)

    def add_include(self, pattern: str) -> None:
        self._include_patterns.append(_compile_glob(pattern))

    def add_exclude(self, pattern: str) -> None:
        self._exclude_patterns.append(_compile_glob(pattern))

    def _match_patterns(self, path: Path, patterns: List[str]) -> bool:
        if not patterns:
            return False

        path_str = str(path)
        normalized_path = path_str.replace("\\", "/")

        for pattern in patterns:
            if self._match_single_pattern(normalized_path, pattern):
                return True
        return False

    def _match_single_pattern(self, path_str: str, pattern: str) -> bool:
        if "**" in pattern:
            return self._match_double_star(path_str, pattern)
        return fnmatch(path_str, pattern) or fnmatch(Path(path_str).name, pattern)

    def _match_double_star(self, path_str: str, pattern: str) -> bool:
        normalized_path = path_str.replace("\\", "/")
        path_parts = normalized_path.split("/")
        pattern_parts = pattern.split("/")

        return self._match_path_parts(path_parts, pattern_parts)

    def _match_path_parts(self, path_parts: List[str], pattern_parts: List[str]) -> bool:
        if not pattern_parts:
            return not path_parts

        if not path_parts:
            return all(p == "**" for p in pattern_parts)

        current_pattern = pattern_parts[0]

        if current_pattern == "**":
            if len(pattern_parts) == 1:
                return True
            for i in range(len(path_parts) + 1):
                if self._match_path_parts(path_parts[i:], pattern_parts[1:]):
                    return True
            return False

        if fnmatch(path_parts[0], current_pattern):
            return self._match_path_parts(path_parts[1:], pattern_parts[1:])

        return False

    def matches(self, path: Path | str) -> bool:
        path_obj = Path(path)

        if self._exclude_patterns and self._match_patterns(path_obj, self._exclude_patterns):
            return False

        if self._include_patterns:
            return self._match_patterns(path_obj, self._include_patterns)

        return True

    def __call__(self, path: Path | str) -> bool:
        return self.matches(path)
