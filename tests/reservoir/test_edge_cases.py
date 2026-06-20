from __future__ import annotations

from collections import Counter

import pytest

from solocoder_py.reservoir import (
    ReservoirSampler,
    WeightedReservoirSampler,
)


class TestReservoirSamplerEdgeCases:
    def test_k_equals_1_degenerate_case(self):
        trials = 50000
        n = 100
        counter = Counter()
        for trial in range(trials):
            sampler = ReservoirSampler(capacity=1, seed=trial)
            sampler.feed_many(range(n))
            samples = sampler.samples()
            assert len(samples) == 1
            counter[samples[0]] += 1
        expected = trials / n
        counts = list(counter.values())
        avg = sum(counts) / len(counts)
        assert abs(avg - expected) / expected < 0.05

    def test_k_equals_0_empty_reservoir(self, sampler_k0):
        sampler_k0.feed_many([1, 2, 3, 4, 5])
        assert sampler_k0.sample_count == 0
        assert sampler_k0.total_processed == 5
        assert sampler_k0.samples() == []
        assert len(sampler_k0) == 0

    def test_k_equals_0_iter_is_empty(self, sampler_k0):
        sampler_k0.feed(42)
        items = list(sampler_k0)
        assert items == []

    def test_empty_data_stream(self, sampler_k5):
        assert sampler_k5.sample_count == 0
        assert sampler_k5.total_processed == 0
        assert sampler_k5.samples() == []

    def test_empty_data_stream_close(self, sampler_k5):
        result = sampler_k5.close()
        assert result == []
        assert sampler_k5.closed is True

    def test_empty_data_stream_k0(self, sampler_k0):
        assert sampler_k0.sample_count == 0
        assert sampler_k0.total_processed == 0
        result = sampler_k0.close()
        assert result == []

    def test_all_same_items_stream(self, sampler_k5):
        sampler_k5.feed_many([7] * 100)
        assert sampler_k5.sample_count == 5
        assert all(x == 7 for x in sampler_k5.samples())

    def test_large_data_volume_correctness(self):
        n = 100000
        k = 20
        sampler = ReservoirSampler(capacity=k, seed=123)
        sampler.feed_many(range(n))
        assert sampler.total_processed == n
        assert sampler.sample_count == k
        samples = sampler.samples()
        assert len(set(samples)) == k
        for s in samples:
            assert 0 <= s < n

    def test_n_less_than_k_exactly_preserved(self):
        k = 100
        sampler = ReservoirSampler(capacity=k, seed=42)
        data = list(range(50))
        sampler.feed_many(data)
        assert sampler.sample_count == 50
        assert set(sampler.samples()) == set(data)

    def test_n_exactly_k_preserved(self):
        k = 50
        sampler = ReservoirSampler(capacity=k, seed=42)
        data = list(range(50))
        sampler.feed_many(data)
        assert sampler.sample_count == 50
        assert set(sampler.samples()) == set(data)

    def test_deterministic_with_same_seed(self):
        data = list(range(1000))
        s1 = ReservoirSampler(capacity=10, seed=99)
        s2 = ReservoirSampler(capacity=10, seed=99)
        s1.feed_many(data)
        s2.feed_many(data)
        assert s1.samples() == s2.samples()

    def test_incremental_vs_bulk_same_seed(self):
        data = list(range(500))
        s1 = ReservoirSampler(capacity=7, seed=7)
        s2 = ReservoirSampler(capacity=7, seed=7)
        s1.feed_many(data)
        for item in data:
            s2.feed(item)
        assert s1.samples() == s2.samples()


class TestWeightedSamplerEdgeCases:
    def test_k_equals_1_weighted_proportional(self):
        trials = 40000
        items = ["A", "B", "C"]
        weights = [1.0, 2.0, 3.0]
        n = 3
        counter = Counter()
        for trial in range(trials):
            sampler = WeightedReservoirSampler(capacity=1, seed=trial)
            for i in range(n):
                sampler.feed(items[i], weights[i])
            samples = sampler.samples()
            assert len(samples) == 1
            counter[samples[0]] += 1
        total_weight = sum(weights)
        for item, w in zip(items, weights):
            expected_ratio = w / total_weight
            actual_ratio = counter[item] / trials
            assert abs(actual_ratio - expected_ratio) < 0.03

    def test_k_equals_0_weighted_empty(self, weighted_sampler_k0):
        weighted_sampler_k0.feed_many([(1, 1.0), (2, 2.0)])
        assert weighted_sampler_k0.sample_count == 0
        assert weighted_sampler_k0.total_processed == 2
        assert weighted_sampler_k0.samples() == []

    def test_empty_stream_weighted(self, weighted_sampler_k5):
        assert weighted_sampler_k5.sample_count == 0
        assert weighted_sampler_k5.total_processed == 0
        assert weighted_sampler_k5.samples() == []

    def test_all_same_weights_uniformity(self):
        trials = 30000
        n = 50
        k = 5
        counter = Counter()
        for trial in range(trials):
            sampler = WeightedReservoirSampler(capacity=k, seed=trial)
            for i in range(n):
                sampler.feed(i, 5.0)
            for s in sampler.samples():
                counter[s] += 1
        expected = k * trials / n
        counts = list(counter.values())
        avg = sum(counts) / len(counts)
        assert abs(avg - expected) / expected < 0.05

    def test_extreme_weight_ratios(self):
        trials = 20000
        n = 4
        k = 1
        items = list(range(n))
        weights = [0.01, 0.01, 0.01, 100.0]
        heavy_selected = 0
        total_weight = sum(weights)
        expected_heavy_ratio = weights[3] / total_weight
        for trial in range(trials):
            sampler = WeightedReservoirSampler(capacity=k, seed=trial)
            for i in range(n):
                sampler.feed(items[i], weights[i])
            if 3 in sampler.samples():
                heavy_selected += 1
        actual_ratio = heavy_selected / trials
        assert abs(actual_ratio - expected_heavy_ratio) < 0.03

    def test_n_less_than_k_weighted_preserved(self):
        sampler = WeightedReservoirSampler(capacity=100, seed=42)
        data = [(i, float(i + 1)) for i in range(30)]
        sampler.feed_many(data)
        assert sampler.sample_count == 30
        sampled_values = set(sampler.samples())
        assert sampled_values == {i for i in range(30)}

    def test_n_exactly_k_weighted_preserved(self):
        sampler = WeightedReservoirSampler(capacity=30, seed=42)
        data = [(i, float(i + 1)) for i in range(30)]
        sampler.feed_many(data)
        assert sampler.sample_count == 30

    def test_deterministic_with_same_seed_weighted(self):
        data = [(i, float(i * 0.5 + 1)) for i in range(500)]
        s1 = WeightedReservoirSampler(capacity=10, seed=123)
        s2 = WeightedReservoirSampler(capacity=10, seed=123)
        s1.feed_many(data)
        s2.feed_many(data)
        assert s1.samples() == s2.samples()

    def test_incremental_vs_bulk_same_seed_weighted(self):
        data = [(i, 1.0 / (i + 1)) for i in range(300)]
        s1 = WeightedReservoirSampler(capacity=8, seed=5)
        s2 = WeightedReservoirSampler(capacity=8, seed=5)
        s1.feed_many(data)
        for item, w in data:
            s2.feed(item, w)
        assert s1.samples() == s2.samples()

    def test_large_volume_weighted(self):
        n = 50000
        k = 15
        sampler = WeightedReservoirSampler(capacity=k, seed=456)
        for i in range(n):
            sampler.feed(i, float(i % 10 + 1))
        assert sampler.total_processed == n
        assert sampler.sample_count == k
        samples = sampler.samples()
        assert len(samples) == k
        for s in samples:
            assert 0 <= s < n
