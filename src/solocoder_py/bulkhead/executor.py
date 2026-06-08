from __future__ import annotations

import threading
from collections import deque
from contextlib import contextmanager
from typing import Any, Callable, Deque, Dict, Iterator, Optional, Union
from uuid import uuid4

from .clock import Clock, SystemClock
from .exceptions import (
    BulkheadFullError,
    BulkheadQueueTimeoutError,
    GroupAlreadyExistsError,
    GroupNotFoundError,
)
from .models import (
    FullStrategy,
    GroupConfig,
    GroupStats,
    TaskResult,
    TaskStatus,
    _AcquireWaiter,
    _TaskWrapper,
)

_QueueEntry = Union[_TaskWrapper, _AcquireWaiter]


class _GroupState:
    def __init__(self, config: GroupConfig) -> None:
        self.config = config
        self.current_concurrency: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.queue: Deque[_QueueEntry] = deque()
        self.condition = threading.Condition()

    def get_stats(self) -> GroupStats:
        return GroupStats(
            name=self.config.name,
            max_concurrency=self.config.max_concurrency,
            current_concurrency=self.current_concurrency,
            queue_size=len(self.queue),
            success_count=self.success_count,
            failure_count=self.failure_count,
            full_strategy=self.config.full_strategy,
            queue_timeout=self.config.queue_timeout,
            max_queue_size=self.config.max_queue_size,
        )


class BulkheadExecutor:
    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._clock: Clock = clock or SystemClock()
        self._groups: Dict[str, _GroupState] = {}
        self._lock: threading.RLock = threading.RLock()

    def create_group(self, config: GroupConfig) -> None:
        with self._lock:
            if config.name in self._groups:
                raise GroupAlreadyExistsError(config.name)
            self._groups[config.name] = _GroupState(config)

    def remove_group(self, group_name: str) -> None:
        with self._lock:
            if group_name not in self._groups:
                raise GroupNotFoundError(group_name)
            del self._groups[group_name]

    def has_group(self, group_name: str) -> bool:
        with self._lock:
            return group_name in self._groups

    def update_group_config(self, config: GroupConfig) -> None:
        with self._lock:
            if config.name not in self._groups:
                raise GroupNotFoundError(config.name)
            self._groups[config.name].config = config

    def get_group_stats(self, group_name: str) -> GroupStats:
        with self._lock:
            if group_name not in self._groups:
                raise GroupNotFoundError(group_name)
            return self._groups[group_name].get_stats()

    def get_all_group_stats(self) -> Dict[str, GroupStats]:
        with self._lock:
            return {name: state.get_stats() for name, state in self._groups.items()}

    def submit(
        self,
        group_name: str,
        func: Callable[..., Any],
        *args: Any,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> TaskResult:
        with self._lock:
            if group_name not in self._groups:
                raise GroupNotFoundError(group_name)

        if task_id is None:
            task_id = uuid4().hex

        task = _TaskWrapper(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            submitted_at=self._clock.now(),
        )

        return self._execute_task(group_name, task)

    def _execute_task(self, group_name: str, task: _TaskWrapper) -> TaskResult:
        state = self._get_group_state(group_name)
        acquired = False
        queue_start: Optional[float] = None
        rejected_result: Optional[TaskResult] = None

        with state.condition:
            if state.current_concurrency >= state.config.max_concurrency:
                if state.config.full_strategy == FullStrategy.REJECT:
                    return TaskResult(
                        task_id=task.task_id,
                        group_name=group_name,
                        status=TaskStatus.REJECTED,
                        exception=BulkheadFullError(task.task_id, group_name),
                    )
                else:
                    if (
                        state.config.max_queue_size > 0
                        and len(state.queue) >= state.config.max_queue_size
                    ):
                        return TaskResult(
                            task_id=task.task_id,
                            group_name=group_name,
                            status=TaskStatus.REJECTED,
                            exception=BulkheadFullError(
                                task.task_id,
                                group_name,
                                f"Bulkhead group '{group_name}' queue is full, "
                                f"task '{task.task_id}' rejected",
                            ),
                        )

                    queue_start = self._clock.now()
                    deadline: Optional[float] = None
                    if state.config.queue_timeout > 0:
                        deadline = task.submitted_at + state.config.queue_timeout

                    state.queue.append(task)

                    while True:
                        if state.current_concurrency < state.config.max_concurrency:
                            if task in state.queue:
                                state.queue.remove(task)
                            break

                        wait_timeout: Optional[float] = None
                        if deadline is not None:
                            wait_timeout = deadline - self._clock.now()
                            if wait_timeout <= 0:
                                if task in state.queue:
                                    state.queue.remove(task)
                                queue_wait = self._clock.now() - queue_start
                                rejected_result = TaskResult(
                                    task_id=task.task_id,
                                    group_name=group_name,
                                    status=TaskStatus.QUEUE_TIMEOUT,
                                    exception=BulkheadQueueTimeoutError(
                                        task.task_id, group_name
                                    ),
                                    queue_wait_time=queue_wait,
                                )
                                break

                        state.condition.wait(timeout=wait_timeout)

                        if (
                            deadline is not None
                            and self._clock.now() >= deadline
                            and rejected_result is None
                        ):
                            if task in state.queue:
                                state.queue.remove(task)
                            queue_wait = self._clock.now() - queue_start
                            rejected_result = TaskResult(
                                task_id=task.task_id,
                                group_name=group_name,
                                status=TaskStatus.QUEUE_TIMEOUT,
                                exception=BulkheadQueueTimeoutError(
                                    task.task_id, group_name
                                ),
                                queue_wait_time=queue_wait,
                            )
                            break

                    if rejected_result is not None:
                        return rejected_result

            state.current_concurrency += 1
            acquired = True

        try:
            if queue_start is not None:
                queue_wait = self._clock.now() - queue_start
            else:
                queue_wait = 0.0

            exec_start = self._clock.now()
            try:
                result = task.func(*task.args, **task.kwargs)
                exec_time = self._clock.now() - exec_start
                with state.condition:
                    state.success_count += 1
                return TaskResult(
                    task_id=task.task_id,
                    group_name=group_name,
                    status=TaskStatus.SUCCESS,
                    result=result,
                    execution_time=exec_time,
                    queue_wait_time=queue_wait,
                )
            except Exception as e:
                exec_time = self._clock.now() - exec_start
                with state.condition:
                    state.failure_count += 1
                return TaskResult(
                    task_id=task.task_id,
                    group_name=group_name,
                    status=TaskStatus.FAILED,
                    exception=e,
                    execution_time=exec_time,
                    queue_wait_time=queue_wait,
                )
        finally:
            if acquired:
                with state.condition:
                    state.current_concurrency -= 1
                    if state.queue:
                        state.condition.notify_all()

    def _get_group_state(self, group_name: str) -> _GroupState:
        with self._lock:
            if group_name not in self._groups:
                raise GroupNotFoundError(group_name)
            return self._groups[group_name]

    @contextmanager
    def acquire(
        self,
        group_name: str,
        *,
        task_id: Optional[str] = None,
    ) -> Iterator[None]:
        if task_id is None:
            task_id = uuid4().hex

        state = self._get_group_state(group_name)
        acquired = False
        waiter: Optional[_AcquireWaiter] = None
        submitted_at = self._clock.now()

        with state.condition:
            if state.current_concurrency >= state.config.max_concurrency:
                if state.config.full_strategy == FullStrategy.REJECT:
                    raise BulkheadFullError(task_id, group_name)
                else:
                    if (
                        state.config.max_queue_size > 0
                        and len(state.queue) >= state.config.max_queue_size
                    ):
                        raise BulkheadFullError(
                            task_id,
                            group_name,
                            f"Bulkhead group '{group_name}' queue is full, "
                            f"task '{task_id}' rejected",
                        )

                    deadline: Optional[float] = None
                    if state.config.queue_timeout > 0:
                        deadline = submitted_at + state.config.queue_timeout

                    waiter = _AcquireWaiter(task_id=task_id, submitted_at=submitted_at)
                    state.queue.append(waiter)

                    while True:
                        if state.current_concurrency < state.config.max_concurrency:
                            if waiter in state.queue:
                                state.queue.remove(waiter)
                            break

                        wait_timeout: Optional[float] = None
                        if deadline is not None:
                            wait_timeout = deadline - self._clock.now()
                            if wait_timeout <= 0:
                                if waiter in state.queue:
                                    state.queue.remove(waiter)
                                raise BulkheadQueueTimeoutError(task_id, group_name)

                        state.condition.wait(timeout=wait_timeout)

                        if deadline is not None and self._clock.now() >= deadline:
                            if waiter in state.queue:
                                state.queue.remove(waiter)
                            raise BulkheadQueueTimeoutError(task_id, group_name)

            state.current_concurrency += 1
            acquired = True

        try:
            yield
        finally:
            if acquired:
                with state.condition:
                    state.current_concurrency -= 1
                    if state.queue:
                        state.condition.notify_all()
