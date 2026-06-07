from __future__ import annotations

import pytest

from solocoder_py.token_bucket import (
    InvalidBucketConfigError,
    NotEnoughTokensError,
    TokenBucketConfig,
    TokenBucketError,
    TokenBucketState,
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


class TestTokenBucketState:
    def test_state_initialization(self):
        state = TokenBucketState(current_tokens=5.0, last_refill_time=100.0)
        assert state.current_tokens == 5.0
        assert state.last_refill_time == 100.0

    def test_state_mutable(self):
        state = TokenBucketState(current_tokens=5.0, last_refill_time=100.0)
        state.current_tokens = 8.0
        state.last_refill_time = 200.0
        assert state.current_tokens == 8.0
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
