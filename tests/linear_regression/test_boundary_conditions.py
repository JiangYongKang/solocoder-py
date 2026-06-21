from __future__ import annotations

import pytest

from solocoder_py.linear_regression import SimpleLinearRegression


class TestSingleSampleR2:
    def test_single_sample_r2_returns_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 5.0)
        assert reg.r2_score() == 0.0

    def test_single_sample_predict_works(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 5.0)
        prediction = reg.predict(2.0)
        assert isinstance(prediction, float)


class TestVerySmallLearningRate:
    def test_tiny_lr_small_changes(self):
        tiny_lr = 1e-10
        reg = SimpleLinearRegression(learning_rate=tiny_lr)
        old_w = reg.w
        old_b = reg.b
        reg.update(100.0, 200.0)
        assert abs(reg.w - old_w) < 1e-5
        assert abs(reg.b - old_b) < 1e-5

    def test_tiny_lr_many_updates_eventually_changes(self):
        tiny_lr = 1e-8
        reg = SimpleLinearRegression(learning_rate=tiny_lr)
        old_w = reg.w
        for _ in range(10000):
            reg.update(1.0, 2.0)
        assert abs(reg.w - old_w) > 0


class TestZeroLearningRate:
    def test_zero_lr_params_unchanged_multiple_updates(self):
        reg = SimpleLinearRegression(learning_rate=0.0)
        old_w = reg.w
        old_b = reg.b
        for x in range(100):
            reg.update(float(x), float(x * 2 + 3))
        assert reg.w == old_w
        assert reg.b == old_b

    def test_zero_lr_n_samples_still_increments(self):
        reg = SimpleLinearRegression(learning_rate=0.0)
        for i in range(50):
            reg.update(float(i), float(i))
        assert reg.n_samples == 50

    def test_zero_lr_r2_calculated(self):
        reg = SimpleLinearRegression(learning_rate=0.0)
        for x in range(10):
            reg.update(float(x), float(x * 2))
        r2 = reg.r2_score()
        assert isinstance(r2, float)


class TestAllXSameDegenerateCase:
    def test_all_x_same_updates_run(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        for y in range(100):
            reg.update(5.0, float(y))
        assert reg.n_samples == 100
        assert isinstance(reg.w, float)
        assert isinstance(reg.b, float)

    def test_all_x_same_predict_works(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        for y in range(50):
            reg.update(10.0, float(y))
        pred = reg.predict(10.0)
        assert isinstance(pred, float)

    def test_all_x_same_r2_valid(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        for y in range(20):
            reg.update(5.0, float(y * 3))
        r2 = reg.r2_score()
        assert isinstance(r2, float)


class TestZeroData:
    def test_y_all_same_r2_returns_zero(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        for x in range(10):
            reg.update(float(x), 5.0)
        r2 = reg.r2_score()
        assert r2 == 0.0


class TestEdgeValues:
    def test_large_x_values(self):
        reg = SimpleLinearRegression(learning_rate=1e-10)
        reg.update(1e6, 2e6)
        assert reg.n_samples == 1
        assert isinstance(reg.w, float)
        assert not (reg.w != reg.w)

    def test_negative_x_values(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 1.0
        for epoch in range(5):
            for x in range(-100, 100):
                y = true_w * x + true_b
                reg.update(float(x), y)
        assert abs(reg.w - true_w) < 0.1

    def test_negative_y_values(self):
        reg = SimpleLinearRegression(learning_rate=0.0001)
        for x in range(100):
            reg.update(float(x), -float(x) - 5.0)
        assert reg.w < 0
        assert reg.n_samples == 100

    def test_float_precision(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(0.1, 0.2)
        reg.update(0.3, 0.4)
        assert reg.n_samples == 2


class TestTwoSamples:
    def test_two_samples_r2_valid(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(0.0, 0.0)
        reg.update(1.0, 1.0)
        r2 = reg.r2_score()
        assert isinstance(r2, float)
