import pytest

from solocoder_py.quantile import MockClock, QuantileEstimator, WindowConfig


@pytest.fixture
def mock_clock():
    return MockClock(initial_time=1000.0)


@pytest.fixture
def estimator_no_window(mock_clock):
    return QuantileEstimator(delta=100.0, clock=mock_clock)


@pytest.fixture
def estimator_with_window(mock_clock):
    config = WindowConfig(window_seconds=60.0, half_life_seconds=30.0)
    return QuantileEstimator(delta=100.0, window_config=config, clock=mock_clock)


@pytest.fixture
def estimator_with_data(mock_clock):
    est = QuantileEstimator(delta=200.0, clock=mock_clock)
    for i in range(1, 101):
        est.insert(float(i))
    return est


@pytest.fixture
def estimator_large_dataset(mock_clock):
    est = QuantileEstimator(delta=500.0, clock=mock_clock)
    import random
    random.seed(42)
    for _ in range(10000):
        est.insert(random.gauss(100, 15))
    return est
