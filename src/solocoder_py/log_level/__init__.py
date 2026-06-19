from __future__ import annotations

from enum import IntEnum
from typing import Dict, Optional


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


_VALID_LEVEL_NAMES = {level.name for level in LogLevel}

_DEFAULT_LEVEL = LogLevel.INFO


class LogLevelManager:
    def __init__(self) -> None:
        self._levels: Dict[str, LogLevel] = {}

    def set_level(self, name: str, level: str) -> None:
        upper = level.upper()
        if upper not in _VALID_LEVEL_NAMES:
            raise ValueError(
                f"Invalid log level: {level!r}. "
                f"Valid levels: {', '.join(sorted(_VALID_LEVEL_NAMES))}"
            )
        self._levels[name] = LogLevel[upper]

    def get_effective_level(self, name: str) -> LogLevel:
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

    def is_enabled(self, name: str, level: str) -> bool:
        upper = level.upper()
        if upper not in _VALID_LEVEL_NAMES:
            raise ValueError(
                f"Invalid log level: {level!r}. "
                f"Valid levels: {', '.join(sorted(_VALID_LEVEL_NAMES))}"
            )
        effective = self.get_effective_level(name)
        return LogLevel[upper] >= effective

    def clear_level(self, name: str) -> bool:
        if name in self._levels:
            del self._levels[name]
            return True
        return False

    def has_explicit_level(self, name: str) -> bool:
        return name in self._levels

    def clear_all(self) -> None:
        self._levels.clear()


__all__ = ["LogLevel", "LogLevelManager"]
