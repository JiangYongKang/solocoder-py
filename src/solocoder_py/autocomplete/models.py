from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Candidate:
    word: str
    weight: int

    def __post_init__(self) -> None:
        if self.weight < 0:
            from .exceptions import InvalidWeightError

            raise InvalidWeightError(f"weight must be non-negative, got {self.weight}")
        if not self.word or not self.word.strip():
            from .exceptions import EmptyWordError

            raise EmptyWordError("word cannot be empty or blank")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Candidate):
            return NotImplemented
        return self.word == other.word and self.weight == other.weight

    def __hash__(self) -> int:
        return hash((self.word, self.weight))

    def __lt__(self, other: "Candidate") -> bool:
        if self.weight != other.weight:
            return self.weight > other.weight
        return self.word < other.word

    def __le__(self, other: "Candidate") -> bool:
        return self < other or self == other

    def __gt__(self, other: "Candidate") -> bool:
        return not self <= other

    def __ge__(self, other: "Candidate") -> bool:
        return not self < other


@dataclass
class SearchResult:
    candidate: Candidate
    is_fuzzy: bool = False
    edit_distance: int = 0

    @property
    def word(self) -> str:
        return self.candidate.word

    @property
    def weight(self) -> int:
        return self.candidate.weight


class TrieNode:
    def __init__(self, char: str) -> None:
        self.char: str = char
        self.children: dict[str, TrieNode] = {}
        self.is_end_of_word: bool = False
        self.weight: int = 0
        self.candidates: list[Candidate] = []
        self.max_candidates: int = 0
        self.original_words: set[str] = set()

    def add_candidate(self, word: str, weight: int, original_word: Optional[str] = None) -> None:
        if original_word is None:
            original_word = word
        self.original_words.add(original_word)
        for i, candidate in enumerate(self.candidates):
            if candidate.word == original_word:
                self.candidates.pop(i)
                break
        new_candidate = Candidate(word=original_word, weight=weight)
        inserted = False
        for i, candidate in enumerate(self.candidates):
            if weight > candidate.weight or (
                weight == candidate.weight and original_word < candidate.word
            ):
                self.candidates.insert(i, new_candidate)
                inserted = True
                break
        if not inserted:
            self.candidates.append(new_candidate)

    def update_candidate_weight(self, word: str, new_weight: int, original_word: Optional[str] = None) -> None:
        self.add_candidate(word, new_weight, original_word)

    def remove_candidate(self, word: str, original_word: Optional[str] = None) -> None:
        if original_word is None:
            original_word = word
        self.original_words.discard(original_word)
        self.candidates = [c for c in self.candidates if c.word != original_word]

    def get_top_candidates(self, n: Optional[int] = None) -> list[Candidate]:
        if n is None or n <= 0:
            return list(self.candidates)
        return self.candidates[:n]
