from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .models import (
    CycleDetectedError,
    DAGError,
    DependencyNotFoundError,
    Task,
    TaskAlreadyRegisteredError,
    TaskExecutionContext,
    TaskNotFoundError,
    TaskNotReadyError,
    TaskStatus,
)


class DAGScheduler:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._dependents: Dict[str, Set[str]] = {}

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def has_task(self, task_id: str) -> bool:
        return task_id in self._tasks

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return self._tasks[task_id]

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def register_task(
        self,
        task_id: str,
        dependencies: Optional[List[str]] = None,
        action=None,
        name: Optional[str] = None,
    ) -> Task:
        if task_id in self._tasks:
            raise TaskAlreadyRegisteredError(f"Task already registered: {task_id}")

        deps = dependencies or []

        if task_id in deps:
            cycle_info = f"{task_id} -> {task_id}"
            raise CycleDetectedError(
                f"Adding dependencies for '{task_id}' would create a cycle: {cycle_info}"
            )

        for dep_id in deps:
            if dep_id not in self._tasks:
                raise DependencyNotFoundError(
                    f"Dependency '{dep_id}' not found for task '{task_id}'"
                )

        has_cycle, cycle_path = self._detect_cycle(task_id, deps)
        if has_cycle:
            cycle_info = " -> ".join(cycle_path + [cycle_path[0]])
            raise CycleDetectedError(
                f"Adding dependencies for '{task_id}' would create a cycle: {cycle_info}"
            )

        task = Task(task_id=task_id, dependencies=deps, action=action, name=name)
        self._tasks[task_id] = task
        if task_id not in self._dependents:
            self._dependents[task_id] = set()
        for dep_id in deps:
            self._dependents[dep_id].add(task_id)

        if not deps:
            task.mark_ready()

        return task

    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        if dependency_id not in self._tasks:
            raise DependencyNotFoundError(
                f"Dependency task not found: {dependency_id}"
            )

        if task_id == dependency_id:
            cycle_info = f"{task_id} -> {task_id}"
            raise CycleDetectedError(
                f"Adding dependency '{dependency_id}' -> '{task_id}' would create a cycle: {cycle_info}"
            )

        task = self._tasks[task_id]
        if dependency_id in task.dependencies:
            return

        has_cycle, cycle_path = self._detect_cycle(
            task_id, task.dependencies + [dependency_id]
        )
        if has_cycle:
            cycle_info = " -> ".join(cycle_path + [cycle_path[0]])
            raise CycleDetectedError(
                f"Adding dependency '{dependency_id}' -> '{task_id}' would create a cycle: {cycle_info}"
            )

        task.dependencies.append(dependency_id)
        self._dependents[dependency_id].add(task_id)

        if task.status == TaskStatus.READY:
            task.status = TaskStatus.PENDING

    def get_dependents(self, task_id: str) -> List[str]:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return sorted(self._dependents.get(task_id, set()))

    def get_dependencies(self, task_id: str) -> List[str]:
        task = self.get_task(task_id)
        return list(task.dependencies)

    def topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {
            tid: len(t.dependencies) for tid, t in self._tasks.items()
        }
        queue: List[str] = [tid for tid, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in self._dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._tasks):
            raise DAGError("DAG has a cycle, cannot perform topological sort")

        return result

    def get_ready_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.READY]

    def execute_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.status != TaskStatus.READY:
            raise TaskNotReadyError(
                f"Task '{task_id}' is not ready (status: {task.status.value})"
            )

        task.mark_running()

        if task.action is not None:
            ctx = TaskExecutionContext(task_id=task_id)
            try:
                result = task.action(ctx)
                task.mark_success(result if result is not None else ctx.result)
            except Exception as e:
                task.mark_failed(e)
                self._block_downstream(task_id)
                return task
        else:
            task.mark_success()

        self._propagate_success(task_id)
        return task

    def complete_task(self, task_id: str, result=None) -> Task:
        task = self.get_task(task_id)
        if task.status == TaskStatus.READY:
            task.mark_running()
        if task.status != TaskStatus.RUNNING:
            raise TaskNotReadyError(
                f"Task '{task_id}' is not running (status: {task.status.value})"
            )

        task.mark_success(result)
        self._propagate_success(task_id)
        return task

    def fail_task(self, task_id: str, error: Optional[Exception] = None) -> Task:
        task = self.get_task(task_id)
        if task.status == TaskStatus.READY:
            task.mark_running()
        if task.status != TaskStatus.RUNNING:
            raise TaskNotReadyError(
                f"Task '{task_id}' is not running (status: {task.status.value})"
            )

        if error is None:
            error = DAGError(f"Task failed: {task_id}")
        task.mark_failed(error)
        self._block_downstream(task_id)
        return task

    def reset(self) -> None:
        for task in self._tasks.values():
            task.status = TaskStatus.PENDING
            task.result = None
            task.error = None
            task.started_at = None
            task.completed_at = None

        for task in self._tasks.values():
            if not task.dependencies:
                task.mark_ready()

    def is_complete(self) -> bool:
        return all(t.is_terminal() for t in self._tasks.values())

    def is_success(self) -> bool:
        return all(t.status == TaskStatus.SUCCESS for t in self._tasks.values())

    def get_downstream(self, task_id: str) -> List[str]:
        visited: Set[str] = set()
        result: List[str] = []
        self._collect_downstream(task_id, visited, result)
        return result

    def _collect_downstream(
        self, task_id: str, visited: Set[str], result: List[str]
    ) -> None:
        for dep in self._dependents.get(task_id, set()):
            if dep not in visited:
                visited.add(dep)
                result.append(dep)
                self._collect_downstream(dep, visited, result)

    def _detect_cycle(
        self, new_task_id: str, dependencies: List[str]
    ) -> Tuple[bool, List[str]]:
        adjacency: Dict[str, List[str]] = {}
        for tid, task in self._tasks.items():
            adjacency[tid] = list(task.dependencies)
        adjacency[new_task_id] = list(dependencies)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {tid: WHITE for tid in adjacency}
        recursion_stack: List[str] = []
        found_cycle: List[str] = []

        def dfs(node: str) -> bool:
            color[node] = GRAY
            recursion_stack.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    idx = recursion_stack.index(neighbor)
                    found_cycle.extend(recursion_stack[idx:])
                    return True
                if color[neighbor] == WHITE:
                    if dfs(neighbor):
                        return True
            recursion_stack.pop()
            color[node] = BLACK
            return False

        for node in adjacency:
            if color[node] == WHITE:
                if dfs(node):
                    return True, found_cycle

        return False, []

    def _propagate_success(self, completed_task_id: str) -> None:
        for dependent_id in self._dependents.get(completed_task_id, set()):
            dependent = self._tasks[dependent_id]
            if dependent.status != TaskStatus.PENDING:
                continue
            if all(
                self._tasks[dep_id].status == TaskStatus.SUCCESS
                for dep_id in dependent.dependencies
            ):
                dependent.mark_ready()

    def _block_downstream(self, failed_task_id: str) -> None:
        downstream = self.get_downstream(failed_task_id)
        for task_id in downstream:
            self._tasks[task_id].mark_blocked()

    def run_all(self) -> List[Task]:
        executed: List[Task] = []
        while True:
            ready = self.get_ready_tasks()
            if not ready:
                break
            for task in ready:
                self.execute_task(task.task_id)
                executed.append(task)
        return executed
