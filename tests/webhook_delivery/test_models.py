from __future__ import annotations

import pytest

from solocoder_py.webhook_delivery import (
    DeliveryStatus,
    InvalidRetryStrategyError,
    InvalidSigningSecretError,
    InvalidUrlError,
    RetryStrategy,
    WebhookMessage,
    WebhookTarget,
    generate_delivery_attempt_id,
    generate_message_id,
    generate_target_id,
)
from solocoder_py.webhook_delivery.models import _is_valid_url


class TestIsValidUrl:
    def test_valid_http_url(self):
        assert _is_valid_url("http://example.com/webhook") is True

    def test_valid_https_url(self):
        assert _is_valid_url("https://api.example.com/hooks/123") is True

    def test_valid_url_with_port(self):
        assert _is_valid_url("http://localhost:8080/callback") is True

    def test_invalid_ftp_url(self):
        assert _is_valid_url("ftp://example.com") is False

    def test_empty_string(self):
        assert _is_valid_url("") is False

    def test_none_url(self):
        assert _is_valid_url(None) is False

    def test_no_scheme(self):
        assert _is_valid_url("example.com/webhook") is False

    def test_no_netloc(self):
        assert _is_valid_url("http://") is False

    def test_non_string(self):
        assert _is_valid_url(123) is False


class TestRetryStrategy:
    def test_default_values(self):
        strategy = RetryStrategy()
        assert strategy.initial_delay == 1.0
        assert strategy.backoff_multiplier == 2.0
        assert strategy.max_delay == 60.0
        assert strategy.max_retries == 3

    def test_custom_values(self):
        strategy = RetryStrategy(
            initial_delay=2.0,
            backoff_multiplier=3.0,
            max_delay=120.0,
            max_retries=5,
        )
        assert strategy.initial_delay == 2.0
        assert strategy.backoff_multiplier == 3.0
        assert strategy.max_delay == 120.0
        assert strategy.max_retries == 5

    def test_negative_initial_delay_invalid(self):
        with pytest.raises(InvalidRetryStrategyError):
            RetryStrategy(initial_delay=-1.0)

    def test_zero_initial_delay_valid(self):
        strategy = RetryStrategy(initial_delay=0.0)
        assert strategy.initial_delay == 0.0

    def test_backoff_multiplier_below_one_invalid(self):
        with pytest.raises(InvalidRetryStrategyError):
            RetryStrategy(backoff_multiplier=0.5)

    def test_backoff_multiplier_equal_one_valid(self):
        strategy = RetryStrategy(backoff_multiplier=1.0)
        assert strategy.backoff_multiplier == 1.0

    def test_max_delay_zero_invalid(self):
        with pytest.raises(InvalidRetryStrategyError):
            RetryStrategy(max_delay=0.0)

    def test_max_delay_less_than_initial_invalid(self):
        with pytest.raises(InvalidRetryStrategyError):
            RetryStrategy(initial_delay=10.0, max_delay=5.0)

    def test_max_delay_equal_to_initial_valid(self):
        strategy = RetryStrategy(initial_delay=5.0, max_delay=5.0)
        assert strategy.initial_delay == 5.0
        assert strategy.max_delay == 5.0

    def test_negative_max_retries_invalid(self):
        with pytest.raises(InvalidRetryStrategyError):
            RetryStrategy(max_retries=-1)

    def test_zero_max_retries_valid(self):
        strategy = RetryStrategy(max_retries=0)
        assert strategy.max_retries == 0

    def test_calculate_delay_first_attempt_is_zero(self):
        strategy = RetryStrategy(initial_delay=5.0, backoff_multiplier=2.0)
        assert strategy.calculate_delay(1) == 0.0

    def test_calculate_delay_second_attempt_is_initial_delay(self):
        strategy = RetryStrategy(initial_delay=5.0, backoff_multiplier=2.0)
        assert strategy.calculate_delay(2) == 5.0

    def test_calculate_delay_exponential_growth(self):
        strategy = RetryStrategy(initial_delay=1.0, backoff_multiplier=2.0)
        assert strategy.calculate_delay(3) == 2.0
        assert strategy.calculate_delay(4) == 4.0
        assert strategy.calculate_delay(5) == 8.0

    def test_calculate_delay_max_delay_capping(self):
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_delay=5.0
        )
        assert strategy.calculate_delay(2) == 1.0
        assert strategy.calculate_delay(3) == 2.0
        assert strategy.calculate_delay(4) == 4.0
        assert strategy.calculate_delay(5) == 5.0
        assert strategy.calculate_delay(6) == 5.0
        assert strategy.calculate_delay(10) == 5.0

    def test_calculate_delay_invalid_attempt_number(self):
        strategy = RetryStrategy()
        with pytest.raises(ValueError):
            strategy.calculate_delay(0)
        with pytest.raises(ValueError):
            strategy.calculate_delay(-1)

    def test_should_retry_within_limit(self):
        strategy = RetryStrategy(max_retries=3)
        assert strategy.should_retry(0) is True
        assert strategy.should_retry(1) is True
        assert strategy.should_retry(2) is True
        assert strategy.should_retry(3) is True

    def test_should_retry_at_limit_returns_false(self):
        strategy = RetryStrategy(max_retries=3)
        assert strategy.should_retry(4) is False
        assert strategy.should_retry(5) is False

    def test_should_retry_zero_max_retries(self):
        strategy = RetryStrategy(max_retries=0)
        assert strategy.should_retry(0) is True
        assert strategy.should_retry(1) is False


class TestWebhookTarget:
    def test_valid_target_creation(self):
        target = WebhookTarget(
            id="tgt_001",
            url="https://example.com/hook",
            signing_secret="secret123",
        )
        assert target.id == "tgt_001"
        assert target.url == "https://example.com/hook"
        assert target.signing_secret == "secret123"
        assert target.is_active is True
        assert isinstance(target.retry_strategy, RetryStrategy)

    def test_target_with_custom_retry_strategy(self):
        strategy = RetryStrategy(max_retries=5)
        target = WebhookTarget(
            id="tgt_002",
            url="http://localhost:3000/webhook",
            signing_secret="abc",
            retry_strategy=strategy,
            is_active=False,
        )
        assert target.retry_strategy.max_retries == 5
        assert target.is_active is False

    def test_empty_id_invalid(self):
        with pytest.raises(ValueError):
            WebhookTarget(
                id="",
                url="https://example.com",
                signing_secret="secret",
            )

    def test_invalid_url_raises(self):
        with pytest.raises(InvalidUrlError):
            WebhookTarget(
                id="tgt_003",
                url="not-a-url",
                signing_secret="secret",
            )

    def test_ftp_url_invalid(self):
        with pytest.raises(InvalidUrlError):
            WebhookTarget(
                id="tgt_004",
                url="ftp://example.com",
                signing_secret="secret",
            )

    def test_empty_signing_secret_invalid(self):
        with pytest.raises(InvalidSigningSecretError):
            WebhookTarget(
                id="tgt_005",
                url="https://example.com",
                signing_secret="",
            )

    def test_non_string_signing_secret_invalid(self):
        with pytest.raises(InvalidSigningSecretError):
            WebhookTarget(
                id="tgt_006",
                url="https://example.com",
                signing_secret=123,
            )


class TestWebhookMessage:
    def test_valid_message_creation(self):
        msg = WebhookMessage(
            id="msg_001",
            target_id="tgt_001",
            event_type="order.created",
            payload={"order_id": "123"},
            created_at=1000.0,
        )
        assert msg.id == "msg_001"
        assert msg.target_id == "tgt_001"
        assert msg.event_type == "order.created"
        assert msg.payload == {"order_id": "123"}
        assert msg.created_at == 1000.0
        assert msg.delivery_attempts == 0
        assert msg.last_error is None
        assert msg.status == DeliveryStatus.PENDING

    def test_empty_id_invalid(self):
        with pytest.raises(ValueError):
            WebhookMessage(
                id="",
                target_id="tgt_001",
                event_type="x",
                payload={},
                created_at=0.0,
            )

    def test_empty_target_id_invalid(self):
        with pytest.raises(ValueError):
            WebhookMessage(
                id="msg_001",
                target_id="",
                event_type="x",
                payload={},
                created_at=0.0,
            )

    def test_empty_event_type_invalid(self):
        with pytest.raises(ValueError):
            WebhookMessage(
                id="msg_001",
                target_id="tgt_001",
                event_type="",
                payload={},
                created_at=0.0,
            )

    def test_negative_delivery_attempts_invalid(self):
        with pytest.raises(ValueError):
            WebhookMessage(
                id="msg_001",
                target_id="tgt_001",
                event_type="x",
                payload={},
                created_at=0.0,
                delivery_attempts=-1,
            )

    def test_status_properties(self):
        msg = WebhookMessage(
            id="msg_001",
            target_id="tgt_001",
            event_type="x",
            payload={},
            created_at=0.0,
        )
        assert msg.is_pending is True
        assert msg.is_delivering is False
        assert msg.is_success is False
        assert msg.is_failed is False
        assert msg.is_dead_letter is False

        msg.status = DeliveryStatus.SUCCESS
        assert msg.is_success is True
        assert msg.is_pending is False


class TestIdGenerators:
    def test_generate_message_id_format(self):
        mid = generate_message_id()
        assert mid.startswith("msg_")
        assert len(mid) > 4

    def test_generate_target_id_format(self):
        tid = generate_target_id()
        assert tid.startswith("tgt_")
        assert len(tid) > 4

    def test_generate_delivery_attempt_id_format(self):
        aid = generate_delivery_attempt_id()
        assert aid.startswith("att_")
        assert len(aid) > 4

    def test_ids_are_unique(self):
        ids = {generate_message_id() for _ in range(100)}
        assert len(ids) == 100
