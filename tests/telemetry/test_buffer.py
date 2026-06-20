from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from solocoder_py.telemetry.buffer import BatchBuffer
from solocoder_py.telemetry.clock import ManualClock
from solocoder_py.telemetry.exceptions import BufferClosedError, InvalidDataError
from solocoder_py.telemetry.models import BufferConfig, FlushReason, FlushResult


class TestBatchSizeTrigger:
    def test_flush_triggered_at_batch_size(self, buffer_config_default, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=3, timeout_seconds=100.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        buffer.ingest({"id": 2})
        assert len(collected_flushes) == 0
        buffer.ingest({"id": 3})
        assert len(collected_flushes) == 1
        assert collected_flushes[0].reason == FlushReason.BATCH_SIZE
        assert len(collected_flushes[0].batch) == 3

    def test_batch_size_one_immediate_trigger(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=1, timeout_seconds=100.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        assert len(collected_flushes) == 1
        assert collected_flushes[0].reason == FlushReason.BATCH_SIZE
        assert len(collected_flushes[0].batch) == 1

    def test_exact_batch_size_triggers(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=5, timeout_seconds=100.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        for i in range(5):
            buffer.ingest({"id": i})
        assert len(collected_flushes) == 1
        assert len(collected_flushes[0].batch) == 5


class TestTimeoutTrigger:
    def test_timeout_triggers_flush(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=100, timeout_seconds=5.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        assert len(collected_flushes) == 0

        manual_clock.advance(5.0)
        buffer._try_flush(force=False)
        assert len(collected_flushes) == 1
        assert collected_flushes[0].reason == FlushReason.TIMEOUT

    def test_timeout_not_triggered_before_expiry(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=100, timeout_seconds=10.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        manual_clock.advance(5.0)
        buffer._try_flush(force=False)
        assert len(collected_flushes) == 0

    def test_timeout_zero_flushes_immediately(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=100, timeout_seconds=0.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        assert len(collected_flushes) == 1
        assert collected_flushes[0].reason == FlushReason.TIMEOUT


class TestManualFlush:
    def test_manual_flush_force(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        buffer.ingest({"id": 1})
        buffer.ingest({"id": 2})
        assert len(collected_flushes) == 0

        result = buffer.flush()
        assert result is not None
        assert result.reason == FlushReason.MANUAL
        assert len(result.batch) == 2

    def test_flush_empty_buffer_returns_none(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        result = buffer.flush()
        assert result is None
        assert len(collected_flushes) == 0


class TestBufferClosed:
    def test_ingest_after_close_raises(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)
        buffer.close()

        with pytest.raises(BufferClosedError):
            buffer.ingest({"id": 1})

    def test_ingest_many_after_close_raises(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)
        buffer.close()

        with pytest.raises(BufferClosedError):
            buffer.ingest_many([{"id": 1}])


class TestInvalidData:
    def test_ingest_non_dict_raises(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        with pytest.raises(InvalidDataError):
            buffer.ingest("not a dict")

    def test_ingest_list_raises(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        with pytest.raises(InvalidDataError):
            buffer.ingest([1, 2, 3])

    def test_ingest_many_with_non_dict_item_raises(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        with pytest.raises(InvalidDataError):
            buffer.ingest_many([{"id": 1}, "not a dict"])


class TestBufferProperties:
    def test_buffer_size_tracks_correctly(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)

        assert buffer.buffer_size == 0
        buffer.ingest({"id": 1})
        assert buffer.buffer_size == 1
        buffer.ingest({"id": 2})
        assert buffer.buffer_size == 2

    def test_is_closed_property(self, buffer_config_default, manual_clock, collected_flushes):
        buffer = BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock)
        assert buffer.is_closed is False
        buffer.close()
        assert buffer.is_closed is True


class TestConcurrentAccess:
    def test_concurrent_ingest_thread_safety(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=1000, timeout_seconds=100.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        errors = []

        def ingest_items(start, count):
            try:
                for i in range(start, start + count):
                    buffer.ingest({"id": i})
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
        total_items = sum(len(r.batch) for r in collected_flushes) + buffer.buffer_size
        assert total_items == 1000

    def test_concurrent_flush_race_safety(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=1, timeout_seconds=0.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        errors = []

        def ingest_and_flush(item_id):
            try:
                buffer.ingest({"id": item_id})
                buffer.flush()
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            thread = threading.Thread(target=ingest_and_flush, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        total_items = sum(len(r.batch) for r in collected_flushes)
        assert total_items == 50


class TestIngestMany:
    def test_ingest_many_adds_all(self, manual_clock, collected_flushes):
        config = BufferConfig(batch_size=10, timeout_seconds=100.0)
        buffer = BatchBuffer(config, on_flush=collected_flushes.append, clock=manual_clock)

        items = [{"id": i} for i in range(3)]
        buffer.ingest_many(items)
        assert buffer.buffer_size == 3


class TestContextManager:
    def test_context_manager(self, buffer_config_default, manual_clock, collected_flushes):
        with BatchBuffer(buffer_config_default, on_flush=collected_flushes.append, clock=manual_clock) as buf:
            buf.ingest({"id": 1})
        assert buf.is_closed
