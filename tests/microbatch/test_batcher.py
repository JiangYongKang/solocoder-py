from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.microbatch import (
    BatchRecord,
    BatchStatus,
    BufferClosedError,
    FlushResult,
    InvalidConfigError,
    ManualClock,
    MicroBatchBatcher,
    MicroBatchConfig,
    SystemClock,
)


class TransientError(Exception):
    pass


class FatalError(Exception):
    pass


class RecordingWriter:
    def __init__(self, always_succeed: bool = True) -> None:
        self.batches: list[list] = []
        self.call_count = 0
        self._always_succeed = always_succeed
        self._first_n_fail: int = 0
        self._fail_indices: set[int] = set()
        self._lock = threading.Lock()
        self._call_event: threading.Event | None = None
        self._delay_before_response: float = 0.0

    def set_call_event(self, event: threading.Event) -> None:
        self._call_event = event

    def set_delay_before_response(self, delay: float) -> None:
        self._delay_before_response = delay

    def set_first_n_calls_fail(self, n: int) -> None:
        self._first_n_fail = n

    def add_fail_call_index(self, index: int) -> None:
        self._fail_indices.add(index)

    def write_batch(self, batch) -> FlushResult:
        with self._lock:
            self.call_count += 1
            current_call = self.call_count
            self.batches.append(list(batch))

        if self._delay_before_response > 0:
            time.sleep(self._delay_before_response)

        if self._call_event is not None:
            self._call_event.set()

        should_fail = current_call <= self._first_n_fail or current_call in self._fail_indices

        if should_fail:
            return FlushResult.fail(TransientError(f"simulated failure on call {current_call}"))

        if not self._always_succeed:
            return FlushResult.fail(FatalError("fatal failure"))

        return FlushResult.ok()


class TestMicroBatchConfig:
    def test_default_config_valid(self):
        config = MicroBatchConfig()
        assert config.max_size == 100
        assert config.max_interval == 5.0
        assert config.max_retries == 3
        assert config.retry_interval == 1.0

    def test_valid_custom_config(self):
        config = MicroBatchConfig(
            max_size=10,
            max_interval=2.0,
            max_retries=5,
            retry_interval=0.5,
            scheduler_interval=0.05,
        )
        assert config.max_size == 10
        assert config.max_retries == 5

    def test_invalid_max_size(self):
        with pytest.raises(InvalidConfigError, match="max_size"):
            MicroBatchConfig(max_size=0)
        with pytest.raises(InvalidConfigError, match="max_size"):
            MicroBatchConfig(max_size=-1)

    def test_invalid_max_interval(self):
        with pytest.raises(InvalidConfigError, match="max_interval"):
            MicroBatchConfig(max_interval=0)
        with pytest.raises(InvalidConfigError, match="max_interval"):
            MicroBatchConfig(max_interval=-1)

    def test_invalid_max_retries(self):
        with pytest.raises(InvalidConfigError, match="max_retries"):
            MicroBatchConfig(max_retries=-1)

    def test_invalid_retry_interval(self):
        with pytest.raises(InvalidConfigError, match="retry_interval"):
            MicroBatchConfig(retry_interval=-1)

    def test_zero_retry_interval_valid(self):
        config = MicroBatchConfig(retry_interval=0)
        assert config.retry_interval == 0

    def test_invalid_scheduler_interval(self):
        with pytest.raises(InvalidConfigError, match="scheduler_interval"):
            MicroBatchConfig(scheduler_interval=0)


class TestNormalFlowsBySize:
    def test_size_trigger_flush_single_submit(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=3, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("item1")
        batcher.submit("item2")
        assert writer.call_count == 0
        assert batcher.buffer_size == 2

        batcher.submit("item3")
        assert writer.call_count == 1
        assert batcher.buffer_size == 0
        assert len(writer.batches) == 1
        assert writer.batches[0] == ["item1", "item2", "item3"]

        success = batcher.success_batches
        assert len(success) == 1
        assert success[0].status == BatchStatus.SUCCESS
        assert success[0].items == ["item1", "item2", "item3"]
        assert success[0].attempts == 1
        assert success[0].batch_id == 1

    def test_size_trigger_exactly_at_threshold(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=5, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        for i in range(4):
            batcher.submit(f"item{i}")
        assert writer.call_count == 0
        assert batcher.buffer_size == 4

        batcher.submit("item4")
        assert writer.call_count == 1
        assert batcher.buffer_size == 0
        assert writer.batches[0] == ["item0", "item1", "item2", "item3", "item4"]

    def test_size_trigger_submit_many(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=3, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit_many(["item1", "item2", "item3"])
        assert writer.call_count == 1
        assert writer.batches[0] == ["item1", "item2", "item3"]
        assert batcher.buffer_size == 0

    def test_size_trigger_submit_many_over_threshold(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=3, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit_many(["item1", "item2", "item3", "item4", "item5"])
        assert writer.call_count == 1
        assert writer.batches[0] == ["item1", "item2", "item3", "item4", "item5"]
        assert batcher.buffer_size == 0

    def test_multiple_batches_by_size(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=2, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        batcher.submit("b")
        assert writer.call_count == 1

        batcher.submit("c")
        batcher.submit("d")
        assert writer.call_count == 2

        assert writer.batches[0] == ["a", "b"]
        assert writer.batches[1] == ["c", "d"]
        assert len(batcher.success_batches) == 2
        assert batcher.success_batches[0].batch_id == 1
        assert batcher.success_batches[1].batch_id == 2

    def test_flush_clears_buffer(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=10, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("x")
        batcher.submit("y")
        assert batcher.buffer_size == 2

        flushed = batcher.flush_if_needed(force=True)
        assert flushed is True
        assert batcher.buffer_size == 0
        assert writer.call_count == 1

        flushed_again = batcher.flush_if_needed(force=True)
        assert flushed_again is False


class TestNormalFlowsByTime:
    def test_time_trigger_flush(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=5.0)
        clock = ManualClock(start_time=0.0)
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("item1")
        batcher.submit("item2")
        assert writer.call_count == 0
        assert batcher.buffer_size == 2

        clock.advance(4.0)
        flushed = batcher.flush_if_needed(force=False)
        assert flushed is False
        assert writer.call_count == 0

        clock.advance(1.0)
        flushed = batcher.flush_if_needed(force=False)
        assert flushed is True
        assert writer.call_count == 1
        assert batcher.buffer_size == 0
        assert writer.batches[0] == ["item1", "item2"]

    def test_time_trigger_after_last_flush(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=5.0)
        clock = ManualClock(start_time=0.0)
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        clock.advance(10.0)
        batcher.flush_if_needed(force=False)
        assert writer.call_count == 1

        batcher.submit("b")
        assert writer.call_count == 1

        clock.advance(4.0)
        batcher.flush_if_needed(force=False)
        assert writer.call_count == 1

        clock.advance(1.0)
        batcher.flush_if_needed(force=False)
        assert writer.call_count == 2
        assert writer.batches[1] == ["b"]

    def test_flush_all_with_multiple_batches(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=2, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        batcher.submit("b")
        batcher.submit("c")
        batcher.flush_all()

        assert writer.call_count == 2
        assert writer.batches[0] == ["a", "b"]
        assert writer.batches[1] == ["c"]


class TestBoundaryConditions:
    def test_empty_buffer_does_not_flush(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=3, max_interval=1.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        flushed = batcher.flush_if_needed(force=False)
        assert flushed is False
        assert writer.call_count == 0

        clock.advance(10.0)
        flushed = batcher.flush_if_needed(force=False)
        assert flushed is False
        assert writer.call_count == 0

    def test_force_flush_empty_buffer_returns_false(self):
        writer = RecordingWriter()
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, clock=clock)

        flushed = batcher.flush_if_needed(force=True)
        assert flushed is False
        assert writer.call_count == 0

    def test_max_size_one_flushes_each_submit(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=1, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        assert writer.call_count == 1
        batcher.submit("b")
        assert writer.call_count == 2
        assert writer.batches[0] == ["a"]
        assert writer.batches[1] == ["b"]

    def test_time_interval_exactly_reached(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=5.0)
        clock = ManualClock(start_time=100.0)
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("item")
        clock.advance(5.0)
        flushed = batcher.flush_if_needed(force=False)
        assert flushed is True
        assert writer.call_count == 1

    def test_buffer_size_property_thread_safe(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=1000, max_interval=60.0)
        batcher = MicroBatchBatcher(writer=writer, config=config)

        def submit_items(n, barrier):
            barrier.wait()
            for i in range(n):
                batcher.submit(i)

        num_threads = 5
        items_per_thread = 20
        barrier = threading.Barrier(num_threads)
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=submit_items, args=(items_per_thread, barrier))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert batcher.buffer_size == num_threads * items_per_thread


class TestRetryAndFailure:
    def test_retry_succeeds_on_second_attempt(self):
        writer = RecordingWriter()
        writer.set_first_n_calls_fail(1)
        config = MicroBatchConfig(
            max_size=2,
            max_interval=60.0,
            max_retries=3,
            retry_interval=0.1,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        batcher.submit("b")

        assert writer.call_count == 2
        assert batcher.buffer_size == 0

        success = batcher.success_batches
        assert len(success) == 1
        assert success[0].status == BatchStatus.SUCCESS
        assert success[0].attempts == 2
        assert clock.sleep_history == [0.1]

    def test_retry_succeeds_after_multiple_failures(self):
        writer = RecordingWriter()
        writer.set_first_n_calls_fail(2)
        config = MicroBatchConfig(
            max_size=2,
            max_interval=60.0,
            max_retries=5,
            retry_interval=0.5,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        batcher.submit("b")

        assert writer.call_count == 3
        success = batcher.success_batches
        assert len(success) == 1
        assert success[0].attempts == 3
        assert clock.sleep_history == [0.5, 0.5]

    def test_max_retries_exceeded_marks_failed(self):
        writer = RecordingWriter()
        writer.set_first_n_calls_fail(10)
        config = MicroBatchConfig(
            max_size=2,
            max_interval=60.0,
            max_retries=2,
            retry_interval=0.1,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        batcher.submit("b")

        assert writer.call_count == 3
        assert len(batcher.failed_batches) == 1
        assert len(batcher.success_batches) == 0

        failed = batcher.failed_batches[0]
        assert failed.status == BatchStatus.FAILED
        assert failed.attempts == 3
        assert failed.items == ["a", "b"]
        assert failed.last_error is not None
        assert isinstance(failed.last_error, TransientError)
        assert clock.sleep_history == [0.1, 0.1]

    def test_zero_retries_no_retry(self):
        writer = RecordingWriter()
        writer.set_first_n_calls_fail(5)
        config = MicroBatchConfig(
            max_size=1,
            max_interval=60.0,
            max_retries=0,
            retry_interval=1.0,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("x")

        assert writer.call_count == 1
        assert len(batcher.failed_batches) == 1
        assert batcher.failed_batches[0].attempts == 1
        assert clock.sleep_history == []

    def test_failed_batch_does_not_block_subsequent_batches(self):
        writer = RecordingWriter()
        writer.add_fail_call_index(1)
        writer.add_fail_call_index(2)
        config = MicroBatchConfig(
            max_size=2,
            max_interval=60.0,
            max_retries=1,
            retry_interval=0.0,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a1")
        batcher.submit("a2")
        assert len(batcher.failed_batches) == 1

        batcher.submit("b1")
        batcher.submit("b2")
        assert len(batcher.success_batches) == 1
        assert len(batcher.failed_batches) == 1

        assert batcher.success_batches[0].items == ["b1", "b2"]
        assert batcher.failed_batches[0].items == ["a1", "a2"]

    def test_writer_raises_exception_handled(self):
        class ExceptionRaisingWriter:
            def __init__(self, fail_count: int):
                self.fail_count = fail_count
                self.call_count = 0

            def write_batch(self, batch):
                self.call_count += 1
                if self.call_count <= self.fail_count:
                    raise RuntimeError("writer boom")
                return FlushResult.ok()

        writer = ExceptionRaisingWriter(fail_count=2)
        config = MicroBatchConfig(
            max_size=1,
            max_interval=60.0,
            max_retries=3,
            retry_interval=0.0,
        )
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("x")

        assert writer.call_count == 3
        assert len(batcher.success_batches) == 1
        assert batcher.success_batches[0].attempts == 3
        assert batcher.success_batches[0].last_error is None

    def test_writer_always_raises_exception(self):
        class AlwaysFailWriter:
            def write_batch(self, batch):
                raise RuntimeError("always boom")

        writer = AlwaysFailWriter()
        config = MicroBatchConfig(
            max_size=1,
            max_interval=60.0,
            max_retries=1,
            retry_interval=0.0,
        )
        batcher = MicroBatchBatcher(writer=writer, config=config)

        batcher.submit("x")

        assert len(batcher.failed_batches) == 1
        failed = batcher.failed_batches[0]
        assert failed.attempts == 2
        assert failed.last_error is not None
        assert isinstance(failed.last_error, RuntimeError)


class TestConcurrentSubmission:
    def test_concurrent_submit_all_collected(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=1000, max_interval=60.0)
        batcher = MicroBatchBatcher(writer=writer, config=config)

        num_threads = 10
        items_per_thread = 50
        barrier = threading.Barrier(num_threads)
        all_items: list[int] = []

        def submit_range(start: int):
            barrier.wait()
            for i in range(start, start + items_per_thread):
                batcher.submit(i)

        threads = []
        for t in range(num_threads):
            start = t * items_per_thread
            all_items.extend(range(start, start + items_per_thread))
            thread = threading.Thread(target=submit_range, args=(start,))
            threads.append(thread)
            thread.start()

        for t in threads:
            t.join()

        assert batcher.buffer_size == num_threads * items_per_thread
        assert writer.call_count == 0

        batcher.flush_all()
        assert writer.call_count == 1

        flushed_items: list[int] = []
        for batch in writer.batches:
            flushed_items.extend(batch)
        assert sorted(flushed_items) == sorted(all_items)

    def test_concurrent_submit_with_flushing(self):
        writer = RecordingWriter()
        writer.set_delay_before_response(0.01)
        config = MicroBatchConfig(max_size=10, max_interval=60.0)
        batcher = MicroBatchBatcher(writer=writer, config=config)

        submit_count = 100
        barrier = threading.Barrier(2)
        flushed_during: list[int] = []

        def fast_submitter():
            barrier.wait()
            for i in range(submit_count):
                batcher.submit(i)

        def flush_periodically():
            barrier.wait()
            for _ in range(20):
                batcher.flush_if_needed(force=True)
                flushed_during.append(batcher.buffer_size)
                time.sleep(0.002)

        t1 = threading.Thread(target=fast_submitter)
        t2 = threading.Thread(target=flush_periodically)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        batcher.flush_all()

        total_flushed = sum(len(b) for b in writer.batches)
        assert total_flushed == submit_count

        unique_items: list[int] = []
        for b in writer.batches:
            unique_items.extend(b)
        assert len(unique_items) == submit_count
        assert sorted(unique_items) == list(range(submit_count))

    def test_new_items_accumulate_in_next_batch_during_flush(self):
        call_started = threading.Event()
        proceed_with_flush = threading.Event()
        results: list[FlushResult] = []

        class TwoPhaseWriter:
            def __init__(self):
                self.call_count = 0
                self.batches: list[list] = []

            def write_batch(self, batch):
                self.call_count += 1
                self.batches.append(list(batch))
                if self.call_count == 1:
                    call_started.set()
                    proceed_with_flush.wait(timeout=5.0)
                result = FlushResult.ok()
                results.append(result)
                return result

        writer = TwoPhaseWriter()
        config = MicroBatchConfig(max_size=3, max_interval=60.0)
        batcher = MicroBatchBatcher(writer=writer, config=config)

        def submit_initial_batch():
            batcher.submit("a")
            batcher.submit("b")
            batcher.submit("c")

        flush_thread = threading.Thread(target=submit_initial_batch)
        flush_thread.start()

        call_started.wait(timeout=5.0)

        batcher.submit("d")
        batcher.submit("e")

        proceed_with_flush.set()
        flush_thread.join()

        batcher.submit("f")

        batcher.flush_all()

        assert writer.call_count >= 2
        first_batch = writer.batches[0]
        assert "a" in first_batch
        assert "b" in first_batch
        assert "c" in first_batch
        assert "d" not in first_batch

        all_items: list[str] = []
        for b in writer.batches:
            all_items.extend(b)
        assert sorted(all_items) == ["a", "b", "c", "d", "e", "f"]

    def test_concurrent_submit_and_scheduler(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(
            max_size=100,
            max_interval=0.05,
            scheduler_interval=0.01,
        )
        batcher = MicroBatchBatcher(writer=writer, config=config)

        batcher.start()

        num_threads = 5
        items_per_thread = 20
        total_items = num_threads * items_per_thread
        barrier = threading.Barrier(num_threads)

        def submit_items(start):
            barrier.wait()
            for i in range(items_per_thread):
                batcher.submit(f"{start}-{i}")

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=submit_items, args=(t,))
            threads.append(thread)
            thread.start()

        for t in threads:
            t.join()

        time.sleep(0.2)
        batcher.stop(flush_remaining=True)

        total_flushed = sum(len(b) for b in writer.batches)
        assert total_flushed == total_items
        assert batcher.buffer_size == 0


class TestLifecycleAndClosing:
    def test_close_flushes_remaining(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("orphan1")
        batcher.submit("orphan2")
        assert writer.call_count == 0

        batcher.close(flush_remaining=True)

        assert writer.call_count == 1
        assert writer.batches[0] == ["orphan1", "orphan2"]
        assert batcher.buffer_size == 0

    def test_close_without_flush(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=60.0)
        batcher = MicroBatchBatcher(writer=writer, config=config)

        batcher.submit("lost")
        batcher.close(flush_remaining=False)

        assert writer.call_count == 0
        assert batcher.buffer_size == 1

    def test_submit_after_close_raises(self):
        writer = RecordingWriter()
        batcher = MicroBatchBatcher(writer=writer)
        batcher.close()

        with pytest.raises(BufferClosedError):
            batcher.submit("after")

        with pytest.raises(BufferClosedError):
            batcher.submit_many(["a", "b"])

    def test_close_idempotent(self):
        writer = RecordingWriter()
        batcher = MicroBatchBatcher(writer=writer)
        batcher.close()
        batcher.close()

    def test_context_manager(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=100, max_interval=60.0)

        with MicroBatchBatcher(writer=writer, config=config) as batcher:
            batcher.submit("inside1")
            batcher.submit("inside2")
            assert batcher.is_closed is False

        assert batcher.is_closed is True
        assert writer.call_count == 1
        assert writer.batches[0] == ["inside1", "inside2"]

    def test_start_stop_scheduler(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(
            max_size=100,
            max_interval=0.05,
            scheduler_interval=0.01,
        )
        batcher = MicroBatchBatcher(writer=writer, config=config)

        batcher.start()
        batcher.start()

        batcher.submit("scheduled_item")

        time.sleep(0.2)

        assert writer.call_count == 1
        assert writer.batches[0] == ["scheduled_item"]

        batcher.stop()
        batcher.stop()

        assert batcher.buffer_size == 0


class TestHistorySnapshots:
    def test_success_batches_is_snapshot(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=1, max_interval=60.0)
        clock = ManualClock()
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        batcher.submit("a")
        snap1 = batcher.success_batches
        batcher.submit("b")
        snap2 = batcher.success_batches

        assert len(snap1) == 1
        assert len(snap2) == 2

    def test_failed_batches_is_snapshot(self):
        writer = RecordingWriter()
        writer.set_first_n_calls_fail(2)
        config = MicroBatchConfig(
            max_size=1,
            max_interval=60.0,
            max_retries=0,
            retry_interval=0.0,
        )
        batcher = MicroBatchBatcher(writer=writer, config=config)

        batcher.submit("fail1")
        snap1 = batcher.failed_batches
        batcher.submit("fail2")
        snap2 = batcher.failed_batches

        assert len(snap1) == 1
        assert len(snap2) == 2

    def test_batch_record_timestamps(self):
        writer = RecordingWriter()
        config = MicroBatchConfig(max_size=1, max_interval=60.0)
        clock = ManualClock(start_time=100.0)
        batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

        clock.advance(1.5)
        batcher.submit("x")

        record = batcher.success_batches[0]
        assert record.created_at == pytest.approx(101.5)
        assert record.flushed_at is not None
        assert record.flushed_at >= record.created_at
        assert record.batch_id == 1
