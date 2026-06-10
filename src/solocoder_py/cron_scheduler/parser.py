from __future__ import annotations

import re
from typing import FrozenSet, List, Optional, Set

from .exceptions import (
    CronParseError,
    InvalidFieldValueError,
    InvalidRangeError,
    InvalidStepError,
)
from .models import (
    FIELD_NAMES,
    FIELD_RANGES,
    CronExpression,
    CronField,
    FieldType,
)


_RANGE_PATTERN = re.compile(r"^(-?\d+)-(-?\d+)$")


class CronParser:
    _FIELD_ORDER: List[FieldType] = [
        FieldType.MINUTE,
        FieldType.HOUR,
        FieldType.DAY_OF_MONTH,
        FieldType.MONTH,
        FieldType.DAY_OF_WEEK,
    ]

    @classmethod
    def parse(cls, expression: str) -> CronExpression:
        if not expression or not expression.strip():
            raise CronParseError("Cron expression cannot be empty")

        parts = expression.strip().split()
        if len(parts) != 5:
            raise CronParseError(
                f"Cron expression must have exactly 5 fields, got {len(parts)}: '{expression}'"
            )

        fields: dict[FieldType, CronField] = {}
        for i, field_type in enumerate(cls._FIELD_ORDER):
            raw_field = parts[i]
            fields[field_type] = cls._parse_field(raw_field, field_type)

        return CronExpression(
            raw=expression,
            minute=fields[FieldType.MINUTE],
            hour=fields[FieldType.HOUR],
            day_of_month=fields[FieldType.DAY_OF_MONTH],
            month=fields[FieldType.MONTH],
            day_of_week=fields[FieldType.DAY_OF_WEEK],
        )

    @classmethod
    def _parse_field(cls, raw: str, field_type: FieldType) -> CronField:
        if not raw:
            raise CronParseError(
                f"Empty field expression for '{FIELD_NAMES[field_type]}'"
            )

        min_val, max_val = FIELD_RANGES[field_type]
        values: Set[int] = set()

        segments = raw.split(",")
        for segment in segments:
            segment = segment.strip()
            if not segment:
                raise CronParseError(
                    f"Empty segment in field '{FIELD_NAMES[field_type]}': '{raw}'"
                )
            values.update(cls._parse_segment(segment, field_type, min_val, max_val))

        if not values:
            raise CronParseError(
                f"No valid values parsed for field '{FIELD_NAMES[field_type]}': '{raw}'"
            )

        return CronField(
            field_type=field_type,
            values=frozenset(values),
            raw_expression=raw,
        )

    @classmethod
    def _parse_segment(
        cls,
        segment: str,
        field_type: FieldType,
        min_val: int,
        max_val: int,
    ) -> Set[int]:
        if "/" in segment:
            return cls._parse_step_segment(segment, field_type, min_val, max_val)

        range_match = _RANGE_PATTERN.match(segment)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            cls._validate_range(field_type, start, end, min_val, max_val)
            return set(range(start, end + 1))

        if segment == "*":
            return set(range(min_val, max_val + 1))

        return cls._parse_single_value(segment, field_type, min_val, max_val)

    @classmethod
    def _parse_step_segment(
        cls,
        segment: str,
        field_type: FieldType,
        min_val: int,
        max_val: int,
    ) -> Set[int]:
        parts = segment.split("/")
        if len(parts) != 2:
            raise CronParseError(
                f"Invalid step syntax in field '{FIELD_NAMES[field_type]}': '{segment}'"
            )

        range_part, step_part = parts[0], parts[1]

        try:
            step = int(step_part)
        except ValueError:
            raise CronParseError(
                f"Invalid step value '{step_part}' in field '{FIELD_NAMES[field_type]}': must be an integer"
            )

        if step <= 0 or step > max_val:
            raise InvalidStepError(FIELD_NAMES[field_type], step, max_val)

        range_start, range_end = cls._parse_step_range_part(
            range_part, field_type, min_val, max_val
        )

        cls._validate_range(field_type, range_start, range_end, min_val, max_val)

        values: Set[int] = set()
        current = range_start
        while current <= range_end:
            values.add(current)
            current += step

        return values

    @classmethod
    def _parse_step_range_part(
        cls,
        range_part: str,
        field_type: FieldType,
        min_val: int,
        max_val: int,
    ) -> tuple[int, int]:
        if range_part == "*":
            return (min_val, max_val)

        if "-" in range_part:
            range_parts = range_part.split("-")
            if len(range_parts) != 2:
                raise CronParseError(
                    f"Invalid range syntax in step segment for field '{FIELD_NAMES[field_type]}': '{range_part}'"
                )
            try:
                start = int(range_parts[0])
                end = int(range_parts[1])
            except ValueError:
                raise CronParseError(
                    f"Invalid range values in field '{FIELD_NAMES[field_type]}': '{range_part}'"
                )
            return (start, end)

        try:
            start = int(range_part)
        except ValueError:
            raise CronParseError(
                f"Invalid start value '{range_part}' in step segment for field '{FIELD_NAMES[field_type]}'"
            )
        return (start, max_val)

    @classmethod
    def _parse_range_segment(
        cls,
        segment: str,
        field_type: FieldType,
        min_val: int,
        max_val: int,
    ) -> Set[int]:
        parts = segment.split("-")
        if len(parts) != 2:
            raise CronParseError(
                f"Invalid range syntax in field '{FIELD_NAMES[field_type]}': '{segment}'"
            )

        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            raise CronParseError(
                f"Invalid range values in field '{FIELD_NAMES[field_type]}': '{segment}'"
            )

        cls._validate_range(field_type, start, end, min_val, max_val)

        return set(range(start, end + 1))

    @classmethod
    def _parse_single_value(
        cls,
        value_str: str,
        field_type: FieldType,
        min_val: int,
        max_val: int,
    ) -> Set[int]:
        try:
            value = int(value_str)
        except ValueError:
            raise CronParseError(
                f"Invalid value '{value_str}' in field '{FIELD_NAMES[field_type]}': must be an integer, '*', range, or step expression"
            )

        if value < min_val or value > max_val:
            raise InvalidFieldValueError(
                FIELD_NAMES[field_type], value, min_val, max_val
            )

        return {value}

    @classmethod
    def _validate_range(
        cls,
        field_type: FieldType,
        start: int,
        end: int,
        min_val: int,
        max_val: int,
    ) -> None:
        if start < min_val or start > max_val:
            raise InvalidFieldValueError(
                FIELD_NAMES[field_type], start, min_val, max_val
            )
        if end < min_val or end > max_val:
            raise InvalidFieldValueError(
                FIELD_NAMES[field_type], end, min_val, max_val
            )
        if start > end:
            raise InvalidRangeError(FIELD_NAMES[field_type], start, end)
