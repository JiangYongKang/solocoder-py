from __future__ import annotations

from pathlib import Path

import pytest

from solocoder_py.etl import (
    STAGE_EXTRACT,
    STAGE_LOAD,
    STAGE_TRANSFORM,
    Checkpoint,
    CheckpointCorruptedError,
    CheckpointStore,
    DataRow,
)


class TestCheckpointStoreBasics:
    def test_create_store_creates_dir(self, tmp_path: Path):
        target = tmp_path / "sub" / "dir"
        assert not target.exists()
        store = CheckpointStore(checkpoint_dir=str(target))
        assert target.exists()
        assert target.is_dir()

    def test_save_and_load_checkpoint(self, checkpoint_store: CheckpointStore):
        cp = Checkpoint(job_id="job1")
        cp.mark_stage_completed(STAGE_EXTRACT)
        cp.rows_extracted = 10
        cp.rows_failed = 2
        checkpoint_store.save(cp)

        loaded = checkpoint_store.load("job1")
        assert loaded is not None
        assert loaded.job_id == "job1"
        assert loaded.last_completed_stage == STAGE_EXTRACT
        assert loaded.rows_extracted == 10
        assert loaded.rows_failed == 2

    def test_load_missing_job_returns_none(self, checkpoint_store: CheckpointStore):
        assert checkpoint_store.load("nonexistent") is None

    def test_delete_removes_all_files(self, checkpoint_store: CheckpointStore):
        cp = Checkpoint(job_id="j1")
        cp.mark_stage_completed(STAGE_EXTRACT)
        checkpoint_store.save(cp)
        rows = [DataRow(row_id=i, data=i) for i in range(5)]
        checkpoint_store.save_extracted("j1", rows)
        checkpoint_store.save_transformed(
            "j1", [(r, r.data * 2) for r in rows]
        )

        result = checkpoint_store.delete("j1")
        assert result is True
        assert checkpoint_store.load("j1") is None
        assert checkpoint_store.load_extracted("j1") is None
        assert checkpoint_store.load_transformed("j1") is None

    def test_delete_missing_job_returns_false(self, checkpoint_store: CheckpointStore):
        assert checkpoint_store.delete("missing") is False


class TestCheckpointStoreCorrupted:
    def test_corrupted_json_raises(self, checkpoint_dir: Path):
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        cp_path = checkpoint_dir / "badjob.checkpoint.json"
        cp_path.write_text("this is not json{{{", encoding="utf-8")

        with pytest.raises(CheckpointCorruptedError) as exc:
            store.load("badjob")
        assert "badjob.checkpoint.json" in exc.value.path

    def test_missing_field_raises(self, checkpoint_dir: Path):
        import json

        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        cp_path = checkpoint_dir / "badjob2.checkpoint.json"
        payload = {"job_id": "badjob2"}
        cp_path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(CheckpointCorruptedError):
            store.load("badjob2")

    def test_corrupted_extracted_pickle_raises(self, checkpoint_dir: Path):
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        pkl_path = checkpoint_dir / "bad.extracted.pkl"
        pkl_path.write_bytes(b"not a pickle \x00\x01\x02")

        with pytest.raises(CheckpointCorruptedError):
            store.load_extracted("bad")

    def test_corrupted_transformed_pickle_raises(self, checkpoint_dir: Path):
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        pkl_path = checkpoint_dir / "bad.transformed.pkl"
        pkl_path.write_bytes(b"\x00\x01\x02 definitely not pickle")

        with pytest.raises(CheckpointCorruptedError):
            store.load_transformed("bad")


class TestCheckpointStoreExtractedData:
    def test_save_and_load_extracted(self, checkpoint_store: CheckpointStore):
        rows = [
            DataRow(row_id=0, data={"a": 1}),
            DataRow(row_id=1, data={"a": 2}),
            DataRow(row_id=2, data={"a": 3}),
        ]
        checkpoint_store.save_extracted("j", rows)
        loaded = checkpoint_store.load_extracted("j")
        assert loaded is not None
        assert len(loaded) == 3
        assert loaded[0].row_id == 0
        assert loaded[0].data == {"a": 1}
        assert loaded[2].row_id == 2

    def test_load_missing_extracted_returns_none(self, checkpoint_store: CheckpointStore):
        assert checkpoint_store.load_extracted("nope") is None


class TestCheckpointStoreTransformedData:
    def test_save_and_load_transformed(self, checkpoint_store: CheckpointStore):
        rows = [DataRow(row_id=i, data=f"orig-{i}") for i in range(3)]
        pairs = [(r, f"transformed-{r.row_id}") for r in rows]
        checkpoint_store.save_transformed("j", pairs)
        loaded = checkpoint_store.load_transformed("j")
        assert loaded is not None
        assert len(loaded) == 3
        assert loaded[0][0].row_id == 0
        assert loaded[0][1] == "transformed-0"
        assert loaded[2][0].data == "orig-2"
        assert loaded[2][1] == "transformed-2"

    def test_load_missing_transformed_returns_none(self, checkpoint_store: CheckpointStore):
        assert checkpoint_store.load_transformed("nope") is None
