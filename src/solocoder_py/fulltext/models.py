from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Document:
    doc_id: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class TermInfo:
    term: str
    doc_id: str
    frequency: int
    positions: list[int] = field(default_factory=list)


@dataclass
class SearchResult:
    doc_id: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
