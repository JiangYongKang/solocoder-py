from __future__ import annotations

import re
from typing import Iterable

from .porter import (
    AggressivenessLevel,
    PorterStemmer,
    StemmerConfig,
    _apply_case,
    _detect_case,
)


DEFAULT_EXCEPTIONS: dict[str, str] = {
    "ran": "run",
    "mice": "mouse",
    "mouse": "mouse",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
    "men": "man",
    "women": "woman",
    "children": "child",
    "teeth": "tooth",
    "feet": "foot",
    "geese": "goose",
    "goose": "goose",
    "was": "be",
    "were": "be",
    "been": "be",
    "am": "be",
    "is": "be",
    "are": "be",
    "has": "have",
    "had": "have",
    "does": "do",
    "did": "do",
    "went": "go",
    "goes": "go",
    "gone": "go",
    "said": "say",
    "say": "say",
    "says": "say",
    "saying": "say",
    "got": "get",
    "gotten": "get",
    "made": "make",
    "knew": "know",
    "known": "know",
    "thought": "think",
    "saw": "see",
    "seen": "see",
    "came": "come",
    "took": "take",
    "taken": "take",
}


def _is_english_word(word: str) -> bool:
    return bool(re.match(r'^[a-zA-Z]+$', word))


class Stemmer:
    def __init__(
        self,
        config: StemmerConfig | None = None,
        exceptions: dict[str, str] | None = None,
    ) -> None:
        self.config = config or StemmerConfig()
        self._preserve_case = self.config.preserve_case
        self.config.preserve_case = False
        self._porter = PorterStemmer(self.config)
        self._exceptions: dict[str, str] = {}
        if exceptions is not None:
            for word, stem in exceptions.items():
                self._exceptions[word.lower()] = stem.lower()
        else:
            for word, stem in DEFAULT_EXCEPTIONS.items():
                self._exceptions[word.lower()] = stem.lower()

    def add_exception(self, word: str, stem: str) -> None:
        self._exceptions[word.lower()] = stem.lower()

    def remove_exception(self, word: str) -> bool:
        word_lower = word.lower()
        if word_lower in self._exceptions:
            del self._exceptions[word_lower]
            return True
        return False

    def get_exceptions(self) -> dict[str, str]:
        return dict(self._exceptions)

    def stem(self, word: str) -> str:
        if not word:
            return word

        if not _is_english_word(word):
            return word

        case_style = _detect_case(word) if self._preserve_case else 'lower'
        word_lower = word.lower()

        if word_lower in self._exceptions:
            result = self._exceptions[word_lower]
        else:
            if len(word_lower) <= self.config.min_stem_length:
                result = word_lower
            else:
                result = self._porter.stem(word_lower)
                if len(result) < self.config.min_stem_length:
                    result = word_lower

        if self._preserve_case:
            result = _apply_case(result, case_style)

        return result

    def stem_words(self, words: Iterable[str]) -> list[str]:
        return [self.stem(w) for w in words]

    @property
    def aggressiveness(self) -> AggressivenessLevel:
        return self.config.level

    @aggressiveness.setter
    def aggressiveness(self, level: AggressivenessLevel) -> None:
        self.config.level = level
