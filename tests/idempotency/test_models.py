import pytest

from solocoder_py.idempotency import (
    FailureReplayPolicy,
    IdempotencyRecord,
    IdempotencyState,
    ManualClock,
    SystemClock,
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


class TestClock:
    def test_manual_clock_starts_at_zero(self):
        clock = ManualClock()
        assert clock.now() == 0.0

    def test_manual_clock_advance(self):
        clock = ManualClock(start_time=10.0)
        clock.advance(5.0)
        assert clock.now() == 15.0

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0

    def test_manual_clock_cannot_advance_negative(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot advance by negative seconds"):
            clock.advance(-1.0)

    def test_manual_clock_sleep_advances_time(self):
        clock = ManualClock(start_time=10.0)
        clock.sleep(3.5)
        assert clock.now() == 13.5

    def test_manual_clock_sleep_records_history(self):
        clock = ManualClock(start_time=0.0)
        clock.sleep(1.0)
        clock.sleep(2.5)
        assert clock.sleep_history == [1.0, 2.5]

    def test_manual_clock_sleep_negative_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot sleep for negative seconds"):
            clock.sleep(-1.0)


class TestIdempotencyRecordCreation:
    def test_record_creation_defaults(self):
        clock = ManualClock(start_time=100.0)
        record = IdempotencyRecord(
            key="test-key",
            request_fingerprint="fp-123",
            created_at=clock.now(),
            expires_at=clock.now() + 3600.0,
        )
        assert record.key == "test-key"
        assert record.request_fingerprint == "fp-123"
        assert record.state == IdempotencyState.PROCESSING
        assert record.response_data is None
        assert record.error_message is None
        assert record.created_at == 100.0
        assert record.expires_at == 100.0 + 3600.0
        assert record.is_processing is True
        assert record.is_success is False
        assert record.is_failed is False
        assert record.is_expired(clock) is False

    def test_record_creation_custom_expiry(self):
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=0.0,
            expires_at=7200.0,
        )
        assert record.expires_at == 7200.0

    def test_empty_key_rejected(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            IdempotencyRecord(key="", request_fingerprint="fp", created_at=0.0, expires_at=1.0)

    def test_empty_fingerprint_rejected(self):
        with pytest.raises(ValueError, match="request_fingerprint cannot be empty"):
            IdempotencyRecord(key="k", request_fingerprint="", created_at=0.0, expires_at=1.0)

    def test_expires_before_created_rejected(self):
        with pytest.raises(ValueError, match="expires_at must be after created_at"):
            IdempotencyRecord(
                key="k",
                request_fingerprint="fp",
                created_at=100.0,
                expires_at=50.0,
            )

    def test_expired_record_skips_expiry_validation(self):
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            state=IdempotencyState.EXPIRED,
            created_at=100.0,
            expires_at=50.0,
        )
        assert record.state == IdempotencyState.EXPIRED


class TestIdempotencyRecordStateTransitions:
    def test_mark_success(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_success({"result": "ok"})
        assert record.state == IdempotencyState.SUCCESS
        assert record.response_data == {"result": "ok"}
        assert record.error_message is None
        assert record.is_success is True
        assert record.is_processing is False

    def test_mark_failed(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_failed("something went wrong")
        assert record.state == IdempotencyState.FAILED
        assert record.error_message == "something went wrong"
        assert record.response_data is None
        assert record.is_failed is True
        assert record.is_processing is False

    def test_mark_success_from_failed_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_failed("err")
        with pytest.raises(ValueError, match="Cannot mark success"):
            record.mark_success("data")

    def test_mark_failed_from_success_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_success("data")
        with pytest.raises(ValueError, match="Cannot mark failed"):
            record.mark_failed("err")

    def test_mark_success_from_expired_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_expired()
        with pytest.raises(ValueError, match="Cannot mark success"):
            record.mark_success("data")

    def test_mark_expired(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        record.mark_expired()
        assert record.state == IdempotencyState.EXPIRED
        assert record.is_expired() is True


class TestIdempotencyRecordFingerprint:
    def test_fingerprint_matches(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp-1", created_at=0.0, expires_at=1.0)
        assert record.fingerprint_matches("fp-1") is True
        assert record.fingerprint_matches("fp-2") is False


class TestIdempotencyRecordExpiration:
    def test_record_auto_expires_with_clock(self):
        clock = ManualClock(start_time=0.0)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=clock.now(),
            expires_at=clock.now() + 0.05,
        )
        assert record.is_expired(clock) is False
        clock.advance(0.1)
        assert record.is_expired(clock) is True

    def test_remaining_ttl(self):
        clock = ManualClock(start_time=0.0)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=0.0,
            expires_at=3600.0,
        )
        remaining = record.remaining_ttl(clock)
        assert remaining == 3600.0

    def test_remaining_ttl_zero_when_expired(self):
        clock = ManualClock(start_time=100.0)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=0.0,
            expires_at=50.0,
        )
        remaining = record.remaining_ttl(clock)
        assert remaining == 0.0

    def test_refresh_ttl(self):
        clock = ManualClock(start_time=10.0)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=0.0,
            expires_at=20.0,
        )
        original_expiry = record.expires_at
        record.refresh_ttl(7200.0, clock)
        assert record.expires_at == clock.now() + 7200.0
        assert record.expires_at > original_expiry

    def test_refresh_ttl_negative_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        with pytest.raises(ValueError, match="ttl must be positive"):
            record.refresh_ttl(-1.0)

    def test_refresh_ttl_zero_rejected(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        with pytest.raises(ValueError, match="ttl must be positive"):
            record.refresh_ttl(0.0)


class TestIdempotencyRecordSnapshot:
    def test_snapshot_preserves_all_fields(self):
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            state=IdempotencyState.SUCCESS,
            response_data={"x": 1},
            error_message=None,
            created_at=10.0,
            expires_at=20.0,
        )
        snap = record.snapshot()
        assert snap.key == record.key
        assert snap.request_fingerprint == record.request_fingerprint
        assert snap.state == record.state
        assert snap.response_data == record.response_data
        assert snap.error_message == record.error_message
        assert snap.created_at == record.created_at
        assert snap.expires_at == record.expires_at

    def test_snapshot_is_independent_copy(self):
        record = IdempotencyRecord(key="k", request_fingerprint="fp", created_at=0.0, expires_at=1.0)
        snap = record.snapshot()
        record.mark_success("changed")
        assert snap.state == IdempotencyState.PROCESSING
        assert snap.response_data is None
        assert record.state == IdempotencyState.SUCCESS

    def test_snapshot_of_expired_record_no_validation_error(self):
        clock = ManualClock(start_time=100.0)
        record = IdempotencyRecord(
            key="k",
            request_fingerprint="fp",
            created_at=0.0,
            expires_at=50.0,
        )
        record.mark_expired()
        snap = record.snapshot()
        assert snap.state == IdempotencyState.EXPIRED
        assert snap.expires_at == 50.0
        assert snap.created_at == 0.0
