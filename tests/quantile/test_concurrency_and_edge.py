import threading
import time

import pytest

from solocoder_py.quantile import (
    EmptyDigestError,
    MockClock,
    QuantileEstimator,
    QuantileResult,
    WindowConfig,
)


class TestQuantileEstimatorConcurrency:
    def test_concurrent_inserts_no_data_loss(self):
        est = QuantileEstimator(delta=200.0)
        num_threads = 8
        per_thread = 200
        errors = []

        def writer(start):
            try:
                for i in range(start, start + per_thread):
                    est.insert(float(i))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * per_thread,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert est.insert_count == num_threads * per_thread

    def test_concurrent_inserts_and_queries(self):
        est = QuantileEstimator(delta=200.0)
        errors = []

        def writer():
            try:
                for i in range(200):
                    est.insert(float(i))
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    try:
                        _ = est.p50()
                        _ = est.p95()
                        _ = est.common_quantiles()
                    except EmptyDigestError:
                        pass
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(4):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_queries_return_consistent_values(self):
        est = QuantileEstimator(delta=200.0)
        for i in range(1000):
            est.insert(float(i % 100))

        results = []
        errors = []

        def reader():
            try:
                for _ in range(50):
                    p50 = est.p50()
                    p95 = est.p95()
                    results.append((p50, p95))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) > 0
        for p50, p95 in results:
            assert 30 <= p50 <= 70
            assert 80 <= p95 <= 110
            assert p50 <= p95

    def test_concurrent_inserts_with_weights(self):
        est = QuantileEstimator(delta=200.0)
        errors = []

        def writer(start):
            try:
                for i in range(100):
                    est.insert(float(start + i), weight=2.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert est.insert_count == 500
        assert est.total_weight == 1000.0

    def test_concurrent_insert_many(self):
        est = QuantileEstimator(delta=200.0)
        errors = []

        def writer(offset):
            try:
                values = [float(offset + i) for i in range(50)]
                est.insert_many(values)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 50,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert est.insert_count == 500

    def test_concurrent_window_queries(self, mock_clock):
        config = WindowConfig(window_seconds=60.0)
        est = QuantileEstimator(delta=200.0, window_config=config, clock=mock_clock)
        errors = []

        for i in range(200):
            est.insert(float(i))

        def reader():
            try:
                for _ in range(50):
                    try:
                        _ = est.quantile(0.5, window_seconds=60.0)
                        _ = est.quantiles([0.5, 0.95], window_seconds=60.0)
                    except EmptyDigestError:
                        pass
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestQuantileEstimatorModels:
    def test_window_config_validation(self):
        with pytest.raises(ValueError):
            WindowConfig(window_seconds=0.0)
        with pytest.raises(ValueError):
            WindowConfig(window_seconds=-1.0)
        with pytest.raises(ValueError):
            WindowConfig(window_seconds=60.0, half_life_seconds=0.0)
        with pytest.raises(ValueError):
            WindowConfig(window_seconds=60.0, half_life_seconds=-5.0)

        config = WindowConfig(window_seconds=60.0)
        assert config.window_seconds == 60.0
        assert config.half_life_seconds is None

        config = WindowConfig(window_seconds=60.0, half_life_seconds=30.0)
        assert config.half_life_seconds == 30.0


class TestQuantileEstimatorClock:
    def test_mock_clock_initial(self):
        clock = MockClock(initial_time=1000.0)
        assert clock.now() == 1000.0

    def test_mock_clock_advance(self):
        clock = MockClock(initial_time=1000.0)
        clock.advance(50.0)
        assert clock.now() == 1050.0
        clock.advance(-10.0)
        assert clock.now() == 1040.0

    def test_mock_clock_set(self):
        clock = MockClock()
        clock.set(5000.0)
        assert clock.now() == 5000.0

    def test_system_clock_returns_current_time(self):
        from solocoder_py.quantile import SystemClock

        clock = SystemClock()
        t1 = clock.now()
        time.sleep(0.01)
        t2 = clock.now()
        assert t2 >= t1


class TestQuantileEstimatorEdgeCases:
    def test_very_large_values(self, estimator_no_window):
        estimator_no_window.insert(1e15)
        estimator_no_window.insert(1e15 + 1000)
        p50 = estimator_no_window.p50()
        assert p50 >= 1e15

    def test_very_small_values(self, estimator_no_window):
        estimator_no_window.insert(1e-15)
        estimator_no_window.insert(1e-15 * 2)
        p50 = estimator_no_window.p50()
        assert 0 < p50 < 1e-10

    def test_negative_values(self, estimator_no_window):
        estimator_no_window.insert(-100.0)
        estimator_no_window.insert(-50.0)
        estimator_no_window.insert(0.0)
        p50 = estimator_no_window.p50()
        assert -100 <= p50 <= 0

    def test_mixed_sign_values(self, estimator_no_window):
        for i in range(-50, 51):
            estimator_no_window.insert(float(i))
        p50 = estimator_no_window.p50()
        assert -5 <= p50 <= 5

    def test_duplicate_values(self, estimator_no_window):
        for _ in range(100):
            estimator_no_window.insert(42.0)
        assert estimator_no_window.p50() == pytest.approx(42.0)
        assert estimator_no_window.p99() == pytest.approx(42.0)

    def test_weighted_single_element(self, estimator_no_window):
        estimator_no_window.insert(100.0, weight=100.0)
        assert estimator_no_window.p50() == pytest.approx(100.0)
        assert estimator_no_window.total_weight == 100.0

    def test_quantile_results_ordered(self, estimator_no_window):
        for i in range(1, 1001):
            estimator_no_window.insert(float(i))
        results = estimator_no_window.quantiles([0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
        values = [r.value for r in results]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]

    def test_constructor_validation(self):
        with pytest.raises(ValueError):
            QuantileEstimator(delta=0.0)
        with pytest.raises(ValueError):
            QuantileEstimator(delta=-5.0)

        est = QuantileEstimator(delta=50.0)
        assert est.delta == 50.0
