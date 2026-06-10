import pytest

from solocoder_py.heavy_hitter import HeavyHitterDetector, InvalidKError


class TestEdgeCaseKEqualsCapacity:
    def test_k_equals_capacity_exact_fit(self):
        detector = HeavyHitterDetector(capacity=5)
        for i in range(5):
            detector.record(f"item{i}", count=i + 1)
        top5 = detector.get_top_k(5)
        assert len(top5) == 5
        assert detector.size == 5

    def test_k_equals_capacity_with_eviction(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("A", count=100)
        detector.record("B", count=80)
        detector.record("C", count=60)
        detector.record("D", count=200)
        top3 = detector.get_top_k(3)
        assert len(top3) == 3
        assert top3[0].item == "D"

    def test_k_equals_capacity_all_same_frequency(self):
        detector = HeavyHitterDetector(capacity=3)
        for item in ["A", "B", "C"]:
            for _ in range(10):
                detector.record(item)
        top3 = detector.get_top_k(3)
        assert len(top3) == 3
        for hh in top3:
            assert hh.count >= 10


class TestEdgeCaseAllSameFrequency:
    def test_all_same_frequency_within_capacity(self):
        detector = HeavyHitterDetector(capacity=10)
        items = ["A", "B", "C", "D", "E"]
        for item in items:
            for _ in range(50):
                detector.record(item)
        assert detector.size == 5
        top5 = detector.get_top_k(5)
        assert len(top5) == 5
        counts = [hh.count for hh in top5]
        for c in counts:
            assert c >= 50

    def test_all_same_frequency_exceeds_capacity(self):
        detector = HeavyHitterDetector(capacity=3)
        items = ["A", "B", "C", "D", "E", "F"]
        for item in items:
            for _ in range(10):
                detector.record(item)
        assert detector.size == 3
        tracked_items = [hh.item for hh in detector.get_all_tracked()]
        assert all(item in items for item in tracked_items)
        for hh in detector.get_all_tracked():
            assert hh.count >= 10

    def test_all_same_frequency_skewed_insertion_order(self):
        detector = HeavyHitterDetector(capacity=3)
        items = ["A", "B", "C", "D", "E"]
        for item in items:
            for _ in range(10):
                detector.record(item)
        tracked = detector.get_all_tracked()
        assert len(tracked) == 3
        for hh in tracked:
            assert hh.item in items


class TestEdgeCaseDataExceedsCapacity:
    def test_large_data_volume_small_capacity(self):
        detector = HeavyHitterDetector(capacity=10)
        true_counts = {"A": 1000, "B": 800, "C": 500}
        for item, count in true_counts.items():
            for _ in range(count):
                detector.record(item)
        for i in range(5000):
            detector.record(f"rare_{i}")
        assert detector.size == 10
        assert detector.total_items_processed == 7300
        top3 = detector.get_top_k(3)
        assert top3[0].item == "A"
        assert top3[0].count >= 1000

    def test_high_eviction_rate(self):
        detector = HeavyHitterDetector(capacity=5)
        num_unique = 10000
        for i in range(num_unique):
            detector.record(f"item_{i}")
        assert detector.size == 5
        assert detector.evicted_count >= 0
        assert detector.total_items_processed == num_unique

    def test_heavy_hitters_emerge_from_noise(self):
        detector = HeavyHitterDetector(capacity=20)
        for _ in range(10000):
            detector.record("HOT1")
        for _ in range(8000):
            detector.record("HOT2")
        for _ in range(5000):
            detector.record("HOT3")
        for i in range(50000):
            detector.record(f"noise_{i}")
        top5 = detector.get_top_k(5)
        top_items = [hh.item for hh in top5[:3]]
        assert "HOT1" in top_items
        assert "HOT2" in top_items
        assert "HOT3" in top_items

    def test_eviction_count_tracking(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("A", count=10)
        detector.record("B", count=10)
        detector.record("C", count=10)
        initial_evicted = detector.evicted_count
        detector.record("D", count=20)
        assert detector.evicted_count == initial_evicted + 1
        detector.record("E", count=30)
        assert detector.evicted_count == initial_evicted + 2

    def test_item_replaces_itself_no_eviction(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("A", count=5)
        detector.record("B", count=5)
        detector.record("C", count=5)
        evicted_before = detector.evicted_count
        detector.record("A", count=5)
        assert detector.evicted_count == evicted_before
        assert detector.estimate_count("A") >= 10


class TestEdgeCaseBoundaryValues:
    def test_capacity_one(self):
        detector = HeavyHitterDetector(capacity=1)
        detector.record("A", count=10)
        assert detector.size == 1
        assert detector.contains("A")
        detector.record("B", count=20)
        assert detector.size == 1
        assert detector.estimate_count("B") >= 20
        assert detector.evicted_count == 1

    def test_single_item_repeated(self):
        detector = HeavyHitterDetector(capacity=10)
        for _ in range(10000):
            detector.record("only_item")
        assert detector.size == 1
        assert detector.estimate_count("only_item") >= 10000
        assert detector.evicted_count == 0

    def test_item_not_tracked_but_cms_has_data(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("A", count=100)
        detector.record("B", count=100)
        detector.record("C", count=100)
        detector.record("D", count=50)
        assert detector.contains("D") is False
        assert detector.estimate_count("D") >= 50

    def test_zero_evictions_when_within_capacity(self):
        detector = HeavyHitterDetector(capacity=100)
        for i in range(50):
            detector.record(f"item_{i}")
        assert detector.evicted_count == 0
        assert detector.size == 50


class TestEdgeCaseApproximationQuality:
    def test_estimate_is_lower_bound(self):
        detector = HeavyHitterDetector(capacity=10, epsilon=0.001, delta=0.99)
        true_counts = {}
        for i in range(20):
            count = (i + 1) * 10
            true_counts[f"item_{i}"] = count
            detector.record(f"item_{i}", count=count)
        for item, true_count in true_counts.items():
            est = detector.estimate_count(item)
            assert est >= true_count, f"{item}: estimate {est} < true {true_count}"

    def test_top_k_order_maintained(self):
        detector = HeavyHitterDetector(capacity=10)
        for i in range(10, 0, -1):
            detector.record(f"rank_{11 - i}", count=i * 100)
        top10 = detector.get_top_k(10)
        for i in range(9):
            assert top10[i].count >= top10[i + 1].count

    def test_evicted_item_still_queryable(self):
        detector = HeavyHitterDetector(capacity=2)
        detector.record("X", count=10)
        detector.record("Y", count=20)
        detector.record("Z", count=30)
        assert detector.contains("X") is False
        est_x = detector.estimate_count("X")
        assert est_x >= 10
        lower = detector.lower_bound("X")
        upper = detector.upper_bound("X")
        assert lower <= est_x <= upper


class TestEdgeCaseEmptyState:
    def test_get_top_k_empty_detector(self):
        detector = HeavyHitterDetector(capacity=5)
        top3 = detector.get_top_k(3)
        assert len(top3) == 0

    def test_estimate_on_empty_detector(self):
        detector = HeavyHitterDetector(capacity=5)
        assert detector.estimate_count("anything") == 0
        assert detector.lower_bound("anything") == 0
        assert detector.upper_bound("anything") == 0

    def test_contains_on_empty_detector(self):
        detector = HeavyHitterDetector(capacity=5)
        assert detector.contains("anything") is False

    def test_get_all_tracked_empty(self):
        detector = HeavyHitterDetector(capacity=5)
        all_tracked = detector.get_all_tracked()
        assert len(all_tracked) == 0


class TestEdgeCaseLargeCountValues:
    def test_large_single_count(self):
        detector = HeavyHitterDetector(capacity=5)
        detector.record("big", count=1000000)
        assert detector.estimate_count("big") >= 1000000
        assert detector.total_items_processed == 1000000

    def test_many_small_counts(self):
        detector = HeavyHitterDetector(capacity=5)
        total = 0
        for i in range(100000):
            detector.record(f"item_{i % 10}", count=1)
            total += 1
        assert detector.total_items_processed == total
        top1 = detector.get_top_k(1)
        assert top1[0].count >= 10000
