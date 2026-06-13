from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MatchMode(str, Enum):
    SOUNDEX = "soundex"
    METAPHONE = "metaphone"
    BOTH = "both"


@dataclass(frozen=True)
class PhoneticCode:
    soundex: str
    metaphone: str


@dataclass(frozen=True)
class MatchResult:
    name: str
    soundex_match: bool
    metaphone_match: bool
