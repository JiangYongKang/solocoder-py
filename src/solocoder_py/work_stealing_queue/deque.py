from __future__ import annotations

import threading
from collections import deque
from typing import Generic, TypeVar

from .exceptions import QueueFullError

T = TypeVar("T")


class WorkStealingDeque(Generic[T]):
    """
    工作窃取双端队列。

    队列两端采用不同的操作策略：
    - 底端（bottom / right end）：本地工作线程使用，LIFO 策略
      * push_bottom: 向底端推入任务
      * pop_bottom: 从底端弹出任务
    - 顶端（top / left end）：窃取线程使用，FIFO 策略
      * steal: 从顶端窃取任务

    并发设计：
    - 底端操作由 _bottom_lock 保护，同一时刻只有一个底端操作在执行
    - 窃取操作由 _steal_lock 保护，同一时刻只有一个窃取操作在执行
    - 当队列元素 > 1 时，底端操作与窃取操作可在不同端并发执行，互不阻塞
    - 当队列元素 == 1 时，需要协调两端操作，按 bottom -> steal 顺序加锁避免死锁
    - 满容量检测仅需底端锁（只有 push_bottom 能增加元素）
    """

    def __init__(self, max_capacity: int = 1024) -> None:
        if max_capacity <= 0:
            raise ValueError("max_capacity must be positive")
        self._deque: deque[T] = deque()
        self._max_capacity = max_capacity
        self._bottom_lock = threading.Lock()
        self._steal_lock = threading.Lock()

    @property
    def max_capacity(self) -> int:
        return self._max_capacity

    def __len__(self) -> int:
        return self.size()

    def is_empty(self) -> bool:
        return self.size() == 0

    def size(self) -> int:
        with self._bottom_lock:
            with self._steal_lock:
                return len(self._deque)

    def push_bottom(self, item: T) -> None:
        """
        本地推入：向队列底端添加元素（LIFO 入队）。

        由队列的所有者线程调用。

        Args:
            item: 要推入的元素

        Raises:
            QueueFullError: 队列已满时抛出
        """
        with self._bottom_lock:
            if len(self._deque) >= self._max_capacity:
                raise QueueFullError(
                    f"Queue is at full capacity ({self._max_capacity})"
                )
            self._deque.append(item)

    def pop_bottom(self) -> T | None:
        """
        本地弹出：从队列底端取出元素（LIFO 出队）。

        由队列的所有者线程调用。

        Returns:
            队底端的元素，如果队列为空则返回 None
        """
        self._bottom_lock.acquire()
        if not self._deque:
            self._bottom_lock.release()
            return None

        if len(self._deque) > 1:
            item = self._deque.pop()
            self._bottom_lock.release()
            return item

        item = self._pop_bottom_slow_path()
        self._bottom_lock.release()
        return item

    def _pop_bottom_slow_path(self) -> T | None:
        """
        慢路径：队列只有一个元素时，同时获取窃取锁避免冲突。

        前置条件：已持有 _bottom_lock
        锁顺序：bottom_lock -> steal_lock（与 steal 慢路径一致，避免死锁）
        """
        self._steal_lock.acquire()
        try:
            if not self._deque:
                return None
            return self._deque.pop()
        finally:
            self._steal_lock.release()

    def steal(self) -> T | None:
        """
        窃取：从队列顶端取出元素（FIFO 出队）。

        由其他工作线程调用，窃取最早入队的任务。

        Returns:
            队顶端的元素，如果队列为空则返回 None
        """
        self._steal_lock.acquire()
        if not self._deque:
            self._steal_lock.release()
            return None

        if len(self._deque) > 1:
            item = self._deque.popleft()
            self._steal_lock.release()
            return item

        self._steal_lock.release()
        return self._steal_slow_path()

    def _steal_slow_path(self) -> T | None:
        """
        慢路径：队列只有一个元素时，同时获取两把锁避免冲突。

        按 bottom -> steal 顺序获取锁，与 pop_bottom 慢路径一致，避免死锁。
        """
        self._bottom_lock.acquire()
        self._steal_lock.acquire()
        try:
            if not self._deque:
                return None
            return self._deque.popleft()
        finally:
            self._steal_lock.release()
            self._bottom_lock.release()
