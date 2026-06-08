import threading
from time import sleep

import pytest

from solocoder_py.inbox import (
    DedupResult,
    DedupStats,
    DedupWindowMode,
    DedupWindowConfigError,
    InboxDedupStore,
    InboxMessageRecord,
    ManualClock,
)
from .conftest import make_store, make_manual_clock


class TestConfiguration:
    def test_count_mode_config(self):
        store = make_store(max_count=100)
        assert store.window_mode == DedupWindowMode.COUNT
        assert store.max_count == 100
        assert store.max_time_seconds is None

    def test_time_mode_config(self):
        store = make_store(max_time_seconds=60.0)
        assert store.window_mode == DedupWindowMode.TIME
        assert store.max_time_seconds == 60.0
        assert store.max_count is None

    def test_hybrid_mode_config(self):
        store = make_store(max_count=100, max_time_seconds=60.0)
        assert store.window_mode == DedupWindowMode.HYBRID
        assert store.max_count == 100
        assert store.max_time_seconds == 60.0

    def test_must_have_at_least_one_window_constraint(self):
        with pytest.raises(DedupWindowConfigError):
            InboxDedupStore()

    def test_invalid_max_count(self):
        with pytest.raises(DedupWindowConfigError, match="max_count must be positive"):
            InboxDedupStore(max_count=0)
        with pytest.raises(DedupWindowConfigError, match="max_count must be positive"):
            InboxDedupStore(max_count=-1)

    def test_invalid_max_time_seconds(self):
        with pytest.raises(DedupWindowConfigError, match="max_time_seconds must be positive"):
            InboxDedupStore(max_time_seconds=0.0)
        with pytest.raises(DedupWindowConfigError, match="max_time_seconds must be positive"):
            InboxDedupStore(max_time_seconds=-1.0)

    def test_invalid_ttl(self):
        with pytest.raises(DedupWindowConfigError, match="ttl_seconds must be positive"):
            InboxDedupStore(max_count=10, ttl_seconds=0.0)
        with pytest.raises(DedupWindowConfigError, match="ttl_seconds must be positive"):
            InboxDedupStore(max_count=10, ttl_seconds=-1.0)

    def test_invalid_cleanup_interval(self):
        with pytest.raises(DedupWindowConfigError, match="cleanup_interval_seconds must be positive"):
            InboxDedupStore(max_count=10, cleanup_interval_seconds=0.0)
        with pytest.raises(DedupWindowConfigError, match="cleanup_interval_seconds must be positive"):
            InboxDedupStore(max_count=10, cleanup_interval_seconds=-1.0)

    def test_empty_message_id_rejected(self):
        store = make_store(max_count=10)
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.check_duplicate("")
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.contains("")
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.get_record("")
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.remove("")

    def test_clock_injection(self):
        clock = make_manual_clock(start_time=1234.5)
        store = make_store(max_count=10, clock=clock)
        result = store.check_duplicate("msg-1")
        assert result.record is not None
        assert result.record.received_at == 1234.5


class TestBasicDedup:
    def test_first_message_not_duplicate(self):
        store = make_store(max_count=100)
        result = store.check_duplicate("msg-1")
        assert isinstance(result, DedupResult)
        assert result.is_duplicate is False
        assert result.should_process is True
        assert result.record is not None
        assert result.record.message_id == "msg-1"

    def test_same_message_second_time_is_duplicate(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-1")
        result = store.check_duplicate("msg-1")
        assert result.is_duplicate is True
        assert result.should_process is False
        assert result.record is not None
        assert result.record.message_id == "msg-1"

    def test_different_messages_not_duplicate(self):
        store = make_store(max_count=100)
        r1 = store.check_duplicate("msg-1")
        r2 = store.check_duplicate("msg-2")
        assert r1.is_duplicate is False
        assert r2.is_duplicate is False
        assert store.window_count() == 2

    def test_multiple_duplicates(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-a")
        for _ in range(5):
            r = store.check_duplicate("msg-a")
            assert r.is_duplicate is True

    def test_contains_and_get_record(self):
        store = make_store(max_count=100)
        assert store.contains("msg-x") is False
        assert store.get_record("msg-x") is None

        store.check_duplicate("msg-x")
        assert store.contains("msg-x") is True
        record = store.get_record("msg-x")
        assert isinstance(record, InboxMessageRecord)
        assert record.message_id == "msg-x"

    def test_get_record_returns_snapshot(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, clock=clock)
        store.check_duplicate("msg-snap")
        record = store.get_record("msg-snap")
        assert record is not None
        clock.advance(10.0)
        assert record.age_seconds(clock) == 10.0


class TestOutOfOrderArrival:
    def test_out_of_order_messages_not_duplicate(self):
        store = make_store(max_count=100)
        r3 = store.check_duplicate("msg-3")
        r1 = store.check_duplicate("msg-1")
        r2 = store.check_duplicate("msg-2")
        assert r1.is_duplicate is False
        assert r2.is_duplicate is False
        assert r3.is_duplicate is False
        assert store.window_count() == 3

    def test_out_of_order_duplicate_detected(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-3")
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        r1_dup = store.check_duplicate("msg-1")
        r3_dup = store.check_duplicate("msg-3")
        assert r1_dup.is_duplicate is True
        assert r3_dup.is_duplicate is True
        assert store.window_count() == 3

    def test_complex_out_of_order_scenario(self):
        store = make_store(max_count=10)
        send_order = [f"msg-{i}" for i in range(1, 11)]
        arrival_order = [
            "msg-5", "msg-2", "msg-8", "msg-1", "msg-10",
            "msg-4", "msg-7", "msg-3", "msg-9", "msg-6",
        ]
        for msg_id in arrival_order:
            r = store.check_duplicate(msg_id)
            assert r.is_duplicate is False
        for msg_id in send_order:
            r = store.check_duplicate(msg_id)
            assert r.is_duplicate is True
        assert store.window_count() == 10


class TestCountBasedSlidingWindow:
    def test_count_window_evicts_oldest(self):
        store = make_store(max_count=3)
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        store.check_duplicate("msg-3")
        assert store.window_count() == 3

        store.check_duplicate("msg-4")
        assert store.window_count() == 3
        assert store.contains("msg-1") is False
        assert store.contains("msg-2") is True
        assert store.contains("msg-3") is True
        assert store.contains("msg-4") is True

    def test_count_window_boundary_exactly_full(self):
        store = make_store(max_count=3)
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        store.check_duplicate("msg-3")
        assert store.window_count() == 3
        assert store.contains("msg-1") is True
        assert store.contains("msg-2") is True
        assert store.contains("msg-3") is True

    def test_count_window_evicted_message_treated_as_new(self):
        store = make_store(max_count=2)
        store.check_duplicate("msg-A")
        store.check_duplicate("msg-B")
        store.check_duplicate("msg-C")
        assert store.contains("msg-A") is False

        result = store.check_duplicate("msg-A")
        assert result.is_duplicate is False
        assert result.should_process is True
        assert store.window_count() == 2
        assert store.contains("msg-A") is True
        assert store.contains("msg-B") is False
        assert store.contains("msg-C") is True

    def test_count_window_max_count_one(self):
        store = make_store(max_count=1)
        store.check_duplicate("msg-only")
        assert store.window_count() == 1
        assert store.check_duplicate("msg-only").is_duplicate is True

        store.check_duplicate("msg-new")
        assert store.window_count() == 1
        assert store.contains("msg-only") is False
        assert store.check_duplicate("msg-new").is_duplicate is True


class TestTimeBasedSlidingWindow:
    def test_time_window_evicts_old_records(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_time_seconds=60.0, clock=clock)

        store.check_duplicate("msg-old")
        clock.advance(30.0)
        store.check_duplicate("msg-new")
        assert store.window_count() == 2

        clock.advance(31.0)
        assert store.window_count() == 1
        assert store.contains("msg-old") is False
        assert store.contains("msg-new") is True

    def test_time_window_boundary_exactly_at_limit(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_time_seconds=60.0, clock=clock)

        store.check_duplicate("msg-boundary")
        clock.advance(60.0)
        assert store.window_count() == 0
        assert store.contains("msg-boundary") is False

    def test_time_window_boundary_just_before_limit(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_time_seconds=60.0, clock=clock)

        store.check_duplicate("msg-boundary")
        clock.advance(59.999)
        assert store.window_count() == 1
        assert store.contains("msg-boundary") is True

    def test_time_window_empty_after_all_expire(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_time_seconds=10.0, clock=clock)

        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        store.check_duplicate("msg-3")
        assert store.window_count() == 3

        clock.advance(11.0)
        assert store.window_count() == 0

        r = store.check_duplicate("msg-1")
        assert r.is_duplicate is False


class TestHybridWindow:
    def test_hybrid_count_triggers_eviction(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=2, max_time_seconds=3600.0, clock=clock)

        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        store.check_duplicate("msg-3")
        assert store.window_count() == 2
        assert store.contains("msg-1") is False

    def test_hybrid_time_triggers_eviction(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, max_time_seconds=10.0, clock=clock)

        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        clock.advance(11.0)
        store.check_duplicate("msg-3")
        assert store.window_count() == 1
        assert store.contains("msg-1") is False
        assert store.contains("msg-2") is False
        assert store.contains("msg-3") is True


class TestTTLExpiration:
    def test_ttl_expired_message_treated_as_new(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=60.0, clock=clock)

        store.check_duplicate("msg-ttl")
        clock.advance(61.0)

        result = store.check_duplicate("msg-ttl")
        assert result.is_duplicate is False
        assert result.should_process is True

    def test_ttl_boundary_exactly_at_limit(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=60.0, clock=clock)

        store.check_duplicate("msg-boundary")
        clock.advance(60.0)

        result = store.check_duplicate("msg-boundary")
        assert result.is_duplicate is False

    def test_ttl_boundary_just_before_limit(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=60.0, clock=clock)

        store.check_duplicate("msg-boundary")
        clock.advance(59.999)

        result = store.check_duplicate("msg-boundary")
        assert result.is_duplicate is True

    def test_lazy_expiration_on_contains(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=30.0, clock=clock)

        store.check_duplicate("msg-lazy")
        clock.advance(31.0)

        assert store.contains("msg-lazy") is False

    def test_lazy_expiration_on_get_record(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=30.0, clock=clock)

        store.check_duplicate("msg-lazy")
        clock.advance(31.0)

        assert store.get_record("msg-lazy") is None

    def test_cleanup_expired_removes_all_expired(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=30.0, clock=clock)

        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        clock.advance(10.0)
        store.check_duplicate("msg-3")

        clock.advance(21.0)
        removed = store.cleanup_expired()
        assert removed == 2
        assert store.contains("msg-1") is False
        assert store.contains("msg-2") is False
        assert store.contains("msg-3") is True

    def test_cleanup_expired_nothing_to_remove(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, ttl_seconds=3600.0, clock=clock)

        store.check_duplicate("msg-1")
        removed = store.cleanup_expired()
        assert removed == 0

    def test_periodic_cleanup_via_interval(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(
            max_count=100,
            ttl_seconds=10.0,
            cleanup_interval_seconds=5.0,
            clock=clock,
        )

        store.check_duplicate("msg-1")
        clock.advance(11.0)
        store.check_duplicate("msg-trigger")

        assert store.contains("msg-1") is False

    def test_ttl_vs_window_independent(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=5, ttl_seconds=5.0, clock=clock)

        store.check_duplicate("msg-A")
        clock.advance(3.0)
        store.check_duplicate("msg-B")
        store.check_duplicate("msg-C")
        store.check_duplicate("msg-D")
        store.check_duplicate("msg-E")

        assert store.window_count() == 5
        clock.advance(3.0)

        store.check_duplicate("msg-F")
        assert store.window_count() == 5
        assert store.contains("msg-A") is False
        assert store.contains("msg-B") is True


class TestStats:
    def test_empty_stats(self):
        store = make_store(max_count=100)
        stats = store.get_stats()
        assert isinstance(stats, DedupStats)
        assert stats.window_size == 0
        assert stats.total_received == 0
        assert stats.total_duplicates == 0
        assert stats.hit_rate == 0.0

    def test_stats_after_unique_messages(self):
        store = make_store(max_count=100)
        for i in range(5):
            store.check_duplicate(f"msg-{i}")
        stats = store.get_stats()
        assert stats.window_size == 5
        assert stats.total_received == 5
        assert stats.total_duplicates == 0
        assert stats.hit_rate == 0.0

    def test_stats_after_duplicates(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-1")
        store.check_duplicate("msg-2")
        stats = store.get_stats()
        assert stats.total_received == 5
        assert stats.total_duplicates == 3
        assert stats.hit_rate == 3 / 5

    def test_stats_100_percent_hit_rate(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-only")
        for _ in range(9):
            store.check_duplicate("msg-only")
        stats = store.get_stats()
        assert stats.total_received == 10
        assert stats.total_duplicates == 9
        assert stats.hit_rate == 0.9


class TestConcurrency:
    def test_concurrent_same_message_only_one_new(self):
        store = make_store(max_count=1000)
        thread_count = 10
        barrier = threading.Barrier(thread_count, timeout=10)
        new_count = [0]
        dup_count = [0]
        counter_lock = threading.Lock()
        errors = {}

        def thread_fn(thread_id):
            try:
                barrier.wait(timeout=10)
                result = store.check_duplicate("concurrent-msg")
                with counter_lock:
                    if result.is_duplicate:
                        dup_count[0] += 1
                    else:
                        new_count[0] += 1
            except Exception as e:
                errors[thread_id] = e

        threads = [
            threading.Thread(target=thread_fn, args=(i,))
            for i in range(thread_count)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Errors: {errors}"
        assert new_count[0] == 1, f"Expected exactly 1 new, got {new_count[0]}"
        assert dup_count[0] == thread_count - 1

        stats = store.get_stats()
        assert stats.total_received == thread_count
        assert stats.total_duplicates == thread_count - 1

    def test_concurrent_different_messages_all_new(self):
        store = make_store(max_count=1000)
        thread_count = 10
        barrier = threading.Barrier(thread_count, timeout=10)
        new_count = [0]
        counter_lock = threading.Lock()
        errors = {}

        def thread_fn(thread_id):
            try:
                barrier.wait(timeout=10)
                result = store.check_duplicate(f"msg-{thread_id}")
                with counter_lock:
                    if not result.is_duplicate:
                        new_count[0] += 1
            except Exception as e:
                errors[thread_id] = e

        threads = [
            threading.Thread(target=thread_fn, args=(i,))
            for i in range(thread_count)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Errors: {errors}"
        assert new_count[0] == thread_count
        assert store.window_count() == thread_count

    def test_concurrent_reads_and_writes(self):
        store = make_store(max_count=1000)
        errors = {}

        def writer(writer_id):
            try:
                for i in range(20):
                    store.check_duplicate(f"writer-{writer_id}-msg-{i}")
            except Exception as e:
                errors[f"writer-{writer_id}"] = e

        def reader(reader_id):
            try:
                for _ in range(50):
                    store.window_count()
                    store.get_stats()
                    store.contains(f"writer-0-msg-0")
                    sleep(0.001)
            except Exception as e:
                errors[f"reader-{reader_id}"] = e

        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=writer, args=(i,)))
        for i in range(2):
            threads.append(threading.Thread(target=reader, args=(i,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Errors: {errors}"


class TestManagementOperations:
    def test_remove(self):
        store = make_store(max_count=100)
        store.check_duplicate("msg-1")
        assert store.remove("msg-1") is True
        assert store.contains("msg-1") is False
        assert store.remove("msg-1") is False

    def test_clear(self):
        store = make_store(max_count=100)
        for i in range(10):
            store.check_duplicate(f"msg-{i}")
        store.clear()
        assert store.window_count() == 0
        stats = store.get_stats()
        assert stats.total_received == 0
        assert stats.total_duplicates == 0

    def test_list_records(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, clock=clock)
        store.check_duplicate("msg-A")
        clock.advance(1.0)
        store.check_duplicate("msg-B")
        clock.advance(1.0)
        store.check_duplicate("msg-C")

        records = store.list_records()
        assert len(records) == 3
        ids = [r.message_id for r in records]
        assert ids == ["msg-A", "msg-B", "msg-C"]

    def test_list_records_returns_snapshots(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_count=100, clock=clock)
        store.check_duplicate("msg-snap")
        records = store.list_records()
        assert records[0].received_at == 0.0
        clock.advance(5.0)
        assert records[0].age_seconds(clock) == 5.0


class TestEdgeCases:
    def test_empty_window(self):
        store = make_store(max_count=100)
        assert store.window_count() == 0
        assert store.list_records() == []
        stats = store.get_stats()
        assert stats.window_size == 0
        assert stats.hit_rate == 0.0

    def test_single_message_window_duplicate(self):
        store = make_store(max_count=1)
        r1 = store.check_duplicate("msg-solo")
        assert r1.is_duplicate is False
        r2 = store.check_duplicate("msg-solo")
        assert r2.is_duplicate is True

    def test_remove_nonexistent(self):
        store = make_store(max_count=100)
        assert store.remove("nope") is False

    def test_cleanup_expired_empty_store(self):
        store = make_store(max_count=100, ttl_seconds=60.0)
        assert store.cleanup_expired() == 0

    def test_message_outside_count_window_not_duplicate(self):
        store = make_store(max_count=3)
        store.check_duplicate("msg-A")
        store.check_duplicate("msg-B")
        store.check_duplicate("msg-C")
        store.check_duplicate("msg-D")

        assert store.contains("msg-A") is False
        result = store.check_duplicate("msg-A")
        assert result.is_duplicate is False

    def test_message_outside_time_window_not_duplicate(self):
        clock = make_manual_clock(start_time=0.0)
        store = make_store(max_time_seconds=10.0, ttl_seconds=3600.0, clock=clock)

        store.check_duplicate("msg-old")
        clock.advance(5.0)
        store.check_duplicate("msg-mid")
        clock.advance(6.0)

        assert store.contains("msg-old") is False
        result = store.check_duplicate("msg-old")
        assert result.is_duplicate is False

        assert store.contains("msg-mid") is True
        result2 = store.check_duplicate("msg-mid")
        assert result2.is_duplicate is True
