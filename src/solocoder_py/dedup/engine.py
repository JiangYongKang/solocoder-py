from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .exact_matcher import exact_group
from .exceptions import EmptyMatchKeysError, InvalidConfigError, InvalidThresholdError
from .fuzzy_matcher import fuzzy_group
from .merge_strategies import (
    STRATEGY_FIRST,
    STRATEGY_LAST,
    merge_group,
)
from .models import DedupGroup, DedupResult, MergeFunction, Record


@dataclass
class DedupEngine:
    exact_match_keys: list[str] | None = None
    fuzzy_fields: list[str] | None = None
    fuzzy_threshold: float = 0.8
    fuzzy_field_weights: dict[str, float] | None = None
    merge_strategy: str = STRATEGY_FIRST
    custom_merge: MergeFunction | None = None
    field_merge_strategies: dict[str, str] | None = None
    fallback_merge_strategy: str = STRATEGY_LAST
    use_fuzzy: bool = False
    _records: list[Record] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.exact_match_keys is None and not self.use_fuzzy:
            raise InvalidConfigError(
                "At least one of exact_match_keys or use_fuzzy must be configured"
            )
        if self.exact_match_keys is not None and len(self.exact_match_keys) == 0:
            raise EmptyMatchKeysError("exact_match_keys cannot be empty")
        if self.use_fuzzy:
            if self.fuzzy_fields is None or len(self.fuzzy_fields) == 0:
                raise InvalidConfigError(
                    "fuzzy_fields must be provided when use_fuzzy is True"
                )
            if self.fuzzy_threshold <= 0 or self.fuzzy_threshold > 1:
                raise InvalidThresholdError(
                    "fuzzy_threshold must be in (0, 1]"
                )

    def add_record(self, record: Record) -> None:
        self._records.append(record)

    def add_records(self, records: list[Record]) -> None:
        self._records.extend(records)

    def clear(self) -> None:
        self._records.clear()

    @property
    def record_count(self) -> int:
        return len(self._records)

    def dedup(self) -> DedupResult:
        records = self._records
        n = len(records)

        if n == 0:
            return DedupResult(
                unique_records=[],
                groups=[],
                total_input=0,
                total_unique=0,
                total_duplicates=0,
            )

        groups = self._group_records(records)

        unique_records: list[Record] = []
        for group in groups:
            if len(group.records) == 1:
                unique_records.append(group.records[0])
            else:
                merge_result = merge_group(
                    group,
                    strategy=self.merge_strategy,
                    custom_merge=self.custom_merge,
                    field_strategies=self.field_merge_strategies,
                    fallback_strategy=self.fallback_merge_strategy,
                )
                unique_records.append(merge_result.record)

        total_unique = len(unique_records)
        total_duplicates = n - total_unique

        return DedupResult(
            unique_records=unique_records,
            groups=groups,
            total_input=n,
            total_unique=total_unique,
            total_duplicates=total_duplicates,
        )

    def _group_records(self, records: list[Record]) -> list[DedupGroup]:
        if self.exact_match_keys and not self.use_fuzzy:
            return exact_group(records, self.exact_match_keys)

        if self.use_fuzzy and self.exact_match_keys is None:
            return fuzzy_group(
                records,
                self.fuzzy_fields or [],
                self.fuzzy_threshold,
                self.fuzzy_field_weights,
            )

        if self.exact_match_keys and self.use_fuzzy:
            return self._hybrid_group(records)

        return [
            DedupGroup(records=[r], indices=[i], is_exact=True, match_score=1.0)
            for i, r in enumerate(records)
        ]

    def _hybrid_group(self, records: list[Record]) -> list[DedupGroup]:
        exact_groups = exact_group(records, self.exact_match_keys or [])

        if not self.use_fuzzy:
            return exact_groups

        all_groups: list[DedupGroup] = []
        for exact_group_obj in exact_groups:
            if len(exact_group_obj.records) <= 1:
                all_groups.append(exact_group_obj)
                continue

            fuzzy_subgroups = fuzzy_group(
                exact_group_obj.records,
                self.fuzzy_fields or [],
                self.fuzzy_threshold,
                self.fuzzy_field_weights,
            )

            for fg in fuzzy_subgroups:
                original_indices = [exact_group_obj.indices[i] for i in fg.indices]
                fg.indices = original_indices
                all_groups.append(fg)

        return all_groups
