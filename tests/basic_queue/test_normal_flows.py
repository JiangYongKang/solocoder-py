import pytest

from solocoder_py.basic_queue import BasicQueue


class TestEnqueueDequeueOrder:
    def test_single_element_enqueue_dequeue(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(42)
        assert queue.dequeue() == 42

    def test_multiple_elements_fifo_order(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.enqueue(3)

        assert queue.dequeue() == 1
        assert queue.dequeue() == 2
        assert queue.dequeue() == 3

    def test_string_elements_preserved(self) -> None:
        q: BasicQueue[str] = BasicQueue[str]()
        q.enqueue("hello")
        q.enqueue("world")
        assert q.dequeue() == "hello"
        assert q.dequeue() == "world"


class TestPeekOperation:
    def test_peek_returns_front_element(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(10)
        queue.enqueue(20)
        assert queue.peek() == 10

    def test_peek_does_not_remove_element(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(100)
        assert queue.peek() == 100
        assert queue.peek() == 100
        assert queue.size() == 1

    def test_peek_after_some_dequeues(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.enqueue(3)
        queue.dequeue()
        assert queue.peek() == 2


class TestIsEmpty:
    def test_new_queue_is_empty(self, queue: BasicQueue[int]) -> None:
        assert queue.is_empty() is True

    def test_queue_not_empty_after_enqueue(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        assert queue.is_empty() is False

    def test_queue_empty_after_all_dequeued(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.dequeue()
        queue.dequeue()
        assert queue.is_empty() is True


class TestSize:
    def test_new_queue_size_zero(self, queue: BasicQueue[int]) -> None:
        assert queue.size() == 0

    def test_size_increments_on_enqueue(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        assert queue.size() == 1
        queue.enqueue(2)
        assert queue.size() == 2

    def test_size_decrements_on_dequeue(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.enqueue(3)
        queue.dequeue()
        assert queue.size() == 2
        queue.dequeue()
        assert queue.size() == 1

    def test_size_accurate_with_mixed_operations(self, queue: BasicQueue[int]) -> None:
        queue.enqueue(1)
        queue.enqueue(2)
        queue.dequeue()
        queue.enqueue(3)
        queue.dequeue()
        queue.dequeue()
        assert queue.size() == 0
