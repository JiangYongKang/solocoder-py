from __future__ import annotations


class BulkheadError(Exception):
    pass


class BulkheadFullError(BulkheadError):
    def __init__(self, task_id: str, group_name: str, message: str | None = None) -> None:
        self.task_id = task_id
        self.group_name = group_name
        if message is None:
            message = (
                f"Bulkhead group '{group_name}' is full, "
                f"task '{task_id}' rejected"
            )
        super().__init__(message)


class BulkheadQueueTimeoutError(BulkheadError):
    def __init__(self, task_id: str, group_name: str, message: str | None = None) -> None:
        self.task_id = task_id
        self.group_name = group_name
        if message is None:
            message = (
                f"Bulkhead group '{group_name}' queue timeout, "
                f"task '{task_id}' failed to acquire slot"
            )
        super().__init__(message)


class GroupNotFoundError(BulkheadError):
    def __init__(self, group_name: str) -> None:
        self.group_name = group_name
        super().__init__(f"Bulkhead group '{group_name}' not found")


class GroupAlreadyExistsError(BulkheadError):
    def __init__(self, group_name: str) -> None:
        self.group_name = group_name
        super().__init__(f"Bulkhead group '{group_name}' already exists")


class InvalidConfigError(BulkheadError):
    pass
