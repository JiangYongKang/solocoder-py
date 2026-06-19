import pytest

from solocoder_py.metrics import MetricsRegistry


@pytest.fixture
def registry():
    return MetricsRegistry()
