from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Optional

from .exceptions import FutureAlreadySettledError, FutureNotReadyError, TimeoutError
from .models import FutureState, SettledResult

logger = logging.getLogger(__name__)

_OnFulfilled = Callable[[Any], Any]
_OnRejected = Callable[[Exception], Any]


class Future:
    def __init__(self) -> None:
        self._state: FutureState = FutureState.PENDING
        self._value: Any = None
        self._reason: Optional[Exception] = None
        self._lock: threading.Lock = threading.Lock()
        self._fulfill_handlers: List[_OnFulfilled] = []
        self._reject_handlers: List[_OnRejected] = []
        self._next_futures: List["_ChainLink"] = []

    @property
    def state(self) -> FutureState:
        with self._lock:
            return self._state

    @property
    def is_settled(self) -> bool:
        with self._lock:
            return self._state != FutureState.PENDING

    @property
    def value(self) -> Any:
        with self._lock:
            if self._state == FutureState.PENDING:
                raise FutureNotReadyError("Future is not yet settled")
            if self._state == FutureState.REJECTED:
                raise self._reason
            return self._value

    @property
    def reason(self) -> Optional[Exception]:
        with self._lock:
            if self._state == FutureState.PENDING:
                raise FutureNotReadyError("Future is not yet settled")
            return self._reason

    def _fulfill(self, value: Any) -> None:
        with self._lock:
            if self._state != FutureState.PENDING:
                raise FutureAlreadySettledError(
                    f"Future already settled with state {self._state.value}"
                )
            self._value = value
            self._state = FutureState.FULFILLED
            fulfill_handlers = list(self._fulfill_handlers)
            next_futures = list(self._next_futures)

        for handler in fulfill_handlers:
            try:
                handler(value)
            except Exception:
                logger.exception("Unexpected error in fulfill handler")

        for link in next_futures:
            self._propagate_fulfill(link, value)

    def _reject(self, reason: Exception) -> None:
        with self._lock:
            if self._state != FutureState.PENDING:
                raise FutureAlreadySettledError(
                    f"Future already settled with state {self._state.value}"
                )
            self._reason = reason
            self._state = FutureState.REJECTED
            reject_handlers = list(self._reject_handlers)
            next_futures = list(self._next_futures)

        for handler in reject_handlers:
            try:
                handler(reason)
            except Exception:
                logger.exception("Unexpected error in reject handler")

        for link in next_futures:
            self._propagate_reject(link, reason)

    def _propagate_fulfill(self, link: "_ChainLink", value: Any) -> None:
        if link.on_fulfilled is not None:
            try:
                result = link.on_fulfilled(value)
                if link.flatten and isinstance(result, Future):
                    def _inner_fulfill(v: Any) -> None:
                        try:
                            link.future._fulfill(v)
                        except FutureAlreadySettledError:
                            pass

                    def _inner_reject(e: Exception) -> None:
                        try:
                            link.future._reject(e)
                        except FutureAlreadySettledError:
                            pass

                    result._add_chain_link(_ChainLink(
                        future=link.future,
                        on_fulfilled=_inner_fulfill,
                        on_rejected=_inner_reject,
                        flatten=True,
                    ))
                else:
                    try:
                        link.future._fulfill(result)
                    except FutureAlreadySettledError:
                        pass
            except Exception as e:
                try:
                    link.future._reject(e)
                except FutureAlreadySettledError:
                    pass
        else:
            try:
                link.future._fulfill(value)
            except FutureAlreadySettledError:
                pass

    def _propagate_reject(self, link: "_ChainLink", reason: Exception) -> None:
        if link.on_rejected is not None:
            try:
                result = link.on_rejected(reason)
                if link.flatten and isinstance(result, Future):
                    def _inner_fulfill(v: Any) -> None:
                        try:
                            link.future._fulfill(v)
                        except FutureAlreadySettledError:
                            pass

                    def _inner_reject(e: Exception) -> None:
                        try:
                            link.future._reject(e)
                        except FutureAlreadySettledError:
                            pass

                    result._add_chain_link(_ChainLink(
                        future=link.future,
                        on_fulfilled=_inner_fulfill,
                        on_rejected=_inner_reject,
                        flatten=True,
                    ))
                else:
                    try:
                        link.future._fulfill(result)
                    except FutureAlreadySettledError:
                        pass
            except Exception as e:
                try:
                    link.future._reject(e)
                except FutureAlreadySettledError:
                    pass
        else:
            try:
                link.future._reject(reason)
            except FutureAlreadySettledError:
                pass

    def _add_chain_link(self, link: "_ChainLink") -> None:
        with self._lock:
            if self._state == FutureState.PENDING:
                self._next_futures.append(link)
                return

        if self._state == FutureState.FULFILLED:
            self._propagate_fulfill(link, self._value)
        else:
            self._propagate_reject(link, self._reason)

    def then(self, on_fulfilled: _OnFulfilled) -> "Future":
        next_future = Future()
        link = _ChainLink(future=next_future, on_fulfilled=on_fulfilled, on_rejected=None, flatten=False)
        self._add_chain_link(link)
        return next_future

    def compose(self, on_fulfilled: Callable[[Any], "Future"]) -> "Future":
        next_future = Future()

        def _handler(value: Any) -> Any:
            inner_future = on_fulfilled(value)
            if not isinstance(inner_future, Future):
                raise TypeError(f"compose callback must return a Future, got {type(inner_future)}")
            return inner_future

        link = _ChainLink(future=next_future, on_fulfilled=_handler, on_rejected=None, flatten=True)
        self._add_chain_link(link)
        return next_future

    def catch(self, on_rejected: _OnRejected) -> "Future":
        next_future = Future()
        link = _ChainLink(future=next_future, on_fulfilled=None, on_rejected=on_rejected, flatten=True)
        self._add_chain_link(link)
        return next_future

    def with_timeout(self, timeout: float) -> "Future":
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        result_future = Future()
        settled_lock = threading.Lock()
        settled_flag: bool = False

        def _on_fulfill(value: Any) -> None:
            nonlocal settled_flag
            with settled_lock:
                if settled_flag:
                    return
                settled_flag = True
            try:
                result_future._fulfill(value)
            except FutureAlreadySettledError:
                pass

        def _on_reject(reason: Exception) -> None:
            nonlocal settled_flag
            with settled_lock:
                if settled_flag:
                    return
                settled_flag = True
            try:
                result_future._reject(reason)
            except FutureAlreadySettledError:
                pass

        def _on_timeout() -> None:
            nonlocal settled_flag
            with settled_lock:
                if settled_flag:
                    return
                settled_flag = True
            try:
                result_future._reject(TimeoutError(timeout))
            except FutureAlreadySettledError:
                pass

        with self._lock:
            already_settled = self._state != FutureState.PENDING
            current_value = self._value
            current_reason = self._reason
            current_state = self._state

        if already_settled:
            if current_state == FutureState.FULFILLED:
                result_future._fulfill(current_value)
            else:
                result_future._reject(current_reason)
            return result_future

        self._add_chain_link(_ChainLink(
            future=Future(),
            on_fulfilled=_on_fulfill,
            on_rejected=_on_reject,
        ))

        timer = threading.Timer(timeout, _on_timeout)
        timer.daemon = True
        timer.start()

        def _cancel_timer(_: Any) -> None:
            timer.cancel()

        result_future._add_chain_link(_ChainLink(
            future=Future(),
            on_fulfilled=_cancel_timer,
            on_rejected=_cancel_timer,
        ))

        return result_future

    @staticmethod
    def resolve(value: Any) -> "Future":
        f = Future()
        f._fulfill(value)
        return f

    @staticmethod
    def reject(reason: Exception) -> "Future":
        f = Future()
        f._reject(reason)
        return f

    @staticmethod
    def all(futures: List["Future"]) -> "Future":
        if not futures:
            return Future.resolve([])

        result_future = Future()
        total = len(futures)
        fulfilled_count = 0
        results: list = [None] * total
        lock = threading.Lock()
        rejected = False

        def _on_fulfill(index: int, value: Any) -> None:
            nonlocal fulfilled_count, rejected
            with lock:
                if rejected:
                    return
                results[index] = value
                fulfilled_count += 1
                if fulfilled_count == total:
                    try:
                        result_future._fulfill(list(results))
                    except FutureAlreadySettledError:
                        pass

        def _on_reject(reason: Exception) -> None:
            nonlocal rejected
            with lock:
                if rejected:
                    return
                rejected = True
            try:
                result_future._reject(reason)
            except FutureAlreadySettledError:
                pass

        for i, f in enumerate(futures):
            f._add_chain_link(_ChainLink(
                future=Future(),
                on_fulfilled=lambda v, idx=i: _on_fulfill(idx, v),
                on_rejected=_on_reject,
            ))

        return result_future

    @staticmethod
    def allSettled(futures: List["Future"]) -> "Future":
        if not futures:
            return Future.resolve([])

        result_future = Future()
        total = len(futures)
        settled_count = 0
        results: list = [None] * total
        lock = threading.Lock()

        def _on_fulfill(index: int, value: Any) -> None:
            nonlocal settled_count
            with lock:
                results[index] = SettledResult.fulfilled(value)
                settled_count += 1
                if settled_count == total:
                    try:
                        result_future._fulfill(list(results))
                    except FutureAlreadySettledError:
                        pass

        def _on_reject(index: int, reason: Exception) -> None:
            nonlocal settled_count
            with lock:
                results[index] = SettledResult.rejected(reason)
                settled_count += 1
                if settled_count == total:
                    try:
                        result_future._fulfill(list(results))
                    except FutureAlreadySettledError:
                        pass

        for i, f in enumerate(futures):
            f._add_chain_link(_ChainLink(
                future=Future(),
                on_fulfilled=lambda v, idx=i: _on_fulfill(idx, v),
                on_rejected=lambda e, idx=i: _on_reject(idx, e),
            ))

        return result_future

    @staticmethod
    def race(futures: List["Future"]) -> "Future":
        if not futures:
            raise ValueError("race requires at least one Future")

        result_future = Future()
        settled_lock = threading.Lock()
        settled_flag = False

        def _on_fulfill(value: Any) -> None:
            nonlocal settled_flag
            with settled_lock:
                if settled_flag:
                    return
                settled_flag = True
            try:
                result_future._fulfill(value)
            except FutureAlreadySettledError:
                pass

        def _on_reject(reason: Exception) -> None:
            nonlocal settled_flag
            with settled_lock:
                if settled_flag:
                    return
                settled_flag = True
            try:
                result_future._reject(reason)
            except FutureAlreadySettledError:
                pass

        for f in futures:
            f._add_chain_link(_ChainLink(
                future=Future(),
                on_fulfilled=_on_fulfill,
                on_rejected=_on_reject,
            ))

        return result_future


class _ChainLink:
    def __init__(
        self,
        future: Future,
        on_fulfilled: Optional[_OnFulfilled],
        on_rejected: Optional[_OnRejected],
        flatten: bool = False,
    ) -> None:
        self.future = future
        self.on_fulfilled = on_fulfilled
        self.on_rejected = on_rejected
        self.flatten = flatten
