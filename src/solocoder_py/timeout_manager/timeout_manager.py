from __future__ import annotations

import threading
import uuid
from typing import Callable, Dict, List, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    ContextAlreadyCancelledError,
    ContextCancelledError,
    InvalidDeadlineError,
)
from .models import TimeoutContextInfo


class TimeoutContext:
    def __init__(
        self,
        context_id: str,
        deadline: float,
        created_at: float,
        parent: Optional["TimeoutContext"] = None,
    ) -> None:
        self._context_id = context_id
        self._deadline = deadline
        self._created_at = created_at
        self._parent = parent
        self._children: List["TimeoutContext"] = []
        self._callbacks: List[Callable[["TimeoutContext"], None]] = []
        self._is_cancelled = False
        self._is_expired = False
        self._cancel_reason: Optional[str] = None
        self._callbacks_triggered = False

    @property
    def context_id(self) -> str:
        return self._context_id

    @property
    def deadline(self) -> float:
        return self._deadline

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def parent(self) -> Optional["TimeoutContext"]:
        return self._parent

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def is_expired(self) -> bool:
        return self._is_expired

    @property
    def cancel_reason(self) -> Optional[str]:
        return self._cancel_reason

    @property
    def callbacks_triggered(self) -> bool:
        return self._callbacks_triggered

    @property
    def children(self) -> List["TimeoutContext"]:
        return list(self._children)

    @property
    def callbacks(self) -> List[Callable[["TimeoutContext"], None]]:
        return list(self._callbacks)

    def is_active(self) -> bool:
        return not self._is_cancelled and not self._is_expired

    def add_callback(self, callback: Callable[["TimeoutContext"], None]) -> None:
        if self._is_cancelled:
            raise ContextAlreadyCancelledError(
                f"Cannot add callback to cancelled context '{self._context_id}'"
            )
        if callback is None:
            raise InvalidDeadlineError("Callback cannot be None")
        self._callbacks.append(callback)

    def _add_child(self, child: "TimeoutContext") -> None:
        self._children.append(child)

    def _cancel(self, reason: Optional[str] = None) -> None:
        if self._is_cancelled:
            return
        self._is_cancelled = True
        self._cancel_reason = reason

    def _mark_expired(self) -> None:
        if self._is_expired or self._is_cancelled:
            return
        self._is_expired = True

    def _trigger_callbacks(self) -> None:
        if self._callbacks_triggered:
            return
        self._callbacks_triggered = True
        for callback in list(self._callbacks):
            try:
                callback(self)
            except Exception:
                pass

    def to_info(self) -> TimeoutContextInfo:
        return TimeoutContextInfo(
            context_id=self._context_id,
            deadline=self._deadline,
            created_at=self._created_at,
            is_cancelled=self._is_cancelled,
            is_expired=self._is_expired,
            cancel_reason=self._cancel_reason,
            parent_id=self._parent.context_id if self._parent else None,
        )


class TimeoutManager:
    def __init__(
        self,
        clock: Optional[Clock] = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._contexts: Dict[str, TimeoutContext] = {}
        self._lock = threading.RLock()

    @property
    def clock(self) -> Clock:
        return self._clock

    def create_root_context(self, deadline: float) -> TimeoutContext:
        with self._lock:
            now = self._clock.now()
            if deadline <= now:
                raise InvalidDeadlineError(
                    f"Deadline {deadline} must be greater than current time {now}"
                )
            context_id = str(uuid.uuid4())
            context = TimeoutContext(
                context_id=context_id,
                deadline=deadline,
                created_at=now,
                parent=None,
            )
            self._contexts[context_id] = context
            return context

    def create_child_context(
        self,
        parent_id: str,
        deadline: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> TimeoutContext:
        with self._lock:
            parent = self._contexts.get(parent_id)
            if parent is None:
                raise ContextCancelledError(
                    f"Parent context '{parent_id}' not found"
                )
            if parent.is_cancelled:
                raise ContextAlreadyCancelledError(
                    f"Cannot create child context: parent context '{parent_id}' is already cancelled"
                )
            if parent.is_expired:
                raise ContextCancelledError(
                    f"Cannot create child context: parent context '{parent_id}' has already expired"
                )

            now = self._clock.now()
            parent_deadline = parent.deadline

            if deadline is not None and timeout is not None:
                raise InvalidDeadlineError(
                    "Cannot specify both deadline and timeout"
                )

            if deadline is not None:
                child_deadline = deadline
            elif timeout is not None:
                if timeout <= 0:
                    raise InvalidDeadlineError("Timeout must be positive")
                child_deadline = now + timeout
            else:
                child_deadline = parent_deadline

            actual_deadline = min(child_deadline, parent_deadline)

            if actual_deadline <= now:
                raise InvalidDeadlineError(
                    f"Computed deadline {actual_deadline} must be greater than current time {now}"
                )

            context_id = str(uuid.uuid4())
            child = TimeoutContext(
                context_id=context_id,
                deadline=actual_deadline,
                created_at=now,
                parent=parent,
            )
            parent._add_child(child)
            self._contexts[context_id] = child
            return child

    def cancel_context(self, context_id: str, reason: Optional[str] = None) -> None:
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise ContextCancelledError(
                    f"Context '{context_id}' not found"
                )
            if context.is_cancelled or context.is_expired:
                return

            self._cancel_context_and_children(context, reason)

    def _cancel_context_and_children(
        self, context: TimeoutContext, reason: Optional[str]
    ) -> None:
        context._cancel(reason)
        for child in context.children:
            self._cancel_context_and_children(child, reason)

    def add_callback(
        self,
        context_id: str,
        callback: Callable[[TimeoutContext], None],
    ) -> None:
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise ContextCancelledError(
                    f"Context '{context_id}' not found"
                )
            if context.is_cancelled:
                raise ContextAlreadyCancelledError(
                    f"Cannot add callback to cancelled context '{context_id}'"
                )
            context.add_callback(callback)

    def get_context(self, context_id: str) -> Optional[TimeoutContextInfo]:
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return None
            return context.to_info()

    def get_all_contexts(self) -> Dict[str, TimeoutContextInfo]:
        with self._lock:
            return {
                cid: ctx.to_info() for cid, ctx in self._contexts.items()
            }

    def check_expired(self) -> List[str]:
        expired_ids: List[str] = []
        pending_callbacks: List[TimeoutContext] = []

        with self._lock:
            now = self._clock.now()
            contexts_snapshot = list(self._contexts.values())

            for context in contexts_snapshot:
                if not context.is_active():
                    continue
                if now >= context.deadline:
                    self._expire_context_and_children(context)
                    expired_ids.append(context.context_id)

            for context in contexts_snapshot:
                if context.is_expired and not context.callbacks_triggered:
                    pending_callbacks.append(context)

        for context in pending_callbacks:
            context._trigger_callbacks()

        return expired_ids

    def _expire_context_and_children(self, context: TimeoutContext) -> None:
        context._mark_expired()
        for child in context.children:
            self._expire_context_and_children(child)

    def is_active(self, context_id: str) -> bool:
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return False
            return context.is_active()
