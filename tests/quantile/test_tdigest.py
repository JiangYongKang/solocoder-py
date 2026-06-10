import math

import pytest

from solocoder_py.quantile import (
    Centroid,
    EmptyDigestError,
    InvalidQuantileError,
    TDigest,
)


class TestTDigestBasic:
    def test_initial_state(self):
        td = TDigest(delta=100.0)
        assert td.is_empty is True
        assert td.total_weight == 0.0
        assert td.delta == 100.0
        assert td.centroids == []

    def test_invalid_delta_raises(self):
        with pytest.raises(ValueError):
            TDigest(delta=0.0)
        with pytest.raises(ValueError):
            TDigest(delta=-1.0)

    def test_add_single_value(self):
        td = TDigest(delta=100.0)
        td.add(42.0)
        assert td.is_empty is False
        assert td.total_weight == 1.0

    def test_add_with_weight(self):
        td = TDigest(delta=100.0)
        td.add(50.0, weight=5.0)
        assert td.total_weight == 5.0

    def test_add_invalid_value_raises(self):
        td = TDigest(delta=100.0)
        with pytest.raises(ValueError):
            td.add(float("nan"))
        with pytest.raises(ValueError):
            td.add(float("inf"))

    def test_add_invalid_weight_raises(self):
        td = TDigest(delta=100.0)
        with pytest.raises(ValueError):
            td.add(1.0, weight=0.0)
        with pytest.raises(ValueError):
            td.add(1.0, weight=-1.0)

    def test_add_centroid(self):
        td = TDigest(delta=100.0)
        c = Centroid(mean=25.0, weight=2.0, timestamp=100.0)
        td.add_centroid(c)
        assert td.total_weight == 2.0


class TestTDigestQuantile:
    def test_quantile_empty_raises(self):
        td = TDigest(delta=100.0)
        with pytest.raises(EmptyDigestError):
            td.quantile(0.5)

    def test_quantile_invalid_raises(self):
        td = TDigest(delta=100.0)
        td.add(1.0)
        with pytest.raises(InvalidQuantileError):
            td.quantile(-0.1)
        with pytest.raises(InvalidQuantileError):
            td.quantile(1.1)

    def test_single_value_quantiles(self):
        td = TDigest(delta=100.0)
        td.add(100.0)
        for q in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert td.quantile(q) == pytest.approx(100.0)

    def test_uniform_distribution(self):
        td = TDigest(delta=200.0)
        for i in range(1, 101):
            td.add(float(i))

        p50 = td.quantile(0.5)
        p95 = td.quantile(0.95)
        p99 = td.quantile(0.99)

        assert 45 <= p50 <= 55
        assert 90 <= p95 <= 100
        assert 95 <= p99 <= 100

    def test_quantiles_batch(self):
        td = TDigest(delta=200.0)
        for i in range(1, 101):
            td.add(float(i))

        results = td.quantiles([0.5, 0.95, 0.99])
        assert len(results) == 3
        assert results[0] <= results[1] <= results[2]

    def test_quantiles_invalid_raises(self):
        td = TDigest(delta=100.0)
        td.add(1.0)
        with pytest.raises(InvalidQuantileError):
            td.quantiles([0.5, -0.1])

    def test_quantiles_empty_raises(self):
        td = TDigest(delta=100.0)
        with pytest.raises(EmptyDigestError):
            td.quantiles([0.5, 0.95])

    def test_weighted_values(self):
        td = TDigest(delta=100.0)
        td.add(10.0, weight=10.0)
        td.add(100.0, weight=1.0)

        p50 = td.quantile(0.5)
        assert 5 <= p50 <= 30


class TestTDigestTrim:
    def test_trim_removes_old_data(self):
        td = TDigest(delta=100.0)
        td.add(10.0, timestamp=0.0)
        td.add(100.0, timestamp=100.0)

        td.trim(current_time=100.0, window_seconds=50.0)

        p50 = td.quantile(0.5)
        assert 80 <= p50 <= 120

    def test_trim_with_half_life(self):
        td = TDigest(delta=200.0)
        for _ in range(100):
            td.add(10.0, timestamp=0.0)
        for _ in range(100):
            td.add(100.0, timestamp=100.0)

        half_life = 50.0
        td.trim(current_time=100.0, window_seconds=200.0, half_life_seconds=half_life)

        p50 = td.quantile(0.5)
        assert 50 <= p50 <= 100

    def test_trim_all_data_removed(self):
        td = TDigest(delta=100.0)
        td.add(10.0, timestamp=0.0)
        td.add(20.0, timestamp=10.0)

        td.trim(current_time=200.0, window_seconds=50.0)
        assert td.is_empty is True

    def test_trim_preserves_recent_data(self):
        td = TDigest(delta=100.0)
        td.add(10.0, timestamp=0.0)
        td.add(100.0, timestamp=90.0)

        td.trim(current_time=100.0, window_seconds=50.0)
        assert not td.is_empty


class TestTDigestMerge:
    def test_merge_two_digests(self):
        td1 = TDigest(delta=100.0)
        for i in range(1, 51):
            td1.add(float(i))

        td2 = TDigest(delta=100.0)
        for i in range(51, 101):
            td2.add(float(i))

        td1.merge(td2)

        p50 = td1.quantile(0.5)
        p95 = td1.quantile(0.95)
        assert 45 <= p50 <= 55
        assert 90 <= p95 <= 100

    def test_merge_into_empty(self):
        td1 = TDigest(delta=100.0)
        td2 = TDigest(delta=100.0)
        td2.add(42.0)

        td1.merge(td2)
        assert td1.quantile(0.5) == pytest.approx(42.0)

    def test_merge_empty_into(self):
        td1 = TDigest(delta=100.0)
        td1.add(42.0)
        td2 = TDigest(delta=100.0)

        td1.merge(td2)
        assert td1.quantile(0.5) == pytest.approx(42.0)


class TestTDigestCompression:
    def test_compression_limits_centroids(self):
        td = TDigest(delta=50.0)
        for i in range(1000):
            td.add(float(i))

        assert len(td.centroids) <= 200

    def test_compression_preserves_accuracy(self):
        td = TDigest(delta=100.0)
        import random
        random.seed(42)
        values = [random.gauss(0, 1) for _ in range(10000)]
        for v in values:
            td.add(v)

        p50 = td.quantile(0.5)
        assert -0.3 <= p50 <= 0.3
