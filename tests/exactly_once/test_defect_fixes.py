import pytest

from solocoder_py.exactly_once import (
    CheckpointMonotonicityError,
    DedupStoreOverflowError,
    OffsetSkipWarning,
    ProcessStatus,
)
from .conftest import (
    make_clock,
    make_dedup_store,
    make_message_source,
    make_processor,
    make_processor_with_components,
    make_checkpoint_store,
)


class TestOffsetSkipWarning:
    def test_process_message_at_skips_intermediate_offsets(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        assert proc.current_offset == -1

        r = proc.process_message_at(5, handler=lambda m: m.payload)
        assert r.is_new is True
        assert r.message.offset == 5
        assert proc.current_offset == -1

    def test_process_message_at_emits_skip_warning(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        assert proc.last_skip_warning is None

        proc.process_message_at(5)
        w = proc.last_skip_warning
        assert w is not None
        assert w.expected_offset == 0
        assert w.actual_offset == 5

    def test_process_message_at_no_warning_when_sequential(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        assert proc.last_skip_warning is None

        proc.process_message_at(1)
        assert proc.last_skip_warning is None

    def test_process_message_at_does_not_change_current_offset(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        assert proc.current_offset == 0

        proc.process_message_at(5)
        assert proc.current_offset == 0

        proc.process_message_at(7)
        assert proc.current_offset == 0

    def test_process_message_at_sequential_consumption_unchanged(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_message_at(5)
        assert proc.current_offset == -1

        r1 = proc.process_next()
        assert r1.message.offset == 0
        assert r1.is_new is True

        r2 = proc.process_next()
        assert r2.message.offset == 1
        assert r2.is_new is True

    def test_process_message_at_duplicate_after_first(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        r1 = proc.process_message_at(3)
        assert r1.is_new is True

        r2 = proc.process_message_at(3)
        assert r2.is_duplicate is True

    def test_process_message_at_no_skip_warning_at_beginning(self):
        proc = make_processor(auto_commit_interval=100)
        proc.publish_message("m0", 0)

        r = proc.process_message_at(0)
        assert r.is_new is True
        assert proc.last_skip_warning is None


class TestUncommittedBatchReplayOverlap:
    def test_replay_skips_uncommitted_messages(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        handler_calls = []

        def handler(msg):
            handler_calls.append(msg.message_id)
            return f"handled-{msg.message_id}"

        proc.process_next(handler)
        proc.process_next(handler)
        assert proc.uncommitted_count == 2
        assert handler_calls == ["m0", "m1"]

        handler_calls.clear()
        result = proc.replay_range(0, 4, handler)

        assert result.duplicate_count == 2
        assert result.processed_count == 3
        assert set(handler_calls) == {"m2", "m3", "m4"}

    def test_replay_uncommitted_does_not_double_execute_handler(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        call_count = [0]

        def handler(msg):
            call_count[0] += 1
            return msg.message_id

        proc.process_next(handler)
        proc.process_next(handler)
        assert call_count[0] == 2

        call_count[0] = 0
        result = proc.replay_range(0, 4, handler)
        assert call_count[0] == 3
        assert result.duplicate_count == 2

    def test_replay_overlap_with_all_uncommitted(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        handler_calls = []

        def handler(msg):
            handler_calls.append(msg.message_id)
            return msg.message_id

        for _ in range(5):
            proc.process_next(handler)

        handler_calls.clear()
        result = proc.replay_range(0, 4, handler)
        assert result.processed_count == 0
        assert result.duplicate_count == 5
        assert len(handler_calls) == 0

    def test_replay_partial_overlap_with_uncommitted(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        handler_calls = []

        def handler(msg):
            handler_calls.append(msg.message_id)
            return msg.message_id

        proc.process_next(handler)
        proc.process_next(handler)
        proc.process_next(handler)

        handler_calls.clear()
        result = proc.replay_range(2, 6, handler)

        assert result.duplicate_count == 1
        assert result.processed_count == 4
        assert "m2" not in handler_calls
        assert "m3" in handler_calls


class TestCheckpointMonotonicity:
    def test_replay_low_offset_does_not_overwrite_high_checkpoint(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(10):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        assert proc.committed_offset == 9

        result = proc.replay_range(0, 3)
        assert result.processed_count == 0
        assert result.duplicate_count == 4
        assert proc.committed_offset == 9

        all_cp = cp_store.get_all()
        offsets = [c.committed_offset for c in all_cp]
        for i in range(1, len(offsets)):
            assert offsets[i] > offsets[i - 1], (
                f"Checkpoint offset not monotonic: {offsets}"
            )

    def test_auto_checkpoint_skips_when_offset_not_advancing(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(6):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        committed_before = proc.committed_offset

        proc.process_message_at(2, handler=lambda m: "retry")
        proc.commit_checkpoint()

        assert proc.committed_offset == committed_before

    def test_checkpoint_offsets_always_monotonically_increasing(self):
        proc = make_processor(auto_commit_interval=3)
        for i in range(20):
            proc.publish_message(f"m{i}", i)

        proc.process_all()

        all_cp = proc.checkpoint_store.get_all()
        offsets = [c.committed_offset for c in all_cp]

        for i in range(1, len(offsets)):
            assert offsets[i] > offsets[i - 1], (
                f"Non-monotonic checkpoint at index {i}: "
                f"{offsets[i-1]} -> {offsets[i]}"
            )

    def test_replay_with_new_high_offset_advances_checkpoint(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        assert proc.committed_offset == 4

        for i in range(5, 10):
            proc.publish_message(f"m{i}", i)

        result = proc.replay_range(0, 9)
        assert result.processed_count == 5
        assert proc.committed_offset == 9

        all_cp = proc.checkpoint_store.get_all()
        offsets = [c.committed_offset for c in all_cp]
        for i in range(1, len(offsets)):
            assert offsets[i] > offsets[i - 1]

    def test_recovery_from_high_checkpoint_ignores_low_replay(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(10):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        proc.replay_range(0, 3)

        proc.recover_from_checkpoint()
        assert proc.committed_offset == 9
        assert proc.current_offset == 9

        results = proc.process_all()
        assert len(results) == 0


class TestOffsetContinuity:
    def test_process_next_maintains_sequential_offsets(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        offsets = []
        for _ in range(10):
            r = proc.process_next()
            offsets.append(r.message.offset)

        assert offsets == list(range(10))
        assert proc.current_offset == 9

    def test_process_message_at_then_process_next_no_gap(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_message_at(5)
        assert proc.current_offset == -1

        r = proc.process_next()
        assert r.message.offset == 0
        assert proc.current_offset == 0

    def test_process_message_at_with_handler_does_not_affect_sequential(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        r_at = proc.process_message_at(7, handler=lambda m: "out-of-order")
        assert r_at.is_new is True
        assert r_at.dedup_record.result_data == "out-of-order"

        results = proc.process_all(handler=lambda m: f"seq-{m.payload}")
        offsets = [r.message.offset for r in results]
        assert offsets == list(range(10))

        r_offset7 = results[7]
        assert r_offset7.is_duplicate is True
        assert r_offset7.previous_result == "out-of-order"

    def test_process_message_at_multiple_random_access(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        r1 = proc.process_message_at(3)
        r2 = proc.process_message_at(7)
        r3 = proc.process_message_at(9)
        assert r1.is_new is True
        assert r2.is_new is True
        assert r3.is_new is True
        assert proc.current_offset == -1

        results = proc.process_all()
        news = [r for r in results if r.is_new]
        dups = [r for r in results if r.is_duplicate]
        assert len(news) == 7
        assert len(dups) == 3
        dup_offsets = [r.message.offset for r in dups]
        assert set(dup_offsets) == {3, 7, 9}


class TestReplayDedupConsistency:
    def test_replay_dedup_records_written_to_store(self):
        proc = make_processor()
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        result = proc.replay_range(0, 4, handler=lambda m: f"r-{m.payload}")
        assert result.new_dedup_count == 5

        for i in range(5):
            rec = proc.dedup_store.get(f"m{i}")
            assert rec is not None
            assert rec.replayed is True

    def test_replay_then_normal_consumption_dedup_consistent(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(5):
            proc.publish_message(f"m{i}", i)

        proc.replay_range(0, 2, handler=lambda m: "replayed")

        proc.process_next()
        proc.process_next()
        proc.process_next()

        assert proc.dedup_store.get("m0") is not None
        assert proc.dedup_store.get("m1") is not None
        assert proc.dedup_store.get("m2") is not None

        r0 = proc.dedup_store.get("m0")
        assert r0.replayed is True

    def test_replay_uncommitted_and_dedup_store_both_checked(self):
        proc = make_processor(auto_commit_interval=100)
        for i in range(10):
            proc.publish_message(f"m{i}", i)

        proc.process_next()
        proc.process_next()
        proc.process_next()
        proc.process_next()
        proc.process_next()
        proc.commit_checkpoint()

        for i in range(5, 10):
            proc.process_next()
        assert proc.uncommitted_count == 5

        handler_calls = []

        def handler(msg):
            handler_calls.append(msg.message_id)
            return msg.message_id

        result = proc.replay_range(0, 9, handler)

        assert result.duplicate_count == 10
        assert result.processed_count == 0
        assert len(handler_calls) == 0

    def test_replay_crash_recovery_checkpoint_monotonicity(self):
        clock = make_clock(start_time=0.0)
        msg_src = make_message_source(clock=clock)
        dedup = make_dedup_store(clock=clock)
        cp_store = make_checkpoint_store(clock=clock)
        proc = make_processor_with_components(
            msg_src, dedup, cp_store, auto_commit_interval=2, clock=clock
        )

        for i in range(20):
            proc.publish_message(f"m{i}", i)
        proc.process_all()

        high_committed = proc.committed_offset

        proc.replay_range(0, 5)
        assert proc.committed_offset == high_committed

        proc.recover_from_checkpoint()
        assert proc.current_offset == high_committed

        results = proc.process_all()
        assert len(results) == 0
