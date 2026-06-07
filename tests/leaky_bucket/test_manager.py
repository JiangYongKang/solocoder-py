from __future__ import annotations

import pytest

from solocoder_py.leaky_bucket import (
    BucketConfig,
    BucketRequest,
    InvalidBucketConfigError,
    OverflowStrategy,
    SubjectLeakyBucketManager,
)
from solocoder_py.ratelimiter import ManualClock


class TestSubjectRegistration:
    def test_register_subject(self, manual_clock):
        manager = SubjectLeakyBucketManager(clock=manual_clock)
        config = BucketConfig(capacity=3, leak_rate=1.0)

        manager.register_subject("user-1", config)
        assert manager.has_subject("user-1") is True

    def test_register_subject_with_strategy(self, manual_clock):
        manager = SubjectLeakyBucketManager(clock=manual_clock)
        config = BucketConfig(capacity=3, leak_rate=1.0)

        manager.register_subject(
            "user-1", config, overflow_strategy=OverflowStrategy.DROP_OLDEST
        )
        bucket = manager.get_bucket("user-1")
        assert bucket is not None
        assert bucket.overflow_strategy == OverflowStrategy.DROP_OLDEST

    def test_unregister_subject(self, manual_clock):
        manager = SubjectLeakyBucketManager(clock=manual_clock)
        config = BucketConfig(capacity=3, leak_rate=1.0)

        manager.register_subject("user-1", config)
        assert manager.has_subject("user-1") is True

        manager.unregister_subject("user-1")
        assert manager.has_subject("user-1") is False

    def test_unregister_nonexistent_no_error(self, default_manager):
        default_manager.unregister_subject("nonexistent")

    def test_register_with_invalid_config_raises(self, manual_clock):
        manager = SubjectLeakyBucketManager(clock=manual_clock)
        with pytest.raises(InvalidBucketConfigError):
            manager.register_subject(
                "user-1", BucketConfig(capacity=0, leak_rate=1.0)
            )


class TestSubjectIsolation:
    def test_subjects_have_independent_queues(self, default_manager, manual_clock):
        default_manager.enqueue("user-a", BucketRequest(id="a-1"))
        default_manager.enqueue("user-a", BucketRequest(id="a-2"))
        default_manager.enqueue("user-b", BucketRequest(id="b-1"))

        assert default_manager.current_size("user-a") == 2
        assert default_manager.current_size("user-b") == 1
        assert default_manager.has_subject("user-a")
        assert default_manager.has_subject("user-b")

    def test_subject_full_does_not_affect_others(self, default_manager):
        for i in range(3):
            result = default_manager.enqueue(
                "user-a", BucketRequest(id=f"a-{i}")
            )
            assert result.accepted is True

        result = default_manager.enqueue("user-a", BucketRequest(id="a-extra"))
        assert result.accepted is False

        result = default_manager.enqueue("user-b", BucketRequest(id="b-1"))
        assert result.accepted is True

    def test_subject_leak_independent(self, default_manager, manual_clock):
        for i in range(3):
            default_manager.enqueue("user-a", BucketRequest(id=f"a-{i}"))
        for i in range(3):
            default_manager.enqueue("user-b", BucketRequest(id=f"b-{i}"))

        manual_clock.advance(1.0)

        assert default_manager.current_size("user-a") == 2
        assert default_manager.current_size("user-b") == 2
        assert default_manager.get_processed_count("user-a") == 1
        assert default_manager.get_processed_count("user-b") == 1

    def test_subject_dropped_count_independent(self, default_manager):
        for i in range(3):
            default_manager.enqueue("user-a", BucketRequest(id=f"a-{i}"))

        default_manager.enqueue("user-a", BucketRequest(id="a-dropped"))

        assert default_manager.get_dropped_count("user-a") == 1
        assert default_manager.get_dropped_count("user-b") == 0

    def test_get_all_subject_ids(self, default_manager):
        default_manager.enqueue("user-a", BucketRequest(id="a-1"))
        default_manager.enqueue("user-b", BucketRequest(id="b-1"))
        default_manager.enqueue("user-c", BucketRequest(id="c-1"))

        ids = default_manager.get_all_subject_ids()
        assert len(ids) == 3
        assert "user-a" in ids
        assert "user-b" in ids
        assert "user-c" in ids


class TestDefaultConfigAutoCreate:
    def test_auto_create_with_default_config(self, default_manager):
        result = default_manager.enqueue("new-user", BucketRequest(id="req-1"))
        assert result.accepted is True
        assert default_manager.has_subject("new-user") is True
        bucket = default_manager.get_bucket("new-user")
        assert bucket.capacity == 3
        assert bucket.leak_rate == 1.0

    def test_no_default_config_raises(self, manual_clock):
        manager = SubjectLeakyBucketManager(clock=manual_clock)
        with pytest.raises(ValueError, match="not registered and no default config"):
            manager.enqueue("user-1", BucketRequest(id="req-1"))

    def test_registered_config_overrides_default(self, manual_clock):
        default_config = BucketConfig(capacity=3, leak_rate=1.0)
        manager = SubjectLeakyBucketManager(
            default_config=default_config, clock=manual_clock
        )

        custom_config = BucketConfig(capacity=10, leak_rate=5.0)
        manager.register_subject("custom-user", custom_config)

        for i in range(8):
            result = manager.enqueue("custom-user", BucketRequest(id=f"req-{i}"))
            assert result.accepted is True

        assert manager.current_size("custom-user") == 8


class TestSubjectOperations:
    def test_enqueue_result(self, default_manager):
        result = default_manager.enqueue("user-1", BucketRequest(id="req-1"))
        assert result.accepted is True
        assert result.queue_position == 1
        assert result.estimated_wait_seconds == 1.0

    def test_peek_next(self, default_manager):
        default_manager.enqueue("user-1", BucketRequest(id="first"))
        default_manager.enqueue("user-1", BucketRequest(id="second"))

        peeked = default_manager.peek_next("user-1")
        assert peeked is not None
        assert peeked.id == "first"

    def test_peek_next_empty(self, default_manager):
        assert default_manager.peek_next("user-1") is None

    def test_get_all_pending(self, default_manager):
        for i in range(3):
            default_manager.enqueue("user-1", BucketRequest(id=f"req-{i}"))

        pending = default_manager.get_all_pending("user-1")
        assert len(pending) == 3
        assert [r.id for r in pending] == ["req-0", "req-1", "req-2"]

    def test_is_empty_and_is_full(self, default_manager):
        assert default_manager.is_empty("user-1") is True
        assert default_manager.is_full("user-1") is False

        for i in range(3):
            default_manager.enqueue("user-1", BucketRequest(id=f"req-{i}"))

        assert default_manager.is_empty("user-1") is False
        assert default_manager.is_full("user-1") is True

    def test_get_state(self, default_manager, manual_clock):
        for i in range(3):
            default_manager.enqueue("user-1", BucketRequest(id=f"req-{i}"))

        manual_clock.advance(2.0)

        state = default_manager.get_state("user-1")
        assert state.capacity == 3
        assert state.leak_rate == 1.0
        assert state.current_size == 1
        assert state.processed_count == 2


class TestSubjectClearAndReset:
    def test_clear_subject(self, default_manager):
        for i in range(3):
            default_manager.enqueue("user-1", BucketRequest(id=f"req-{i}"))
        default_manager.enqueue("user-1", BucketRequest(id="dropped"))

        default_manager.clear_subject("user-1")

        assert default_manager.current_size("user-1") == 0
        assert default_manager.is_empty("user-1")
        assert default_manager.get_dropped_count("user-1") == 1

    def test_reset_subject(self, default_manager, manual_clock):
        for i in range(3):
            default_manager.enqueue("user-1", BucketRequest(id=f"req-{i}"))
        manual_clock.advance(1.0)
        default_manager.enqueue("user-1", BucketRequest(id="dropped"))

        default_manager.reset_subject("user-1")

        assert default_manager.current_size("user-1") == 0
        assert default_manager.get_processed_count("user-1") == 0
        assert default_manager.get_dropped_count("user-1") == 0

    def test_clear_all(self, default_manager):
        default_manager.enqueue("user-a", BucketRequest(id="a-1"))
        default_manager.enqueue("user-a", BucketRequest(id="a-2"))
        default_manager.enqueue("user-b", BucketRequest(id="b-1"))

        default_manager.clear_all()

        assert default_manager.current_size("user-a") == 0
        assert default_manager.current_size("user-b") == 0

    def test_reset_all(self, default_manager, manual_clock):
        default_manager.enqueue("user-a", BucketRequest(id="a-1"))
        default_manager.enqueue("user-b", BucketRequest(id="b-1"))
        manual_clock.advance(2.0)
        default_manager.enqueue("user-a", BucketRequest(id="a-dropped"))

        default_manager.reset_all()

        assert default_manager.current_size("user-a") == 0
        assert default_manager.current_size("user-b") == 0
        assert default_manager.get_processed_count("user-a") == 0
        assert default_manager.get_processed_count("user-b") == 0
        assert default_manager.get_dropped_count("user-a") == 0


class TestDifferentSubjectStrategies:
    def test_different_subjects_different_strategies(self, manual_clock):
        config = BucketConfig(capacity=2, leak_rate=1.0)
        manager = SubjectLeakyBucketManager(
            default_config=config,
            default_overflow_strategy=OverflowStrategy.REJECT_NEW,
            clock=manual_clock,
        )

        manager.register_subject(
            "dropper",
            config,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
        )

        for i in range(2):
            manager.enqueue("rejector", BucketRequest(id=f"r-{i}"))
            manager.enqueue("dropper", BucketRequest(id=f"d-{i}"))

        reject_result = manager.enqueue("rejector", BucketRequest(id="r-extra"))
        assert reject_result.accepted is False

        drop_result = manager.enqueue("dropper", BucketRequest(id="d-new"))
        assert drop_result.accepted is True
        assert drop_result.dropped_request.id == "d-0"
