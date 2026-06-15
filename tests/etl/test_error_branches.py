from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from solocoder_py.etl import (
    ETLPipeline,
    CheckpointCorruptedError,
    CheckpointStore,
    DataRow,
    FatalEtlError,
    IdentityTransformer,
    InMemoryExtractor,
    InMemoryLoader,
    Transformer,
    Loader,
    Extractor,
    STAGE_EXTRACT,
    STAGE_TRANSFORM,
)


class FatalExtractor(Extractor):
    def __init__(self, fail_after: int = 2):
        self._fail_after = fail_after

    def extract(self):
        for i in range(self._fail_after):
            yield DataRow(row_id=i, data=i)
        raise RuntimeError("extract iterator exploded")


class FatalTransformer(Transformer):
    def __init__(self, fail_at: int = 1):
        self._fail_at = fail_at
        self._count = 0

    def transform_row(self, row: DataRow) -> Any:
        self._count += 1
        if self._count - 1 == self._fail_at:
            raise FatalEtlError("transformer fatal error")
        return row.data


class FatalLoader(Loader):
    def __init__(self, fail_at: int = 2):
        self._fail_at = fail_at
        self._count = 0
        self._loaded: list = []

    @property
    def loaded(self):
        return list(self._loaded)

    def load_row(self, row: DataRow, transformed: Any) -> None:
        self._count += 1
        self._loaded.append((row.row_id, transformed))
        if self._count - 1 == self._fail_at:
            raise FatalEtlError("loader fatal error")


class TestFatalErrorTermination:
    def test_extractor_runtime_error_becomes_fatal(
        self, checkpoint_store
    ):
        pipeline = ETLPipeline(
            job_id="fatal_extract",
            extractor=FatalExtractor(fail_after=3),
            transformer=IdentityTransformer(),
            loader=InMemoryLoader(),
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        assert "Extractor failed" in str(result.fatal_error)
        assert result.rows_extracted == 3
        assert result.rows_failed == 3
        assert len(result.error_records) == 3
        for rec in result.error_records:
            assert rec.stage == STAGE_EXTRACT

    def test_transformer_fatal_error_stops_job(
        self, checkpoint_store
    ):
        pipeline = ETLPipeline(
            job_id="fatal_transform",
            extractor=InMemoryExtractor([0, 1, 2, 3, 4]),
            transformer=FatalTransformer(fail_at=1),
            loader=InMemoryLoader(),
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        assert result.rows_extracted == 5
        assert result.rows_transformed == 1
        assert result.rows_loaded == 0
        cp = checkpoint_store.load("fatal_transform")
        assert cp is not None
        assert cp.last_completed_stage == STAGE_EXTRACT

    def test_loader_fatal_error_stops_job(
        self, checkpoint_store
    ):
        loader = FatalLoader(fail_at=2)
        pipeline = ETLPipeline(
            job_id="fatal_load",
            extractor=InMemoryExtractor(list(range(10))),
            transformer=IdentityTransformer(),
            loader=loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        assert result.rows_extracted == 10
        assert result.rows_transformed == 10
        assert result.rows_loaded == 2
        assert len(loader.loaded) == 3


class TestCorruptedCheckpointRecovery:
    def test_run_with_corrupted_checkpoint_json(
        self, checkpoint_dir: Path, in_memory_loader
    ):
        import json

        job_id = "corrupted_cp_json"
        cp_path = checkpoint_dir / f"{job_id}.checkpoint.json"
        cp_path.write_text("not json at all {{{{", encoding="utf-8")
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))

        pipeline = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([1, 2, 3]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        inner = result.fatal_error.__cause__
        assert isinstance(inner, CheckpointCorruptedError)

    def test_run_with_corrupted_extracted_pickle(
        self, checkpoint_dir: Path, in_memory_loader
    ):
        from solocoder_py.etl import Checkpoint

        job_id = "corrupted_extracted"
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        cp = Checkpoint(job_id=job_id)
        cp.mark_stage_completed(STAGE_EXTRACT)
        cp.rows_extracted = 5
        store.save(cp)

        pkl = checkpoint_dir / f"{job_id}.extracted.pkl"
        pkl.write_bytes(b"\x00\x01\x02 not a real pickle")

        pipeline = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([1, 2, 3, 4, 5]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        cause = result.fatal_error.__cause__
        assert isinstance(cause, CheckpointCorruptedError)

    def test_run_with_corrupted_transformed_pickle(
        self, checkpoint_dir: Path
    ):
        from solocoder_py.etl import Checkpoint

        job_id = "corrupted_transformed"
        store = CheckpointStore(checkpoint_dir=str(checkpoint_dir))
        cp = Checkpoint(job_id=job_id)
        cp.mark_stage_completed(STAGE_TRANSFORM)
        cp.rows_extracted = 3
        cp.rows_transformed = 3
        store.save(cp)
        store.save_extracted(
            job_id,
            [DataRow(row_id=i, data=i) for i in range(3)],
        )

        pkl = checkpoint_dir / f"{job_id}.transformed.pkl"
        pkl.write_bytes(b"garbage data \xff\xfe\x00")

        pipeline = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([0, 1, 2]),
            transformer=IdentityTransformer(),
            loader=InMemoryLoader(),
            checkpoint_store=store,
        )
        result = pipeline.run()
        assert result.completed is False
        assert isinstance(result.fatal_error, FatalEtlError)
        cause = result.fatal_error.__cause__
        assert isinstance(cause, CheckpointCorruptedError)


class TestExplicitGetCheckpoint:
    def test_get_checkpoint_without_store(self):
        pipeline = ETLPipeline(
            job_id="no_store",
            extractor=InMemoryExtractor([]),
            transformer=None,
            loader=InMemoryLoader(),
            checkpoint_store=None,
        )
        assert pipeline.get_checkpoint() is None

    def test_get_checkpoint_returns_none_before_run(self, checkpoint_store):
        pipeline = ETLPipeline(
            job_id="not_run",
            extractor=InMemoryExtractor([]),
            transformer=None,
            loader=InMemoryLoader(),
            checkpoint_store=checkpoint_store,
        )
        assert pipeline.get_checkpoint() is None

    def test_get_checkpoint_after_run(self, checkpoint_store, in_memory_loader):
        pipeline = ETLPipeline(
            job_id="after_run",
            extractor=InMemoryExtractor([10, 20]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        pipeline.run()
        cp = pipeline.get_checkpoint()
        assert cp is not None
        assert cp.rows_extracted == 2
        assert cp.rows_loaded == 2


class TestErrorRecordDetails:
    def test_error_record_contains_original_row(self):
        class Broken(Transformer):
            def transform_row(self, row: DataRow) -> Any:
                raise TypeError("wrong type")

        pipeline = ETLPipeline(
            job_id="err_detail",
            extractor=InMemoryExtractor([{"x": "bad"}]),
            transformer=Broken(),
            loader=InMemoryLoader(),
        )
        result = pipeline.run()
        assert len(result.error_records) == 1
        rec = result.error_records[0]
        assert rec.original_row.row_id == 0
        assert rec.original_row.data == {"x": "bad"}
        assert rec.error_type == "TypeError"
        assert rec.error_message == "wrong type"
        assert rec.stage == STAGE_TRANSFORM

    def test_extractor_error_record_timestamp_set(self):
        from datetime import datetime

        pipeline = ETLPipeline(
            job_id="err_ts",
            extractor=FatalExtractor(fail_after=1),
            transformer=IdentityTransformer(),
            loader=InMemoryLoader(),
        )
        result = pipeline.run()
        assert len(result.error_records) >= 1
        assert isinstance(result.error_records[0].timestamp, datetime)
