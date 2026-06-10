from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Posting:
    doc_id: str
    term_freq: int


@dataclass
class SearchResult:
    doc_id: str
    score: float


@dataclass
class SearchResponse:
    results: list[SearchResult]
    next_cursor: str | None = None
    total_count: int = 0
