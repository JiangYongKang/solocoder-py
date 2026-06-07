from __future__ import annotations

import pytest

from solocoder_py.token_bucket import (
    InvalidBucketConfigError,
    NotEnoughTokensError,
    TokenBucketConfig,
    TokenBucketError,
    TokenBucketState,
)
from solocoder_py.token_bucket.models import (
    _TOKEN_SCALE,
    scaled_to_tokens,
    tokens_to_scaled,
)


class TestTokenBucketConfig:
    def test_valid_config(self):
        config = TokenBucketConfig(capacity=10, refill_rate_per_second=5.0)
        assert config.capacity == 10
        assert config.refill_rate_per_second == 5.0

    def test_capacity_zero_raises(self):
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            TokenBucketConfig(capacity=0, refill_rate_per_second=1.0)

    def test_capacity_negative_raises(self):
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            TokenBucketConfig(capacity=-5, refill_rate_per_second=1.0)

    def test_refill_rate_zero_allowed(self):
        config = TokenBucketConfig(capacity=10, refill_rate_per_second=0.0)
        assert config.refill_rate_per_second == 0.0

    def test_refill_rate_negative_raises(self):
        with pytest.raises(InvalidBucketConfigError, match="refill_rate_per_second must be non-negative"):
            TokenBucketConfig(capacity=10, refill_rate_per_second=-2.0)

    def test_config_is_frozen(self):
        config = TokenBucketConfig(capacity=10, refill_rate_per_second=5.0)
        with pytest.raises(Exception):
            config.capacity = 20


class TestTokenBucketConfigScaled:
    def test_capacity_scaled(self):
        config = TokenBucketConfig(capacity=10, refill_rate_per_second=5.0)
        assert config.capacity_scaled == 10 * _TOKEN_SCALE

    def test_refill_rate_scaled_per_second(self):
        config = TokenBucketConfig(capacity=10, refill_rate_per_second=2.5)
        assert config.refill_rate_scaled_per_second == 2.5 * _TOKEN_SCALE


class TestTokenPrecisionHelpers:
    def test_tokens_to_scaled_integer(self):
        assert tokens_to_scaled(3) == 3 * _TOKEN_SCALE

    def test_tokens_to_scaled_float(self):
        assert tokens_to_scaled(2.5) == int(round(2.5 * _TOKEN_SCALE))

    def test_scaled_to_tokens(self):
        assert scaled_to_tokens(3 * _TOKEN_SCALE) == 3.0

    def test_roundtrip_precision(self):
        for value in [0, 1, 100, 0.5, 2.5, 0.000001]:
            assert abs(scaled_to_tokens(tokens_to_scaled(value)) - value) < 1e-6


class TestTokenBucketState:
    def test_state_initialization(self):
        state = TokenBucketState(current_tokens_scaled=5 * _TOKEN_SCALE, last_refill_time=100.0)
        assert state.current_tokens_scaled == 5 * _TOKEN_SCALE
        assert state.last_refill_time == 100.0

    def test_state_mutable(self):
        state = TokenBucketState(current_tokens_scaled=5 * _TOKEN_SCALE, last_refill_time=100.0)
        state.current_tokens_scaled = 8 * _TOKEN_SCALE
        state.last_refill_time = 200.0
        assert state.current_tokens_scaled == 8 * _TOKEN_SCALE
        assert state.last_refill_time == 200.0


class TestExceptionHierarchy:
    def test_invalid_config_is_token_bucket_error(self):
        assert issubclass(InvalidBucketConfigError, TokenBucketError)

    def test_not_enough_tokens_is_token_bucket_error(self):
        assert issubclass(NotEnoughTokensError, TokenBucketError)

    def test_not_enough_tokens_attributes(self):
        exc = NotEnoughTokensError(requested=5, available=3.5)
        assert exc.requested == 5
        assert exc.available == 3.5
        assert "5" in str(exc)
        assert "3.5" in str(exc)
