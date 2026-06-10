import threading

import pytest

from solocoder_py.exactly_once import (
    AtomicCommitInterruptedError,
    CheckpointNotFoundError,
    DedupStoreOverflowError,
    InvalidOffsetError,
    ProcessStatus,
)
from .conftest import (
    make_checkpoint_store,
    make_clock,
    make_dedup_store,
    make_message_source,
    make_processor,
    make_processor_with_components,
)


class TestBasicProcessingAndDedup:
    def test_process_single_message_new(self):
        proc = make_processor()
        proc.publish_message("msg-1", {"v": 1})

        result = proc.process_next()
        assert result is not None
        assert result.is_new is True
        assert result.should_process is True
        assert result.message.message_id == "msg-1"
        assert result.message.offset == 0
        assert result.processed_new is True

    def test_process_duplicate_message_detected(self):
        proc = make_processor()
        proc.publish_message("msg-1", {"v": 1})
        proc.publish_message("msg-1", {"v": 2})

        r1 = proc.process_next()
        assert r1.is_new is True

        r2 = proc.process_next()
        assert r2 is not None
        assert r2.is_duplicate is True
        assert r2.should_process is False
        assert r2.message.offset == 1
        assert r2.dedup_record is not None
        assert r2.dedup_record.offset == 0

    def test_handler_executed_for_new_only(self):
        proc = make_processor()
        proc.publish_message("dup", 1)
        proc.publish_message("dup", 2)

        call_count = [0]
        results = []

        def handler(msg):
            call_count[0] += 1
            results.append(msg.payload)
            return f"handled-{msg.payload}"

        r1 = proc.process_next(handler)
        r2 = proc.process_next(handler)

        assert r1.is_new is True
        assert r2.is_duplicate is True
        assert call_count[0] == 1
        assert results == [1]
        assert r1.dedup_record.result_data == "handled-1"
        assert r2.previous_result == "handled-1"

    def test_consecutive_duplicate_messages(self):
        proc = make_processor()
        for _ in range(5):
            proc.publish_message("same-id", "data")

        new_count = 0
        dup_count = 0
        for _ in range(5):
            r = proc.process_next()
            if r.is_new:
                new_count += 1
            elif r.is_duplicate:
                dup_count += 1

        assert new_count == 1
        assert dup_count == 4

    def test_interleaved_new_and_dup(self):
        proc = make_processor()
        proc.publish_message("a", 1)
        proc.publish_message("b", 2)
        proc.publish_message("a", 10)
        proc.publish_message("c", 3)
        proc.publish_message("b", 20)

        results = [proc.process_next() for _ in range(5)]
        statuses = [r.status for r in results]

        assert statuses[0] == ProcessStatus.NEW
        assert statuses[1] == ProcessStatus.NEW
        assert statuses[2] == ProcessStatus.DUPLICATE
        assert statuses[3] == ProcessStatus.NEW
        assert statuses[4] == ProcessStatus.DUPLICATE

    def test_process_all(self):
        proc = make_processor()
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        results = proc.process_all()
        assert len(results) == 10
        assert all(r.is_new for r in results)
        assert proc.current_offset == 9

    def test_process_batch(self):
        proc = make_processor()
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        batch = proc.process_batch(3)
        assert len(batch) == 3
        assert proc.current_offset == 2

        batch2 = proc.process_batch(10)
        assert len(batch2) == 7
        assert proc.current_offset == 9

    def test_process_none_when_empty(self):
        proc = make_processor()
        assert proc.process_next() is None
        assert proc.process_all() == []

    def test_process_batch_invalid_count(self):
        proc = make_processor()
        with pytest.raises(ValueError, match="max_count must be positive"):
            proc.process_batch(0)


class TestAutoCommitAndCheckpoints:
    def test_single_auto_commit_interval(self):
        proc = make_processor(auto_commit_interval=1)
        proc.publish_message("m1", 1)
        proc.publish_message("m2", 2)

        r1 = proc.process_next()
        assert r1.is_new is True
        assert proc.committed_offset == 0
        assert proc.uncommitted_count == 0

        r2 = proc.process_next()
        assert r2.is_new is True
        assert proc.committed_offset == 1

    def test_larger_auto_commit_interval(self):
        proc = make_processor(auto_commit_interval=3)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        proc.process_next()
        assert proc.committed_offset == -1
        assert proc.uncommitted_count == 2

        proc.process_next()
        assert proc.committed_offset == 2
        assert proc.uncommitted_count == 0

        proc.process_next()
        assert proc.committed_offset == 2
        assert proc.uncommitted_count == 1

        proc.process_next()
        assert proc.committed_offset == 2
        assert proc.uncommitted_count == 2

        proc.process_all()
        assert proc.committed_offset == 4

    def test_manual_checkpoint_commit(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        for _ in range(5):
            proc.process_next()
        assert proc.committed_offset == -1
        assert proc.uncommitted_count == 5

        cp = proc.commit_checkpoint()
        assert cp is not None
        assert cp.committed_offset == 4
        assert proc.uncommitted_count == 0
        assert proc.committed_offset == 4

    def test_manual_checkpoint_empty(self):
        proc = make_processor()
        assert proc.commit_checkpoint() is None

    def test_multiple_checkpoints(self):
        proc = make_processor(auto_commit_interval=2)
        for i in range(6):
            proc.publish_message(f"m{i}", i)

        proc.process_all()
        all_cp = proc.checkpoint_store.get_all()
        assert len(all_cp) == 3
        assert all_cp[0].committed_offset == 1
        assert all_cp[1].committed_offset == 3
        assert all_cp[2].committed_offset == 5

    def test_checkpoint_boundary_alignment(self):
        proc = make_processor(auto_commit_interval=3)
        for i in range(9):
            proc.publish_message(f"m{i}", i)

        for step in range(3):
            proc.process_batch(3)
            expected = (step + 1) * 3 - 1
            assert proc.committed_offset == expected

        all_cp = proc.checkpoint_store.get_all()
        assert [c.committed_offset for c in all_cp] == [2, 5, 8]


class TestCrashRecovery:
    def test_recover_from_checkpoint(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=3, clock=clock
        )

        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_all()
        assert proc.current_offset == 9
        assert proc.committed_offset == 9
        assert dedup.size() == 10

        recovered = proc.recover_from_checkpoint()
        assert recovered.committed_offset == 9
        assert proc.current_offset == 9
        assert dedup.size() == 10
        assert proc.is_recovered is True

    def test_recover_no_checkpoint(self):
        proc = make_processor()
        with pytest.raises(CheckpointNotFoundError):
            proc.recover_from_checkpoint()

    def test_recover_or_start_fresh_no_cp(self):
        proc = make_processor()
        result = proc.recover_or_start_fresh()
        assert result is None
        assert proc.is_recovered is True
        assert proc.current_offset == -1

    def test_recover_then_continue_processing(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        for i in range(5, 10):
            proc.publish_message(f"m{i}", i)

        proc.recover_from_checkpoint()
        results = proc.process_all()

        new_messages = [r for r in results if r.is_new]
        dup_messages = [r for r in results if r.is_duplicate]
        assert len(new_messages) == 5
        assert len(dup_messages) == 0

    def test_atomic_crash_after_prepare_recovery(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=100, clock=clock
        )

        for i in range(5):
            proc.publish_message(f"m{i}", i)
        for _ in range(5):
            proc.process_next()

        cp_store.simulate_crash_after_prepare(True)

        with pytest.raises(AtomicCommitInterruptedError):
            proc.commit_checkpoint()

        assert cp_store.has_pending_batch is False
        assert dedup.size() == 0

        results = proc.process_all()
        assert all(r.is_new for r in results)
        assert proc.committed_offset == 4

    def test_atomic_crash_after_dedup_recovery(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=100, clock=clock
        )

        for i in range(5):
            proc.publish_message(f"m{i}", i)
        for _ in range(5):
            proc.process_next()

        cp_store.simulate_crash_after_dedup(True)

        with pytest.raises(AtomicCommitInterruptedError):
            proc.commit_checkpoint()

        assert dedup.size() == 5
        assert cp_store.has_pending_batch is False
        assert cp_store.checkpoint_count() == 0

        results = proc.process_all()
        assert all(r.is_duplicate for r in results)

    def test_recover_then_publish_more(self):
        proc = make_processor(auto_commit_interval=2)
        for i in range(4):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        proc.recover_from_checkpoint()

        for i in range(4, 8):
            proc.publish_message(f"m{i}", i)

        results = proc.process_all()
        news = [r for r in results if r.is_new]
        dups = [r for r in results if r.is_duplicate]
        assert len(news) == 4
        assert len(dups) == 0

    def test_recovery_preserves_dedup_for_committed(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=3, clock=clock
        )

        for i in range(7):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        proc.recover_from_checkpoint()
        assert dedup.size() == 7

        for i in range(7):
            proc.publish_message(f"m{i}", i * 100)

        results = proc.process_all()
        new_count = sum(1 for r in results if r.is_new)
        dup_count = sum(1 for r in results if r.is_duplicate)

        assert new_count == 0
        assert dup_count == 7


class TestReplayFunctionality:
    def test_replay_range_all_new(self):
        proc = make_processor()
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        result = proc.replay_range(0, 4)
        assert result.start_offset == 0
        assert result.end_offset == 4
        assert result.total_messages == 5
        assert result.processed_count == 5
        assert result.duplicate_count == 0
        assert result.new_dedup_count == 5

    def test_replay_range_all_duplicate(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        result = proc.replay_range(0, 4)
        assert result.total_messages == 5
        assert result.processed_count == 0
        assert result.duplicate_count == 5
        assert result.new_dedup_count == 0

    def test_replay_range_mixed(self):
        proc = make_processor()
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        for _ in range(5):
            proc.process_next()

        result = proc.replay_range(0, 9)
        assert result.total_messages == 10
        assert result.duplicate_count == 5
        assert result.processed_count == 5

    def test_replay_does_not_duplicate_dedup_records(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        proc.replay_range(0, 4)
        size_after_1 = proc.dedup_store.size()

        proc.replay_range(0, 4)
        size_after_2 = proc.dedup_store.size()

        assert size_after_1 == 5
        assert size_after_2 == 5

    def test_replay_preserves_processing_state(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        proc.process_next()
        offset_before = proc.current_offset
        uncommitted_before = proc.uncommitted_count

        proc.replay_range(5, 8)

        assert proc.current_offset == offset_before
        assert proc.uncommitted_count == uncommitted_before

    def test_replay_from(self):
        proc = make_processor()
        for i in range(7):
            proc.publish_message(f"m{i}", i)

        result = proc.replay_from(3)
        assert result.start_offset == 3
        assert result.end_offset == 6
        assert result.total_messages == 4

    def test_replay_from_empty_source(self):
        proc = make_processor()
        result = proc.replay_from(0)
        assert result.total_messages == 0
        assert result.processed_count == 0

    def test_replay_invalid_range(self):
        proc = make_processor()
        with pytest.raises(InvalidOffsetError, match="start_offset must be non-negative"):
            proc.replay_range(-1, 5)
        with pytest.raises(InvalidOffsetError, match="end_offset must be >= start_offset"):
            proc.replay_range(5, 3)

    def test_replay_handler_executed_correctly(self):
        proc = make_processor()
        for i in range(6):
            proc.publish_message(f"m{i}", i)

        for _ in range(3):
            proc.process_next()

        processed = []

        def handler(msg):
            processed.append(msg.message_id)
            return f"replayed-{msg.payload}"

        result = proc.replay_range(0, 5, handler)

        assert len(processed) == 3
        assert set(processed) == {"m3", "m4", "m5"}
        for r in result.replayed_dedup_records:
            assert r.replayed is True

    def test_replay_with_crash_then_recover(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(10):
            proc.publish_message(f"m{i}", i)

        cp_store.simulate_crash_after_prepare(True)

        with pytest.raises(AtomicCommitInterruptedError):
            proc.replay_range(0, 9)

        proc.recover_or_start_fresh()

        result = proc.replay_range(0, 9)
        assert result.processed_count == 10


class TestEdgeCases:
    def test_dedup_overflow_with_evict(self):
        proc = make_processor(max_dedup_size=3)
        proc.publish_message("m1", 1)
        proc.publish_message("m2", 2)
        proc.publish_message("m3", 3)
        proc.process_all()

        proc.publish_message("m4", 4)
        with pytest.raises(DedupStoreOverflowError):
            proc.process_next()

        evicted = proc.force_evict_dedup(1)
        assert len(evicted) == 1
        assert evicted[0].message_id == "m1"

        r = proc.process_next()
        assert r.is_new is True
        assert proc.dedup_store.size() == 3

    def test_dedup_overflow_batch(self):
        proc = make_processor(max_dedup_size=2, auto_commit_interval=100)
        proc.publish_message("m1", 1)
        proc.publish_message("m2", 2)
        proc.publish_message("m3", 3)
        proc.publish_message("m4", 4)

        with pytest.raises(DedupStoreOverflowError):
            proc.process_all()

    def test_stats_reporting(self):
        proc = make_processor(auto_commit_interval=2)
        s = proc.stats()
        assert s["current_offset"] == -1
        assert s["committed_offset"] == -1
        assert s["dedup_size"] == 0
        assert s["is_recovered"] is False

        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        s = proc.stats()
        assert s["current_offset"] == 4
        assert s["committed_offset"] == 4
        assert s["dedup_size"] == 5
        assert s["message_source_size"] == 5

    def test_reset_processor(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        proc.reset()
        assert proc.current_offset == -1
        assert proc.committed_offset == -1
        assert proc.is_recovered is False
        assert proc.message_source.size() == 0

    def test_process_message_at_specific_offset(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        r = proc.process_message_at(3)
        assert r.message.offset == 3
        assert r.is_new is True

        r2 = proc.process_message_at(3)
        assert r2.is_duplicate is True

    def test_zero_messages_initial_state(self):
        proc = make_processor()
        assert proc.current_offset == -1
        assert proc.committed_offset == -1
        assert proc.uncommitted_count == 0
        assert proc.is_recovered is False

    def test_auto_commit_interval_validation(self):
        with pytest.raises(ValueError, match="auto_commit_interval must be positive"):
            make_processor(auto_commit_interval=0)

    def test_process_batch_commit_on_remainder(self):
        proc = make_processor(auto_commit_interval=5)
        for i in range(7):
            proc.publish_message(f"m{i}", i)

        proc.process_batch(7)
        assert proc.committed_offset == 6
        assert proc.uncommitted_count == 0

    def test_replay_dedup_records_not_in_uncommitted(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        assert proc.uncommitted_count == 1

        proc.replay_range(2, 4)

        assert proc.uncommitted_count == 1

    def test_concurrent_processing(self):
        proc = make_processor(auto_commit_interval=1, max_dedup_size=1000)
        n_per_thread = 100
        n_threads = 5

        for i in range(n_per_thread * n_threads):
            proc.publish_message(f"m{i}", i)

        errors = {}
        results_lock = threading.Lock()
        new_counts = [0]
        dup_counts = [0]

        def worker(tid):
            try:
                for _ in range(n_per_thread):
                    with results_lock:
                        r = proc.process_next()
                    if r is None:
                        break
                    if r.is_new:
                        with results_lock:
                            new_counts[0] += 1
                    else:
                        with results_lock:
                            dup_counts[0] += 1
            except Exception as e:
                errors[tid] = e

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert proc.current_offset == n_per_thread * n_threads - 1


class TestAtomicityGuarantees:
    def test_dedup_and_offset_committed_together(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=100, clock=clock
        )

        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()
        proc.commit_checkpoint()

        cp = cp_store.get_latest()
        assert cp.committed_offset == 4
        assert cp.dedup_count == 5

        for i in range(5):
            assert dedup.contains(f"m{i}")
            rec = dedup.get(f"m{i}")
            assert rec.offset == i

    def test_no_leaked_dedup_on_failed_commit(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=100, clock=clock
        )

        for i in range(3):
            proc.publish_message(f"m{i}", i)
        for _ in range(3):
            proc.process_next()

        cp_store.simulate_crash_after_prepare(True)
        with pytest.raises(AtomicCommitInterruptedError):
            proc.commit_checkpoint()

        assert dedup.size() == 0
        assert cp_store.has_pending_batch is False

        for _ in range(3):
            proc.process_next()
        cp_store.simulate_crash_after_dedup(True)
        with pytest.raises(AtomicCommitInterruptedError):
            proc.commit_checkpoint()

        assert dedup.size() == 3
        assert cp_store.get_latest_or_none() is None
        assert cp_store.has_pending_batch is False

    def test_consistency_after_multiple_recoveries(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for round_idx in range(3):
            base = round_idx * 4
            for i in range(4):
                proc.publish_message(f"m{base + i}", base + i)
            proc.process_all()

            cp = proc.recover_from_checkpoint()

            results = proc.process_all()
            if results:
                news = [r for r in results if r.is_new]
                dups = [r for r in results if r.is_duplicate]
                assert len(news) + len(dups) == len(results)
