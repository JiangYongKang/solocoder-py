from __future__ import annotations

import re


_EN_WORD_PATTERN = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")
_CN_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_PUNCTUATION_PATTERN = re.compile(
    r"[^\w\u4e00-\u9fff\s']", re.UNICODE
)


def tokenize(text: str) -> list[tuple[str, int]]:
    if not text:
        return []

    tokens: list[tuple[str, int]] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch.isspace():
            i += 1
            continue

        if _PUNCTUATION_PATTERN.match(ch):
            i += 1
            continue

        if 'a' <= ch.lower() <= 'z':
            match = _EN_WORD_PATTERN.match(text, i)
            if match:
                word = match.group(0).lower()
                tokens.append((word, i))
                i = match.end()
                continue

        if '\u4e00' <= ch <= '\u9fff':
            tokens.append((ch, i))
            i += 1
            continue

        if ch.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            tokens.append((text[i:j], i))
            i = j
            continue

        i += 1

    return tokens


class Tokenizer:
    def __init__(self) -> None:
        pass

    def tokenize(self, text: str) -> list[tuple[str, int]]:
        return tokenize(text)

    def tokenize_terms(self, text: str) -> list[str]:
        return [term for term, _ in tokenize(text)]
