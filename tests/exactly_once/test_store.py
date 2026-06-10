import threading

import pytest

from solocoder_py.exactly_once import (
    CheckpointNotFoundError,
    DedupStoreOverflowError,
    InvalidOffsetError,
    MessageNotFoundError,
)
from .conftest import (
    make_checkpoint_store,
    make_clock,
    make_dedup_store,
    make_message_source,
)


class TestMessageSource:
    def test_publish_and_get(self):
        src = make_message_source()
        off = src.publish("msg-1", {"data": 1})
        assert off == 0
        msg = src.get_message(0)
        assert msg.message_id == "msg-1"
        assert msg.payload == {"data": 1}
        assert msg.offset == 0

    def test_publish_sequential_offsets(self):
        src = make_message_source()
        for i in range(5):
            off = src.publish(f"msg-{i}", i)
            assert off == i
        assert src.latest_offset == 4
        assert src.next_offset == 5
        assert src.size() == 5

    def test_publish_empty_id_rejected(self):
        src = make_message_source()
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            src.publish("", "data")

    def test_get_nonexistent_message(self):
        src = make_message_source()
        with pytest.raises(MessageNotFoundError):
            src.get_message(999)

    def test_get_negative_offset(self):
        src = make_message_source()
        with pytest.raises(InvalidOffsetError):
            src.get_message(-1)

    def test_get_range(self):
        src = make_message_source()
        for i in range(10):
            src.publish(f"m{i}", i)
        msgs = src.get_range(2, 5)
        assert len(msgs) == 4
        assert [m.offset for m in msgs] == [2, 3, 4, 5]

    def test_get_range_empty(self):
        src = make_message_source()
        assert src.get_range(0, -1) == []
        assert src.get_range(10, 20) == []

    def test_get_range_none_end(self):
        src = make_message_source()
        for i in range(5):
            src.publish(f"m{i}", i)
        msgs = src.get_range(2)
        assert len(msgs) == 3
        assert msgs[0].offset == 2
        assert msgs[-1].offset == 4

    def test_iter_from(self):
        src = make_message_source()
        for i in range(5):
            src.publish(f"m{i}", i)
        offsets = [m.offset for m in src.iter_from(2)]
        assert offsets == [2, 3, 4]

    def test_iter_from_start(self):
        src = make_message_source()
        for i in range(3):
            src.publish(f"m{i}", i)
        offsets = [m.offset for m in src.iter_from(0)]
        assert offsets == [0, 1, 2]

    def test_latest_offset_empty(self):
        src = make_message_source()
        assert src.latest_offset == -1

    def test_publish_batch(self):
        src = make_message_source()
        msgs = [(f"m{i}", f"data-{i}") for i in range(3)]
        offsets = src.publish_batch(msgs)
        assert offsets == [0, 1, 2]
        assert src.size() == 3

    def test_clear(self):
        src = make_message_source()
        for i in range(5):
            src.publish(f"m{i}", i)
        src.clear()
        assert src.size() == 0
        assert src.latest_offset == -1
        assert src.next_offset == 0

    def test_contains_offset(self):
        src = make_message_source()
        src.publish("m1", 1)
        assert src.contains_offset(0) is True
        assert src.contains_offset(1) is False

    def test_get_message_returns_snapshot(self):
        src = make_message_source()
        src.publish("m1", {"mutable": [1]})
        msg = src.get_message(0)
        msg.payload["mutable"].append(999)
        original = src.get_message(0)
        assert original.payload == {"mutable": [1]}


class TestDedupStore:
    def test_put_and_contains(self):
        store = make_dedup_store()
        store.put("msg-1", offset=0, result_data={"ok": True})
        assert store.contains("msg-1") is True
        assert store.contains("msg-2") is False

    def test_get_record(self):
        clock = make_clock(start_time=5.0)
        store = make_dedup_store(clock=clock)
        store.put("msg-1", offset=3, result_data="result")
        rec = store.get("msg-1")
        assert rec is not None
        assert rec.message_id == "msg-1"
        assert rec.offset == 3
        assert rec.result_data == "result"
        assert rec.processed_at == 5.0

    def test_get_nonexistent(self):
        store = make_dedup_store()
        assert store.get("nope") is None

    def test_put_duplicate_updates(self):
        store = make_dedup_store()
        store.put("m1", offset=0, result_data="first")
        rec = store.put("m1", offset=0, result_data="second")
        assert rec.result_data == "second"
        assert store.size() == 1

    def test_empty_id_rejected(self):
        store = make_dedup_store()
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.put("", offset=0)
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.contains("")
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            store.get("")

    def test_negative_offset_rejected(self):
        store = make_dedup_store()
        with pytest.raises(InvalidOffsetError):
            store.put("m1", offset=-1)

    def test_max_size_overflow(self):
        store = make_dedup_store(max_size=3)
        store.put("m1", 0)
        store.put("m2", 1)
        store.put("m3", 2)
        with pytest.raises(DedupStoreOverflowError):
            store.put("m4", 3)

    def test_max_size_config_invalid(self):
        with pytest.raises(ValueError, match="max_size must be positive"):
            make_dedup_store(max_size=0)

    def test_contains_offset_and_get_by_offset(self):
        store = make_dedup_store()
        store.put("m1", offset=5)
        assert store.contains_offset(5) is True
        assert store.contains_offset(6) is False
        rec = store.get_by_offset(5)
        assert rec is not None
        assert rec.message_id == "m1"
        assert store.get_by_offset(99) is None

    def test_put_batch(self):
        from solocoder_py.exactly_once import DedupRecord

        clock = make_clock(start_time=0.0)
        records = [
            DedupRecord(message_id=f"m{i}", offset=i, processed_at=float(i))
            for i in range(3)
        ]
        store = make_dedup_store(clock=clock)
        store.put_batch(records)
        assert store.size() == 3
        for i in range(3):
            assert store.contains(f"m{i}")

    def test_put_batch_respects_max_size(self):
        from solocoder_py.exactly_once import DedupRecord

        clock = make_clock(start_time=0.0)
        store = make_dedup_store(max_size=2, clock=clock)
        store.put("m0", 0)
        records = [
            DedupRecord(message_id="m1", offset=1, processed_at=1.0),
            DedupRecord(message_id="m2", offset=2, processed_at=2.0),
        ]
        with pytest.raises(DedupStoreOverflowError):
            store.put_batch(records)

    def test_remove(self):
        store = make_dedup_store()
        store.put("m1", 0)
        assert store.remove("m1") is True
        assert store.contains("m1") is False
        assert store.contains_offset(0) is False
        assert store.remove("m1") is False

    def test_evict_oldest(self):
        store = make_dedup_store()
        for i in range(5):
            store.put(f"m{i}", i)
        evicted = store.evict_oldest(2)
        assert len(evicted) == 2
        assert evicted[0].message_id == "m0"
        assert evicted[1].message_id == "m1"
        assert store.size() == 3
        assert store.contains("m0") is False
        assert store.contains("m2") is True

    def test_evict_invalid_count(self):
        store = make_dedup_store()
        with pytest.raises(ValueError, match="count must be positive"):
            store.evict_oldest(0)

    def test_size_and_clear(self):
        store = make_dedup_store()
        assert store.size() == 0
        for i in range(5):
            store.put(f"m{i}", i)
        assert store.size() == 5
        store.clear()
        assert store.size() == 0

    def test_list_records(self):
        clock = make_clock(start_time=0.0)
        store = make_dedup_store(clock=clock)
        ids = []
        for i in range(3):
            clock.advance(1.0)
            store.put(f"m{i}", i)
            ids.append(f"m{i}")
        records = store.list_records()
        assert [r.message_id for r in records] == ids

    def test_list_message_ids(self):
        store = make_dedup_store()
        for i in range(3):
            store.put(f"m{i}", i)
        assert store.list_message_ids() == ["m0", "m1", "m2"]

    def test_lru_move_to_end_on_access(self):
        store = make_dedup_store(max_size=3)
        store.put("a", 0)
        store.put("b", 1)
        store.put("c", 2)
        store.put("a", 0)
        assert store.list_message_ids() == ["b", "c", "a"]

    def test_concurrent_puts(self):
        store = make_dedup_store(max_size=1000)
        threads = []
        errors = {}
        n = 50

        def worker(tid):
            try:
                for i in range(n):
                    store.put(f"t{tid}-m{i}", tid * n + i)
            except Exception as e:
                errors[tid] = e

        for t in range(10):
            threads.append(threading.Thread(target=worker, args=(t,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert store.size() == 10 * n


class TestCheckpointStore:
    def test_no_checkpoint_raises(self):
        cs = make_checkpoint_store()
        with pytest.raises(CheckpointNotFoundError):
            cs.get_latest()

    def test_get_latest_or_none(self):
        cs = make_checkpoint_store()
        assert cs.get_latest_or_none() is None

    def test_prepare_and_commit_batch(self):
        from solocoder_py.exactly_once import DedupRecord

        clock = make_clock(start_time=0.0)
        cs = make_checkpoint_store(clock=clock)
        ds = make_dedup_store(clock=clock)
        records = [
            DedupRecord(message_id=f"m{i}", offset=i, processed_at=float(i))
            for i in range(3)
        ]

        cs.prepare_batch(target_offset=2, dedup_records=records)
        assert cs.has_pending_batch is True
        cp = cs.commit_batch(ds)

        assert cp.committed_offset == 2
        assert cp.last_message_id == "m2"
        assert cs.has_pending_batch is False
        assert cs.checkpoint_count() == 1
        assert ds.size() == 3

    def test_double_prepare_rejected(self):
        from solocoder_py.exactly_once import DedupRecord

        cs = make_checkpoint_store()
        r = [DedupRecord(message_id="m1", offset=0, processed_at=0.0)]
        cs.prepare_batch(0, r)
        with pytest.raises(RuntimeError, match="another batch is pending"):
            cs.prepare_batch(0, r)

    def test_commit_without_prepare_rejected(self):
        cs = make_checkpoint_store()
        ds = make_dedup_store()
        with pytest.raises(RuntimeError, match="No prepared batch"):
            cs.commit_batch(ds)

    def test_rollback_batch(self):
        from solocoder_py.exactly_once import DedupRecord

        cs = make_checkpoint_store()
        r = [DedupRecord(message_id="m1", offset=0, processed_at=0.0)]
        cs.prepare_batch(0, r)
        rolled_back = cs.rollback_batch()
        assert rolled_back is not None
        assert cs.has_pending_batch is False
        assert cs.checkpoint_count() == 0

    def test_simulate_crash_after_prepare(self):
        from solocoder_py.exactly_once import (
            AtomicCommitInterruptedError,
            DedupRecord,
        )

        clock = make_clock(start_time=0.0)
        cs = make_checkpoint_store(clock=clock)
        ds = make_dedup_store(clock=clock)
        records = [
            DedupRecord(message_id="m1", offset=0, processed_at=0.0),
        ]

        cs.prepare_batch(0, records)
        cs.simulate_crash_after_prepare(True)

        with pytest.raises(AtomicCommitInterruptedError) as exc:
            cs.commit_batch(ds)

        assert exc.value.offset == 0
        assert "m1" in exc.value.message_ids
        assert cs.has_pending_batch is True
        assert ds.size() == 0

    def test_simulate_crash_after_dedup(self):
        from solocoder_py.exactly_once import (
            AtomicCommitInterruptedError,
            DedupRecord,
        )

        clock = make_clock(start_time=0.0)
        cs = make_checkpoint_store(clock=clock)
        ds = make_dedup_store(clock=clock)
        records = [
            DedupRecord(message_id="m1", offset=0, processed_at=0.0),
        ]

        cs.prepare_batch(0, records)
        cs.simulate_crash_after_dedup(True)

        with pytest.raises(AtomicCommitInterruptedError):
            cs.commit_batch(ds)

        assert ds.size() == 1
        assert cs.has_pending_batch is True
        assert cs.checkpoint_count() == 0

    def test_restore_from_checkpoint(self):
        from solocoder_py.exactly_once import DedupRecord

        clock = make_clock(start_time=0.0)
        cs = make_checkpoint_store(clock=clock)
        ds = make_dedup_store(clock=clock)

        for i in range(5):
            records = [DedupRecord(message_id=f"m{i}", offset=i, processed_at=float(i))]
            cs.prepare_batch(i, records)
            cs.commit_batch(ds)

        assert ds.size() == 5
        cp = cs.restore_from_checkpoint(ds)
        assert cp is not None
        assert cp.committed_offset == 4
        assert ds.size() == 5
        assert ds.contains("m0")
        assert cs.has_pending_batch is False

    def test_restore_no_checkpoint(self):
        cs = make_checkpoint_store()
        ds = make_dedup_store()
        assert cs.restore_from_checkpoint(ds) is None

    def test_get_all_checkpoints(self):
        from solocoder_py.exactly_once import DedupRecord

        clock = make_clock(start_time=0.0)
        cs = make_checkpoint_store(clock=clock)
        ds = make_dedup_store(clock=clock)

        for i in range(3):
            records = [DedupRecord(message_id=f"m{i}", offset=i, processed_at=float(i))]
            cs.prepare_batch(i, records)
            cs.commit_batch(ds)

        all_cp = cs.get_all()
        assert len(all_cp) == 3
        assert [c.committed_offset for c in all_cp] == [0, 1, 2]

    def test_clear(self):
        cs = make_checkpoint_store()
        from solocoder_py.exactly_once import DedupRecord

        r = [DedupRecord(message_id="m", offset=0, processed_at=0.0)]
        ds = make_dedup_store()
        cs.prepare_batch(0, r)
        cs.commit_batch(ds)
        cs.clear()
        assert cs.checkpoint_count() == 0
        assert cs.has_pending_batch is False
