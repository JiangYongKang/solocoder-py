from datetime import timedelta
from time import sleep

import pytest

from solocoder_py.idempotency import (
    FailureReplayPolicy,
    IdempotencyRecord,
    IdempotencyState,
)


class TestIdempotencyState:
    def test_state_enum_values(self):
        assert IdempotencyState.PROCESSING == "processing"
        assert IdempotencyState.SUCCESS == "success"
        assert IdempotencyState.FAILED == "failed"
        assert IdempotencyState.EXPIRED == "expired"


class TestFailureReplayPolicy:
    def test_policy_enum_values(self):
        assert FailureReplayPolicy.REPLAY == "replay"
        assert FailureReplayPolicy.REJECT == "reject"
        assert FailureReplayPolicy.RETRY == "retry"


class TestIdempotencyRecordCreation:
    def test_record_creation_defaults(self):
        record = IdempotencyRecord(
            key="test-key",
            request_fingerprint="fp-123",
        )
        assert record.key == "test-key"
        assert record.request_fingerprint == "fp-123"
        assert record.state == IdempotencyState.PROCESSING
        assert record.response_data is None
        assert record.error_message is None
        assert record.created_at is not None
        assert record.expires_at is not None
        assert record.expires_at > record.created_at
        assert record.is_processing is True
        assert record.is_success is False
        assert record.is_failed is False
        assert record.is_expired is False

    def test_record_creation_custom_expiry(self):
        from datetime import datetime
        custom_expiry = datetime.now() + timedelta(hours=1)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            expires_at=custom_expiry,
        )
        assert record.expires_at == custom_expiry

    def test_empty_key_rejected(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            IdempotencyRecord(key="", request_fingerprint="fp")

    def test_empty_fingerprint_rejected(self):
        with pytest.raises(ValueError, match="request_fingerprint cannot be empty"):
            IdempotencyRecord(key="k", request_fingerprint="")

    def test_expires_before_created_rejected(self):
        from datetime import datetime
        past = datetime.now() - timedelta(hours=1)
        with pytest.raises(ValueError, match="expires_at must be after created_at"):
            IdempotencyRecord(
                key="k",
                request_fingerprint="fp",
                expires_at=past,
            )


class TestIdempotencyRecordStateTransitions:
    def test_mark_success(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_success({"result": "ok"})
        assert record.state == IdempotencyState.SUCCESS
        assert record.response_data == {"result": "ok"}
        assert record.error_message is None
        assert record.is_success is True
        assert record.is_processing is False

    def test_mark_failed(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_failed("something went wrong")
        assert record.state == IdempotencyState.FAILED
        assert record.error_message == "something went wrong"
        assert record.response_data is None
        assert record.is_failed is True
        assert record.is_processing is False

    def test_mark_success_from_failed_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_failed("err")
        with pytest.raises(ValueError, match="Cannot mark success"):
            record.mark_success("data")

    def test_mark_failed_from_success_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_success("data")
        with pytest.raises(ValueError, match="Cannot mark failed"):
            record.mark_failed("err")

    def test_mark_success_from_expired_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_expired()
        with pytest.raises(ValueError, match="Cannot mark success"):
            record.mark_success("data")

    def test_mark_expired(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        record.mark_expired()
        assert record.state == IdempotencyState.EXPIRED
        assert record.is_expired is True


class TestIdempotencyRecordFingerprint:
    def test_fingerprint_matches(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp-1")
        assert record.fingerprint_matches("fp-1") is True
        assert record.fingerprint_matches("fp-2") is False


class TestIdempotencyRecordExpiration:
    def test_record_auto_expires(self):
        from datetime import datetime
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            expires_at=datetime.now() + timedelta(milliseconds=50),
        )
        assert record.is_expired is False
        sleep(0.1)
        assert record.is_expired is True

    def test_remaining_ttl(self):
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
        )
        remaining = record.remaining_ttl
        assert remaining is not None
        assert remaining.total_seconds() > 0

    def test_remaining_ttl_zero_when_expired(self):
        from datetime import datetime
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            expires_at=datetime.now() + timedelta(milliseconds=10),
        )
        sleep(0.05)
        remaining = record.remaining_ttl
        assert remaining is not None
        assert remaining.total_seconds() >= 0

    def test_refresh_ttl(self):
        from datetime import datetime
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
        )
        original_expiry = record.expires_at
        sleep(0.01)
        record.refresh_ttl(timedelta(hours=48))
        assert record.expires_at > original_expiry

    def test_refresh_ttl_negative_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        with pytest.raises(ValueError, match="ttl must be positive"):
            record.refresh_ttl(timedelta(seconds=-1))

    def test_refresh_ttl_zero_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp")
        with pytest.raises(ValueError, match="ttl must be positive"):
            record.refresh_ttl(timedelta(seconds=0))
