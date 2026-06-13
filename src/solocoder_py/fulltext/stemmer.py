from __future__ import annotations

import re


_VOWELS = set("aeiou")


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
            return word
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
            return word
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
            return word
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


def stem_word(word: str) -> str:
    if not word:
        return word
    if not _is_english(word):
        return word

    word = word.lower()

    if len(word) <= 2:
        return word

    word = _step1a(word)
    word = _step1b(word)
    word = _step1c(word)
    word = _step2(word)
    word = _step3(word)
    word = _step4(word)
    word = _step5a(word)
    word = _step5b(word)

    return word


class Stemmer:
    def __init__(self) -> None:
        pass

    def stem(self, word: str) -> str:
        return stem_word(word)

    def stem_terms(self, terms: list[str]) -> list[str]:
        return [stem_word(t) for t in terms]

    def stem_tokens(
        self, tokens: list[tuple[str, int]]
    ) -> list[tuple[str, int]]:
        return [(stem_word(t), pos) for t, pos in tokens]
