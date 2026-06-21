import pytest

from solocoder_py.ringbuffer import (
    RingBuffer,
    WriteMode,
    InvalidCapacityError,
    RingBufferError,
    TimeoutError,
)


class TestInvalidCapacity:
    def test_capacity_zero_raises(self):
        with pytest.raises(InvalidCapacityError) as excinfo:
            RingBuffer[int](capacity=0)
        assert "positive integer" in str(excinfo.value)

    def test_capacity_negative_raises(self):
        with pytest.raises(InvalidCapacityError) as excinfo:
            RingBuffer[int](capacity=-1)
        assert "positive integer" in str(excinfo.value)

    def test_capacity_negative_large_raises(self):
        with pytest.raises(InvalidCapacityError):
            RingBuffer[int](capacity=-100)

    def test_invalid_capacity_is_subclass_of_ring_buffer_error(self):
        assert issubclass(InvalidCapacityError, RingBufferError)


class TestReadEmptyBufferNonBlocking:
    def test_read_empty_returns_none(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.available_to_read() == 0
        result = rb_no_overwrite.read(raise_timeout=False)
        assert result is None

    def test_read_batch_empty_returns_empty_list(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.available_to_read() == 0
        result = rb_no_overwrite.read_batch(5, raise_timeout=False)
        assert result == []
        assert isinstance(result, list)

    def test_read_empty_after_consuming_all(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write(1)
        assert rb_no_overwrite.read() == 1
        assert rb_no_overwrite.read(raise_timeout=False) is None
        assert rb_no_overwrite.read_batch(1, raise_timeout=False) == []

    def test_multiple_reads_on_empty(self, rb_no_overwrite: RingBuffer[int]):
        for _ in range(10):
            assert rb_no_overwrite.read(raise_timeout=False) is None
            assert rb_no_overwrite.read_batch(1, raise_timeout=False) == []


class TestWriteFullBufferNoOverwrite:
    def test_write_full_returns_zero(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_no_overwrite.available_to_write() == 0

        result = rb_no_overwrite.write(6, raise_timeout=False)
        assert result == 0
        assert rb_no_overwrite.available_to_read() == 5

    def test_write_batch_full_returns_zero(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        result = rb_no_overwrite.write_batch([6, 7, 8], raise_timeout=False)
        assert result == 0

        data = rb_no_overwrite.read_batch(5)
        assert data == [1, 2, 3, 4, 5]

    def test_write_partial_when_some_space(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4])
        assert rb_no_overwrite.available_to_write() == 1

        result = rb_no_overwrite.write_batch([5, 6, 7])
        assert result == 1

        assert rb_no_overwrite.available_to_read() == 5
        data = rb_no_overwrite.read_batch(5)
        assert data == [1, 2, 3, 4, 5]

    def test_write_zero_items_on_full(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        for _ in range(10):
            assert rb_no_overwrite.write(99, raise_timeout=False) == 0


class TestOverwriteReadPointerAdvance:
    def test_overwrite_single_item_read_ptr_advances(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_overwrite._read_ptr == 0

        rb_overwrite.write(6)
        assert rb_overwrite._read_ptr == 1
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [2, 3, 4, 5, 6]

    def test_overwrite_multiple_items_read_ptr_advances(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_overwrite._read_ptr == 0

        rb_overwrite.write_batch([6, 7, 8])
        assert rb_overwrite._read_ptr == 3
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [4, 5, 6, 7, 8]

    def test_overwrite_full_capacity_read_ptr_wraps(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])

        rb_overwrite.write_batch([6, 7, 8, 9, 10])
        assert rb_overwrite._read_ptr == 0
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [6, 7, 8, 9, 10]

    def test_overwrite_more_than_capacity(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])

        result = rb_overwrite.write_batch([6, 7, 8, 9, 10, 11, 12])
        assert result == 5
        assert rb_overwrite._read_ptr == 0
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [8, 9, 10, 11, 12]

    def test_overwrite_after_partial_read(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3, 4, 5])
        assert rb_overwrite.read() == 1
        assert rb_overwrite._read_ptr == 1

        rb_overwrite.write_batch([6, 7, 8])
        assert rb_overwrite._read_ptr == 3
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [4, 5, 6, 7, 8]

    def test_overwrite_with_wrap_around_read_ptr(self):
        rb = RingBuffer[int](capacity=4, write_mode=WriteMode.OVERWRITE)
        rb.write_batch([1, 2])
        assert rb.read_batch(2) == [1, 2]
        assert rb._read_ptr == 2
        assert rb._write_ptr == 2

        rb.write_batch([3, 4, 5, 6, 7])
        assert rb._read_ptr == 2
        assert rb.available_to_read() == 4

        data = rb.read_batch(4)
        assert data == [4, 5, 6, 7]


class TestBatchOperationsLimits:
    def test_read_batch_does_not_exceed_available(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])
        assert rb_no_overwrite.available_to_read() == 3

        result = rb_no_overwrite.read_batch(100)
        assert len(result) == 3
        assert result == [1, 2, 3]

    def test_read_batch_exactly_available(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        result = rb_no_overwrite.read_batch(5)
        assert len(result) == 5
        assert result == [1, 2, 3, 4, 5]

    def test_read_batch_less_than_available(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3, 4, 5])
        result = rb_no_overwrite.read_batch(2)
        assert len(result) == 2
        assert result == [1, 2]
        assert rb_no_overwrite.available_to_read() == 3

    def test_write_batch_does_not_exceed_available_space(self, rb_no_overwrite: RingBuffer[int]):
        rb_no_overwrite.write_batch([1, 2, 3])
        assert rb_no_overwrite.available_to_write() == 2

        result = rb_no_overwrite.write_batch([4, 5, 6, 7, 8])
        assert result == 2
        assert rb_no_overwrite.available_to_read() == 5

        data = rb_no_overwrite.read_batch(5)
        assert data == [1, 2, 3, 4, 5]

    def test_write_batch_overwrite_does_not_exceed_capacity(self, rb_overwrite: RingBuffer[int]):
        rb_overwrite.write_batch([1, 2, 3])
        result = rb_overwrite.write_batch([4, 5, 6, 7, 8, 9, 10, 11, 12])
        assert result == 5
        assert rb_overwrite.available_to_read() == 5

        data = rb_overwrite.read_batch(5)
        assert data == [8, 9, 10, 11, 12]

    def test_multiple_batch_operations_preserve_order(self, rb_no_overwrite: RingBuffer[int]):
        total_data = list(range(20))
        written = 0
        read_data = []

        for i in range(0, 20, 3):
            chunk = total_data[i:i + 3]
            n = rb_no_overwrite.write_batch(chunk)
            written += n

            if rb_no_overwrite.available_to_read() >= 3:
                read_data.extend(rb_no_overwrite.read_batch(3))

        while rb_no_overwrite.available_to_read() > 0:
            read_data.extend(rb_no_overwrite.read_batch(10))

        assert len(read_data) == written
        assert read_data == total_data[:written]


class TestProperties:
    def test_capacity_property(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.capacity == 5

        rb1 = RingBuffer[int](capacity=100)
        assert rb1.capacity == 100

    def test_write_mode_property(self):
        rb1 = RingBuffer[int](capacity=5, write_mode=WriteMode.OVERWRITE)
        assert rb1.write_mode == WriteMode.OVERWRITE

        rb2 = RingBuffer[int](capacity=5, write_mode=WriteMode.NO_OVERWRITE)
        assert rb2.write_mode == WriteMode.NO_OVERWRITE

        rb3 = RingBuffer[int](capacity=5)
        assert rb3.write_mode == WriteMode.NO_OVERWRITE


class TestClearWithBlockedOperations:
    def test_clear_unblocks_blocked_writers(self):
        import threading
        import time

        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write(1)
        rb.write(2)

        write_result = []

        def writer():
            n = rb.write(3, blocking=True, timeout=1.0, raise_timeout=False)
            write_result.append(n)

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.05)

        rb.clear()
        t.join(timeout=1.0)

        assert len(write_result) == 1
        assert write_result[0] == 1
        assert rb.available_to_read() == 1
        assert rb.read() == 3


class TestTimeoutErrorRaise:
    def test_blocking_read_timeout_raises_default(self, rb_no_overwrite: RingBuffer[int]):
        import time

        start = time.monotonic()
        with pytest.raises(TimeoutError) as excinfo:
            rb_no_overwrite.read(blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert "timed out" in str(excinfo.value)
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_read_batch_timeout_raises_default(self, rb_no_overwrite: RingBuffer[int]):
        import time

        start = time.monotonic()
        with pytest.raises(TimeoutError) as excinfo:
            rb_no_overwrite.read_batch(3, blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert "timed out" in str(excinfo.value)
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_read_timeout_no_raise_returns_none(self, rb_no_overwrite: RingBuffer[int]):
        result = rb_no_overwrite.read(blocking=True, timeout=0.05, raise_timeout=False)
        assert result is None

    def test_blocking_write_timeout_raises_default(self):
        import time

        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])

        start = time.monotonic()
        with pytest.raises(TimeoutError) as excinfo:
            rb.write(3, blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert "timed out" in str(excinfo.value)
        assert 0.08 <= elapsed <= 0.15

    def test_blocking_write_batch_timeout_raises_default(self):
        import time

        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])

        start = time.monotonic()
        with pytest.raises(TimeoutError) as excinfo:
            rb.write_batch([3, 4], blocking=True, timeout=0.1)
        elapsed = time.monotonic() - start

        assert "timed out" in str(excinfo.value)
        assert 0.08 <= elapsed <= 0.15

    def test_nonblocking_read_empty_raises_default(self, rb_no_overwrite: RingBuffer[int]):
        with pytest.raises(TimeoutError) as excinfo:
            rb_no_overwrite.read()
        assert "empty" in str(excinfo.value)

    def test_nonblocking_read_batch_empty_raises_default(self, rb_no_overwrite: RingBuffer[int]):
        with pytest.raises(TimeoutError) as excinfo:
            rb_no_overwrite.read_batch(3)
        assert "empty" in str(excinfo.value)

    def test_nonblocking_write_full_raises_default(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])

        with pytest.raises(TimeoutError) as excinfo:
            rb.write(3)
        assert "full" in str(excinfo.value)

    def test_nonblocking_write_batch_full_raises_default(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])

        with pytest.raises(TimeoutError) as excinfo:
            rb.write_batch([3, 4])
        assert "full" in str(excinfo.value)

    def test_nonblocking_read_empty_no_raise(self, rb_no_overwrite: RingBuffer[int]):
        assert rb_no_overwrite.read(raise_timeout=False) is None
        assert rb_no_overwrite.read_batch(1, raise_timeout=False) == []

    def test_nonblocking_write_full_no_raise(self):
        rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2])
        assert rb.write(3, raise_timeout=False) == 0
        assert rb.write_batch([3, 4], raise_timeout=False) == 0

    def test_blocking_write_partial_success_no_raise(self):
        import threading
        import time

        rb = RingBuffer[int](capacity=3, write_mode=WriteMode.NO_OVERWRITE)
        rb.write_batch([1, 2, 3])

        result = []
        exc_raised = []

        def writer():
            try:
                n = rb.write_batch([4, 5, 6], blocking=True, timeout=0.15)
                result.append(n)
            except TimeoutError as e:
                exc_raised.append(e)

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.05)

        rb.read()
        t.join(timeout=1.0)

        assert len(result) == 1
        assert result[0] == 1
        assert len(exc_raised) == 0

    def test_timeout_error_is_ring_buffer_error(self):
        assert issubclass(TimeoutError, RingBufferError)

    def test_read_timeout_raises_isinstance_check(self, rb_no_overwrite: RingBuffer[int]):
        with pytest.raises(RingBufferError):
            rb_no_overwrite.read(blocking=True, timeout=0.05)

    def test_write_timeout_raises_isinstance_check(self):
        rb = RingBuffer[int](capacity=1, write_mode=WriteMode.NO_OVERWRITE)
        rb.write(1)
        with pytest.raises(RingBufferError):
            rb.write(2, blocking=True, timeout=0.05)

