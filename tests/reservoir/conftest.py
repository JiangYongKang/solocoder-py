import pytest

from solocoder_py.reservoir import ReservoirSampler, WeightedReservoirSampler


@pytest.fixture
def sampler_k5():
    return ReservoirSampler(capacity=5, seed=42)


@pytest.fixture
def sampler_k1():
    return ReservoirSampler(capacity=1, seed=42)


@pytest.fixture
def sampler_k0():
    return ReservoirSampler(capacity=0, seed=42)


@pytest.fixture
def weighted_sampler_k5():
    return WeightedReservoirSampler(capacity=5, seed=42)


@pytest.fixture
def weighted_sampler_k1():
    return WeightedReservoirSampler(capacity=1, seed=42)


@pytest.fixture
def weighted_sampler_k0():
    return WeightedReservoirSampler(capacity=0, seed=42)
