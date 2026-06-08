from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.backpressure import (
    BackpressureError,
    BackpressureStrategy,
    BoundedQueue,
    BoundedQueueState,
    DequeueTimeoutError,
    EnqueueResult,
    RejectedError,
)


class TestBoundedQueueInit:
    def test_valid_creation(self):
        q = BoundedQueue(capacity=10)
        assert q.capacity == 10
        assert q.size == 0
        assert q.remaining_capacity == 10
        assert q.strategy == BackpressureStrategy.BLOCK

    def test_invalid_capacity_zero(self):
        with pytest.raises(ValueError):
            BoundedQueue(capacity=0)

    def test_invalid_capacity_negative(self):
        with pytest.raises(ValueError):
            BoundedQueue(capacity=-1)

    def test_invalid_watermark_ratios(self):
        with pytest.raises(ValueError):
            BoundedQueue(capacity=5, high_watermark_ratio=0.5, low_watermark_ratio=0.8)

    def test_custom_strategy(self):
        q = BoundedQueue(capacity=5, strategy=BackpressureStrategy.DROP)
        assert q.strategy == BackpressureStrategy.DROP


class TestBasicEnqueueDequeue:
    def test_simple_enqueue_dequeue_fifo(self, queue_block: BoundedQueue):
        queue_block.enqueue(1)
        queue_block.enqueue(2)
        queue_block.enqueue(3)
        assert queue_block.size == 3
        assert queue_block.dequeue() == 1
        assert queue_block.dequeue() == 2
        assert queue_block.dequeue() == 3
        assert queue_block.size == 0

    def test_enqueue_result_success(self, queue_block: BoundedQueue):
        result = queue_block.enqueue("item")
        assert isinstance(result, EnqueueResult)
        assert result.success is True
        assert result.dropped is False

    def test_len_bool(self, queue_block: BoundedQueue):
        assert len(queue_block) == 0
        assert bool(queue_block) is False
        queue_block.enqueue("x")
        assert len(queue_block) == 1
        assert bool(queue_block) is True


class TestDropStrategy:
    def test_drop_when_full(self, queue_drop: BoundedQueue):
        for i in range(5):
            queue_drop.enqueue(i)
        assert queue_drop.size == 5

        result = queue_drop.enqueue(99)
        assert result.success is False
        assert result.dropped is True
        assert result.element == 99
        assert queue_drop.size == 5
        assert queue_drop.dropped_count == 1

    def test_drop_does_not_alter_queue(self, queue_drop: BoundedQueue):
        for i in range(5):
            queue_drop.enqueue(i)
        queue_drop.enqueue(99)
        for i in range(5):
            assert queue_drop.dequeue() == i

    def test_drop_multiple_drops_counted(self, queue_drop: BoundedQueue):
        for i in range(5):
            queue_drop.enqueue(i)
        queue_drop.enqueue("a")
        queue_drop.enqueue("b")
        queue_drop.enqueue("c")
        assert queue_drop.dropped_count == 3


class TestRejectStrategy:
    def test_reject_when_full(self, queue_reject: BoundedQueue):
        for i in range(5):
            queue_reject.enqueue(i)

        with pytest.raises(RejectedError) as exc_info:
            queue_reject.enqueue(99)
        assert exc_info.value.element == 99
        assert queue_reject.rejected_count == 1
        assert queue_reject.size == 5

    def test_reject_error_is_backpressure_error(self, queue_reject: BoundedQueue):
        for i in range(5):
            queue_reject.enqueue(i)
        with pytest.raises(BackpressureError):
            queue_reject.enqueue(99)

    def test_reject_count(self, queue_reject: BoundedQueue):
        for i in range(5):
            queue_reject.enqueue(i)
        for _ in range(3):
            with pytest.raises(RejectedError):
                queue_reject.enqueue("x")
        assert queue_reject.rejected_count == 3


class TestBlockStrategy:
    def test_producer_consumer_coordination(self, queue_block: BoundedQueue):
        results = []
        producer_done = threading.Event()

        def producer():
            for i in range(10):
                queue_block.enqueue(i)
            producer_done.set()

        def consumer():
            while not (producer_done.is_set() and queue_block.size == 0):
                try:
                    item = queue_block.dequeue(timeout=0.1)
                    results.append(item)
                except DequeueTimeoutError:
                    pass

        t_prod = threading.Thread(target=producer)
        t_cons = threading.Thread(target=consumer)
        t_prod.start()
        t_cons.start()
        t_prod.join()
        t_cons.join()
        assert results == list(range(10))

    def test_block_enqueue_with_timeout_success(self):
        q = BoundedQueue(capacity=2, strategy=BackpressureStrategy.BLOCK)
        q.enqueue("a")
        q.enqueue("b")

        start = time.monotonic()
        result = q.enqueue("c", timeout=0.05)
        elapsed = time.monotonic() - start

        assert result.success is False
        assert result.dropped is True
        assert 0.04 <= elapsed <= 0.2

    def test_block_enqueue_no_timeout_waits(self):
        q = BoundedQueue(capacity=1, strategy=BackpressureStrategy.BLOCK)
        q.enqueue("first")

        unblocked = threading.Event()

        def slow_consumer():
            time.sleep(0.05)
            q.dequeue()
            unblocked.set()

        t = threading.Thread(target=slow_consumer)
        t.start()

        start = time.monotonic()
        result = q.enqueue("second")
        elapsed = time.monotonic() - start

        t.join()
        assert result.success is True
        assert elapsed >= 0.03


class TestDequeueBlocking:
    def test_dequeue_empty_blocking(self, queue_block: BoundedQueue):
        queue_block.enqueue("only")
        assert queue_block.dequeue(block=False) == "only"
        assert queue_block.dequeue(block=False) is None

    def test_dequeue_timeout_raises(self, queue_block: BoundedQueue):
        start = time.monotonic()
        with pytest.raises(DequeueTimeoutError):
            queue_block.dequeue(timeout=0.05)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.03

    def test_dequeue_blocks_until_available(self, queue_block: BoundedQueue):
        def delayed_enqueue():
            time.sleep(0.05)
            queue_block.enqueue("arrived")

        t = threading.Thread(target=delayed_enqueue)
        t.start()

        start = time.monotonic()
        item = queue_block.dequeue()
        elapsed = time.monotonic() - start

        t.join()
        assert item == "arrived"
        assert elapsed >= 0.03


class TestRuntimeStrategySwitch:
    def test_switch_strategy(self, queue_block: BoundedQueue):
        for i in range(5):
            queue_block.enqueue(i)
        assert queue_block.strategy == BackpressureStrategy.BLOCK

        queue_block.set_strategy(BackpressureStrategy.DROP)
        assert queue_block.strategy == BackpressureStrategy.DROP
        result = queue_block.enqueue(99)
        assert result.success is False
        assert result.dropped is True

        queue_block.set_strategy(BackpressureStrategy.REJECT)
        with pytest.raises(RejectedError):
            queue_block.enqueue(99)
        assert queue_block.rejected_count == 1

    def test_enqueue_override_strategy(self, queue_reject: BoundedQueue):
        for i in range(5):
            queue_reject.enqueue(i)

        result = queue_reject.enqueue(
                99, strategy=BackpressureStrategy.DROP
            )
        assert result.success is False
        assert result.dropped is True
        assert queue_reject.strategy == BackpressureStrategy.REJECT


class TestWatermarkCallbacks:
    def test_high_watermark_triggered(self, queue_with_watermarks: BoundedQueue):
        high_events = []
        queue_with_watermarks.register_high_watermark_callback(
            lambda s: high_events.append(s)
        )

        for i in range(7):
            queue_with_watermarks.enqueue(i)

        assert len(high_events) == 0
        assert queue_with_watermarks.is_high_watermark is False

        queue_with_watermarks.enqueue(7)
        assert queue_with_watermarks.is_high_watermark is True
        assert len(high_events) == 1
        state = high_events[0]
        assert isinstance(state, BoundedQueueState)
        assert state.is_high_watermark is True
        assert state.size == 8

    def test_high_watermark_not_retriggered_while_above(self, queue_with_watermarks: BoundedQueue):
        events = []
        queue_with_watermarks.register_high_watermark_callback(lambda s: events.append(s))
        for i in range(10):
            queue_with_watermarks.enqueue(i)
        assert len(events) == 1

    def test_low_watermark_triggered_on_drain(self, queue_with_watermarks: BoundedQueue):
        high_events = []
        low_events = []
        queue_with_watermarks.register_high_watermark_callback(lambda s: high_events.append(s))
        queue_with_watermarks.register_low_watermark_callback(lambda s: low_events.append(s))

        for i in range(10):
            queue_with_watermarks.enqueue(i)
        assert len(high_events) == 1

        for _ in range(7):
            queue_with_watermarks.dequeue()
        assert len(low_events) == 0

        queue_with_watermarks.dequeue()
        assert len(low_events) == 1
        assert queue_with_watermarks.is_high_watermark is False

        state = low_events[0]
        assert state.is_high_watermark is False
        assert state.size == 2

    def test_clear_resets_watermark_state(self, queue_with_watermarks: BoundedQueue):
        events = []
        queue_with_watermarks.register_high_watermark_callback(lambda s: events.append(s))
        queue_with_watermarks.register_low_watermark_callback(lambda s: events.append("low"))

        for i in range(10):
            queue_with_watermarks.enqueue(i)
        queue_with_watermarks.clear()

        assert queue_with_watermarks.is_high_watermark is False
        assert queue_with_watermarks.size == 0

    def test_multiple_callbacks_all_invoked(self, queue_with_watermarks: BoundedQueue):
        count1 = []
        count2 = []
        queue_with_watermarks.register_high_watermark_callback(lambda s: count1.append(1))
        queue_with_watermarks.register_high_watermark_callback(lambda s: count2.append(1))

        for i in range(10):
            queue_with_watermarks.enqueue(i)

        assert len(count1) == 1
        assert len(count2) == 1


class TestStateQuery:
    def test_get_state(self, queue_drop: BoundedQueue):
        queue_drop.enqueue("a")
        queue_drop.enqueue("b")
        state = queue_drop.get_state()
        assert isinstance(state, BoundedQueueState)
        assert state.capacity == 5
        assert state.size == 2
        assert state.remaining_capacity == 3
        assert state.strategy == BackpressureStrategy.DROP
        assert state.is_high_watermark is False
        assert state.dropped_count == 0
        assert state.rejected_count == 0

    def test_state_immutable(self, queue_reject: BoundedQueue):
        for i in range(5):
            queue_reject.enqueue(i)
        for _ in range(2):
            with pytest.raises(RejectedError):
                queue_reject.enqueue("x")
        state = queue_reject.get_state()
        assert state.rejected_count == 2
        assert state.size == 5
        assert state.remaining_capacity == 0


class TestConcurrency:
    def test_concurrent_producers(self):
        q = BoundedQueue(capacity=100, strategy=BackpressureStrategy.BLOCK)
        num_producers = 5
        per_producer = 20

        def produce(q):
            for i in range(per_producer):
                q.enqueue(i)

        threads = [threading.Thread(target=produce, args=(q,)) for _ in range(num_producers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert q.size == num_producers * per_producer

    def test_concurrent_producers_consumers(self):
        q = BoundedQueue(capacity=50, strategy=BackpressureStrategy.BLOCK)
        produced = []
        consumed = []
        num_items = 200
        num_producers = 4
        num_consumers = 4
        lock = threading.Lock()

        def producer(pid: int):
            for i in range(num_items // num_producers):
                item = (pid, i)
                q.enqueue(item)
                with lock:
                    produced.append(item)

        def consumer():
            while True:
                try:
                    item = q.dequeue(timeout=0.1)
                    with lock:
                        consumed.append(item)
                except DequeueTimeoutError:
                    return

        prod_threads = [threading.Thread(target=producer, args=(i,)) for i in range(num_producers)]
        cons_threads = [threading.Thread(target=consumer) for _ in range(num_consumers)]

        for t in prod_threads:
            t.start()
        for t in cons_threads:
            t.start()
        for t in prod_threads:
            t.join()
        for t in cons_threads:
            t.join()

        assert len(consumed) == num_items
        assert sorted(produced) == sorted(consumed)

    def test_concurrent_drop_strategy(self):
        capacity = 10
        q = BoundedQueue(capacity=capacity, strategy=BackpressureStrategy.DROP)
        num_threads = 10
        per_thread = 20
        total = num_threads * per_thread

        def producer():
            for i in range(per_thread):
                q.enqueue(i)

        threads = [threading.Thread(target=producer) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        state = q.get_state()
        assert state.size <= capacity
        assert state.dropped_count + state.size == total


class TestClear:
    def test_clear_empties_queue(self, queue_block: BoundedQueue):
        for i in range(5):
            queue_block.enqueue(i)
        queue_block.clear()
        assert queue_block.size == 0
        assert queue_block.remaining_capacity == 5

    def test_clear_resets_counters(self, queue_drop: BoundedQueue):
        for i in range(5):
            queue_drop.enqueue(i)
        queue_drop.enqueue("extra")
        assert queue_drop.dropped_count == 1
        queue_drop.clear()
        assert queue_drop.dropped_count == 0
        assert queue_drop.rejected_count == 0


class TestEdgeCases:
    def test_watermark_at_boundary_zero(self):
        q = BoundedQueue(
            capacity=10,
            strategy=BackpressureStrategy.BLOCK,
            high_watermark_ratio=0.0,
            low_watermark_ratio=0.0,
        )
        assert q.is_high_watermark is False

    def test_watermark_at_boundary_one(self):
        q = BoundedQueue(
            capacity=10,
            strategy=BackpressureStrategy.BLOCK,
            high_watermark_ratio=1.0,
            low_watermark_ratio=1.0,
        )
        high_called = []
        q.register_high_watermark_callback(lambda s: high_called.append(1))
        for i in range(10):
            q.enqueue(i)
        assert len(high_called) == 1

    def test_dequeue_from_empty_non_blocking(self, queue_block: BoundedQueue):
        assert queue_block.dequeue(block=False) is None

    def test_callback_cleared(self, queue_with_watermarks: BoundedQueue):
        events = []
        queue_with_watermarks.register_high_watermark_callback(lambda s: events.append(s))
        queue_with_watermarks.clear_callbacks()
        for i in range(10):
            queue_with_watermarks.enqueue(i)
        assert len(events) == 0
