import math
import statistics

import pytest

from solocoder_py.streamstats import StreamStats


class TestMeanVarianceWithStandardLibrary:
    def test_incremental_sequence_mean_matches_statistics(self):
        data = list(range(1, 11))
        s = StreamStats()
        for v in data:
            s.add(v)
        assert s.count == 10
        assert math.isclose(s.mean, statistics.mean(data))
        assert math.isclose(s.variance_sample, statistics.variance(data))
        assert math.isclose(s.variance_population, statistics.pvariance(data))

    def test_incremental_sequence_stddev(self):
        data = list(range(1, 11))
        s = StreamStats()
        for v in data:
            s.add(v)
        assert math.isclose(s.stddev_sample, statistics.stdev(data))
        assert math.isclose(s.stddev_population, statistics.pstdev(data))

    def test_floating_point_sequence(self):
        data = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
        s = StreamStats()
        for v in data:
            s.add(v)
        assert s.count == 10
        assert math.isclose(s.mean, statistics.mean(data))
        assert math.isclose(s.variance_sample, statistics.variance(data))

    def test_negative_values(self):
        data = [-5, -3, -1, 0, 1, 3, 5]
        s = StreamStats()
        for v in data:
            s.add(v)
        assert s.count == 7
        assert math.isclose(s.mean, statistics.mean(data), abs_tol=1e-14)
        assert math.isclose(s.variance_sample, statistics.variance(data))


class TestNormalDistributionSkewKurtosis:
    def test_normal_distribution_skewness_near_zero(self):
        import random
        rng = random.Random(42)
        s = StreamStats()
        for _ in range(50000):
            s.add(rng.gauss(0, 1))
        assert abs(s.skewness) < 0.1

    def test_normal_distribution_kurtosis_near_zero(self):
        import random
        rng = random.Random(123)
        s = StreamStats()
        for _ in range(50000):
            s.add(rng.gauss(10, 2))
        assert abs(s.kurtosis) < 0.1


class TestFluctuatingSequenceOnlineUpdate:
    def test_online_update_step_by_step(self):
        data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
        s = StreamStats()
        for i, v in enumerate(data, 1):
            s.add(v)
            assert s.count == i
            expected_mean = statistics.mean(data[:i])
            assert math.isclose(s.mean, expected_mean)
            if i >= 2:
                expected_var = statistics.variance(data[:i])
                assert math.isclose(s.variance_sample, expected_var)

    def test_add_all_batch(self):
        data = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        s1 = StreamStats()
        s1.add_all(data)
        s2 = StreamStats()
        for v in data:
            s2.add(v)
        assert s1.count == s2.count
        assert math.isclose(s1.mean, s2.mean)
        assert math.isclose(s1.variance_sample, s2.variance_sample)
        assert math.isclose(s1.skewness, s2.skewness, abs_tol=1e-12)
        assert math.isclose(s1.kurtosis, s2.kurtosis, abs_tol=1e-12)


class TestMergeTwoOperators:
    def test_merge_matches_full_computation(self):
        data_a = [1, 2, 3, 4, 5]
        data_b = [6, 7, 8, 9, 10]
        a = StreamStats()
        a.add_all(data_a)
        b = StreamStats()
        b.add_all(data_b)
        full = StreamStats()
        full.add_all(data_a + data_b)
        merged = a.copy()
        merged.merge(b)
        assert merged.count == full.count
        assert math.isclose(merged.mean, full.mean)
        assert math.isclose(merged.variance_sample, full.variance_sample)
        assert math.isclose(merged.variance_population, full.variance_population)
        assert math.isclose(merged.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(merged.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)

    def test_merge_operator_plus(self):
        data_a = [1, 3, 5, 7]
        data_b = [2, 4, 6, 8]
        a = StreamStats()
        a.add_all(data_a)
        b = StreamStats()
        b.add_all(data_b)
        full = StreamStats()
        full.add_all(data_a + data_b)
        merged = a + b
        assert merged.count == full.count
        assert math.isclose(merged.mean, full.mean)
        assert math.isclose(merged.variance_sample, full.variance_sample)

    def test_merge_inplace(self):
        data_a = [10, 20, 30]
        data_b = [40, 50, 60, 70]
        a = StreamStats()
        a.add_all(data_a)
        b = StreamStats()
        b.add_all(data_b)
        full = StreamStats()
        full.add_all(data_a + data_b)
        a += b
        assert a.count == full.count
        assert math.isclose(a.mean, full.mean)
        assert math.isclose(a.variance_sample, full.variance_sample)
        assert math.isclose(a.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(a.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)

    def test_merge_multiple_batches(self):
        batches = [
            [1, 2],
            [3, 4, 5],
            [6],
            [7, 8, 9, 10],
        ]
        all_data = []
        result = StreamStats()
        for batch in batches:
            all_data.extend(batch)
            s = StreamStats()
            s.add_all(batch)
            result.merge(s)
        full = StreamStats()
        full.add_all(all_data)
        assert result.count == full.count
        assert math.isclose(result.mean, full.mean)
        assert math.isclose(result.variance_sample, full.variance_sample)
        assert math.isclose(result.skewness, full.skewness, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(result.kurtosis, full.kurtosis, rel_tol=1e-9, abs_tol=1e-9)
