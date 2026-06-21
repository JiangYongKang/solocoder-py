from __future__ import annotations

import inspect
import logging
import threading
import weakref
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EventCallback = Callable[[Any], None]


class _Subscription:
    def __init__(self, callback: EventCallback, once: bool = False) -> None:
        self.once = once
        self._is_weak = inspect.ismethod(callback)
        self._weak_ref: Optional[weakref.ReferenceType] = None
        self._strong_ref: Optional[EventCallback] = None
        self._once_fired: bool = False
        self._once_lock: Optional[threading.Lock] = threading.Lock() if once else None

        if self._is_weak:
            self._weak_ref = weakref.WeakMethod(callback)
        else:
            self._strong_ref = callback

    def get_callback(self) -> Optional[EventCallback]:
        if self._is_weak:
            return self._weak_ref()
        return self._strong_ref

    def is_alive(self) -> bool:
        return self.get_callback() is not None

    def matches(self, callback: EventCallback) -> bool:
        cb = self.get_callback()
        if cb is None:
            return False
        return cb == callback

    def claim_once(self) -> bool:
        if not self.once:
            return False
        with self._once_lock:
            if self._once_fired:
                return False
            self._once_fired = True
            return True


class EventBus:
    def __init__(self) -> None:
        self._channels: Dict[str, List[_Subscription]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if callback is None:
            raise ValueError("callback cannot be None")
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            if event_type not in self._channels:
                self._channels[event_type] = []
            self._channels[event_type].append(_Subscription(callback, once=False))

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if callback is None:
            raise ValueError("callback cannot be None")

        with self._lock:
            if event_type not in self._channels:
                return
            subscribers = self._channels[event_type]
            filtered = [
                sub for sub in subscribers
                if not sub.matches(callback)
            ]
            if filtered:
                self._channels[event_type] = filtered
            else:
                del self._channels[event_type]

    def once(self, event_type: str, callback: EventCallback) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if callback is None:
            raise ValueError("callback cannot be None")
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            if event_type not in self._channels:
                self._channels[event_type] = []
            self._channels[event_type].append(_Subscription(callback, once=True))

    def publish(self, event_type: str, data: Any = None) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")

        with self._lock:
            if event_type not in self._channels:
                return
            subscribers = list(self._channels[event_type])

        indices_to_remove: List[int] = []
        callbacks_to_invoke: List[EventCallback] = []

        for i, sub in enumerate(subscribers):
            with self._lock:
                cb = sub.get_callback()
                if cb is None:
                    indices_to_remove.append(i)
                    continue
                if sub.once:
                    if not sub.claim_once():
                        continue
                    indices_to_remove.append(i)

            callbacks_to_invoke.append(cb)

        for cb in callbacks_to_invoke:
            try:
                cb(data)
            except Exception:
                logger.exception(
                    "Subscriber callback raised an exception for event type '%s'",
                    event_type,
                )

        if indices_to_remove:
            with self._lock:
                if event_type in self._channels:
                    channel = self._channels[event_type]
                    for i in reversed(indices_to_remove):
                        if i < len(channel):
                            del channel[i]
                    if not channel:
                        del self._channels[event_type]

    def subscriber_count(self, event_type: str) -> int:
        with self._lock:
            if event_type not in self._channels:
                return 0
            count = 0
            for sub in self._channels[event_type]:
                if sub.is_alive():
                    count += 1
            return count

    def event_types(self) -> List[str]:
        with self._lock:
            return list(self._channels.keys())

    def clear(self) -> None:
        with self._lock:
            self._channels.clear()

    def is_subscribed(self, event_type: str, callback: EventCallback) -> bool:
        with self._lock:
            if event_type not in self._channels:
                return False
            for sub in self._channels[event_type]:
                if sub.matches(callback):
                    return True
            return False
