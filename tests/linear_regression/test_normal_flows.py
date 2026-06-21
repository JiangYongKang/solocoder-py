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
        reg = SimpleLinearRegression(learning_rate=0.01)
        true_w = 2.0
        true_b = 3.0
        for x in range(20):
            y = true_w * x + true_b
            reg.update(float(x), y)
        assert abs(reg.w - true_w) < 0.5
        assert abs(reg.b - true_b) < 3.0

    def test_converges_with_many_iterations(self):
        reg = SimpleLinearRegression(learning_rate=0.001)
        true_w = 2.0
        true_b = 3.0
        for x in range(50):
            y = true_w * x + true_b
            reg.update(float(x), y)
        assert abs(reg.w - true_w) < 1.0

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
        reg = SimpleLinearRegression(learning_rate=0.01)
        true_w = 2.0
        true_b = 3.0
        for x in range(10):
            y = true_w * x + true_b
            reg.update(float(x), y)
        x_test = 5.0
        expected = true_w * x_test + true_b
        assert abs(reg.predict(x_test) - expected) < 5.0


class TestRSquaredGoodFit:
    def test_r2_positive_good_fit(self):
        reg = SimpleLinearRegression(learning_rate=0.001)
        true_w = 2.0
        true_b = 3.0
        for x in range(20):
            y = true_w * x + true_b
            reg.update(float(x), y)
        r2 = reg.r2_score()
        assert r2 > 0.5

    def test_r2_finite(self):
        reg = SimpleLinearRegression(learning_rate=0.01)
        for x in range(10):
            y = 3 * x + 5
            reg.update(float(x), y)
        r2 = reg.r2_score()
        assert isinstance(r2, float)


class TestRSquaredRandomNoise:
    def test_r2_near_zero_random_data(self):
        import random

        random.seed(42)
        reg = SimpleLinearRegression(learning_rate=0.001)
        for _ in range(1000):
            x = random.uniform(0, 10)
            y = random.uniform(0, 10)
            reg.update(x, y)
        r2 = reg.r2_score()
        assert r2 < 0.5


class TestConvergenceTrend:
    def test_error_decreases_over_time(self):
        reg = SimpleLinearRegression(learning_rate=0.0005)
        true_w = 2.0
        true_b = 3.0

        errors = []
        for x in range(50):
            y = true_w * x + true_b
            y_pred_before = reg.w * x + reg.b
            errors.append(abs(y_pred_before - y))
            reg.update(float(x), y)

        first_quarter_avg = sum(errors[:10]) / 10
        last_quarter_avg = sum(errors[40:]) / 10
        assert last_quarter_avg < first_quarter_avg

    def test_params_change_decreases_over_time(self):
        reg = SimpleLinearRegression(learning_rate=0.0005)
        true_w = 2.0
        true_b = 3.0

        w_changes = []
        for x in range(50):
            y = true_w * x + true_b
            w_before = reg.w
            reg.update(float(x), y)
            w_changes.append(abs(reg.w - w_before))

        first_quarter_avg = sum(w_changes[:10]) / 10
        last_quarter_avg = sum(w_changes[40:]) / 10
        assert last_quarter_avg < first_quarter_avg


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
