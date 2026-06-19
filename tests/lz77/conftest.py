import pytest

from solocoder_py.lz77 import (
    LZ77Compressor,
    LZ77Decompressor,
    LZ77Config,
)


@pytest.fixture
def default_config():
    return LZ77Config()


@pytest.fixture
def small_window_config():
    return LZ77Config(window_size=256, hash_chain_limit=32)


@pytest.fixture
def min_match_2_config():
    return LZ77Config(min_match_length=2, max_match_length=100)


@pytest.fixture
def small_chain_config():
    return LZ77Config(hash_chain_limit=4, window_size=1024)


@pytest.fixture
def make_compressor():
    def _make_compressor(config=None):
        return LZ77Compressor(config=config)
    return _make_compressor


@pytest.fixture
def make_decompressor():
    def _make_decompressor(config=None):
        return LZ77Decompressor(config=config)
    return _make_decompressor


@pytest.fixture
def roundtrip():
    def _roundtrip(data, config=None):
        compressor = LZ77Compressor(config=config)
        compressed = compressor.compress(data)

        decompressor = LZ77Decompressor(config=config)
        decompressed = decompressor.decompress(compressed)

        return decompressed, compressed, compressor.get_stats(), decompressor.get_stats()
    return _roundtrip
