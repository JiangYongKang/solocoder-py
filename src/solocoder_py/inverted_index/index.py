from __future__ import annotations

import base64
import math
import re
from typing import Optional

from .exceptions import DocumentExistsError, EmptyQueryError, InvalidCursorError
from .models import Posting, SearchResponse, SearchResult


class InvertedIndex:
    def __init__(self) -> None:
        self._index: dict[str, dict[str, int]] = {}
        self._documents: dict[str, str] = {}
        self._doc_term_counts: dict[str, int] = {}

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def vocabulary_size(self) -> int:
        return len(self._index)

    def add_document(self, doc_id: str, content: str) -> None:
        if doc_id in self._documents:
            raise DocumentExistsError(f"Document '{doc_id}' already exists")

        self._documents[doc_id] = content
        tokens = self._tokenize(content)
        term_counts: dict[str, int] = {}
        for token in tokens:
            term_counts[token] = term_counts.get(token, 0) + 1

        self._doc_term_counts[doc_id] = len(tokens)

        for term, freq in term_counts.items():
            if term not in self._index:
                self._index[term] = {}
            self._index[term][doc_id] = freq

    def get_postings(self, term: str) -> list[Posting]:
        normalized = term.lower().strip()
        if normalized not in self._index:
            return []
        return [
            Posting(doc_id=doc_id, term_freq=freq)
            for doc_id, freq in self._index[normalized].items()
        ]

    def search(
        self,
        query_terms: list[str],
        page_size: int = 10,
        cursor: Optional[str] = None,
    ) -> SearchResponse:
        if not query_terms:
            raise EmptyQueryError("Query terms list cannot be empty")

        normalized = [t.lower().strip() for t in query_terms if t.strip()]
        if not normalized:
            raise EmptyQueryError("Query terms list cannot be empty after normalization")

        matching_doc_ids = self._intersect(normalized)
        if not matching_doc_ids:
            return SearchResponse(results=[], next_cursor=None, total_count=0)

        scored = self._score_documents(matching_doc_ids, normalized)
        scored.sort(key=lambda r: (-r.score, r.doc_id))

        start_idx = 0
        if cursor is not None:
            cursor_score, cursor_doc_id = self._decode_cursor(cursor)
            start_idx = self._find_cursor_position(scored, cursor_score, cursor_doc_id)

        page = scored[start_idx:start_idx + page_size]
        next_cursor = None
        if start_idx + page_size < len(scored):
            last = page[-1]
            next_cursor = self._encode_cursor(last.score, last.doc_id)

        return SearchResponse(
            results=page,
            next_cursor=next_cursor,
            total_count=len(scored),
        )

    def _intersect(self, terms: list[str]) -> set[str]:
        postings_list: list[set[str]] = []
        for term in terms:
            if term not in self._index:
                return set()
            postings_list.append(set(self._index[term].keys()))

        result = postings_list[0]
        for postings in postings_list[1:]:
            result = result & postings
        return result

    def _score_documents(
        self, doc_ids: set[str], terms: list[str]
    ) -> list[SearchResult]:
        n = self.document_count
        results: list[SearchResult] = []
        for doc_id in doc_ids:
            score = 0.0
            for term in terms:
                if term in self._index and doc_id in self._index[term]:
                    tf = self._index[term][doc_id]
                    df = len(self._index[term])
                    idf = math.log((1 + n) / (1 + df)) + 1
                    score += tf * idf
            results.append(SearchResult(doc_id=doc_id, score=score))
        return results

    def _find_cursor_position(
        self,
        sorted_results: list[SearchResult],
        cursor_score: float,
        cursor_doc_id: str,
    ) -> int:
        for i, r in enumerate(sorted_results):
            if r.score < cursor_score:
                return i
            if r.score == cursor_score and r.doc_id > cursor_doc_id:
                return i
            if r.score == cursor_score and r.doc_id == cursor_doc_id:
                return i + 1
        return len(sorted_results)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t.lower() for t in re.findall(r"\w+", text)]

    @staticmethod
    def _encode_cursor(score: float, doc_id: str) -> str:
        raw = f"{score}:{doc_id}"
        return base64.b64encode(raw.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[float, str]:
        try:
            raw = base64.b64decode(cursor.encode()).decode()
            parts = raw.split(":", 1)
            return float(parts[0]), parts[1]
        except Exception:
            raise InvalidCursorError(f"Invalid cursor: '{cursor}'")
