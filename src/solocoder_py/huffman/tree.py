from __future__ import annotations

import heapq
from typing import Any, Optional

from .exceptions import (
    HuffmanEmptyFrequencyTableError,
    HuffmanCodeLengthOverflowError,
)
from .frequency import validate_frequency_table
from .models import (
    CodeLengthTable,
    FrequencyTable,
    HuffmanNode,
)

MAX_CODE_LENGTH = 64


def build_huffman_tree(
    freq_table: dict[Any, int] | FrequencyTable,
) -> Optional[HuffmanNode]:
    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    if not freq_dict:
        raise HuffmanEmptyFrequencyTableError("Frequency table is empty")

    validate_frequency_table(freq_dict)

    valid_freqs = {s: f for s, f in freq_dict.items() if f > 0}
    if not valid_freqs:
        raise HuffmanEmptyFrequencyTableError("No symbols with positive frequency")

    if len(valid_freqs) == 1:
        symbol, freq = next(iter(valid_freqs.items()))
        return HuffmanNode(frequency=freq, symbol=symbol, order=0)

    heap: list[HuffmanNode] = []
    order_counter = 0

    for symbol, freq in valid_freqs.items():
        node = HuffmanNode(frequency=freq, symbol=symbol, order=order_counter)
        heapq.heappush(heap, node)
        order_counter += 1

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        merged = HuffmanNode(
            frequency=left.frequency + right.frequency,
            symbol=None,
            left=left,
            right=right,
            order=order_counter,
        )
        order_counter += 1
        heapq.heappush(heap, merged)

    return heap[0] if heap else None


def extract_code_lengths(
    root: Optional[HuffmanNode],
    freq_table: dict[Any, int] | FrequencyTable,
    max_code_length: int = MAX_CODE_LENGTH,
) -> CodeLengthTable:
    if isinstance(freq_table, FrequencyTable):
        freq_dict = freq_table.frequencies
    else:
        freq_dict = freq_table

    if not freq_dict:
        raise HuffmanEmptyFrequencyTableError("Frequency table is empty")

    valid_freqs = {s: f for s, f in freq_dict.items() if f > 0}
    if not valid_freqs:
        raise HuffmanEmptyFrequencyTableError("No symbols with positive frequency")

    lengths: dict[Any, int] = {}

    if root is None:
        raise HuffmanEmptyFrequencyTableError("Huffman tree root is None")

    if len(valid_freqs) == 1:
        single_symbol = next(iter(valid_freqs.keys()))
        lengths[single_symbol] = 1
        return CodeLengthTable(lengths=lengths)

    def _traverse(node: HuffmanNode, depth: int) -> None:
        if node.is_leaf:
            if depth > max_code_length:
                raise HuffmanCodeLengthOverflowError(
                    f"Code length {depth} exceeds maximum allowed {max_code_length}"
                )
            lengths[node.symbol] = depth
            return

        if node.left is not None:
            _traverse(node.left, depth + 1)
        if node.right is not None:
            _traverse(node.right, depth + 1)

    _traverse(root, 0)

    for symbol in valid_freqs.keys():
        if symbol not in lengths:
            raise HuffmanEmptyFrequencyTableError(
                f"Symbol {symbol!r} missing from code length table"
            )

    return CodeLengthTable(lengths=lengths)


def build_code_lengths(
    freq_table: dict[Any, int] | FrequencyTable,
    max_code_length: int = MAX_CODE_LENGTH,
) -> CodeLengthTable:
    root = build_huffman_tree(freq_table)
    return extract_code_lengths(root, freq_table, max_code_length)
