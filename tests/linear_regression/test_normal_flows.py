from __future__ import annotations

import pytest

from solocoder_py.linear_regression import SimpleLinearRegression


class TestInitialization:
    def test_initial_state_zero_params(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        assert reg.w == 0.0
        assert reg.b == 0.0
        assert reg.n_samples == 0
        assert reg.learning_rate == 0.01

    def test_learning_rate_property(self):
        reg = SimpleLinearRegression(learning_rate=0.5)
        assert reg.learning_rate == 0.5


class TestPerfectLinearData:
    def test_converges_to_correct_params_small_lr(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 3.0
        for epoch in range(5):
            for x in range(20):
                y = true_w * x + true_b
                reg.update(float(x), y)
        assert abs(reg.w - true_w) < 0.2
        assert abs(reg.b - true_b) < 1.0

    def test_converges_with_many_iterations(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 3.0
        for epoch in range(5):
            for x in range(50):
                y = true_w * x + true_b
                reg.update(float(x), y)
        assert abs(reg.w - true_w) < 0.1

    def test_n_samples_increments_correctly(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        for i in range(10):
            reg.update(float(i), float(i))
        assert reg.n_samples == 10


class TestPointPrediction:
    def test_prediction_matches_manual_calc(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        reg.update(1.0, 5.0)
        expected = reg.w * 2.0 + reg.b
        assert reg.predict(2.0) == pytest.approx(expected)

    def test_predict_after_multiple_updates(self):
        reg = SimpleLinearRegression(learning_rate=0.5)
        true_w = 2.0
        true_b = 3.0
        for epoch in range(3):
            for x in range(10):
                y = true_w * x + true_b
                reg.update(float(x), y)
        x_test = 5.0
        expected = true_w * x_test + true_b
        assert abs(reg.predict(x_test) - expected) < 3.0


class TestRSquaredGoodFit:
    def test_r2_positive_good_fit(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 3.0
        for epoch in range(5):
            for x in range(20):
                y = true_w * x + true_b
                reg.update(float(x), y)
        r2 = reg.r2_score()
        assert r2 > 0.95

    def test_r2_finite(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        for x in range(10):
            y = 3 * x + 5
            reg.update(float(x), y)
        r2 = reg.r2_score()
        assert isinstance(r2, float)


class TestRSquaredRandomNoise:
    def test_r2_near_zero_random_data(self):
        import random

        random.seed(42)
        reg = SimpleLinearRegression(learning_rate=0.01)
        for _ in range(1000):
            x = random.uniform(0, 10)
            y = random.uniform(0, 10)
            reg.update(x, y)
        r2 = reg.r2_score()
        assert abs(r2) < 0.3


class TestConvergenceTrend:
    def test_error_decreases_over_time(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 3.0

        epoch_abs_errors = []
        for epoch in range(5):
            total_err = 0.0
            for x in range(20):
                y = true_w * x + true_b
                y_pred_before = reg.w * x + reg.b
                denom = 1.0 + abs(y)
                total_err += abs(y_pred_before - y) / denom
                reg.update(float(x), y)
            epoch_abs_errors.append(total_err / 20)

        assert epoch_abs_errors[-1] < epoch_abs_errors[0]

    def test_params_change_decreases_over_time(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        true_w = 2.0
        true_b = 3.0

        epoch_w_changes = []
        for epoch in range(5):
            epoch_change = 0.0
            for x in range(20):
                y = true_w * x + true_b
                w_before = reg.w
                reg.update(float(x), y)
                epoch_change += abs(reg.w - w_before)
            epoch_w_changes.append(epoch_change / 20)

        assert epoch_w_changes[-1] < epoch_w_changes[0]


class TestOnlineUpdateConsistency:
    def test_single_update_changes_params(self):
        reg = SimpleLinearRegression(learning_rate=0.1)
        old_w = reg.w
        old_b = reg.b
        reg.update(1.0, 5.0)
        assert reg.w != old_w
        assert reg.b != old_b

    def test_zero_learning_rate_no_change(self):
        reg = SimpleLinearRegression(learning_rate=0.0)
        old_w = reg.w
        old_b = reg.b
        reg.update(10.0, 20.0)
        assert reg.w == old_w
        assert reg.b == old_b
