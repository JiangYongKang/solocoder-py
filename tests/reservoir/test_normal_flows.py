from __future__ import annotations

from collections import Counter

import pytest

from solocoder_py.reservoir import (
    ReservoirSampler,
    WeightedReservoirSampler,
)


class TestReservoirSamplerNormalFlows:
    def test_small_data_less_than_capacity_kept_all(self, sampler_k5):
        data = [1, 2, 3]
        sampler_k5.feed_many(data)
        assert sampler_k5.sample_count == 3
        assert sampler_k5.total_processed == 3
        assert set(sampler_k5.samples()) == {1, 2, 3}

    def test_data_equals_capacity_kept_all(self, sampler_k5):
        data = [1, 2, 3, 4, 5]
        sampler_k5.feed_many(data)
        assert sampler_k5.sample_count == 5
        assert sampler_k5.total_processed == 5
        assert set(sampler_k5.samples()) == {1, 2, 3, 4, 5}

    def test_large_data_sample_size_equals_capacity(self, sampler_k5):
        data = list(range(1000))
        sampler_k5.feed_many(data)
        assert sampler_k5.sample_count == 5
        assert sampler_k5.total_processed == 1000

    def test_statistical_uniformity(self):
        n = 1000
        k = 10
        trials = 20000
        counter = Counter()
        for trial in range(trials):
            sampler = ReservoirSampler(capacity=k, seed=trial)
            sampler.feed_many(range(n))
            for s in sampler.samples():
                counter[s] += 1
        expected = k * trials / n
        counts = list(counter.values())
        avg = sum(counts) / len(counts)
        assert abs(avg - expected) / expected < 0.05
        min_count = min(counts)
        max_count = max(counts)
        assert (max_count - min_count) / expected < 0.5

    def test_feed_single_item(self, sampler_k5):
        sampler_k5.feed(42)
        assert sampler_k5.total_processed == 1
        assert sampler_k5.sample_count == 1
        assert 42 in sampler_k5

    def test_samples_returns_copy(self, sampler_k5):
        sampler_k5.feed_many([1, 2, 3])
        s1 = sampler_k5.samples()
        s2 = sampler_k5.samples()
        assert s1 == s2
        s1.append(999)
        s3 = sampler_k5.samples()
        assert 999 not in s3

    def test_len_matches_sample_count(self, sampler_k5):
        assert len(sampler_k5) == 0
        sampler_k5.feed_many([1, 2, 3])
        assert len(sampler_k5) == 3

    def test_iter_works(self, sampler_k5):
        data = [10, 20, 30]
        sampler_k5.feed_many(data)
        result = [x for x in sampler_k5]
        assert set(result) == {10, 20, 30}

    def test_contains_works(self, sampler_k5):
        sampler_k5.feed_many([1, 2, 3])
        assert 1 in sampler_k5
        assert 2 in sampler_k5
        assert 99 not in sampler_k5

    def test_close_returns_samples_and_sets_closed(self, sampler_k5):
        sampler_k5.feed_many([1, 2, 3])
        result = sampler_k5.close()
        assert set(result) == {1, 2, 3}
        assert sampler_k5.closed is True

    def test_get_state_returns_correct_snapshot(self, sampler_k5):
        sampler_k5.feed_many([1, 2, 3, 4, 5, 6, 7])
        state = sampler_k5.get_state()
        assert state.capacity == 5
        assert state.total_processed == 7
        assert state.closed is False
        assert len(state.reservoir) == 5


class TestWeightedSamplerNormalFlows:
    def test_small_data_less_than_capacity_kept_all(self, weighted_sampler_k5):
        data = [(1, 1.0), (2, 2.0), (3, 3.0)]
        weighted_sampler_k5.feed_many(data)
        assert weighted_sampler_k5.sample_count == 3
        assert weighted_sampler_k5.total_processed == 3
        sampled_values = set(weighted_sampler_k5.samples())
        assert sampled_values == {1, 2, 3}

    def test_data_equals_capacity_kept_all(self, weighted_sampler_k5):
        data = [(i, float(i)) for i in range(1, 6)]
        weighted_sampler_k5.feed_many(data)
        assert weighted_sampler_k5.sample_count == 5
        assert weighted_sampler_k5.total_processed == 5

    def test_large_data_sample_size_equals_capacity(self, weighted_sampler_k5):
        data = [(i, float(i + 1)) for i in range(1000)]
        weighted_sampler_k5.feed_many(data)
        assert weighted_sampler_k5.sample_count == 5
        assert weighted_sampler_k5.total_processed == 1000

    def test_weight_proportional_selection(self):
        n = 100
        k = 10
        trials = 30000
        weights = [1.0, 2.0, 3.0] * (n // 3 + 1)
        weights = weights[:n]
        items = list(range(n))
        weight_map = dict(zip(items, weights))
        counter = Counter()
        for trial in range(trials):
            sampler = WeightedReservoirSampler(capacity=k, seed=trial)
            for i in range(n):
                sampler.feed(items[i], weights[i])
            for s in sampler.samples():
                counter[s] += 1
        total_weight = sum(weights)
        group_totals = {1: 0.0, 2: 0.0, 3: 0.0}
        group_counts = {1: 0, 2: 0, 3: 0}
        for item, count in counter.items():
            w = weight_map[item]
            group_totals[w] += count
        total_samples = k * trials
        for w in [1.0, 2.0, 3.0]:
            group_weight_sum = sum(x for x in weights if x == w)
            expected_ratio = group_weight_sum / total_weight
            actual_ratio = group_totals[w] / total_samples
            assert abs(actual_ratio - expected_ratio) < 0.05

    def test_feed_single_item_with_weight(self, weighted_sampler_k5):
        weighted_sampler_k5.feed("hello", 2.5)
        assert weighted_sampler_k5.total_processed == 1
        assert weighted_sampler_k5.sample_count == 1
        assert "hello" in weighted_sampler_k5

    def test_equal_weights_become_uniform(self):
        n = 200
        k = 10
        trials = 20000
        counter = Counter()
        for trial in range(trials):
            sampler = WeightedReservoirSampler(capacity=k, seed=trial)
            for i in range(n):
                sampler.feed(i, 1.0)
            for s in sampler.samples():
                counter[s] += 1
        expected = k * trials / n
        counts = list(counter.values())
        avg = sum(counts) / len(counts)
        assert abs(avg - expected) / expected < 0.05

    def test_samples_returns_copy(self, weighted_sampler_k5):
        weighted_sampler_k5.feed_many([(1, 1.0), (2, 2.0)])
        s1 = weighted_sampler_k5.samples()
        s2 = weighted_sampler_k5.samples()
        assert sorted(s1) == sorted(s2)
        s1.append(999)
        s3 = weighted_sampler_k5.samples()
        assert 999 not in s3

    def test_len_iter_contains(self, weighted_sampler_k5):
        data = [(10, 1.0), (20, 1.0), (30, 1.0)]
        weighted_sampler_k5.feed_many(data)
        assert len(weighted_sampler_k5) == 3
        result = [x for x in weighted_sampler_k5]
        assert set(result) == {10, 20, 30}
        assert 10 in weighted_sampler_k5
        assert 99 not in weighted_sampler_k5

    def test_close_and_state(self, weighted_sampler_k5):
        weighted_sampler_k5.feed_many([(1, 1.0), (2, 2.0)])
        result = weighted_sampler_k5.close()
        assert set(result) == {1, 2}
        assert weighted_sampler_k5.closed is True
        state = weighted_sampler_k5.get_state()
        assert state.closed is True
        assert state.total_processed == 2
