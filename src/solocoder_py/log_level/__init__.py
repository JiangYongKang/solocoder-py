from __future__ import annotations

from enum import IntEnum
from typing import Dict, Union


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


_VALID_LEVEL_NAMES = {level.name for level in LogLevel}

_DEFAULT_LEVEL = LogLevel.INFO

_LevelType = Union[str, LogLevel]


def _validate_name(name: str, func_name: str) -> None:
    if name is None:
        raise TypeError(
            f"{func_name}: 'name' must not be None. "
            f"Expected non-empty string or empty string for root logger."
        )
    if not isinstance(name, str):
        raise TypeError(
            f"{func_name}: 'name' must be a string, got {type(name).__name__}."
        )


def _resolve_level(level: _LevelType, func_name: str) -> LogLevel:
    if isinstance(level, LogLevel):
        return level
    if isinstance(level, str):
        upper = level.upper()
        if upper not in _VALID_LEVEL_NAMES:
            raise ValueError(
                f"{func_name}: Invalid log level: {level!r}. "
                f"Valid levels: {', '.join(sorted(_VALID_LEVEL_NAMES))}"
            )
        return LogLevel[upper]
    raise TypeError(
        f"{func_name}: 'level' must be a string or LogLevel enum, got {type(level).__name__}."
    )


class LogLevelManager:
    def __init__(self) -> None:
        self._levels: Dict[str, LogLevel] = {}

    def set_level(self, name: str, level: _LevelType) -> None:
        _validate_name(name, "set_level")
        resolved = _resolve_level(level, "set_level")
        self._levels[name] = resolved

    def get_effective_level(self, name: str) -> LogLevel:
        _validate_name(name, "get_effective_level")
        current = name
        while current:
            if current in self._levels:
                return self._levels[current]
            dot_pos = current.rfind(".")
            if dot_pos == -1:
                break
            current = current[:dot_pos]
        if "" in self._levels:
            return self._levels[""]
        return _DEFAULT_LEVEL

    def is_enabled(self, name: str, level: _LevelType) -> bool:
        _validate_name(name, "is_enabled")
        resolved = _resolve_level(level, "is_enabled")
        effective = self.get_effective_level(name)
        return resolved >= effective

    def clear_level(self, name: str) -> bool:
        _validate_name(name, "clear_level")
        if name in self._levels:
            del self._levels[name]
            return True
        return False

    def has_explicit_level(self, name: str) -> bool:
        _validate_name(name, "has_explicit_level")
        return name in self._levels

    def clear_all(self) -> None:
        self._levels.clear()


__all__ = ["LogLevel", "LogLevelManager"]
