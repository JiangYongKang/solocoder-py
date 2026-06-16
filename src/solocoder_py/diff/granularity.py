from __future__ import annotations

import re
from typing import List, Union

from .exceptions import InvalidGranularityError
from .models import DiffGranularity, DiffToken


def tokenize_lines(text: str) -> List[DiffToken]:
    if not text:
        return []
    lines = text.split("\n")
    return [DiffToken(content=line, index=i) for i, line in enumerate(lines)]


def tokenize_words(text: str) -> List[DiffToken]:
    if not text:
        return []
    pattern = re.compile(r"(\s+|\w+|[^\w\s])", re.UNICODE)
    tokens = pattern.findall(text)
    return [DiffToken(content=t, index=i) for i, t in enumerate(tokens)]


def tokenize_chars(text: str) -> List[DiffToken]:
    if not text:
        return []
    return [DiffToken(content=ch, index=i) for i, ch in enumerate(text)]


def tokenize(text: Union[str, List[str]], granularity: DiffGranularity) -> List[DiffToken]:
    if isinstance(text, list):
        text = "\n".join(text)

    if granularity == DiffGranularity.LINE:
        return tokenize_lines(text)
    elif granularity == DiffGranularity.WORD:
        return tokenize_words(text)
    elif granularity == DiffGranularity.CHAR:
        return tokenize_chars(text)
    else:
        raise InvalidGranularityError(granularity)


def validate_granularity(granularity: str) -> DiffGranularity:
    try:
        return DiffGranularity(granularity)
    except ValueError:
        raise InvalidGranularityError(granularity)
