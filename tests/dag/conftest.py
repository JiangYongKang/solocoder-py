from __future__ import annotations

from typing import Any, Callable, Dict, List

import pytest

from solocoder_py.dag import DAGScheduler, Task, TaskExecutionContext


class TaskTracker:
    def __init__(self) -> None:
        self.executed: List[str] = []
        self.results: Dict[str, Any] = {}

    def make_action(
        self,
        task_id: str,
        result: Any = None,
        fail: bool = False,
        fail_after_execution: bool = False,
    ) -> Callable[[TaskExecutionContext], Any]:
        def action(ctx: TaskExecutionContext) -> Any:
            self.executed.append(task_id)
            if fail or fail_after_execution:
                raise RuntimeError(f"Task {task_id} failed intentionally")
            if result is not None:
                ctx.result = result
                self.results[task_id] = result
            return result

        return action


@pytest.fixture
def tracker() -> TaskTracker:
    return TaskTracker()


@pytest.fixture
def scheduler() -> DAGScheduler:
    return DAGScheduler()


def build_linear_scheduler(
    tracker: TaskTracker,
    task_count: int = 3,
    fail_at: int | None = None,
) -> DAGScheduler:
    scheduler = DAGScheduler()
    for i in range(task_count):
        task_id = f"task-{i}"
        deps = [f"task-{i - 1}"] if i > 0 else []
        should_fail = fail_at is not None and i == fail_at
        scheduler.register_task(
            task_id=task_id,
            dependencies=deps,
            action=tracker.make_action(task_id, result=i, fail=should_fail),
        )
    return scheduler


def build_diamond_scheduler(
    tracker: TaskTracker,
    fail_at: str | None = None,
) -> DAGScheduler:
    scheduler = DAGScheduler()
    for task_id in ["A", "B", "C", "D"]:
        should_fail = fail_at == task_id
        if task_id == "A":
            deps: List[str] = []
        elif task_id in ("B", "C"):
            deps = ["A"]
        else:
            deps = ["B", "C"]
        scheduler.register_task(
            task_id=task_id,
            dependencies=deps,
            action=tracker.make_action(task_id, result=task_id, fail=should_fail),
        )
    return scheduler


def build_single_node_scheduler(tracker: TaskTracker, fail: bool = False) -> DAGScheduler:
    scheduler = DAGScheduler()
    scheduler.register_task(
        task_id="only",
        dependencies=[],
        action=tracker.make_action("only", result=42, fail=fail),
    )
    return scheduler
