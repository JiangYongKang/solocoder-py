from __future__ import annotations

from typing import Any

import pytest

from solocoder_py.etl import (
    ETLPipeline,
    CheckpointStore,
    DataRow,
    IdentityTransformer,
    InMemoryExtractor,
    InMemoryLoader,
    Transformer,
    Loader,
    STAGE_COMPLETED,
    STAGE_EXTRACT,
    STAGE_LOAD,
    STAGE_TRANSFORM,
)


class TestEmptySourceEdgeCase:
    def test_empty_extract_completes(self, in_memory_loader, checkpoint_store):
        pipeline = ETLPipeline(
            job_id="empty_source",
            extractor=InMemoryExtractor([]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 0
        assert result.rows_transformed == 0
        assert result.rows_loaded == 0
        assert result.rows_failed == 0
        assert in_memory_loader.loaded_count == 0
        assert len(result.error_records) == 0

    def test_empty_source_rerun_is_noop(
        self, in_memory_loader, checkpoint_store
    ):
        job_id = "empty_rerun"
        pipeline1 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        result1 = pipeline1.run()
        assert result1.completed is True
        assert result1.resumed_from_checkpoint is False

        loader2 = InMemoryLoader()
        pipeline2 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([]),
            transformer=IdentityTransformer(),
            loader=loader2,
            checkpoint_store=checkpoint_store,
        )
        result2 = pipeline2.run()
        assert result2.completed is True
        assert result2.resumed_from_checkpoint is True
        assert loader2.loaded_count == 0


class FailAllTransformer(Transformer):
    def transform_row(self, row: DataRow) -> Any:
        raise ValueError(f"fail-all: {row.row_id}")


class FailAllLoader(Loader):
    def load_row(self, row: DataRow, transformed: Any) -> None:
        raise RuntimeError(f"load-fail: {row.row_id}")


class TestAllRowsToErrorChannel:
    def test_transform_all_fail(self, checkpoint_store):
        loader = InMemoryLoader()
        pipeline = ETLPipeline(
            job_id="all_fail_transform",
            extractor=InMemoryExtractor([1, 2, 3, 4, 5]),
            transformer=FailAllTransformer(),
            loader=loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 5
        assert result.rows_transformed == 0
        assert result.rows_loaded == 0
        assert result.rows_failed == 5
        assert loader.loaded_count == 0
        assert len(result.error_records) == 5
        for rec in result.error_records:
            assert rec.stage == STAGE_TRANSFORM
            assert rec.error_type == "ValueError"
            assert "fail-all" in rec.error_message

    def test_load_all_fail(self, checkpoint_store):
        loader = FailAllLoader()
        pipeline = ETLPipeline(
            job_id="all_fail_load",
            extractor=InMemoryExtractor([{"a": i} for i in range(4)]),
            transformer=IdentityTransformer(),
            loader=loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 4
        assert result.rows_transformed == 4
        assert result.rows_loaded == 0
        assert result.rows_failed == 4
        assert len(result.error_records) == 4
        for rec in result.error_records:
            assert rec.stage == STAGE_LOAD
            assert rec.error_type == "RuntimeError"


class PartialFailTransformer(Transformer):
    def transform_row(self, row: DataRow) -> Any:
        if row.row_id % 2 == 1:
            raise ValueError(f"odd row: {row.row_id}")
        return row.data * 2 if isinstance(row.data, int) else row.data


class PartialFailLoader(Loader):
    def __init__(self):
        self._loaded: list = []

    @property
    def loaded(self):
        return list(self._loaded)

    def load_row(self, row: DataRow, transformed: Any) -> None:
        if isinstance(transformed, dict) and transformed.get("fail"):
            raise RuntimeError("marked fail")
        self._loaded.append((row.row_id, transformed))


class TestMixedSuccessAndFailure:
    def test_partial_transform_fail(self, checkpoint_store):
        loader = InMemoryLoader()
        pipeline = ETLPipeline(
            job_id="partial_fail_t",
            extractor=InMemoryExtractor([10, 20, 30, 40, 50, 60]),
            transformer=PartialFailTransformer(),
            loader=loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 6
        assert result.rows_transformed == 3
        assert result.rows_loaded == 3
        assert result.rows_failed == 3
        transform_errors = [
            e for e in result.error_records if e.stage == STAGE_TRANSFORM
        ]
        assert len(transform_errors) == 3
        assert [e.original_row.row_id for e in transform_errors] == [1, 3, 5]
        assert loader.loaded_count == 3

    def test_partial_load_fail(self, checkpoint_store):
        loader = PartialFailLoader()
        source = [
            {"id": 0, "fail": False},
            {"id": 1, "fail": True},
            {"id": 2, "fail": False},
            {"id": 3, "fail": True},
            {"id": 4, "fail": False},
        ]
        pipeline = ETLPipeline(
            job_id="partial_fail_l",
            extractor=InMemoryExtractor(source),
            transformer=IdentityTransformer(),
            loader=loader,
            checkpoint_store=checkpoint_store,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 5
        assert result.rows_transformed == 5
        assert result.rows_loaded == 3
        assert result.rows_failed == 2
        load_errors = [
            e for e in result.error_records if e.stage == STAGE_LOAD
        ]
        assert len(load_errors) == 2
        assert len(loader.loaded) == 3
        assert [rid for rid, _ in loader.loaded] == [0, 2, 4]


class TestResumeBoundary:
    def test_resume_after_extract_completed(
        self, checkpoint_dir, checkpoint_store
    ):
        job_id = "resume_after_extract"
        data = list(range(8))

        class BreakAfterExtractTransformer(Transformer):
            def transform_row(self, row: DataRow) -> Any:
                from solocoder_py.etl import FatalEtlError
                if row.row_id == 0:
                    raise FatalEtlError("break at transform start")
                return row.data

        pipeline1 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor(data),
            transformer=BreakAfterExtractTransformer(),
            loader=InMemoryLoader(),
            checkpoint_store=checkpoint_store,
        )
        result1 = pipeline1.run()
        assert result1.completed is False
        assert result1.fatal_error is not None
        assert result1.rows_extracted == 8
        cp = checkpoint_store.load(job_id)
        assert cp is not None
        assert cp.last_completed_stage == STAGE_EXTRACT

        loader2 = InMemoryLoader()
        pipeline2 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor(data),
            transformer=IdentityTransformer(),
            loader=loader2,
            checkpoint_store=checkpoint_store,
        )
        result2 = pipeline2.run()
        assert result2.completed is True
        assert result2.resumed_from_checkpoint is True
        assert result2.rows_extracted == 8
        assert result2.rows_transformed == 8
        assert result2.rows_loaded == 8
        assert loader2.loaded_count == 8

    def test_resume_after_transform_completed(
        self, checkpoint_dir, checkpoint_store
    ):
        job_id = "resume_after_transform"
        data = list(range(6))

        class BreakAfterTransformLoader(Loader):
            def load_row(self, row: DataRow, transformed: Any) -> None:
                from solocoder_py.etl import FatalEtlError
                if row.row_id == 0:
                    raise FatalEtlError("break at load start")

        pipeline1 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor(data),
            transformer=IdentityTransformer(),
            loader=BreakAfterTransformLoader(),
            checkpoint_store=checkpoint_store,
        )
        result1 = pipeline1.run()
        assert result1.completed is False
        cp = checkpoint_store.load(job_id)
        assert cp is not None
        assert cp.last_completed_stage == STAGE_TRANSFORM

        loader2 = InMemoryLoader()
        pipeline2 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor(data),
            transformer=IdentityTransformer(),
            loader=loader2,
            checkpoint_store=checkpoint_store,
        )
        result2 = pipeline2.run()
        assert result2.completed is True
        assert result2.resumed_from_checkpoint is True
        assert loader2.loaded_count == 6

    def test_resume_when_already_completed(
        self, checkpoint_store, in_memory_loader
    ):
        job_id = "already_done"
        pipeline1 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([1, 2, 3]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        result1 = pipeline1.run()
        assert result1.completed is True
        assert in_memory_loader.loaded_count == 3

        loader2 = InMemoryLoader()
        pipeline2 = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([1, 2, 3]),
            transformer=IdentityTransformer(),
            loader=loader2,
            checkpoint_store=checkpoint_store,
        )
        result2 = pipeline2.run()
        assert result2.completed is True
        assert result2.resumed_from_checkpoint is True
        assert loader2.loaded_count == 0


class TestCheckpointPersistsAcrossRuns:
    def test_checkpoint_progress_visible_via_store(
        self, checkpoint_store, in_memory_loader
    ):
        job_id = "cp_visible"
        pipeline = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([9, 8, 7]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        pipeline.run()
        cp = checkpoint_store.load(job_id)
        assert cp is not None
        assert cp.last_completed_stage == STAGE_COMPLETED
        assert cp.rows_extracted == 3
        assert cp.rows_loaded == 3

    def test_clear_checkpoint(self, checkpoint_store, in_memory_loader):
        job_id = "clear_cp"
        pipeline = ETLPipeline(
            job_id=job_id,
            extractor=InMemoryExtractor([1]),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
            checkpoint_store=checkpoint_store,
        )
        pipeline.run()
        assert pipeline.get_checkpoint() is not None
        pipeline.clear_checkpoint()
        assert pipeline.get_checkpoint() is None
