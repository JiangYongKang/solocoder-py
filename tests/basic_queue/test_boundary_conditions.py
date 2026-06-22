import pytest

from solocoder_py.basic_queue import BasicQueue, QueueEmptyException


class TestEmptyQueueExceptions:
    def test_dequeue_empty_raises_exception(self, queue: BasicQueue[int]) -> None:
        with pytest.raises(QueueEmptyException) as exc_info:
            queue.dequeue()
        assert "empty" in str(exc_info.value).lower()

    def test_peek_empty_raises_exception(self, queue: BasicQueue[int]) -> None:
        with pytest.raises(QueueEmptyException) as exc_info:
            queue.peek()
        assert "empty" in str(exc_info.value).lower()

    def test_exception_type_is_correct(self, queue: BasicQueue[int]) -> None:
        with pytest.raises(Exception) as exc_info:
            queue.dequeue()
        assert isinstance(exc_info.value, QueueEmptyException)

    def test_dequeue_after_all_elements_removed_raises(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.dequeue()
        with pytest.raises(QueueEmptyException):
            queue.dequeue()

    def test_peek_after_all_elements_removed_raises(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.dequeue()
        with pytest.raises(QueueEmptyException):
            queue.peek()


class TestLargeNumberOfElements:
    def test_1000_elements_enqueue_then_dequeue(self, queue: BasicQueue[int]) -> None:
        n = 1000
        for i in range(n):
            queue.enqueue(i)

        assert queue.size() == n
        assert queue.peek() == 0

        for i in range(n):
            assert queue.dequeue() == i

        assert queue.is_empty()
        assert queue.size() == 0

    def test_10000_elements_fifo_correctness(self, queue: BasicQueue[int]) -> None:
        n = 10000
        for i in range(n):
            queue.enqueue(i * 2)

        assert queue.size() == n

        for i in range(n):
            assert queue.dequeue() == i * 2

        assert queue.is_empty()


class TestAlternatingEnqueueDequeue:
    def test_alternate_enqueue_dequeue_single(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        assert queue.dequeue() == 1
        queue.enqueue(2)
        assert queue.dequeue() == 2
        queue.enqueue(3)
        assert queue.dequeue() == 3
        assert queue.is_empty()

    def test_alternate_partial_dequeue_then_enqueue(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.enqueue(3)
        assert queue.dequeue() == 1
        queue.enqueue(4)
        assert queue.dequeue() == 2
        queue.enqueue(5)
        assert queue.dequeue() == 3
        assert queue.dequeue() == 4
        assert queue.dequeue() == 5
        assert queue.is_empty()

    def test_alternating_sequence_preserves_order(self, queue: BasicQueue[int]) -> None:
        expected: list[int] = []
        counter = 0

        for batch in range(5):
            for _ in range(3):
                queue.enqueue(counter)
                expected.append(counter)
                counter += 1
            for _ in range(2):
                assert queue.dequeue() == expected.pop(0)

        while not queue.is_empty():
            assert queue.dequeue() == expected.pop(0)

        assert len(expected) == 0

    def test_enqueue_dequeue_enqueue_dequeue_100_times(self, queue: BasicQueue[int]) -> None:
        for i in range(100):
            queue.enqueue(i)
            assert queue.dequeue() == i
            assert queue.is_empty()

        assert queue.size() == 0


class TestMixedOperationsEdgeCases:
    def test_duplicate_values_stored_independently(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(5)
        queue.enqueue(5)
        queue.enqueue(5)

        assert queue.size() == 3
        assert queue.dequeue() == 5
        assert queue.dequeue() == 5
        assert queue.dequeue() == 5
        assert queue.is_empty()

    def test_none_value_as_element(self) -> None:
        q: BasicQueue[object] = BasicQueue[object]()
        q.enqueue(None)
        q.enqueue("not none")

        assert q.peek() is None
        assert q.dequeue() is None
        assert q.dequeue() == "not none"
        assert q.is_empty()

    def test_mixed_types_in_generic_object_queue(self) -> None:
        q: BasicQueue[object] = BasicQueue[object]()
        q.enqueue(1)
        q.enqueue("string")
        q.enqueue(3.14)
        q.enqueue(True)

        assert q.dequeue() == 1
        assert q.dequeue() == "string"
        assert q.dequeue() == 3.14
        assert q.dequeue() is True
