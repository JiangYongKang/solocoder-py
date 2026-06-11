from __future__ import annotations

import random
import threading
import time
import uuid
from typing import Any, Callable

from .deque import WorkStealingDeque
from .exceptions import InvalidWorkerError, QueueFullError, WorkStealingQueueError
from .models import Task, TaskStatus


class WorkerPool:
    """
    工作窃取线程池。

    管理一组工作线程，每个线程拥有自己的本地任务队列。
    当某线程的本地队列为空时，它会尝试从其他线程的队列中窃取任务。

    关键特性：
    - 本地 LIFO：每个线程从自己队列的底端弹出任务（后进先出，提高缓存局部性）
    - 窃取 FIFO：从其他线程队列的顶端窃取任务（先进先出，避免与本地操作冲突）
    - 随机窃取：空闲线程随机选择一个受害者进行窃取
    """

    def __init__(
        self,
        num_workers: int = 4,
        max_queue_capacity: int = 1024,
        steal_retry_delay: float = 0.01,
    ) -> None:
        if num_workers <= 0:
            raise ValueError("num_workers must be positive")
        if max_queue_capacity <= 0:
            raise ValueError("max_queue_capacity must be positive")
        if steal_retry_delay < 0:
            raise ValueError("steal_retry_delay must be non-negative")

        self._num_workers = num_workers
        self._max_queue_capacity = max_queue_capacity
        self._steal_retry_delay = steal_retry_delay

        self._queues: list[WorkStealingDeque[Task]] = [
            WorkStealingDeque(max_capacity=max_queue_capacity)
            for _ in range(num_workers)
        ]
        self._workers: list[threading.Thread] = []
        self._worker_ids: list[str] = [
            f"worker-{i}" for i in range(num_workers)
        ]

        self._running = False
        self._lock = threading.Lock()
        self._submitted_count = 0
        self._completed_count = 0
        self._failed_count = 0
        self._stolen_count = 0
        self._round_robin_index = 0

    @property
    def num_workers(self) -> int:
        return self._num_workers

    @property
    def max_queue_capacity(self) -> int:
        return self._max_queue_capacity

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def submitted_count(self) -> int:
        return self._submitted_count

    @property
    def completed_count(self) -> int:
        return self._completed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    @property
    def stolen_count(self) -> int:
        return self._stolen_count

    def get_queue_size(self, worker_id: int) -> int:
        if worker_id < 0 or worker_id >= self._num_workers:
            raise InvalidWorkerError(f"Invalid worker id: {worker_id}")
        return self._queues[worker_id].size()

    def get_total_queued(self) -> int:
        return sum(q.size() for q in self._queues)

    def submit(self, body: Any, worker_id: int | None = None) -> Task:
        """
        提交任务到指定工作线程的队列。

        如果未指定 worker_id，则使用轮询策略分配。

        Args:
            body: 任务内容
            worker_id: 目标工作线程索引，None 表示自动分配

        Returns:
            创建的 Task 对象

        Raises:
            InvalidWorkerError: worker_id 无效
            QueueFullError: 目标队列已满
        """
        if worker_id is None:
            with self._lock:
                worker_id = self._round_robin_index % self._num_workers
                self._round_robin_index += 1
                self._submitted_count += 1
        else:
            if worker_id < 0 or worker_id >= self._num_workers:
                raise InvalidWorkerError(f"Invalid worker id: {worker_id}")
            with self._lock:
                self._submitted_count += 1

        task = Task(
            id=str(uuid.uuid4()),
            body=body,
            owner_worker_id=self._worker_ids[worker_id],
        )

        queue = self._queues[worker_id]
        queue.push_bottom(task)
        return task

    def start(self, task_handler: Callable[[Task], None]) -> None:
        """
        启动所有工作线程。

        Args:
            task_handler: 处理任务的回调函数
        """
        if self._running:
            return

        self._running = True
        for i in range(self._num_workers):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(i, task_handler),
                daemon=True,
                name=self._worker_ids[i],
            )
            self._workers.append(thread)
            thread.start()

    def stop(self) -> None:
        """停止所有工作线程。"""
        self._running = False
        for thread in self._workers:
            thread.join(timeout=5.0)
        self._workers.clear()

    def _worker_loop(self, worker_index: int, task_handler: Callable[[Task], None]) -> None:
        """工作线程主循环。"""
        local_queue = self._queues[worker_index]

        while self._running:
            task = local_queue.pop_bottom()
            if task is not None:
                self._execute_task(task, task_handler)
                continue

            stolen_task = self._try_steal(worker_index)
            if stolen_task is not None:
                self._execute_task(stolen_task, task_handler)
                continue

            time.sleep(self._steal_retry_delay)

    def _try_steal(self, thief_index: int) -> Task | None:
        """
        尝试从其他工作线程窃取任务。

        随机选择受害者，从其队列顶端窃取一个任务。

        Args:
            thief_index: 窃取者的线程索引

        Returns:
            窃取到的任务，如果没偷到则返回 None
        """
        if self._num_workers <= 1:
            return None

        candidates = list(range(self._num_workers))
        candidates.remove(thief_index)
        random.shuffle(candidates)

        for victim_index in candidates:
            victim_queue = self._queues[victim_index]
            task = victim_queue.steal()
            if task is not None:
                task.mark_stolen(self._worker_ids[thief_index])
                with self._lock:
                    self._stolen_count += 1
                return task

        return None

    def _execute_task(self, task: Task, task_handler: Callable[[Task], None]) -> None:
        """执行任务并更新状态。"""
        try:
            task.mark_running()
            task_handler(task)
            task.mark_completed()
        except Exception as e:
            task.mark_failed(error_message=str(e))
        finally:
            with self._lock:
                if task.status == TaskStatus.FAILED:
                    self._failed_count += 1
                else:
                    self._completed_count += 1
