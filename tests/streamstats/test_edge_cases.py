import math

import pytest

from solocoder_py.streamstats import StreamStats, StatsResult


class TestEmptyStats:
    def test_empty_count_is_zero(self, empty_stats):
        assert empty_stats.count == 0

    def test_empty_mean_is_none(self, empty_stats):
        assert empty_stats.mean is None

    def test_empty_variance_is_none(self, empty_stats):
        assert empty_stats.variance is None
        assert empty_stats.variance_population is None
        assert empty_stats.variance_sample is None

    def test_empty_stddev_is_none(self, empty_stats):
        assert empty_stats.stddev_population is None
        assert empty_stats.stddev_sample is None

    def test_empty_skewness_is_none(self, empty_stats):
        assert empty_stats.skewness is None

    def test_empty_kurtosis_is_none(self, empty_stats):
        assert empty_stats.kurtosis is None

    def test_empty_get_result(self, empty_stats):
        r = empty_stats.get_result()
        assert isinstance(r, StatsResult)
        assert r.count == 0
        assert r.mean is None
        assert r.variance is None
        assert r.skewness is None
        assert r.kurtosis is None


class TestSingleDataPoint:
    def test_single_count(self):
        s = StreamStats()
        s.add(42.0)
        assert s.count == 1

    def test_single_mean_equals_value(self):
        s = StreamStats()
        s.add(42.0)
        assert math.isclose(s.mean, 42.0)

    def test_single_variance_is_none(self):
        s = StreamStats()
        s.add(42.0)
        assert s.variance_sample is None

    def test_single_population_variance_is_zero(self):
        s = StreamStats()
        s.add(42.0)
        assert math.isclose(s.variance_population, 0.0)

    def test_single_skewness_is_none(self):
        s = StreamStats()
        s.add(42.0)
        assert s.skewness is None

    def test_single_kurtosis_is_none(self):
        s = StreamStats()
        s.add(42.0)
        assert s.kurtosis is None


class TestTwoDataPoints:
    def test_two_count(self):
        s = StreamStats()
        s.add(1.0)
        s.add(3.0)
        assert s.count == 2

    def test_two_mean(self):
        s = StreamStats()
        s.add(1.0)
        s.add(3.0)
        assert math.isclose(s.mean, 2.0)

    def test_two_variance(self):
        s = StreamStats()
        s.add(1.0)
        s.add(3.0)
        assert math.isclose(s.variance_sample, 2.0)
        assert math.isclose(s.variance_population, 1.0)

    def test_two_skewness_is_none(self):
        s = StreamStats()
        s.add(1.0)
        s.add(3.0)
        assert s.skewness is None

    def test_two_kurtosis_is_none(self):
        s = StreamStats()
        s.add(1.0)
        s.add(3.0)
        assert s.kurtosis is None


class TestAllIdenticalValues:
    def test_all_same_variance_zero(self):
        s = StreamStats()
        for _ in range(100):
            s.add(5.0)
        assert s.count == 100
        assert math.isclose(s.mean, 5.0)
        assert math.isclose(s.variance_sample, 0.0)
        assert math.isclose(s.variance_population, 0.0)

    def test_all_same_skewness(self):
        s = StreamStats()
        for _ in range(50):
            s.add(10.0)
        assert s.skewness is None

    def test_all_same_kurtosis(self):
        s = StreamStats()
        for _ in range(50):
            s.add(10.0)
        assert s.kurtosis is None


class TestUnequalBatchSizesMerge:
    def test_small_batch_merged_with_large(self):
        small_data = [1.0, 2.0]
        large_data = list(range(10, 10010))
        small = StreamStats()
        small.add_all(small_data)
        large = StreamStats()
        large.add_all(large_data)
        full = StreamStats()
        full.add_all(small_data + large_data)
        merged = large.copy()
        merged.merge(small)
        assert merged.count == full.count
        assert math.isclose(merged.mean, full.mean)
        assert math.isclose(merged.variance_sample, full.variance_sample, rel_tol=1e-10)
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-3, abs_tol=1e-3)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-3, abs_tol=1e-3)

    def test_large_batch_merged_with_small(self):
        small_data = [100.0, 200.0, 300.0]
        large_data = list(range(1, 5001))
        small = StreamStats()
        small.add_all(small_data)
        large = StreamStats()
        large.add_all(large_data)
        full = StreamStats()
        full.add_all(large_data + small_data)
        merged = small.copy()
        merged.merge(large)
        assert merged.count == full.count
        assert math.isclose(merged.mean, full.mean)
        assert math.isclose(merged.variance_sample, full.variance_sample, rel_tol=1e-10)
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-3, abs_tol=1e-3)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-3, abs_tol=1e-3)

    def test_one_element_merged_with_many(self):
        one_data = [999.0]
        many_data = list(range(1, 1001))
        one = StreamStats()
        one.add_all(one_data)
        many = StreamStats()
        many.add_all(many_data)
        full = StreamStats()
        full.add_all(many_data + one_data)
        merged = many.copy()
        merged.merge(one)
        assert merged.count == full.count
        assert math.isclose(merged.mean, full.mean)
        assert math.isclose(merged.variance_sample, full.variance_sample, rel_tol=1e-10)


class TestCopy:
    def test_copy_independent(self):
        s1 = StreamStats()
        s1.add_all([1, 2, 3])
        s2 = s1.copy()
        s2.add(100)
        assert s1.count == 3
        assert s2.count == 4
        assert not math.isclose(s1.mean, s2.mean)

    def test_copy_preserves_state(self):
        s1 = StreamStats()
        s1.add_all([5, 10, 15, 20, 25])
        s2 = s1.copy()
        assert s1.count == s2.count
        assert math.isclose(s1.mean, s2.mean)
        assert math.isclose(s1.variance_sample, s2.variance_sample)
        assert math.isclose(s1.skewness, s2.skewness, abs_tol=1e-12)
        assert math.isclose(s1.kurtosis, s2.kurtosis, abs_tol=1e-12)
