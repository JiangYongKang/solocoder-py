from __future__ import annotations

import pytest

from solocoder_py.rate_limiter import (
    InvalidConfigError,
    InvalidResponseHeaderError,
    RateLimitHeaders,
    TokenBucketConfig,
)


class TestTokenBucketConfigValidation:
    def test_valid_config_default_initial(self):
        config = TokenBucketConfig(refill_rate=5.0, capacity=100)
        assert config.refill_rate == 5.0
        assert config.capacity == 100
        assert config.initial_tokens is None

    def test_valid_config_with_initial_tokens(self):
        config = TokenBucketConfig(refill_rate=2.0, capacity=10, initial_tokens=5)
        assert config.initial_tokens == 5

    def test_valid_config_zero_initial_tokens(self):
        config = TokenBucketConfig(refill_rate=1.0, capacity=10, initial_tokens=0)
        assert config.initial_tokens == 0

    def test_valid_config_initial_equals_capacity(self):
        config = TokenBucketConfig(refill_rate=3.0, capacity=20, initial_tokens=20)
        assert config.initial_tokens == 20

    def test_invalid_refill_rate_zero(self):
        with pytest.raises(InvalidConfigError, match="refill_rate must be positive"):
            TokenBucketConfig(refill_rate=0.0, capacity=10)

    def test_invalid_refill_rate_negative(self):
        with pytest.raises(InvalidConfigError, match="refill_rate must be positive"):
            TokenBucketConfig(refill_rate=-1.0, capacity=10)

    def test_invalid_capacity_zero(self):
        with pytest.raises(InvalidConfigError, match="capacity must be positive"):
            TokenBucketConfig(refill_rate=1.0, capacity=0)

    def test_invalid_capacity_negative(self):
        with pytest.raises(InvalidConfigError, match="capacity must be positive"):
            TokenBucketConfig(refill_rate=1.0, capacity=-5)

    def test_invalid_initial_tokens_negative(self):
        with pytest.raises(InvalidConfigError, match="initial_tokens must be non-negative"):
            TokenBucketConfig(refill_rate=1.0, capacity=10, initial_tokens=-1)

    def test_invalid_initial_tokens_exceeds_capacity(self):
        with pytest.raises(InvalidConfigError, match="initial_tokens cannot exceed capacity"):
            TokenBucketConfig(refill_rate=1.0, capacity=10, initial_tokens=15)


class TestRateLimitHeadersParsing:
    def test_parse_all_headers(self):
        headers = {
            "X-RateLimit-Remaining": "50",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "1718409600.5",
            "Retry-After": "30",
        }
        parsed = RateLimitHeaders.from_headers(headers)
        assert parsed.remaining == 50
        assert parsed.limit == 100
        assert parsed.reset == 1718409600.5
        assert parsed.retry_after == 30.0
        assert len(parsed.raw_headers) == 4

    def test_parse_partial_headers(self):
        headers = {
            "X-RateLimit-Remaining": "25",
        }
        parsed = RateLimitHeaders.from_headers(headers)
        assert parsed.remaining == 25
        assert parsed.limit is None
        assert parsed.reset is None
        assert parsed.retry_after is None

    def test_parse_empty_headers(self):
        parsed = RateLimitHeaders.from_headers({})
        assert parsed.remaining is None
        assert parsed.limit is None
        assert parsed.reset is None
        assert parsed.retry_after is None

    def test_parse_case_insensitive_headers(self):
        headers = {
            "x-ratelimit-remaining": "75",
            "X-RATELIMIT-LIMIT": "200",
        }
        parsed = RateLimitHeaders.from_headers(headers)
        assert parsed.remaining == 75
        assert parsed.limit == 200

    def test_parse_integer_values(self):
        headers = {"X-RateLimit-Reset": 1718409600}
        parsed = RateLimitHeaders.from_headers(headers)
        assert parsed.reset == 1718409600.0

    def test_invalid_remaining_header(self):
        with pytest.raises(InvalidResponseHeaderError, match="X-RateLimit-Remaining"):
            RateLimitHeaders.from_headers({"X-RateLimit-Remaining": "not_a_number"})

    def test_invalid_limit_header(self):
        with pytest.raises(InvalidResponseHeaderError, match="X-RateLimit-Limit"):
            RateLimitHeaders.from_headers({"X-RateLimit-Limit": "invalid"})

    def test_invalid_reset_header(self):
        with pytest.raises(InvalidResponseHeaderError, match="X-RateLimit-Reset"):
            RateLimitHeaders.from_headers({"X-RateLimit-Reset": "bad_time"})

    def test_invalid_retry_after_header(self):
        with pytest.raises(InvalidResponseHeaderError, match="Retry-After"):
            RateLimitHeaders.from_headers({"Retry-After": "wait_a_bit"})

    def test_raw_headers_preserved(self):
        headers = {
            "X-RateLimit-Remaining": "10",
            "Content-Type": "application/json",
        }
        parsed = RateLimitHeaders.from_headers(headers)
        assert "X-RateLimit-Remaining" in parsed.raw_headers
        assert "Content-Type" in parsed.raw_headers
        assert parsed.raw_headers["X-RateLimit-Remaining"] == "10"
