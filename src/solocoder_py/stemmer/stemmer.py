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
    "runs": "run",
    "running": "run",
    "mice": "mouse",
    "mouse": "mouse",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
    "men": "man",
    "man": "man",
    "women": "woman",
    "woman": "woman",
    "children": "child",
    "child": "child",
    "teeth": "tooth",
    "tooth": "tooth",
    "feet": "foot",
    "foot": "foot",
    "geese": "goose",
    "goose": "goose",
    "was": "be",
    "were": "be",
    "be": "be",
    "been": "be",
    "being": "be",
    "am": "be",
    "is": "be",
    "are": "be",
    "have": "have",
    "has": "have",
    "had": "have",
    "having": "have",
    "do": "do",
    "does": "do",
    "did": "do",
    "doing": "do",
    "go": "go",
    "goes": "go",
    "went": "go",
    "gone": "go",
    "going": "go",
    "say": "say",
    "says": "say",
    "said": "say",
    "saying": "say",
    "get": "get",
    "gets": "get",
    "got": "get",
    "gotten": "get",
    "getting": "get",
    "make": "make",
    "makes": "make",
    "made": "make",
    "making": "make",
    "know": "know",
    "knows": "know",
    "knew": "know",
    "known": "know",
    "knowing": "know",
    "think": "think",
    "thinks": "think",
    "thought": "think",
    "thinking": "think",
    "see": "see",
    "sees": "see",
    "saw": "see",
    "seen": "see",
    "seeing": "see",
    "come": "come",
    "comes": "come",
    "came": "come",
    "coming": "come",
    "take": "take",
    "takes": "take",
    "took": "take",
    "taken": "take",
    "taking": "take",
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
        porter_config = StemmerConfig(
            level=self.config.level,
            min_stem_length=self.config.min_stem_length,
            preserve_case=False,
        )
        self._porter = PorterStemmer(porter_config)
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

        case_style = _detect_case(word) if self.config.preserve_case else 'lower'
        word_lower = word.lower()

        result = None
        if word_lower in self._exceptions:
            exception_result = self._exceptions[word_lower]
            if len(exception_result) >= self.config.min_stem_length:
                result = exception_result

        if result is None:
            if len(word_lower) <= self.config.min_stem_length:
                result = word_lower
            else:
                result = self._porter.stem(word_lower)
                if len(result) < self.config.min_stem_length:
                    result = word_lower

        if self.config.preserve_case:
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
        self._porter.config.level = level
