from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models import (
    InsufficientSlotsError,
    Priority,
    Task,
    TaskNotFoundError,
    TaskNotRunningError,
)


class FairResourcePoolScheduler:
    def __init__(
        self,
        total_slots: int,
        aging_interval: timedelta = timedelta(seconds=30),
        aging_promotion_step: int = 1,
        aging_threshold: Priority = Priority.LOW,
        max_wait_time: timedelta = timedelta(minutes=2),
        clock: Optional[callable] = None,
    ) -> None:
        if total_slots <= 0:
            raise ValueError("total_slots must be positive")
        if aging_promotion_step <= 0:
            raise ValueError("aging_promotion_step must be positive")

        self._total_slots: int = total_slots
        self._used_slots: int = 0
        self._aging_interval: timedelta = aging_interval
        self._aging_promotion_step: int = aging_promotion_step
        self._aging_threshold: Priority = aging_threshold
        self._max_wait_time: timedelta = max_wait_time
        self._clock = clock or datetime.now

        self._waiting_queue: List[Task] = []
        self._running_tasks: Dict[str, Task] = {}

    @property
    def total_slots(self) -> int:
        return self._total_slots

    @property
    def available_slots(self) -> int:
        return self._total_slots - self._used_slots

    @property
    def used_slots(self) -> int:
        return self._used_slots

    @property
    def waiting_count(self) -> int:
        return len(self._waiting_queue)

    @property
    def running_count(self) -> int:
        return len(self._running_tasks)

    def submit(self, task: Task) -> Optional[Task]:
        if task.resource_slots > self._total_slots:
            raise InsufficientSlotsError(
                f"Task requires {task.resource_slots} slots but pool only has {self._total_slots}"
            )

        task.wait_started_at = self._clock()
        task.is_running = False
        task.started_at = None
        task.effective_priority = task.priority
        task.is_starvation_protected = False
        task.last_promoted_at = None

        if self._can_allocate(task):
            self._allocate(task)
            return task

        self._waiting_queue.append(task)
        return None

    def release(self, task_id: str) -> List[Task]:
        if task_id not in self._running_tasks:
            raise TaskNotFoundError(f"Task not found or not running: {task_id}")

        task = self._running_tasks.pop(task_id)
        if not task.is_running:
            raise TaskNotRunningError(f"Task is not running: {task_id}")

        self._used_slots -= task.resource_slots
        task.is_running = False
        task.started_at = None

        newly_started = self._schedule_from_queue()
        return newly_started

    def tick(self) -> List[Task]:
        self._apply_aging()
        self._apply_starvation_protection()
        return self._schedule_from_queue()

    def _can_allocate(self, task: Task) -> bool:
        return task.resource_slots <= self.available_slots

    def _allocate(self, task: Task) -> None:
        self._used_slots += task.resource_slots
        task.is_running = True
        task.started_at = self._clock()
        self._running_tasks[task.id] = task

    def _apply_aging(self) -> None:
        now = self._clock()
        for task in self._waiting_queue:
            if task.is_starvation_protected:
                continue
            if task.effective_priority >= Priority.HIGHEST:
                continue
            reference_time = task.last_promoted_at or task.wait_started_at
            elapsed = now - reference_time
            if elapsed >= self._aging_interval:
                new_effective = Priority.clamp(
                    task.effective_priority + self._aging_promotion_step
                )
                if new_effective <= self._aging_threshold:
                    new_effective = Priority.clamp(self._aging_threshold + 1)
                task.effective_priority = new_effective
                task.last_promoted_at = now

    def _apply_starvation_protection(self) -> None:
        now = self._clock()
        for task in self._waiting_queue:
            if task.is_starvation_protected:
                continue
            waited = now - task.wait_started_at
            if waited >= self._max_wait_time:
                task.is_starvation_protected = True
                task.effective_priority = Priority.HIGHEST
                task.last_promoted_at = now

    def _schedule_from_queue(self) -> List[Task]:
        newly_started: List[Task] = []
        skipped: List[Task] = []

        while True:
            next_task = self._pick_next(skipped)
            if next_task is None:
                break
            if not self._can_allocate(next_task):
                skipped.append(next_task)
                continue
            self._waiting_queue.remove(next_task)
            self._allocate(next_task)
            newly_started.append(next_task)

        return newly_started

    def _pick_next(self, skipped: Optional[List[Task]] = None) -> Optional[Task]:
        if not self._waiting_queue:
            return None

        skipped_set = set(t.id for t in (skipped or []))

        starvation_tasks = [
            t for t in self._waiting_queue
            if t.is_starvation_protected and t.id not in skipped_set
        ]
        if starvation_tasks:
            starvation_tasks.sort(key=lambda t: t.wait_started_at)
            return starvation_tasks[0]

        normal_tasks = [t for t in self._waiting_queue if t.id not in skipped_set]
        if not normal_tasks:
            return None

        sorted_tasks = sorted(
            normal_tasks,
            key=lambda t: (-t.effective_priority, t.wait_started_at),
        )
        return sorted_tasks[0]
