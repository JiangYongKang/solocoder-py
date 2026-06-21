import threading
import time

import pytest

from solocoder_py.ringbuffer import RingBuffer, WriteMode


class TestCapacityOne:
    def test_capacity_one_write_read(self):
        rb = RingBuffer[int](capacity=1)

        assert rb.write(1) == 1
        assert rb.available_to_read() == 1
        assert rb.available_to_write() == 0

        assert rb.read() == 1
        assert rb.available_to_read() == 0
        assert rb.available_to_write() == 1

        assert rb.write(2) == 1
        assert rb.read() == 2

    def test_capacity_one_no_overwrite_full(self):
        rb = RingBuffer[int](capacity=1, write_mode=WriteMode.NO_OVERWRITE)

        assert rb.write(1) == 1
        assert rb.write(2) == 0
        assert rb.read() == 1

    def test_capacity_one_overwrite(self):
        rb = RingBuffer[int](capacity=1, write_mode=WriteMode.OVERWRITE)

        assert rb.write(1) == 1
        assert rb.write(2) == 1
        assert rb.write(3) == 1

        assert rb.available_to_read() == 1
        assert rb.read() == 3

    def test_capacity_one_batch_operations(self):
        rb = RingBuffer[int](capacity=1)

        assert rb.write_batch([1, 2, 3]) == 1
        assert rb.read_batch(5) == [1]

        assert rb.write_batch([4]) == 1
        assert rb.read_batch(1) == [4]


class TestWriteExactlyCapacity:
    def test_write_exactly_capacity(self, rb_no_overwrite: RingBuffer[int]):
        data = [1, 2, 3, 4, 5]
        result = rb_no_overwrite.write_batch(data)
        assert result == 5
        assert rb_no_overwrite.available_to_read() == 5
        assert rb_no_overwrite.available_to_write() == 0

        read_data = rb_no_overwrite.read_batch(5)
        assert read_data == data
        assert rb_no_overwrite.available_to_read() == 0

    def test_read_exactly_capacity(self, rb_no_overwrite: RingBuffer[int]):
        data = list(range(5))
        rb_no_overwrite.write_batch(data)

        result = rb_no_overwrite.read_batch(5)
        assert result == data
        assert len(result) == 5

    def test_alternating_full_capacity(self, rb_no_overwrite: RingBuffer[int]):
        for i in range(3):
            data = list(range(i * 5, (i + 1) * 5))
            assert rb_no_overwrite.write_batch(data) == 5
            assert rb_no_overwrite.read_batch(5) == data


class TestAlternatingReadWrite:
    def test_alternating_keep_buffer_not_full_not_empty(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])

        for i in range(10):
            assert rb_no_overwrite.read() == i + 1
            assert rb_no_overwrite.write(i + 4) == 1
            assert 2 <= rb_no_overwrite.available_to_read() <= 3

        assert rb_no_overwrite.available_to_read() == 3
        remaining = rb_no_overwrite.read_batch(10)
        assert remaining == [11, 12, 13]

    def test_read_write_alternate_wrap_around(self, rb_small: RingBuffer[int]):
        sequence = []
        for i in range(20):
            if rb_small.available_to_write() > 0:
                rb_small.write(i)
            if rb_small.available_to_read() > 0 and i % 2 == 1:
                sequence.append(rb_small.read())

        assert len(sequence) > 0
        assert sequence == sorted(sequence)


class TestBlockingTimeout:
    def test_blocking_read_timeout_on_empty(self):
        rb = RingBuffer[int](capacity=5)

        start = time.monotonic()
        result = rb.read(blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert result is None
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_read_batch_timeout_on_empty(self):
        rb = RingBuffer[int](capacity=5)

        start = time.monotonic()
        result = rb.read_batch(3, blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert result == []
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_write_timeout_on_full(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write(1)
        rb.write(2)

        start = time.monotonic()
        result = rb.write(3, blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert result == 0
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_write_batch_timeout_on_full(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])

        start = time.monotonic()
        result = rb.write_batch([3, 4], blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert result == 0
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_read_no_timeout_returns_when_data_arrives(self):
        rb = RingBuffer[int](capacity=5)
        result = []

        def writer():
            time.sleep(0.05)
            rb.write(99)

        t = threading.Thread(target=writer)
        t.start()

        start = time.monotonic()
        data = rb.read(blocking=True, timeout=1.0)
        elapsed = time.monotonic() - start

        t.join()
        assert data == 99
        assert 0.03 <= elapsed <= 0.2

    def test_blocking_write_no_timeout_returns_when_space_freed(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write(1)
        rb.write(2)

        def reader():
            time.sleep(0.05)
            rb.read()

        t = threading.Thread(target=reader)
        t.start()

        start = time.monotonic()
        n = rb.write(3, blocking=True, timeout=1.0)
        elapsed = time.monotonic() - start

        t.join()
        assert n == 1
        assert 0.03 <= elapsed <= 0.2


class TestZeroAndEmptyOperations:
    def test_write_empty_batch(self, rb_no_overwrite: RingBuffer[int]):
        result = rb_no_overwrite.write_batch([])
        assert result == 0
        assert rb_no_overwrite.available_to_read() == 0

    def test_read_batch_zero_max_count(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write(1)
        result = rb_no_overwrite.read_batch(0)
        assert result == []
        assert rb_no_overwrite.available_to_read() == 1

    def test_read_batch_negative_max_count(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write(1)
        result = rb_no_overwrite.read_batch(-1)
        assert result == []
        assert rb_no_overwrite.available_to_read() == 1


class TestClearOperation:
    def test_clear_empty_buffer(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.clear()
        assert rb_no_overwrite.available_to_read() == 0
        assert rb_no_overwrite.available_to_write() == 5

    def test_clear_full_buffer(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        rb_no_overwrite.clear()

        assert rb_no_overwrite.available_to_read() == 0
        assert rb_no_overwrite.available_to_write() == 5
        assert rb_no_overwrite.read() is None

    def test_clear_then_operations(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])
        rb_no_overwrite.clear()

        assert rb_no_overwrite.write_batch([4, 5]) == 2
        assert rb_no_overwrite.read_batch(2) == [4, 5]
