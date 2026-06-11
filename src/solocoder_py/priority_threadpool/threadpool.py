from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from .clock import Clock, SystemClock
from .exceptions import TaskNotFoundError, ThreadPoolShutdownError
from .models import (
    Priority,
    TaskResult,
    TaskStatus,
    ThreadPoolConfig,
    ThreadPoolState,
    ThreadPoolStats,
    _TaskWrapper,
)


@dataclass
class _RunningTask:
    task: _TaskWrapper
    started_at: float
    completes_at: float


class PriorityThreadPool:
    def __init__(
        self,
        config: ThreadPoolConfig,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config
        self._clock: Clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._state = ThreadPoolState.RUNNING

        self._queues: Dict[Priority, Deque[_TaskWrapper]] = {
            Priority.HIGH: deque(),
            Priority.MEDIUM: deque(),
            Priority.LOW: deque(),
        }

        self._running: List[_RunningTask] = []
        self._total_submitted: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._last_aging_check: float = self._clock.now()

        self._pending_tasks: Dict[str, _TaskWrapper] = {}
        self._results: Dict[str, TaskResult] = {}
        self._completion_order: List[str] = []

    @property
    def state(self) -> ThreadPoolState:
        with self._lock:
            return self._state

    @property
    def config(self) -> ThreadPoolConfig:
        return self._config

    @property
    def completion_order(self) -> List[str]:
        with self._lock:
            return list(self._completion_order)

    @property
    def current_concurrency(self) -> int:
        with self._lock:
            return len(self._running)

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: Priority = Priority.MEDIUM,
        task_id: Optional[str] = None,
        duration: float = 0.0,
        **kwargs: Any,
    ) -> str:
        with self._lock:
            if self._state != ThreadPoolState.RUNNING:
                raise ThreadPoolShutdownError()

            task = _TaskWrapper.create(
                func=func,
                priority=priority,
                submitted_at=self._clock.now(),
                args=args,
                kwargs={**kwargs, "__duration": duration},
                task_id=task_id,
            )

            self._queues[priority].append(task)
            self._pending_tasks[task.task_id] = task
            self._total_submitted += 1

            return task.task_id

    def submit_many(
        self,
        tasks: List[Tuple[Callable[..., Any], Tuple, Dict, Priority]],
    ) -> List[str]:
        task_ids: List[str] = []
        for func, args, kwargs, priority in tasks:
            task_kwargs = dict(kwargs)
            duration = task_kwargs.pop("duration", 0.0)
            tid = self.submit(func, *args, priority=priority, duration=duration, **task_kwargs)
            task_ids.append(tid)
        return task_ids

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if self._state == ThreadPoolState.TERMINATED:
                return
            if self._state == ThreadPoolState.RUNNING:
                self._state = ThreadPoolState.SHUTTING_DOWN

            if not self._has_pending_work():
                self._state = ThreadPoolState.TERMINATED
                return

            if not wait:
                return

        is_manual = hasattr(self._clock, "advance")
        while True:
            with self._lock:
                self._advance_time(0)
                if self._state == ThreadPoolState.TERMINATED:
                    break
                if self._running:
                    min_completes = min(rt.completes_at for rt in self._running)
                    wait_time = max(0.0, min_completes - self._clock.now())
                else:
                    wait_time = 0.001
            if is_manual:
                with self._lock:
                    self._clock.advance(wait_time + 0.001)
            else:
                if wait_time > 0:
                    time.sleep(wait_time)

    def get_task_result(self, task_id: str) -> TaskResult:
        with self._lock:
            if task_id in self._results:
                return self._results[task_id]
            if task_id in self._pending_tasks:
                task = self._pending_tasks[task_id]
                running_task = next(
                    (rt for rt in self._running if rt.task.task_id == task_id),
                    None,
                )
                if running_task is not None:
                    return TaskResult(
                        task_id=task_id,
                        status=TaskStatus.RUNNING,
                        priority=task.priority,
                        submitted_at=task.submitted_at,
                        started_at=running_task.started_at,
                        original_priority=task.original_priority,
                        priority_boost_count=task.priority_boost_count,
                    )
                else:
                    return TaskResult(
                        task_id=task_id,
                        status=TaskStatus.PENDING,
                        priority=task.priority,
                        submitted_at=task.submitted_at,
                        original_priority=task.original_priority,
                        priority_boost_count=task.priority_boost_count,
                    )
            raise TaskNotFoundError(task_id)

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        is_manual = hasattr(self._clock, "advance")
        start = self._clock.now()
        while True:
            with self._lock:
                if task_id in self._results:
                    return self._results[task_id]
                if task_id not in self._pending_tasks:
                    raise TaskNotFoundError(task_id)
                if timeout is not None:
                    elapsed = self._clock.now() - start
                    if elapsed >= timeout:
                        task = self._pending_tasks[task_id]
                        running_task = next(
                            (rt for rt in self._running if rt.task.task_id == task_id),
                            None,
                        )
                        if running_task is not None:
                            return TaskResult(
                                task_id=task_id,
                                status=TaskStatus.RUNNING,
                                priority=task.priority,
                                submitted_at=task.submitted_at,
                                started_at=running_task.started_at,
                                original_priority=task.original_priority,
                                priority_boost_count=task.priority_boost_count,
                            )
                        else:
                            return TaskResult(
                                task_id=task_id,
                                status=TaskStatus.PENDING,
                                priority=task.priority,
                                submitted_at=task.submitted_at,
                                original_priority=task.original_priority,
                                priority_boost_count=task.priority_boost_count,
                            )
                self._advance_time(0)
                if self._running:
                    min_completes = min(rt.completes_at for rt in self._running)
                    wait_time = max(0.0, min_completes - self._clock.now())
                else:
                    wait_time = 0.001
            if is_manual:
                with self._lock:
                    self._clock.advance(wait_time + 0.001)
            else:
                if wait_time > 0:
                    time.sleep(wait_time)

    def run_until_complete(self) -> None:
        is_manual = hasattr(self._clock, "advance")
        while True:
            with self._lock:
                self._advance_time(0)
                if not self._has_pending_work():
                    break
                if self._running:
                    min_completes = min(rt.completes_at for rt in self._running)
                    wait_time = max(0.0, min_completes - self._clock.now())
                else:
                    wait_time = 0.001
            if is_manual:
                with self._lock:
                    self._clock.advance(wait_time + 0.001)
            else:
                if wait_time > 0:
                    time.sleep(wait_time)

    def tick(self) -> None:
        with self._lock:
            self._advance_time(0)

    def advance_time(self, seconds: float) -> None:
        with self._lock:
            if hasattr(self._clock, "advance"):
                self._clock.advance(seconds)
            self._advance_time(seconds)

    def get_stats(self) -> ThreadPoolStats:
        with self._lock:
            return ThreadPoolStats(
                state=self._state,
                max_concurrency=self._config.max_concurrency,
                current_concurrency=len(self._running),
                high_queue_size=len(self._queues[Priority.HIGH]),
                medium_queue_size=len(self._queues[Priority.MEDIUM]),
                low_queue_size=len(self._queues[Priority.LOW]),
                total_submitted=self._total_submitted,
                total_completed=self._total_completed,
                total_failed=self._total_failed,
            )

    def _has_pending_work(self) -> bool:
        return (
            len(self._queues[Priority.HIGH]) > 0
            or len(self._queues[Priority.MEDIUM]) > 0
            or len(self._queues[Priority.LOW]) > 0
            or len(self._running) > 0
        )

    def _try_launch_tasks(self) -> int:
        launched = 0
        while len(self._running) < self._config.max_concurrency:
            task = self._pop_next_task()
            if task is None:
                break
            duration = task.kwargs.pop("__duration", 0.0)
            started_at = self._clock.now()
            completes_at = started_at + duration
            self._running.append(_RunningTask(
                task=task,
                started_at=started_at,
                completes_at=completes_at,
            ))
            launched += 1
        return launched

    def _pop_next_task(self) -> Optional[_TaskWrapper]:
        for priority in (Priority.HIGH, Priority.MEDIUM, Priority.LOW):
            if self._queues[priority]:
                return self._queues[priority].popleft()
        return None

    def _advance_time(self, delta: float) -> None:
        now = self._clock.now()
        self._check_and_apply_aging()
        self._try_launch_tasks()

        still_running: List[_RunningTask] = []
        for rt in self._running:
            if now >= rt.completes_at:
                self._execute_and_complete(rt)
            else:
                still_running.append(rt)
        self._running = still_running

        self._try_launch_tasks()

        if (
            self._state == ThreadPoolState.SHUTTING_DOWN
            and not self._has_pending_work()
        ):
            self._state = ThreadPoolState.TERMINATED

    def _execute_and_complete(self, rt: _RunningTask) -> None:
        try:
            result = rt.task.func(*rt.task.args, **rt.task.kwargs)
            completed_at = self._clock.now()
            self._complete_task(
                rt.task,
                status=TaskStatus.SUCCESS,
                result=result,
                started_at=rt.started_at,
                completed_at=completed_at,
            )
        except Exception as e:
            completed_at = self._clock.now()
            self._complete_task(
                rt.task,
                status=TaskStatus.FAILED,
                exception=e,
                started_at=rt.started_at,
                completed_at=completed_at,
            )

    def _check_and_apply_aging(self) -> None:
        now = self._clock.now()
        if now - self._last_aging_check < self._config.aging_check_interval:
            return
        self._last_aging_check = now

        for current_priority in (Priority.MEDIUM, Priority.LOW):
            target_priority = Priority(current_priority - 1)
            queue = self._queues[current_priority]
            promoted: List[_TaskWrapper] = []
            remaining: Deque[_TaskWrapper] = deque()

            while queue:
                task = queue.popleft()
                wait_time = now - task.submitted_at
                if wait_time >= self._config.aging_threshold:
                    task.priority = target_priority
                    task.priority_boost_count += 1
                    promoted.append(task)
                else:
                    remaining.append(task)

            self._queues[current_priority] = remaining
            for task in promoted:
                self._insert_task_by_submit_time(self._queues[target_priority], task)

    def _complete_task(
        self,
        task: _TaskWrapper,
        status: TaskStatus,
        started_at: float,
        completed_at: float,
        result: Any = None,
        exception: Optional[BaseException] = None,
    ) -> None:
        if status == TaskStatus.SUCCESS:
            self._total_completed += 1
        else:
            self._total_failed += 1

        task_result = TaskResult(
            task_id=task.task_id,
            status=status,
            priority=task.priority,
            result=result,
            exception=exception,
            submitted_at=task.submitted_at,
            started_at=started_at,
            completed_at=completed_at,
            original_priority=task.original_priority,
            priority_boost_count=task.priority_boost_count,
        )
        self._results[task.task_id] = task_result
        self._completion_order.append(task.task_id)
        self._pending_tasks.pop(task.task_id, None)

    @staticmethod
    def _insert_task_by_submit_time(queue: Deque[_TaskWrapper], task: _TaskWrapper) -> None:
        inserted = False
        for i, existing in enumerate(queue):
            if task.submitted_at < existing.submitted_at:
                queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            queue.append(task)
