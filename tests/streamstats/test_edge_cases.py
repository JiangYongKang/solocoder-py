import math

import pytest

from solocoder_py.streamstats import StreamStats, StatsResult


def _exact_moments(mpmath_mod, data):
    n = len(data)
    xs = [mpmath_mod.mpf(x) for x in data]
    mean = sum(xs) / n
    m2 = sum((x - mean) ** 2 for x in xs)
    m3 = sum((x - mean) ** 3 for x in xs)
    m4 = sum((x - mean) ** 4 for x in xs)
    return {"n": n, "mean": float(mean), "m2": float(m2), "m3": float(m3), "m4": float(m4)}


def _assert_moments_close(s, exact, m2_rtol, m3_rtol, m4_rtol):
    assert s._n == exact["n"]
    assert math.isclose(s._mean, exact["mean"], rel_tol=1e-14)
    if exact["m2"] != 0:
        assert math.isclose(s._m2, exact["m2"], rel_tol=m2_rtol)
    else:
        assert abs(s._m2) < 1e-6
    if exact["m3"] != 0:
        assert math.isclose(s._m3, exact["m3"], rel_tol=m3_rtol)
    else:
        assert abs(s._m3) < 1e-3
    if exact["m4"] != 0:
        assert math.isclose(s._m4, exact["m4"], rel_tol=m4_rtol)
    else:
        assert abs(s._m4) < 1e-6


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
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)

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
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)

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
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)


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


class TestMergeDirectionIndependence:
    def test_merge_direction_bit_identical_100_to_10(self):
        self._check_direction(100, 10)

    def test_merge_direction_bit_identical_1000_to_1(self):
        self._check_direction(1000, 1)

    def test_merge_direction_bit_identical_10000_to_3(self):
        self._check_direction(10000, 3)

    def test_merge_direction_bit_identical_100k_to_1(self):
        self._check_direction(100000, 1)

    def test_merge_direction_bit_identical_1M_to_1(self):
        self._check_direction(1000000, 1)

    def _check_direction(self, n_large, n_small):
        large_data = list(range(1, n_large + 1))
        small_data = [float(n_large + i * 100) for i in range(n_small)]

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        fwd = large_s.copy()
        fwd.merge(small_s)

        rev = small_s.copy()
        rev.merge(large_s)

        assert fwd._mean == rev._mean, (
            f"mean differs: fwd={fwd._mean!r}, rev={rev._mean!r}"
        )
        assert fwd._m2 == rev._m2, (
            f"M2 differs: fwd={fwd._m2!r}, rev={rev._m2!r}"
        )
        assert fwd._m3 == rev._m3, (
            f"M3 differs: fwd={fwd._m3!r}, rev={rev._m3!r}"
        )
        assert fwd._m4 == rev._m4, (
            f"M4 differs: fwd={fwd._m4!r}, rev={rev._m4!r}"
        )


class TestExtremeBatchRatioMerge:
    def test_100k_to_1_near_mean(self):
        mpmath = pytest.importorskip("mpmath")
        mpmath.mp.dps = 50

        large_data = list(range(1, 100001))
        small_data = [99999.0]
        all_data = large_data + small_data

        exact = _exact_moments(mpmath, all_data)

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        merged = large_s.copy()
        merged.merge(small_s)

        _assert_moments_close(merged, exact, m2_rtol=1e-13, m3_rtol=1e-12, m4_rtol=1e-12)

    def test_100k_to_2_symmetric_outliers(self):
        mpmath = pytest.importorskip("mpmath")
        mpmath.mp.dps = 50

        large_data = list(range(1, 100001))
        small_data = [-50000.0, 50000.0]
        all_data = large_data + small_data

        exact = _exact_moments(mpmath, all_data)

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        merged = large_s.copy()
        merged.merge(small_s)

        _assert_moments_close(merged, exact, m2_rtol=1e-13, m3_rtol=1e-12, m4_rtol=1e-12)

    def test_100k_to_1_extreme_delta(self):
        mpmath = pytest.importorskip("mpmath")
        mpmath.mp.dps = 50

        large_data = list(range(1, 100001))
        small_data = [1e8]
        all_data = large_data + small_data

        exact = _exact_moments(mpmath, all_data)

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        merged = large_s.copy()
        merged.merge(small_s)

        _assert_moments_close(merged, exact, m2_rtol=1e-13, m3_rtol=1e-12, m4_rtol=1e-12)

    def test_1M_to_1_extreme_delta(self):
        mpmath = pytest.importorskip("mpmath")
        mpmath.mp.dps = 50

        large_data = list(range(1, 1000001))
        small_data = [1e8]
        all_data = large_data + small_data

        exact = _exact_moments(mpmath, all_data)

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        merged = large_s.copy()
        merged.merge(small_s)

        _assert_moments_close(merged, exact, m2_rtol=1e-13, m3_rtol=1e-12, m4_rtol=1e-12)

    def test_1M_to_1_near_mean(self):
        mpmath = pytest.importorskip("mpmath")
        mpmath.mp.dps = 50

        large_data = list(range(1, 1000001))
        small_data = [500000.0]
        all_data = large_data + small_data

        exact = _exact_moments(mpmath, all_data)

        large_s = StreamStats()
        large_s.add_all(large_data)
        small_s = StreamStats()
        small_s.add_all(small_data)

        merged = large_s.copy()
        merged.merge(small_s)

        _assert_moments_close(merged, exact, m2_rtol=1e-13, m3_rtol=1e-4, m4_rtol=1e-12)
