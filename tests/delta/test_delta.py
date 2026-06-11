import io
import pytest

from solocoder_py.delta import (
    CompressionStats,
    CorruptedDataError,
    DataLengthMismatchError,
    DeltaCompressionError,
    DeltaCompressor,
    DeltaDecompressor,
    DeltaDecompressionError,
    DeltaEncodingConfig,
    InvalidAnchorIntervalError,
    InvalidWidthMarkerError,
    TruncatedDataError,
    ValueOutOfRangeError,
    WidthMarker,
    decode_int,
    determine_width,
    encode_int,
)
from .conftest import roundtrip


class TestWidthMarkerEnum:
    def test_width_marker_values(self):
        assert WidthMarker.WIDTH_1 == 0
        assert WidthMarker.WIDTH_2 == 1
        assert WidthMarker.WIDTH_4 == 2
        assert WidthMarker.WIDTH_8 == 3

    def test_width_marker_is_int(self):
        assert isinstance(WidthMarker.WIDTH_1, int)
        assert WidthMarker.WIDTH_1 + 1 == 1


class TestDetermineWidth:
    def test_width_1_positive(self):
        assert determine_width(0) == WidthMarker.WIDTH_1
        assert determine_width(127) == WidthMarker.WIDTH_1

    def test_width_1_negative(self):
        assert determine_width(-1) == WidthMarker.WIDTH_1
        assert determine_width(-128) == WidthMarker.WIDTH_1

    def test_width_2_positive(self):
        assert determine_width(128) == WidthMarker.WIDTH_2
        assert determine_width(32767) == WidthMarker.WIDTH_2

    def test_width_2_negative(self):
        assert determine_width(-129) == WidthMarker.WIDTH_2
        assert determine_width(-32768) == WidthMarker.WIDTH_2

    def test_width_4_positive(self):
        assert determine_width(32768) == WidthMarker.WIDTH_4
        assert determine_width(2147483647) == WidthMarker.WIDTH_4

    def test_width_4_negative(self):
        assert determine_width(-32769) == WidthMarker.WIDTH_4
        assert determine_width(-2147483648) == WidthMarker.WIDTH_4

    def test_width_8_positive(self):
        assert determine_width(2147483648) == WidthMarker.WIDTH_8
        assert determine_width(9223372036854775807) == WidthMarker.WIDTH_8

    def test_width_8_negative(self):
        assert determine_width(-2147483649) == WidthMarker.WIDTH_8
        assert determine_width(-9223372036854775808) == WidthMarker.WIDTH_8

    def test_unsigned_widths(self):
        assert determine_width(255, signed=False) == WidthMarker.WIDTH_1
        assert determine_width(256, signed=False) == WidthMarker.WIDTH_2
        assert determine_width(65535, signed=False) == WidthMarker.WIDTH_2
        assert determine_width(65536, signed=False) == WidthMarker.WIDTH_4

    def test_unsigned_negative_rejected(self):
        with pytest.raises(ValueOutOfRangeError, match="cannot be negative"):
            determine_width(-1, signed=False)

    def test_out_of_range_signed(self):
        with pytest.raises(ValueOutOfRangeError):
            determine_width(9223372036854775808)

    def test_boundary_values_width_1(self):
        assert determine_width(127) == WidthMarker.WIDTH_1
        assert determine_width(128) == WidthMarker.WIDTH_2
        assert determine_width(-128) == WidthMarker.WIDTH_1
        assert determine_width(-129) == WidthMarker.WIDTH_2

    def test_boundary_values_width_2(self):
        assert determine_width(32767) == WidthMarker.WIDTH_2
        assert determine_width(32768) == WidthMarker.WIDTH_4
        assert determine_width(-32768) == WidthMarker.WIDTH_2
        assert determine_width(-32769) == WidthMarker.WIDTH_4

    def test_boundary_values_width_4(self):
        assert determine_width(2147483647) == WidthMarker.WIDTH_4
        assert determine_width(2147483648) == WidthMarker.WIDTH_8
        assert determine_width(-2147483648) == WidthMarker.WIDTH_4
        assert determine_width(-2147483649) == WidthMarker.WIDTH_8


class TestVarintEncoding:
    def test_encode_width_1_positive(self):
        encoded = encode_int(42)
        assert len(encoded) == 2
        assert encoded[0] >> 6 == WidthMarker.WIDTH_1
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == 42
        assert consumed == 2
        assert is_anchor is False

    def test_encode_width_1_negative(self):
        encoded = encode_int(-42)
        assert len(encoded) == 2
        assert encoded[0] >> 6 == WidthMarker.WIDTH_1
        assert encoded[0] & 0x20 != 0
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == -42
        assert consumed == 2
        assert is_anchor is False

    def test_encode_width_2_positive(self):
        encoded = encode_int(1000)
        assert len(encoded) == 3
        assert encoded[0] >> 6 == WidthMarker.WIDTH_2
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == 1000
        assert consumed == 3
        assert is_anchor is False

    def test_encode_width_2_negative(self):
        encoded = encode_int(-1000)
        assert len(encoded) == 3
        assert encoded[0] >> 6 == WidthMarker.WIDTH_2
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == -1000
        assert consumed == 3
        assert is_anchor is False

    def test_encode_width_4(self):
        encoded = encode_int(100000)
        assert len(encoded) == 5
        assert encoded[0] >> 6 == WidthMarker.WIDTH_4
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == 100000
        assert consumed == 5
        assert is_anchor is False

    def test_encode_width_8(self):
        encoded = encode_int(10000000000)
        assert len(encoded) == 9
        assert encoded[0] >> 6 == WidthMarker.WIDTH_8
        value, consumed, is_anchor = decode_int(encoded, 0)
        assert value == 10000000000
        assert consumed == 9
        assert is_anchor is False

    def test_anchor_flag(self):
        from solocoder_py.delta import encode_anchor, decode_anchor
        encoded = encode_anchor(42)
        assert encoded[0] & 0x10 != 0
        value, consumed, is_anchor = decode_anchor(encoded, 0)
        assert value == 42
        assert is_anchor is True

    def test_roundtrip_boundary_values(self):
        test_values = [
            0, 1, -1, 127, -128, 128, -129,
            32767, -32768, 32768, -32769,
            2147483647, -2147483648, 2147483648, -2147483649,
        ]
        for value in test_values:
            encoded = encode_int(value)
            decoded, consumed, _ = decode_int(encoded, 0)
            assert decoded == value, f"Failed for value {value}"

    def test_decode_with_offset(self):
        buffer = encode_int(100) + encode_int(200) + encode_int(300)
        v1, c1, _ = decode_int(buffer, 0)
        v2, c2, _ = decode_int(buffer, c1)
        v3, c3, _ = decode_int(buffer, c1 + c2)
        assert v1 == 100
        assert v2 == 200
        assert v3 == 300
        assert c1 + c2 + c3 == len(buffer)

    def test_truncated_width_marker(self):
        with pytest.raises(TruncatedDataError, match="cannot read width marker"):
            decode_int(b"", 0)

    def test_truncated_value_bytes(self):
        encoded = encode_int(1000)
        truncated = encoded[:2]
        with pytest.raises(TruncatedDataError, match="expected 2 bytes"):
            decode_int(truncated, 0)

    def test_invalid_width_marker(self):
        invalid_marker = bytes([0xFF])
        with pytest.raises(InvalidWidthMarkerError, match="Invalid width marker"):
            decode_int(invalid_marker, 0)

    def test_sign_bit_in_marker(self):
        encoded = encode_int(-50)
        assert encoded[0] & 0x20 == 0x20
        value, _, _ = decode_int(encoded, 0)
        assert value == -50


class TestDeltaEncodingConfig:
    def test_default_config(self):
        config = DeltaEncodingConfig()
        assert config.anchor_interval == 100
        assert config.max_width == WidthMarker.WIDTH_8
        assert config.signed is True

    def test_custom_config(self):
        config = DeltaEncodingConfig(anchor_interval=10, max_width=WidthMarker.WIDTH_4, signed=False)
        assert config.anchor_interval == 10
        assert config.max_width == WidthMarker.WIDTH_4
        assert config.signed is False

    def test_negative_anchor_interval_rejected(self):
        with pytest.raises(InvalidAnchorIntervalError, match="must be >= 0"):
            DeltaEncodingConfig(anchor_interval=-1)

    def test_value_ranges(self):
        config1 = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_1)
        assert config1.max_value == 127
        assert config1.min_value == -128

        config2 = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_2)
        assert config2.max_value == 32767
        assert config2.min_value == -32768


class TestCompressionStats:
    def test_compression_ratio(self):
        stats = CompressionStats(original_size=100, compressed_size=50, anchor_count=2, total_values=10)
        assert stats.compression_ratio == 0.5

    def test_zero_original_size(self):
        stats = CompressionStats(original_size=0, compressed_size=0, anchor_count=0, total_values=0)
        assert stats.compression_ratio == 0.0


class TestNormalFlows:
    def test_monotonic_increasing_sequence(self, roundtrip):
        values = list(range(100))
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values
        assert c_stats.total_values == 100
        assert c_stats.compression_ratio < 1.0

    def test_fluctuating_sequence(self, roundtrip):
        values = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_anchor_reset_at_interval(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=5)
        values = [100] + [100 + i for i in range(1, 20)]
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 4
        assert d_stats.anchor_count == 4

    def test_different_width_deltas(self, roundtrip):
        values = [
            0,
            1,
            200,
            -300,
            50000,
            -60000,
            1000000,
            -2000000,
            10000000000,
        ]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_small_deltas_compress_well(self, roundtrip):
        values = [1000] * 50
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values
        assert c_stats.compression_ratio < 0.3

    def test_single_value_per_read(self, make_compressor, make_decompressor):
        values = [10, 20, 30, 40, 50]
        compressor = make_compressor()
        compressor.write_all(values)
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)

        results = []
        while decompressor.has_more_data():
            results.append(decompressor.read())

        assert results == values

    def test_write_one_by_one(self, make_compressor, make_decompressor):
        values = [1, 3, 5, 7, 9, 11, 13]
        compressor = make_compressor()
        for v in values:
            compressor.write(v)
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()
        assert result == values

    def test_context_manager(self):
        with DeltaCompressor() as compressor:
            compressor.write_all([1, 2, 3, 4, 5])
            compressed = compressor.get_compressed_data()

        with DeltaDecompressor() as decompressor:
            decompressor.set_input_data(compressed)
            result = decompressor.read_all()

        assert result == [1, 2, 3, 4, 5]

    def test_reset_compressor(self, make_compressor):
        compressor = make_compressor()
        compressor.write_all([1, 2, 3])
        assert compressor.total_values == 3

        compressor.reset()
        assert compressor.total_values == 0
        assert compressor.anchor is None
        assert compressor.get_compressed_data() == b""

    def test_reset_decompressor(self, make_decompressor, make_compressor):
        compressor = make_compressor()
        compressor.write_all([1, 2, 3])
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        decompressor.read()
        assert decompressor.total_values == 1

        decompressor.reset()
        assert decompressor.total_values == 0
        assert decompressor.anchor is None

    def test_has_more_data(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([10, 20])
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        assert decompressor.has_more_data() is True
        decompressor.read()
        assert decompressor.has_more_data() is True
        decompressor.read()
        assert decompressor.has_more_data() is False

    def test_no_anchor_reset_every_value(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=0)
        values = [1, 2, 3, 4, 5]
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 5

    def test_large_anchor_interval(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=1000)
        values = list(range(100))
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 1


class TestEdgeCases:
    def test_empty_stream(self, roundtrip):
        values = []
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == []
        assert compressed == b""
        assert c_stats.total_values == 0
        assert c_stats.anchor_count == 0

    def test_single_data_point(self, roundtrip):
        values = [42]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == [42]
        assert c_stats.anchor_count == 1
        assert c_stats.total_values == 1

    def test_exact_anchor_interval_boundary(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=5)
        values = list(range(10))
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 2

    def test_just_over_anchor_interval(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=5)
        values = list(range(11))
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 3

    def test_all_zero_sequence(self, roundtrip):
        values = [0] * 100
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values
        assert c_stats.compression_ratio < 0.5

    def test_boundary_values_width_1(self, roundtrip):
        values = [0, 127, -128, 127, -128, 0]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_boundary_values_width_2(self, roundtrip):
        values = [0, 32767, -32768, 32767, -32768, 0]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_boundary_values_width_4(self, roundtrip):
        values = [0, 2147483647, -2147483648, 2147483647]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_large_positive_and_negative(self, roundtrip):
        values = [
            9223372036854775807,
            -9223372036854775808,
            9223372036854775807,
            -9223372036854775808,
        ]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_alternating_large_deltas(self, roundtrip):
        values = [0, 1000000, 0, 1000000, 0, 1000000]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values

    def test_read_eof_on_empty(self, make_decompressor):
        decompressor = make_decompressor()
        decompressor.set_input_data(b"")
        with pytest.raises(EOFError):
            decompressor.read()

    def test_custom_output_stream(self):
        output = io.BytesIO()
        compressor = DeltaCompressor(output_stream=output)
        compressor.write_all([1, 2, 3])
        compressed = output.getvalue()
        assert len(compressed) > 0

    def test_custom_input_stream(self, make_compressor):
        compressor = make_compressor()
        compressor.write_all([4, 5, 6])
        compressed = compressor.get_compressed_data()

        input_stream = io.BytesIO(compressed)
        decompressor = DeltaDecompressor(input_stream=input_stream)
        result = decompressor.read_all()
        assert result == [4, 5, 6]


class TestErrorCases:
    def test_truncated_data_during_decode(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([100, 200, 300])
        compressed = compressor.get_compressed_data()
        truncated = compressed[:-1]

        decompressor = make_decompressor()
        decompressor.set_input_data(truncated)
        with pytest.raises(TruncatedDataError):
            decompressor.read_all()

    def test_anchor_interval_zero_special(self, roundtrip):
        config = DeltaEncodingConfig(anchor_interval=0)
        values = [10, 20, 30]
        result, compressed, c_stats, d_stats = roundtrip(values, config)
        assert result == values
        assert c_stats.anchor_count == 3

    def test_value_exceeds_max_range(self, make_compressor):
        config = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_1)
        compressor = make_compressor(config)
        with pytest.raises(ValueOutOfRangeError, match="out of range"):
            compressor.write(200)

    def test_negative_value_unsigned(self, make_compressor):
        config = DeltaEncodingConfig(signed=False)
        compressor = make_compressor(config)
        with pytest.raises(ValueOutOfRangeError):
            compressor.write(-1)

    def test_data_length_mismatch(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([1, 2, 3])
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        with pytest.raises(DataLengthMismatchError, match="Expected 5 values"):
            decompressor.read_all(expected_count=5)

    def test_corrupted_data_invalid_marker(self, make_decompressor):
        corrupted = bytes([0xFF, 0x00, 0x00])
        decompressor = make_decompressor()
        decompressor.set_input_data(corrupted)
        with pytest.raises(CorruptedDataError):
            decompressor.read_all()

    def test_corrupted_data_partial(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([1000, 2000, 3000])
        compressed = compressor.get_compressed_data()

        corrupted = compressed[:5] + bytes([0xFF]) + compressed[5:]
        decompressor = make_decompressor()
        decompressor.set_input_data(corrupted)
        with pytest.raises((CorruptedDataError, TruncatedDataError)):
            decompressor.read_all()

    def test_decoding_without_anchor(self, make_decompressor):
        corrupted_data = encode_int(50, is_anchor=False)
        decompressor = make_decompressor()
        decompressor.set_input_data(corrupted_data)

        with pytest.raises(CorruptedDataError, match="Delta value encountered before anchor"):
            decompressor.read()

    def test_delta_before_anchor_in_mixed_stream(self, make_decompressor):
        from solocoder_py.delta import encode_anchor
        corrupted_data = encode_anchor(100) + encode_int(50, is_anchor=False) + encode_int(30, is_anchor=False)
        decompressor = make_decompressor()
        decompressor.set_input_data(corrupted_data)

        decompressor.read()
        decompressor.read()

        decompressor._anchor = None

        with pytest.raises(CorruptedDataError, match="Delta value encountered before anchor"):
            decompressor.read()

    def test_config_mismatch_anchor_interval_still_works(self, make_compressor, make_decompressor):
        large_value_1 = 1000000000000
        large_value_2 = 2000000000000
        values = [large_value_1] + [large_value_1 + i for i in range(1, 5)] + [large_value_2] + [large_value_2 + i for i in range(1, 5)]

        compressor = make_compressor(DeltaEncodingConfig(anchor_interval=5))
        compressor.write_all(values)
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor(DeltaEncodingConfig(anchor_interval=10))
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()
        assert result == values

    def test_anchor_flag_detection(self, make_compressor, make_decompressor):
        values = [100, 101, 102, 200, 201, 202]
        config = DeltaEncodingConfig(anchor_interval=3)
        compressor = make_compressor(config)
        compressor.write_all(values)
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor(config)
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()

        assert result == values
        assert decompressor.anchor_count == 2

    def test_out_of_range_large_value(self, make_compressor):
        config = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_2)
        compressor = make_compressor(config)
        with pytest.raises(ValueOutOfRangeError):
            compressor.write(100000)

    def test_out_of_range_large_negative(self, make_compressor):
        config = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_2)
        compressor = make_compressor(config)
        with pytest.raises(ValueOutOfRangeError):
            compressor.write(-100000)

    def test_delta_compression_error_base(self):
        assert issubclass(DeltaDecompressionError, DeltaCompressionError)
        assert issubclass(TruncatedDataError, DeltaDecompressionError)
        assert issubclass(CorruptedDataError, DeltaDecompressionError)


class TestCompressionEfficiency:
    def test_similar_values_compress_well(self, roundtrip):
        values = [1000 + i for i in range(100)]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values
        assert c_stats.compression_ratio < 0.5

    def test_random_large_values_compress_poorly(self, roundtrip):
        values = [i * 1000000 for i in range(100)]
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert result == values
        assert c_stats.compression_ratio < 1.0

    def test_stats_match_between_compressor_and_decompressor(self, roundtrip):
        values = list(range(50))
        result, compressed, c_stats, d_stats = roundtrip(values)
        assert c_stats.total_values == d_stats.total_values
        assert c_stats.anchor_count == d_stats.anchor_count
        assert c_stats.compressed_size == d_stats.compressed_size
