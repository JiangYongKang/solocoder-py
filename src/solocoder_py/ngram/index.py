from __future__ import annotations

from typing import Optional

from .exceptions import (
    DocumentExistsError,
    DocumentNotFoundError,
    EmptyQueryError,
    InvalidContextSizeError,
    InvalidNValueError,
)
from .models import (
    GramPosting,
    HighlightedFragment,
    NGramSearchResponse,
    NGramSearchResult,
)

DEFAULT_HIGHLIGHT_START = "[["
DEFAULT_HIGHLIGHT_END = "]]"


class NGramIndex:
    def __init__(self, n: int = 2) -> None:
        if n < 1:
            raise InvalidNValueError(f"N value must be >= 1, got {n}")
        self._n = n
        self._index: dict[str, dict[str, list[int]]] = {}
        self._documents: dict[str, str] = {}
        self._doc_grams: dict[str, dict[str, list[int]]] = {}

    @property
    def n(self) -> int:
        return self._n

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def gram_count(self) -> int:
        return len(self._index)

    def add_document(self, doc_id: str, content: str) -> None:
        if doc_id in self._documents:
            raise DocumentExistsError(f"Document '{doc_id}' already exists")

        self._documents[doc_id] = content
        grams = self._extract_grams(content)
        self._doc_grams[doc_id] = grams
        for gram, positions in grams.items():
            if gram not in self._index:
                self._index[gram] = {}
            self._index[gram][doc_id] = positions

    def remove_document(self, doc_id: str) -> None:
        if doc_id not in self._documents:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found")

        grams = self._doc_grams[doc_id]
        for gram in grams:
            if gram in self._index and doc_id in self._index[gram]:
                del self._index[gram][doc_id]
                if not self._index[gram]:
                    del self._index[gram]

        del self._documents[doc_id]
        del self._doc_grams[doc_id]

    def update_document(self, doc_id: str, new_content: str) -> None:
        if doc_id not in self._documents:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found")

        old_grams = self._doc_grams[doc_id]
        new_grams = self._extract_grams(new_content)

        grams_to_remove = old_grams.keys() - new_grams.keys()
        grams_to_add = new_grams.keys() - old_grams.keys()
        grams_to_update = old_grams.keys() & new_grams.keys()

        for gram in grams_to_remove:
            if gram in self._index and doc_id in self._index[gram]:
                del self._index[gram][doc_id]
                if not self._index[gram]:
                    del self._index[gram]

        for gram in grams_to_add:
            if gram not in self._index:
                self._index[gram] = {}
            self._index[gram][doc_id] = new_grams[gram]

        for gram in grams_to_update:
            if old_grams[gram] != new_grams[gram]:
                self._index[gram][doc_id] = new_grams[gram]

        self._documents[doc_id] = new_content
        self._doc_grams[doc_id] = new_grams

    def get_gram_postings(self, gram: str) -> list[GramPosting]:
        if gram not in self._index:
            return []
        return [
            GramPosting(doc_id=doc_id, positions=list(positions))
            for doc_id, positions in self._index[gram].items()
        ]

    def search(
        self,
        query: str,
        context_size: int = 10,
        highlight_start: str = DEFAULT_HIGHLIGHT_START,
        highlight_end: str = DEFAULT_HIGHLIGHT_END,
    ) -> NGramSearchResponse:
        if not query:
            raise EmptyQueryError("Query string cannot be empty")
        if context_size < 0:
            raise InvalidContextSizeError(
                f"Context size must be >= 0, got {context_size}"
            )

        query_grams = self._extract_grams(query)
        if not query_grams:
            results = self._search_short_query(query, context_size, highlight_start, highlight_end)
            return NGramSearchResponse(results=results, total_count=len(results))

        gram_keys = list(query_grams.keys())
        candidate_doc_ids = self._find_candidate_docs(gram_keys)
        if not candidate_doc_ids:
            return NGramSearchResponse(results=[], total_count=0)

        results: list[NGramSearchResult] = []
        for doc_id in candidate_doc_ids:
            content = self._documents[doc_id]
            positions = self._verify_and_locate(doc_id, query, query_grams, content)
            if positions:
                fragments = [
                    self._extract_highlighted_fragment(
                        content, pos, len(query), context_size,
                        highlight_start, highlight_end
                    )
                    for pos in positions
                ]
                results.append(NGramSearchResult(
                    doc_id=doc_id,
                    hit_positions=positions,
                    fragments=fragments,
                ))

        results.sort(key=lambda r: (-len(r.hit_positions), r.doc_id))
        return NGramSearchResponse(results=results, total_count=len(results))

    def _search_short_query(
        self,
        query: str,
        context_size: int,
        highlight_start: str,
        highlight_end: str,
    ) -> list[NGramSearchResult]:
        results: list[NGramSearchResult] = []
        for doc_id, content in self._documents.items():
            positions: list[int] = []
            start = 0
            while True:
                idx = content.find(query, start)
                if idx == -1:
                    break
                positions.append(idx)
                start = idx + 1
            if positions:
                fragments = [
                    self._extract_highlighted_fragment(
                        content, pos, len(query), context_size,
                        highlight_start, highlight_end
                    )
                    for pos in positions
                ]
                results.append(NGramSearchResult(
                    doc_id=doc_id,
                    hit_positions=positions,
                    fragments=fragments,
                ))
        return results

    def _find_candidate_docs(self, gram_keys: list[str]) -> set[str]:
        if not gram_keys:
            return set()

        postings_sets: list[set[str]] = []
        for gram in gram_keys:
            if gram not in self._index:
                return set()
            postings_sets.append(set(self._index[gram].keys()))

        postings_sets.sort(key=lambda s: len(s))

        result = postings_sets[0]
        for postings in postings_sets[1:]:
            result = result & postings
            if not result:
                break
        return result

    def _verify_and_locate(
        self,
        doc_id: str,
        query: str,
        query_grams: dict[str, list[int]],
        content: str,
    ) -> list[int]:
        candidate_positions = self._merge_gram_positions(doc_id, query_grams)
        if not candidate_positions:
            return []

        verified: list[int] = []
        query_len = len(query)
        for pos in candidate_positions:
            if pos + query_len > len(content):
                continue
            if content[pos:pos + query_len] == query:
                verified.append(pos)
        verified.sort()
        return verified

    def _merge_gram_positions(
        self,
        doc_id: str,
        query_grams: dict[str, list[int]],
    ) -> set[int]:
        ordered_grams = list(query_grams.items())
        first_gram, first_query_offsets = ordered_grams[0]

        if first_gram not in self._index or doc_id not in self._index[first_gram]:
            return set()

        first_doc_positions = self._index[first_gram][doc_id]
        candidates: set[int] = set()
        for first_qoffset in first_query_offsets:
            for doc_pos in first_doc_positions:
                candidate = doc_pos - first_qoffset
                if candidate >= 0:
                    candidates.add(candidate)

        for gram, query_offsets in ordered_grams[1:]:
            if not candidates:
                break
            if gram not in self._index or doc_id not in self._index[gram]:
                return set()
            doc_positions = set(self._index[gram][doc_id])
            new_candidates: set[int] = set()
            for candidate in candidates:
                valid = True
                for qoffset in query_offsets:
                    if (candidate + qoffset) not in doc_positions:
                        valid = False
                        break
                if valid:
                    new_candidates.add(candidate)
            candidates = new_candidates

        return candidates

    def _extract_grams(self, text: str) -> dict[str, list[int]]:
        grams: dict[str, list[int]] = {}
        text_len = len(text)
        n = self._n
        if text_len < n:
            return grams
        for i in range(text_len - n + 1):
            gram = text[i:i + n]
            if gram not in grams:
                grams[gram] = []
            grams[gram].append(i)
        return grams

    @staticmethod
    def _extract_highlighted_fragment(
        content: str,
        hit_start: int,
        hit_length: int,
        context_size: int,
        highlight_start: str,
        highlight_end: str,
    ) -> HighlightedFragment:
        content_len = len(content)
        hit_end = hit_start + hit_length

        frag_start = max(0, hit_start - context_size)
        frag_end = min(content_len, hit_end + context_size)

        before = content[frag_start:hit_start]
        hit_text = content[hit_start:hit_end]
        after = content[hit_end:frag_end]

        highlighted = before + highlight_start + hit_text + highlight_end + after

        rel_hit_start = len(before)
        rel_hit_end = rel_hit_start + len(highlight_start) + hit_length + len(highlight_end)

        return HighlightedFragment(
            text=highlighted,
            hit_start=rel_hit_start,
            hit_end=rel_hit_end,
        )
