from __future__ import annotations

import threading
from typing import Optional

from .exceptions import EmptyWordError, InvalidWeightError
from .models import Candidate, TrieNode


class TrieAutocomplete:
    def __init__(self) -> None:
        self._root: TrieNode = TrieNode("")
        self._word_weights: dict[str, int] = {}
        self._lock = threading.RLock()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._word_weights)

    def insert(self, word: str, weight: int = 1) -> None:
        if not word:
            raise EmptyWordError("word cannot be empty")
        if weight < 0:
            raise InvalidWeightError(f"weight must be non-negative, got {weight}")

        with self._lock:
            if word in self._word_weights:
                return

            self._word_weights[word] = weight
            self._insert_word(word, weight)

    def _insert_word(self, word: str, weight: int) -> None:
        node = self._root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode(char)
            node = node.children[char]
            node.add_candidate(word, weight)
        node.is_end_of_word = True
        node.weight = weight

    def update_weight(self, word: str, weight: int, *, accumulate: bool = False) -> None:
        if not word:
            raise EmptyWordError("word cannot be empty")
        if weight < 0:
            raise InvalidWeightError(f"weight must be non-negative, got {weight}")

        with self._lock:
            if word not in self._word_weights:
                self.insert(word, weight)
                return

            if accumulate:
                new_weight = self._word_weights[word] + weight
            else:
                new_weight = weight

            self._word_weights[word] = new_weight
            self._update_word_in_trie(word, new_weight)

    def _update_word_in_trie(self, word: str, new_weight: int) -> None:
        node = self._root
        for char in word:
            if char not in node.children:
                break
            node = node.children[char]
            node.update_candidate_weight(word, new_weight)

    def get_weight(self, word: str) -> Optional[int]:
        with self._lock:
            return self._word_weights.get(word)

    def contains(self, word: str) -> bool:
        with self._lock:
            return word in self._word_weights

    def search(self, prefix: str, *, top_n: Optional[int] = None) -> list[Candidate]:
        if prefix is None:
            raise TypeError("prefix cannot be None")

        with self._lock:
            if not prefix:
                return self._get_all_candidates(top_n)

            node = self._root
            for char in prefix:
                if char not in node.children:
                    return []
                node = node.children[char]

            return node.get_top_candidates(top_n)

    def _get_all_candidates(self, top_n: Optional[int]) -> list[Candidate]:
        all_candidates: list[Candidate] = [
            Candidate(word=word, weight=weight)
            for word, weight in self._word_weights.items()
        ]
        all_candidates.sort(key=lambda c: (-c.weight, c.word))
        if top_n is not None and top_n > 0:
            return all_candidates[:top_n]
        return all_candidates

    def delete(self, word: str) -> bool:
        if not word:
            raise EmptyWordError("word cannot be empty")

        with self._lock:
            if word not in self._word_weights:
                return False

            del self._word_weights[word]
            self._delete_word_from_trie(word)
            return True

    def _delete_word_from_trie(self, word: str) -> None:
        node = self._root
        path: list[TrieNode] = [node]
        for char in word:
            if char not in node.children:
                return
            node = node.children[char]
            path.append(node)
            node.remove_candidate(word)

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

    def get_all_words(self) -> list[str]:
        with self._lock:
            return sorted(self._word_weights.keys())
