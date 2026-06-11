from __future__ import annotations


class PriorityThreadPoolError(Exception):
    pass


class InvalidConfigError(PriorityThreadPoolError):
    pass


class ThreadPoolShutdownError(PriorityThreadPoolError):
    def __init__(self, message: str | None = None) -> None:
        if message is None:
            message = "Thread pool is shutdown and no longer accepts new tasks"
        super().__init__(message)


class TaskNotFoundError(PriorityThreadPoolError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' not found")
