import threading

import pytest

from solocoder_py.heavy_hitter import (
    HeavyHitter,
    HeavyHitterDetector,
    InvalidCapacityError,
    InvalidKError,
)


class TestHeavyHitterDetectorConstruction:
    def test_valid_capacity(self):
        detector = HeavyHitterDetector(capacity=10)
        assert detector.capacity == 10
        assert detector.size == 0
        assert detector.evicted_count == 0
        assert detector.total_items_processed == 0

    def test_capacity_zero_raises(self):
        with pytest.raises(InvalidCapacityError, match="capacity must be a positive integer"):
            HeavyHitterDetector(capacity=0)

    def test_negative_capacity_raises(self):
        with pytest.raises(InvalidCapacityError, match="capacity must be a positive integer"):
            HeavyHitterDetector(capacity=-5)

    def test_custom_epsilon_delta(self):
        detector = HeavyHitterDetector(capacity=5, epsilon=0.01, delta=0.95)
        assert detector.capacity == 5


class TestHeavyHitterDetectorBasicRecording:
    def test_record_single_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1")
        assert detector.size == 1
        assert detector.total_items_processed == 1
        assert detector.contains("item1")
        est = detector.estimate_count("item1")
        assert est == 1, "Tracked item should have exact count as lower bound"
        assert detector.lower_bound("item1") <= 1
        assert detector.upper_bound("item1") >= 1

    def test_record_same_item_multiple_times(self):
        detector = HeavyHitterDetector(capacity=10)
        for _ in range(100):
            detector.record("item1")
        assert detector.size == 1
        assert detector.total_items_processed == 100
        est = detector.estimate_count("item1")
        assert est == 100, "Tracked item should have exact count as lower bound"
        assert detector.lower_bound("item1") == est
        assert detector.upper_bound("item1") >= 100

    def test_record_multiple_items_within_capacity(self):
        detector = HeavyHitterDetector(capacity=10)
        for i in range(5):
            detector.record(f"item{i}")
        assert detector.size == 5
        assert detector.total_items_processed == 5
        for i in range(5):
            assert detector.contains(f"item{i}")
            assert detector.estimate_count(f"item{i}") == 1

    def test_record_with_count(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1", count=5)
        assert detector.total_items_processed == 5
        est = detector.estimate_count("item1")
        assert est == 5, "Tracked item should have exact count as lower bound"
        assert detector.upper_bound("item1") >= 5

    def test_record_count_zero_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        with pytest.raises(ValueError, match="count must be positive"):
            detector.record("item1", count=0)

    def test_record_count_negative_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        with pytest.raises(ValueError, match="count must be positive"):
            detector.record("item1", count=-1)

    def test_record_different_item_types(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record(42)
        detector.record(3.14)
        detector.record(True)
        detector.record(b"bytes")
        assert detector.size == 4
        assert detector.contains(42)
        assert detector.contains(3.14)
        assert detector.contains(True)
        assert detector.contains(b"bytes")


class TestHeavyHitterDetectorTopK:
    def test_top_k_with_sufficient_items(self):
        detector = HeavyHitterDetector(capacity=10)
        true_counts = {"A": 100, "B": 80, "C": 60, "D": 40, "E": 20}
        for item, count in true_counts.items():
            for _ in range(count):
                detector.record(item)
        top3 = detector.get_top_k(3)
        assert len(top3) == 3
        assert top3[0].count >= top3[1].count >= top3[2].count
        assert top3[0].item == "A"
        assert top3[0].count == 100

    def test_top_k_returns_heavy_hitter_objects(self):
        detector = HeavyHitterDetector(capacity=5)
        detector.record("A", count=10)
        result = detector.get_top_k(1)
        assert len(result) == 1
        assert isinstance(result[0], HeavyHitter)
        assert result[0].item == "A"
        assert result[0].count == 10

    def test_top_k_sorted_descending(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=30)
        detector.record("B", count=50)
        detector.record("C", count=20)
        top3 = detector.get_top_k(3)
        assert top3[0].item == "B"
        assert top3[1].item == "A"
        assert top3[2].item == "C"
        assert top3[0].count == 50
        assert top3[1].count == 30
        assert top3[2].count == 20
        assert top3[0].count >= top3[1].count >= top3[2].count

    def test_top_k_less_than_available(self):
        detector = HeavyHitterDetector(capacity=10)
        for i in range(5):
            detector.record(f"item{i}", count=i + 1)
        top3 = detector.get_top_k(3)
        assert len(top3) == 3

    def test_get_all_tracked(self):
        detector = HeavyHitterDetector(capacity=10)
        for i in range(5):
            detector.record(f"item{i}", count=(5 - i) * 10)
        all_tracked = detector.get_all_tracked()
        assert len(all_tracked) == 5
        counts = [hh.count for hh in all_tracked]
        assert counts == sorted(counts, reverse=True)


class TestHeavyHitterDetectorEstimate:
    def test_estimate_for_tracked_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1", count=50)
        est = detector.estimate_count("item1")
        assert est == 50, "Tracked item estimate should be exact count"
        lower = detector.lower_bound("item1")
        upper = detector.upper_bound("item1")
        assert lower == 50, "lower_bound for tracked item equals exact store count"
        assert upper >= 50, "upper_bound should be >= true count (CMS overestimate)"
        assert lower <= est <= upper

    def test_estimate_for_untracked_item(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("item1", count=100)
        detector.record("item2", count=100)
        detector.record("item3", count=100)
        detector.record("item4", count=1)
        est = detector.estimate_count("item4")
        lower = detector.lower_bound("item4")
        upper = detector.upper_bound("item4")
        assert est >= 0, "lower bound should be >= 0"
        assert lower <= upper, "lower <= upper"
        assert upper >= 1, "CMS upper bound should be >= actual count"

    def test_lower_bound_property(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1", count=30)
        detector.record("item2", count=20)
        assert detector.lower_bound("item1") == 30, "Tracked item lower bound is exact count"
        assert detector.lower_bound("item2") == 20, "Tracked item lower bound is exact count"
        assert detector.lower_bound("item1") == detector.estimate_count("item1")
        assert detector.lower_bound("item2") == detector.estimate_count("item2")

    def test_upper_bound_property(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1", count=30)
        detector.record("item2", count=20)
        assert detector.upper_bound("item1") >= 30, "upper_bound >= true count"
        assert detector.upper_bound("item2") >= 20, "upper_bound >= true count"
        assert detector.upper_bound("item1") >= detector.estimate_count("item1")
        assert detector.upper_bound("item2") >= detector.estimate_count("item2")


class TestHeavyHitterDetectorContains:
    def test_contains_for_tracked_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1")
        assert detector.contains("item1") is True

    def test_contains_for_untracked_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1")
        assert detector.contains("item2") is False


class TestHeavyHitterDetectorClear:
    def test_clear_resets_state(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("item1", count=100)
        detector.record("item2", count=50)
        assert detector.size == 2
        assert detector.total_items_processed == 150
        detector.clear()
        assert detector.size == 0
        assert detector.evicted_count == 0
        assert detector.total_items_processed == 0
        assert detector.contains("item1") is False
        assert detector.estimate_count("item1") == 0


class TestHeavyHitterDetectorMerge:
    def test_merge_compatible_detectors(self):
        detector1 = HeavyHitterDetector(capacity=5)
        detector2 = HeavyHitterDetector(capacity=5)
        detector1.record("A", count=100)
        detector2.record("B", count=80)
        detector2.record("A", count=20)
        detector1.merge(detector2)
        assert detector1.total_items_processed == 200
        assert detector1.upper_bound("A") >= 120
        assert detector1.upper_bound("B") >= 80

    def test_merge_different_capacity_raises(self):
        detector1 = HeavyHitterDetector(capacity=5)
        detector2 = HeavyHitterDetector(capacity=10)
        with pytest.raises(ValueError, match="different capacities"):
            detector1.merge(detector2)

    def test_merge_with_eviction(self):
        detector1 = HeavyHitterDetector(capacity=3)
        detector2 = HeavyHitterDetector(capacity=3)
        detector1.record("A", count=100)
        detector1.record("B", count=90)
        detector1.record("C", count=80)
        detector2.record("D", count=200)
        detector2.record("E", count=150)
        detector1.merge(detector2)
        assert detector1.size == 3
        top3 = detector1.get_top_k(3)
        assert top3[0].item == "D"
        assert top3[1].item == "E"


class TestHeavyHitterDetectorConcurrent:
    def test_concurrent_records(self):
        detector = HeavyHitterDetector(capacity=100)
        num_threads = 10
        per_thread = 1000
        errors = []

        def record_items(start):
            try:
                for i in range(start, start + per_thread):
                    detector.record(f"item{i % 10}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=record_items, args=(i * per_thread,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert detector.total_items_processed == num_threads * per_thread

    def test_concurrent_reads_and_writes(self):
        detector = HeavyHitterDetector(capacity=50)
        errors = []

        def writer():
            for i in range(500):
                try:
                    detector.record(f"item{i % 20}")
                except Exception as e:
                    errors.append(e)

        def reader():
            for i in range(500):
                try:
                    detector.estimate_count(f"item{i % 20}")
                    if i % 50 == 0:
                        detector.get_top_k(5)
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


class TestHeavyHitterComparison:
    def test_heavy_hitter_lt(self):
        hh1 = HeavyHitter(item="A", count=10)
        hh2 = HeavyHitter(item="B", count=20)
        assert hh1 < hh2
        assert not hh2 < hh1

    def test_heavy_hitter_gt(self):
        hh1 = HeavyHitter(item="A", count=30)
        hh2 = HeavyHitter(item="B", count=20)
        assert hh1 > hh2
        assert not hh2 > hh1

    def test_heavy_hitter_le(self):
        hh1 = HeavyHitter(item="A", count=10)
        hh2 = HeavyHitter(item="B", count=10)
        hh3 = HeavyHitter(item="C", count=20)
        assert hh1 <= hh2
        assert hh1 <= hh3
        assert not hh3 <= hh1

    def test_heavy_hitter_ge(self):
        hh1 = HeavyHitter(item="A", count=20)
        hh2 = HeavyHitter(item="B", count=20)
        hh3 = HeavyHitter(item="C", count=10)
        assert hh1 >= hh2
        assert hh1 >= hh3
        assert not hh3 >= hh1
