from __future__ import annotations

from typing import Any

import pytest

from solocoder_py.etl import (
    ETLPipeline,
    Extractor,
    DataRow,
    IdentityTransformer,
    InMemoryExtractor,
    InMemoryLoader,
    Transformer,
    Loader,
    STAGE_EXTRACT,
    STAGE_LOAD,
    STAGE_TRANSFORM,
)


class TestInMemoryExtractor:
    def test_empty_extractor(self):
        ext = InMemoryExtractor()
        rows = list(ext.extract())
        assert rows == []

    def test_extract_with_rows(self):
        data = [{"a": 1}, {"b": 2}, {"c": 3}]
        ext = InMemoryExtractor(data)
        rows = list(ext.extract())
        assert len(rows) == 3
        assert [r.row_id for r in rows] == [0, 1, 2]
        assert [r.data for r in rows] == data

    def test_add_row(self):
        ext = InMemoryExtractor()
        ext.add_row("x")
        ext.add_row("y")
        rows = list(ext.extract())
        assert len(rows) == 2
        assert rows[0].data == "x"
        assert rows[1].data == "y"


class TestIdentityTransformer:
    def test_passthrough(self):
        tr = IdentityTransformer()
        row = DataRow(row_id=0, data={"k": "v"})
        assert tr.transform_row(row) == {"k": "v"}


class TestInMemoryLoader:
    def test_empty_loader(self):
        ld = InMemoryLoader()
        assert ld.loaded_count == 0
        assert ld.loaded_data == []

    def test_load_and_retrieve(self):
        ld = InMemoryLoader()
        row0 = DataRow(row_id=0, data="orig0")
        row1 = DataRow(row_id=1, data="orig1")
        ld.load_row(row0, "trans0")
        ld.load_row(row1, "trans1")
        assert ld.loaded_count == 2
        data = ld.loaded_data
        assert data[0]["row_id"] == 0
        assert data[0]["original"] == "orig0"
        assert data[0]["transformed"] == "trans0"
        assert data[1]["transformed"] == "trans1"

    def test_clear(self):
        ld = InMemoryLoader()
        ld.load_row(DataRow(row_id=0, data=1), 1)
        ld.clear()
        assert ld.loaded_count == 0
        assert ld.loaded_data == []


class UppercaseNameTransformer(Transformer):
    def transform_row(self, row: DataRow) -> dict:
        data = dict(row.data)
        if "name" not in data:
            raise ValueError("missing 'name' field")
        data["name"] = data["name"].upper()
        if "age" in data:
            if not isinstance(data["age"], int) or data["age"] < 0:
                raise ValueError(f"invalid age: {data['age']}")
            data["age_plus_one"] = data["age"] + 1
        return data


class TestNormalPipelineFlow:
    def test_full_pipeline_success(
        self, simple_source, simple_extractor, in_memory_loader
    ):
        transformer = UppercaseNameTransformer()
        pipeline = ETLPipeline(
            job_id="test_full",
            extractor=simple_extractor,
            transformer=transformer,
            loader=in_memory_loader,
            checkpoint_store=None,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.fatal_error is None
        assert result.rows_extracted == 4
        assert result.rows_transformed == 4
        assert result.rows_loaded == 4
        assert result.rows_failed == 0
        assert len(result.successful_rows) == 4
        assert len(result.error_records) == 0
        assert in_memory_loader.loaded_count == 4

        loaded = in_memory_loader.loaded_data
        assert loaded[0]["transformed"]["name"] == "ALICE"
        assert loaded[0]["transformed"]["age_plus_one"] == 31

    def test_pipeline_no_transformer(self, simple_source, in_memory_loader):
        pipeline = ETLPipeline(
            job_id="test_no_trans",
            extractor=InMemoryExtractor(simple_source),
            transformer=None,
            loader=in_memory_loader,
            checkpoint_store=None,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 4
        assert result.rows_transformed == 4
        assert result.rows_loaded == 4
        loaded = in_memory_loader.loaded_data
        assert loaded[0]["transformed"]["name"] == "Alice"

    def test_pipeline_no_checkpoint_store_no_crash(self, make_simple_pipeline):
        pipeline = make_simple_pipeline(
            job_id="no_cp", enable_checkpoint=False
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.resumed_from_checkpoint is False

    def test_pipeline_counting(self):
        data = list(range(10))
        pipeline = ETLPipeline(
            job_id="count_test",
            extractor=InMemoryExtractor(data),
            transformer=IdentityTransformer(),
            loader=InMemoryLoader(),
        )
        result = pipeline.run()
        assert result.rows_extracted == 10
        assert result.rows_transformed == 10
        assert result.rows_loaded == 10


class TestDecoupledStages:
    def test_custom_extractor(self, in_memory_loader):
        class RangeExtractor(Extractor):
            def __init__(self, n: int):
                self._n = n

            def extract(self):
                for i in range(self._n):
                    yield DataRow(row_id=i, data=i * 10)

        pipeline = ETLPipeline(
            job_id="custom_ext",
            extractor=RangeExtractor(5),
            transformer=IdentityTransformer(),
            loader=in_memory_loader,
        )
        result = pipeline.run()
        assert result.completed is True
        assert result.rows_extracted == 5
        assert [d["transformed"] for d in in_memory_loader.loaded_data] == [
            0, 10, 20, 30, 40
        ]

    def test_custom_transformer_and_loader(self):
        data = [1, 2, 3, 4, 5]
        results: list[int] = []

        class Doubler(Transformer):
            def transform_row(self, row: DataRow) -> Any:
                return row.data * 2

        class ListAppender(Loader):
            def load_row(self, row: DataRow, transformed: Any) -> None:
                results.append(transformed)

        pipeline = ETLPipeline(
            job_id="custom_both",
            extractor=InMemoryExtractor(data),
            transformer=Doubler(),
            loader=ListAppender(),
        )
        result = pipeline.run()
        assert result.completed is True
        assert results == [2, 4, 6, 8, 10]

    def test_stage_combinations_work(
        self, simple_source, identity_transformer, in_memory_loader
    ):
        pipeline1 = ETLPipeline(
            job_id="combo1",
            extractor=InMemoryExtractor(simple_source),
            transformer=identity_transformer,
            loader=in_memory_loader,
        )
        result1 = pipeline1.run()
        assert result1.completed is True

        pipeline2 = ETLPipeline(
            job_id="combo2",
            extractor=InMemoryExtractor(simple_source),
            transformer=None,
            loader=in_memory_loader,
        )
        result2 = pipeline2.run()
        assert result2.completed is True
