from __future__ import annotations

import pytest

from solocoder_py.huffman import (
    HuffmanDecoder,
    HuffmanEncoder,
    build_code_lengths,
    build_canonical_codes,
    build_huffman_tree,
    count_frequencies,
    count_frequencies_text,
    decode,
    encode,
    extract_code_lengths,
    generate_code_table,
    verify_prefix_code_property,
)
from solocoder_py.huffman.models import CodeLengthTable


class TestSingleCharacterEdgeCase:
    def test_single_char_frequency(self):
        text = "AAAAA"
        freq = count_frequencies_text(text)
        assert len(freq) == 1
        assert freq["A"] == 5

    def test_single_char_tree_build(self):
        freq = {"A": 10}
        root = build_huffman_tree(freq)
        assert root is not None
        assert root.is_leaf is True
        assert root.symbol == "A"
        assert root.frequency == 10

    def test_single_char_code_length(self):
        freq = {"A": 10}
        code_lengths = build_code_lengths(freq)
        assert code_lengths["A"] == 1

    def test_single_char_canonical_code(self):
        freq = {"A": 10}
        code_table = generate_code_table(freq)
        assert code_table.get_code("A") == "0"
        assert code_table.get_code_length("A") == 1

    def test_single_char_roundtrip(self):
        text = "A" * 100
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text
        assert len(encoded.bit_string) == 100


class TestAllEqualFrequency:
    def test_all_same_frequency_code_length_symmetry(self):
        freq = {"A": 1, "B": 1, "C": 1, "D": 1}
        code_lengths = build_code_lengths(freq)
        lengths = list(code_lengths.lengths.values())

        unique_lengths = set(lengths)
        assert len(unique_lengths) <= 2

        for l in lengths:
            assert 2 <= l <= 3

    def test_all_same_frequency_prefix_property(self):
        freq = {"A": 5, "B": 5, "C": 5, "D": 5, "E": 5, "F": 5}
        code_table = generate_code_table(freq)
        assert verify_prefix_code_property(code_table) is True

    def test_all_same_frequency_roundtrip(self):
        chars = ["A", "B", "C", "D", "E", "F", "G", "H"]
        text = "".join(chars * 10)
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text

    def test_power_of_two_symbols(self):
        freq = {str(i): 1 for i in range(8)}
        code_lengths = build_code_lengths(freq)
        all_three = all(l == 3 for l in code_lengths.lengths.values())
        assert all_three is True


class TestTwoCharacters:
    def test_two_chars_minimal_tree(self):
        freq = {"A": 1, "B": 1}
        root = build_huffman_tree(freq)
        assert root is not None
        assert root.frequency == 2
        assert root.is_leaf is False

    def test_two_chars_code_lengths(self):
        freq = {"A": 1, "B": 1}
        code_lengths = build_code_lengths(freq)
        assert code_lengths["A"] == 1
        assert code_lengths["B"] == 1

    def test_two_chars_canonical_codes(self):
        freq = {"A": 1, "B": 1}
        code_table = generate_code_table(freq)
        codes = {code_table.get_code("A"), code_table.get_code("B")}
        assert codes == {"0", "1"}

    def test_two_chars_roundtrip(self):
        text = "ABABABABABAB"
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text

    def test_two_chars_skewed(self):
        freq = {"A": 100, "B": 1}
        code_lengths = build_code_lengths(freq)
        assert code_lengths["A"] == 1
        assert code_lengths["B"] == 1
        code_table = generate_code_table(freq)
        assert verify_prefix_code_property(code_table) is True


class TestManyCharacters:
    def test_large_alphabet_26_letters(self):
        import string
        text = string.ascii_lowercase * 10
        encoded = encode(text)
        decoded = decode(encoded.bit_string, encoded.code_table, expected_length=len(text))
        assert "".join(decoded) == text

    def test_large_alphabet_prefix_property(self):
        import string
        freq = {c: ord(c) for c in string.printable}
        code_table = generate_code_table(freq)
        assert verify_prefix_code_property(code_table) is True

    def test_256_byte_values(self):
        freq = {i: 256 - i for i in range(256)}
        code_table = generate_code_table(freq)
        assert verify_prefix_code_property(code_table) is True

        data = bytes([i % 256 for i in range(1000)])
        encoder = HuffmanEncoder(freq_table=freq)
        encoder.write(data)
        result = encoder.finish()
        decoded = decode(result.bit_string, result.code_table, expected_length=len(data))
        assert bytes(decoded) == data

    def test_many_symbols_code_lengths_valid(self):
        freq = {str(i): (i + 1) * 10 for i in range(100)}
        code_lengths = build_code_lengths(freq)
        assert len(code_lengths) == 100
        assert code_lengths.max_length() <= 20


class TestEncoderDecoderEdgeCases:
    def test_encoder_multiple_writes(self):
        encoder = HuffmanEncoder()
        encoder.write("ABC")
        encoder.write("DEF")
        encoder.write("GHI")
        result = encoder.finish()
        decoded = decode(result.bit_string, result.code_table, expected_length=9)
        assert "".join(decoded) == "ABCDEFGHI"

    def test_decoder_incremental_decode(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        encoded = encode(text)

        decoder = HuffmanDecoder(encoded.code_table)
        bs = encoded.bit_string
        incremental_results: list[Any] = []
        for i in range(0, len(bs), 3):
            chunk = bs[i : i + 3]
            decoded_chunk = decoder.write(chunk)
            incremental_results.extend(decoded_chunk)
        final_result = decoder.finish(expected_length=len(text))

        assert "".join(incremental_results) == text
        assert "".join(final_result) == text
        assert incremental_results == final_result

    def test_encoder_with_preset_freq_table(self):
        freq = {"A": 5, "B": 3, "C": 2, "D": 1}
        encoder = HuffmanEncoder(freq_table=freq)
        encoder.write("ABCDABCDA")
        result = encoder.finish()
        decoded = decode(result.bit_string, result.code_table, expected_length=9)
        assert "".join(decoded) == "ABCDABCDA"

    def test_reset_encoder(self):
        encoder = HuffmanEncoder()
        encoder.write("AAAAA")
        encoder.finish()
        encoder.reset()
        encoder.write("BBBBB")
        result = encoder.finish()
        decoded = decode(result.bit_string, result.code_table, expected_length=5)
        assert "".join(decoded) == "BBBBB"

    def test_reset_decoder(self):
        encoded1 = encode("AAAAA")

        decoder = HuffmanDecoder(encoded1.code_table)
        decoder.write(encoded1.bit_string)
        result1 = decoder.finish(expected_length=5)
        assert "".join(result1) == "AAAAA"

        decoder.reset()
        assert decoder._buffer == ""
        assert decoder._output == []
        assert decoder._finished is False
        decoder.write(encoded1.bit_string)
        result2 = decoder.finish(expected_length=5)
        assert "".join(result2) == "AAAAA"

        decoder.reset()
        assert decoder._buffer == ""
        assert decoder._output == []
        assert decoder._finished is False
        decoder.write(encoded1.bit_string)
        result3 = decoder.finish(expected_length=5)
        assert "".join(result3) == "AAAAA"

        decoder.reset()
        assert decoder._buffer == ""
        assert decoder._output == []
        assert decoder._finished is False
        decoder.write(encoded1.bit_string)
        result4 = decoder.finish(expected_length=5)
        assert "".join(result4) == "AAAAA"

        assert result1 == result2 == result3 == result4
