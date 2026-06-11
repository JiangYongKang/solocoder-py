from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .exceptions import FutureAlreadyCompletedError, FutureNotReadyError
from .models import FutureState

logger = logging.getLogger(__name__)

_Callback = Callable[["Future"], None]


class Future:
    def __init__(self) -> None:
        self._state: FutureState = FutureState.PENDING
        self._result: Any = None
        self._error: Optional[Exception] = None
        self._lock: threading.Lock = threading.Lock()
        self._event: threading.Event = threading.Event()
        self._callbacks: list[_Callback] = []

    @property
    def state(self) -> FutureState:
        with self._lock:
            return self._state

    @property
    def is_done(self) -> bool:
        with self._lock:
            return self._state != FutureState.PENDING

    @property
    def result(self) -> Any:
        with self._lock:
            if self._state == FutureState.PENDING:
                raise FutureNotReadyError("Future is not yet completed")
            if self._state == FutureState.FAILED:
                raise self._error
            return self._result

    @property
    def error(self) -> Optional[Exception]:
        with self._lock:
            if self._state == FutureState.PENDING:
                raise FutureNotReadyError("Future is not yet completed")
            return self._error

    def set_result(self, value: Any) -> None:
        with self._lock:
            if self._state != FutureState.PENDING:
                raise FutureAlreadyCompletedError(
                    f"Future already completed with state {self._state.value}"
                )
            self._result = value
            self._state = FutureState.COMPLETED
            self._event.set()
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(self)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in Future callback during set_result")

    def set_error(self, error: Exception) -> None:
        with self._lock:
            if self._state != FutureState.PENDING:
                raise FutureAlreadyCompletedError(
                    f"Future already completed with state {self._state.value}"
                )
            self._error = error
            self._state = FutureState.FAILED
            self._event.set()
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(self)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in Future callback during set_error")

    def add_callback(self, callback: _Callback) -> None:
        with self._lock:
            if self._state != FutureState.PENDING:
                fire_now = True
            else:
                self._callbacks.append(callback)
                fire_now = False

        if fire_now:
            try:
                callback(self)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in Future callback during add_callback")

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._event.wait(timeout=timeout)

    def get(self, timeout: Optional[float] = None) -> Any:
        if not self._event.wait(timeout=timeout):
            from .exceptions import FutureTimeoutError

            raise FutureTimeoutError(
                f"Future did not complete within {timeout} seconds"
            )
        with self._lock:
            if self._state == FutureState.FAILED:
                raise self._error
            return self._result

    @staticmethod
    def completed(value: Any) -> Future:
        f = Future()
        f.set_result(value)
        return f

    @staticmethod
    def failed(error: Exception) -> Future:
        f = Future()
        f.set_error(error)
        return f

    @staticmethod
    def from_callable(fn: Callable[[], Any]) -> Future:
        f: Future = Future()

        def _run() -> None:
            try:
                result = fn()
                f.set_result(result)
            except Exception as e:
                f.set_error(e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return f
