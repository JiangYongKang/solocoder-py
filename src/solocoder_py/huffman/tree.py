from __future__ import annotations

import heapq
from typing import Any, Optional

from .exceptions import (
    HuffmanEmptyFrequencyTableError,
    HuffmanCodeLengthOverflowError,
)
from .frequency import prepare_frequency_table
from .models import (
    CodeLengthTable,
    FrequencyTable,
    HuffmanNode,
)

MAX_CODE_LENGTH = 64


def _build_tree_from_clean_freqs(
    valid_freqs: dict[Any, int],
) -> Optional[HuffmanNode]:
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


def build_huffman_tree(
    freq_table: dict[Any, int] | FrequencyTable,
) -> Optional[HuffmanNode]:
    valid_freqs = prepare_frequency_table(freq_table)
    return _build_tree_from_clean_freqs(valid_freqs)


def _extract_lengths_from_tree(
    root: Optional[HuffmanNode],
    valid_freqs: dict[Any, int],
    max_code_length: int,
) -> CodeLengthTable:
    lengths: dict[Any, int] = {}

    if root is None:
        raise HuffmanEmptyFrequencyTableError("Huffman tree root is None")

    if len(valid_freqs) == 1:
        single_symbol = next(iter(valid_freqs.keys()))
        single_length = 1
        if single_length > max_code_length:
            raise HuffmanCodeLengthOverflowError(
                f"Code length {single_length} exceeds maximum allowed {max_code_length}"
            )
        lengths[single_symbol] = single_length
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


def extract_code_lengths(
    root: Optional[HuffmanNode],
    freq_table: dict[Any, int] | FrequencyTable,
    max_code_length: int = MAX_CODE_LENGTH,
) -> CodeLengthTable:
    valid_freqs = prepare_frequency_table(freq_table)
    return _extract_lengths_from_tree(root, valid_freqs, max_code_length)


def build_code_lengths(
    freq_table: dict[Any, int] | FrequencyTable,
    max_code_length: int = MAX_CODE_LENGTH,
) -> CodeLengthTable:
    valid_freqs = prepare_frequency_table(freq_table)
    root = _build_tree_from_clean_freqs(valid_freqs)
    return _extract_lengths_from_tree(root, valid_freqs, max_code_length)
