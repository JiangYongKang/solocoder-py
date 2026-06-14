from __future__ import annotations

import math
from collections import defaultdict

from .exceptions import DocumentNotFoundError, InvalidDocumentError
from .models import Document, SearchResult
from .stemmer import Stemmer, stem_word
from .stopwords import StopWords
from .tokenizer import Tokenizer, tokenize


DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


class FullTextIndex:
    def __init__(
        self,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
        extra_stopwords: set[str] | None = None,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._tokenizer = Tokenizer()
        self._stopwords = StopWords(extra_stopwords)
        self._stemmer = Stemmer()

        self._inverted_index: dict[str, dict[str, list[int]]] = defaultdict(dict)
        self._term_freq: dict[str, dict[str, int]] = defaultdict(dict)
        self._doc_length: dict[str, int] = {}
        self._documents: dict[str, Document] = {}
        self._avg_doc_length: float = 0.0
        self._total_docs: int = 0

    @property
    def k1(self) -> float:
        return self._k1

    @property
    def b(self) -> float:
        return self._b

    @property
    def total_docs(self) -> int:
        return self._total_docs

    @property
    def avg_doc_length(self) -> float:
        return self._avg_doc_length

    @property
    def stopwords(self) -> StopWords:
        return self._stopwords

    def add_document(self, doc: Document) -> None:
        if not doc or not doc.doc_id:
            raise InvalidDocumentError("Document must have a valid doc_id")

        if doc.doc_id in self._documents:
            self._remove_from_index(doc.doc_id)

        processed_content = self._stopwords.preprocess_text(doc.content)
        tokens = tokenize(processed_content)
        filtered_tokens = self._stopwords.filter_tokens(tokens)
        stemmed_tokens = self._stemmer.stem_tokens(filtered_tokens)

        doc_len = len(stemmed_tokens)
        self._documents[doc.doc_id] = doc
        self._doc_length[doc.doc_id] = doc_len

        term_positions: dict[str, list[int]] = defaultdict(list)
        for idx, (term, _) in enumerate(stemmed_tokens):
            term_positions[term].append(idx)

        for term, positions in term_positions.items():
            self._inverted_index[term][doc.doc_id] = positions
            self._term_freq[term][doc.doc_id] = len(positions)

        self._total_docs += 1
        self._update_avg_doc_length()

    def add_documents(self, docs: list[Document]) -> None:
        for doc in docs:
            self.add_document(doc)

    def remove_document(self, doc_id: str) -> None:
        if doc_id not in self._documents:
            raise DocumentNotFoundError(f"Document {doc_id} not found")
        self._remove_from_index(doc_id)

    def _remove_from_index(self, doc_id: str) -> None:
        terms_to_remove = []
        for term, doc_positions in self._inverted_index.items():
            if doc_id in doc_positions:
                del doc_positions[doc_id]
                del self._term_freq[term][doc_id]
                if not doc_positions:
                    terms_to_remove.append(term)

        for term in terms_to_remove:
            del self._inverted_index[term]
            del self._term_freq[term]

        del self._documents[doc_id]
        del self._doc_length[doc_id]
        self._total_docs -= 1
        self._update_avg_doc_length()

    def _update_avg_doc_length(self) -> None:
        if self._total_docs == 0:
            self._avg_doc_length = 0.0
        else:
            total_len = sum(self._doc_length.values())
            self._avg_doc_length = total_len / self._total_docs

    def get_document(self, doc_id: str) -> Document | None:
        return self._documents.get(doc_id)

    def contains_document(self, doc_id: str) -> bool:
        return doc_id in self._documents

    def _process_query(self, query: str) -> list[str]:
        processed_query = self._stopwords.preprocess_text(query)
        tokens = tokenize(processed_query)
        filtered = self._stopwords.filter_tokens(tokens)
        stemmed = self._stemmer.stem_tokens(filtered)
        return [term for term, _ in stemmed]

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        query_terms = self._process_query(query)

        if not query_terms:
            return []

        if self._total_docs == 0:
            return []

        doc_scores: dict[str, float] = defaultdict(float)
        doc_matched_terms: dict[str, set[str]] = defaultdict(set)

        for term in query_terms:
            if term not in self._inverted_index:
                continue

            doc_freq = len(self._inverted_index[term])
            idf = self._compute_idf(doc_freq)

            for doc_id, freq in self._term_freq[term].items():
                score = self._compute_bm25_term_score(
                    term_freq=freq,
                    idf=idf,
                    doc_length=self._doc_length[doc_id],
                )
                doc_scores[doc_id] += score
                doc_matched_terms[doc_id].add(term)

        results: list[SearchResult] = []
        for doc_id, score in doc_scores.items():
            doc = self._documents[doc_id]
            results.append(SearchResult(
                doc_id=doc_id,
                score=score,
                matched_terms=sorted(doc_matched_terms[doc_id]),
                metadata=doc.metadata,
            ))

        results.sort(key=lambda r: r.score, reverse=True)

        if top_k is not None:
            results = results[:top_k]

        return results

    def _compute_idf(self, doc_freq: int) -> float:
        if self._total_docs == 0:
            return 0.0
        return math.log(
            (self._total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0
        )

    def _compute_bm25_term_score(
        self,
        term_freq: int,
        idf: float,
        doc_length: int,
    ) -> float:
        if self._avg_doc_length == 0:
            normalized_len = 1.0
        else:
            normalized_len = doc_length / self._avg_doc_length

        denominator = term_freq + self._k1 * (
            1.0 - self._b + self._b * normalized_len
        )

        if denominator == 0:
            return 0.0

        tf_component = (term_freq * (self._k1 + 1.0)) / denominator
        return idf * tf_component

    def get_term_frequency(self, term: str, doc_id: str) -> int:
        stemmed = stem_word(term.lower())
        if stemmed not in self._term_freq:
            return 0
        return self._term_freq[stemmed].get(doc_id, 0)

    def get_term_positions(self, term: str, doc_id: str) -> list[int]:
        stemmed = stem_word(term.lower())
        if stemmed not in self._inverted_index:
            return []
        return list(self._inverted_index[stemmed].get(doc_id, []))

    def get_document_frequency(self, term: str) -> int:
        stemmed = stem_word(term.lower())
        if stemmed not in self._inverted_index:
            return 0
        return len(self._inverted_index[stemmed])

    def clear(self) -> None:
        self._inverted_index.clear()
        self._term_freq.clear()
        self._doc_length.clear()
        self._documents.clear()
        self._avg_doc_length = 0.0
        self._total_docs = 0
