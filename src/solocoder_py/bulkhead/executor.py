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

_POLL_INTERVAL: float = 0.01


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
        queue_wait_time: float = 0.0

        with state.condition:
            if state.current_concurrency >= state.config.max_concurrency:
                if state.config.full_strategy == FullStrategy.REJECT:
                    return TaskResult(
                        task_id=task.task_id,
                        group_name=group_name,
                        status=TaskStatus.REJECTED,
                        exception=BulkheadFullError(task.task_id, group_name),
                    )
                try:
                    queue_wait_time = self._wait_for_slot(state, task)
                except BulkheadQueueTimeoutError as e:
                    return TaskResult(
                        task_id=task.task_id,
                        group_name=group_name,
                        status=TaskStatus.QUEUE_TIMEOUT,
                        exception=e,
                        queue_wait_time=e.queue_wait_time,
                    )
                except BulkheadFullError as e:
                    return TaskResult(
                        task_id=task.task_id,
                        group_name=group_name,
                        status=TaskStatus.REJECTED,
                        exception=e,
                    )

            state.current_concurrency += 1
            acquired = True

        try:
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
                    queue_wait_time=queue_wait_time,
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
                    queue_wait_time=queue_wait_time,
                )
        finally:
            if acquired:
                with state.condition:
                    state.current_concurrency -= 1
                    if state.queue:
                        state.condition.notify_all()

    def _wait_for_slot(self, state: _GroupState, entry: _QueueEntry) -> float:
        assert state.config.full_strategy == FullStrategy.QUEUE

        if state.config.max_queue_size > 0 and len(state.queue) >= state.config.max_queue_size:
            raise BulkheadFullError(
                entry.task_id,
                state.config.name,
                f"Bulkhead group '{state.config.name}' queue is full, "
                f"task '{entry.task_id}' rejected",
            )

        queue_start = self._clock.now()
        deadline: Optional[float] = None
        if state.config.queue_timeout > 0:
            deadline = entry.submitted_at + state.config.queue_timeout

        state.queue.append(entry)

        try:
            while True:
                if state.current_concurrency < state.config.max_concurrency:
                    state.queue.remove(entry)
                    return self._clock.now() - queue_start

                if deadline is not None and self._clock.now() >= deadline:
                    state.queue.remove(entry)
                    wait = self._clock.now() - queue_start
                    raise BulkheadQueueTimeoutError(
                        entry.task_id, state.config.name, queue_wait_time=wait
                    )

                state.condition.wait(timeout=_POLL_INTERVAL)
        except BaseException:
            if entry in state.queue:
                state.queue.remove(entry)
            raise

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
        submitted_at = self._clock.now()

        with state.condition:
            if state.current_concurrency >= state.config.max_concurrency:
                if state.config.full_strategy == FullStrategy.REJECT:
                    raise BulkheadFullError(task_id, group_name)
                waiter = _AcquireWaiter(task_id=task_id, submitted_at=submitted_at)
                self._wait_for_slot(state, waiter)

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
