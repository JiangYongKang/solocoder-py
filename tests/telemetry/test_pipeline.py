from __future__ import annotations

import threading

import pytest

from solocoder_py.telemetry.clock import ManualClock
from solocoder_py.telemetry.exceptions import (
    BufferClosedError,
    InvalidDataError,
    CircularMappingError,
    TargetConflictError,
)
from solocoder_py.telemetry.models import (
    BufferConfig,
    FlushReason,
    LateDataStrategy,
    ProcessedBatch,
    SchemaConfig,
    WindowConfig,
)
from solocoder_py.telemetry.pipeline import TelemetryPipeline


class TestPipelineBatchSizeTrigger:
    def test_batch_size_triggers_full_pipeline(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=3, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={"temp": "temperature"}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        batches = []
        pipeline._on_batch = batches.append

        pipeline.ingest({"temp": 25.0, "timestamp": 100.0})
        pipeline.ingest({"temp": 26.0, "timestamp": 101.0})
        assert len(batches) == 0
        pipeline.ingest({"temp": 27.0, "timestamp": 102.0})
        assert len(batches) == 1

        batch = batches[0]
        assert batch.original_count == 3
        assert len(batch.data) == 3
        assert all("temperature" in r for r in batch.data)


class TestPipelineTimeoutTrigger:
    def test_timeout_triggers_pipeline(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=100, timeout_seconds=5.0),
            schema_config=SchemaConfig(field_mapping={"temp": "temperature"}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        batches = []
        pipeline._on_batch = batches.append

        pipeline.ingest({"temp": 25.0, "timestamp": 100.0})
        assert len(batches) == 0

        manual_clock.advance(5.0)
        pipeline._buffer._try_flush(force=False)
        assert len(batches) == 1


class TestPipelineSchemaNormalization:
    def test_schema_normalized_in_pipeline(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=2, timeout_seconds=100.0),
            schema_config=SchemaConfig(
                field_mapping={"temp": "temperature", "humid": "humidity"},
                drop_unmapped=True,
            ),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        batches = []
        pipeline._on_batch = batches.append

        pipeline.ingest({"temp": 25.0, "humid": 60, "extra": "val", "timestamp": 100.0})
        pipeline.ingest({"temp": 26.0, "humid": 55, "extra": "val2", "timestamp": 101.0})

        batch = batches[0]
        for record in batch.data:
            assert "temperature" in record
            assert "humidity" in record
            assert "extra" not in record
            assert "temp" not in record

    def test_nested_schema_in_pipeline(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=1, timeout_seconds=100.0),
            schema_config=SchemaConfig(
                field_mapping={"device.temp": "device.temperature"},
            ),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        batches = []
        pipeline._on_batch = batches.append

        pipeline.ingest({"device": {"temp": 22.1}, "timestamp": 100.0})

        batch = batches[0]
        assert batch.data[0]["device"]["temperature"] == 22.1


class TestPipelineOrderWindow:
    def test_in_order_data_passes_through(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=5, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        pipeline.ingest({"timestamp": 100.0, "v": 1})
        pipeline.ingest({"timestamp": 101.0, "v": 2})
        pipeline.ingest({"timestamp": 102.0, "v": 3})
        pipeline.ingest({"timestamp": 103.0, "v": 4})
        pipeline.ingest({"timestamp": 104.0, "v": 5})

        batch = pipeline.processed_batches[0]
        assert len(batch.data) == 5
        assert len(batch.late_data) == 0

    def test_out_of_order_within_window_resorted(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=3, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        pipeline.ingest({"timestamp": 100.0, "v": "a"})
        pipeline.ingest({"timestamp": 120.0, "v": "b"})
        pipeline.ingest({"timestamp": 105.0, "v": "c"})

        batch = pipeline.processed_batches[0]
        assert len(batch.data) == 3
        assert len(batch.late_data) == 0
        timestamps = [r["timestamp"] for r in batch.data]
        assert timestamps == [100.0, 105.0, 120.0]

    def test_late_data_beyond_window(self, manual_clock):
        late_records = []
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=3, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(
                tolerance_seconds=5.0,
                late_data_strategy=LateDataStrategy.CALLBACK,
            ),
            on_late=late_records.append,
            clock=manual_clock,
        )

        pipeline.ingest({"timestamp": 100.0, "v": "a"})
        pipeline.ingest({"timestamp": 200.0, "v": "b"})
        pipeline.ingest({"timestamp": 50.0, "v": "c"})

        batch = pipeline.processed_batches[0]
        assert len(batch.late_data) == 1
        assert batch.late_data[0]["v"] == "c"

    def test_cross_batch_out_of_order_within_window_accepted(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=2, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        pipeline.ingest({"timestamp": 100.0, "v": "a1"})
        pipeline.ingest({"timestamp": 200.0, "v": "a2"})
        assert len(pipeline.processed_batches) == 1
        batch1 = pipeline.processed_batches[0]
        assert len(batch1.late_data) == 0
        assert pipeline.order_window.high_watermark == 200.0

        pipeline.ingest({"timestamp": 180.0, "v": "b1"})
        pipeline.ingest({"timestamp": 210.0, "v": "b2"})
        assert len(pipeline.processed_batches) == 2
        batch2 = pipeline.processed_batches[1]
        assert len(batch2.late_data) == 0
        assert batch2.data[0]["v"] == "b1"
        assert len(batch2.data) == 2

    def test_cross_batch_late_beyond_window_rejected(self, manual_clock):
        late_records = []
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=2, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(
                tolerance_seconds=30.0,
                late_data_strategy=LateDataStrategy.CALLBACK,
            ),
            on_late=late_records.append,
            clock=manual_clock,
        )

        pipeline.ingest({"timestamp": 100.0, "v": "a1"})
        pipeline.ingest({"timestamp": 200.0, "v": "a2"})
        assert pipeline.order_window.high_watermark == 200.0

        pipeline.ingest({"timestamp": 50.0, "v": "b1"})
        pipeline.ingest({"timestamp": 210.0, "v": "b2"})
        assert len(pipeline.processed_batches) == 2
        batch2 = pipeline.processed_batches[1]
        assert len(batch2.late_data) == 1
        assert batch2.late_data[0]["v"] == "b1"
        assert len(late_records) == 1
        assert late_records[0]["v"] == "b1"


class TestPipelineManualFlush:
    def test_manual_flush(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=100, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={"temp": "temperature"}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        pipeline.ingest({"temp": 25.0, "timestamp": 100.0})
        pipeline.ingest({"temp": 26.0, "timestamp": 101.0})

        batch = pipeline.flush()
        assert batch is not None
        assert batch.original_count == 2
        assert all("temperature" in r for r in batch.data)

    def test_flush_empty_pipeline(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=100, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        result = pipeline.flush()
        assert result is None


class TestPipelineInvalidData:
    def test_ingest_non_dict_raises(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=10, timeout_seconds=10.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        with pytest.raises(InvalidDataError):
            pipeline.ingest("not a dict")


class TestPipelineCircularMapping:
    def test_circular_mapping_in_config_raises(self, manual_clock):
        with pytest.raises(CircularMappingError):
            TelemetryPipeline(
                buffer_config=BufferConfig(batch_size=10, timeout_seconds=10.0),
                schema_config=SchemaConfig(field_mapping={"a": "b", "b": "a"}),
                window_config=WindowConfig(tolerance_seconds=30.0),
                clock=manual_clock,
            )


class TestPipelineTargetConflict:
    def test_target_conflict_in_config_raises(self, manual_clock):
        with pytest.raises(TargetConflictError):
            TelemetryPipeline(
                buffer_config=BufferConfig(batch_size=10, timeout_seconds=10.0),
                schema_config=SchemaConfig(field_mapping={"temp": "t", "tmp": "t"}),
                window_config=WindowConfig(tolerance_seconds=30.0),
                clock=manual_clock,
            )


class TestPipelineConcurrentAccess:
    def test_concurrent_ingest(self, manual_clock):
        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=1000, timeout_seconds=100.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        )

        errors = []

        def ingest_items(start, count):
            try:
                for i in range(start, start + count):
                    pipeline.ingest({"timestamp": float(i), "v": i})
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(10):
            thread = threading.Thread(target=ingest_items, args=(t * 100, 100))
            threads.append(thread)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0


class TestPipelineContextManager:
    def test_context_manager(self, manual_clock):
        with TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=10, timeout_seconds=10.0),
            schema_config=SchemaConfig(field_mapping={}),
            window_config=WindowConfig(tolerance_seconds=30.0),
            clock=manual_clock,
        ) as pipeline:
            pipeline.ingest({"timestamp": 100.0, "v": 1})
        assert pipeline.buffer.is_closed


class TestPipelineEndToEnd:
    def test_full_pipeline_flow(self, manual_clock):
        batches = []

        pipeline = TelemetryPipeline(
            buffer_config=BufferConfig(batch_size=4, timeout_seconds=10.0),
            schema_config=SchemaConfig(
                field_mapping={
                    "temp": "temperature",
                    "humid": "humidity",
                    "device.temp": "device.temperature",
                },
                drop_unmapped=False,
            ),
            window_config=WindowConfig(tolerance_seconds=30.0),
            on_batch=batches.append,
            clock=manual_clock,
        )

        pipeline.ingest({"temp": 25.0, "humid": 60, "timestamp": 100.0, "id": "s1"})
        pipeline.ingest({"temp": 26.0, "humid": 55, "timestamp": 101.0, "id": "s2"})
        pipeline.ingest({"device": {"temp": 22.1}, "timestamp": 102.0})
        pipeline.ingest({"temp": 27.0, "humid": 50, "timestamp": 95.0, "id": "s4"})

        assert len(batches) == 1
        batch = batches[0]
        assert batch.original_count == 4
        assert len(batch.data) == 4
        assert len(batch.late_data) == 0

        for record in batch.data:
            if "device" in record and "temperature" in record.get("device", {}):
                continue
            if "temperature" in record:
                assert "temp" not in record
                assert "humidity" in record

        timestamps = [r["timestamp"] for r in batch.data]
        assert timestamps == sorted(timestamps)
