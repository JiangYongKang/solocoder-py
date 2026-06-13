from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GramPosting:
    doc_id: str
    positions: list[int]


@dataclass
class HighlightedFragment:
    text: str
    hit_start: int
    hit_end: int


@dataclass
class NGramSearchResult:
    doc_id: str
    hit_positions: list[int]
    fragments: list[HighlightedFragment] = field(default_factory=list)


@dataclass
class NGramSearchResponse:
    results: list[NGramSearchResult]
    total_count: int = 0
