import math

import pytest

from solocoder_py.streamstats import (
    InvalidValueError,
    StreamStats,
    StreamStatsError,
)


class TestNaNInfIsolation:
    def test_nan_raises_invalid_value_error(self):
        s = StreamStats()
        s.add(1.0)
        s.add(2.0)
        with pytest.raises(InvalidValueError):
            s.add(float("nan"))

    def test_positive_inf_raises_invalid_value_error(self):
        s = StreamStats()
        with pytest.raises(InvalidValueError):
            s.add(float("inf"))

    def test_negative_inf_raises_invalid_value_error(self):
        s = StreamStats()
        with pytest.raises(InvalidValueError):
            s.add(float("-inf"))

    def test_invalid_value_does_not_corrupt_state(self):
        s = StreamStats()
        s.add(1.0)
        s.add(2.0)
        count_before = s.count
        mean_before = s.mean
        try:
            s.add(float("nan"))
        except InvalidValueError:
            pass
        assert s.count == count_before
        assert math.isclose(s.mean, mean_before)

    def test_boolean_rejected(self):
        s = StreamStats()
        with pytest.raises(InvalidValueError):
            s.add(True)
        with pytest.raises(InvalidValueError):
            s.add(False)
        assert s.count == 0

    def test_invalid_value_error_contains_value(self):
        s = StreamStats()
        with pytest.raises(InvalidValueError) as exc_info:
            s.add(float("nan"))
        assert math.isnan(exc_info.value.value)


class TestMergeWithEmpty:
    def test_merge_into_empty(self):
        empty = StreamStats()
        data = StreamStats()
        data.add_all([1, 2, 3, 4, 5])
        empty.merge(data)
        assert empty.count == 5
        assert math.isclose(empty.mean, 3.0)

    def test_merge_empty_into_nonempty(self):
        s = StreamStats()
        s.add_all([10, 20, 30])
        empty = StreamStats()
        count_before = s.count
        mean_before = s.mean
        s.merge(empty)
        assert s.count == count_before
        assert math.isclose(s.mean, mean_before)

    def test_merge_two_empty(self):
        a = StreamStats()
        b = StreamStats()
        a.merge(b)
        assert a.count == 0
        assert a.mean is None

    def test_merge_none_raises(self):
        s = StreamStats()
        with pytest.raises(StreamStatsError):
            s.merge(None)


class TestNumericalStability:
    def test_m2_never_negative_after_many_values(self):
        import random
        rng = random.Random(99)
        s = StreamStats()
        for _ in range(10000):
            s.add(rng.gauss(0, 1))
        assert s._m2 >= 0.0

    def test_m2_nonnegative_with_constant_values(self):
        s = StreamStats()
        for _ in range(1000):
            s.add(7.5)
        assert s._m2 >= 0.0
        assert math.isclose(s._m2, 0.0, abs_tol=1e-10)

    def test_merged_m2_never_negative(self):
        import random
        rng = random.Random(42)
        a = StreamStats()
        b = StreamStats()
        for _ in range(5000):
            a.add(rng.gauss(10, 2))
            b.add(rng.gauss(10, 2))
        merged = a + b
        assert merged._m2 >= 0.0


class TestExtremeValuesPrecision:
    def test_very_large_values_mean(self):
        s = StreamStats()
        s.add(1e15)
        s.add(1e15 + 1)
        s.add(1e15 + 2)
        expected = (1e15 + 1e15 + 1 + 1e15 + 2) / 3
        assert math.isclose(s.mean, expected, rel_tol=1e-10)

    def test_very_small_values_variance(self):
        s = StreamStats()
        s.add(1e-10)
        s.add(2e-10)
        s.add(3e-10)
        mean = s.mean
        var_expected = ((1e-10 - mean) ** 2 + (2e-10 - mean) ** 2 + (3e-10 - mean) ** 2) / 2
        assert math.isclose(s.variance_sample, var_expected, rel_tol=1e-10)

    def test_mixed_extreme_values(self):
        s = StreamStats()
        s.add(1e15)
        s.add(1e-10)
        s.add(-1e15)
        s.add(-1e-10)
        full = [1e15, 1e-10, -1e15, -1e-10]
        expected_mean = sum(full) / len(full)
        expected_var = sum((x - expected_mean) ** 2 for x in full) / (len(full) - 1)
        assert math.isclose(s.mean, expected_mean, rel_tol=1e-10)
        assert math.isclose(s.variance_sample, expected_var, rel_tol=1e-8)

    def test_large_number_of_small_values(self):
        s = StreamStats()
        n = 10000
        for i in range(n):
            s.add(i * 1e-10)
        expected_mean = (n - 1) * 1e-10 / 2
        assert math.isclose(s.mean, expected_mean, rel_tol=1e-6)
        assert s._m2 >= 0.0
