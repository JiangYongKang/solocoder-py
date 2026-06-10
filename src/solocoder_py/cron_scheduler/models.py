from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, List, Optional


class FieldType(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY_OF_MONTH = "day_of_month"
    MONTH = "month"
    DAY_OF_WEEK = "day_of_week"


FIELD_RANGES: dict[FieldType, tuple[int, int]] = {
    FieldType.MINUTE: (0, 59),
    FieldType.HOUR: (0, 23),
    FieldType.DAY_OF_MONTH: (1, 31),
    FieldType.MONTH: (1, 12),
    FieldType.DAY_OF_WEEK: (0, 6),
}

FIELD_NAMES: dict[FieldType, str] = {
    FieldType.MINUTE: "minute",
    FieldType.HOUR: "hour",
    FieldType.DAY_OF_MONTH: "day of month",
    FieldType.MONTH: "month",
    FieldType.DAY_OF_WEEK: "day of week",
}


@dataclass(frozen=True)
class CronField:
    field_type: FieldType
    values: FrozenSet[int] = field(hash=True)
    raw_expression: str

    @property
    def min_value(self) -> int:
        return FIELD_RANGES[self.field_type][0]

    @property
    def max_value(self) -> int:
        return FIELD_RANGES[self.field_type][1]

    @property
    def name(self) -> str:
        return FIELD_NAMES[self.field_type]

    def contains(self, value: int) -> bool:
        return value in self.values

    def sorted_values(self) -> List[int]:
        return sorted(self.values)

    def next_value(self, current: int) -> Optional[int]:
        sorted_vals = self.sorted_values()
        for v in sorted_vals:
            if v >= current:
                return v
        return None

    def __len__(self) -> int:
        return len(self.values)


@dataclass
class CronExpression:
    raw: str
    minute: CronField
    hour: CronField
    day_of_month: CronField
    month: CronField
    day_of_week: CronField

    @property
    def fields(self) -> List[CronField]:
        return [
            self.minute,
            self.hour,
            self.day_of_month,
            self.month,
            self.day_of_week,
        ]

    def __str__(self) -> str:
        return self.raw
