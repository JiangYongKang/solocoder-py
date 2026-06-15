import pytest


@pytest.fixture
def default_hll():
    from solocoder_py.cardinality import HyperLogLog
    return HyperLogLog(num_registers=4096)


@pytest.fixture
def high_precision_hll():
    from solocoder_py.cardinality import HyperLogLog
    return HyperLogLog(standard_error=0.01)


@pytest.fixture
def sample_data_source():
    from solocoder_py.cardinality import MemoryDataSource, generate_random_strings
    ds = MemoryDataSource(name="sample")
    ds.add_many(generate_random_strings(100, seed=42))
    return ds
