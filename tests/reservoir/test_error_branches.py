from __future__ import annotations

import pytest

from solocoder_py.reservoir import (
    ReservoirSampler,
    WeightedReservoirSampler,
    InvalidCapacityError,
    InvalidWeightError,
    SamplerClosedError,
)


class TestConstructionErrors:
    def test_negative_capacity_raises(self):
        with pytest.raises(InvalidCapacityError, match="positive"):
            ReservoirSampler(capacity=-1)

    def test_negative_capacity_weighted_raises(self):
        with pytest.raises(InvalidCapacityError, match="positive"):
            WeightedReservoirSampler(capacity=-1)

    def test_large_negative_capacity_raises(self):
        with pytest.raises(InvalidCapacityError):
            ReservoirSampler(capacity=-9999)

    def test_zero_capacity_raises(self):
        with pytest.raises(InvalidCapacityError, match="positive"):
            ReservoirSampler(capacity=0)

    def test_zero_capacity_weighted_raises(self):
        with pytest.raises(InvalidCapacityError, match="positive"):
            WeightedReservoirSampler(capacity=0)

    def test_non_integer_capacity_raises(self):
        with pytest.raises(InvalidCapacityError, match="integer"):
            ReservoirSampler(capacity=5.5)

    def test_non_integer_capacity_weighted_raises(self):
        with pytest.raises(InvalidCapacityError, match="integer"):
            WeightedReservoirSampler(capacity=3.14)

    def test_string_capacity_raises(self):
        with pytest.raises(InvalidCapacityError):
            ReservoirSampler(capacity="5")


class TestWeightedSamplerWeightErrors:
    def test_zero_weight_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError, match="positive"):
            weighted_sampler_k5.feed("item", 0.0)

    def test_negative_weight_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError, match="positive"):
            weighted_sampler_k5.feed("item", -1.0)

    def test_large_negative_weight_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError):
            weighted_sampler_k5.feed("item", -100.5)

    def test_string_weight_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError, match="number"):
            weighted_sampler_k5.feed("item", "2.5")

    def test_none_weight_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError):
            weighted_sampler_k5.feed("item", None)

    def test_zero_weight_in_feed_many_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError):
            weighted_sampler_k5.feed_many([(1, 1.0), (2, 0.0), (3, 2.0)])

    def test_negative_weight_in_feed_many_raises(self, weighted_sampler_k5):
        with pytest.raises(InvalidWeightError):
            weighted_sampler_k5.feed_many([(1, 1.0), (2, -5.0)])


class TestClosedSamplerErrors:
    def test_feed_after_close_raises(self, sampler_k5):
        sampler_k5.feed_many([1, 2, 3])
        sampler_k5.close()
        with pytest.raises(SamplerClosedError, match="closed"):
            sampler_k5.feed(4)

    def test_feed_many_after_close_raises(self, sampler_k5):
        sampler_k5.close()
        with pytest.raises(SamplerClosedError):
            sampler_k5.feed_many([4, 5, 6])

    def test_weighted_feed_after_close_raises(self, weighted_sampler_k5):
        weighted_sampler_k5.feed(1, 1.0)
        weighted_sampler_k5.close()
        with pytest.raises(SamplerClosedError, match="closed"):
            weighted_sampler_k5.feed(2, 2.0)

    def test_weighted_feed_many_after_close_raises(self, weighted_sampler_k5):
        weighted_sampler_k5.close()
        with pytest.raises(SamplerClosedError):
            weighted_sampler_k5.feed_many([(2, 2.0)])

    def test_double_close_is_fine(self, sampler_k5):
        sampler_k5.feed(1)
        r1 = sampler_k5.close()
        r2 = sampler_k5.close()
        assert r1 == r2
        assert sampler_k5.closed is True

    def test_double_close_weighted_is_fine(self, weighted_sampler_k5):
        weighted_sampler_k5.feed(1, 1.0)
        r1 = weighted_sampler_k5.close()
        r2 = weighted_sampler_k5.close()
        assert sorted(r1) == sorted(r2)
        assert weighted_sampler_k5.closed is True
