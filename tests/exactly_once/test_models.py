import pytest

from solocoder_py.exactly_once import (
    Checkpoint,
    CommitBatch,
    DedupRecord,
    InvalidOffsetError,
    Message,
    ProcessResult,
    ProcessStatus,
    ReplayResult,
)
from .conftest import make_clock


class TestMessage:
    def test_create_message_valid(self):
        msg = Message(
            offset=0,
            message_id="msg-001",
            payload={"key": "value"},
            created_at=100.0,
        )
        assert msg.offset == 0
        assert msg.message_id == "msg-001"
        assert msg.payload == {"key": "value"}
        assert msg.created_at == 100.0

    def test_message_negative_offset_rejected(self):
        with pytest.raises(InvalidOffsetError):
            Message(offset=-1, message_id="msg-001", payload={})

    def test_message_empty_id_rejected(self):
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            Message(offset=0, message_id="", payload={})

    def test_message_snapshot(self):
        msg = Message(offset=5, message_id="msg-abc", payload="data", created_at=1.0)
        snap = msg.snapshot()
        assert snap is not msg
        assert snap.offset == 5
        assert snap.message_id == "msg-abc"
        assert snap.payload == "data"
        assert snap.created_at == 1.0


class TestDedupRecord:
    def test_create_dedup_record(self):
        clock = make_clock(start_time=42.0)
        rec = DedupRecord(
            message_id="msg-1",
            offset=3,
            processed_at=clock.now(),
            result_data={"result": "ok"},
        )
        assert rec.message_id == "msg-1"
        assert rec.offset == 3
        assert rec.processed_at == 42.0
        assert rec.result_data == {"result": "ok"}
        assert rec.replayed is False

    def test_dedup_record_empty_id_rejected(self):
        with pytest.raises(ValueError, match="message_id cannot be empty"):
            DedupRecord(message_id="", offset=0, processed_at=0.0)

    def test_dedup_record_negative_offset_rejected(self):
        with pytest.raises(InvalidOffsetError):
            DedupRecord(message_id="msg", offset=-1, processed_at=0.0)

    def test_dedup_record_snapshot(self):
        rec = DedupRecord(
            message_id="m1",
            offset=7,
            processed_at=10.0,
            result_data="x",
            replayed=True,
        )
        snap = rec.snapshot()
        assert snap is not rec
        assert snap.message_id == "m1"
        assert snap.offset == 7
        assert snap.result_data == "x"
        assert snap.replayed is True


class TestCheckpoint:
    def test_create_checkpoint(self):
        cp = Checkpoint(
            committed_offset=10,
            checkpoint_id="cp-abc",
            created_at=123.0,
            dedup_count=5,
            last_message_id="msg-10",
        )
        assert cp.committed_offset == 10
        assert cp.checkpoint_id == "cp-abc"
        assert cp.created_at == 123.0
        assert cp.dedup_count == 5
        assert cp.last_message_id == "msg-10"

    def test_checkpoint_minus_one_offset(self):
        cp = Checkpoint(
            committed_offset=-1,
            checkpoint_id="cp-1",
            created_at=0.0,
        )
        assert cp.committed_offset == -1

    def test_checkpoint_invalid_offset(self):
        with pytest.raises(InvalidOffsetError):
            Checkpoint(committed_offset=-2, checkpoint_id="cp", created_at=0.0)

    def test_checkpoint_empty_id_rejected(self):
        with pytest.raises(ValueError, match="checkpoint_id cannot be empty"):
            Checkpoint(committed_offset=0, checkpoint_id="", created_at=0.0)

    def test_checkpoint_snapshot(self):
        cp = Checkpoint(
            committed_offset=99,
            checkpoint_id="id-1",
            created_at=5.0,
            dedup_count=10,
            last_message_id="last",
        )
        snap = cp.snapshot()
        assert snap is not cp
        assert snap.committed_offset == 99
        assert snap.checkpoint_id == "id-1"
        assert snap.dedup_count == 10


class TestProcessResult:
    def test_new_status(self):
        msg = Message(offset=0, message_id="m1", payload={})
        dedup = DedupRecord(message_id="m1", offset=0, processed_at=0.0)
        r = ProcessResult(
            message=msg,
            status=ProcessStatus.NEW,
            dedup_record=dedup,
            processed_new=True,
        )
        assert r.is_new is True
        assert r.is_duplicate is False
        assert r.is_skipped_replay is False
        assert r.should_process is True

    def test_duplicate_status(self):
        msg = Message(offset=0, message_id="m1", payload={})
        dedup = DedupRecord(message_id="m1", offset=0, processed_at=0.0, result_data={"ok": True})
        r = ProcessResult(
            message=msg,
            status=ProcessStatus.DUPLICATE,
            dedup_record=dedup,
        )
        assert r.is_new is False
        assert r.is_duplicate is True
        assert r.should_process is False
        assert r.previous_result == {"ok": True}

    def test_skipped_replay_status(self):
        msg = Message(offset=5, message_id="m5", payload={})
        r = ProcessResult(
            message=msg,
            status=ProcessStatus.SKIPPED_REPLAY,
            dedup_record=DedupRecord(message_id="m5", offset=5, processed_at=0.0),
        )
        assert r.is_skipped_replay is True
        assert r.is_duplicate is False
        assert r.should_process is False


class TestCommitBatch:
    def test_create_batch(self):
        records = [
            DedupRecord(message_id=f"m{i}", offset=i, processed_at=0.0)
            for i in range(3)
        ]
        batch = CommitBatch(
            target_offset=2,
            message_ids=[r.message_id for r in records],
            dedup_records=records,
            batch_id="batch-1",
            started_at=10.0,
        )
        assert batch.target_offset == 2
        assert len(batch.message_ids) == 3
        assert len(batch.dedup_records) == 3
        assert batch.is_prepared is False
        assert batch.is_committed is False

    def test_batch_mismatched_lengths(self):
        with pytest.raises(ValueError, match="message_ids and dedup_records must have the same length"):
            CommitBatch(
                target_offset=1,
                message_ids=["m1"],
                dedup_records=[
                    DedupRecord(message_id="m1", offset=0, processed_at=0.0),
                    DedupRecord(message_id="m2", offset=1, processed_at=0.0),
                ],
                batch_id="b",
                started_at=0.0,
            )

    def test_batch_empty_id_rejected(self):
        with pytest.raises(ValueError, match="batch_id cannot be empty"):
            CommitBatch(
                target_offset=0,
                message_ids=[],
                dedup_records=[],
                batch_id="",
                started_at=0.0,
            )


class TestReplayResult:
    def test_replay_result_stats(self):
        r = ReplayResult(
            start_offset=0,
            end_offset=9,
            total_messages=10,
            processed_count=3,
            duplicate_count=5,
            skipped_count=2,
        )
        assert r.total_messages == 10
        assert r.processed_count == 3
        assert r.processed_new_count == 3
        assert r.duplicate_count == 5
        assert r.new_dedup_count == 0

    def test_replay_result_with_records(self):
        records = [
            DedupRecord(message_id=f"m{i}", offset=i, processed_at=0.0)
            for i in range(2)
        ]
        r = ReplayResult(
            start_offset=0,
            end_offset=1,
            total_messages=2,
            processed_count=2,
            duplicate_count=0,
            skipped_count=0,
            replayed_dedup_records=records,
        )
        assert r.new_dedup_count == 2
