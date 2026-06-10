import math
import threading

import pytest

from solocoder_py.heavy_hitter import (
    CountMinSketch,
    InvalidDeltaError,
    InvalidEpsilonError,
)


class TestCountMinSketchConstruction:
    def test_default_parameters(self):
        cms = CountMinSketch()
        assert cms.epsilon == 0.001
        assert cms.delta == 0.99
        assert cms.width == math.ceil(math.e / 0.001)
        assert cms.depth == math.ceil(math.log(1 / 0.99))
        assert cms.total_count == 0

    def test_custom_parameters(self):
        cms = CountMinSketch(epsilon=0.01, delta=0.9)
        assert cms.epsilon == 0.01
        assert cms.delta == 0.9
        assert cms.width == math.ceil(math.e / 0.01)
        assert cms.depth == math.ceil(math.log(1 / 0.9))

    def test_epsilon_zero_raises(self):
        with pytest.raises(InvalidEpsilonError, match="epsilon must be between 0 and 1"):
            CountMinSketch(epsilon=0)

    def test_epsilon_one_raises(self):
        with pytest.raises(InvalidEpsilonError, match="epsilon must be between 0 and 1"):
            CountMinSketch(epsilon=1)

    def test_epsilon_negative_raises(self):
        with pytest.raises(InvalidEpsilonError, match="epsilon must be between 0 and 1"):
            CountMinSketch(epsilon=-0.01)

    def test_epsilon_greater_than_one_raises(self):
        with pytest.raises(InvalidEpsilonError, match="epsilon must be between 0 and 1"):
            CountMinSketch(epsilon=1.5)

    def test_delta_zero_raises(self):
        with pytest.raises(InvalidDeltaError, match="delta must be between 0 and 1"):
            CountMinSketch(delta=0)

    def test_delta_one_raises(self):
        with pytest.raises(InvalidDeltaError, match="delta must be between 0 and 1"):
            CountMinSketch(delta=1)

    def test_delta_negative_raises(self):
        with pytest.raises(InvalidDeltaError, match="delta must be between 0 and 1"):
            CountMinSketch(delta=-0.5)


class TestCountMinSketchBasicOperations:
    def test_add_single_item(self):
        cms = CountMinSketch()
        cms.add("item1")
        assert cms.total_count == 1
        est = cms.estimate("item1")
        assert est >= 1

    def test_add_multiple_times(self):
        cms = CountMinSketch()
        for _ in range(100):
            cms.add("item1")
        assert cms.total_count == 100
        est = cms.estimate("item1")
        assert est >= 100

    def test_add_multiple_items(self):
        cms = CountMinSketch()
        for i in range(10):
            cms.add(f"item{i}", count=i + 1)
        assert cms.total_count == 55
        for i in range(10):
            est = cms.estimate(f"item{i}")
            assert est >= i + 1

    def test_add_with_count(self):
        cms = CountMinSketch()
        cms.add("item1", count=5)
        assert cms.total_count == 5
        est = cms.estimate("item1")
        assert est >= 5

    def test_add_count_zero_raises(self):
        cms = CountMinSketch()
        with pytest.raises(ValueError, match="count must be positive"):
            cms.add("item1", count=0)

    def test_add_count_negative_raises(self):
        cms = CountMinSketch()
        with pytest.raises(ValueError, match="count must be positive"):
            cms.add("item1", count=-1)

    def test_estimate_nonexistent_item(self):
        cms = CountMinSketch()
        cms.add("item1")
        est = cms.estimate("item2")
        assert est >= 0

    def test_lower_bound_same_as_estimate(self):
        cms = CountMinSketch()
        cms.add("item1", count=10)
        assert cms.lower_bound("item1") == cms.estimate("item1")

    def test_upper_bound_includes_error(self):
        cms = CountMinSketch(epsilon=0.01)
        for _ in range(1000):
            cms.add("item1")
        est = cms.estimate("item1")
        upper = cms.upper_bound("item1")
        error_bound = cms.error_bound()
        assert upper == est + int(0.01 * 1000)
        assert upper >= est

    def test_error_bound(self):
        cms = CountMinSketch(epsilon=0.001)
        for _ in range(10000):
            cms.add("item1")
        assert cms.error_bound() == 0.001 * 10000

    def test_clear(self):
        cms = CountMinSketch()
        cms.add("item1", count=100)
        cms.add("item2", count=50)
        assert cms.total_count == 150
        cms.clear()
        assert cms.total_count == 0
        assert cms.estimate("item1") == 0
        assert cms.estimate("item2") == 0

    def test_different_item_types(self):
        cms = CountMinSketch()
        cms.add(42, count=3)
        cms.add(3.14, count=2)
        cms.add(True, count=5)
        cms.add(b"bytes", count=7)
        assert cms.estimate(42) >= 3
        assert cms.estimate(3.14) >= 2
        assert cms.estimate(True) >= 5
        assert cms.estimate(b"bytes") >= 7
        assert cms.total_count == 17


class TestCountMinSketchMerge:
    def test_merge_compatible_sketches(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms1.add("item1", count=10)
        cms2.add("item1", count=20)
        cms2.add("item2", count=5)
        cms1.merge(cms2)
        assert cms1.total_count == 35
        assert cms1.estimate("item1") >= 30
        assert cms1.estimate("item2") >= 5

    def test_merge_different_width_raises(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.95)
        with pytest.raises(ValueError, match="different epsilon/delta"):
            cms1.merge(cms2)

    def test_merge_different_epsilon_raises(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.02, delta=0.9)
        with pytest.raises(ValueError, match="different epsilon/delta"):
            cms1.merge(cms2)

    def test_merge_does_not_affect_other(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms1.add("item1", count=10)
        cms2.add("item2", count=20)
        cms1.merge(cms2)
        assert cms2.total_count == 20
        assert cms2.estimate("item1") == 0


class TestCountMinSketchAccuracy:
    def test_high_frequency_items_accurate(self):
        cms = CountMinSketch(epsilon=0.001, delta=0.99)
        true_counts = {"A": 10000, "B": 5000, "C": 1000}
        for item, count in true_counts.items():
            for _ in range(count):
                cms.add(item)
        for item, true_count in true_counts.items():
            est = cms.estimate(item)
            assert est >= true_count
            error_bound = cms.error_bound()
            assert est <= true_count + error_bound

    def test_lower_bound_property(self):
        cms = CountMinSketch(epsilon=0.001, delta=0.99)
        items = [f"item{i}" for i in range(100)]
        true_counts = {item: (i + 1) * 10 for i, item in enumerate(items)}
        for item, count in true_counts.items():
            cms.add(item, count=count)
        for item, true_count in true_counts.items():
            est = cms.estimate(item)
            assert est >= true_count, f"Item {item}: estimate {est} < true {true_count}"


class TestCountMinSketchConcurrent:
    def test_concurrent_adds(self):
        cms = CountMinSketch()
        num_threads = 10
        per_thread = 1000
        errors = []

        def add_items(start):
            try:
                for i in range(start, start + per_thread):
                    cms.add(f"item{i % 10}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_items, args=(i * per_thread,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert cms.total_count == num_threads * per_thread

    def test_concurrent_reads_and_writes(self):
        cms = CountMinSketch()
        errors = []
        results = []

        def writer():
            for i in range(500):
                try:
                    cms.add(f"item{i % 20}")
                except Exception as e:
                    errors.append(e)

        def reader():
            for i in range(500):
                try:
                    est = cms.estimate(f"item{i % 20}")
                    results.append(est >= 0)
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert all(results)
