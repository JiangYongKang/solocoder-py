from __future__ import annotations

from typing import Any

from .exceptions import EmptyMatchKeysError
from .models import DedupGroup, Record


def _make_hashable(value: Any) -> Any:
    if isinstance(value, (list, set)):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in value.items()))
    return value


def _build_key(record: Record, keys: list[str]) -> tuple[Any, ...]:
    return tuple(_make_hashable(record.get(k)) for k in keys)


def exact_group(
    records: list[Record],
    match_keys: list[str],
) -> list[DedupGroup]:
    if not match_keys:
        raise EmptyMatchKeysError("match_keys cannot be empty")

    groups_dict: dict[tuple[Any, ...], DedupGroup] = {}

    for idx, record in enumerate(records):
        key = _build_key(record, match_keys)
        if key not in groups_dict:
            groups_dict[key] = DedupGroup(
                records=[],
                indices=[],
                is_exact=True,
                match_score=1.0,
            )
        groups_dict[key].records.append(record)
        groups_dict[key].indices.append(idx)

    return list(groups_dict.values())


def keep_first(group: DedupGroup) -> Record:
    return group.records[0]


def keep_last(group: DedupGroup) -> Record:
    return group.records[-1]


def keep_most_complete(group: DedupGroup) -> Record:
    def _count_non_empty(record: Record) -> int:
        count = 0
        for v in record.values():
            if v is not None and v != "" and v != [] and v != {}:
                count += 1
        return count

    best = group.records[0]
    best_count = _count_non_empty(best)
    for record in group.records[1:]:
        cnt = _count_non_empty(record)
        if cnt > best_count:
            best = record
            best_count = cnt
    return best


def keep_by_field(
    group: DedupGroup,
    field: str,
    desc: bool = True,
) -> Record:
    sorted_records = sorted(
        group.records,
        key=lambda r: r.get(field),
        reverse=desc,
    )
    return sorted_records[0]
