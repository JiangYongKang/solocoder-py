import pytest

from solocoder_py.delta import (
    DeltaCompressor,
    DeltaDecompressor,
    DeltaEncodingConfig,
    WidthMarker,
)


@pytest.fixture
def default_config():
    return DeltaEncodingConfig(anchor_interval=10)


@pytest.fixture
def small_anchor_config():
    return DeltaEncodingConfig(anchor_interval=5)


@pytest.fixture
def no_anchor_reset_config():
    return DeltaEncodingConfig(anchor_interval=0)


@pytest.fixture
def make_compressor():
    def _make_compressor(config=None):
        return DeltaCompressor(config=config)
    return _make_compressor


@pytest.fixture
def make_decompressor():
    def _make_decompressor(config=None):
        return DeltaDecompressor(config=config)
    return _make_decompressor


@pytest.fixture
def roundtrip():
    def _roundtrip(values, config=None):
        compressor = DeltaCompressor(config=config)
        compressor.write_all(values)
        compressed = compressor.get_compressed_data()

        decompressor = DeltaDecompressor(config=config)
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()

        return result, compressed, compressor.get_stats(), decompressor.get_stats()
    return _roundtrip
