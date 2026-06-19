import pytest

from solocoder_py.lz77 import (
    LZ77Compressor,
    LZ77Decompressor,
    LZ77Config,
    CorruptedDataError,
    TruncatedDataError,
    DistanceOutOfRangeError,
    LengthOutOfRangeError,
    ValueOutOfRangeError,
)


class TestErrorBranches:
    def test_truncated_data_only_flag(self, make_decompressor):
        decompressor = make_decompressor()
        with pytest.raises(TruncatedDataError):
            decompressor.decompress(b"\x05")

    def test_truncated_literal_block(self, make_decompressor):
        truncated = b"\x05abc"
        decompressor = make_decompressor()
        with pytest.raises(TruncatedDataError, match="Truncated literal block"):
            decompressor.decompress(truncated)

    def test_truncated_match_pair(self, make_decompressor):
        truncated = b"\x80\x00\x00"
        decompressor = make_decompressor()
        with pytest.raises(TruncatedDataError, match="Truncated match pair"):
            decompressor.decompress(truncated)

    def test_distance_zero(self, make_decompressor):
        decompressor = make_decompressor()
        decompressor._output_buffer = bytearray(b"hello world")
        flag_byte = 0x80
        decompressor._input_data = bytes([flag_byte, 0x05, 0x00, 0x00])
        decompressor._input_pos = 1
        with pytest.raises(DistanceOutOfRangeError, match="Invalid distance"):
            decompressor._process_match_pair(flag_byte)

    def test_distance_exceeds_output(self, make_decompressor):
        decompressor = make_decompressor()
        decompressor._output_buffer = bytearray(b"abc")
        flag_byte = 0x80
        decompressor._input_data = bytes([flag_byte, 0x05, 0x00, 0x10])
        decompressor._input_pos = 1
        with pytest.raises(DistanceOutOfRangeError, match="exceeds current output size"):
            decompressor._process_match_pair(flag_byte)

    def test_distance_exceeds_window_size(self, make_decompressor, default_config):
        decompressor = make_decompressor()
        large_data = b"X" * (default_config.window_size + 10)
        decompressor._output_buffer = bytearray(large_data)
        distance = default_config.window_size + 5
        flag_byte = 0x80
        decompressor._input_data = bytes([flag_byte, 0x05, (distance >> 8) & 0xFF, distance & 0xFF])
        decompressor._input_pos = 1
        with pytest.raises(DistanceOutOfRangeError, match="exceeds window size"):
            decompressor._process_match_pair(flag_byte)

    def test_length_exceeds_max(self, make_decompressor):
        from solocoder_py.lz77 import LZ77Config
        config = LZ77Config(min_match_length=3, max_match_length=100)
        decompressor = make_decompressor(config)
        decompressor._output_buffer = bytearray(b"hello world test data more bytes here")
        length_offset = 255
        flag_byte = 0x80
        decompressor._input_data = bytes([flag_byte, length_offset, 0x00, 0x05])
        decompressor._input_pos = 1
        with pytest.raises(LengthOutOfRangeError):
            decompressor._process_match_pair(flag_byte)

    def test_corrupted_control_marker_zero_distance(self, make_decompressor):
        decompressor = make_decompressor()
        decompressor._output_buffer = bytearray(b"test data")
        flag_byte = 0x80
        decompressor._input_data = bytes([flag_byte, 0x05, 0x00, 0x00])
        decompressor._input_pos = 1
        with pytest.raises(DistanceOutOfRangeError, match="Invalid distance"):
            decompressor._process_match_pair(flag_byte)

    def test_corrupted_control_marker_length_overflow(self, make_decompressor):
        from solocoder_py.lz77 import LZ77Config
        config = LZ77Config(min_match_length=3, max_match_length=100)
        decompressor = make_decompressor(config)
        decompressor._output_buffer = bytearray(b"test data more content here to make it long enough")
        flag_byte = 0x80
        bad_length_offset = 255
        decompressor._input_data = bytes([flag_byte, bad_length_offset, 0x00, 0x05])
        decompressor._input_pos = 1
        with pytest.raises(LengthOutOfRangeError):
            decompressor._process_match_pair(flag_byte)

    def test_value_out_of_range_distance_compression(self, make_compressor):
        compressor = make_compressor()
        with pytest.raises(ValueOutOfRangeError, match="Distance"):
            compressor._write_match_pair(0, 5)

    def test_value_out_of_range_distance_too_large(self, make_compressor, default_config):
        compressor = make_compressor()
        with pytest.raises(ValueOutOfRangeError, match="Distance"):
            compressor._write_match_pair(default_config.window_size + 1, 5)

    def test_value_out_of_range_length_too_small(self, make_compressor, default_config):
        compressor = make_compressor()
        with pytest.raises(ValueOutOfRangeError, match="Length"):
            compressor._write_match_pair(10, default_config.min_match_length - 1)

    def test_value_out_of_range_length_too_large(self, make_compressor, default_config):
        compressor = make_compressor()
        with pytest.raises(ValueOutOfRangeError, match="Length"):
            compressor._write_match_pair(10, default_config.max_match_length + 1)

    def test_value_out_of_range_literal_block_size(self, make_compressor, default_config):
        compressor = make_compressor()
        too_big = b"X" * (default_config.literal_block_max + 1)
        with pytest.raises(ValueOutOfRangeError, match="Literal block length"):
            compressor._write_literal_block(too_big)

    def test_compressor_value_errors_base_class(self):
        from solocoder_py.lz77 import LZ77CompressionError
        assert issubclass(ValueOutOfRangeError, LZ77CompressionError)

    def test_decompressor_errors_base_class(self):
        from solocoder_py.lz77 import LZ77DecompressionError
        assert issubclass(CorruptedDataError, LZ77DecompressionError)
        assert issubclass(TruncatedDataError, LZ77DecompressionError)
        assert issubclass(DistanceOutOfRangeError, LZ77DecompressionError)
        assert issubclass(LengthOutOfRangeError, LZ77DecompressionError)

    def test_lz77_error_hierarchy(self):
        from solocoder_py.lz77 import LZ77Error, LZ77CompressionError, LZ77DecompressionError
        assert issubclass(LZ77CompressionError, LZ77Error)
        assert issubclass(LZ77DecompressionError, LZ77Error)

    def test_empty_input_returns_empty(self, make_decompressor):
        decompressor = make_decompressor()
        result = decompressor.decompress(b"")
        assert result == b""
        assert decompressor.total_output == 0

    def test_mixed_corrupted_after_good_data(self, make_compressor, make_decompressor, default_config):
        compressor = make_compressor()
        good_data = b"hello"
        compressed = compressor.compress(good_data)
        corrupted = compressed + b"\x80\x00\xFF\xFF"
        decompressor = make_decompressor()
        with pytest.raises(DistanceOutOfRangeError):
            decompressor.decompress(corrupted)

    def test_literal_block_single_byte(self, make_decompressor):
        decompressor = make_decompressor()
        literal_flag = 0x00
        decompressor._input_data = bytes([literal_flag, 0x41])
        decompressor._input_pos = 1
        decompressor._process_literal_block(literal_flag)
        assert decompressor._output_buffer == b"A"
