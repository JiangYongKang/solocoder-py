from __future__ import annotations

import math

import pytest

from solocoder_py.huffman import (
    HuffmanDecoder,
    HuffmanEncoder,
    build_code_lengths,
    build_huffman_tree,
    count_frequencies,
    count_frequencies_bytes,
    count_frequencies_text,
    decode,
    encode,
    extract_code_lengths,
    generate_code_table,
    verify_prefix_code_property,
    build_canonical_codes,
)
from solocoder_py.huffman.models import CodeLengthTable


class TestFrequencyStatistics:
    def test_simple_uniform_distribution_text(self):
        text = "AABBCCDDEEFF"
        freq = count_frequencies_text(text)
        assert freq["A"] == 2
        assert freq["B"] == 2
        assert freq["C"] == 2
        assert freq["D"] == 2
        assert freq["E"] == 2
        assert freq["F"] == 2
        assert len(freq) == 6
        assert freq.total() == 12

    def test_skewed_distribution_frequency(self):
        text = "AAAAABBBCCD"
        freq = count_frequencies_text(text)
        assert freq["A"] == 5
        assert freq["B"] == 3
        assert freq["C"] == 2
        assert freq["D"] == 1
        assert len(freq) == 4
        assert freq.total() == 11

    def test_bytes_frequency_count(self):
        data = bytes([0x41, 0x41, 0x42, 0x43, 0x43, 0x43])
        freq = count_frequencies_bytes(data)
        assert freq[0x41] == 2
        assert freq[0x42] == 1
        assert freq[0x43] == 3
        assert len(freq) == 3

    def test_zero_frequency_symbols_excluded(self):
        text = "ABC"
        freq = count_frequencies_text(text)
        assert "D" not in freq
        assert "E" not in freq


class TestHuffmanTreeConstruction:
    def test_skewed_distribution_code_lengths(self):
        freq = {"A": 5, "B": 3, "C": 2, "D": 1}
        code_lengths = build_code_lengths(freq)

        assert code_lengths["A"] <= code_lengths["B"]
        assert code_lengths["B"] <= code_lengths["C"]
        assert code_lengths["C"] <= code_lengths["D"]

        assert sum(freq[s] * code_lengths[s] for s in freq) >= len(freq)

    def test_four_symbols_uniform_code_lengths(self):
        freq = {"A": 1, "B": 1, "C": 1, "D": 1}
        code_lengths = build_code_lengths(freq)
        lengths = set(code_lengths.lengths.values())
        assert all(2 <= l <= 3 for l in lengths)

    def test_tree_build_returns_root(self):
        freq = {"A": 5, "B": 3, "C": 1}
        root = build_huffman_tree(freq)
        assert root is not None
        assert root.frequency == 9

    def test_extract_code_lengths_matches_frequency(self):
        freq = {"A": 10, "B": 5, "C": 3, "D": 2, "E": 1}
        root = build_huffman_tree(freq)
        code_lengths = extract_code_lengths(root, freq)
        assert len(code_lengths) == 5
        for symbol in freq:
            assert symbol in code_lengths


class TestCanonicalCodeGeneration:
    def test_canonical_codes_have_prefix_property(self):
        freq = {"A": 5, "B": 3, "C": 2, "D": 1}
        code_table = generate_code_table(freq)
        assert verify_prefix_code_property(code_table) is True

    def test_same_length_codes_are_contiguous(self):
        freq = {"A": 4, "B": 3, "C": 2, "D": 2, "E": 1, "F": 1}
        code_table = generate_code_table(freq)

        by_length: dict[int, list[tuple[str, object]]] = {}
        for symbol, info in code_table.items():
            by_length.setdefault(info.code_length, []).append((info.code, symbol))

        for length, codes in by_length.items():
            numeric_codes = sorted(int(c, 2) for c, _ in codes)
            for i in range(len(numeric_codes) - 1):
                assert numeric_codes[i + 1] - numeric_codes[i] == 1

    def test_code_length_matches_table(self):
        freq = {"A": 5, "B": 3, "C": 2, "D": 1}
        code_lengths = build_code_lengths(freq)
        code_table = build_canonical_codes(code_lengths, freq)

        for symbol, info in code_table.items():
            assert info.code_length == len(info.code)
            assert info.code_length == code_lengths[symbol]

    def test_shorter_codes_not_prefix_of_longer(self):
        freq = {"A": 10, "B": 5, "C": 3, "D": 2, "E": 1, "F": 1, "G": 1, "H": 1}
        code_table = generate_code_table(freq)
        codes = [(info.code, sym) for sym, info in code_table.items()]
        codes.sort(key=lambda x: len(x[0]))

        for i, (code_i, sym_i) in enumerate(codes):
            for code_j, sym_j in codes[i + 1:]:
                assert not code_j.startswith(code_i), (
                    f"{sym_i} code {code_i} is prefix of {sym_j} code {code_j}"
                )


class TestEncodingDecodingConsistency:
    def test_encode_decode_roundtrip_simple_text(self):
        text = "ABCDEFGH"
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text

    def test_encode_decode_roundtrip_skewed(self):
        text = "AAAAAABBBBBCCCCDDEE"
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text

    def test_encoder_decoder_classes_roundtrip(self):
        text = "The quick brown fox jumps over the lazy dog"
        encoder = HuffmanEncoder()
        encoder.write(text)
        result = encoder.finish()

        decoder = HuffmanDecoder(result.code_table)
        decoder.write(result.bit_string)
        decoded = decoder.finish(expected_length=len(text))
        assert "".join(decoded) == text

    def test_bytes_roundtrip(self):
        data = bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x01, 0x03, 0x03, 0x03, 0x00])
        encoded = encode(data)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(data))
        assert bytes(decoded) == data

    def test_original_length_preserved(self):
        text = "Hello, World!" * 100
        encoded = encode(text)
        assert encoded.original_length == len(text)

    def test_compression_efficiency_skewed(self):
        text = "A" * 1000 + "B" * 500 + "C" * 250 + "D" * 125
        encoded = encode(text)

        original_bits = len(text) * 8
        compressed_bits = len(encoded.bit_string)
        assert compressed_bits < original_bits * 0.5
