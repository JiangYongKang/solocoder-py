import pytest
from typing import List

from solocoder_py.tsdelta import (
    TsDeltaCompressor,
    TsDeltaDecompressor,
    TsDeltaConfig,
)


@pytest.fixture
def default_config():
    return TsDeltaConfig()


@pytest.fixture
def no_validation_config():
    return TsDeltaConfig(validate_strictly_increasing=False)


@pytest.fixture
def make_compressor():
    def _make_compressor(config=None):
        return TsDeltaCompressor(config=config)
    return _make_compressor


@pytest.fixture
def make_decompressor():
    def _make_decompressor(config=None):
        return TsDeltaDecompressor(config=config)
    return _make_decompressor


@pytest.fixture
def roundtrip():
    def _roundtrip(timestamps: List[int], config=None):
        compressor = TsDeltaCompressor(config=config)
        compressor.write_all(timestamps)
        compressed = compressor.get_compressed_data()
        c_stats = compressor.get_stats()

        decompressor = TsDeltaDecompressor(config=config)
        decompressor.set_input_data(compressed)
        result = decompressor.read_all()
        d_stats = decompressor.get_stats()

        return result, compressed, c_stats, d_stats
    return _roundtrip


@pytest.fixture
def equal_interval_timestamps():
    base = 1718841600000
    return [base + i * 1000 for i in range(100)]


@pytest.fixture
def non_equal_interval_timestamps():
    base = 1718841600000
    intervals = [1000, 1001, 999, 1002, 998, 1003, 997, 1004, 996, 1005]
    timestamps = [base]
    current = base
    for interval in intervals:
        current += interval
        timestamps.append(current)
    return timestamps
