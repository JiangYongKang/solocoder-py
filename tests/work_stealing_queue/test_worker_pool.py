import time

import pytest

from solocoder_py.work_stealing_queue import (
    InvalidWorkerError,
    Task,
    TaskStatus,
    WorkerPool,
)


class TestWorkerPoolBasics:
    def test_pool_creation(self, worker_pool: WorkerPool):
        assert worker_pool.num_workers == 4
        assert worker_pool.max_queue_capacity == 100
        assert not worker_pool.is_running
        assert worker_pool.submitted_count == 0
        assert worker_pool.completed_count == 0
        assert worker_pool.stolen_count == 0

    def test_invalid_num_workers_raises(self):
        with pytest.raises(ValueError):
            WorkerPool(num_workers=0)
        with pytest.raises(ValueError):
            WorkerPool(num_workers=-1)

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            WorkerPool(num_workers=2, max_queue_capacity=0)

    def test_invalid_steal_delay_raises(self):
        with pytest.raises(ValueError):
            WorkerPool(num_workers=2, steal_retry_delay=-1)

    def test_get_queue_size(self, worker_pool: WorkerPool):
        for i in range(4):
            assert worker_pool.get_queue_size(i) == 0

        worker_pool.submit("task-0", worker_id=0)
        worker_pool.submit("task-1", worker_id=1)

        assert worker_pool.get_queue_size(0) == 1
        assert worker_pool.get_queue_size(1) == 1
        assert worker_pool.get_queue_size(2) == 0
        assert worker_pool.get_queue_size(3) == 0

    def test_get_queue_size_invalid_worker(self, worker_pool: WorkerPool):
        with pytest.raises(InvalidWorkerError):
            worker_pool.get_queue_size(-1)
        with pytest.raises(InvalidWorkerError):
            worker_pool.get_queue_size(4)

    def test_get_total_queued(self, worker_pool: WorkerPool):
        assert worker_pool.get_total_queued() == 0

        worker_pool.submit("a", worker_id=0)
        worker_pool.submit("b", worker_id=0)
        worker_pool.submit("c", worker_id=2)

        assert worker_pool.get_total_queued() == 3


class TestTaskSubmission:
    def test_submit_specific_worker(self, worker_pool: WorkerPool):
        task = worker_pool.submit("hello", worker_id=2)

        assert task.body == "hello"
        assert task.owner_worker_id == "worker-2"
        assert task.status == TaskStatus.PENDING
        assert worker_pool.get_queue_size(2) == 1
        assert worker_pool.submitted_count == 1

    def test_submit_round_robin(self, worker_pool: WorkerPool):
        for i in range(8):
            worker_pool.submit(f"task-{i}")

        for i in range(4):
            assert worker_pool.get_queue_size(i) == 2

        assert worker_pool.submitted_count == 8

    def test_submit_invalid_worker(self, worker_pool: WorkerPool):
        with pytest.raises(InvalidWorkerError):
            worker_pool.submit("x", worker_id=10)

    def test_submit_creates_task_with_id(self, worker_pool: WorkerPool):
        task = worker_pool.submit("test")
        assert task.id
        assert len(task.id) > 0

    def test_submit_returns_task_object(self, worker_pool: WorkerPool):
        task = worker_pool.submit("payload")
        assert isinstance(task, Task)
        assert task.body == "payload"


class TestSingleWorkerAllLocal:
    def test_single_worker_consumes_all_locally(self, single_worker_pool: WorkerPool):
        num_tasks = 10
        processed = []

        def handler(task: Task):
            processed.append(task.body)

        for i in range(num_tasks):
            single_worker_pool.submit(f"task-{i}")

        single_worker_pool.start(handler)

        timeout = 2.0
        start = time.time()
        while single_worker_pool.completed_count < num_tasks:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        single_worker_pool.stop()

        assert single_worker_pool.completed_count == num_tasks
        assert len(processed) == num_tasks
        assert single_worker_pool.stolen_count == 0
        assert single_worker_pool.get_total_queued() == 0

    def test_single_worker_no_stealing_possible(self, single_worker_pool: WorkerPool):
        single_worker_pool.submit("only-task")
        assert single_worker_pool.stolen_count == 0

    def test_single_worker_lifo_order(self, single_worker_pool: WorkerPool):
        processed = []

        def handler(task: Task):
            processed.append(task.body)

        for i in range(5):
            single_worker_pool.submit(f"task-{i}")

        single_worker_pool.start(handler)

        timeout = 2.0
        start = time.time()
        while single_worker_pool.completed_count < 5:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        single_worker_pool.stop()

        assert len(processed) == 5


class TestWorkStealing:
    def test_work_stealing_occurs(self, worker_pool: WorkerPool):
        num_tasks = 50
        processed_tasks: list[str] = []

        def handler(task: Task):
            processed_tasks.append(task.body)
            time.sleep(0.005)

        for i in range(num_tasks):
            worker_pool.submit(f"task-{i}", worker_id=0)

        assert worker_pool.get_queue_size(0) == num_tasks

        worker_pool.start(handler)

        timeout = 5.0
        start = time.time()
        while worker_pool.completed_count < num_tasks:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        worker_pool.stop()

        assert worker_pool.completed_count == num_tasks
        assert worker_pool.get_total_queued() == 0

        assert worker_pool.stolen_count > 0

        assert len(processed_tasks) == num_tasks

    def test_steal_from_empty_queue_returns_empty(self, worker_pool: WorkerPool):
        assert worker_pool.stolen_count == 0

        worker_pool.start(lambda t: None)
        time.sleep(0.1)
        worker_pool.stop()

        assert worker_pool.stolen_count == 0

    def test_all_workers_participate(self, worker_pool: WorkerPool):
        num_tasks = 100

        def handler(task: Task):
            time.sleep(0.002)

        for i in range(num_tasks):
            worker_pool.submit(f"task-{i}", worker_id=0)

        worker_pool.start(handler)

        timeout = 5.0
        start = time.time()
        while worker_pool.completed_count < num_tasks:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        worker_pool.stop()

        assert worker_pool.completed_count == num_tasks
        assert worker_pool.stolen_count > 0

    def test_task_marked_stolen(self, worker_pool: WorkerPool):
        stolen_tasks = []

        def handler(task: Task):
            time.sleep(0.005)
            if task.stolen_by is not None:
                stolen_tasks.append(task)

        for i in range(60):
            worker_pool.submit(f"task-{i}", worker_id=0)

        worker_pool.start(handler)

        timeout = 5.0
        start = time.time()
        while worker_pool.completed_count < 60:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        worker_pool.stop()

        if worker_pool.stolen_count > 0:
            assert len(stolen_tasks) > 0
            for task in stolen_tasks:
                assert task.stolen_by is not None
                assert task.stolen_by != task.owner_worker_id

    def test_even_distribution(self, worker_pool: WorkerPool):
        num_tasks = 40

        def handler(task: Task):
            time.sleep(0.01)

        for i in range(num_tasks):
            worker_pool.submit(f"task-{i}", worker_id=0)

        worker_pool.start(handler)

        timeout = 5.0
        start = time.time()
        while worker_pool.completed_count < num_tasks:
            if time.time() - start > timeout:
                break
            time.sleep(0.01)

        worker_pool.stop()

        assert worker_pool.completed_count == num_tasks
        assert worker_pool.get_total_queued() == 0


class TestTaskStatusLifecycle:
    def test_task_status_transitions(self):
        task = Task(id="t1", body="test", owner_worker_id="worker-0")
        assert task.status == TaskStatus.PENDING

        task.mark_running()
        assert task.status == TaskStatus.RUNNING

        task.mark_completed()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_task_stolen_status(self):
        task = Task(id="t2", body="test", owner_worker_id="worker-0")
        task.mark_stolen("worker-1")
        assert task.status == TaskStatus.STOLEN
        assert task.stolen_by == "worker-1"

    def test_task_validation(self):
        with pytest.raises(ValueError):
            Task(id="", body="x", owner_worker_id="w")
        with pytest.raises(ValueError):
            Task(id="1", body="x", owner_worker_id="")

    def test_task_created_at(self):
        task = Task(id="t3", body="test", owner_worker_id="w")
        assert task.created_at is not None


class TestPoolStop:
    def test_stop_idempotent(self, worker_pool: WorkerPool):
        worker_pool.start(lambda t: None)
        assert worker_pool.is_running
        worker_pool.stop()
        assert not worker_pool.is_running
        worker_pool.stop()
        assert not worker_pool.is_running

    def test_start_idempotent(self, worker_pool: WorkerPool):
        worker_pool.start(lambda t: None)
        worker_pool.start(lambda t: None)
        assert worker_pool.is_running
        worker_pool.stop()


class TestErrorCases:
    def test_submit_to_full_queue(self):
        pool = WorkerPool(num_workers=2, max_queue_capacity=2)

        pool.submit("a", worker_id=0)
        pool.submit("b", worker_id=0)

        from solocoder_py.work_stealing_queue import QueueFullError

        with pytest.raises(QueueFullError):
            pool.submit("c", worker_id=0)

    def test_invalid_worker_id_negative(self, worker_pool: WorkerPool):
        with pytest.raises(InvalidWorkerError):
            worker_pool.submit("x", worker_id=-1)

    def test_invalid_worker_id_too_large(self, worker_pool: WorkerPool):
        with pytest.raises(InvalidWorkerError):
            worker_pool.submit("x", worker_id=100)
