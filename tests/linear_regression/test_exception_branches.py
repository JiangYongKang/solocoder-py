from __future__ import annotations

import math

import pytest

from solocoder_py.linear_regression import (
    InvalidLearningRateError,
    InvalidSampleError,
    NotFittedError,
    SimpleLinearRegression,
)


class TestNegativeLearningRate:
    def test_negative_lr_raises(self):
        with pytest.raises(InvalidLearningRateError, match="non-negative"):
            SimpleLinearRegression(learning_rate=-0.01)

    def test_large_negative_lr_raises(self):
        with pytest.raises(InvalidLearningRateError):
            SimpleLinearRegression(learning_rate=-100.0)


class TestNaNInfLearningRate:
    def test_nan_lr_raises(self):
        with pytest.raises(InvalidLearningRateError):
            SimpleLinearRegression(learning_rate=float("nan"))

    def test_pos_inf_lr_raises(self):
        with pytest.raises(InvalidLearningRateError):
            SimpleLinearRegression(learning_rate=float("inf"))

    def test_neg_inf_lr_raises(self):
        with pytest.raises(InvalidLearningRateError):
            SimpleLinearRegression(learning_rate=float("-inf"))


class TestNaNSampleData:
    def test_nan_x_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError, match="NaN"):
            reg.update(float("nan"), 5.0)

    def test_nan_y_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError, match="NaN"):
            reg.update(5.0, float("nan"))

    def test_both_nan_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(float("nan"), float("nan"))


class TestInfSampleData:
    def test_pos_inf_x_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError, match="Inf"):
            reg.update(float("inf"), 5.0)

    def test_neg_inf_x_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(float("-inf"), 5.0)

    def test_pos_inf_y_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(5.0, float("inf"))

    def test_neg_inf_y_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(5.0, float("-inf"))


class TestPredictBeforeFit:
    def test_predict_before_fit_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(NotFittedError, match="not been fitted"):
            reg.predict(5.0)

    def test_predict_after_one_update_works(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        result = reg.predict(3.0)
        assert isinstance(result, float)

    def test_predict_nan_raises_after_fit(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        with pytest.raises(InvalidSampleError):
            reg.predict(float("nan"))

    def test_predict_inf_raises_after_fit(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        with pytest.raises(InvalidSampleError):
            reg.predict(float("inf"))


class TestR2BeforeFit:
    def test_r2_before_fit_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(NotFittedError, match="not been fitted"):
            reg.r2_score()

    def test_r2_after_one_sample_returns_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        assert reg.r2_score() == 0.0


class TestZeroSamples:
    def test_zero_samples_n_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        assert reg.n_samples == 0

    def test_zero_samples_w_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        assert reg.w == 0.0

    def test_zero_samples_b_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        assert reg.b == 0.0

    def test_zero_samples_predict_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(NotFittedError):
            reg.predict(1.0)

    def test_zero_samples_r2_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(NotFittedError):
            reg.r2_score()


class TestNonNumericInput:
    def test_string_x_update_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update("hello", 5.0)

    def test_string_y_update_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(5.0, "world")

    def test_string_predict_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        with pytest.raises(InvalidSampleError):
            reg.predict("abc")

    def test_none_update_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        with pytest.raises(InvalidSampleError):
            reg.update(None, 5.0)

    def test_none_predict_raises(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 2.0)
        with pytest.raises(InvalidSampleError):
            reg.predict(None)
