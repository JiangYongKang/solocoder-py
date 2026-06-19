from __future__ import annotations

from typing import List, Optional, Tuple

from .exceptions import (
    NonMonotonicTimestampError,
    InvalidTimestampError,
)
from .models import DeltaResult


def validate_timestamps(timestamps: List[int]) -> None:
    if not timestamps:
        return

    for ts in timestamps:
        if not isinstance(ts, int):
            raise InvalidTimestampError(
                f"Timestamp must be integer, got {type(ts).__name__}"
            )

    for i in range(1, len(timestamps)):
        if timestamps[i] <= timestamps[i - 1]:
            raise NonMonotonicTimestampError(
                f"Timestamps must be strictly increasing: "
                f"timestamps[{i}] = {timestamps[i]} <= timestamps[{i-1}] = {timestamps[i-1]}"
            )


def compute_first_order_deltas(timestamps: List[int]) -> List[int]:
    if len(timestamps) < 2:
        return []

    deltas: List[int] = []
    for i in range(1, len(timestamps)):
        deltas.append(timestamps[i] - timestamps[i - 1])

    return deltas


def compute_second_order_deltas(first_order_deltas: List[int]) -> List[int]:
    if len(first_order_deltas) < 2:
        return []

    deltas: List[int] = []
    for i in range(1, len(first_order_deltas)):
        deltas.append(first_order_deltas[i] - first_order_deltas[i - 1])

    return deltas


def compute_deltas(timestamps: List[int], validate: bool = True) -> DeltaResult:
    if validate:
        validate_timestamps(timestamps)

    if len(timestamps) == 0:
        return DeltaResult(
            first_order_deltas=[],
            second_order_deltas=[],
            base_timestamp=0,
            first_delta=None,
        )

    if len(timestamps) == 1:
        return DeltaResult(
            first_order_deltas=[],
            second_order_deltas=[],
            base_timestamp=timestamps[0],
            first_delta=None,
        )

    first_order = compute_first_order_deltas(timestamps)

    if len(timestamps) == 2:
        return DeltaResult(
            first_order_deltas=first_order,
            second_order_deltas=[],
            base_timestamp=timestamps[0],
            first_delta=first_order[0],
        )

    second_order = compute_second_order_deltas(first_order)

    return DeltaResult(
        first_order_deltas=first_order,
        second_order_deltas=second_order,
        base_timestamp=timestamps[0],
        first_delta=first_order[0],
    )


def reconstruct_first_order_deltas(
    first_delta: int,
    second_order_deltas: List[int],
) -> List[int]:
    first_order: List[int] = [first_delta]

    for delta in second_order_deltas:
        first_order.append(first_order[-1] + delta)

    return first_order


def reconstruct_timestamps(
    base_timestamp: int,
    first_delta: Optional[int],
    second_order_deltas: List[int],
    expected_count: Optional[int] = None,
) -> List[int]:
    if expected_count is not None and expected_count == 0:
        return []

    if expected_count is not None and expected_count == 1:
        return [base_timestamp]

    if first_delta is None:
        return [base_timestamp]

    first_order = reconstruct_first_order_deltas(first_delta, second_order_deltas)

    timestamps: List[int] = [base_timestamp]
    current = base_timestamp

    for delta in first_order:
        current += delta
        timestamps.append(current)

    if expected_count is not None and len(timestamps) != expected_count:
        from .exceptions import DataLengthMismatchError
        raise DataLengthMismatchError(
            f"Expected {expected_count} timestamps, got {len(timestamps)}"
        )

    return timestamps
