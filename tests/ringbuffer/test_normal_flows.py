import threading
import time

import pytest

from solocoder_py.ringbuffer import RingBuffer, WriteMode


class TestBasicReadWrite:
    def test_write_then_read_content_consistent(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.write(1) == 1
        assert rb_no_overwrite.write(2) == 1
        assert rb_no_overwrite.write(3) == 1

        assert rb_no_overwrite.available_to_read() == 3
        assert rb_no_overwrite.available_to_write() == 2

        assert rb_no_overwrite.read() == 1
        assert rb_no_overwrite.read() == 2
        assert rb_no_overwrite.read() == 3

        assert rb_no_overwrite.available_to_read() == 0
        assert rb_no_overwrite.available_to_write() == 5

    def test_read_write_pointer_wrap_around(self, rb_small: RingBuffer[int]):
        assert rb_small.write(1) == 1
        assert rb_small.write(2) == 1
        assert rb_small.read() == 1
        assert rb_small.read() == 2

        assert rb_small.write(3) == 1
        assert rb_small.write(4) == 1
        assert rb_small.write(5) == 1

        assert rb_small.available_to_read() == 3
        assert rb_small.available_to_write() == 0

        assert rb_small.read() == 3
        assert rb_small.read() == 4
        assert rb_small.read() == 5

        assert rb_small.available_to_read() == 0

    def test_available_to_read_and_write(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.available_to_read() == 0
        assert rb_no_overwrite.available_to_write() == 5

        rb_no_overwrite.write(1)
        assert rb_no_overwrite.available_to_read() == 1
        assert rb_no_overwrite.available_to_write() == 4

        rb_no_overwrite.write_batch([2, 3, 4])
        assert rb_no_overwrite.available_to_read() == 4
        assert rb_no_overwrite.available_to_write() == 1

        rb_no_overwrite.read()
        assert rb_no_overwrite.available_to_read() == 3
        assert rb_no_overwrite.available_to_write() == 2

    def test_write_returns_count(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.write(1) == 1
        assert rb_no_overwrite.write(2) == 1

        result = rb_no_overwrite.write_batch([3, 4, 5, 6, 7, 8])
        assert result == 3

        assert rb_no_overwrite.available_to_read() == 5
        assert rb_no_overwrite.available_to_write() == 0


class TestBatchOperations:
    def test_write_batch_partial_when_not_enough_space(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])
        result = rb_no_overwrite.write_batch([4, 5, 6, 7, 8])
        assert result == 2

        assert rb_no_overwrite.available_to_read() == 5
        data = rb_no_overwrite.read_batch(5)
        assert data == [1, 2, 3, 4, 5]

    def test_read_batch_returns_available_when_less_than_max(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])
        result = rb_no_overwrite.read_batch(10)
        assert result == [1, 2, 3]
        assert len(result) == 3

    def test_read_batch_wraps_around(self, rb_small: RingBuffer[int]):
        rb_small.write_batch([1, 2])
        assert rb_small.read_batch(2) == [1, 2]

        rb_small.write_batch([3, 4, 5])
        assert rb_small.read_batch(3) == [3, 4, 5]

        rb_small.write_batch([6, 7, 8])
        assert rb_small.read_batch(3) == [6, 7, 8]

    def test_batch_efficiency_consecutive(self, rb_no_overwrite: RingBuffer[int]):
        data = list(range(100))
        written = 0
        for i in range(0, 100, 5):
            chunk = data[i:i + 5]
            written += rb_no_overwrite.write_batch(chunk)
            if rb_no_overwrite.available_to_write() == 0:
                break

        assert written == 5
        assert rb_no_overwrite.read_batch(5) == [0, 1, 2, 3, 4]


class TestOverwriteMode:
    def test_overwrite_when_full(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_overwrite.available_to_read() == 5

        result = rb_overwrite.write(6)
        assert result == 1
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [2, 3, 4, 5, 6]

    def test_overwrite_multiple_items(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])

        result = rb_overwrite.write_batch([6, 7, 8])
        assert result == 3
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [4, 5, 6, 7, 8]

    def test_overwrite_more_than_capacity(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])

        result = rb_overwrite.write_batch([6, 7, 8, 9, 10, 11, 12])
        assert result == 5
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [8, 9, 10, 11, 12]

    def test_overwrite_read_ptr_advances_correctly(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_overwrite.read() == 1

        rb_overwrite.write_batch([6, 7])
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [3, 4, 5, 6, 7]


class TestNoOverwriteModeFull:
    def test_write_returns_zero_when_full(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_no_overwrite.available_to_write() == 0

        result = rb_no_overwrite.write(6)
        assert result == 0
        assert rb_no_overwrite.available_to_read() == 5

        data = rb_no_overwrite.read_batch(5)
        assert data == [1, 2, 3, 4, 5]

    def test_write_batch_returns_zero_when_full(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        result = rb_no_overwrite.write_batch([6, 7, 8])
        assert result == 0

    def test_write_works_after_read_frees_space(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_no_overwrite.write(6) == 0

        assert rb_no_overwrite.read() == 1
        assert rb_no_overwrite.write(6) == 1

        data = rb_no_overwrite.read_batch(5)
        assert data == [2, 3, 4, 5, 6]


class TestBlockingOperations:
    def test_blocking_read_wakes_up_on_write(self):
        rb = RingBuffer[int](capacity=5)
        result = []

        def reader():
            data = rb.read(blocking=True)
            result.append(data)

        t = threading.Thread(target=reader)
        t.start()
        time.sleep(0.05)

        assert len(result) == 0
        rb.write(42)
        t.join(timeout=1.0)

        assert len(result) == 1
        assert result[0] == 42

    def test_blocking_write_wakes_up_on_read(self):
        rb = RingBuffer[int](capacity=2)
        rb.write(1)
        rb.write(2)

        result = []

        def writer():
            n = rb.write(3, blocking=True)
            result.append(n)

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.05)

        assert len(result) == 0
        assert rb.read() == 1
        t.join(timeout=1.0)

        assert len(result) == 1
        assert result[0] == 1
        assert rb.available_to_read() == 2
        assert rb.read() == 2
        assert rb.read() == 3

    def test_blocking_read_batch_wakes_up(self):
        rb = RingBuffer[int](capacity=5)
        result = []

        def reader():
            data = rb.read_batch(3, blocking=True)
            result.extend(data)

        t = threading.Thread(target=reader)
        t.start()
        time.sleep(0.05)

        rb.write_batch([1, 2, 3])

        t.join(timeout=1.0)
        assert result == [1, 2, 3]

    def test_blocking_write_batch_wakes_up(self):
        rb = RingBuffer[int](capacity=2)
        rb.write_batch([1, 2])

        result = []

        def writer():
            n = rb.write_batch([3, 4], blocking=True)
            result.append(n)

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.05)

        assert rb.read_batch(2) == [1, 2]
        t.join(timeout=1.0)

        assert result == [2]
        assert rb.available_to_read() == 2
        assert rb.read_batch(2) == [3, 4]

    def test_multiple_blocking_readers(self):
        rb = RingBuffer[int](capacity=10)
        results = [[], [], []]

        def reader(idx):
            while True:
                data = rb.read(blocking=True, timeout=0.2)
                if data is None:
                    break
                results[idx].append(data)

        threads = []
        for i in range(3):
            t = threading.Thread(target=reader, args=(i,))
            t.start()
            threads.append(t)

        time.sleep(0.05)
        rb.write_batch([1, 2, 3, 4, 5, 6])

        for t in threads:
            t.join(timeout=1.0)

        all_results = sorted(results[0] + results[1] + results[2])
        assert all_results == [1, 2, 3, 4, 5, 6]
