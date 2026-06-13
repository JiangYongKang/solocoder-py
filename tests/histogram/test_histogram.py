from __future__ import annotations

import pytest

from solocoder_py.histogram import (
    EmptyHistogramError,
    IncompatibleBoundariesError,
    InvalidBoundariesError,
    InvalidQuantileError,
    StreamingHistogram,
)


class TestInitializationNormalFlows:
    def test_valid_boundaries_initialization(self):
        boundaries = [0, 10, 50, 100, 500, 1000]
        hist = StreamingHistogram(boundaries)
        assert hist.boundaries == boundaries
        assert hist.total_count == 0
        assert hist.underflow_count == 0
        assert hist.overflow_count == 0
        assert hist.bucket_counts == [0, 0, 0, 0, 0]

    def test_two_boundaries_single_bucket(self):
        boundaries = [0, 100]
        hist = StreamingHistogram(boundaries)
        assert hist.boundaries == boundaries
        assert hist.bucket_counts == [0]

    def test_negative_and_zero_boundaries(self):
        boundaries = [-100, -50, 0, 50, 100]
        hist = StreamingHistogram(boundaries)
        assert hist.boundaries == boundaries
        assert hist.bucket_counts == [0, 0, 0, 0]

    def test_float_boundaries(self):
        boundaries = [0.0, 0.5, 1.0, 2.5, 5.0]
        hist = StreamingHistogram(boundaries)
        assert hist.boundaries == boundaries
        assert hist.bucket_counts == [0, 0, 0, 0]


class TestInsertNormalFlows:
    def test_insert_values_into_correct_buckets(self):
        boundaries = [0, 10, 50, 100, 500, 1000]
        hist = StreamingHistogram(boundaries)
        hist.insert(5)
        hist.insert(30)
        hist.insert(75)
        hist.insert(200)
        hist.insert(750)
        assert hist.bucket_counts == [1, 1, 1, 1, 1]
        assert hist.total_count == 5

    def test_insert_boundary_values_left_closed(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(0)
        hist.insert(10)
        hist.insert(50)
        assert hist.bucket_counts == [1, 1, 1]

    def test_insert_boundary_value_max_in_overflow(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(100)
        hist.insert(150)
        assert hist.overflow_count == 2
        assert hist.bucket_counts == [0, 0, 0]

    def test_insert_underflow_values(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(-5)
        hist.insert(-100)
        assert hist.underflow_count == 2

    def test_multiple_inserts_same_bucket(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for _ in range(10):
            hist.insert(25)
        assert hist.bucket_counts[1] == 10
        assert hist.total_count == 10


class TestQuantileNormalFlows:
    def test_p50_even_distribution(self):
        boundaries = [0, 10, 20, 30, 40, 50]
        hist = StreamingHistogram(boundaries)
        for i in range(50):
            hist.insert(i)
        p50 = hist.quantile(50)
        assert 24 <= p50 <= 26

    def test_p90_even_distribution(self):
        boundaries = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        hist = StreamingHistogram(boundaries)
        for i in range(100):
            hist.insert(i)
        p90 = hist.quantile(90)
        assert 89 <= p90 <= 91

    def test_p95_p99_even_distribution(self):
        boundaries = list(range(0, 101, 10))
        hist = StreamingHistogram(boundaries)
        for i in range(100):
            hist.insert(i)
        p95 = hist.quantile(95)
        p99 = hist.quantile(99)
        assert 94 <= p95 <= 96
        assert 98 <= p99 <= 100

    def test_multiple_quantiles(self):
        boundaries = list(range(0, 101, 10))
        hist = StreamingHistogram(boundaries)
        for i in range(100):
            hist.insert(i)
        results = hist.quantiles([50, 90, 95, 99])
        assert len(results) == 4
        assert 49 <= results[0] <= 51
        assert 89 <= results[1] <= 91
        assert 94 <= results[2] <= 96
        assert 98 <= results[3] <= 100

    def test_linear_interpolation_within_bucket(self):
        boundaries = [0, 100]
        hist = StreamingHistogram(boundaries)
        for _ in range(10):
            hist.insert(25)
            hist.insert(75)
        p50 = hist.quantile(50)
        assert p50 == 50.0

    def test_linear_interpolation_exact_boundary(self):
        boundaries = [0, 10, 20, 30]
        hist = StreamingHistogram(boundaries)
        for i in range(10):
            hist.insert(i)
        p33 = hist.quantile(33.33)
        assert 3 <= p33 <= 4


class TestMergeNormalFlows:
    def test_merge_two_histograms_counts(self):
        boundaries = [0, 10, 50, 100]
        h1 = StreamingHistogram(boundaries)
        h2 = StreamingHistogram(boundaries)
        h1.insert(5)
        h1.insert(5)
        h2.insert(30)
        merged = h1.merge(h2)
        assert merged.bucket_counts == [2, 1, 0]
        assert merged.total_count == 3

    def test_merge_preserves_original_histograms(self):
        boundaries = [0, 10, 50, 100]
        h1 = StreamingHistogram(boundaries)
        h2 = StreamingHistogram(boundaries)
        h1.insert(5)
        h2.insert(30)
        h1.merge(h2)
        assert h1.total_count == 1
        assert h2.total_count == 1

    def test_merge_with_underflow_overflow(self):
        boundaries = [0, 10, 50, 100]
        h1 = StreamingHistogram(boundaries)
        h2 = StreamingHistogram(boundaries)
        h1.insert(-5)
        h1.insert(-10)
        h2.insert(150)
        merged = h1.merge(h2)
        assert merged.underflow_count == 2
        assert merged.overflow_count == 1

    def test_merge_quantiles_match_combined_insertion(self):
        boundaries = list(range(0, 101, 10))
        h1 = StreamingHistogram(boundaries)
        h2 = StreamingHistogram(boundaries)
        combined = StreamingHistogram(boundaries)
        for i in range(50):
            h1.insert(i)
            combined.insert(i)
        for i in range(50, 100):
            h2.insert(i)
            combined.insert(i)
        merged = h1.merge(h2)
        for q in [50, 90, 95, 99]:
            assert merged.quantile(q) == pytest.approx(combined.quantile(q), abs=0.01)

    def test_multiple_merges(self):
        boundaries = [0, 10, 20, 30, 40, 50]
        h1 = StreamingHistogram(boundaries)
        h2 = StreamingHistogram(boundaries)
        h3 = StreamingHistogram(boundaries)
        combined = StreamingHistogram(boundaries)
        for i in range(50):
            if i < 17:
                h1.insert(i)
            elif i < 34:
                h2.insert(i)
            else:
                h3.insert(i)
            combined.insert(i)
        merged = h1.merge(h2).merge(h3)
        for q in [25, 50, 75, 90]:
            assert merged.quantile(q) == pytest.approx(combined.quantile(q), abs=0.01)


class TestStatisticsNormalFlows:
    def test_total_count(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for i in range(25):
            hist.insert(i)
        assert hist.total_count == 25

    def test_bucket_counts(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for i in range(10):
            hist.insert(5)
        for i in range(20):
            hist.insert(30)
        assert hist.bucket_counts == [10, 20, 0]

    def test_bucket_percentage(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for i in range(10):
            hist.insert(5)
        for i in range(30):
            hist.insert(30)
        assert hist.get_bucket_percentage(0) == pytest.approx(25.0, abs=0.01)
        assert hist.get_bucket_percentage(1) == pytest.approx(75.0, abs=0.01)

    def test_bucket_percentage_empty(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        assert hist.get_bucket_percentage(0) == 0.0

    def test_reset(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(5)
        hist.insert(30)
        hist.reset()
        assert hist.total_count == 0
        assert hist.bucket_counts == [0, 0, 0]
        assert hist.underflow_count == 0
        assert hist.overflow_count == 0


class TestBoundaryConditions:
    def test_empty_histogram_quantile_raises(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        with pytest.raises(EmptyHistogramError):
            hist.quantile(50)

    def test_quantile_zero_returns_min_boundary(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(25)
        hist.insert(75)
        assert hist.quantile(0) == 0

    def test_quantile_hundred_returns_max_boundary(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(25)
        hist.insert(75)
        assert hist.quantile(100) == 100

    def test_single_bucket_histogram(self):
        boundaries = [0, 100]
        hist = StreamingHistogram(boundaries)
        assert hist.bucket_counts == [0]
        hist.insert(50)
        hist.insert(60)
        assert hist.bucket_counts == [2]

    def test_single_bucket_quantile(self):
        boundaries = [0, 100]
        hist = StreamingHistogram(boundaries)
        for i in range(100):
            hist.insert(i)
        p50 = hist.quantile(50)
        assert 49 <= p50 <= 51

    def test_all_data_same_bucket_quantile(self):
        boundaries = [0, 10, 50, 100, 500]
        hist = StreamingHistogram(boundaries)
        for _ in range(100):
            hist.insert(30)
        p50 = hist.quantile(50)
        assert 10 <= p50 <= 50

    def test_all_data_underflow(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for _ in range(10):
            hist.insert(-5)
        assert hist.underflow_count == 10
        assert hist.total_count == 10
        assert hist.quantile(50) == 0

    def test_all_data_overflow(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        for _ in range(10):
            hist.insert(200)
        assert hist.overflow_count == 10
        assert hist.total_count == 10
        assert hist.quantile(50) == 100

    def test_boundary_value_at_min(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(0)
        assert hist.bucket_counts[0] == 1
        assert hist.underflow_count == 0

    def test_boundary_value_at_max(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(100)
        assert hist.overflow_count == 1
        assert hist.bucket_counts[-1] == 0

    def test_empty_bucket_interpolation_skips(self):
        boundaries = [0, 10, 20, 30, 40, 50]
        hist = StreamingHistogram(boundaries)
        for i in range(10):
            hist.insert(5)
        for i in range(40, 50):
            hist.insert(i)
        p50 = hist.quantile(50)
        assert 35 <= p50 <= 45


class TestErrorBranches:
    def test_boundaries_empty_list_raises(self):
        with pytest.raises(InvalidBoundariesError, match="at least 2 elements"):
            StreamingHistogram([])

    def test_boundaries_single_element_raises(self):
        with pytest.raises(InvalidBoundariesError, match="at least 2 elements"):
            StreamingHistogram([0])

    def test_boundaries_none_raises(self):
        with pytest.raises(InvalidBoundariesError, match="at least 2 elements"):
            StreamingHistogram(None)

    def test_boundaries_not_strictly_increasing_duplicates(self):
        with pytest.raises(InvalidBoundariesError, match="strictly increasing"):
            StreamingHistogram([0, 10, 10, 50])

    def test_boundaries_not_strictly_increasing_decreasing(self):
        with pytest.raises(InvalidBoundariesError, match="strictly increasing"):
            StreamingHistogram([50, 10, 0])

    def test_boundaries_not_strictly_increasing_plateau(self):
        with pytest.raises(InvalidBoundariesError, match="strictly increasing"):
            StreamingHistogram([0, 10, 10, 20])

    def test_merge_different_boundaries_raises(self):
        h1 = StreamingHistogram([0, 10, 50, 100])
        h2 = StreamingHistogram([0, 20, 60, 100])
        with pytest.raises(IncompatibleBoundariesError, match="different bucket boundaries"):
            h1.merge(h2)

    def test_merge_different_length_boundaries_raises(self):
        h1 = StreamingHistogram([0, 10, 100])
        h2 = StreamingHistogram([0, 10, 50, 100])
        with pytest.raises(IncompatibleBoundariesError):
            h1.merge(h2)

    def test_quantile_negative_raises(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(50)
        with pytest.raises(InvalidQuantileError, match="range \\[0, 100\\]"):
            hist.quantile(-1)

    def test_quantile_greater_than_100_raises(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(50)
        with pytest.raises(InvalidQuantileError, match="range \\[0, 100\\]"):
            hist.quantile(101)

    def test_invalid_bucket_index_raises(self):
        boundaries = [0, 10, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(50)
        with pytest.raises(IndexError):
            hist.get_bucket_percentage(5)
        with pytest.raises(IndexError):
            hist.get_bucket_percentage(-1)

    def test_boundaries_with_negative_numbers_valid(self):
        boundaries = [-100, -50, 0, 50, 100]
        hist = StreamingHistogram(boundaries)
        hist.insert(-75)
        hist.insert(-25)
        hist.insert(25)
        hist.insert(75)
        assert hist.bucket_counts == [1, 1, 1, 1]

    def test_boundaries_with_zero_valid(self):
        boundaries = [-10, 0, 10]
        hist = StreamingHistogram(boundaries)
        hist.insert(-5)
        hist.insert(0)
        hist.insert(5)
        assert hist.bucket_counts == [1, 2]
