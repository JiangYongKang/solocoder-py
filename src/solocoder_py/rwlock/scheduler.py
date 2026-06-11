from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


class Parked(Exception):
    pass


class Scheduler(ABC):
    @abstractmethod
    def current_thread_id(self) -> Any:
        ...

    @abstractmethod
    def park(self, thread_id: Any) -> None:
        ...

    @abstractmethod
    def unpark(self, thread_id: Any) -> bool:
        ...

    @abstractmethod
    def unpark_all(self, thread_ids: List[Any]) -> int:
        ...


@dataclass
class ManualScheduler(Scheduler):
    _current_thread_id: Any = None
    _parked: Deque[Any] = field(default_factory=deque)
    _parked_set: set = field(default_factory=set)

    def set_current_thread(self, thread_id: Any) -> None:
        self._current_thread_id = thread_id

    def current_thread_id(self) -> Any:
        if self._current_thread_id is None:
            raise RuntimeError("current_thread_id is not set in ManualScheduler")
        return self._current_thread_id

    def park(self, thread_id: Any) -> None:
        if thread_id in self._parked_set:
            raise ValueError(f"Thread {thread_id} is already parked")
        self._parked.append(thread_id)
        self._parked_set.add(thread_id)
        raise Parked(thread_id)

    def unpark(self, thread_id: Any) -> bool:
        if thread_id in self._parked_set:
            self._parked.remove(thread_id)
            self._parked_set.discard(thread_id)
            return True
        return False

    def unpark_all(self, thread_ids: List[Any]) -> int:
        count = 0
        for tid in thread_ids:
            if self.unpark(tid):
                count += 1
        return count

    def is_parked(self, thread_id: Any) -> bool:
        return thread_id in self._parked_set

    @property
    def parked_count(self) -> int:
        return len(self._parked)

    @property
    def parked_threads(self) -> List[Any]:
        return list(self._parked)
