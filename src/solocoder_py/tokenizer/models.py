from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ScriptType(Enum):
    UNKNOWN = "unknown"
    LATIN = "latin"
    CYRILLIC = "cyrillic"
    ARABIC = "arabic"
    CJK = "cjk"
    THAI = "thai"
    DEVANAGARI = "devanagari"
    GREEK = "greek"
    HEBREW = "hebrew"
    KATAKANA = "katakana"
    HIRAGANA = "hiragana"
    HANGUL = "hangul"
    PUNCTUATION = "punctuation"
    NUMBER = "number"
    EMOJI = "emoji"
    WHITESPACE = "whitespace"


@dataclass
class Token:
    text: str
    script: ScriptType
    start: int
    end: int
    metadata: dict[str, object] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.text)

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Token(text={self.text!r}, script={self.script.value.upper()}, start={self.start}, end={self.end})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return NotImplemented
        return (
            self.text == other.text
            and self.script == other.script
            and self.start == other.start
            and self.end == other.end
        )

    def __hash__(self) -> int:
        return hash((self.text, self.script, self.start, self.end))


@dataclass
class TokenizationResult:
    tokens: list[Token]
    original_text: str
    detected_scripts: set[ScriptType]
    duration_ms: Optional[float] = None

    def __len__(self) -> int:
        return len(self.tokens)

    def __iter__(self):
        return iter(self.tokens)

    def __getitem__(self, index: int) -> Token:
        return self.tokens[index]

    def to_strings(self) -> list[str]:
        return [token.text for token in self.tokens]
