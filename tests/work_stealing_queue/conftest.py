import pytest

from solocoder_py.work_stealing_queue import WorkStealingDeque, WorkerPool


@pytest.fixture
def deque() -> WorkStealingDeque[int]:
    return WorkStealingDeque[int](max_capacity=100)


@pytest.fixture
def small_deque() -> WorkStealingDeque[int]:
    return WorkStealingDeque[int](max_capacity=3)


@pytest.fixture
def worker_pool() -> WorkerPool:
    return WorkerPool(num_workers=4, max_queue_capacity=100)


@pytest.fixture
def single_worker_pool() -> WorkerPool:
    return WorkerPool(num_workers=1, max_queue_capacity=100)
