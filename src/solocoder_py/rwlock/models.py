from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional
from collections import deque


class LockMode(str, Enum):
    FREE = "free"
    READ = "read"
    WRITE = "write"


class WaiterType(str, Enum):
    READER = "reader"
    WRITER = "writer"


@dataclass
class Waiter:
    thread_id: Any
    waiter_type: WaiterType
    ticket: int

    def __post_init__(self) -> None:
        if self.ticket < 0:
            raise ValueError("ticket cannot be negative")


@dataclass
class RWLockState:
    mode: LockMode = LockMode.FREE
    writer_thread_id: Optional[Any] = None
    readers: Dict[Any, int] = field(default_factory=dict)
    waiting_readers: Deque[Waiter] = field(default_factory=deque)
    waiting_writers: Deque[Waiter] = field(default_factory=deque)
    next_ticket: int = 0
    write_lock_count: int = 0

    @property
    def reader_count(self) -> int:
        return sum(self.readers.values())

    @property
    def is_free(self) -> bool:
        return self.mode == LockMode.FREE

    @property
    def is_read_locked(self) -> bool:
        return self.mode == LockMode.READ

    @property
    def is_write_locked(self) -> bool:
        return self.mode == LockMode.WRITE

    @property
    def has_waiting_writers(self) -> bool:
        return len(self.waiting_writers) > 0

    @property
    def has_waiting_readers(self) -> bool:
        return len(self.waiting_readers) > 0

    def generate_ticket(self) -> int:
        ticket = self.next_ticket
        self.next_ticket += 1
        return ticket

    def is_held_by(self, thread_id: Any) -> bool:
        if self.mode == LockMode.WRITE:
            return self.writer_thread_id == thread_id
        if self.mode == LockMode.READ:
            return thread_id in self.readers
        return False
