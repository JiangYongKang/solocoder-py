import pytest

from solocoder_py.counter import DimensionSchema, MultiDimCounter


@pytest.fixture
def three_level_schema():
    return DimensionSchema(levels=["datacenter", "host", "service"])


@pytest.fixture
def single_level_schema():
    return DimensionSchema(levels=["region"])


@pytest.fixture
def two_level_schema():
    return DimensionSchema(levels=["country", "city"])


@pytest.fixture
def three_level_counter(three_level_schema):
    return MultiDimCounter(schema=three_level_schema)


@pytest.fixture
def single_level_counter(single_level_schema):
    return MultiDimCounter(schema=single_level_schema)

