import pytest

from solocoder_py.ewma import EWMA


@pytest.fixture
def ewma_alpha_05():
    return EWMA(alpha=0.5)


@pytest.fixture
def ewma_alpha_03_warmup_10():
    return EWMA(alpha=0.3, warmup_period=10)


@pytest.fixture
def ewma_alpha_02_warmup_5_initial():
    return EWMA(alpha=0.2, warmup_period=5, initial_value=10.0)
