from __future__ import annotations

from typing import Any

from .exceptions import MergeConflictError, UnknownStrategyError
from .models import DedupGroup, MergeFunction, MergeResult, Record


STRATEGY_FIRST = "first"
STRATEGY_LAST = "last"
STRATEGY_LONGEST_STRING = "longest_string"
STRATEGY_MOST_COMMON = "most_common"
STRATEGY_CUSTOM = "custom"
STRATEGY_FIRST_NON_EMPTY = "first_non_empty"

ALL_STRATEGIES = [
    STRATEGY_FIRST,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_MOST_COMMON,
    STRATEGY_FIRST_NON_EMPTY,
    STRATEGY_CUSTOM,
]


def _all_equal(values: list[Any]) -> bool:
    if not values:
        return True
    first = values[0]
    for v in values[1:]:
        if v != first:
            return False
    return True


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and v == "":
        return False
    if isinstance(v, (list, dict, set, tuple)) and len(v) == 0:
        return False
    return True


def _resolve_first(field: str, values: list[Any]) -> Any:
    return values[0]


def _resolve_last(field: str, values: list[Any]) -> Any:
    return values[-1]


def _resolve_longest_string(field: str, values: list[Any]) -> Any:
    best = values[0]
    best_len = len(str(best)) if _has_value(best) else -1
    for v in values[1:]:
        if not _has_value(v):
            continue
        v_len = len(str(v))
        if v_len > best_len:
            best = v
            best_len = v_len
    return best


def _resolve_most_common(field: str, values: list[Any]) -> Any:
    counts: dict[str, int] = {}
    val_map: dict[str, Any] = {}
    for v in values:
        key = str(v)
        counts[key] = counts.get(key, 0) + 1
        val_map[key] = v
    max_count = max(counts.values())
    for v in values:
        key = str(v)
        if counts[key] == max_count:
            return v
    return values[0]


def _resolve_first_non_empty(field: str, values: list[Any]) -> Any:
    for v in values:
        if _has_value(v):
            return v
    return values[0]


_STRATEGY_RESOLVERS = {
    STRATEGY_FIRST: _resolve_first,
    STRATEGY_LAST: _resolve_last,
    STRATEGY_LONGEST_STRING: _resolve_longest_string,
    STRATEGY_MOST_COMMON: _resolve_most_common,
    STRATEGY_FIRST_NON_EMPTY: _resolve_first_non_empty,
}


def merge_group(
    group: DedupGroup,
    strategy: str = STRATEGY_FIRST,
    custom_merge: MergeFunction | None = None,
    field_strategies: dict[str, str] | None = None,
    fallback_strategy: str = STRATEGY_LAST,
) -> MergeResult:
    if not group.records:
        raise MergeConflictError("Cannot merge empty group")

    if strategy not in ALL_STRATEGIES:
        raise UnknownStrategyError(f"Unknown strategy: {strategy}")

    if strategy == STRATEGY_CUSTOM and custom_merge is None:
        raise UnknownStrategyError(
            "custom_merge function must be provided for 'custom' strategy"
        )

    records = group.records
    all_fields: set[str] = set()
    for r in records:
        all_fields.update(r.keys())

    merged: Record = {}
    conflict_fields: list[str] = []
    merged_fields: list[str] = []
    fallback_fields: list[str] = []

    def _apply_strategy(
        field_name: str,
        field_values: list[Any],
        strat: str,
    ) -> tuple[Any, bool]:
        used_fallback = False
        current_strat = strat

        if current_strat == STRATEGY_CUSTOM and custom_merge is not None:
            try:
                return custom_merge(field_name, field_values), False
            except Exception:
                current_strat = fallback_strategy
                used_fallback = True

        if current_strat == STRATEGY_CUSTOM and custom_merge is None:
            current_strat = fallback_strategy
            used_fallback = True

        resolver = _STRATEGY_RESOLVERS.get(current_strat)
        if resolver is None:
            resolver = _STRATEGY_RESOLVERS.get(fallback_strategy)
            used_fallback = True

        try:
            return resolver(field_name, field_values), used_fallback
        except Exception:
            return field_values[0], True

    for field in all_fields:
        values = [r.get(field) for r in records]

        if _all_equal(values):
            merged[field] = values[0]
            continue

        conflict_fields.append(field)

        field_strategy = (field_strategies or {}).get(field, strategy)
        merged_value, used_fallback = _apply_strategy(field, values, field_strategy)
        merged[field] = merged_value
        merged_fields.append(field)
        if used_fallback:
            fallback_fields.append(field)

    return MergeResult(
        record=merged,
        conflict_fields=conflict_fields,
        merged_fields=merged_fields,
        fallback_fields=fallback_fields,
    )
