from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FacetError(Exception):
    pass


class FieldNotFoundError(FacetError):
    pass


class ItemNotFoundError(FacetError):
    pass


class DuplicateItemError(FacetError):
    pass


class InvalidFilterError(FacetError):
    pass


class InvalidBucketError(FacetError):
    pass


class FacetFieldType(str, Enum):
    CATEGORICAL = "categorical"
    NUMERIC = "numeric"


@dataclass
class NumericBucket:
    min: Optional[float]
    max: Optional[float]
    label: str

    def __post_init__(self) -> None:
        if self.min is None and self.max is None:
            raise InvalidBucketError("Bucket must have at least one of min or max")
        if self.min is not None and self.max is not None and self.min >= self.max:
            raise InvalidBucketError(f"Bucket min {self.min} must be less than max {self.max}")

    def contains(self, value: float) -> bool:
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and value >= self.max:
            return False
        return True


@dataclass
class FacetConfig:
    field_name: str
    field_type: FacetFieldType
    buckets: Optional[List[NumericBucket]] = None

    def __post_init__(self) -> None:
        if self.field_type == FacetFieldType.NUMERIC and not self.buckets:
            raise InvalidBucketError(
                f"Numeric field '{self.field_name}' requires buckets configuration"
            )
        if self.field_type == FacetFieldType.CATEGORICAL and self.buckets:
            raise InvalidBucketError(
                f"Categorical field '{self.field_name}' should not have buckets"
            )
        if self.buckets:
            self._validate_buckets()

    def _validate_buckets(self) -> None:
        for bucket in self.buckets:
            if not isinstance(bucket, NumericBucket):
                raise InvalidBucketError(
                    f"All buckets for field '{self.field_name}' must be NumericBucket instances"
                )


@dataclass
class FacetValueCount:
    value: Any
    count: int
    selected: bool = False


@dataclass
class FacetResult:
    field_name: str
    field_type: FacetFieldType
    values: List[FacetValueCount]


@dataclass
class SearchResult:
    total_count: int
    items: List[Dict[str, Any]]
    facets: List[FacetResult]
    active_filters: Dict[str, List[Any]]
