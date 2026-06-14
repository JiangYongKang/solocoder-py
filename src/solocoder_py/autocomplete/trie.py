from __future__ import annotations

import threading
from typing import Optional

from .exceptions import EmptyWordError, InvalidPrefixError, InvalidWeightError, WordConflictError
from .models import Candidate, SearchResult, TrieNode


def _levenshtein_distance(s1: str, s2: str) -> int:
    len1 = len(s1)
    len2 = len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    if len1 < len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len2 + 1))
    curr_row = [0] * (len2 + 1)

    for i in range(1, len1 + 1):
        curr_row[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,
                prev_row[j] + 1,
                prev_row[j - 1] + cost,
            )
        prev_row, curr_row = curr_row, prev_row

    return prev_row[len2]


class TrieAutocomplete:
    def __init__(
        self,
        *,
        case_sensitive: bool = False,
        fuzzy_threshold: int = 2,
        default_top_n: Optional[int] = None,
    ) -> None:
        self._root: TrieNode = TrieNode("")
        self._word_weights: dict[str, int] = {}
        self._word_originals: dict[str, str] = {}
        self._lock = threading.RLock()
        self._case_sensitive = case_sensitive
        self._fuzzy_threshold = fuzzy_threshold
        self._default_top_n = default_top_n

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._word_weights)

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    @property
    def fuzzy_threshold(self) -> int:
        return self._fuzzy_threshold

    @fuzzy_threshold.setter
    def fuzzy_threshold(self, value: int) -> None:
        if value < 0:
            raise InvalidWeightError(f"fuzzy_threshold must be non-negative, got {value}")
        self._fuzzy_threshold = value

    def _normalize(self, word: str) -> str:
        if self._case_sensitive:
            return word
        return word.lower()

    def insert(self, word: str, weight: int = 1) -> None:
        if not word or not word.strip():
            raise EmptyWordError("word cannot be empty or blank")
        if weight < 0:
            raise InvalidWeightError(f"weight must be non-negative, got {weight}")

        with self._lock:
            normalized = self._normalize(word)
            if normalized in self._word_weights:
                new_weight = self._word_weights[normalized] + weight
                self._word_weights[normalized] = new_weight
                original = self._word_originals[normalized]
                self._update_word_in_trie(normalized, new_weight, original_word=original)
                return

            self._word_weights[normalized] = weight
            self._word_originals[normalized] = word
            self._insert_word(normalized, weight, original_word=word)

    def _insert_word(self, word: str, weight: int, *, original_word: Optional[str] = None) -> None:
        if original_word is None:
            original_word = word
        node = self._root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode(char)
            node = node.children[char]
            node.add_candidate(word, weight, original_word=original_word)
        node.is_end_of_word = True
        node.weight = weight

    def update_weight(self, word: str, weight: int, *, accumulate: bool = False) -> None:
        if not word or not word.strip():
            raise EmptyWordError("word cannot be empty or blank")
        if weight < 0:
            raise InvalidWeightError(f"weight must be non-negative, got {weight}")

        with self._lock:
            normalized = self._normalize(word)
            if normalized not in self._word_weights:
                self._word_weights[normalized] = weight
                self._word_originals[normalized] = word
                self._insert_word(normalized, weight, original_word=word)
                return

            if accumulate:
                new_weight = self._word_weights[normalized] + weight
            else:
                new_weight = weight

            self._word_weights[normalized] = new_weight
            original = self._word_originals[normalized]
            self._update_word_in_trie(normalized, new_weight, original_word=original)

    def _update_word_in_trie(self, word: str, new_weight: int, *, original_word: Optional[str] = None) -> None:
        if original_word is None:
            original_word = word
        node = self._root
        for char in word:
            if char not in node.children:
                break
            node = node.children[char]
            node.update_candidate_weight(word, new_weight, original_word=original_word)

    def get_weight(self, word: str) -> Optional[int]:
        with self._lock:
            normalized = self._normalize(word)
            return self._word_weights.get(normalized)

    def contains(self, word: str) -> bool:
        with self._lock:
            normalized = self._normalize(word)
            return normalized in self._word_weights

    def search(
        self,
        prefix: str,
        *,
        top_n: Optional[int] = None,
        fuzzy: bool = True,
        fuzzy_threshold: Optional[int] = None,
    ) -> list[SearchResult]:
        if prefix is None:
            raise TypeError("prefix cannot be None")

        if top_n is None:
            top_n = self._default_top_n

        if fuzzy_threshold is None:
            fuzzy_threshold = self._fuzzy_threshold

        with self._lock:
            if not prefix:
                results = self._get_all_candidates(top_n)
                return [SearchResult(candidate=c, is_fuzzy=False) for c in results]

            normalized_prefix = self._normalize(prefix)
            exact_matches = self._search_exact(normalized_prefix)

            if exact_matches:
                results = [SearchResult(candidate=c, is_fuzzy=False) for c in exact_matches]
                if top_n is not None and top_n > 0 and len(results) >= top_n:
                    return results[:top_n]
                return results

            if not fuzzy or fuzzy_threshold <= 0:
                return []

            fuzzy_results = self._search_fuzzy(normalized_prefix, fuzzy_threshold)
            if top_n is not None and top_n > 0:
                fuzzy_results = fuzzy_results[:top_n]
            return fuzzy_results

    def _search_exact(self, prefix: str) -> list[Candidate]:
        node = self._root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return list(node.candidates)

    def _search_fuzzy(self, query: str, threshold: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        query_lower = query.lower() if not self._case_sensitive else query

        for normalized, weight in self._word_weights.items():
            word = self._word_originals[normalized]
            word_lower = word.lower() if not self._case_sensitive else word
            distance = _levenshtein_distance(query_lower, word_lower)
            if distance <= threshold and distance > 0:
                results.append(
                    SearchResult(
                        candidate=Candidate(word=word, weight=weight),
                        is_fuzzy=True,
                        edit_distance=distance,
                    )
                )

        results.sort(key=lambda r: (r.edit_distance, -r.weight, r.word))
        return results

    def _get_all_candidates(self, top_n: Optional[int]) -> list[Candidate]:
        all_candidates: list[Candidate] = [
            Candidate(word=self._word_originals[normalized], weight=weight)
            for normalized, weight in self._word_weights.items()
        ]
        all_candidates.sort(key=lambda c: (-c.weight, c.word))
        if top_n is not None and top_n > 0:
            return all_candidates[:top_n]
        return all_candidates

    def delete(self, word: str) -> bool:
        if not word or not word.strip():
            raise EmptyWordError("word cannot be empty or blank")

        with self._lock:
            normalized = self._normalize(word)
            if normalized not in self._word_weights:
                return False

            original = self._word_originals[normalized]
            del self._word_weights[normalized]
            del self._word_originals[normalized]
            self._delete_word_from_trie(normalized, original_word=original)
            return True

    def update_word(self, old_word: str, new_word: str) -> bool:
        if not old_word or not old_word.strip():
            raise EmptyWordError("old_word cannot be empty or blank")
        if not new_word or not new_word.strip():
            raise EmptyWordError("new_word cannot be empty or blank")

        with self._lock:
            old_normalized = self._normalize(old_word)
            new_normalized = self._normalize(new_word)

            if old_normalized not in self._word_weights:
                return False

            if old_normalized == new_normalized:
                old_original = self._word_originals[old_normalized]
                if old_original == new_word:
                    return True
                weight = self._word_weights[old_normalized]
                self._delete_word_from_trie(old_normalized, original_word=old_original)
                self._word_originals[old_normalized] = new_word
                self._insert_word(old_normalized, weight, original_word=new_word)
                return True

            if new_normalized in self._word_weights:
                raise WordConflictError(
                    f"cannot rename '{old_word}' to '{new_word}': "
                    f"'{self._word_originals[new_normalized]}' already exists"
                )

            weight = self._word_weights[old_normalized]
            old_original = self._word_originals[old_normalized]

            del self._word_weights[old_normalized]
            del self._word_originals[old_normalized]
            self._delete_word_from_trie(old_normalized, original_word=old_original)

            self._word_weights[new_normalized] = weight
            self._word_originals[new_normalized] = new_word
            self._insert_word(new_normalized, weight, original_word=new_word)
            return True

    def get_original_word(self, word: str) -> Optional[str]:
        with self._lock:
            normalized = self._normalize(word)
            return self._word_originals.get(normalized)

    def _delete_word_from_trie(self, word: str, *, original_word: Optional[str] = None) -> None:
        if original_word is None:
            original_word = word
        node = self._root
        path: list[TrieNode] = [node]
        for char in word:
            if char not in node.children:
                return
            node = node.children[char]
            path.append(node)
            node.remove_candidate(word, original_word=original_word)

        if path[-1].is_end_of_word:
            path[-1].is_end_of_word = False
            path[-1].weight = 0

        for i in range(len(path) - 1, 0, -1):
            current = path[i]
            if not current.children and not current.is_end_of_word and not current.candidates:
                parent = path[i - 1]
                del parent.children[current.char]
            else:
                break

    def clear(self) -> None:
        with self._lock:
            self._root = TrieNode("")
            self._word_weights.clear()
            self._word_originals.clear()

    def get_all_words(self) -> list[str]:
        with self._lock:
            return sorted(self._word_originals.values())
