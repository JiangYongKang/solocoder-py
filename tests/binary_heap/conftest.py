import pytest

from solocoder_py.binary_heap import BinaryHeap


@pytest.fixture
def empty_heap() -> BinaryHeap:
    return BinaryHeap()


@pytest.fixture
def small_heap() -> BinaryHeap:
    heap = BinaryHeap()
    heap.insert("task_c", priority=3)
    heap.insert("task_a", priority=1)
    heap.insert("task_b", priority=2)
    return heap
