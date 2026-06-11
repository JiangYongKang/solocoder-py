from __future__ import annotations

import pytest

from solocoder_py.rle import (
    RLETruncatedDataError,
    RLEInvalidCountError,
    RLEInvalidLengthError,
    RLEOutputLengthMismatchError,
    ESC_BYTE,
    TYPE_RUN,
    TYPE_LITERAL,
    TYPE_ESC_ESCAPE,
    encode,
    decode,
    RLEEncoder,
    RLEDecoder,
)


class TestEncodeNormalFlows:
    def test_contiguous_same_bytes_compress(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        assert len(encoded) < len(data)
        assert encoded[0] == ESC_BYTE
        assert encoded[1] == TYPE_RUN
        assert encoded[2] == 10
        assert encoded[3] == 0x41

    def test_literal_block_passthrough(self):
        data = bytes([0x01, 0x02, 0x03, 0x04, 0x05])
        encoded = encode(data)
        assert encoded[0] == ESC_BYTE
        assert encoded[1] == TYPE_LITERAL
        assert encoded[2] == 5
        assert encoded[3:8] == data

    def test_mixed_data_roundtrip(self):
        data = bytes([0x41] * 5 + [0x42, 0x43, 0x44] + [0x45] * 8 + [0x46])
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data

    def test_long_run_split(self):
        data = bytes([0x5A] * 300)
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data
        assert len(encoded) < len(data)


class TestEncodeBoundaryConditions:
    def test_empty_data(self):
        assert encode(b"") == b""

    def test_all_same_bytes_max_compression(self):
        data = bytes([0xFF] * 100)
        encoded = encode(data)
        assert len(encoded) == 4
        decoded = decode(encoded)
        assert decoded == data

    def test_all_different_bytes_passthrough(self):
        data = bytes(range(255))
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data

    def test_single_byte_no_compression(self):
        data = bytes([0x42])
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data

    def test_two_same_bytes_no_compression(self):
        data = bytes([0x42, 0x42])
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data

    def test_escape_byte_in_data(self):
        data = bytes([ESC_BYTE])
        encoded = encode(data)
        assert encoded == bytes([ESC_BYTE, TYPE_ESC_ESCAPE])
        decoded = decode(encoded)
        assert decoded == data

    def test_escape_byte_in_mixed_data(self):
        data = bytes([0x41, ESC_BYTE, 0x42, 0x42, 0x42])
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data

    def test_exactly_min_run_length(self):
        data = bytes([0x41] * 3)
        encoded = encode(data)
        assert encoded[0] == ESC_BYTE
        assert encoded[1] == TYPE_RUN
        assert encoded[2] == 3
        assert encoded[3] == 0x41
        decoded = decode(encoded)
        assert decoded == data


class TestDecodeNormalFlows:
    def test_run_decode(self):
        encoded = bytes([ESC_BYTE, TYPE_RUN, 10, 0x41])
        decoded = decode(encoded)
        assert decoded == bytes([0x41] * 10)

    def test_literal_decode(self):
        encoded = bytes([ESC_BYTE, TYPE_LITERAL, 5, 0x01, 0x02, 0x03, 0x04, 0x05])
        decoded = decode(encoded)
        assert decoded == bytes([0x01, 0x02, 0x03, 0x04, 0x05])

    def test_escape_escape_decode(self):
        encoded = bytes([ESC_BYTE, TYPE_ESC_ESCAPE])
        decoded = decode(encoded)
        assert decoded == bytes([ESC_BYTE])

    def test_mixed_sequence_decode(self):
        encoded = (
            bytes([ESC_BYTE, TYPE_RUN, 5, 0x41])
            + bytes([ESC_BYTE, TYPE_LITERAL, 3, 0x42, 0x43, 0x44])
            + bytes([ESC_BYTE, TYPE_ESC_ESCAPE])
        )
        decoded = decode(encoded)
        expected = bytes([0x41] * 5) + bytes([0x42, 0x43, 0x44]) + bytes([ESC_BYTE])
        assert decoded == expected


class TestDecodeBoundaryConditions:
    def test_empty_data_decode(self):
        assert decode(b"") == b""

    def test_max_count_run(self):
        encoded = bytes([ESC_BYTE, TYPE_RUN, 255, 0x5A])
        decoded = decode(encoded)
        assert len(decoded) == 255
        assert all(b == 0x5A for b in decoded)

    def test_max_literal_length(self):
        literal_data = bytes(range(255))
        encoded = bytes([ESC_BYTE, TYPE_LITERAL, 255]) + literal_data
        decoded = decode(encoded)
        assert decoded == literal_data

    def test_expected_length_correct(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        decoded = decode(encoded, expected_length=10)
        assert decoded == data


class TestDecodeErrorCases:
    def test_truncated_escape_only(self):
        with pytest.raises(RLETruncatedDataError, match="missing type byte"):
            decode(bytes([ESC_BYTE]))

    def test_truncated_run_missing_count(self):
        with pytest.raises(RLETruncatedDataError, match="missing count byte"):
            decode(bytes([ESC_BYTE, TYPE_RUN]))

    def test_truncated_run_missing_value(self):
        with pytest.raises(RLETruncatedDataError, match="missing value byte"):
            decode(bytes([ESC_BYTE, TYPE_RUN, 10]))

    def test_invalid_run_count_too_small(self):
        with pytest.raises(RLEInvalidCountError, match="must be >="):
            decode(bytes([ESC_BYTE, TYPE_RUN, 2, 0x41]))

    def test_invalid_run_count_zero(self):
        with pytest.raises(RLEInvalidCountError):
            decode(bytes([ESC_BYTE, TYPE_RUN, 0, 0x41]))

    def test_truncated_literal_missing_length(self):
        with pytest.raises(RLETruncatedDataError, match="missing length byte"):
            decode(bytes([ESC_BYTE, TYPE_LITERAL]))

    def test_literal_length_zero(self):
        with pytest.raises(RLEInvalidLengthError, match="cannot be zero"):
            decode(bytes([ESC_BYTE, TYPE_LITERAL, 0]))

    def test_literal_length_exceeds_data(self):
        with pytest.raises(RLETruncatedDataError, match="exceeds remaining data"):
            decode(bytes([ESC_BYTE, TYPE_LITERAL, 10, 0x01, 0x02]))

    def test_unknown_sequence_type(self):
        with pytest.raises(RLETruncatedDataError, match="Unknown escape sequence type"):
            decode(bytes([ESC_BYTE, 0xFF]))

    def test_expected_length_mismatch(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        with pytest.raises(RLEOutputLengthMismatchError, match="does not match"):
            decode(encoded, expected_length=15)

    def test_non_escape_start_byte(self):
        with pytest.raises(RLETruncatedDataError, match="Expected escape byte"):
            decode(bytes([0x42]))

    def test_malicious_short_data(self):
        test_cases = [
            b"\x1B",
            b"\x1B\x01",
            b"\x1B\x01\x05",
            b"\x1B\x02",
            b"\x1B\x02\xFF",
            b"\x1B\xFF",
        ]
        for case in test_cases:
            with pytest.raises((RLETruncatedDataError, RLEInvalidCountError, RLEInvalidLengthError)):
                decode(case)


class TestRoundtripVarious:
    def test_random_mixed_patterns(self):
        patterns = [
            bytes([0x00] * 100),
            bytes(range(200)),
            bytes([0x55] * 5 + [0xAA] * 5) * 20,
            bytes([ESC_BYTE] * 5),
            bytes([ESC_BYTE, 0x01, ESC_BYTE, ESC_BYTE, 0x02]),
            bytes([i % 3 for i in range(100)]),
        ]
        for pattern in patterns:
            encoded = encode(pattern)
            decoded = decode(encoded)
            assert decoded == pattern

    def test_very_long_run(self):
        data = bytes([0x42] * 10000)
        encoded = encode(data)
        assert len(encoded) < len(data) // 10
        decoded = decode(encoded)
        assert decoded == data

    def test_alternating_short_long_runs(self):
        data = bytearray()
        for i in range(10):
            data.extend(bytes([i]) * (2 + i * 3))
        data = bytes(data)
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded == data


class TestRLEEncoder:
    def test_encode_single_write(self):
        encoder = RLEEncoder()
        encoder.write(bytes([0x41] * 10))
        result = encoder.finish()
        assert decode(result) == bytes([0x41] * 10)

    def test_encode_multiple_writes(self):
        encoder = RLEEncoder()
        encoder.write(bytes([0x41] * 5))
        encoder.write(bytes([0x41] * 5))
        result = encoder.finish()
        assert decode(result) == bytes([0x41] * 10)

    def test_encode_literal_multiple_writes(self):
        encoder = RLEEncoder()
        encoder.write(b"Hello ")
        encoder.write(b"World")
        result = encoder.finish()
        assert decode(result) == b"Hello World"

    def test_encode_reset(self):
        encoder = RLEEncoder()
        encoder.write(bytes([0x41] * 10))
        encoder.finish()
        encoder.reset()
        encoder.write(bytes([0x42] * 5))
        result = encoder.finish()
        assert decode(result) == bytes([0x42] * 5)

    def test_encode_finish_twice(self):
        encoder = RLEEncoder()
        encoder.write(b"test")
        r1 = encoder.finish()
        r2 = encoder.finish()
        assert r1 == r2

    def test_encode_write_after_finish_raises(self):
        encoder = RLEEncoder()
        encoder.finish()
        with pytest.raises(RuntimeError, match="already been finished"):
            encoder.write(b"test")


class TestRLEDecoder:
    def test_decode_single_write(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        decoder = RLEDecoder()
        result = decoder.write(encoded)
        decoder.finish()
        assert result == data

    def test_decode_incremental(self):
        data = bytes([0x41] * 100)
        encoded = encode(data)
        decoder = RLEDecoder()
        output = bytearray()
        for i in range(0, len(encoded), 2):
            chunk = encoded[i : i + 2]
            output.extend(decoder.write(chunk))
        decoder.finish()
        assert bytes(output) == data

    def test_decode_literal_incremental(self):
        data = bytes(range(100))
        encoded = encode(data)
        decoder = RLEDecoder()
        output = bytearray()
        for i in range(0, len(encoded), 3):
            chunk = encoded[i : i + 3]
            output.extend(decoder.write(chunk))
        decoder.finish()
        assert bytes(output) == data

    def test_decode_reset(self):
        decoder = RLEDecoder()
        encoded1 = encode(bytes([0x41] * 10))
        decoder.write(encoded1)
        decoder.finish()
        decoder.reset()
        encoded2 = encode(bytes([0x42] * 5))
        result = decoder.write(encoded2)
        decoder.finish()
        assert result == bytes([0x42] * 5)

    def test_decode_finish_with_remaining_buffer_raises(self):
        decoder = RLEDecoder()
        decoder.write(bytes([ESC_BYTE, TYPE_RUN]))
        with pytest.raises(RLETruncatedDataError, match="Truncated data"):
            decoder.finish()

    def test_decode_expected_length_correct(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        decoder = RLEDecoder()
        decoder.write(encoded)
        result = decoder.finish(expected_length=10)
        assert result == data

    def test_decode_expected_length_mismatch(self):
        data = bytes([0x41] * 10)
        encoded = encode(data)
        decoder = RLEDecoder()
        decoder.write(encoded)
        with pytest.raises(RLEOutputLengthMismatchError):
            decoder.finish(expected_length=15)

    def test_decode_write_after_finish_raises(self):
        decoder = RLEDecoder()
        decoder.finish()
        with pytest.raises(RuntimeError, match="already been finished"):
            decoder.write(b"test")
