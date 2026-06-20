import pytest

from solocoder_py.linear_regression import SimpleLinearRegression


@pytest.fixture
def lr_small():
    return SimpleLinearRegression(learning_rate=0.01)


@pytest.fixture
def lr_medium():
    return SimpleLinearRegression(learning_rate=0.1)


@pytest.fixture
def lr_zero():
    return SimpleLinearRegression(learning_rate=0.0)
