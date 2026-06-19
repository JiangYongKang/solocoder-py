import pytest

from solocoder_py.lz77 import (
    LZ77Compressor,
    LZ77Decompressor,
    LZ77Config,
    CompressionStats,
)


class TestLZ77Config:
    def test_default_config(self):
        config = LZ77Config()
        assert config.window_size == 32768
        assert config.min_match_length == 3
        assert config.max_match_length == 258
        assert config.hash_chain_limit == 256
        assert config.literal_block_max == 128

    def test_custom_config(self):
        config = LZ77Config(
            window_size=1024,
            min_match_length=4,
            max_match_length=100,
            hash_chain_limit=64,
            literal_block_max=64,
        )
        assert config.window_size == 1024
        assert config.min_match_length == 4
        assert config.max_match_length == 100
        assert config.hash_chain_limit == 64
        assert config.literal_block_max == 64


class TestCompressionStats:
    def test_compression_ratio(self):
        stats = CompressionStats(
            original_size=100,
            compressed_size=50,
            literal_count=20,
            match_count=5,
            hash_chain_truncations=0,
        )
        assert stats.compression_ratio == 0.5

    def test_savings_ratio(self):
        stats = CompressionStats(
            original_size=100,
            compressed_size=30,
            literal_count=10,
            match_count=3,
            hash_chain_truncations=0,
        )
        assert stats.savings_ratio == 0.7

    def test_zero_original_size(self):
        stats = CompressionStats(
            original_size=0,
            compressed_size=0,
            literal_count=0,
            match_count=0,
            hash_chain_truncations=0,
        )
        assert stats.compression_ratio == 0.0
        assert stats.savings_ratio == 0.0


class TestNormalFlows:
    def test_repeated_string_compression(self, roundtrip):
        data = b"abcabcabcabcabcabcabcabcabcabc"
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.match_count > 0
        assert c_stats.compression_ratio < 1.0

    def test_single_long_repeated_pattern(self, roundtrip):
        data = b"Hello World! " * 50
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.match_count > 0
        assert c_stats.compression_ratio < 0.5

    def test_mixed_literal_and_match(self, roundtrip):
        data = b"The quick brown fox jumps over the lazy dog. The quick brown fox."
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.literal_count > 0
        assert c_stats.match_count > 0

    def test_hash_chain_multiple_candidates(self, roundtrip):
        pattern = b"abc"
        data = pattern * 10 + b"def" + pattern * 5
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.match_count >= 2

    def test_longest_match_selected(self, make_compressor, make_decompressor):
        data = b"abcdefg" + b"x" * 10 + b"abcdefghij"
        compressor = make_compressor()
        compressed = compressor.compress(data)
        decompressor = make_decompressor()
        result = decompressor.decompress(compressed)
        assert result == data
        stats = compressor.get_stats()
        assert stats.match_count >= 1

    def test_sliding_window_eviction(self, roundtrip, small_window_config):
        window_size = small_window_config.window_size
        prefix = b"A" * (window_size + 100)
        suffix = b"B" * 200
        data = prefix + suffix
        result, compressed, c_stats, d_stats = roundtrip(data, small_window_config)
        assert result == data

    def test_large_data_compression(self, roundtrip):
        data = b"abcdefghij" * 1000
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert len(compressed) < len(data)

    def test_context_manager(self):
        data = b"test data with repetition test data"
        with LZ77Compressor() as compressor:
            compressed = compressor.compress(data)
        with LZ77Decompressor() as decompressor:
            result = decompressor.decompress(compressed)
        assert result == data

    def test_reset_compressor(self, make_compressor):
        compressor = make_compressor()
        data1 = b"hello world hello"
        compressor.compress(data1)
        assert compressor.total_input == len(data1)

        compressor.reset()
        assert compressor.total_input == 0
        assert compressor.match_count == 0
        assert compressor.literal_count == 0
        assert compressor.get_compressed_data() == b""

    def test_reset_decompressor(self, make_decompressor, make_compressor):
        compressor = make_compressor()
        data = b"test compression"
        compressed = compressor.compress(data)

        decompressor = make_decompressor()
        decompressor.decompress(compressed)
        assert decompressor.total_output == len(data)

        decompressor.reset()
        assert decompressor.total_output == 0
        assert decompressor.match_count == 0
        assert decompressor.literal_count == 0

    def test_literal_block_aggregation(self, make_compressor):
        data = bytes(range(200))
        compressor = make_compressor()
        compressed = compressor.compress(data)
        stats = compressor.get_stats()
        assert stats.literal_count == 200

    def test_multiple_match_lengths(self, roundtrip):
        parts = []
        for i in range(50):
            parts.append(bytes([i % 256]) * (i + 10))
        data = b"".join(parts)
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data

    def test_compressor_output_stream(self):
        import io
        data = b"hello world hello"
        output = io.BytesIO()
        compressor = LZ77Compressor(output_stream=output)
        compressed = compressor.compress(data)
        output_value = output.getvalue()
        assert output_value == compressed
        assert len(output_value) > 0

    def test_decompressor_output_stream(self):
        import io
        data = b"hello world hello test data"
        compressor = LZ77Compressor()
        compressed = compressor.compress(data)

        output = io.BytesIO()
        decompressor = LZ77Decompressor(output_stream=output)
        result = decompressor.decompress(compressed)
        output_value = output.getvalue()
        assert output_value == data
        assert result == data
