from __future__ import annotations


class WorkStealingQueueError(Exception):
    pass


class QueueFullError(WorkStealingQueueError):
    pass


class InvalidWorkerError(WorkStealingQueueError):
    pass
