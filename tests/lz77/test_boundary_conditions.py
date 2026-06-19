import pytest

from solocoder_py.lz77 import (
    LZ77Compressor,
    LZ77Decompressor,
    LZ77Config,
    InvalidConfigError,
)


class TestBoundaryConditions:
    def test_empty_input(self, roundtrip):
        data = b""
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == b""
        assert compressed == b""
        assert c_stats.original_size == 0
        assert c_stats.compressed_size == 0
        assert c_stats.match_count == 0
        assert c_stats.literal_count == 0

    def test_all_repeated_data(self, roundtrip):
        data = b"A" * 1000
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.compression_ratio < 0.1
        assert c_stats.match_count > 0

    def test_all_incompressible_data(self, roundtrip):
        data = bytes(range(256)) * 2
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.literal_count > 0

    def test_single_byte_input(self, roundtrip):
        data = b"X"
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.literal_count == 1
        assert c_stats.match_count == 0

    def test_two_bytes_input(self, roundtrip):
        data = b"XY"
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data
        assert c_stats.literal_count == 2
        assert c_stats.match_count == 0

    def test_exact_min_match_length(self, roundtrip, default_config):
        min_len = default_config.min_match_length
        pattern = b"abc"
        data = pattern + b"x" + pattern
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data

    def test_match_exactly_at_min_length(self, make_compressor, make_decompressor, default_config):
        min_len = default_config.min_match_length
        data = b"a" * min_len + b"b" + b"a" * min_len
        compressor = make_compressor()
        compressed = compressor.compress(data)
        decompressor = make_decompressor()
        result = decompressor.decompress(compressed)
        assert result == data

    def test_max_match_length(self, roundtrip, default_config):
        max_len = default_config.max_match_length
        pattern = b"abc" * 100
        data = pattern + b"X" + pattern
        result, compressed, c_stats, d_stats = roundtrip(data)
        assert result == data

    def test_hash_chain_truncation(self, small_chain_config):
        limit = small_chain_config.hash_chain_limit
        pattern = b"aaa"
        repetitions = limit * 3
        data = pattern * repetitions

        compressor = LZ77Compressor(config=small_chain_config)
        compressed = compressor.compress(data)
        stats = compressor.get_stats()

        assert stats.hash_chain_truncations > 0

        decompressor = LZ77Decompressor(config=small_chain_config)
        result = decompressor.decompress(compressed)
        assert result == data

    def test_exact_window_size_boundary(self, small_window_config):
        window_size = small_window_config.window_size
        pattern = b"abcd"
        data = pattern * 100
        while len(data) < window_size + 100:
            data += pattern
        data = data[:window_size + 200]

        compressor = LZ77Compressor(config=small_window_config)
        compressed = compressor.compress(data)

        decompressor = LZ77Decompressor(config=small_window_config)
        result = decompressor.decompress(compressed)
        assert result == data

    def test_literal_block_at_max_size(self, make_compressor, make_decompressor, default_config):
        max_block = default_config.literal_block_max
        data = bytes(range(max_block))
        compressor = make_compressor()
        compressed = compressor.compress(data)
        decompressor = make_decompressor()
        result = decompressor.decompress(compressed)
        assert result == data

    def test_literal_block_exactly_at_boundary(self, make_compressor, make_decompressor, default_config):
        max_block = default_config.literal_block_max
        data = bytes(range(max_block + 1))
        compressor = make_compressor()
        compressed = compressor.compress(data)
        stats = compressor.get_stats()
        assert stats.literal_count == max_block + 1
        decompressor = make_decompressor()
        result = decompressor.decompress(compressed)
        assert result == data

    def test_distance_at_max_window_size(self, small_window_config):
        window_size = small_window_config.window_size
        pattern = b"test"
        data = pattern + b"X" * (window_size - len(pattern)) + pattern
        compressor = LZ77Compressor(config=small_window_config)
        compressed = compressor.compress(data)
        decompressor = LZ77Decompressor(config=small_window_config)
        result = decompressor.decompress(compressed)
        assert result == data

    def test_min_match_length_2(self, min_match_2_config):
        data = b"abababab"
        compressor = LZ77Compressor(config=min_match_2_config)
        compressed = compressor.compress(data)
        stats = compressor.get_stats()
        assert stats.match_count > 0
        decompressor = LZ77Decompressor(config=min_match_2_config)
        result = decompressor.decompress(compressed)
        assert result == data


class TestConfigBoundaries:
    def test_invalid_window_size_zero(self):
        with pytest.raises(InvalidConfigError, match="window_size must be >= 1"):
            LZ77Config(window_size=0)

    def test_invalid_window_size_negative(self):
        with pytest.raises(InvalidConfigError, match="window_size must be >= 1"):
            LZ77Config(window_size=-1)

    def test_invalid_min_match_length(self):
        with pytest.raises(InvalidConfigError, match="min_match_length must be >= 2"):
            LZ77Config(min_match_length=1)

    def test_invalid_max_match_length_less_than_min(self):
        with pytest.raises(InvalidConfigError, match="max_match_length must be >= min_match_length"):
            LZ77Config(min_match_length=5, max_match_length=3)

    def test_invalid_hash_chain_limit_zero(self):
        with pytest.raises(InvalidConfigError, match="hash_chain_limit must be >= 1"):
            LZ77Config(hash_chain_limit=0)

    def test_invalid_literal_block_max_zero(self):
        with pytest.raises(InvalidConfigError, match="literal_block_max must be >= 1"):
            LZ77Config(literal_block_max=0)

    def test_invalid_window_size_exceeds_max_distance(self):
        with pytest.raises(InvalidConfigError, match="window_size must be <="):
            LZ77Config(window_size=65536)

    def test_invalid_max_match_length_exceeds_encoding(self):
        with pytest.raises(InvalidConfigError, match="max_match_length must be <= min_match_length"):
            LZ77Config(min_match_length=3, max_match_length=300)

    def test_invalid_literal_block_max_exceeds_encoding(self):
        with pytest.raises(InvalidConfigError, match="literal_block_max must be <="):
            LZ77Config(literal_block_max=129)

    def test_max_match_length_at_encoding_limit(self):
        config = LZ77Config(min_match_length=3, max_match_length=258)
        assert config.max_match_length == 258

    def test_literal_block_max_at_encoding_limit(self):
        config = LZ77Config(literal_block_max=128)
        assert config.literal_block_max == 128

    def test_window_size_at_max_distance(self):
        config = LZ77Config(window_size=65535)
        assert config.window_size == 65535

    def test_valid_minimal_config(self):
        config = LZ77Config(
            window_size=1,
            min_match_length=2,
            max_match_length=2,
            hash_chain_limit=1,
            literal_block_max=1,
        )
        assert config.window_size == 1
        assert config.min_match_length == 2
        assert config.max_match_length == 2
        assert config.hash_chain_limit == 1
        assert config.literal_block_max == 1
