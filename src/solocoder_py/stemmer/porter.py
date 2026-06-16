from __future__ import annotations

import re
from enum import Enum


_VOWELS = set("aeiou")


class AggressivenessLevel(Enum):
    CONSERVATIVE = "conservative"
    LIGHT = "light"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


class StemmerConfig:
    def __init__(
        self,
        level: AggressivenessLevel = AggressivenessLevel.STANDARD,
        min_stem_length: int = 2,
        preserve_case: bool = True,
    ) -> None:
        self.level = level
        self.min_stem_length = min_stem_length
        self.preserve_case = preserve_case


def _is_consonant(word: str, i: int) -> bool:
    ch = word[i]
    if ch in _VOWELS:
        return False
    if ch == 'y':
        if i == 0:
            return True
        return not _is_consonant(word, i - 1)
    return True


def _measure(word: str) -> int:
    n = 0
    i = 0
    length = len(word)
    while i < length and _is_consonant(word, i):
        i += 1
    while i < length:
        while i < length and not _is_consonant(word, i):
            i += 1
        if i >= length:
            break
        n += 1
        while i < length and _is_consonant(word, i):
            i += 1
    return n


def _contains_vowel(word: str) -> bool:
    for i in range(len(word)):
        if not _is_consonant(word, i):
            return True
    return False


def _ends_double_consonant(word: str) -> bool:
    if len(word) < 2:
        return False
    if word[-1] != word[-2]:
        return False
    return _is_consonant(word, len(word) - 1)


def _cvc(word: str) -> bool:
    length = len(word)
    if length < 3:
        return False
    if not _is_consonant(word, length - 1):
        return False
    if _is_consonant(word, length - 2):
        return False
    if not _is_consonant(word, length - 3):
        return False
    if word[-1] in 'wxy':
        return False
    return True


def _step1a(word: str) -> str:
    if word.endswith('sses'):
        return word[:-2]
    if word.endswith('ies'):
        return word[:-2]
    if word.endswith('ss'):
        return word
    if word.endswith('s'):
        return word[:-1]
    return word


def _step1b(word: str) -> str:
    if word.endswith('eed'):
        stem = word[:-3]
        if _measure(stem) > 0:
            return stem + 'ee'
        return word
    if word.endswith('ed'):
        stem = word[:-2]
        if _contains_vowel(stem):
            return _step1b_helper(stem)
        return word
    if word.endswith('ing'):
        stem = word[:-3]
        if _contains_vowel(stem):
            return _step1b_helper(stem)
        return word
    return word


def _step1b_helper(stem: str) -> str:
    if stem.endswith('at'):
        return stem + 'e'
    if stem.endswith('bl'):
        return stem + 'e'
    if stem.endswith('iz'):
        return stem + 'e'
    if _ends_double_consonant(stem) and not stem.endswith(('l', 's', 'z')):
        return stem[:-1]
    if _measure(stem) == 1 and _cvc(stem):
        return stem + 'e'
    return stem


def _step1c(word: str) -> str:
    if word.endswith('y'):
        stem = word[:-1]
        if _contains_vowel(stem):
            return stem + 'i'
    return word


def _step2(word: str) -> str:
    suffixes = [
        ('ational', 'ate'), ('tional', 'tion'), ('enci', 'ence'),
        ('anci', 'ance'), ('izer', 'ize'), ('abli', 'able'),
        ('alli', 'al'), ('entli', 'ent'), ('eli', 'e'),
        ('ousli', 'ous'), ('ization', 'ize'), ('ation', 'ate'),
        ('ator', 'ate'), ('alism', 'al'), ('iveness', 'ive'),
        ('fulness', 'ful'), ('ousness', 'ous'), ('aliti', 'al'),
        ('iviti', 'ive'), ('biliti', 'ble'),
    ]
    for suffix, replacement in suffixes:
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if _measure(stem) > 0:
                return stem + replacement
            continue
    return word


def _step3(word: str) -> str:
    suffixes = [
        ('icate', 'ic'), ('ative', ''), ('alize', 'al'),
        ('iciti', 'ic'), ('ical', 'ic'), ('ful', ''), ('ness', ''),
    ]
    for suffix, replacement in suffixes:
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if _measure(stem) > 0:
                return stem + replacement
            continue
    return word


def _step4(word: str) -> str:
    suffixes = [
        'al', 'ance', 'ence', 'er', 'ic', 'able', 'ible', 'ant',
        'ement', 'ment', 'ent', 'ion', 'ou', 'ism', 'ate', 'iti',
        'ous', 'ive', 'ize',
    ]
    for suffix in suffixes:
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if suffix == 'ion':
                if not stem.endswith(('s', 't')):
                    continue
            if _measure(stem) > 1:
                return stem
            continue
    return word


def _step5a(word: str) -> str:
    if word.endswith('e'):
        stem = word[:-1]
        if _measure(stem) > 1:
            return stem
        if _measure(stem) == 1 and not _cvc(stem):
            return stem
    return word


def _step5b(word: str) -> str:
    if _measure(word) > 1 and _ends_double_consonant(word) and word.endswith('l'):
        return word[:-1]
    return word


def _is_english(word: str) -> bool:
    return bool(re.match(r'^[a-zA-Z]+$', word))


def _detect_case(word: str) -> str:
    if word.isupper():
        return 'upper'
    if word.istitle():
        return 'title'
    return 'lower'


def _apply_case(word: str, case_style: str) -> str:
    if case_style == 'upper':
        return word.upper()
    if case_style == 'title':
        return word.capitalize()
    return word.lower()


class PorterStemmer:
    def __init__(self, config: StemmerConfig | None = None) -> None:
        self.config = config or StemmerConfig()

    def stem(self, word: str) -> str:
        if not word:
            return word

        if not _is_english(word):
            return word

        case_style = _detect_case(word) if self.config.preserve_case else 'lower'
        word_lower = word.lower()

        if len(word_lower) <= self.config.min_stem_length:
            result = word_lower
        else:
            result = self._apply_steps(word_lower)

        if self.config.preserve_case:
            result = _apply_case(result, case_style)

        return result

    def _apply_steps(self, word: str) -> str:
        level = self.config.level

        if level == AggressivenessLevel.CONSERVATIVE:
            word = _step1a(word)
            word = _step1b(word)
            return word

        if level == AggressivenessLevel.LIGHT:
            word = _step1a(word)
            word = _step1b(word)
            word = _step1c(word)
            word = _step2(word)
            return word

        if level == AggressivenessLevel.STANDARD:
            word = _step1a(word)
            word = _step1b(word)
            word = _step1c(word)
            word = _step2(word)
            word = _step3(word)
            word = _step4(word)
            word = _step5a(word)
            word = _step5b(word)
            return word

        if level == AggressivenessLevel.AGGRESSIVE:
            word = _step1a(word)
            word = _step1b(word)
            word = _step1c(word)
            word = _step2(word)
            word = _step3(word)
            word = _step4(word)
            word = _step5a(word)
            word = _step5b(word)
            word = self._extra_aggressive_step(word)
            return word

        return word

    def _extra_aggressive_step(self, word: str) -> str:
        if len(word) <= 3:
            return word

        extra_suffixes = [
            'able', 'ible', 'al', 'ance', 'ence', 'er', 'ic',
            'ing', 'ed', 'ly', 'ous', 's', 'es',
        ]

        for suffix in extra_suffixes:
            if word.endswith(suffix):
                stem = word[:-len(suffix)]
                if len(stem) >= self.config.min_stem_length and _contains_vowel(stem):
                    word = stem
                    break

        return word


def stem_word(word: str, config: StemmerConfig | None = None) -> str:
    stemmer = PorterStemmer(config)
    return stemmer.stem(word)
