import math
import statistics

import pytest

from solocoder_py.quantile import (
    EmptyDigestError,
    InvalidQuantileError,
    InvalidValueError,
    InvalidWindowError,
    QuantileEstimator,
    QuantileResult,
    WindowConfig,
)


class TestQuantileEstimatorBasicOperations:
    def test_initial_state(self, estimator_no_window):
        assert estimator_no_window.is_empty is True
        assert estimator_no_window.insert_count == 0
        assert estimator_no_window.total_weight == 0.0
        assert estimator_no_window.delta == 100.0

    def test_insert_single_value(self, estimator_no_window):
        estimator_no_window.insert(42.0)
        assert estimator_no_window.is_empty is False
        assert estimator_no_window.insert_count == 1
        assert estimator_no_window.total_weight == 1.0

    def test_insert_increases_count(self, estimator_no_window):
        for i in range(10):
            estimator_no_window.insert(float(i))
        assert estimator_no_window.insert_count == 10
        assert estimator_no_window.total_weight == 10.0

    def test_insert_with_weight(self, estimator_no_window):
        estimator_no_window.insert(50.0, weight=3.0)
        estimator_no_window.insert(100.0, weight=1.0)
        assert estimator_no_window.insert_count == 2
        assert estimator_no_window.total_weight == 4.0

    def test_insert_many(self, estimator_no_window):
        values = [float(i) for i in range(50)]
        estimator_no_window.insert_many(values)
        assert estimator_no_window.insert_count == 50
        assert estimator_no_window.total_weight == 50.0

    def test_insert_many_with_weights(self, estimator_no_window):
        values = [10.0, 20.0, 30.0]
        weights = [2.0, 3.0, 5.0]
        estimator_no_window.insert_many(values, weights)
        assert estimator_no_window.insert_count == 3
        assert estimator_no_window.total_weight == 10.0


class TestQuantileEstimatorQuantileQueries:
    def test_single_value_quantile(self, estimator_no_window):
        estimator_no_window.insert(42.0)
        assert estimator_no_window.quantile(0.5) == pytest.approx(42.0)
        assert estimator_no_window.quantile(0.0) == pytest.approx(42.0)
        assert estimator_no_window.quantile(1.0) == pytest.approx(42.0)

    def test_two_values_quantile(self, estimator_no_window):
        estimator_no_window.insert(10.0)
        estimator_no_window.insert(30.0)
        median = estimator_no_window.quantile(0.5)
        assert 10.0 <= median <= 30.0

    def test_uniform_distribution_p50(self, estimator_with_data):
        p50 = estimator_with_data.p50()
        assert 45 <= p50 <= 55

    def test_uniform_distribution_p95(self, estimator_with_data):
        p95 = estimator_with_data.p95()
        assert 90 <= p95 <= 100

    def test_uniform_distribution_p99(self, estimator_with_data):
        p99 = estimator_with_data.p99()
        assert 95 <= p99 <= 100

    def test_quantiles_batch_query(self, estimator_with_data):
        results = estimator_with_data.quantiles([0.5, 0.95, 0.99])
        assert len(results) == 3
        assert all(isinstance(r, QuantileResult) for r in results)
        assert results[0].quantile == 0.5
        assert results[1].quantile == 0.95
        assert results[2].quantile == 0.99
        assert results[0].value <= results[1].value <= results[2].value

    def test_common_quantiles(self, estimator_with_data):
        result = estimator_with_data.common_quantiles()
        assert "p50" in result
        assert "p90" in result
        assert "p95" in result
        assert "p99" in result
        assert "p999" in result
        assert result["p50"] <= result["p90"] <= result["p95"] <= result["p99"] <= result["p999"]

    def test_normal_distribution_accuracy(self, estimator_large_dataset):
        p50 = estimator_large_dataset.p50()
        p95 = estimator_large_dataset.p95()
        assert 95 <= p50 <= 105
        assert 115 <= p95 <= 135

    def test_quantile_0_and_1(self, estimator_with_data):
        p0 = estimator_with_data.quantile(0.0)
        p1 = estimator_with_data.quantile(1.0)
        assert p0 <= estimator_with_data.p50() <= p1


class TestQuantileEstimatorEmptyQueries:
    def test_quantile_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.quantile(0.5)

    def test_quantiles_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.quantiles([0.5, 0.95])

    def test_p50_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.p50()

    def test_p95_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.p95()

    def test_p99_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.p99()

    def test_common_quantiles_on_empty_raises(self, estimator_no_window):
        with pytest.raises(EmptyDigestError):
            estimator_no_window.common_quantiles()


class TestQuantileEstimatorInvalidInputs:
    def test_insert_nan_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert(float("nan"))

    def test_insert_inf_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert(float("inf"))

    def test_insert_negative_inf_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert(float("-inf"))

    def test_insert_zero_weight_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert(1.0, weight=0.0)

    def test_insert_negative_weight_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert(1.0, weight=-1.0)

    def test_quantile_negative_raises(self, estimator_with_data):
        with pytest.raises(InvalidQuantileError):
            estimator_with_data.quantile(-0.1)

    def test_quantile_greater_than_one_raises(self, estimator_with_data):
        with pytest.raises(InvalidQuantileError):
            estimator_with_data.quantile(1.1)

    def test_quantiles_with_invalid_raises(self, estimator_with_data):
        with pytest.raises(InvalidQuantileError):
            estimator_with_data.quantiles([0.5, -0.1, 0.95])

    def test_insert_many_length_mismatch_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many([1.0, 2.0], [1.0])

    def test_insert_many_with_nan_raises(self, estimator_no_window):
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many([1.0, float("nan"), 3.0])

    def test_negative_window_raises(self, estimator_with_data):
        with pytest.raises(InvalidWindowError):
            estimator_with_data.quantile(0.5, window_seconds=-1.0)

    def test_zero_window_raises(self, estimator_with_data):
        with pytest.raises(InvalidWindowError):
            estimator_with_data.quantile(0.5, window_seconds=0.0)


class TestQuantileEstimatorSingleElement:
    def test_single_element_p50(self, estimator_no_window):
        estimator_no_window.insert(123.45)
        assert estimator_no_window.p50() == pytest.approx(123.45)

    def test_single_element_p95(self, estimator_no_window):
        estimator_no_window.insert(123.45)
        assert estimator_no_window.p95() == pytest.approx(123.45)

    def test_single_element_p99(self, estimator_no_window):
        estimator_no_window.insert(123.45)
        assert estimator_no_window.p99() == pytest.approx(123.45)

    def test_single_element_all_quantiles(self, estimator_no_window):
        estimator_no_window.insert(42.0)
        for q in [0.0, 0.25, 0.5, 0.75, 0.99, 1.0]:
            assert estimator_no_window.quantile(q) == pytest.approx(42.0)


class TestQuantileEstimatorWindowDecay:
    def test_window_excludes_old_data(self, estimator_with_window, mock_clock):
        estimator_with_window.insert(10.0)
        mock_clock.advance(120.0)
        estimator_with_window.insert(100.0)

        result = estimator_with_window.p50(window_seconds=60.0)
        assert result == pytest.approx(100.0, abs=1.0)

    def test_window_includes_recent_data(self, estimator_with_window, mock_clock):
        estimator_with_window.insert(10.0)
        mock_clock.advance(30.0)
        estimator_with_window.insert(100.0)

        result = estimator_with_window.p50(window_seconds=60.0)
        assert 10.0 <= result <= 100.0

    def test_default_window_from_config(self, estimator_with_window, mock_clock):
        estimator_with_window.insert(10.0)
        mock_clock.advance(120.0)
        estimator_with_window.insert(200.0)

        result = estimator_with_window.p50()
        assert 150 <= result <= 250

    def test_empty_window_raises(self, estimator_with_window, mock_clock):
        estimator_with_window.insert(10.0)
        mock_clock.advance(120.0)
        with pytest.raises(EmptyDigestError):
            estimator_with_window.p50(window_seconds=60.0)

    def test_half_life_decay_effect(self, estimator_with_window, mock_clock):
        for _ in range(10):
            estimator_with_window.insert(10.0)

        mock_clock.advance(30.0)

        for _ in range(10):
            estimator_with_window.insert(100.0)

        result = estimator_with_window.p50()
        assert 50.0 <= result <= 100.0

    def test_long_aged_data_weight_zero(self, estimator_with_window, mock_clock):
        estimator_with_window.insert(50.0)
        mock_clock.advance(300.0)
        estimator_with_window.insert(200.0)

        result = estimator_with_window.p50()
        assert 150 <= result <= 250

    def test_custom_window_overrides_config(self, mock_clock):
        config = WindowConfig(window_seconds=10.0)
        est = QuantileEstimator(delta=100.0, window_config=config, clock=mock_clock)
        est.insert(10.0)
        mock_clock.advance(30.0)
        est.insert(200.0)

        result = est.p50(window_seconds=60.0)
        assert 10.0 <= result <= 200.0
