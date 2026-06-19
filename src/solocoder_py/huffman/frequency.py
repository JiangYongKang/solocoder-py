from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .exceptions import (
    HuffmanEmptyInputError,
    HuffmanEmptyFrequencyTableError,
    HuffmanInvalidFrequencyError,
)
from .models import FrequencyTable


def count_frequencies(data: Iterable[Any]) -> FrequencyTable:
    if data is None:
        raise HuffmanEmptyInputError("Input data cannot be None")

    counter = Counter(data)
    frequencies = {symbol: count for symbol, count in counter.items() if count > 0}

    if not frequencies:
        return FrequencyTable(frequencies={})

    return FrequencyTable(frequencies=frequencies)


def count_frequencies_text(text: str) -> FrequencyTable:
    if text is None:
        raise HuffmanEmptyInputError("Input text cannot be None")
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    return count_frequencies(text)


def count_frequencies_bytes(data: bytes) -> FrequencyTable:
    if data is None:
        raise HuffmanEmptyInputError("Input data cannot be None")
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("Input must be bytes or bytearray")

    return count_frequencies(data)


def validate_frequency_table(
    freq_table: dict[Any, int] | FrequencyTable,
    min_frequency: int = 1,
) -> None:
    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    if freq_dict is None:
        raise HuffmanInvalidFrequencyError("Frequency table cannot be None")

    if not isinstance(freq_dict, dict):
        raise HuffmanInvalidFrequencyError("Frequency table must be a dictionary")

    for symbol, freq in freq_dict.items():
        if not isinstance(freq, int):
            raise HuffmanInvalidFrequencyError(
                f"Frequency for symbol {symbol!r} must be an integer, got {type(freq).__name__}"
            )
        if freq < min_frequency:
            if min_frequency == 1:
                raise HuffmanInvalidFrequencyError(
                    f"Frequency for symbol {symbol!r} must be positive, got {freq}"
                )
            else:
                raise HuffmanInvalidFrequencyError(
                    f"Frequency for symbol {symbol!r} must be >= {min_frequency}, got {freq}"
                )


def prepare_frequency_table(
    freq_table: dict[Any, int] | FrequencyTable,
) -> dict[Any, int]:
    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    if not freq_dict:
        raise HuffmanEmptyFrequencyTableError("Frequency table is empty")

    validate_frequency_table(freq_dict)

    return dict(freq_dict)


def filter_frequency_table(
    freq_table: dict[Any, int] | FrequencyTable,
    min_frequency: int = 1,
) -> FrequencyTable:
    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    validate_frequency_table(freq_dict)

    filtered = {
        symbol: freq
        for symbol, freq in freq_dict.items()
        if freq >= min_frequency
    }

    return FrequencyTable(frequencies=filtered)
