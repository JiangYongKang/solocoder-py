import threading
from time import sleep

import pytest

from solocoder_py.idempotency import (
    FailureReplayPolicy,
    IdempotencyProcessingError,
    IdempotencyKeyConflictError,
    IdempotencyKeyExpiredError,
    IdempotencyKeyMismatchError,
    IdempotencyResult,
    IdempotencyState,
    IdempotencyStore,
    ManualClock,
)
from .conftest import make_store, make_manual_clock


class TestStoreConfiguration:
    def test_default_configuration(self):
        store = make_store()
        assert store.default_ttl_seconds == 86400.0
        assert store.failure_replay_policy == FailureReplayPolicy.REJECT
        assert store.wait_timeout_seconds == 30.0

    def test_negative_default_ttl_rejected(self):
        with pytest.raises(ValueError, match="default_ttl_seconds must be positive"):
            IdempotencyStore(default_ttl_seconds=-1.0)

    def test_zero_default_ttl_rejected(self):
        with pytest.raises(ValueError, match="default_ttl_seconds must be positive"):
            IdempotencyStore(default_ttl_seconds=0.0)

    def test_negative_wait_timeout_rejected(self):
        with pytest.raises(ValueError, match="wait_timeout_seconds must be positive"):
            IdempotencyStore(wait_timeout_seconds=-1.0)

    def test_zero_wait_poll_interval_rejected(self):
        with pytest.raises(ValueError, match="wait_poll_interval_seconds must be positive"):
            IdempotencyStore(wait_poll_interval_seconds=0.0)

    def test_clock_injection(self):
        clock = make_manual_clock(start_time=1234.5)
        store = make_store(clock=clock)
        store.begin_request("k", "fp")
        record = store.get_record("k")
        assert record is not None
        assert record.created_at == 1234.5


class TestBeginRequest:
    def test_begin_new_key_returns_should_execute(self):
        store = make_store()
        result = store.begin_request("key-1", "fp-1")
        assert isinstance(result, IdempotencyResult)
        assert result.should_execute is True
        assert result.is_replay is False
        assert result.state == IdempotencyState.PROCESSING

    def test_begin_empty_key_rejected(self):
        store = make_store()
        with pytest.raises(ValueError, match="key cannot be empty"):
            store.begin_request("", "fp")

    def test_begin_empty_fingerprint_rejected(self):
        store = make_store()
        with pytest.raises(ValueError, match="request_fingerprint cannot be empty"):
            store.begin_request("k", "")

    def test_begin_negative_ttl_rejected(self):
        store = make_store()
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            store.begin_request("k", "fp", ttl_seconds=-1.0)

    def test_begin_with_custom_ttl(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(clock=clock)
        store.begin_request("k", "fp", ttl_seconds=7200.0)
        record = store.get_record("k")
        assert record is not None
        assert record.expires_at == 7200.0
        remaining = record.remaining_ttl(clock)
        assert remaining == 7200.0


class TestNormalFlowSuccess:
    def test_first_processing_success(self):
        store = make_store()
        result = store.begin_request("key-1", "fp-1")
        assert result.should_execute is True

        complete_result = store.complete_success("key-1", "fp-1", {"data": "hello"})
        assert complete_result.state == IdempotencyState.SUCCESS
        assert complete_result.response_data == {"data": "hello"}
        assert complete_result.is_replay is False

    def test_same_request_result_replay(self):
        store = make_store()
        store.begin_request("key-1", "fp-1")
        store.complete_success("key-1", "fp-1", {"data": "hello"})

        replay_result = store.begin_request("key-1", "fp-1")
        assert replay_result.should_execute is False
        assert replay_result.is_replay is True
        assert replay_result.state == IdempotencyState.SUCCESS
        assert replay_result.response_data == {"data": "hello"}

    def test_execute_with_idempotency_success(self):
        store = make_store()
        call_count = [0]

        def operation():
            call_count[0] += 1
            return {"value": 42}

        result1 = store.execute_with_idempotency("key-exec", "fp-exec", operation)
        assert result1.state == IdempotencyState.SUCCESS
        assert result1.response_data == {"value": 42}
        assert result1.is_replay is False
        assert call_count[0] == 1

        result2 = store.execute_with_idempotency("key-exec", "fp-exec", operation)
        assert result2.state == IdempotencyState.SUCCESS
        assert result2.response_data == {"value": 42}
        assert result2.is_replay is True
        assert call_count[0] == 1


class TestNormalFlowExpiredRecreate:
    def test_expired_then_reprocess(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(default_ttl_seconds=60.0, clock=clock)
        store.begin_request("key-exp", "fp-exp")
        store.complete_success("key-exp", "fp-exp", {"old": "data"})

        clock.advance(61.0)

        result = store.begin_request("key-exp", "fp-exp")
        assert result.should_execute is True
        assert result.is_replay is False
        assert result.state == IdempotencyState.PROCESSING

        store.complete_success("key-exp", "fp-exp", {"new": "data"})
        final_result = store.begin_request("key-exp", "fp-exp")
        assert final_result.response_data == {"new": "data"}


class TestFingerprintBinding:
    def test_same_key_different_fingerprint_rejected(self):
        store = make_store()
        store.begin_request("key-1", "fp-1")
        with pytest.raises(IdempotencyKeyMismatchError):
            store.begin_request("key-1", "fp-2")

    def test_same_key_different_fingerprint_after_success_rejected(self):
        store = make_store()
        store.begin_request("key-1", "fp-1")
        store.complete_success("key-1", "fp-1", {"data": "ok"})
        with pytest.raises(IdempotencyKeyMismatchError):
            store.begin_request("key-1", "fp-2")

    def test_different_key_same_fingerprint_allowed(self):
        store = make_store()
        result1 = store.begin_request("key-1", "fp-shared")
        result2 = store.begin_request("key-2", "fp-shared")
        assert result1.should_execute is True
        assert result2.should_execute is True


class TestFailureReplayPolicies:
    def test_reject_policy_raises_on_failure(self):
        store = make_store(failure_replay_policy=FailureReplayPolicy.REJECT)
        store.begin_request("key-f", "fp-f")
        store.complete_failure("key-f", "fp-f", "something broke")

        with pytest.raises(IdempotencyProcessingError, match="something broke"):
            store.begin_request("key-f", "fp-f")

    def test_replay_policy_returns_failure(self):
        store = make_store(failure_replay_policy=FailureReplayPolicy.REPLAY)
        store.begin_request("key-f", "fp-f")
        store.complete_failure("key-f", "fp-f", "something broke")

        result = store.begin_request("key-f", "fp-f")
        assert result.is_replay is True
        assert result.should_execute is False
        assert result.state == IdempotencyState.FAILED
        assert result.error_message == "something broke"

    def test_retry_policy_allows_retry(self):
        store = make_store(failure_replay_policy=FailureReplayPolicy.RETRY)
        store.begin_request("key-f", "fp-f")
        store.complete_failure("key-f", "fp-f", "something broke")

        result = store.begin_request("key-f", "fp-f")
        assert result.is_replay is False
        assert result.should_execute is True
        assert result.state == IdempotencyState.PROCESSING


class TestCompleteSuccessAndFailure:
    def test_complete_success_empty_key_rejected(self):
        store = make_store()
        with pytest.raises(ValueError, match="key cannot be empty"):
            store.complete_success("", "fp", "data")

    def test_complete_success_empty_fingerprint_rejected(self):
        store = make_store()
        with pytest.raises(ValueError, match="request_fingerprint cannot be empty"):
            store.complete_success("k", "", "data")

    def test_complete_failure_empty_error_rejected(self):
        store = make_store()
        store.begin_request("k", "fp")
        with pytest.raises(ValueError, match="error_message cannot be empty"):
            store.complete_failure("k", "fp", "")

    def test_complete_success_unknown_key(self):
        store = make_store()
        with pytest.raises(Exception):
            store.complete_success("unknown", "fp", "data")

    def test_complete_success_wrong_fingerprint(self):
        store = make_store()
        store.begin_request("k", "fp-1")
        with pytest.raises(IdempotencyKeyMismatchError):
            store.complete_success("k", "fp-2", "data")

    def test_complete_failure_records_error(self):
        store = make_store()
        store.begin_request("k", "fp")
        result = store.complete_failure("k", "fp", "network error")
        assert result.state == IdempotencyState.FAILED
        assert result.error_message == "network error"

    def test_execute_with_idempotency_failure_raises(self):
        store = make_store()

        def failing_op():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            store.execute_with_idempotency("k", "fp", failing_op)

        record = store.get_record("k")
        assert record is not None
        assert record.state == IdempotencyState.FAILED
        assert record.error_message == "boom"

    def test_execute_with_idempotency_not_callable(self):
        store = make_store()
        with pytest.raises(ValueError, match="operation must be callable"):
            store.execute_with_idempotency("k", "fp", "not callable")


class TestProcessingStateAndConcurrency:
    def test_concurrent_first_request_wins(self):
        store = make_store(
            wait_timeout_seconds=5.0,
            wait_poll_interval_seconds=0.01,
        )
        barrier = threading.Barrier(2, timeout=5)
        execution_counter = [0]
        counter_lock = threading.Lock()
        errors = {}

        def thread_fn(thread_id):
            try:
                barrier.wait(timeout=5)
                result = store.begin_request("concurrent-key", "fp-concurrent")
                if result.should_execute:
                    with counter_lock:
                        execution_counter[0] += 1
                    sleep(0.1)
                    store.complete_success(
                        "concurrent-key", "fp-concurrent", f"from-{thread_id}"
                    )
            except Exception as e:
                errors[thread_id] = e

        t1 = threading.Thread(target=thread_fn, args=(1,))
        t2 = threading.Thread(target=thread_fn, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert len(errors) == 0, f"Errors: {errors}"
        assert execution_counter[0] == 1, (
            f"Expected exactly one executor, got {execution_counter[0]}"
        )

        final_record = store.get_record("concurrent-key")
        assert final_record is not None
        assert final_record.state == IdempotencyState.SUCCESS

    def test_concurrent_second_reads_final_result(self):
        store = make_store(wait_poll_interval_seconds=0.01)
        result_holder = {}

        def first_thread():
            result = store.begin_request("key-wait", "fp-wait")
            assert result.should_execute is True
            result_holder["first"] = result
            sleep(0.1)
            store.complete_success("key-wait", "fp-wait", {"from": "first"})

        def second_thread():
            sleep(0.02)
            result = store.begin_request("key-wait", "fp-wait")
            result_holder["second"] = result

        t1 = threading.Thread(target=first_thread)
        t2 = threading.Thread(target=second_thread)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert "second" in result_holder
        second_result = result_holder["second"]
        assert second_result.is_replay is True
        assert second_result.response_data == {"from": "first"}

    def test_wait_timeout_raises_conflict(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(
            wait_timeout_seconds=0.05,
            wait_poll_interval_seconds=0.01,
            clock=clock,
        )
        store.begin_request("key-timeout", "fp-timeout")

        clock.advance(0.1)

        with pytest.raises(IdempotencyKeyConflictError):
            store.begin_request("key-timeout", "fp-timeout")


class TestTTLAndExpiration:
    def test_ttl_just_expired_cleanup_on_access(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(default_ttl_seconds=60.0, clock=clock)
        store.begin_request("key-ttl", "fp-ttl")
        store.complete_success("key-ttl", "fp-ttl", {"data": "ok"})

        clock.advance(60.0)

        result = store.begin_request("key-ttl", "fp-ttl")
        assert result.should_execute is True
        assert result.state == IdempotencyState.PROCESSING

    def test_complete_success_on_expired_key(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(default_ttl_seconds=60.0, clock=clock)
        store.begin_request("key-exp-complete", "fp")

        clock.advance(61.0)

        with pytest.raises(IdempotencyKeyExpiredError):
            store.complete_success("key-exp-complete", "fp", "data")

    def test_cleanup_expired(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(default_ttl_seconds=60.0, clock=clock)
        store.begin_request("k1", "fp1")
        store.begin_request("k2", "fp2")
        store.complete_success("k1", "fp1", "d1")

        clock.advance(61.0)

        removed = store.cleanup_expired()
        assert removed == 1
        assert store.exists("k1") is False
        assert store.exists("k2") is True

    def test_lazy_expiration_in_get_record(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(default_ttl_seconds=60.0, clock=clock)
        store.begin_request("lazy-key", "fp")

        clock.advance(61.0)

        record = store.get_record("lazy-key")
        assert record is not None
        assert record.state == IdempotencyState.EXPIRED
        assert record.expires_at == 60.0
        assert record.created_at == 0.0


class TestQueriesAndManagement:
    def test_get_record_nonexistent(self):
        store = make_store()
        assert store.get_record("nonexistent") is None

    def test_get_record_empty_key(self):
        store = make_store()
        with pytest.raises(ValueError, match="key cannot be empty"):
            store.get_record("")

    def test_exists(self):
        store = make_store()
        assert store.exists("k") is False
        store.begin_request("k", "fp")
        assert store.exists("k") is True

    def test_invalidate(self):
        store = make_store()
        assert store.invalidate("k") is False
        store.begin_request("k", "fp")
        assert store.invalidate("k") is True
        assert store.exists("k") is False

    def test_invalidate_empty_key(self):
        store = make_store()
        with pytest.raises(ValueError, match="key cannot be empty"):
            store.invalidate("")

    def test_clear(self):
        store = make_store()
        store.begin_request("k1", "fp1")
        store.begin_request("k2", "fp2")
        assert store.count() == 2
        store.clear()
        assert store.count() == 0

    def test_count(self):
        store = make_store()
        assert store.count() == 0
        store.begin_request("k1", "fp1")
        assert store.count() == 1
