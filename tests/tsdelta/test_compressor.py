import pytest
import struct

from solocoder_py.tsdelta import (
    CorruptedDataError,
    DataLengthMismatchError,
    InvalidSimple8bSelectorError,
    NonMonotonicTimestampError,
    Simple8bOverflowError,
    TruncatedDataError,
    TsDeltaCompressor,
    TsDeltaDecompressor,
    TsDeltaConfig,
    ZigZagOverflowError,
    compress_timestamps,
    decompress_timestamps,
    compute_deltas,
    zigzag_encode_list,
    simple8b_pack,
)
from .conftest import roundtrip


class TestNormalFlow:
    def test_equal_interval_roundtrip(self, roundtrip, equal_interval_timestamps):
        result, compressed, c_stats, d_stats = roundtrip(equal_interval_timestamps)
        assert result == equal_interval_timestamps
        assert c_stats.second_order_count == len(equal_interval_timestamps) - 2

    def test_first_order_deltas_equal_interval(self, equal_interval_timestamps):
        deltas = compute_deltas(equal_interval_timestamps)
        assert deltas.first_delta == 1000
        assert all(d == 1000 for d in deltas.first_order_deltas)
        assert all(d == 0 for d in deltas.second_order_deltas)

    def test_second_order_deltas_zigzag_simple8b_consistency(self, equal_interval_timestamps):
        deltas = compute_deltas(equal_interval_timestamps)
        zigzag_encoded = zigzag_encode_list(deltas.second_order_deltas)
        packed = simple8b_pack(zigzag_encoded)

        from solocoder_py.tsdelta import simple8b_unpack, zigzag_decode_list
        unpacked = simple8b_unpack(packed, expected_count=len(zigzag_encoded))
        decoded = zigzag_decode_list(unpacked)
        assert decoded == deltas.second_order_deltas

    def test_non_equal_interval_roundtrip(self, roundtrip, non_equal_interval_timestamps):
        result, compressed, c_stats, d_stats = roundtrip(non_equal_interval_timestamps)
        assert result == non_equal_interval_timestamps

    def test_non_equal_interval_deltas(self, non_equal_interval_timestamps):
        deltas = compute_deltas(non_equal_interval_timestamps)
        expected_first_order = [1000, 1001, 999, 1002, 998, 1003, 997, 1004, 996, 1005]
        expected_second_order = [1, -2, 3, -4, 5, -6, 7, -8, 9]
        assert deltas.first_order_deltas == expected_first_order
        assert deltas.second_order_deltas == expected_second_order

    def test_multi_block_boundary(self, roundtrip):
        base = 1718841600000
        intervals = [1000 + i % 10 for i in range(200)]
        timestamps = [base]
        current = base
        for interval in intervals:
            current += interval
            timestamps.append(current)

        result, compressed, c_stats, d_stats = roundtrip(timestamps)
        assert result == timestamps
        assert c_stats.simple8b_blocks >= 1

    def test_write_one_by_one(self, make_compressor, make_decompressor):
        base = 1718841600000
        timestamps = [base + i * 1000 for i in range(50)]

        compressor = make_compressor()
        for ts in timestamps:
            compressor.write(ts)
        compressed = compressor.get_compressed_data()
        c_stats = compressor.get_stats()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()
        d_stats = decompressor.get_stats()

        assert result == timestamps
        assert compressor.total_timestamps == 50
        assert c_stats.second_order_count == 48

    def test_context_manager(self):
        base = 1718841600000
        timestamps = [base + i * 1000 for i in range(20)]

        with TsDeltaCompressor() as compressor:
            compressor.write_all(timestamps)
            compressed = compressor.get_compressed_data()

        with TsDeltaDecompressor() as decompressor:
            decompressor.set_input_data(compressed)
            result = decompressor.read_all()

        assert result == timestamps

    def test_compression_stats(self, roundtrip, equal_interval_timestamps):
        result, compressed, c_stats, d_stats = roundtrip(equal_interval_timestamps)
        assert c_stats.original_count == len(equal_interval_timestamps)
        assert c_stats.original_bytes == len(equal_interval_timestamps) * 8
        assert c_stats.compressed_bytes == len(compressed)
        assert c_stats.first_order_count == len(equal_interval_timestamps) - 1
        assert c_stats.second_order_count == len(equal_interval_timestamps) - 2

    def test_large_timestamp_values(self, roundtrip):
        base = 1718841600000000
        timestamps = [base + i * 1000000 for i in range(100)]
        result, compressed, c_stats, d_stats = roundtrip(timestamps)
        assert result == timestamps

    def test_standalone_functions(self, equal_interval_timestamps):
        block = compress_timestamps(equal_interval_timestamps)
        result = decompress_timestamps(block.data)
        assert result == equal_interval_timestamps


class TestBoundaryConditions:
    def test_empty_timestamps(self, roundtrip):
        result, compressed, c_stats, d_stats = roundtrip([])
        assert result == []
        assert c_stats.original_count == 0
        assert c_stats.second_order_count == 0

    def test_single_timestamp(self, roundtrip):
        result, compressed, c_stats, d_stats = roundtrip([1718841600000])
        assert result == [1718841600000]
        assert c_stats.original_count == 1
        assert c_stats.second_order_count == 0

    def test_two_timestamps(self, roundtrip):
        result, compressed, c_stats, d_stats = roundtrip([1000, 2000])
        assert result == [1000, 2000]
        assert c_stats.first_order_count == 1
        assert c_stats.second_order_count == 0

    def test_all_zero_second_order_deltas(self, roundtrip):
        base = 1718841600000
        timestamps = [base + i * 500 for i in range(200)]
        result, compressed, c_stats, d_stats = roundtrip(timestamps)

        deltas = compute_deltas(timestamps)
        assert all(d == 0 for d in deltas.second_order_deltas)
        assert result == timestamps
        assert c_stats.simple8b_blocks == 2

    def test_three_timestamps_one_second_order(self, roundtrip):
        timestamps = [1000, 2000, 3000]
        result, compressed, c_stats, d_stats = roundtrip(timestamps)
        assert result == timestamps
        assert c_stats.second_order_count == 1

    def test_extreme_second_order_deltas(self):
        base = 1718841600000
        large_gap = (1 << 59)
        timestamps = [
            base,
            base + 1000,
            base + 1000 + 1000 + large_gap,
        ]

        with pytest.raises((ZigZagOverflowError, Simple8bOverflowError)):
            compress_timestamps(timestamps)

    def test_max_allowed_second_order_delta(self):
        from solocoder_py.tsdelta import zigzag_encode, simple8b_pack

        max_delta = (1 << 59) - 1
        zigzag_encoded = zigzag_encode(max_delta)
        packed = simple8b_pack([zigzag_encoded])
        assert len(packed) == 8

    def test_very_long_sequence(self, roundtrip):
        base = 1718841600000
        timestamps = [base + i * 1000 for i in range(1000)]
        result, compressed, c_stats, d_stats = roundtrip(timestamps)
        assert result == timestamps
        assert c_stats.simple8b_blocks >= 7

    def test_alternating_intervals(self, roundtrip):
        base = 1718841600000
        intervals = [1000, 1000, 1000, 1000, 10000, 1000, 1000, 1000, 1000]
        timestamps = [base]
        current = base
        for interval in intervals:
            current += interval
            timestamps.append(current)

        result, compressed, c_stats, d_stats = roundtrip(timestamps)
        assert result == timestamps


class TestErrorCases:
    def test_non_monotonic_equal(self):
        with pytest.raises(NonMonotonicTimestampError, match="strictly increasing"):
            compress_timestamps([1000, 1000, 1001])

    def test_non_monotonic_decreasing(self):
        with pytest.raises(NonMonotonicTimestampError, match="strictly increasing"):
            compress_timestamps([3000, 2000, 1000])

    def test_non_monotonic_mixed(self):
        with pytest.raises(NonMonotonicTimestampError, match="strictly increasing"):
            compress_timestamps([1000, 2000, 1500, 3000])

    def test_invalid_selector_during_unpack(self):
        from solocoder_py.tsdelta import unpack_block

        invalid_block = 0x0F
        with pytest.raises(InvalidSimple8bSelectorError):
            unpack_block(invalid_block)

    def test_zigzag_overflow_positive(self):
        from solocoder_py.tsdelta import zigzag_encode, MAX_SIGNED_60BIT

        with pytest.raises(ZigZagOverflowError):
            zigzag_encode(MAX_SIGNED_60BIT + 1)

    def test_zigzag_overflow_negative(self):
        from solocoder_py.tsdelta import zigzag_encode, MIN_SIGNED_60BIT

        with pytest.raises(ZigZagOverflowError):
            zigzag_encode(MIN_SIGNED_60BIT - 1)

    def test_simple8b_overflow(self):
        from solocoder_py.tsdelta import simple8b_pack

        with pytest.raises(Simple8bOverflowError):
            simple8b_pack([1 << 60])

    def test_truncated_header(self, make_decompressor):
        decompressor = make_decompressor()
        truncated = b"\x00" * 10
        decompressor.set_input_data(truncated)
        with pytest.raises(TruncatedDataError):
            decompressor.read_all()

    def test_truncated_simple8b_data(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        base = 1718841600000
        timestamps = [base + i * 1000 for i in range(100)]
        compressor.write_all(timestamps)
        compressed = compressor.get_compressed_data()

        truncated = compressed[:-1]
        decompressor = make_decompressor()
        decompressor.set_input_data(truncated)
        with pytest.raises(TruncatedDataError):
            decompressor.read_all()

    def test_corrupted_data_extra_bytes(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([1000, 2000, 3000])
        compressed = compressor.get_compressed_data()

        corrupted = compressed + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        decompressor = make_decompressor()
        decompressor.set_input_data(corrupted)
        with pytest.raises(CorruptedDataError, match="extra data"):
            decompressor.read_all()

    def test_corrupted_negative_simple8b_length(self):
        header = struct.pack("<q q I I", 1000, 1000, 100, 0xFFFFFFFF)
        decompressor = TsDeltaDecompressor()
        decompressor.set_input_data(header + b"\x00" * 8)
        with pytest.raises(TruncatedDataError):
            decompressor.read_all()

    def test_decompress_without_input(self, make_decompressor):
        decompressor = make_decompressor()
        with pytest.raises(Exception):
            decompressor.read_all()

    def test_non_integer_timestamp(self):
        compressor = TsDeltaCompressor()
        with pytest.raises(Exception):
            compressor.write("not_an_integer")

    def test_config_invalid_max_delta(self):
        with pytest.raises(Exception):
            TsDeltaConfig(max_second_order_delta=-1)

    def test_reset_compressor(self, make_compressor):
        compressor = make_compressor()
        compressor.write_all([1000, 2000, 3000])
        assert compressor.total_timestamps == 3

        compressor.reset()
        assert compressor.total_timestamps == 0

        compressor.write_all([4000, 5000, 6000])
        compressed = compressor.get_compressed_data()
        decompressor = TsDeltaDecompressor()
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()
        assert result == [4000, 5000, 6000]

    def test_reset_decompressor(self, make_compressor, make_decompressor):
        compressor = make_compressor()
        compressor.write_all([1000, 2000, 3000])
        compressed = compressor.get_compressed_data()

        decompressor = make_decompressor()
        decompressor.set_input_data(compressed)
        result1 = decompressor.read_all()
        assert result1 == [1000, 2000, 3000]

        decompressor.reset()
        assert decompressor.value_count == 0

        decompressor.set_input_data(compressed)
        result2 = decompressor.read_all()
        assert result2 == [1000, 2000, 3000]

    def test_invalid_simple8b_data_in_header(self):
        header = struct.pack("<q q I I", 1000, 1000, 10, 5)
        corrupted = header + b"\x00" * 5

        decompressor = TsDeltaDecompressor()
        decompressor.set_input_data(corrupted)
        with pytest.raises(TruncatedDataError):
            decompressor.read_all()
