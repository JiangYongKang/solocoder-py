from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


Record = dict[str, Any]
MergeFunction = Callable[[str, list[Any]], Any]


@dataclass
class FuzzyMatchPair:
    index_a: int
    index_b: int
    score: float
    matched_fields: dict[str, float] = field(default_factory=dict)


@dataclass
class DedupGroup:
    records: list[Record]
    indices: list[int]
    is_exact: bool = False
    match_score: float = 1.0
    fuzzy_pairs: list[FuzzyMatchPair] = field(default_factory=list)


@dataclass
class DedupResult:
    unique_records: list[Record]
    groups: list[DedupGroup]
    total_input: int
    total_unique: int
    total_duplicates: int
    fallback_fields: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class MergeResult:
    record: Record
    conflict_fields: list[str]
    merged_fields: list[str]
    fallback_fields: list[str] = field(default_factory=list)
