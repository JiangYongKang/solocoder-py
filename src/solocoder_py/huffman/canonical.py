from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from .exceptions import (
    HuffmanCodeLengthOverflowError,
    HuffmanEmptyFrequencyTableError,
)
from .frequency import validate_frequency_table
from .models import (
    CodeInfo,
    CodeLengthTable,
    CodeTable,
    FrequencyTable,
)


def build_canonical_codes(
    code_lengths: CodeLengthTable,
    freq_table: Optional[dict[Any, int] | FrequencyTable] = None,
) -> CodeTable:
    if not code_lengths or len(code_lengths) == 0:
        raise HuffmanEmptyFrequencyTableError("Code length table is empty")

    lengths_dict = code_lengths.lengths

    if len(lengths_dict) == 1:
        single_symbol = next(iter(lengths_dict.keys()))
        codes: dict[Any, CodeInfo] = {}
        freq = 0
        if freq_table is not None:
            if isinstance(freq_table, FrequencyTable):
                freq = freq_table.frequencies.get(single_symbol, 0)
            else:
                freq = freq_table.get(single_symbol, 0)
        codes[single_symbol] = CodeInfo(
            symbol=single_symbol,
            code_length=1,
            frequency=freq,
            code="0",
        )
        return CodeTable(codes=codes)

    sorted_pairs = sorted(
        lengths_dict.items(),
        key=lambda x: (x[1], _symbol_sort_key(x[0])),
    )

    codes: dict[Any, CodeInfo] = {}
    code_value = 0
    prev_length = sorted_pairs[0][1]

    for i, (symbol, length) in enumerate(sorted_pairs):
        if length <= 0:
            raise HuffmanCodeLengthOverflowError(
                f"Code length for {symbol!r} must be positive, got {length}"
            )

        if i > 0:
            code_value += 1
            if length > prev_length:
                code_value <<= (length - prev_length)

        code_str = format(code_value, f"0{length}b")

        if len(code_str) != length:
            raise HuffmanCodeLengthOverflowError(
                f"Code value overflow: {code_value} cannot fit in {length} bits"
            )

        freq = 0
        if freq_table is not None:
            if isinstance(freq_table, FrequencyTable):
                freq = freq_table.frequencies.get(symbol, 0)
            else:
                freq = freq_table.get(symbol, 0)

        codes[symbol] = CodeInfo(
            symbol=symbol,
            code_length=length,
            frequency=freq,
            code=code_str,
        )

        prev_length = length

    max_length = max(lengths_dict.values())
    max_code_val = (1 << max_length) - 1
    if code_value > max_code_val:
        raise HuffmanCodeLengthOverflowError(
            f"Code values exceed maximum representable with {max_length} bits"
        )

    return CodeTable(codes=codes)


def _symbol_sort_key(symbol: Any) -> tuple:
    try:
        return (0, symbol)
    except TypeError:
        return (1, repr(symbol))


def generate_code_table(
    freq_table: dict[Any, int] | FrequencyTable,
) -> CodeTable:
    from .tree import build_code_lengths

    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    if not freq_dict:
        raise HuffmanEmptyFrequencyTableError("Frequency table is empty")

    validate_frequency_table(freq_dict)

    code_lengths = build_code_lengths(freq_dict)
    return build_canonical_codes(code_lengths, freq_dict)


def verify_prefix_code_property(code_table: CodeTable) -> bool:
    codes_list: list[tuple[str, Any]] = []
    for symbol, info in code_table.items():
        codes_list.append((info.code, symbol))

    codes_list.sort(key=lambda x: len(x[0]))

    for i, (code_i, sym_i) in enumerate(codes_list):
        for j, (code_j, sym_j) in enumerate(codes_list):
            if i == j:
                continue
            if len(code_j) >= len(code_i) and code_j.startswith(code_i):
                return False
    return True


def build_decode_table(code_table: CodeTable) -> dict[str, Any]:
    decode_table: dict[str, Any] = {}
    for symbol, info in code_table.items():
        if info.code in decode_table:
            raise ValueError(f"Duplicate code found: {info.code}")
        decode_table[info.code] = symbol
    return decode_table
