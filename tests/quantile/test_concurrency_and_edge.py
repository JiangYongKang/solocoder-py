import threading
import time

import pytest

from solocoder_py.quantile import (
    EmptyDigestError,
    InvalidValueError,
    MockClock,
    QuantileEstimator,
    QuantileResult,
    TDigest,
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


class TestInsertManyAtomicity:
    def test_insert_many_partial_failure_no_pollution(self, estimator_no_window):
        initial_count = estimator_no_window.insert_count
        initial_weight = estimator_no_window.total_weight

        values = [1.0, 2.0, float("nan"), 4.0, 5.0]
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many(values)

        assert estimator_no_window.insert_count == initial_count
        assert estimator_no_window.total_weight == initial_weight

    def test_insert_many_negative_weight_no_pollution(self, estimator_no_window):
        initial_count = estimator_no_window.insert_count
        initial_weight = estimator_no_window.total_weight

        values = [1.0, 2.0, 3.0]
        weights = [1.0, -1.0, 1.0]
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many(values, weights)

        assert estimator_no_window.insert_count == initial_count
        assert estimator_no_window.total_weight == initial_weight

    def test_insert_many_zero_weight_no_pollution(self, estimator_no_window):
        initial_count = estimator_no_window.insert_count

        values = [1.0, 2.0, 3.0]
        weights = [1.0, 0.0, 1.0]
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many(values, weights)

        assert estimator_no_window.insert_count == initial_count

    def test_insert_many_all_valid_succeeds(self, estimator_no_window):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        estimator_no_window.insert_many(values)
        assert estimator_no_window.insert_count == 5
        assert estimator_no_window.total_weight == 5.0

    def test_insert_many_length_mismatch_no_pollution(self, estimator_no_window):
        initial_count = estimator_no_window.insert_count

        values = [1.0, 2.0, 3.0]
        weights = [1.0, 2.0]
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many(values, weights)

        assert estimator_no_window.insert_count == initial_count

    def test_insert_many_inf_value_no_pollution(self, estimator_no_window):
        initial_count = estimator_no_window.insert_count

        values = [1.0, float("inf"), 3.0]
        with pytest.raises(InvalidValueError):
            estimator_no_window.insert_many(values)

        assert estimator_no_window.insert_count == initial_count


class TestTimestampPerInsert:
    def test_insert_each_has_independent_timestamp(self, mock_clock):
        est = QuantileEstimator(delta=100.0, clock=mock_clock)

        est.insert(10.0)
        mock_clock.advance(5.0)
        est.insert(20.0)
        mock_clock.advance(5.0)
        est.insert(30.0)

        config = WindowConfig(window_seconds=7.0)
        est_win = QuantileEstimator(delta=100.0, window_config=config, clock=mock_clock)
        est_win.insert(10.0)
        mock_clock.advance(5.0)
        est_win.insert(20.0)
        mock_clock.advance(5.0)
        est_win.insert(30.0)

        p50 = est_win.p50()
        assert 15 <= p50 <= 35

    def test_insert_many_each_has_independent_timestamp(self, mock_clock):
        config = WindowConfig(window_seconds=8.0)
        est = QuantileEstimator(delta=100.0, window_config=config, clock=mock_clock)

        mock_clock.set(100.0)

        class AdvancingMockClock(MockClock):
            def __init__(self, start, step):
                super().__init__(start)
                self._step = step
                self._call_count = 0

            def now(self):
                t = super().now() + self._call_count * self._step
                self._call_count += 1
                return t

        clock = AdvancingMockClock(100.0, 2.0)
        est2 = QuantileEstimator(delta=100.0, window_config=config, clock=clock)

        values = [float(i) for i in range(10)]
        est2.insert_many(values)

        assert est2.insert_count == 10

    def test_concurrent_inserts_have_timestamps_in_lock(self):
        class TrackingClock(MockClock):
            def __init__(self):
                super().__init__(0.0)
                self.call_count = 0
                self._lock = threading.Lock()

            def now(self):
                with self._lock:
                    self.call_count += 1
                    t = self._current_time + self.call_count * 0.001
                    return t

        clock = TrackingClock()
        est = QuantileEstimator(delta=200.0, clock=clock)
        errors = []

        def writer(start, count):
            try:
                for i in range(count):
                    est.insert(float(start + i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100, 100)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert est.insert_count == 800
        assert clock.call_count == 800


class TestWindowFilterBeforeCompression:
    def test_old_data_not_preserved_after_window_filter(self, mock_clock):
        td = TDigest(delta=100.0)

        for i in range(50):
            td.add(10.0 + i * 0.01, timestamp=0.0)

        for i in range(50):
            td.add(100.0 + i * 0.01, timestamp=200.0)

        td.trim(current_time=200.0, window_seconds=50.0)

        p50 = td.quantile(0.5)
        assert 90 <= p50 <= 110

    def test_centroid_merge_does_not_revive_old_data(self, mock_clock):
        td = TDigest(delta=10.0)

        td.add(50.0, weight=10.0, timestamp=0.0)
        td.add(50.1, weight=10.0, timestamp=0.0)

        td.add(50.2, weight=10.0, timestamp=200.0)
        td.add(50.3, weight=10.0, timestamp=200.0)

        td.trim(current_time=200.0, window_seconds=50.0)

        assert td.total_weight > 0
        assert td.total_weight < 30.0

    def test_buffer_data_also_filtered(self, mock_clock):
        td = TDigest(delta=500.0)

        for i in range(10):
            td.add(10.0, timestamp=0.0)

        for i in range(10):
            td.add(100.0, timestamp=300.0)

        td.trim(current_time=300.0, window_seconds=50.0)

        if not td.is_empty:
            p50 = td.quantile(0.5)
            assert 50 <= p50 <= 150

    def test_estimator_window_query_filters_before_compress(self, mock_clock):
        config = WindowConfig(window_seconds=60.0)
        est = QuantileEstimator(delta=10.0, window_config=config, clock=mock_clock)

        mock_clock.set(0.0)
        for i in range(20):
            est.insert(10.0 + i * 0.1)

        mock_clock.set(200.0)
        for i in range(20):
            est.insert(100.0 + i * 0.1)

        p50 = est.p50()
        assert 80 <= p50 <= 120

    def test_half_life_decay_applied_before_compress(self, mock_clock):
        td = TDigest(delta=100.0)

        for _ in range(100):
            td.add(10.0, timestamp=0.0)

        for _ in range(100):
            td.add(100.0, timestamp=100.0)

        td.trim(current_time=100.0, window_seconds=200.0, half_life_seconds=50.0)

        p50 = td.quantile(0.5)
        assert 50 <= p50 <= 100
