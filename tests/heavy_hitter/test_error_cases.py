import pytest

from solocoder_py.heavy_hitter import (
    CountMinSketch,
    HeavyHitterDetector,
    InvalidCapacityError,
    InvalidDeltaError,
    InvalidEpsilonError,
    InvalidKError,
)


class TestInvalidKErrorCases:
    def test_k_zero_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=5)
        with pytest.raises(InvalidKError, match="k must be a positive integer"):
            detector.get_top_k(0)

    def test_k_negative_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=5)
        with pytest.raises(InvalidKError, match="k must be a positive integer"):
            detector.get_top_k(-5)

    def test_k_exceeds_capacity_raises(self):
        detector = HeavyHitterDetector(capacity=5)
        detector.record("A", count=5)
        with pytest.raises(InvalidKError, match="cannot exceed capacity"):
            detector.get_top_k(10)

    def test_k_equals_capacity_plus_one_raises(self):
        detector = HeavyHitterDetector(capacity=5)
        detector.record("A", count=5)
        with pytest.raises(InvalidKError, match="cannot exceed capacity"):
            detector.get_top_k(6)

    def test_k_exceeds_capacity_message_format(self):
        detector = HeavyHitterDetector(capacity=3)
        with pytest.raises(InvalidKError) as exc_info:
            detector.get_top_k(10)
        assert "k (10) cannot exceed capacity (3)" in str(exc_info.value)


class TestInvalidCapacityErrorCases:
    def test_zero_capacity_raises(self):
        with pytest.raises(InvalidCapacityError) as exc_info:
            HeavyHitterDetector(capacity=0)
        assert "capacity must be a positive integer" in str(exc_info.value)

    def test_negative_capacity_raises(self):
        with pytest.raises(InvalidCapacityError) as exc_info:
            HeavyHitterDetector(capacity=-1)
        assert "capacity must be a positive integer" in str(exc_info.value)

    def test_large_negative_capacity_raises(self):
        with pytest.raises(InvalidCapacityError):
            HeavyHitterDetector(capacity=-1000)


class TestInvalidEpsilonErrorCases:
    def test_epsilon_zero_raises(self):
        with pytest.raises(InvalidEpsilonError) as exc_info:
            CountMinSketch(epsilon=0)
        assert "epsilon must be between 0 and 1" in str(exc_info.value)

    def test_epsilon_one_raises(self):
        with pytest.raises(InvalidEpsilonError):
            CountMinSketch(epsilon=1)

    def test_epsilon_negative_raises(self):
        with pytest.raises(InvalidEpsilonError):
            CountMinSketch(epsilon=-0.001)

    def test_epsilon_greater_than_one_raises(self):
        with pytest.raises(InvalidEpsilonError):
            CountMinSketch(epsilon=1.5)

    def test_epsilon_via_detector_raises(self):
        with pytest.raises(InvalidEpsilonError):
            HeavyHitterDetector(capacity=5, epsilon=0)


class TestInvalidDeltaErrorCases:
    def test_delta_zero_raises(self):
        with pytest.raises(InvalidDeltaError) as exc_info:
            CountMinSketch(delta=0)
        assert "delta must be between 0 and 1" in str(exc_info.value)

    def test_delta_one_raises(self):
        with pytest.raises(InvalidDeltaError):
            CountMinSketch(delta=1)

    def test_delta_negative_raises(self):
        with pytest.raises(InvalidDeltaError):
            CountMinSketch(delta=-0.5)

    def test_delta_greater_than_one_raises(self):
        with pytest.raises(InvalidDeltaError):
            CountMinSketch(delta=2.0)

    def test_delta_via_detector_raises(self):
        with pytest.raises(InvalidDeltaError):
            HeavyHitterDetector(capacity=5, delta=1)


class TestInvalidCountErrorCases:
    def test_record_zero_count_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        with pytest.raises(ValueError) as exc_info:
            detector.record("A", count=0)
        assert "count must be positive" in str(exc_info.value)

    def test_record_negative_count_raises(self):
        detector = HeavyHitterDetector(capacity=10)
        with pytest.raises(ValueError):
            detector.record("A", count=-10)

    def test_cms_add_zero_count_raises(self):
        cms = CountMinSketch()
        with pytest.raises(ValueError):
            cms.add("A", count=0)

    def test_cms_add_negative_count_raises(self):
        cms = CountMinSketch()
        with pytest.raises(ValueError):
            cms.add("A", count=-5)


class TestInvalidMergeCases:
    def test_merge_detectors_different_capacity_raises(self):
        detector1 = HeavyHitterDetector(capacity=5)
        detector2 = HeavyHitterDetector(capacity=10)
        detector1.record("A", count=10)
        detector2.record("B", count=20)
        with pytest.raises(ValueError) as exc_info:
            detector1.merge(detector2)
        assert "different capacities" in str(exc_info.value)

    def test_merge_cms_different_dimensions_raises(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.95)
        with pytest.raises(ValueError) as exc_info:
            cms1.merge(cms2)
        assert "different epsilon/delta" in str(exc_info.value)

    def test_merge_cms_different_epsilon_raises(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.02, delta=0.9)
        with pytest.raises(ValueError) as exc_info:
            cms1.merge(cms2)
        assert "different epsilon/delta" in str(exc_info.value)

    def test_merge_cms_different_delta_raises(self):
        cms1 = CountMinSketch(epsilon=0.01, delta=0.9)
        cms2 = CountMinSketch(epsilon=0.01, delta=0.95)
        with pytest.raises(ValueError):
            cms1.merge(cms2)


class TestQueryNonExistentItemCases:
    def test_estimate_nonexistent_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=100)
        est = detector.estimate_count("nonexistent")
        assert est >= 0

    def test_contains_nonexistent_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=100)
        assert detector.contains("nonexistent") is False

    def test_lower_bound_nonexistent_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=100)
        lower = detector.lower_bound("nonexistent")
        assert lower >= 0

    def test_upper_bound_nonexistent_item(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=100)
        upper = detector.upper_bound("nonexistent")
        assert upper >= 0

    def test_estimate_after_eviction(self):
        detector = HeavyHitterDetector(capacity=2)
        detector.record("A", count=10)
        detector.record("B", count=20)
        detector.record("C", count=30)
        assert detector.contains("A") is False
        est = detector.estimate_count("A")
        assert est >= 10

    def test_cms_estimate_nonexistent(self):
        cms = CountMinSketch()
        cms.add("A", count=10)
        assert cms.estimate("nonexistent") >= 0


class TestExceptionHierarchy:
    def test_invalid_capacity_is_heavy_hitter_error(self):
        assert issubclass(InvalidCapacityError, Exception)

    def test_invalid_k_is_heavy_hitter_error(self):
        assert issubclass(InvalidKError, Exception)

    def test_invalid_epsilon_is_heavy_hitter_error(self):
        assert issubclass(InvalidEpsilonError, Exception)

    def test_invalid_delta_is_heavy_hitter_error(self):
        assert issubclass(InvalidDeltaError, Exception)


class TestEmptyStateQueries:
    def test_get_top_k_with_k_greater_than_size(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=5)
        top5 = detector.get_top_k(5)
        assert len(top5) == 1

    def test_get_all_tracked_empty(self):
        detector = HeavyHitterDetector(capacity=5)
        all_tracked = detector.get_all_tracked()
        assert isinstance(all_tracked, list)
        assert len(all_tracked) == 0

    def test_estimate_after_clear(self):
        detector = HeavyHitterDetector(capacity=5)
        detector.record("A", count=100)
        detector.clear()
        assert detector.estimate_count("A") == 0
        assert detector.contains("A") is False


class TestBoundaryKValues:
    def test_k_one(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=100)
        detector.record("B", count=50)
        top1 = detector.get_top_k(1)
        assert len(top1) == 1
        assert top1[0].item == "A"

    def test_k_equals_capacity(self):
        detector = HeavyHitterDetector(capacity=3)
        detector.record("A", count=30)
        detector.record("B", count=20)
        detector.record("C", count=10)
        top3 = detector.get_top_k(3)
        assert len(top3) == 3

    def test_k_greater_than_actual_size_but_less_than_capacity(self):
        detector = HeavyHitterDetector(capacity=10)
        detector.record("A", count=10)
        detector.record("B", count=20)
        top5 = detector.get_top_k(5)
        assert len(top5) == 2
