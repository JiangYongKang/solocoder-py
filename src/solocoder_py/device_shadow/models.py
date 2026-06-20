from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldDiff:
    path: str
    desired_value: Any
    reported_value: Any


@dataclass(frozen=True)
class ShadowDiff:
    desired_only: list[FieldDiff] = field(default_factory=list)
    reported_only: list[FieldDiff] = field(default_factory=list)
    value_diff: list[FieldDiff] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.desired_only or self.reported_only or self.value_diff)
