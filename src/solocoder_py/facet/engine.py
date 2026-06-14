from __future__ import annotations

import threading
from typing import Any, Dict, Iterable, List, Optional, Set

from .models import (
    DuplicateItemError,
    FacetConfig,
    FacetError,
    FacetFieldType,
    FacetResult,
    FacetValueCount,
    FieldNotFoundError,
    InvalidBucketError,
    InvalidFilterError,
    ItemNotFoundError,
    NumericBucket,
    SearchResult,
)


class FacetSearchEngine:
    def __init__(self, facet_configs: Iterable[FacetConfig]) -> None:
        self._facet_configs: Dict[str, FacetConfig] = {}
        for config in facet_configs:
            if config.field_name in self._facet_configs:
                raise FacetError(f"Duplicate facet field: {config.field_name}")
            self._facet_configs[config.field_name] = config

        self._items: Dict[str, Dict[str, Any]] = {}
        self._active_filters: Dict[str, Set[Any]] = {}
        self._lock = threading.RLock()

    def _validate_field_exists(self, field_name: str) -> None:
        if field_name not in self._facet_configs:
            raise FieldNotFoundError(f"Field not configured: {field_name}")

    def _get_item_id(self, item: Dict[str, Any]) -> str:
        if "id" not in item:
            raise FacetError("Item must have an 'id' field")
        return str(item["id"])

    def _validate_item_fields(self, item: Dict[str, Any]) -> None:
        for field_name, config in self._facet_configs.items():
            if field_name not in item:
                raise FacetError(
                    f"Item missing configured facet field: {field_name}"
                )
            if config.field_type == FacetFieldType.NUMERIC:
                value = item[field_name]
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise FacetError(
                        f"Numeric field '{field_name}' requires numeric value, got {type(value).__name__}"
                    )

    def _validate_bucket_label(self, field_name: str, label: str) -> None:
        config = self._facet_configs[field_name]
        if config.field_type != FacetFieldType.NUMERIC:
            return
        bucket_labels = {b.label for b in config.buckets}
        if label not in bucket_labels:
            raise InvalidFilterError(
                f"Invalid bucket label '{label}' for field '{field_name}'. "
                f"Valid labels: {sorted(bucket_labels)}"
            )

    def add_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            item_id = self._get_item_id(item)
            if item_id in self._items:
                raise DuplicateItemError(f"Item already exists: {item_id}")

            self._validate_item_fields(item)

            self._items[item_id] = dict(item)
            return self._items[item_id]

    def remove_item(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._items:
                raise ItemNotFoundError(f"Item not found: {item_id}")
            del self._items[item_id]

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._items.get(item_id)
            return dict(item) if item is not None else None

    def list_items(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._items.values()]

    def add_filter(self, field_name: str, value: Any) -> None:
        with self._lock:
            self._validate_field_exists(field_name)
            self._validate_bucket_label(field_name, value)

            if field_name not in self._active_filters:
                self._active_filters[field_name] = set()
            self._active_filters[field_name].add(value)

    def remove_filter(self, field_name: str, value: Any) -> None:
        with self._lock:
            self._validate_field_exists(field_name)

            if field_name not in self._active_filters:
                raise InvalidFilterError(
                    f"No active filters for field: {field_name}"
                )
            if value not in self._active_filters[field_name]:
                raise InvalidFilterError(
                    f"Filter value '{value}' not active for field: {field_name}"
                )

            self._active_filters[field_name].discard(value)
            if not self._active_filters[field_name]:
                del self._active_filters[field_name]

    def clear_field_filter(self, field_name: str) -> None:
        with self._lock:
            self._validate_field_exists(field_name)
            self._active_filters.pop(field_name, None)

    def clear_all_filters(self) -> None:
        with self._lock:
            self._active_filters.clear()

    def get_active_filters(self) -> Dict[str, List[Any]]:
        with self._lock:
            return {
                field: sorted(list(values))
                for field, values in self._active_filters.items()
            }

    def _matches_field_filter(
        self,
        item: Dict[str, Any],
        field_name: str,
        filter_values: Set[Any],
    ) -> bool:
        if not filter_values:
            return True

        item_value = item[field_name]
        config = self._facet_configs[field_name]

        if config.field_type == FacetFieldType.CATEGORICAL:
            return item_value in filter_values
        else:
            for bucket_label in filter_values:
                for bucket in config.buckets:
                    if bucket.label == bucket_label and bucket.contains(item_value):
                        return True
            return False

    def _matches_all_filters(
        self,
        item: Dict[str, Any],
        exclude_field: Optional[str] = None,
    ) -> bool:
        for field_name, filter_values in self._active_filters.items():
            if field_name == exclude_field:
                continue
            if not self._matches_field_filter(item, field_name, filter_values):
                return False
        return True

    def _get_filtered_items(
        self, exclude_field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._active_filters:
            return list(self._items.values())

        return [
            item
            for item in self._items.values()
            if self._matches_all_filters(item, exclude_field)
        ]

    def _compute_categorical_facet(
        self,
        field_name: str,
        items: List[Dict[str, Any]],
    ) -> FacetResult:
        value_counts: Dict[Any, int] = {}
        for item in items:
            value = item[field_name]
            value_counts[value] = value_counts.get(value, 0) + 1

        active_values = self._active_filters.get(field_name, set())
        facet_values = [
            FacetValueCount(
                value=value,
                count=count,
                selected=value in active_values,
            )
            for value, count in sorted(value_counts.items(), key=lambda x: str(x[0]))
        ]

        return FacetResult(
            field_name=field_name,
            field_type=FacetFieldType.CATEGORICAL,
            values=facet_values,
        )

    def _compute_numeric_facet(
        self,
        field_name: str,
        config: FacetConfig,
        items: List[Dict[str, Any]],
    ) -> FacetResult:
        bucket_counts: Dict[str, int] = {
            bucket.label: 0 for bucket in config.buckets
        }
        bucket_values: Dict[str, NumericBucket] = {
            bucket.label: bucket for bucket in config.buckets
        }

        for item in items:
            value = item[field_name]
            for bucket in config.buckets:
                if bucket.contains(value):
                    bucket_counts[bucket.label] += 1
                    break

        active_values = self._active_filters.get(field_name, set())
        facet_values = []
        for bucket in config.buckets:
            count = bucket_counts[bucket.label]
            selected = bucket.label in active_values
            facet_values.append(
                FacetValueCount(
                    value=bucket.label,
                    count=count,
                    selected=selected,
                )
            )

        return FacetResult(
            field_name=field_name,
            field_type=FacetFieldType.NUMERIC,
            values=facet_values,
        )

    def _compute_facets(
        self, matched_items: List[Dict[str, Any]]
    ) -> List[FacetResult]:
        facets: List[FacetResult] = []

        matched_ids = {item["id"] for item in matched_items}

        for field_name, config in self._facet_configs.items():
            if field_name in self._active_filters:
                items_for_facet = list(matched_items)
                for item_id, item in self._items.items():
                    if item_id in matched_ids:
                        continue
                    if self._matches_all_filters(item, exclude_field=field_name):
                        items_for_facet.append(item)
            else:
                items_for_facet = matched_items

            if config.field_type == FacetFieldType.CATEGORICAL:
                facet = self._compute_categorical_facet(
                    field_name, items_for_facet
                )
            else:
                facet = self._compute_numeric_facet(
                    field_name, config, items_for_facet
                )
            facets.append(facet)

        return facets

    def search(self) -> SearchResult:
        with self._lock:
            matched_items = self._get_filtered_items()
            facets = self._compute_facets(matched_items)
            active_filters = self.get_active_filters()

            return SearchResult(
                total_count=len(matched_items),
                items=[dict(item) for item in matched_items],
                facets=facets,
                active_filters=active_filters,
            )

    def get_total_count(self) -> int:
        with self._lock:
            return len(self._items)
