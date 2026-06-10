from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .exceptions import InvalidWindowConfigError


@dataclass
class WindowConfig:
    name: str
    window_seconds: float
    max_operations: int
    slide_granularity_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise InvalidWindowConfigError("window name cannot be empty")
        if self.window_seconds <= 0:
            raise InvalidWindowConfigError(
                f"window_seconds must be positive for window '{self.name}'"
            )
        if self.max_operations <= 0:
            raise InvalidWindowConfigError(
                f"max_operations must be positive for window '{self.name}'"
            )
        if self.slide_granularity_seconds < 0:
            raise InvalidWindowConfigError(
                f"slide_granularity_seconds cannot be negative for window '{self.name}'"
            )
        if (
            self.slide_granularity_seconds > 0
            and self.slide_granularity_seconds > self.window_seconds
        ):
            raise InvalidWindowConfigError(
                f"slide_granularity_seconds ({self.slide_granularity_seconds}) "
                f"cannot exceed window_seconds ({self.window_seconds}) "
                f"for window '{self.name}'"
            )


@dataclass
class WindowUsage:
    window_name: str
    limit: int
    used: int
    remaining: int
    window_seconds: float


@dataclass
class SubjectQuotas:
    subject_id: str
    per_window_quotas: Dict[str, int] = field(default_factory=dict)

    def get_quota(self, window_name: str, default: int) -> int:
        return self.per_window_quotas.get(window_name, default)


@dataclass
class RateCapConfig:
    windows: List[WindowConfig]
    subject_quotas: Dict[str, SubjectQuotas] = field(default_factory=dict)
    default_subject_quotas: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.windows:
            raise InvalidWindowConfigError("At least one window must be configured")

        seen: set[str] = set()
        for window in self.windows:
            if window.name in seen:
                raise InvalidWindowConfigError(
                    f"Duplicate window name: '{window.name}'"
                )
            seen.add(window.name)

        for subject_id, quotas in self.subject_quotas.items():
            if subject_id != quotas.subject_id:
                raise InvalidWindowConfigError(
                    f"SubjectQuotas.subject_id mismatch: key='{subject_id}', "
                    f"value.subject_id='{quotas.subject_id}'"
                )
            for window_name, limit in quotas.per_window_quotas.items():
                if window_name not in seen:
                    raise InvalidWindowConfigError(
                        f"Subject '{subject_id}' references unknown window '{window_name}'"
                    )
                if limit <= 0:
                    raise InvalidWindowConfigError(
                        f"Subject '{subject_id}' window '{window_name}' "
                        f"quota must be positive"
                    )

        for window_name, limit in self.default_subject_quotas.items():
            if window_name not in seen:
                raise InvalidWindowConfigError(
                    f"default_subject_quotas references unknown window '{window_name}'"
                )
            if limit <= 0:
                raise InvalidWindowConfigError(
                    f"default_subject_quotas window '{window_name}' "
                    f"quota must be positive"
                )

    def get_window(self, name: str) -> Optional[WindowConfig]:
        for w in self.windows:
            if w.name == name:
                return w
        return None

    def get_subject_limit(self, subject_id: str, window_name: str) -> Optional[int]:
        subject = self.subject_quotas.get(subject_id)
        if subject is not None and window_name in subject.per_window_quotas:
            return subject.per_window_quotas[window_name]
        if window_name in self.default_subject_quotas:
            return self.default_subject_quotas[window_name]
        window = self.get_window(window_name)
        if window is not None:
            return window.max_operations
        return None

    def get_global_limit(self, window_name: str) -> Optional[int]:
        window = self.get_window(window_name)
        if window is not None:
            return window.max_operations
        return None
