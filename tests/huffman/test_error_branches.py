from __future__ import annotations

import pytest

from solocoder_py.huffman import (
    HuffmanCodeLengthOverflowError,
    HuffmanDecoder,
    HuffmanEmptyFrequencyTableError,
    HuffmanEmptyInputError,
    HuffmanEncoder,
    HuffmanError,
    HuffmanInvalidCodeError,
    HuffmanInvalidFrequencyError,
    HuffmanTruncatedCodeError,
    build_code_lengths,
    build_canonical_codes,
    build_huffman_tree,
    count_frequencies,
    count_frequencies_bytes,
    count_frequencies_text,
    decode,
    encode,
    extract_code_lengths,
    filter_frequency_table,
    generate_code_table,
    validate_frequency_table,
)
from solocoder_py.huffman.models import (
    CodeLengthTable,
    HuffmanNode,
)


class TestEmptyInputError:
    def test_empty_text_frequency_returns_empty(self):
        freq = count_frequencies_text("")
        assert len(freq) == 0

    def test_empty_bytes_frequency_returns_empty(self):
        freq = count_frequencies_bytes(b"")
        assert len(freq) == 0

    def test_empty_iterable_frequency_returns_empty(self):
        freq = count_frequencies([])
        assert len(freq) == 0

    def test_encode_empty_raises(self):
        with pytest.raises(HuffmanEmptyInputError):
            encode([])

    def test_encode_empty_string_raises(self):
        with pytest.raises(HuffmanEmptyInputError):
            encode("")

    def test_encode_none_raises(self):
        with pytest.raises(HuffmanEmptyInputError):
            count_frequencies(None)


class TestEmptyFrequencyTable:
    def test_build_tree_empty_dict_raises(self):
        with pytest.raises(HuffmanEmptyFrequencyTableError):
            build_huffman_tree({})

    def test_build_code_lengths_empty_raises(self):
        with pytest.raises(HuffmanEmptyFrequencyTableError):
            build_code_lengths({})

    def test_generate_code_table_empty_raises(self):
        with pytest.raises(HuffmanEmptyFrequencyTableError):
            generate_code_table({})

    def test_build_canonical_codes_empty_lengths_raises(self):
        with pytest.raises(HuffmanEmptyFrequencyTableError):
            build_canonical_codes(CodeLengthTable(lengths={}))


class TestInvalidFrequency:
    def test_zero_frequency_raises(self):
        with pytest.raises(HuffmanInvalidFrequencyError):
            validate_frequency_table({"A": 0})

    def test_negative_frequency_raises(self):
        with pytest.raises(HuffmanInvalidFrequencyError):
            validate_frequency_table({"A": -1})

    def test_non_integer_frequency_raises(self):
        with pytest.raises(HuffmanInvalidFrequencyError):
            validate_frequency_table({"A": 1.5})

    def test_string_frequency_raises(self):
        with pytest.raises(HuffmanInvalidFrequencyError):
            validate_frequency_table({"A": "5"})

    def test_build_tree_zero_frequency_raises(self):
        with pytest.raises(HuffmanInvalidFrequencyError):
            build_huffman_tree({"A": 0})

    def test_filter_removes_below_min(self):
        freq = {"A": 5, "B": 2, "C": 1, "D": 3}
        filtered = filter_frequency_table(freq, min_frequency=3)
        assert "A" in filtered
        assert "D" in filtered
        assert "B" not in filtered
        assert "C" not in filtered


class TestHuffmanAmbiguitySameFrequency:
    def test_same_frequency_multiple_symbols(self):
        freq = {"A": 5, "B": 5, "C": 5, "D": 5}
        code_table = generate_code_table(freq)
        assert len(code_table) == 4

        from solocoder_py.huffman import verify_prefix_code_property
        assert verify_prefix_code_property(code_table) is True

        codes = [code_table.get_code(s) for s in "ABCD"]
        assert len(set(len(c) for c in codes)) <= 2

    def test_top_two_same_frequency(self):
        freq = {"A": 10, "B": 10, "C": 5, "D": 3, "E": 1}
        code_lengths = build_code_lengths(freq)
        assert len(code_lengths) == 5
        assert code_lengths["A"] <= 2
        assert code_lengths["B"] <= 2
        assert code_lengths["C"] <= code_lengths["E"]
        assert code_lengths["D"] <= code_lengths["E"]

    def test_all_same_frequency_code_continuity(self):
        freq = {str(i): 1 for i in range(4)}
        code_table = generate_code_table(freq)
        from solocoder_py.huffman import verify_prefix_code_property
        assert verify_prefix_code_property(code_table) is True

        codes_by_length: dict[int, list[str]] = {}
        for i in range(4):
            info = code_table[str(i)]
            codes_by_length.setdefault(info.code_length, []).append(info.code)

        for length, codes in codes_by_length.items():
            numeric = sorted(int(c, 2) for c in codes)
            for i in range(len(numeric) - 1):
                assert numeric[i + 1] - numeric[i] == 1


class TestCodeLengthOverflow:
    def test_code_length_extremely_skewed(self):
        freq = {str(i): 2**(20 - i) for i in range(20)}
        freq["20"] = 1
        code_lengths = build_code_lengths(freq)
        assert code_lengths.max_length() <= 20

    def test_extract_lengths_with_small_max(self):
        freq = {"A": 100, "B": 50, "C": 25, "D": 12, "E": 6, "F": 3, "G": 1, "H": 1}
        root = build_huffman_tree(freq)
        with pytest.raises(HuffmanCodeLengthOverflowError):
            extract_code_lengths(root, freq, max_code_length=1)

    def test_code_length_within_default_max(self):
        freq = {str(i): max(1, 1000 - i * 10) for i in range(100)}
        code_lengths = build_code_lengths(freq)
        assert code_lengths.max_length() <= 64


class TestCanonicalCodeLargeSpan:
    def test_mixed_short_and_long_codes(self):
        code_lengths_data = {
            "A": 1,
            "B": 2,
            "C": 5,
            "D": 5,
            "E": 10,
            "F": 10,
        }
        code_lengths = CodeLengthTable(lengths=code_lengths_data)
        code_table = build_canonical_codes(code_lengths)

        assert len(code_table.get_code("A")) == 1
        assert len(code_table.get_code("B")) == 2
        assert len(code_table.get_code("C")) == 5
        assert len(code_table.get_code("D")) == 5
        assert len(code_table.get_code("E")) == 10
        assert len(code_table.get_code("F")) == 10

        from solocoder_py.huffman import verify_prefix_code_property
        assert verify_prefix_code_property(code_table) is True

    def test_extreme_code_length_span(self):
        code_lengths_data = {"S": 1}
        for i in range(10):
            code_lengths_data[f"L{i}"] = 15

        code_lengths = CodeLengthTable(lengths=code_lengths_data)
        code_table = build_canonical_codes(code_lengths)

        from solocoder_py.huffman import verify_prefix_code_property
        assert verify_prefix_code_property(code_table) is True

        for i in range(10):
            assert len(code_table.get_code(f"L{i}")) == 15

        assert len(code_table.get_code("S")) == 1


class TestDecodeErrors:
    def test_decode_invalid_bit_character(self):
        freq = {"A": 1, "B": 1}
        code_table = generate_code_table(freq)
        decoder = HuffmanDecoder(code_table)
        with pytest.raises(HuffmanInvalidCodeError, match="Invalid bit character"):
            decoder.write("01201")

    def test_decode_truncated_code(self):
        freq = {"A": 100, "B": 50, "C": 25, "D": 12, "E": 6, "F": 3, "G": 2, "H": 1}
        code_table = generate_code_table(freq)

        code_lengths_list = [(info.code, info.code_length) for info in code_table.codes.values()]
        code_lengths_list.sort(key=lambda x: x[1])

        longest_code, longest_len = max(code_lengths_list, key=lambda x: x[1])
        truncated_prefix = longest_code[:-1]

        all_valid_codes = set(c for c, _ in code_lengths_list)
        if truncated_prefix in all_valid_codes:
            for code, length in code_lengths_list:
                if length > 1:
                    candidate = code[:-1]
                    if candidate not in all_valid_codes:
                        truncated_prefix = candidate
                        break

        decoder = HuffmanDecoder(code_table)
        decoder.write(truncated_prefix)

        with pytest.raises(HuffmanTruncatedCodeError, match="Truncated bit string"):
            decoder.finish()

    def test_decode_unknown_symbol_during_encode(self):
        freq = {"A": 1, "B": 1}
        encoder = HuffmanEncoder(freq_table=freq)
        encoder.write("C")
        with pytest.raises(HuffmanInvalidCodeError, match="Unknown symbol"):
            encoder.finish()

    def test_decode_length_mismatch(self):
        text = "ABCD"
        encoded = encode(text)
        with pytest.raises(HuffmanTruncatedCodeError, match="does not match"):
            decode(encoded.bit_string, encoded.code_table, expected_length=10)

    def test_decode_invalid_code_sequence(self):
        code_lengths_data = {"A": 1, "B": 2, "C": 3}
        code_lengths = CodeLengthTable(lengths=code_lengths_data)
        code_table = build_canonical_codes(code_lengths, {"A": 4, "B": 2, "C": 1})

        from solocoder_py.huffman import verify_prefix_code_property
        assert verify_prefix_code_property(code_table) is True

        decode_table_set = set(info.code for info in code_table.codes.values())
        max_len = code_table.max_length()

        bad_bits = None
        for length in range(1, max_len + 2):
            if length == 1:
                candidates = ["0", "1"]
            elif length == 2:
                candidates = ["00", "01", "10", "11"]
            else:
                from itertools import product
                candidates = ["".join(t) for t in product("01", repeat=length)]

            for candidate in candidates:
                prefix_is_code = any(
                    candidate[:pl] in decode_table_set
                    for pl in range(1, len(candidate) + 1)
                )
                if not prefix_is_code and len(candidate) > max_len:
                    bad_bits = candidate
                    break
            if bad_bits:
                break

        if bad_bits is None:
            suffix = "0"
            candidate = ""
            for _ in range(max_len + 5):
                candidate += suffix
                prefix_is_code = any(
                    candidate[:pl] in decode_table_set
                    for pl in range(1, len(candidate) + 1)
                )
                if not prefix_is_code and len(candidate) > max_len:
                    bad_bits = candidate
                    break

        assert bad_bits is not None, "Could not construct invalid bit sequence for test"

        decoder = HuffmanDecoder(code_table)
        with pytest.raises(HuffmanInvalidCodeError, match="Code exceeds maximum length"):
            decoder.write(bad_bits)

    def test_encoder_write_after_finish_raises(self):
        encoder = HuffmanEncoder()
        encoder.write("ABC")
        encoder.finish()
        with pytest.raises(RuntimeError, match="already been finished"):
            encoder.write("D")

    def test_decoder_write_after_finish_raises(self):
        freq = {"A": 10, "B": 10, "C": 10, "D": 10, "E": 10, "F": 10}
        encoded = encode("ABCDEF")
        decoder = HuffmanDecoder(encoded.code_table)
        decoder.write(encoded.bit_string)
        decoder.finish()
        with pytest.raises(RuntimeError, match="already been finished"):
            decoder.write("0")

    def test_decoder_init_empty_table_raises(self):
        from solocoder_py.huffman.models import CodeTable
        with pytest.raises(HuffmanEmptyInputError, match="Code table cannot be empty"):
            HuffmanDecoder(CodeTable(codes={}))
