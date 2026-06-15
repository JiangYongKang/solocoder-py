from __future__ import annotations

import pytest

from solocoder_py.etl import (
    STAGE_COMPLETED,
    STAGE_EXTRACT,
    STAGE_LOAD,
    STAGE_TRANSFORM,
    Checkpoint,
    DataRow,
    ErrorRecord,
    EtlError,
    CheckpointCorruptedError,
    FatalEtlError,
    StageNotReachableError,
)


class TestDataRowModel:
    def test_row_creation(self):
        row = DataRow(row_id=0, data={"key": "value"})
        assert row.row_id == 0
        assert row.data == {"key": "value"}

    def test_negative_row_id_rejected(self):
        with pytest.raises(ValueError, match="row_id must be non-negative"):
            DataRow(row_id=-1, data={})

    def test_row_data_can_be_any_type(self):
        row1 = DataRow(row_id=0, data=None)
        row2 = DataRow(row_id=1, data=42)
        row3 = DataRow(row_id=2, data=["a", "b"])
        assert row1.data is None
        assert row2.data == 42
        assert row3.data == ["a", "b"]


class TestErrorRecordModel:
    def test_error_record_creation(self):
        row = DataRow(row_id=0, data={"x": 1})
        record = ErrorRecord(
            original_row=row,
            stage=STAGE_TRANSFORM,
            error_type="ValueError",
            error_message="bad value",
        )
        assert record.original_row is row
        assert record.stage == STAGE_TRANSFORM
        assert record.error_type == "ValueError"
        assert record.error_message == "bad value"

    def test_invalid_stage_rejected(self):
        row = DataRow(row_id=0, data={})
        with pytest.raises(ValueError, match="stage must be one of"):
            ErrorRecord(
                original_row=row,
                stage="unknown_stage",
                error_type="E",
                error_message="m",
            )

    def test_all_valid_stages(self):
        row = DataRow(row_id=0, data={})
        for s in [STAGE_EXTRACT, STAGE_TRANSFORM, STAGE_LOAD]:
            record = ErrorRecord(
                original_row=row, stage=s, error_type="E", error_message="m"
            )
            assert record.stage == s


class TestCheckpointModel:
    def test_new_checkpoint_defaults(self):
        cp = Checkpoint(job_id="j1")
        assert cp.job_id == "j1"
        assert cp.last_completed_stage == ""
        assert cp.rows_extracted == 0
        assert cp.rows_transformed == 0
        assert cp.rows_loaded == 0
        assert cp.rows_failed == 0
        assert cp.metadata == {}

    def test_is_stage_completed_empty(self):
        cp = Checkpoint(job_id="j1")
        assert cp.is_stage_completed(STAGE_EXTRACT) is False
        assert cp.is_stage_completed(STAGE_TRANSFORM) is False
        assert cp.is_stage_completed(STAGE_LOAD) is False
        assert cp.is_job_completed() is False

    def test_mark_stage_completed_extract(self):
        cp = Checkpoint(job_id="j1")
        cp.mark_stage_completed(STAGE_EXTRACT)
        assert cp.is_stage_completed(STAGE_EXTRACT) is True
        assert cp.is_stage_completed(STAGE_TRANSFORM) is False
        assert cp.is_stage_completed(STAGE_LOAD) is False
        assert cp.is_job_completed() is False

    def test_mark_stage_completed_transform(self):
        cp = Checkpoint(job_id="j1")
        cp.mark_stage_completed(STAGE_TRANSFORM)
        assert cp.is_stage_completed(STAGE_EXTRACT) is True
        assert cp.is_stage_completed(STAGE_TRANSFORM) is True
        assert cp.is_stage_completed(STAGE_LOAD) is False

    def test_mark_stage_completed_all(self):
        cp = Checkpoint(job_id="j1")
        cp.mark_stage_completed(STAGE_COMPLETED)
        assert cp.is_stage_completed(STAGE_EXTRACT) is True
        assert cp.is_stage_completed(STAGE_TRANSFORM) is True
        assert cp.is_stage_completed(STAGE_LOAD) is True
        assert cp.is_job_completed() is True

    def test_mark_invalid_stage_raises(self):
        cp = Checkpoint(job_id="j1")
        with pytest.raises(ValueError):
            cp.mark_stage_completed("bogus")

    def test_is_stage_completed_invalid_stage_returns_false(self):
        cp = Checkpoint(job_id="j1")
        cp.mark_stage_completed(STAGE_COMPLETED)
        assert cp.is_stage_completed("bogus") is False


class TestExceptionsHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(FatalEtlError, EtlError)
        assert issubclass(CheckpointCorruptedError, EtlError)
        assert issubclass(StageNotReachableError, EtlError)

    def test_checkpoint_corrupted_error_attributes(self):
        exc = CheckpointCorruptedError("/tmp/cp.json", "bad json")
        assert exc.path == "/tmp/cp.json"
        assert exc.reason == "bad json"
        assert "/tmp/cp.json" in str(exc)
        assert "bad json" in str(exc)

    def test_stage_not_reachable_error_attributes(self):
        exc = StageNotReachableError(STAGE_EXTRACT, STAGE_COMPLETED)
        assert exc.stage == STAGE_EXTRACT
        assert exc.completed_stage == STAGE_COMPLETED
