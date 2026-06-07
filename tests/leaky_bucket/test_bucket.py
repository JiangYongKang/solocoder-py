from __future__ import annotations

import pytest

from solocoder_py.leaky_bucket import (
    BucketConfig,
    BucketRequest,
    InvalidBucketConfigError,
    LeakyBucket,
    OverflowStrategy,
)
from solocoder_py.ratelimiter import ManualClock


class TestBucketConfigValidation:
    def test_valid_config(self):
        config = BucketConfig(capacity=10, leak_rate=5.0)
        assert config.capacity == 10
        assert config.leak_rate == 5.0

    def test_invalid_capacity_zero(self):
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            BucketConfig(capacity=0, leak_rate=1.0)

    def test_invalid_capacity_negative(self):
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            BucketConfig(capacity=-1, leak_rate=1.0)

    def test_invalid_leak_rate_zero(self):
        with pytest.raises(InvalidBucketConfigError, match="leak_rate must be positive"):
            BucketConfig(capacity=10, leak_rate=0.0)

    def test_invalid_leak_rate_negative(self):
        with pytest.raises(InvalidBucketConfigError, match="leak_rate must be positive"):
            BucketConfig(capacity=10, leak_rate=-1.0)

    def test_bucket_rejects_invalid_config(self, manual_clock):
        with pytest.raises(InvalidBucketConfigError):
            LeakyBucket(
                config=BucketConfig(capacity=0, leak_rate=1.0),
                clock=manual_clock,
            )


class TestBucketBasicOperations:
    def test_empty_bucket_initially(self, basic_bucket):
        assert basic_bucket.is_empty() is True
        assert basic_bucket.is_full() is False
        assert basic_bucket.current_size() == 0
        assert basic_bucket.processed_count == 0
        assert basic_bucket.dropped_count == 0

    def test_bucket_properties(self, basic_bucket, bucket_config):
        assert basic_bucket.capacity == bucket_config.capacity
        assert basic_bucket.leak_rate == bucket_config.leak_rate
        assert basic_bucket.overflow_strategy == OverflowStrategy.REJECT_NEW

    def test_single_request_enqueue(self, basic_bucket, manual_clock):
        request = BucketRequest(id="req-1")
        result = basic_bucket.enqueue(request)

        assert result.accepted is True
        assert result.request.id == "req-1"
        assert result.queue_position == 1
        assert result.estimated_wait_seconds == 0.5
        assert result.estimated_start_time == 0.5
        assert basic_bucket.current_size() == 1
        assert basic_bucket.is_empty() is False

    def test_multiple_requests_enqueue_positions(self, basic_bucket, manual_clock):
        for i in range(3):
            request = BucketRequest(id=f"req-{i}")
            result = basic_bucket.enqueue(request)
            assert result.accepted is True
            assert result.queue_position == i + 1
            assert result.estimated_wait_seconds == (i + 1) / 2.0
            assert result.estimated_start_time == (i + 1) / 2.0

        assert basic_bucket.current_size() == 3

    def test_enqueue_to_capacity(self, basic_bucket):
        for i in range(5):
            request = BucketRequest(id=f"req-{i}")
            result = basic_bucket.enqueue(request)
            assert result.accepted is True

        assert basic_bucket.current_size() == 5
        assert basic_bucket.is_full() is True


class TestLeakyRateAndLazyLeak:
    def test_lazy_leak_after_time_passes(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
        assert basic_bucket.current_size() == 5

        manual_clock.advance(1.0)
        assert basic_bucket.current_size() == 3
        assert basic_bucket.processed_count == 2

    def test_lazy_leak_partial_request(self, basic_bucket, manual_clock):
        for i in range(3):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(0.75)
        assert basic_bucket.current_size() == 2
        assert basic_bucket.processed_count == 1

    def test_lazy_leak_all_requests(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(10.0)
        assert basic_bucket.current_size() == 0
        assert basic_bucket.is_empty() is True
        assert basic_bucket.processed_count == 5

    def test_lazy_leak_no_time_passed(self, basic_bucket, manual_clock):
        basic_bucket.enqueue(BucketRequest(id="req-1"))
        assert basic_bucket.current_size() == 1
        manual_clock.advance(0.0)
        assert basic_bucket.current_size() == 1

    def test_lazy_leak_on_enqueue(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
        assert basic_bucket.is_full() is True

        manual_clock.advance(1.0)
        request = BucketRequest(id="req-5")
        result = basic_bucket.enqueue(request)
        assert result.accepted is True
        assert basic_bucket.current_size() == 4

    def test_leak_rate_boundary_high_rate(self, manual_clock):
        config = BucketConfig(capacity=10, leak_rate=1000.0)
        bucket = LeakyBucket(config=config, clock=manual_clock)

        for i in range(10):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(0.01)
        assert bucket.current_size() == 0
        assert bucket.processed_count == 10

    def test_leak_rate_boundary_very_low(self, manual_clock):
        config = BucketConfig(capacity=5, leak_rate=0.1)
        bucket = LeakyBucket(config=config, clock=manual_clock)

        bucket.enqueue(BucketRequest(id="req-1"))
        manual_clock.advance(5.0)
        assert bucket.current_size() == 1
        assert bucket.processed_count == 0

        manual_clock.advance(5.0)
        assert bucket.current_size() == 0
        assert bucket.processed_count == 1


class TestWaitTimeEstimation:
    def test_first_request_wait_time(self, basic_bucket, manual_clock):
        result = basic_bucket.enqueue(BucketRequest(id="req-1"))
        assert result.estimated_wait_seconds == 0.5
        assert result.estimated_start_time == manual_clock.now() + 0.5

    def test_position_corresponds_to_wait_time(self, basic_bucket):
        positions = []
        for i in range(5):
            result = basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
            positions.append((result.queue_position, result.estimated_wait_seconds))

        for pos, wait in positions:
            assert wait == pos / 2.0

    def test_after_leak_wait_time_adjusts(self, basic_bucket, manual_clock):
        for i in range(4):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(1.0)

        result = basic_bucket.enqueue(BucketRequest(id="req-4"))
        assert result.queue_position == 3
        assert result.estimated_wait_seconds == 1.5


class TestOverflowStrategyRejectNew:
    def test_reject_new_over_capacity(self, basic_bucket):
        for i in range(5):
            result = basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
            assert result.accepted is True

        extra = BucketRequest(id="req-extra")
        result = basic_bucket.enqueue(extra)

        assert result.accepted is False
        assert result.overflow_strategy == OverflowStrategy.REJECT_NEW
        assert result.queue_position == 0
        assert result.estimated_wait_seconds is None
        assert result.dropped_request is None
        assert basic_bucket.current_size() == 5
        assert basic_bucket.dropped_count == 1

    def test_reject_new_records_dropped(self, basic_bucket):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        basic_bucket.enqueue(BucketRequest(id="extra-1"))
        basic_bucket.enqueue(BucketRequest(id="extra-2"))

        assert basic_bucket.dropped_count == 2
        records = basic_bucket.dropped_records
        assert len(records) == 2
        assert records[0].request.id == "extra-1"
        assert records[0].reason == OverflowStrategy.REJECT_NEW
        assert records[1].request.id == "extra-2"


class TestOverflowStrategyDropOldest:
    def test_drop_oldest_accepts_new(self, manual_clock, bucket_config):
        bucket = LeakyBucket(
            config=bucket_config,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
            clock=manual_clock,
        )

        for i in range(5):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        new_req = BucketRequest(id="req-new")
        result = bucket.enqueue(new_req)

        assert result.accepted is True
        assert result.overflow_strategy == OverflowStrategy.DROP_OLDEST
        assert result.dropped_request.id == "req-0"
        assert bucket.current_size() == 5
        assert bucket.dropped_count == 1

    def test_drop_oldest_preserves_recent(self, manual_clock, bucket_config):
        bucket = LeakyBucket(
            config=bucket_config,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
            clock=manual_clock,
        )

        for i in range(5):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        bucket.enqueue(BucketRequest(id="req-new-1"))
        bucket.enqueue(BucketRequest(id="req-new-2"))

        pending = bucket.get_all_pending()
        pending_ids = [r.id for r in pending]
        assert "req-0" not in pending_ids
        assert "req-1" not in pending_ids
        assert "req-new-1" in pending_ids
        assert "req-new-2" in pending_ids
        assert bucket.dropped_count == 2

    def test_drop_oldest_records(self, manual_clock, bucket_config):
        bucket = LeakyBucket(
            config=bucket_config,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
            clock=manual_clock,
        )

        for i in range(5):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        result = bucket.enqueue(BucketRequest(id="req-new"))
        dropped = result.dropped_request

        records = bucket.dropped_records
        assert len(records) == 1
        assert records[0].request.id == dropped.id
        assert records[0].reason == OverflowStrategy.DROP_OLDEST


class TestOverflowStrategyDropNewest:
    def test_drop_newest_rejects_incoming(self, manual_clock, bucket_config):
        bucket = LeakyBucket(
            config=bucket_config,
            overflow_strategy=OverflowStrategy.DROP_NEWEST,
            clock=manual_clock,
        )

        for i in range(5):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        new_req = BucketRequest(id="req-new")
        result = bucket.enqueue(new_req)

        assert result.accepted is False
        assert result.overflow_strategy == OverflowStrategy.DROP_NEWEST
        assert result.dropped_request.id == "req-new"
        assert bucket.current_size() == 5
        assert bucket.dropped_count == 1

    def test_drop_newest_preserves_existing(self, manual_clock, bucket_config):
        bucket = LeakyBucket(
            config=bucket_config,
            overflow_strategy=OverflowStrategy.DROP_NEWEST,
            clock=manual_clock,
        )

        for i in range(5):
            bucket.enqueue(BucketRequest(id=f"req-{i}"))

        bucket.enqueue(BucketRequest(id="extra-1"))
        bucket.enqueue(BucketRequest(id="extra-2"))

        pending = bucket.get_all_pending()
        pending_ids = [r.id for r in pending]
        for i in range(5):
            assert f"req-{i}" in pending_ids

        assert bucket.dropped_count == 2
        dropped_ids = [r.request.id for r in bucket.dropped_records]
        assert "extra-1" in dropped_ids
        assert "extra-2" in dropped_ids


class TestBoundaryConditions:
    def test_empty_bucket_peek_returns_none(self, basic_bucket):
        assert basic_bucket.peek_next() is None

    def test_full_bucket_peek_returns_first(self, basic_bucket):
        first = BucketRequest(id="first")
        basic_bucket.enqueue(first)
        for i in range(1, 5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        peeked = basic_bucket.peek_next()
        assert peeked is not None
        assert peeked.id == "first"
        assert basic_bucket.current_size() == 5

    def test_peek_does_not_remove(self, basic_bucket):
        basic_bucket.enqueue(BucketRequest(id="req-1"))
        basic_bucket.peek_next()
        basic_bucket.peek_next()
        assert basic_bucket.current_size() == 1

    def test_get_state_reflects_lazy_leak(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(0.5)
        state = basic_bucket.get_state()

        assert state.capacity == 5
        assert state.leak_rate == 2.0
        assert state.current_size == 4
        assert state.processed_count == 1
        assert state.dropped_count == 0

    def test_clear_empties_queue_preserves_dropped(self, basic_bucket):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
        basic_bucket.enqueue(BucketRequest(id="extra"))

        basic_bucket.clear()
        assert basic_bucket.current_size() == 0
        assert basic_bucket.is_empty() is True
        assert basic_bucket.dropped_count == 1

    def test_reset_clears_everything(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))
        manual_clock.advance(1.0)
        basic_bucket.enqueue(BucketRequest(id="extra"))

        basic_bucket.reset()
        assert basic_bucket.current_size() == 0
        assert basic_bucket.processed_count == 0
        assert basic_bucket.dropped_count == 0

    def test_request_auto_generates_id(self):
        req = BucketRequest(id="")
        assert req.id != ""
        assert len(req.id) > 0

    def test_get_all_pending_returns_copy(self, basic_bucket):
        for i in range(3):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        pending = basic_bucket.get_all_pending()
        assert len(pending) == 3

        pending.clear()
        assert basic_bucket.current_size() == 3


class TestGetAllPendingAndPeek:
    def test_get_all_pending_after_leak(self, basic_bucket, manual_clock):
        for i in range(5):
            basic_bucket.enqueue(BucketRequest(id=f"req-{i}"))

        manual_clock.advance(1.0)
        pending = basic_bucket.get_all_pending()

        assert len(pending) == 3
        assert pending[0].id == "req-2"
        assert pending[-1].id == "req-4"

    def test_enqueue_sets_timestamps(self, basic_bucket, manual_clock):
        request = BucketRequest(id="req-1", payload={"key": "value"})
        result = basic_bucket.enqueue(request)

        assert result.request.enqueued_at == 0.0
        assert result.request.scheduled_at == 0.5
        assert result.request.payload == {"key": "value"}
